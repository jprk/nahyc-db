import csv
import math
import io
import json
import os
import pathlib
import subprocess
from xml.etree.ElementTree import Element, SubElement, tostring

import pymysql
from dotenv import load_dotenv
from flask import Flask, render_template, request, g, send_file, abort, Response, url_for

app = Flask(__name__)

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
FULLTEXT_DIR = (REPO_ROOT / "data" / "fulltext").resolve()
load_dotenv(REPO_ROOT / ".env")


def get_git_version():
    """Best-effort short description of the running app's own git
    revision (e.g. "e69e637" or "e69e637-dirty") — shown in the footer so
    it's clear which deployed code is actually live. Computed once at
    import time (a running process doesn't change git revision under
    itself) rather than per-request. Never raises: git not installed, or
    a deployment that shipped without the .git directory (an exported
    zip, not this repo's own `zip/v01/` archive) just means it isn't
    shown — not a startup failure."""
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--always", "--dirty"],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=5, check=True)
        return result.stdout.strip() or None
    except (subprocess.SubprocessError, OSError):
        return None


GIT_VERSION = get_git_version()

# doc/REQUIREMENTS.md R2.5, 2026-09-11: export formats/fields for /export/<fmt>.
EXPORT_FORMATS = {"csv", "json", "xml"}
EXPORT_FIELDS = ["title", "description", "type_name", "source_name",
                  "language", "effective_date", "url", "keywords"]


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = pymysql.connect(
            host=os.environ["DB_HOST"], port=int(os.environ["DB_PORT"]),
            user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
            database=os.environ["DB_NAME"], cursorclass=pymysql.cursors.DictCursor,
        )
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def get_db_last_updated(db):
    """Last modification timestamp across the document catalog —
    `Document.updated_at` is already `ON UPDATE CURRENT_TIMESTAMP` (see
    doc/konsolidace/V01-baseline-schema.sql), so this reflects the most
    recent pipeline rebuild/init_db.py run without any new tracking
    needed. None for a genuinely empty table (a fresh, not-yet-seeded
    database) — never guessed."""
    with db.cursor() as cur:
        cur.execute("SELECT MAX(updated_at) AS last_updated FROM Document")
        row = cur.fetchone()
    return row["last_updated"] if row else None


@app.context_processor
def inject_footer_info():
    """Makes git_version/db_last_updated available to every template
    (the footer lives in base.html, shared by all pages) without every
    route having to remember to pass them explicitly."""
    return {
        "git_version": GIT_VERSION,
        "db_last_updated": get_db_last_updated(get_db()),
    }

def get_filters():
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT id, name FROM DocumentType ORDER BY name")
        types = cur.fetchall()
        cur.execute("SELECT id, name FROM DocumentSource ORDER BY name")
        sources = cur.fetchall()
        cur.execute("SELECT id, keyword FROM Keyword ORDER BY keyword")
        keywords = cur.fetchall()
    return types, sources, keywords


def get_total_document_count(db):
    """Real count for the hero section's "Search N documents" headline
    (used to be a hardcoded placeholder, "300") — every Document row,
    regardless of lifecycle state."""
    with db.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS c FROM Document")
        row = cur.fetchone()
    return row["c"] if row else 0


def get_active_document_count(db):
    """For the hero section's active/inactive breakdown note. "Active"
    means the document's CURRENT version's lifecycle_state is 'active' —
    the same three-way active/superseded/draft distinction DocumentVersion
    already tracks (see src/tools/init_db.py's classify_lifecycle_state()),
    not just every row in Document. The inactive ("outdated") count shown
    alongside it is derived as total - active, not a separate query — so
    the two numbers always add up to the headline total even for the
    (currently nonexistent) edge case of a Document with no current
    version row at all."""
    with db.cursor() as cur:
        cur.execute('''
            SELECT COUNT(DISTINCT d.id) AS c FROM Document d
            JOIN DocumentVersion dv ON dv.document_id = d.id
            WHERE dv.is_current = 1 AND dv.lifecycle_state = 'active'
        ''')
        row = cur.fetchone()
    return row["c"] if row else 0

# doc/PLAN.md §16, 2026-09-16: the list was capped at a hardcoded 100
# rows with a static "showing the first 100" banner and no way to reach
# the rest, so ~92 % of the corpus was unreachable through the UI.
PAGE_SIZE = 50

# How many numbered links to show around the current page.
PAGE_WINDOW = 2


def parse_page(args, page_count):
    """1-based page number from the query string, clamped into range.
    Garbage ("?page=abc", "?page=-3", "?page=999") falls back to a valid
    page rather than erroring — a page number is a navigation hint from a
    URL, not input worth rejecting."""
    try:
        page = int(args.get('page', 1))
    except (TypeError, ValueError):
        return 1
    return max(1, min(page, page_count))


