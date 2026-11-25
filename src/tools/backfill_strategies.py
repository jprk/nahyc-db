"""Brings the live database up to the data fixes of doc/MPO_PRIPOMINKY.md,
krok 1 (strategies and language variants, 2026-11-19), in the parts that
apply_manual_corrections.py cannot do because they are not a change of one
document's columns:

1. **Type rename.** `DocumentType` „Strategický dokument“ is renamed
   „Strategie“ (MPO comment 9). When a type „Strategie“ already exists (an
   earlier apply_manual_corrections.py run creates it for a corrected record),
   its documents move to the renamed type and the duplicate row is deleted.
   Candidates (`DocumentCandidate.document_type`) follow.
2. **New documents.** The strategies of data/strategy_documents.json and the
   EIGA publication split from the UN Regulation No 100 record
   (`NEW_DESIGNATIONS`), taken from data/database_merged_deduplicated.json,
   are inserted the way init_db.py inserts a record (prepare_document(),
   versions, keywords, provenance, slug) when no live document has their
   identifier (or, without one, their address).
3. **Relations.** The `TRANSLATION_OF` relations of the Slovak variants
   (`… [SK]`, data/document_relations_variants.json) and the relations of
   data/document_relations.json that name a document of this step
   (`RELATION_NAMES`: the supersession of the National Action Plan for Clean
   Mobility) are added when missing. Ends are resolved the way
   load_document_relations.py resolves them (identifier, or `url-<hash>` of the
   address of a document without one).
4. **States.** A correction of data/manual_corrections.json with
   `stav_dokumentu` (here: the superseded 2019 plan and its annex) sets the
   state of the document's current version. So does `stav_dokumentu` of a
   record of this step: the unapproved updates of the Climate Protection Policy
   (2025–2050) and of the State Energy Concept are prepared documents (`draft`,
   doc/MPO_PRIPOMINKY.md, odstavec 5), joined by `REPEALS` to the strategy each
   is to replace (data/document_relations.json; the document page reads it
   „má nahradit“ while the update is a draft).

Step 2 (2026-11-20) adds to data/strategy_documents.json the five strategies
of priority C and the two prepared updates; the same run inserts them.

Run it after apply_manual_corrections.py (the Slovak variants get their
`… [SK]` identifiers there). Idempotent; dry run unless --apply; back up the
database first (src/tools/backup_db.py).

Usage: .venv/bin/python src/tools/backfill_strategies.py [--apply] [--env-file FILE]
"""
import argparse
import json
import pathlib

import pymysql

import init_db
import language_variants as lv
import load_document_relations as ldr
from apply_manual_corrections import find_documents, records_by_key
from build_unified_db import apply_manual_corrections, load_manual_corrections
from backfill_language_variants import assign_new_slugs
from puvodce import load_eu_gestor_cache

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
DEDUPLICATED_PATH = REPO_ROOT / "data" / "database_merged_deduplicated.json"
STRATEGY_SOURCE = "Strategy_Research"  # zdroj_dat of data/strategy_documents.json
OLD_TYPE, NEW_TYPE = "Strategický dokument", "Strategie"
# Documents of this step that are not strategies.
NEW_DESIGNATIONS = ("EIGA IGC Doc 100/20",)
# The documents data/document_relations.json names in relations of this step.
RELATION_NAMES = ("url-7ee3a2b4", "url-95efd271")  # Aktualizace NAP CM (2019) and its annex


