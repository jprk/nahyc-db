import json
import os
import pathlib
import re

import pymysql
from dotenv import load_dotenv

BASE_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent
JSON_PATH = REPO_ROOT / "data" / "database_merged_deduplicated.json"

# Truncation order respects FK dependencies (children before parents).
TRUNCATE_ORDER = ["DocumentKeyword", "DocumentVersion", "Document", "Keyword",
                  "DocumentSource", "DocumentType"]

# A purely-numeric (or blank) typ_dokumentu is leaked category-id junk —
# 44 records, all from Haltuf_Dokumenty (e.g. "1", "2", "9") — that must
# not become its own DocumentType row. See doc/PLAN.md Step 2.
_NUMERIC_TYPE_RE = re.compile(r"^\d+$")
FALLBACK_DOCUMENT_TYPE = "Nezařazeno"

# jurisdikce values that mean "we don't have a real jurisdiction to
# attribute to this gestor" — never used to seed DocumentSource.jurisdiction.
_UNKNOWN_JURISDIKCE = {"", "neurčeno"}

# Document.identifier is VARCHAR(100) — a znacka longer than this can't be
# stored as-is. Found in practice: one Sinay-parsed record bundles several
# distinct STN designations (newline-joined) into a single znacka field, a
# PDF-parsing artifact, not a real single identifier — see doc/PLAN.md Step 2.
IDENTIFIER_MAX_LENGTH = 100


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


def get_or_create(cursor, table, val_dict, extra_insert_cols=None, return_col="id"):
    """Helper to get a record ID or insert it if it doesn't exist.
    `extra_insert_cols` are only ever written on first INSERT (not part of
    the WHERE match) — used for DocumentSource.institution_type/jurisdiction,
    which key on `name` alone but carry extra derived columns."""
    where_clause = " AND ".join([f"{k} = %s" for k in val_dict.keys()])
    values = tuple(val_dict.values())

    cursor.execute(f"SELECT {return_col} FROM {table} WHERE {where_clause}", values)
    result = cursor.fetchone()
    if result:
        return result[0]

    insert_dict = dict(val_dict)
    if extra_insert_cols:
        insert_dict.update(extra_insert_cols)
    cols = ", ".join(insert_dict.keys())
    placeholders = ", ".join(["%s"] * len(insert_dict))
    cursor.execute(f"INSERT INTO {table} ({cols}) VALUES ({placeholders})", tuple(insert_dict.values()))
    return cursor.lastrowid


def resolve_identifier(znacka, seen_identifiers):
    """Returns the `Document.identifier` value for this record, or None.
    Blank znacka -> None (MariaDB allows multiple NULLs under the UNIQUE
    constraint on `identifier`, so this is free). A znacka that collides
    with one already assigned earlier this run also -> None, with a
    printed warning, instead of crashing the load — a known, disclosed
    residual (e.g. "ASTM F1624-12" exists once as CZ and once as US; same
    reference number, legitimately different national instruments — see
    doc/PLAN.md Step 1 follow-up #9). Mutates `seen_identifiers`."""
    z = (znacka or "").strip()
    if not z:
        return None
    if len(z) > IDENTIFIER_MAX_LENGTH:
        print(f"WARNING: znacka too long for identifier ({len(z)} > "
              f"{IDENTIFIER_MAX_LENGTH} chars) — leaving identifier NULL: {z[:80]!r}...")
        return None
    if z in seen_identifiers:
        print(f"WARNING: duplicate znacka {z!r} across final records — "
              f"leaving identifier NULL for this one (see doc/PLAN.md Step 1 "
              f"follow-up #9 for the known cross-jurisdiction residual).")
        return None
    seen_identifiers.add(z)
    return z


def resolve_document_type(typ_dokumentu):
    """Returns the DocumentType.name to use for this record — the stripped
    value, or FALLBACK_DOCUMENT_TYPE when it's blank or purely numeric
    (leaked category-id junk, see module docstring)."""
    t = (typ_dokumentu or "").strip()
    if not t or _NUMERIC_TYPE_RE.match(t):
        return FALLBACK_DOCUMENT_TYPE
    return t


def normalize_jurisdikce(jurisdikce):
    """Returns the `Document.jurisdikce` value — blank -> None, else the
    stripped value verbatim (including "neurčeno", which is a real,
    meaningful classification outcome — "we tried and couldn't tell" is
    different from "we never had this field at all")."""
    j = (jurisdikce or "").strip()
    return j or None