def build_page_range(page, page_count):
    """Page numbers to render as links: the first, the last, and a window
    around the current one. `None` marks an elided gap, so the template
    can render an ellipsis without recomputing any of this."""
    if page_count <= 1:
        return []
    wanted = {1, page_count}
    wanted.update(p for p in range(page - PAGE_WINDOW, page + PAGE_WINDOW + 1)
                  if 1 <= p <= page_count)

    out = []
    previous = 0
    for p in sorted(wanted):
        if previous and p > previous + 1:
            out.append(None)
        out.append(p)
        previous = p
    return out


@app.template_global()
def page_url(page):
    """URL for `page` preserving every active filter — the pager must not
    silently drop the search the user is paging through."""
    args = {k: v for k, v in request.args.items() if k != 'page'}
    if page > 1:
        args['page'] = page
    return url_for('index', **args)


def parse_filters(args):
    """doc/REQUIREMENTS.md R2.3/R2.5, 2026-09-11: extracts the four
    recognized search/filter query params into a plain dict, shared by
    index() and /export/<fmt> so both apply identical filtering."""
    return {
        'q': args.get('q', '').strip(),
        'type_id': args.get('type_id', ''),
        'source_id': args.get('source_id', ''),
        'keyword_id': args.get('keyword_id', ''),
    }


def build_filter_clause(filters):
    """The shared WHERE fragment + params behind both the document list
    and its result count — kept in one place so the two can never drift
    apart and report different totals."""
    clause = ""
    params = []

    if filters['q']:
        clause += " AND (d.title LIKE %s OR d.description LIKE %s)"
        params.extend([f"%{filters['q']}%", f"%{filters['q']}%"])

    if filters['type_id']:
        clause += " AND d.type_id = %s"
        params.append(filters['type_id'])

    if filters['source_id']:
        clause += " AND d.source_id = %s"
        params.append(filters['source_id'])

    if filters['keyword_id']:
        clause += " AND dk.keyword_id = %s"
        params.append(filters['keyword_id'])

    return clause, params


def build_count_query(filters):
    """doc/PLAN.md §16, 2026-09-16: total number of documents matching
    `filters`, for the pager.

    COUNT(DISTINCT d.id), not COUNT(*): the keyword filter needs the
    DocumentKeyword join, which multiplies a document's rows by its
    keyword count (3231 links over 1238 documents). A plain COUNT(*)
    would therefore report several times the real total and paginate
    into empty pages — the same trap R2.1 exists for, and that commit
    ebc1f60 had to fix once already with GROUP BY d.id."""
    clause, params = build_filter_clause(filters)
    return f'''
        SELECT COUNT(DISTINCT d.id) AS c
        FROM Document d
        LEFT JOIN DocumentType dt ON d.type_id = dt.id
        LEFT JOIN DocumentSource ds ON d.source_id = ds.id
        LEFT JOIN DocumentKeyword dk ON d.id = dk.document_id
        WHERE 1=1{clause}
    ''', params


def build_document_query(filters, limit=None, offset=None):
    """doc/REQUIREMENTS.md R2.1/R2.3/R2.5, 2026-09-11: pure function (no
    DB access) building the parameterized SQL + params for the filtered
    document list. Shared by index() (one page at a time, see PAGE_SIZE)
    and /export/<fmt> (limit=None, i.e. the full filtered result set — an
    export must not silently truncate at the UI's page size). Returns
    (sql, params)."""
    base_query = '''
        SELECT d.id, d.slug, d.title, d.description, d.popis_priblizny,
               dt.name as type_name,
               ds.name as source_name, d.language, d.effective_date, d.url,
               d.file_path, dt.restricted_fulltext, d.needs_review, d.review_reason
        FROM Document d
        LEFT JOIN DocumentType dt ON d.type_id = dt.id
        LEFT JOIN DocumentSource ds ON d.source_id = ds.id
        LEFT JOIN DocumentKeyword dk ON d.id = dk.document_id
        WHERE 1=1
    '''
    clause, params = build_filter_clause(filters)
    base_query += clause

    base_query += " GROUP BY d.id ORDER BY d.title ASC"
    if limit is not None:
        base_query += " LIMIT %s"
        params.append(limit)
        if offset:
            base_query += " OFFSET %s"
            params.append(offset)

    return base_query, params