def load(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def rename_type(cursor):
    """Renames OLD_TYPE to NEW_TYPE; returns a description of what changed, or None."""
    cursor.execute("SELECT name, id FROM DocumentType WHERE name IN (%s, %s)", (OLD_TYPE, NEW_TYPE))
    ids = dict(cursor.fetchall())
    old_id, new_id = ids.get(OLD_TYPE), ids.get(NEW_TYPE)
    if old_id is None:
        return None
    done = []
    if new_id is not None:
        moved = cursor.execute("UPDATE Document SET type_id = %s WHERE type_id = %s", (old_id, new_id))
        cursor.execute("DELETE FROM DocumentType WHERE id = %s", (new_id,))
        done.append(f"{moved} documents moved from the duplicate type #{new_id}")
    cursor.execute("UPDATE DocumentType SET name = %s WHERE id = %s", (NEW_TYPE, old_id))
    candidates = cursor.execute("UPDATE DocumentCandidate SET document_type = %s WHERE document_type = %s",
                                (NEW_TYPE, OLD_TYPE))
    done.append(f"{candidates} candidates")
    return f"type #{old_id} {OLD_TYPE!r} -> {NEW_TYPE!r} (" + ", ".join(done) + ")"


def new_records(records):
    """The records this step adds to the database."""
    return [r for r in records if r.get("zdroj_dat") == STRATEGY_SOURCE
            or (r.get("znacka") or "").strip() in NEW_DESIGNATIONS]


def live_names(cursor):
    """{name: id} as load_document_relations.py resolves relation ends."""
    return ldr.fetch_document_identifier_map(cursor)


def record_name(record):
    """The name a record has in the relation files: its znacka, or `url-<hash>` of its address."""
    from fulltext_keys import first_url, url_designation
    znacka = (record.get("znacka") or "").strip()
    if znacka:
        return znacka
    url = first_url(init_db.resolve_url(record))
    return url_designation(url) if url else None


def insert_document(cursor, item, context):
    """Inserts `item` as init_db.import_json_data() does; returns its id."""
    cursor.execute("SELECT identifier FROM Document WHERE identifier IS NOT NULL")
    seen = {row[0] for row in cursor.fetchall()}
    prepared = init_db.prepare_document(cursor, item, seen, context["gestor_map"], context["gestor_cache"],
                                        context["manifest"])
    columns = {"title": prepared["title"], "description": prepared["description"], "type_id": prepared["type_id"],
               "source_id": prepared["source_id"], "language": prepared["language"], "url": prepared["url"],
               "effective_date": prepared["effective_date"], "identifier": prepared["identifier"],
               "jurisdikce": prepared["jurisdikce"], "file_path": prepared["file_path"],
               "needs_review": prepared["needs_review"], "review_reason": prepared["review_reason"],
               "zdroj_dat": item.get("zdroj_dat") or None,
               "nazev_autoritativni": item.get("nazev_autoritativni") or None,
               "popis_autoritativni": item.get("popis_autoritativni") or None,
               "zdroj_autoritativni_url": item.get("zdroj_autoritativni_url") or None,
               "jurisdikce_puvodni": item.get("jurisdikce_puvodni") or None,
               "popis_priblizny": item.get("popis_priblizny") or None,
               "provenance": (item.get("provenance") or "").strip() or None}
    cursor.execute(f"INSERT INTO Document ({', '.join(columns)}) VALUES ({', '.join(['%s'] * len(columns))})",
                   list(columns.values()))
    doc_id = cursor.lastrowid
    for v in init_db.resolve_document_versions(item):
        state = v["lifecycle_state"]
        if v["is_current"] and (item.get("stav_dokumentu") or "") in ("superseded", "draft"):
            state = item["stav_dokumentu"]
        cursor.execute("INSERT INTO DocumentVersion (document_id, version, edition_label, effective_date, is_current, "
                       "lifecycle_state) VALUES (%s, %s, %s, %s, %s, %s)",
                       (doc_id, v["version"], v["edition_label"], v["effective_date"], v["is_current"], state))
    keywords = list(item.get("klicova_slova") or [])
    for extra in ((item.get("sekce") or "").strip(), (item.get("kategorie_trida") or "").strip()):
        if extra and extra not in keywords:
            keywords.append(extra)
    for keyword in keywords:
        if isinstance(keyword, str) and keyword.strip() and not init_db.is_status_keyword(keyword):
            category_id = init_db.get_or_create(cursor, "SourceCategory", {"name": keyword.strip()})
            cursor.execute("INSERT IGNORE INTO DocumentSourceCategory (document_id, category_id) VALUES (%s, %s)",
                           (doc_id, category_id))
    return doc_id


def wanted_relations(new_names):
    """The relations of this step, by name (load_document_relations.py shape)."""
    variants = [r for r in load(ldr.VARIANTS_RELATIONS_PATH) if r["from_identifier"].endswith(lv.SK_SUFFIX)]
    names = set(new_names) | set(RELATION_NAMES)
    curated = [r for r in load(ldr.RELATIONS_PATH)
               if r["from_identifier"] in names or r["to_identifier"] in names]
    return variants + curated


def add_relations(cursor, relations, apply):
    """Inserts the relations whose two ends exist and which are missing; returns
    (added, unresolved) lists of human-readable lines."""
    resolved, unresolved = ldr.resolve_relations(relations, live_names(cursor))
    added = []
    for rel in ldr.dedupe_resolved_relations(resolved):
        key = (rel["from_document_id"], rel["to_document_id"], rel["relation_type"])
        cursor.execute("SELECT 1 FROM document_relation WHERE from_document_id = %s AND to_document_id = %s "
                       "AND relation_type = %s", key)
        if cursor.fetchone():
            continue
        if apply:
            cursor.execute("INSERT INTO document_relation (from_document_id, to_document_id, relation_type, note) "
                           "VALUES (%s, %s, %s, %s)", key + (rel.get("note") or None,))
        added.append(f"{rel['from_identifier']} (#{key[0]}) {key[2]} {rel['to_identifier']} (#{key[1]})")
    return added, [f"{r['from_identifier']} {r['relation_type']} {r['to_identifier']}: {'; '.join(r['_problems'])}"
                   for r in unresolved]


def set_states(cursor, corrections, records):
    """[(key, document id, old state, new state)] for the corrections with `stav_dokumentu`."""
    by_key = records_by_key(records)
    changes = []
    for key, entry in corrections.items():
        state = (entry.get("changes") or {}).get("stav_dokumentu")
        if not state:
            continue
        record = (by_key.get(key) or [None])[0]
        for doc_id in find_documents(cursor, key, entry, record):
            cursor.execute("SELECT id, lifecycle_state FROM DocumentVersion WHERE document_id = %s AND is_current = 1",
                           (doc_id,))
            for version_id, current in cursor.fetchall():
                if current != state:
                    cursor.execute("UPDATE DocumentVersion SET lifecycle_state = %s WHERE id = %s", (state, version_id))
                    changes.append((key, doc_id, current, state))
    return changes


def record_states(cursor, records, names):
    """[(name, document id, old state, new state)] for the records of this step
    with `stav_dokumentu` whose document's current version has another state
    (a document inserted by an earlier run, or by a rebuild before the state
    was set). `names` is {name: document id} after the insertions."""
    changes = []
    for item in records:
        state = (item.get("stav_dokumentu") or "").strip()
        doc_id = names.get(record_name(item))
        if not state or doc_id is None:
            continue
        cursor.execute("SELECT id, lifecycle_state FROM DocumentVersion WHERE document_id = %s AND is_current = 1",
                       (doc_id,))
        for version_id, current in cursor.fetchall():
            if current != state:
                cursor.execute("UPDATE DocumentVersion SET lifecycle_state = %s WHERE id = %s", (state, version_id))
                changes.append((record_name(item), doc_id, current, state))
    return changes


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--apply", action="store_true", help="change the database (dry run without it)")
    parser.add_argument("--env-file", default=None, help="database account (default: .env, from this tree or the main one)")
    args = parser.parse_args(argv)
    from dotenv import dotenv_values
    import testdb
    env = dotenv_values(args.env_file or str(testdb.find_env_file(".env")))
    conn = pymysql.connect(host=env["DB_HOST"], port=int(env.get("DB_PORT") or 3306), user=env["DB_USER"],
                           password=env["DB_PASSWORD"], database=env["DB_NAME"], charset="utf8mb4")
    try:
        cursor = conn.cursor()
        corrections = load_manual_corrections()
        records = []
        for record in load(DEDUPLICATED_PATH):
            record = dict(record)
            if apply_manual_corrections(record, corrections):
                records.append(record)

        print(rename_type(cursor) or f"type {OLD_TYPE!r} not present (already renamed)")

        context = {"gestor_map": init_db.build_gestor_jurisdiction_map(records),
                   "gestor_cache": load_eu_gestor_cache(REPO_ROOT), "manifest": init_db.load_fulltext_manifest()}
        names = live_names(cursor)
        added_names = []
        for item in new_records(records):
            name = record_name(item)
            added_names.append(name)
            if name in names:
                print(f"document {name!r} already present (#{names[name]})")
                continue
            doc_id = insert_document(cursor, item, context)
            print(f"document {name!r} inserted as #{doc_id}: {init_db.resolve_title(item)[:80]!r}")
        slugs = assign_new_slugs(cursor)

        added, unresolved = add_relations(cursor, wanted_relations(added_names), True)
        for line in added:
            print(f"relation {line}")
        for line in unresolved:
            print(f"relation NOT resolved: {line}")

        for key, doc_id, before, after in set_states(cursor, corrections, load(DEDUPLICATED_PATH)):
            print(f"state {key} (#{doc_id}): {before} -> {after}")
        for name, doc_id, before, after in record_states(cursor, new_records(records), live_names(cursor)):
            print(f"state {name} (#{doc_id}): {before} -> {after}")

        if args.apply:
            conn.commit()
        else:
            conn.rollback()
        print(f"{slugs} slugs assigned, {len(added)} relations added "
              + (f"in {env['DB_NAME']}" if args.apply else "(dry run — add --apply)"))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
