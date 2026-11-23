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
  until fetch_fulltext.py fetches it); `zdroj_autoritativni_url` → url; `jazyk` →
  language; `jurisdikce`; `platnost` → effective date; `znacka` → identifier,
  title (a standard's title begins with its designation) and full-text file (and
  the slug a rebuild would give the document, unless another document has it,
  or the slug the correction pins, `slug`: a standard renamed on switching to a
  new edition keeps its permanent address, norm_editions.py);
  the `*_autoritativni` fields also go to their own columns, which a rebuild
  copies verbatim; the review flags are recomputed in every case;
* `"exclude": true` deletes the document and its English variant (`<znacka> [EN]`,
  doc/PLAN.md §47) with their keywords and versions; relations go with them
  (ON DELETE CASCADE), and so do its links to process nodes (`node_document`,
  which load_process_layer.py derives from citations — a rebuild would not link a
  document that is not there). A document a scenario or an activation rule refers
  to is not deleted;
* `"merged_into": "<znacka>"` deletes the document as a duplicate of the
  document with that identifier and moves its relations, process-node and
  scenario links, keywords, activation rules, review items and candidates to it
  (a link the survivor already has, or a relation between the two, is dropped);
  its versions are deleted with it.

A correction is keyed by the record's `znacka` (`"<znacka> @<zdroj_dat>"` for the record of one
source when two sources list a standard under one znacka), or by `url-<hash>` of its main address
when it has none, or by `title-<hash>` of its title when it has neither
(build_unified_db.correction_key()). The live document is found by its identifier
(the key, or the corrected `znacka`), or by the address the record resolves to, or
by its title. Idempotent. Dry run unless --apply; back up the database first.

