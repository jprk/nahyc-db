"""Splits the documents of acts that exist in a Czech and an English language
variant, in the live database, the way a rebuild from data/database_merged_
deduplicated.json now does (see language_variants.py / split_language_variants.py).

Until now such an act was ONE document that carried a mix of both variants: the
title of one, the language label of the other, the address and the full text of
whichever row the deduplication kept. For every pair in
data/document_relations_variants.json this script
  * turns the existing document (identifier = the designation, so every
    relation, process link and review item that points at it stays valid) into
    the Czech variant: title, description, language, address, file path ... are
    resolved again from the Czech record;
  * inserts the English variant as a new document with the identifier
    `<designation> [EN]` (keywords and versions copied from the Czech one) and
    a slug of its own;
  * adds the `TRANSLATION_OF` relation (English -> Czech), after extending the
    enum of `document_relation.relation_type` when the column does not know it yet.
Idempotent: a pair that is already split is only brought up to date. Dry run
unless --apply; take a backup of the database first (mariadb-dump into backups/).

Usage: .venv/bin/python src/tools/backfill_language_variants.py [--apply] [--env-file FILE]
"""
import argparse
import json
import pathlib

import pymysql

import init_db
import language_variants as lv
import slug as slug_module
from puvodce import load_eu_gestor_cache

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
DEDUPLICATED_PATH = REPO_ROOT / "data" / "database_merged_deduplicated.json"
RELATIONS_PATH = REPO_ROOT / "data" / "document_relations_variants.json"

# the columns resolved from a record (everything but id, identifier and slug)
UPDATED_COLUMNS = ("title", "description", "type_id", "source_id", "language", "url", "effective_date",
                   "jurisdikce", "file_path", "needs_review", "review_reason", "zdroj_dat",
                   "nazev_autoritativni", "popis_autoritativni", "zdroj_autoritativni_url",
                   "jurisdikce_puvodni", "popis_priblizny")


