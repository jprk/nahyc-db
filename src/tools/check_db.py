import json
import os
import pathlib

import pymysql
from dotenv import load_dotenv

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
load_dotenv(REPO_ROOT / ".env")

conn = pymysql.connect(
    host=os.environ["DB_HOST"], port=int(os.environ["DB_PORT"]),
    user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
    database=os.environ["DB_NAME"], cursorclass=pymysql.cursors.DictCursor,
)
c = conn.cursor()
c.execute("SELECT id, title, type_id, source_id FROM Document WHERE title LIKE %s",
          ("%Energetický zákon%",))
rows = c.fetchall()
print(json.dumps(rows, indent=2, ensure_ascii=False))
conn.close()
