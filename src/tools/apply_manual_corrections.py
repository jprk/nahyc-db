"""Applies data/manual_corrections.json to the live database (doc/MPO_PRIPOMINKY.md,
krok 0).

A correction in that file is applied by build_unified_db.py on every rebuild; the
admin app (app/admin.py) writes the ones editors confirm and changes the live row
itself. Corrections added to the file by hand reach the live database through this
script, which resolves the corrected record exactly as a rebuild does
(init_db.prepare_document()) and updates the columns the correction affects:

* `nazev_*`, `nazev_autoritativni` → title; `anotace_poznamka`,
  `popis_autoritativni` → description; `typ_dokumentu` → type (and the source,
  which depends on it); `gestor` → source; `odkaz_*` → url and full-text file (the
  manifest files a text under the address it came from, so a new address has none
  until fetch_fulltext.py fetches it); `zdroj_autoritativni_url` → url; `jazyk` → language; `jurisdikce`; `znacka` → identifier; the review flags
  are recomputed in every case;
* `"exclude": true` deletes the document and its English variant (`<znacka> [EN]`,
  doc/PLAN.md §47) with their keywords and versions; relations go with them
  (ON DELETE CASCADE), and so do its links to process nodes (`node_document`,
  which load_process_layer.py derives from citations — a rebuild would not link a
  document that is not there). A document a scenario or an activation rule refers
  to is not deleted.

A correction is keyed by the record's `znacka`, or by `url-<hash>` of its main address
when it has none (build_unified_db.correction_key()). The live document is found by
its identifier (the key, or the corrected `znacka`), or by the address the record
resolves to. Idempotent. Dry run unless --apply; back up the database first.

Usage: .venv/bin/python src/tools/apply_manual_corrections.py [--apply] [--only KEY] [--env-file FILE]
"""
import argparse
import json
import pathlib

import pymysql

import init_db
from build_unified_db import (MANUAL_CORRECTIONS_PATH, apply_manual_corrections, correction_key,
                              load_manual_corrections)
from fulltext_keys import URL_DESIGNATION_PREFIX, first_url, url_designation
from puvodce import load_eu_gestor_cache

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
RECORDS_PATH = REPO_ROOT / "data" / "database_merged_deduplicated.json"
EN_SUFFIX = " [EN]"

# Which live columns a corrected record field affects.
COLUMNS_BY_FIELD = {
    "nazev_cz": ("title",), "nazev_sk": ("title",), "nazev_eu": ("title",), "nazev_autoritativni": ("title",),
    "anotace_poznamka": ("description",), "popis_autoritativni": ("description",),
    "typ_dokumentu": ("type_id", "source_id"), "gestor": ("source_id",),
    "odkaz_hlavni": ("url", "file_path"), "odkaz_eu": ("url", "file_path"), "odkaz_sk": ("url", "file_path"),
    "zdroj_autoritativni_url": ("url",),
    "jazyk": ("language",), "jurisdikce": ("jurisdikce",), "znacka": ("identifier",),
}
# Process-layer tables whose rows must not lose their document.
PROTECTED_REFERENCES = (("scenario_document", "document_id"), ("node_activation_rule", "basis_document_id"))


def affected_columns(changes):
    columns = []
    for field in changes:
        for column in COLUMNS_BY_FIELD.get(field, ()):
            if column not in columns:
                columns.append(column)
    return columns + ["needs_review", "review_reason"]


def records_by_key(records):
    """{correction key: [records]} — several records can share one znacka (the two
    spreadsheet rows of a language pair before split_language_variants.py)."""
    found = {}
    for record in records:
        key = correction_key(record)
        if key:
            found.setdefault(key, []).append(record)
    return found


def find_documents(cursor, key, entry, record):
    """Ids of the live documents a correction is about."""
    identifiers = [key]
    new_znacka = (entry.get("changes") or {}).get("znacka")
    if new_znacka:
        identifiers.append(new_znacka)
    if entry.get("exclude"):
        identifiers += [i + EN_SUFFIX for i in identifiers]
    marks = ", ".join(["%s"] * len(identifiers))
    cursor.execute(f"SELECT id FROM Document WHERE identifier IN ({marks}) ORDER BY id", identifiers)
    ids = [row[0] for row in cursor.fetchall()]
    if ids or not key.startswith(URL_DESIGNATION_PREFIX):
        return ids
    # A record without znacka: the live document has the address the key was made
    # of (before the correction), or the one the record resolves to (after it).
    resolved = init_db.resolve_url(record) if record else ""
    cursor.execute("SELECT id, url FROM Document WHERE identifier IS NULL ORDER BY id")
    return [doc_id for doc_id, url in cursor.fetchall()
            if url and (url == resolved or url_designation(first_url(url)) == key)]