def load(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def column_values(prepared, item):
    """The values of UPDATED_COLUMNS for a record resolved by init_db.prepare_document()."""
    values = dict(prepared)
    values.update({"zdroj_dat": item.get("zdroj_dat") or None,
                   "nazev_autoritativni": item.get("nazev_autoritativni") or None,
                   "popis_autoritativni": item.get("popis_autoritativni") or None,
                   "zdroj_autoritativni_url": item.get("zdroj_autoritativni_url") or None,
                   "jurisdikce_puvodni": item.get("jurisdikce_puvodni") or None,
                   "popis_priblizny": item.get("popis_priblizny") or None})
    return [values[column] for column in UPDATED_COLUMNS]


def ensure_relation_type(cursor):
    """Adds TRANSLATION_OF to the relation_type enum when it is missing."""
    cursor.execute("SELECT COLUMN_TYPE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() "
                   "AND TABLE_NAME = 'document_relation' AND COLUMN_NAME = 'relation_type'")
    column_type = cursor.fetchone()[0]
    if lv.RELATION_TYPE in column_type:
        return False
    members = column_type[len("enum("):-1] + f",'{lv.RELATION_TYPE}'"
    cursor.execute(f"ALTER TABLE document_relation MODIFY COLUMN relation_type ENUM({members}) NOT NULL")
    return True


def plan(cursor, records, relations):
    """[(czech item, english item, czech id or None, english id or None)]."""
    by_designation = {(record.get("znacka") or "").strip(): record for record in records}
    cursor.execute("SELECT identifier, id FROM Document WHERE identifier IS NOT NULL")
    ids = dict(cursor.fetchall())
    rows = []
    for relation in relations:
        english, czech = relation["from_identifier"], relation["to_identifier"]
        rows.append((by_designation[czech], by_designation[english], ids.get(czech), ids.get(english)))
    return rows


def apply_pair(cursor, czech_item, english_item, czech_id, english_id, context):
    """Updates the Czech variant and inserts or updates the English one; returns the English id."""
    cursor.execute("SELECT identifier FROM Document WHERE identifier IS NOT NULL")
    taken = {row[0] for row in cursor.fetchall()}
    for item, doc_id in ((czech_item, czech_id), (english_item, english_id)):
        own = (item["znacka"] or "").strip()
        seen = taken - {own} if doc_id else taken
        prepared = init_db.prepare_document(cursor, item, seen, context["gestor_map"], context["gestor_cache"],
                                            context["manifest"])
        values = column_values(prepared, item)
        if doc_id:
            assignments = ", ".join(f"{column} = %s" for column in UPDATED_COLUMNS)
            cursor.execute(f"UPDATE Document SET {assignments} WHERE id = %s", values + [doc_id])
        else:
            columns = ", ".join(UPDATED_COLUMNS + ("identifier",))
            marks = ", ".join(["%s"] * (len(UPDATED_COLUMNS) + 1))
            cursor.execute(f"INSERT INTO Document ({columns}) VALUES ({marks})", values + [prepared["identifier"]])
            english_id = cursor.lastrowid
            cursor.execute("INSERT INTO DocumentKeyword (document_id, keyword_id) "
                           "SELECT %s, keyword_id FROM DocumentKeyword WHERE document_id = %s", (english_id, czech_id))
            cursor.execute("INSERT INTO DocumentVersion (document_id, version, edition_label, effective_date, "
                           "is_current, lifecycle_state) SELECT %s, version, edition_label, effective_date, "
                           "is_current, lifecycle_state FROM DocumentVersion WHERE document_id = %s",
                           (english_id, czech_id))
    return english_id


def assign_new_slugs(cursor):
    """Gives the documents without a slug the one slug.assign_slugs() gives them in
    the context of the whole corpus; the slugs already assigned stay as they are."""
    cursor.execute("SELECT id, identifier, title, slug FROM Document")
    documents = cursor.fetchall()
    wanted = slug_module.assign_slugs((doc_id, identifier, title) for doc_id, identifier, title, _ in documents)
    changed = [(wanted[doc_id], doc_id) for doc_id, _, _, current in documents if not current]
    for slug, doc_id in changed:
        cursor.execute("UPDATE Document SET slug = %s WHERE id = %s", (slug, doc_id))
    return len(changed)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--apply", action="store_true", help="change the database (dry run without it)")
    parser.add_argument("--env-file", default=None, help="database account (default: .env, from this tree or the main one)")
    args = parser.parse_args(argv)
    from dotenv import dotenv_values
    import testdb
    env = dotenv_values(args.env_file or str(testdb.find_env_file(".env")))
    conn = pymysql.connect(host=env["DB_HOST"], port=int(env.get("DB_PORT") or 3306), user=env["DB_USER"],
                           password=env["DB_PASSWORD"], database=env["DB_NAME"])
    try:
        records, relations = load(DEDUPLICATED_PATH), load(RELATIONS_PATH)
        cursor = conn.cursor()
        rows = plan(cursor, records, relations)
        for czech, english, czech_id, english_id in rows:
            state = "new" if english_id is None else "update"
            print(f"{czech['znacka']}: Czech #{czech_id}, English {state}"
                  + (f" #{english_id}" if english_id else ""))
        missing = [czech["znacka"] for czech, _, czech_id, _ in rows if czech_id is None]
        if missing:
            print(f"no document with these identifiers, skipped: {missing}")
        if args.apply:
            context = {"gestor_map": init_db.build_gestor_jurisdiction_map(records),
                       "gestor_cache": load_eu_gestor_cache(REPO_ROOT),
                       "manifest": init_db.load_fulltext_manifest()}
            if ensure_relation_type(cursor):
                print(f"relation_type enum extended with {lv.RELATION_TYPE}")
            for czech, english, czech_id, english_id in rows:
                if czech_id is None:
                    continue
                english_id = apply_pair(cursor, czech, english, czech_id, english_id, context)
                cursor.execute("INSERT INTO document_relation (from_document_id, to_document_id, relation_type, note) "
                               "SELECT %s, %s, %s, %s FROM DUAL WHERE NOT EXISTS (SELECT 1 FROM document_relation "
                               "WHERE from_document_id = %s AND to_document_id = %s AND relation_type = %s)",
                               (english_id, czech_id, lv.RELATION_TYPE, "Anglická a česká jazyková verze téhož aktu.",
                                english_id, czech_id, lv.RELATION_TYPE))
            print(f"{assign_new_slugs(cursor)} slugs assigned")
            conn.commit()
        print(f"{len(rows)} pairs " + ("processed in " + env["DB_NAME"] if args.apply else "(dry run — add --apply)"))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
