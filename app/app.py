import os
import pathlib

import pymysql
from dotenv import load_dotenv
from flask import Flask, render_template, request, g, send_file, abort

app = Flask(__name__)

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
FULLTEXT_DIR = (REPO_ROOT / "data" / "fulltext").resolve()
load_dotenv(REPO_ROOT / ".env")


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

@app.route('/')
def index():
    db = get_db()

    # Query parameters
    search_query = request.args.get('q', '').strip()
    type_id = request.args.get('type_id', '')
    source_id = request.args.get('source_id', '')
    keyword_id = request.args.get('keyword_id', '')

    types, sources, keywords = get_filters()

    # Build query
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

    if search_query:
        base_query += " AND (d.title LIKE %s OR d.description LIKE %s)"
        params.extend([f'%{search_query}%', f'%{search_query}%'])

    if type_id:
        base_query += " AND d.type_id = %s"
        params.append(type_id)

    if source_id:
        base_query += " AND d.source_id = %s"
        params.append(source_id)

    if keyword_id:
        base_query += " AND dk.keyword_id = %s"
        params.append(keyword_id)

    base_query += " GROUP BY d.id ORDER BY d.title ASC LIMIT 100"

    with db.cursor() as cur:
        cur.execute(base_query, params)
        documents = cur.fetchall()

        # Fetch keywords for documents to display as tags
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


if __name__ == '__main__':
    # Run the app in debug mode on port 5000
    app.run(debug=True, port=5000)
