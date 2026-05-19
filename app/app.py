import os
import sqlite3
from flask import Flask, render_template, request, g

app = Flask(__name__)

# The database is located in the 'Databaze' folder
DB_PATH = os.path.join('..', 'db', 'regulatory_documents.db')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH)
        # Required to return dictionaries instead of tuples
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def get_filters():
    db = get_db()
    types = db.execute("SELECT id, name FROM document_types ORDER BY name").fetchall()
    sources = db.execute("SELECT id, name FROM document_sources ORDER BY name").fetchall()
    keywords = db.execute("SELECT id, keyword FROM keywords ORDER BY keyword").fetchall()
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
        SELECT MIN(d.id) as id, d.title, d.description, dt.name as type_name, 
               ds.name as source_name, d.language, d.effective_date, d.url
        FROM documents d
        LEFT JOIN document_types dt ON d.type_id = dt.id
        LEFT JOIN document_sources ds ON d.source_id = ds.id
        LEFT JOIN document_keywords dk ON d.id = dk.document_id
        WHERE 1=1
    '''
    params = []
    
    if search_query:
        base_query += " AND (d.title LIKE ? OR d.description LIKE ?)"
        params.extend([f'%{search_query}%', f'%{search_query}%'])
        
    if type_id:
        base_query += " AND d.type_id = ?"
        params.append(type_id)
        
    if source_id:
        base_query += " AND d.source_id = ?"
        params.append(source_id)
        
    if keyword_id:
        base_query += " AND dk.keyword_id = ?"
        params.append(keyword_id)
        
    base_query += " GROUP BY d.title ORDER BY d.title ASC LIMIT 100"
    
    documents = db.execute(base_query, params).fetchall()
    
    # Fetch keywords for documents to display as tags
    doc_ids = [doc['id'] for doc in documents]
    doc_tags = {}
    if doc_ids:
        placeholders = ','.join('?' * len(doc_ids))
        tags_query = f'''
            SELECT dk.document_id, k.keyword
            FROM keywords k
            JOIN document_keywords dk ON k.id = dk.keyword_id
            WHERE dk.document_id IN ({placeholders})
        '''
        tags = db.execute(tags_query, doc_ids).fetchall()
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