def build_gestor_jurisdiction_map(records):
    """Pre-scans all records once to determine each non-blank gestor's
    jurisdiction up front. Needed because DocumentSource rows are
    get_or_create'd — whichever record for a given gestor is processed
    FIRST decides what gets inserted, so the correct value must be known
    before that first insert, not discovered from a later record. Verified
    empirically (doc/PLAN.md Step 2): zero real per-gestor jurisdikce
    conflicts exist in the current corpus, so "first non-blank, non-
    unknown value found" is safe, not an arbitrary pick."""
    mapping = {}
    for item in records:
        gestor = item.get("gestor", [])
        if isinstance(gestor, list):
            gestor = ", ".join(gestor)
        gestor = (gestor or "").strip()
        if not gestor or gestor in mapping:
            continue
        jurisdikce = (item.get("jurisdikce") or "").strip()
        if jurisdikce not in _UNKNOWN_JURISDIKCE:
            mapping[gestor] = jurisdikce
    return mapping


def resolve_source_jurisdiction(gestor_name, gestor_jurisdiction_map):
    """Returns (institution_type, jurisdiction) for this DocumentSource.
    `institution_type` is never populated this pass — no reliable source
    data to derive it from (not guessed). `jurisdiction` is looked up from
    the pre-built map for a non-blank gestor; a blank gestor (95% of
    records, nearly all norms) gets (None, None) — DocumentSource can't
    carry per-document jurisdikce for those, see doc/PLAN.md Step 2 (that's
    what the new Document.jurisdikce column is for)."""
    gestor_name = (gestor_name or "").strip()
    if not gestor_name:
        return None, None
    return None, gestor_jurisdiction_map.get(gestor_name)


def import_json_data(db_conn):
    print(f"Reading from {JSON_PATH}")

    if not JSON_PATH.exists():
        print(f"Error: {JSON_PATH} does not exist. Run build_unified_db.py first.")
        return

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"Found {len(data)} records to import.")

    cursor = db_conn.cursor()
    seen_identifiers = set()
    gestor_jurisdiction_map = build_gestor_jurisdiction_map(data)

    for item in data:
        title = item.get("nazev_cz", "").strip()
        if not title:
            title = item.get("nazev_sk", "").strip()
            if not title:
                title = item.get("nazev_eu", "").strip()
        if not title:
            continue

        doc_type = resolve_document_type(item.get("typ_dokumentu", ""))

        gestor = item.get("gestor", [])
        if isinstance(gestor, list):
            source = ", ".join(gestor)
        else:
            source = str(gestor)
        source = source.strip()

        language = item.get("jazyk", "").strip()
        effective_date = item.get("platnost", "").strip()

        url = item.get("odkaz_hlavni", "").strip()
        if not url:
            url = item.get("odkaz_eu", "").strip()
            if not url:
                url = item.get("odkaz_sk", "").strip()

        description = item.get("anotace_poznamka", "").strip()
        identifier = resolve_identifier(item.get("znacka", ""), seen_identifiers)
        jurisdikce = normalize_jurisdikce(item.get("jurisdikce", ""))

        type_id = get_or_create(cursor, "DocumentType", {"name": doc_type})

        source_id = None
        if source:
            institution_type, source_jurisdiction = resolve_source_jurisdiction(
                source, gestor_jurisdiction_map)
            source_id = get_or_create(
                cursor, "DocumentSource", {"name": source},
                extra_insert_cols={"institution_type": institution_type,
                                    "jurisdiction": source_jurisdiction})

        cursor.execute("""
            INSERT INTO Document
            (title, description, type_id, source_id, language, url,
             effective_date, identifier, jurisdikce)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (title, description, type_id, source_id, language, url,
              effective_date, identifier, jurisdikce))

        doc_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO DocumentVersion (document_id, version, is_current)
            VALUES (%s, 1, TRUE)
        """, (doc_id,))

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
    c.execute("SELECT COUNT(*) FROM DocumentVersion")
    print(f"Document versions: {c.fetchone()[0]}")
    c.execute("SELECT COUNT(*) FROM Document WHERE identifier IS NOT NULL")
    print(f"Documents with a resolved identifier: {c.fetchone()[0]}")

    conn.close()