def fetch_documents_with_tags(db, filters, limit=None, offset=None):
    """Runs build_document_query() and attaches each document's keyword
    tags, exactly like index()'s original inline logic. Returns
    (documents, doc_tags) — used by both index() and /export/<fmt>."""
    query, params = build_document_query(filters, limit=limit, offset=offset)
    with db.cursor() as cur:
        cur.execute(query, params)
        documents = cur.fetchall()

        doc_ids = [doc['id'] for doc in documents]
        doc_tags = {}
        if doc_ids:
            placeholders = ','.join(['%s'] * len(doc_ids))
            tags_query = f'''
                SELECT dk.document_id, k.keyword
                FROM Keyword k
                JOIN DocumentKeyword dk ON k.id = dk.keyword_id
                WHERE dk.document_id IN ({placeholders})
            '''
            cur.execute(tags_query, doc_ids)
            tags = cur.fetchall()
            for tag in tags:
                doc_id = tag['document_id']
                if doc_id not in doc_tags:
                    doc_tags[doc_id] = []
                doc_tags[doc_id].append(tag['keyword'])
    return documents, doc_tags


@app.route('/')
def index():
    db = get_db()
    filters = parse_filters(request.args)
    types, sources, keywords = get_filters()

    with db.cursor() as cur:
        count_query, count_params = build_count_query(filters)
        cur.execute(count_query, count_params)
        row = cur.fetchone()
    result_count = row['c'] if row else 0

    page_count = max(1, math.ceil(result_count / PAGE_SIZE))
    page = parse_page(request.args, page_count)

    documents, doc_tags = fetch_documents_with_tags(
        db, filters, limit=PAGE_SIZE, offset=(page - 1) * PAGE_SIZE)
    total_document_count = get_total_document_count(db)
    active_document_count = get_active_document_count(db)
    inactive_document_count = total_document_count - active_document_count

    return render_template('index.html',
                           documents=documents,
                           doc_tags=doc_tags,
                           types=types,
                           sources=sources,
                           keywords=keywords,
                           total_document_count=total_document_count,
                           active_document_count=active_document_count,
                           inactive_document_count=inactive_document_count,
                           result_count=result_count,
                           page=page,
                           page_count=page_count,
                           page_size=PAGE_SIZE,
                           page_range=build_page_range(page, page_count),
                           request=request)

def fetch_document_detail(db, slug):
    """Everything the per-document page shows, or None when no document
    carries that slug. Three of these tables are populated but were never
    surfaced anywhere in the UI before doc/PLAN.md §16: DocumentVersion
    (1258 rows, until now read only for the hero's aggregate count),
    document_relation (46 edges) and the record's own jurisdiction
    columns."""
    with db.cursor() as cur:
        cur.execute('''
            SELECT d.id, d.slug, d.identifier, d.title, d.description,
                   d.popis_priblizny,
                   d.language, d.effective_date, d.url, d.file_path,
                   d.jurisdikce, d.jurisdikce_uroven, d.needs_review,
                   d.review_reason, d.updated_at,
                   dt.name AS type_name, dt.restricted_fulltext,
                   ds.name AS source_name
            FROM Document d
            LEFT JOIN DocumentType dt ON d.type_id = dt.id
            LEFT JOIN DocumentSource ds ON d.source_id = ds.id
            WHERE d.slug = %s
        ''', (slug,))
        document = cur.fetchone()
        if document is None:
            return None

        cur.execute('''
            SELECT k.keyword FROM Keyword k
            JOIN DocumentKeyword dk ON k.id = dk.keyword_id
            WHERE dk.document_id = %s ORDER BY k.keyword
        ''', (document['id'],))
        keywords = [r['keyword'] for r in cur.fetchall()]

        cur.execute('''
            SELECT version, edition_label, effective_date, is_current, lifecycle_state
            FROM DocumentVersion WHERE document_id = %s ORDER BY version
        ''', (document['id'],))
        versions = cur.fetchall()

        # Both directions in one pass: `direction` tells the template
        # whether this document is the subject or the object of the
        # relation, so e.g. an IMPLEMENTS edge can be phrased correctly
        # from either end rather than always reading as if this record
        # were the implementing one.
        cur.execute('''
            SELECT r.relation_type, 'from' AS direction, r.note,
                   o.id AS other_id, o.slug AS other_slug,
                   o.title AS other_title, o.identifier AS other_identifier
            FROM document_relation r
            JOIN Document o ON o.id = r.to_document_id
            WHERE r.from_document_id = %s
            UNION ALL
            SELECT r.relation_type, 'to' AS direction, r.note,
                   o.id AS other_id, o.slug AS other_slug,
                   o.title AS other_title, o.identifier AS other_identifier
            FROM document_relation r
            JOIN Document o ON o.id = r.from_document_id
            WHERE r.to_document_id = %s
        ''', (document['id'], document['id']))
        relations = cur.fetchall()

    return {"document": document, "keywords": keywords,
            "versions": versions, "relations": relations}


