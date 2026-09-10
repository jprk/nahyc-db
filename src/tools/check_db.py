"""Diagnostic report for the `h2regdocs` MariaDB database — row counts per
table, Step 2 load-health checks (identifier coverage, DocumentVersion
parity), Step 3a load-health checks (layer B/node_document coverage), and
a spot-check for a known regression-anchor record (`458/2000 Sb.`, also
used in `tests/test_search.py`).

Usage: `.venv/bin/python src/tools/check_db.py`
"""
import json
import os
import pathlib

import pymysql
from dotenv import load_dotenv

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
load_dotenv(REPO_ROOT / ".env")

TABLES = ["Document", "DocumentType", "DocumentSource", "Keyword",
          "DocumentKeyword", "DocumentVersion"]

LAYER_B_TABLES = ["node_description", "node_branch", "branch_step", "node_input",
                   "node_output", "subject", "node_subject", "node_problem",
                   "node_document"]


def get_connection():
    return pymysql.connect(
        host=os.environ["DB_HOST"], port=int(os.environ["DB_PORT"]),
        user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"], cursorclass=pymysql.cursors.DictCursor,
    )


def report(conn):
    c = conn.cursor()
    print("--- Row counts ---")
    for table in TABLES:
        c.execute(f"SELECT COUNT(*) AS n FROM {table}")
        print(f"{table}: {c.fetchone()['n']}")

    print("\n--- Step 2 load health ---")
    c.execute("SELECT COUNT(*) AS n FROM Document")
    doc_count = c.fetchone()["n"]
    c.execute("SELECT COUNT(*) AS n FROM Document WHERE identifier IS NOT NULL")
    print(f"Documents with a resolved identifier: {c.fetchone()['n']} / {doc_count}")
    c.execute("SELECT COUNT(*) AS n FROM Document WHERE jurisdikce IS NOT NULL")
    print(f"Documents with a resolved jurisdikce: {c.fetchone()['n']} / {doc_count}")
    c.execute("SELECT COUNT(*) AS n FROM DocumentVersion")
    version_count = c.fetchone()["n"]
    print(f"DocumentVersion rows: {version_count} (expect == {doc_count} for a fresh load)")
    c.execute("SELECT COUNT(*) AS n FROM DocumentVersion WHERE is_current = TRUE")
    print(f"DocumentVersion rows with is_current=TRUE: {c.fetchone()['n']} (expect == {doc_count})")
    c.execute("""
        SELECT document_id, COUNT(*) AS n FROM DocumentVersion
        GROUP BY document_id HAVING COUNT(*) > 1
    """)
    dupes = c.fetchall()
    print(f"Documents with more than one DocumentVersion row: {len(dupes)} (expect 0)")

    print("\n--- Step 3a load health (layer B + node_document) ---")
    for table in LAYER_B_TABLES:
        c.execute(f"SELECT COUNT(*) AS n FROM {table}")
        print(f"{table}: {c.fetchone()['n']}")
    c.execute("SELECT COUNT(DISTINCT node_id) AS n FROM node_description")
    print(f"Nodes with a node_description row: {c.fetchone()['n']} / 7")
    c.execute("""
        SELECT node_id, COUNT(*) AS n FROM node_document
        WHERE link_type = 'LEGAL_BASIS' GROUP BY node_id ORDER BY node_id
    """)
    print("node_document (LEGAL_BASIS) per node:", c.fetchall())

    print("\n--- Spot-check: 458/2000 Sb. ---")
    c.execute("""
        SELECT id, title, identifier, jurisdikce FROM Document
        WHERE identifier = %s
    """, ("458/2000 Sb.",))
    rows = c.fetchall()
    print(json.dumps(rows, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    connection = get_connection()
    report(connection)
    connection.close()
