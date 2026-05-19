import sqlite3
import json

conn = sqlite3.connect('../db/regulatory_documents.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute("SELECT id, title, type_id, source_id FROM documents WHERE title LIKE '%Energetický zákon%'")
rows = c.fetchall()
print(json.dumps([dict(r) for r in rows], indent=2))
