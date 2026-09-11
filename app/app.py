import os
import pathlib

import pymysql
from dotenv import load_dotenv
from flask import Flask, render_template, request, g

app = Flask(__name__)

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
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
               ds.name as source_name, d.language, d.effective_date, d.url
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

if __name__ == '__main__':
    # Run the app in debug mode on port 5000
    app.run(debug=True, port=5000)