Usage: .venv/bin/python src/tools/apply_manual_corrections.py [--apply] [--only KEY] [--env-file FILE]
"""
import argparse
import json
import pathlib

import pymysql

import init_db
from build_unified_db import (MANUAL_CORRECTIONS_PATH, SOURCE_SEPARATOR, apply_manual_corrections, correction_key,
                              load_manual_corrections, source_qualified_key)
from fulltext_keys import (TITLE_DESIGNATION_PREFIX, URL_DESIGNATION_PREFIX, first_url, title_designation,
                           url_designation)
from puvodce import load_eu_gestor_cache
from slug import assign_slugs

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
RECORDS_PATH = REPO_ROOT / "data" / "database_merged_deduplicated.json"
EN_SUFFIX = " [EN]"

# Which live columns a corrected record field affects.
COLUMNS_BY_FIELD = {
    "nazev_cz": ("title",), "nazev_sk": ("title",), "nazev_eu": ("title",), "nazev_autoritativni": ("title",),
    "anotace_poznamka": ("description",), "popis_autoritativni": ("description",),
    "typ_dokumentu": ("type_id", "source_id"), "gestor": ("source_id",),
    "odkaz_hlavni": ("url", "file_path"), "odkaz_eu": ("url", "file_path"), "odkaz_sk": ("url", "file_path"),
    "zdroj_autoritativni_url": ("url", "zdroj_autoritativni_url"),
    "jazyk": ("language",), "jurisdikce": ("jurisdikce",),
    # the full-text manifest files a text under the designation, too
    # and the title of a standard begins with it (init_db.format_norm_title)
    "znacka": ("identifier", "title", "file_path"),
    # a slug pinned by the correction (norm_editions.py: a renamed standard keeps its address)
    "slug": ("slug",),
    "platnost": ("effective_date",),
}
# Columns init_db.py copies from the record verbatim (prepare_document() does not resolve them).
PASS_THROUGH_COLUMNS = ("nazev_autoritativni", "popis_autoritativni", "zdroj_autoritativni_url")
for _column in ("nazev_autoritativni", "popis_autoritativni"):
    COLUMNS_BY_FIELD[_column] = COLUMNS_BY_FIELD[_column] + (_column,)
# Process-layer tables whose rows must not lose their document.
PROTECTED_REFERENCES = (("scenario_document", "document_id"), ("node_activation_rule", "basis_document_id"))


def affected_columns(changes):
    columns = []
    for field in changes:
        for column in COLUMNS_BY_FIELD.get(field, ()):
            if column not in columns:
                columns.append(column)
    return columns + ["needs_review", "review_reason"]


def corrected_item(record, key, entry):
    """The record with the correction applied. The committed outputs may already
    carry the corrected znacka, so the record was found by it and its own key no
    longer matches `key`; the changes are then applied directly (idempotent), or a
    pinned slug and other fields added to the correction later would be lost."""
    item = dict(record)
    apply_manual_corrections(item, {key: entry})
    item.update(entry.get("changes", {}))
    return item


def records_by_key(records):
    """{correction key: [records]} — several records can share one znacka (the two
    spreadsheet rows of a language pair before split_language_variants.py)."""
    found = {}
    for record in records:
        key = correction_key(record)
        if key:
            found.setdefault(key, []).append(record)
            qualified = source_qualified_key(key, record)
            if qualified:
                found.setdefault(qualified, []).append(record)
    return found


def find_documents(cursor, key, entry, record):
    """Ids of the live documents a correction is about."""
    if SOURCE_SEPARATOR in key:
        # the record of one source among records sharing a znacka: the rebuild left
        # it without an identifier, so it is found by its title
        title = " ".join((init_db.resolve_title(record) or "").split()) if record else ""
        cursor.execute("SELECT id, title FROM Document WHERE identifier IS NULL ORDER BY id")
        return [doc_id for doc_id, t in cursor.fetchall() if title and " ".join((t or "").split()) == title]
    identifiers = [key]
    new_znacka = (entry.get("changes") or {}).get("znacka")
    if new_znacka:
        identifiers.append(new_znacka)
    if entry.get("exclude"):
        identifiers += [i + EN_SUFFIX for i in identifiers]
    marks = ", ".join(["%s"] * len(identifiers))
    cursor.execute(f"SELECT id FROM Document WHERE identifier IN ({marks}) ORDER BY id", identifiers)
    ids = [row[0] for row in cursor.fetchall()]
    if ids:
        return ids
    if key.startswith(TITLE_DESIGNATION_PREFIX):
        # A record with neither znacka nor address: the live document has its title.
        cursor.execute("SELECT id, title FROM Document WHERE identifier IS NULL ORDER BY id")
        return [doc_id for doc_id, title in cursor.fetchall() if title_designation(title) == key]
    if not key.startswith(URL_DESIGNATION_PREFIX):
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


# Tables whose rows move to the surviving document of a merge: (table, column,
# whether a row the survivor already has makes it a duplicate to drop).
MERGED_LINKS = (("document_relation", "from_document_id", True), ("document_relation", "to_document_id", True),
                ("node_document", "document_id", True), ("scenario_document", "document_id", True),
                ("DocumentKeyword", "document_id", True), ("node_activation_rule", "basis_document_id", False),
                ("ReviewItem", "document_id", False), ("DocumentCandidate", "document_id", False))


def find_survivor(cursor, identifier):
    cursor.execute("SELECT id FROM Document WHERE identifier = %s", (identifier,))
    row = cursor.fetchone()
    return row[0] if row else None


def merge_document(cursor, doc_id, survivor_id):
    """Moves every link of document `doc_id` to `survivor_id` and deletes it.
    Returns {table: rows moved}. A link the survivor already has is dropped
    (UPDATE IGNORE leaves it behind, the DELETE removes it); so is a relation
    between the two documents, which would become a relation of the survivor with
    itself."""
    cursor.execute("DELETE FROM document_relation WHERE (from_document_id = %s AND to_document_id = %s) "
                   "OR (from_document_id = %s AND to_document_id = %s)", (doc_id, survivor_id, survivor_id, doc_id))
    moved = {}
    for table, column, unique in MERGED_LINKS:
        cursor.execute(f"UPDATE {'IGNORE ' if unique else ''}{table} SET {column} = %s WHERE {column} = %s",
                       (survivor_id, doc_id))
        if cursor.rowcount:
            moved[table] = moved.get(table, 0) + cursor.rowcount
        if unique:
            cursor.execute(f"DELETE FROM {table} WHERE {column} = %s", (doc_id,))
    cursor.execute("DELETE FROM DocumentVersion WHERE document_id = %s", (doc_id,))
    cursor.execute("DELETE FROM Document WHERE id = %s", (doc_id,))
    return moved


def wanted_slug(cursor, doc_id, identifier, title):
    """The slug slug.assign_slugs() gives the document with this identifier and
    title in the context of the whole corpus, or None when another document has it."""
    cursor.execute("SELECT id, identifier, title, slug FROM Document")
    documents = [(i, identifier if i == doc_id else ident, title if i == doc_id else t, s)
                 for i, ident, t, s in cursor.fetchall()]
    slug = assign_slugs((i, ident, t) for i, ident, t, _ in documents).get(doc_id)
    taken = {s for i, _, _, s in documents if i != doc_id}
    return slug if slug and slug not in taken else None


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
            if entry.get("merged_into"):
                survivor_id = find_survivor(cur, entry["merged_into"])
                for doc_id in ids:
                    if survivor_id is None or survivor_id == doc_id:
                        print(f"{key}: document {doc_id} NOT merged, no other document {entry['merged_into']!r}")
                        continue
                    moved = merge_document(cur, doc_id, survivor_id)
                    print(f"{key}: document {doc_id} {'merged' if args.apply else 'to merge'} into {survivor_id} "
                          f"({entry['merged_into']})"
                          + (", moved: " + ", ".join(f"{t} {n}" for t, n in moved.items()) if moved else ""))
                    deleted += 1
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
            item = corrected_item(record, key, entry)
            for doc_id in ids:
                cur.execute("SELECT identifier FROM Document WHERE identifier IS NOT NULL AND id <> %s", (doc_id,))
                seen = {row[0] for row in cur.fetchall()}
                prepared = init_db.prepare_document(cur, item, seen, gestor_map, gestor_cache, manifest)
                prepared.update({column: item.get(column) or None for column in PASS_THROUGH_COLUMNS})
                columns = affected_columns(entry.get("changes", {}))
                if item.get("slug"):
                    prepared["slug"] = item["slug"]
                elif "identifier" in columns:
                    columns.append("slug")
                    prepared["slug"] = wanted_slug(cur, doc_id, prepared["identifier"], prepared["title"])
                cur.execute(f"SELECT {', '.join(columns)} FROM Document WHERE id = %s", (doc_id,))
                old = dict(zip(columns, cur.fetchone()))
                new = {c: prepared[c] for c in columns}
                diff = {c: (old[c], new[c]) for c in columns if old[c] != new[c]
                        and not (c == "needs_review" and bool(old[c]) == bool(new[c]))
                        and not (c == "slug" and new[c] is None)}
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
        print(f"{changed} documents corrected, {deleted} deleted or merged "
              + (f"in {env['DB_NAME']}" if args.apply else "(dry run — add --apply)")
              + f"; corrections from {MANUAL_CORRECTIONS_PATH.relative_to(REPO_ROOT)}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