def blocking_references(cursor, doc_id):
    """The process-layer tables that refer to a document and prevent its deletion."""
    blockers = []
    for table, column in PROTECTED_REFERENCES:
        cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE {column} = %s", (doc_id,))
        if cursor.fetchone()[0]:
            blockers.append(table)
    return blockers


def node_links(cursor, doc_id):
    cursor.execute("SELECT node_id, link_type FROM node_document WHERE document_id = %s ORDER BY node_id", (doc_id,))
    return [f"{node} {link}" for node, link in cursor.fetchall()]


def delete_document(cursor, doc_id):
    """Deletes a document with its keywords, versions and process-node links."""
    cursor.execute("DELETE FROM node_document WHERE document_id = %s", (doc_id,))
    cursor.execute("DELETE FROM DocumentKeyword WHERE document_id = %s", (doc_id,))
    cursor.execute("DELETE FROM DocumentVersion WHERE document_id = %s", (doc_id,))
    cursor.execute("DELETE FROM Document WHERE id = %s", (doc_id,))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--apply", action="store_true", help="change the database (dry run without it)")
    parser.add_argument("--only", action="append", default=None, metavar="KEY",
                        help="apply only this correction (repeatable)")
    parser.add_argument("--env-file", default=None)
    args = parser.parse_args(argv)
    from dotenv import dotenv_values
    import testdb
    env = dotenv_values(args.env_file or str(testdb.find_env_file(".env")))
    corrections = load_manual_corrections()
    records = json.loads(RECORDS_PATH.read_text(encoding="utf-8"))
    by_key = records_by_key(records)
    corrected = []
    for record in records:
        record = dict(record)
        if apply_manual_corrections(record, corrections):
            corrected.append(record)
    gestor_map = init_db.build_gestor_jurisdiction_map(corrected)
    gestor_cache = load_eu_gestor_cache(REPO_ROOT)
    manifest = init_db.load_fulltext_manifest()
    conn = pymysql.connect(host=env["DB_HOST"], port=int(env.get("DB_PORT") or 3306), user=env["DB_USER"],
                           password=env["DB_PASSWORD"], database=env["DB_NAME"], charset="utf8mb4")
    changed = deleted = 0
    try:
        cur = conn.cursor()
        for key, entry in corrections.items():
            if args.only and key not in args.only:
                continue
            candidates = by_key.get(key) or by_key.get((entry.get("changes") or {}).get("znacka") or "") or [None]
            record = candidates[0]
            ids = find_documents(cur, key, entry, record)
            if not ids:
                print(f"{key}: no live document found — skipped")
                continue
            if entry.get("exclude"):
                for doc_id in ids:
                    blockers = blocking_references(cur, doc_id)
                    if blockers:
                        print(f"{key}: document {doc_id} NOT deleted, referenced by {', '.join(blockers)}")
                        continue
                    links = node_links(cur, doc_id)
                    delete_document(cur, doc_id)
                    print(f"{key}: document {doc_id} {'deleted' if args.apply else 'to delete'} (out of scope)"
                          + (f", with its process-node links: {', '.join(links)}" if links else ""))
                    deleted += 1
                continue
            if record is None:
                print(f"{key}: no record in {RECORDS_PATH.name} — skipped")
                continue
            item = dict(record)
            apply_manual_corrections(item, {key: entry})
            for doc_id in ids:
                cur.execute("SELECT identifier FROM Document WHERE identifier IS NOT NULL AND id <> %s", (doc_id,))
                seen = {row[0] for row in cur.fetchall()}
                prepared = init_db.prepare_document(cur, item, seen, gestor_map, gestor_cache, manifest)
                columns = affected_columns(entry.get("changes", {}))
                cur.execute(f"SELECT {', '.join(columns)} FROM Document WHERE id = %s", (doc_id,))
                old = dict(zip(columns, cur.fetchone()))
                new = {c: prepared[c] for c in columns}
                diff = {c: (old[c], new[c]) for c in columns if old[c] != new[c]
                        and not (c == "needs_review" and bool(old[c]) == bool(new[c]))}
                if not diff:
                    print(f"{key}: document {doc_id} already corrected")
                    continue
                for column, (before, after) in diff.items():
                    print(f"{key}: document {doc_id} {column}: {str(before)[:70]!r} -> {str(after)[:70]!r}")
                cur.execute(f"UPDATE Document SET {', '.join(c + ' = %s' for c in diff)} WHERE id = %s",
                            [new[c] for c in diff] + [doc_id])
                changed += 1
        if args.apply:
            conn.commit()
        else:
            conn.rollback()
        print(f"{changed} documents corrected, {deleted} deleted "
              + (f"in {env['DB_NAME']}" if args.apply else "(dry run — add --apply)")
              + f"; corrections from {MANUAL_CORRECTIONS_PATH.relative_to(REPO_ROOT)}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
