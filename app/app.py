import csv
import io
import json
import os
import pathlib
from xml.etree.ElementTree import Element, SubElement, tostring

import pymysql
from dotenv import load_dotenv
from flask import Flask, render_template, request, g, send_file, abort, Response

app = Flask(__name__)

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
FULLTEXT_DIR = (REPO_ROOT / "data" / "fulltext").resolve()
load_dotenv(REPO_ROOT / ".env")

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


def build_document_query(filters, limit=None):
    """doc/REQUIREMENTS.md R2.1/R2.3/R2.5, 2026-09-11: pure function (no
    DB access) building the parameterized SQL + params for the filtered
    document list. Shared by index() (limit=100, the on-screen page) and
    /export/<fmt> (limit=None, i.e. the full filtered result set — an
    export must not silently truncate at the UI's page size). Returns
    (sql, params)."""
    base_query = '''
        SELECT d.id, d.title, d.description, dt.name as type_name,
               ds.name as source_name, d.language, d.effective_date, d.url,
               d.file_path, dt.restricted_fulltext
        FROM Document d
        LEFT JOIN DocumentType dt ON d.type_id = dt.id
        LEFT JOIN DocumentSource ds ON d.source_id = ds.id
        LEFT JOIN DocumentKeyword dk ON d.id = dk.document_id
        WHERE 1=1
    '''
    params = []

    if filters['q']:
        base_query += " AND (d.title LIKE %s OR d.description LIKE %s)"
        params.extend([f"%{filters['q']}%", f"%{filters['q']}%"])

    if filters['type_id']:
        base_query += " AND d.type_id = %s"
        params.append(filters['type_id'])

    if filters['source_id']:
        base_query += " AND d.source_id = %s"
        params.append(filters['source_id'])

    if filters['keyword_id']:
        base_query += " AND dk.keyword_id = %s"
        params.append(filters['keyword_id'])

    base_query += " GROUP BY d.id ORDER BY d.title ASC"
    if limit is not None:
        base_query += " LIMIT %s"
        params.append(limit)

    return base_query, params


def fetch_documents_with_tags(db, filters, limit=None):
    """Runs build_document_query() and attaches each document's keyword
    tags, exactly like index()'s original inline logic. Returns
    (documents, doc_tags) — used by both index() and /export/<fmt>."""
    query, params = build_document_query(filters, limit=limit)
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
    documents, doc_tags = fetch_documents_with_tags(db, filters, limit=100)

    return render_template('index.html',
                           documents=documents,
                           doc_tags=doc_tags,
                           types=types,
                           sources=sources,
                           keywords=keywords,
                           request=request)

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
    # Run the app in debug mode on port 5000
    app.run(debug=True, port=5000)
