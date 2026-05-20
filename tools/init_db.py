import sqlite3
import json
import pathlib
from datetime import datetime
import os

base_dir = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(base_dir, '..', 'db', 'regulatory_documents.db')

def create_schema(cursor):
    """Creates the SQLite tables based on the updated UML diagram."""
    print("Creating database schema...")
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS document_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(255) UNIQUE,
            description TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS document_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(255) UNIQUE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword VARCHAR(255) UNIQUE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title VARCHAR(255),
            description TEXT,
            type_id INTEGER,
            source_id INTEGER,
            language VARCHAR(50),
            url VARCHAR(500),
            file_path VARCHAR(255),
            effective_date VARCHAR(50),
            version INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (type_id) REFERENCES document_types(id),
            FOREIGN KEY (source_id) REFERENCES document_sources(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS document_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER,
            version INTEGER,
            file_path VARCHAR(255),
            change_log TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (document_id) REFERENCES documents(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS document_keywords (
            document_id INTEGER,
            keyword_id INTEGER,
            PRIMARY KEY (document_id, keyword_id),
            FOREIGN KEY (document_id) REFERENCES documents(id),
            FOREIGN KEY (keyword_id) REFERENCES keywords(id)
        )
    ''')

def get_or_create(cursor, table, val_dict, return_col='id'):
    """Helper to get a record ID or insert it if it doesn't exist."""
    # Build WHERE clause
    where_clause = ' AND '.join([f"{k} = ?" for k in val_dict.keys()])
    values = tuple(val_dict.values())
    
    cursor.execute(f"SELECT {return_col} FROM {table} WHERE {where_clause}", values)
    result = cursor.fetchone()
    if result:
        return result[0]
        
    # Insert
    cols = ', '.join(val_dict.keys())
    placeholders = ', '.join(['?'] * len(val_dict))
    cursor.execute(f"INSERT INTO {table} ({cols}) VALUES ({placeholders})", values)
    return cursor.lastrowid

def import_json_data(db_conn):
    json_path = pathlib.Path(os.path.join(base_dir, '..', 'data', 'databaze_komplet.json'))
    print(f"Reading from {json_path}")
    
    if not json_path.exists():
        print(f"Error: {json_path} does not exist. Run build_unified_db.py first.")
        return
        
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    print(f"Found {len(data)} records to import.")
    
    cursor = db_conn.cursor()
    
    for item in data:
        title = item.get("nazev_cz", "").strip()
        if not title:
            title = item.get("nazev_sk", "").strip()
            if not title:
                title = item.get("nazev_eu", "").strip()
        if not title:
            continue
            
        doc_type = item.get("typ_dokumentu", "").strip()
        
        gestor = item.get("gestor", [])
        if isinstance(gestor, list):
            source = ", ".join(gestor)
        else:
            source = str(gestor)
            
        language = item.get("jazyk", "").strip()
        effective_date = item.get("platnost", "").strip()
        
        url = item.get("odkaz_hlavni", "").strip()
        if not url:
             url = item.get("odkaz_eu", "").strip()
             if not url:
                 url = item.get("odkaz_sk", "").strip()
                 
        description = item.get("anotace_poznamka", "").strip()
        
        type_id = None
        if doc_type:
            type_id = get_or_create(cursor, 'document_types', {'name': doc_type})
            
        source_id = None
        if source:
            source_id = get_or_create(cursor, 'document_sources', {'name': source})
            
        cursor.execute('''
            INSERT INTO documents 
            (title, description, type_id, source_id, language, url, effective_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (title, description, type_id, source_id, language, url, effective_date))
        
        doc_id = cursor.lastrowid
        
        klicova_slova = item.get("klicova_slova", [])
        if not isinstance(klicova_slova, list):
            klicova_slova = [klicova_slova]
            
        sekce = item.get("sekce", "").strip()
        kategorie = item.get("kategorie_trida", "").strip()
        
        if sekce and sekce not in klicova_slova:
            klicova_slova.append(sekce)
        if kategorie and kategorie not in klicova_slova:
            klicova_slova.append(kategorie)
            
        for kw in klicova_slova:
            if isinstance(kw, str) and kw.strip():
                kw_id = get_or_create(cursor, 'keywords', {'keyword': kw.strip()})
                try:
                    cursor.execute('INSERT INTO document_keywords (document_id, keyword_id) VALUES (?, ?)', (doc_id, kw_id))
                except sqlite3.IntegrityError:
                    pass
                    
    db_conn.commit()
    print("Import complete.")

if __name__ == "__main__":
    if os.path.exists(DB_PATH):
        print(f"Removing existing {DB_PATH} to start fresh.")
        os.remove(DB_PATH)
        
    conn = sqlite3.connect(DB_PATH)
    create_schema(conn.cursor())
    conn.commit()
    
    import_json_data(conn)
    
    # Print some stats
    c = conn.cursor()
    print("\n--- Database Stats ---")
    c.execute("SELECT COUNT(*) FROM documents")
    print(f"Total Documents: {c.fetchone()[0]}")
    c.execute("SELECT COUNT(*) FROM document_sources")
    print(f"Unique Sources: {c.fetchone()[0]}")
    c.execute("SELECT COUNT(*) FROM keywords")
    print(f"Unique Keywords extracted from filenames: {c.fetchone()[0]}")
    
    conn.close()
