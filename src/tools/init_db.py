import json
import os
import pathlib

import pymysql
from dotenv import load_dotenv

BASE_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent
JSON_PATH = REPO_ROOT / "data" / "database_merged_deduplicated.json"

# Truncation order respects FK dependencies (children before parents).
TRUNCATE_ORDER = ["DocumentKeyword", "DocumentVersion", "Document", "Keyword",
                  "DocumentSource", "DocumentType"]


def get_connection():
    load_dotenv(REPO_ROOT / ".env")
    return pymysql.connect(
        host=os.environ["DB_HOST"], port=int(os.environ["DB_PORT"]),
        user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"], autocommit=False,
    )


def reset_tables(cursor):
    print("Clearing existing rows from V01 tables...")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    for table in TRUNCATE_ORDER:
        cursor.execute(f"TRUNCATE TABLE {table}")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")


def get_or_create(cursor, table, val_dict, return_col="id"):
    """Helper to get a record ID or insert it if it doesn't exist."""
    where_clause = " AND ".join([f"{k} = %s" for k in val_dict.keys()])
    values = tuple(val_dict.values())

    cursor.execute(f"SELECT {return_col} FROM {table} WHERE {where_clause}", values)
    result = cursor.fetchone()
    if result:
        return result[0]

    cols = ", ".join(val_dict.keys())
    placeholders = ", ".join(["%s"] * len(val_dict))
    cursor.execute(f"INSERT INTO {table} ({cols}) VALUES ({placeholders})", values)
    return cursor.lastrowid


def import_json_data(db_conn):
    print(f"Reading from {JSON_PATH}")

    if not JSON_PATH.exists():
        print(f"Error: {JSON_PATH} does not exist. Run build_unified_db.py first.")
        return

    with open(JSON_PATH, "r", encoding="utf-8") as f:
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
            type_id = get_or_create(cursor, "DocumentType", {"name": doc_type})

        source_id = None
        if source:
            source_id = get_or_create(cursor, "DocumentSource", {"name": source})

        cursor.execute("""
            INSERT INTO Document
            (title, description, type_id, source_id, language, url, effective_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (title, description, type_id, source_id, language, url, effective_date))

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
                kw_id = get_or_create(cursor, "Keyword", {"keyword": kw.strip()})
                try:
                    cursor.execute(
                        "INSERT INTO DocumentKeyword (document_id, keyword_id) VALUES (%s, %s)",
                        (doc_id, kw_id))
                except pymysql.err.IntegrityError:
                    pass

    db_conn.commit()
    print("Import complete.")


if __name__ == "__main__":
    conn = get_connection()

    reset_tables(conn.cursor())
    conn.commit()

    import_json_data(conn)

    c = conn.cursor()
    print("\n--- Database Stats ---")
    c.execute("SELECT COUNT(*) FROM Document")
    print(f"Total Documents: {c.fetchone()[0]}")
    c.execute("SELECT COUNT(*) FROM DocumentSource")
    print(f"Unique Sources: {c.fetchone()[0]}")
    c.execute("SELECT COUNT(*) FROM Keyword")
    print(f"Unique Keywords extracted from filenames: {c.fetchone()[0]}")

    conn.close()