@app.route('/dokument/<slug>')
def document_detail(slug):
    """doc/PLAN.md §16, 2026-09-16: permanent page for one document.

    Keyed on `Document.slug`, never on `Document.id` — init_db.py
    TRUNCATEs and reloads on every rebuild, so ids are reassigned and any
    link built on one silently rots (§14 caught exactly that happening to
    id 147). See src/tools/slug.py."""
    detail = fetch_document_detail(get_db(), slug)
    if detail is None:
        abort(404)
    return render_template('document.html', **detail)


@app.route('/fulltext/<int:doc_id>')
def fulltext(doc_id):
    """doc/REQUIREMENTS.md R1.7/R4.1, 2026-09-11: serves a document's
    locally-cached full text (populated by src/tools/fetch_fulltext.py,
    see Document.file_path), but only when its DocumentType is NOT flagged
    restricted_fulltext (copyrighted/paywalled standards — see
    src/tools/init_db.py's RESTRICTED_DOCUMENT_TYPES). This check runs
    server-side on every request, independent of whether the template
    happened to render a download link, so metadata (this route's mere
    existence, the document's title/type/etc.) stays publicly visible
    while the actual file content stays gated even against a guessed URL.
    The resolved path is also verified to stay inside FULLTEXT_DIR before
    being served, even though file_path only ever comes from our own
    trusted manifest — defense in depth against path traversal."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute('''
            SELECT d.file_path, dt.restricted_fulltext
            FROM Document d
            LEFT JOIN DocumentType dt ON d.type_id = dt.id
            WHERE d.id = %s
        ''', (doc_id,))
        row = cur.fetchone()

    if row is None or not row['file_path']:
        abort(404)
    if row['restricted_fulltext']:
        abort(403)

    full_path = (REPO_ROOT / row['file_path']).resolve()
    if FULLTEXT_DIR not in full_path.parents or not full_path.is_file():
        abort(404)

    return send_file(full_path)


def _rows_for_export(documents, doc_tags):
    """doc/REQUIREMENTS.md R2.5/R4.1, 2026-09-11: projects each document
    row down to exactly EXPORT_FIELDS — deliberately excludes file_path/
    restricted_fulltext/id, which must never leave via bulk export (see
    /fulltext/<id> above for that separate, gated channel)."""
    rows = []
    for doc in documents:
        rows.append({
            'title': doc['title'] or '',
            'description': doc['description'] or '',
            'type_name': doc['type_name'] or '',
            'source_name': doc['source_name'] or '',
            'language': doc['language'] or '',
            'effective_date': str(doc['effective_date']) if doc['effective_date'] else '',
            'url': doc['url'] or '',
            'keywords': ', '.join(doc_tags.get(doc['id'], [])),
        })
    return rows


def _export_csv(rows):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=EXPORT_FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    return Response(
        buf.getvalue(), mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=dokumenty.csv'})


def _export_json(rows):
    body = json.dumps(rows, ensure_ascii=False, indent=2)
    return Response(
        body, mimetype='application/json',
        headers={'Content-Disposition': 'attachment; filename=dokumenty.json'})


def _export_xml(rows):
    root = Element('documents')
    for row in rows:
        doc_el = SubElement(root, 'document')
        for field in EXPORT_FIELDS:
            SubElement(doc_el, field).text = row[field]
    body = tostring(root, encoding='unicode')
    return Response(
        body, mimetype='application/xml',
        headers={'Content-Disposition': 'attachment; filename=dokumenty.xml'})


@app.route('/export/<fmt>')
def export(fmt):
    """doc/REQUIREMENTS.md R2.5, 2026-09-11: exports the current
    filtered/searched result set (same q/type_id/source_id/keyword_id
    filters as index()) in csv, json, or xml — the FULL filtered set, not
    the on-screen LIMIT 100 page. Metadata-only per R4.1: never includes
    file_path/restricted_fulltext (see _rows_for_export() — that's the
    separate, gated /fulltext/<id> channel above)."""
    if fmt not in EXPORT_FORMATS:
        abort(400)

    db = get_db()
    filters = parse_filters(request.args)
    documents, doc_tags = fetch_documents_with_tags(db, filters, limit=None)
    rows = _rows_for_export(documents, doc_tags)

    if fmt == 'csv':
        return _export_csv(rows)
    if fmt == 'json':
        return _export_json(rows)
    return _export_xml(rows)


if __name__ == '__main__':
    # Run the app in debug mode on port 5050
    app.run(debug=True, port=5050)
