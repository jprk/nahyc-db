"""Repairs `Document.file_path` values that point at a file which is no longer
on disk — e.g. after `fetch_fulltext.py --audit --apply` removed a stored
search-results page — by pointing the document at the file the manifest now
has for its designation (the same order `init_db.py` uses: `odkaz_hlavni`,
`odkaz_eu`, `odkaz_sk`), or clearing it when there is none, so that nothing
serves a missing file or a wrong one.

A document's own `file_path` is touched only when its file is missing; every
other document is left alone — unless `--fill` is given, which also sets a
`file_path` on documents that have none (a text downloaded after the database
was built; for those without a designation by their address, see
plan_unidentified), but never on a restricted type. Changes are applied in one transaction.

Usage:
    .venv/bin/python src/tools/sync_fulltext_paths.py            # dry run
    .venv/bin/python src/tools/sync_fulltext_paths.py --apply
    .venv/bin/python src/tools/sync_fulltext_paths.py --fill        # also documents with no file_path
"""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import fetch_fulltext as ff  # noqa: E402

REPO_ROOT = ff.REPO_ROOT
FIELD_PRIORITY = ("odkaz_hlavni", "odkaz_eu", "odkaz_sk")


def resolve_by_identifier(manifest, identifier, sources=None):
    """`local_path` of the best fetched manifest entry for this designation, or
    None. With `sources` (the document's own `zdroj_dat`), only entries of those
    spreadsheets/imports count: the same designation can name different
    documents in different sources (a Slovak notice numbered 2010/75 and the EU
    directive 2010/75/EU), and matching on the designation alone attached the
    directive's text to the notice."""
    identifier = (identifier or "").strip()
    for field in FIELD_PRIORITY:
        for key in sorted(manifest):
            source_znacka, _, key_field = key.rpartition("|")
            source, _, znacka = source_znacka.partition("|")
            if key_field != field or znacka != identifier:
                continue
            if sources is not None and source not in sources:
                continue
            entry = manifest[key]
            if entry.get("status") == "fetched" and entry.get("local_path"):
                return entry["local_path"]
    return None


def document_sources(zdroj_dat):
    """The sources a merged document came from (`"A, B"`), as a set."""
    return {part for part in (zdroj_dat or "").split(", ") if part}


def plan_changes(rows, manifest, repo_root=REPO_ROOT, fill=False):
    """[(document id, identifier, old path, new path or None)] for the rows
    `(id, identifier, file_path[, restricted[, zdroj_dat]])` — with `zdroj_dat`
    only manifest entries of the document's own sources are considered:
    - a `file_path` whose file is missing on disk is repointed at the
      manifest's best entry for the designation (or cleared);
    - with `fill`, a document with NO `file_path` gets the manifest's entry for
      its designation when that file exists — never for a restricted type
      (paid standards, R4.1), whatever the manifest says."""
    root = pathlib.Path(repo_root)
    changes = []
    for row in rows:
        doc_id, identifier, path = row[0], row[1], row[2]
        restricted = bool(row[3]) if len(row) > 3 else False
        sources = document_sources(row[4]) if len(row) > 4 and row[4] else None
        if path and not (root / path).is_file():
            changes.append((doc_id, identifier, path, resolve_by_identifier(manifest, identifier, sources)))
        elif fill and not path and not restricted:
            new = resolve_by_identifier(manifest, identifier, sources)
            if new and (root / new).is_file():
                changes.append((doc_id, identifier, None, new))
    return changes


def plan_unidentified(rows, items, manifest, repo_root=REPO_ROOT):
    """Changes for the documents that have no `identifier` (strategies, studies, acts listed
    by their address only, and a designation another document already holds) and no
    `file_path`. The manifest knows a record without a designation by its address
    (fulltext_keys.py), and the database holds nothing to compute that from, so each
    document is matched to its JSON record by slug (`doc-<hash of the title>`, what
    init_db gives a record without an identifier) and, where several records share
    the slug (placeholder titles), by address; the record then names the manifest
    entry the way init_db.resolve_file_path() does. Never a restricted type, never a
    guess between records that cannot be told apart.
    `rows` are `(id, identifier, file_path, restricted, zdroj_dat, slug, url)`, `items`
    the deduplicated records."""
    import init_db
    import slug as slug_module
    by_slug = {}
    for item in items:
        title = init_db.resolve_title(item)
        if title and not init_db.is_restricted_document_type(init_db.resolve_document_type(item.get("typ_dokumentu", ""))):
            by_slug.setdefault(slug_module.base_slug(None, title), []).append(item)
    root = pathlib.Path(repo_root)
    changes = []
    for doc_id, identifier, path, restricted, _sources, slug, url in rows:
        if identifier or path or restricted:
            continue
        base = slug.rsplit("-", 1)[0] if _is_suffixed(slug, by_slug) else slug
        candidates = by_slug.get(base, [])
        if len(candidates) > 1:
            candidates = [item for item in candidates if init_db.resolve_url(item) == (url or "")]
        if len(candidates) != 1:
            continue
        new = init_db.resolve_file_path(candidates[0], manifest)
        if new and (root / new).is_file():
            changes.append((doc_id, f"slug {slug}", None, new))
    return changes


def _is_suffixed(slug, by_slug):
    """A slug the collision handling gave a `-2`, `-3` ... suffix (slug.assign_slugs)."""
    return bool(slug) and slug not in by_slug and slug.rsplit("-", 1)[0] in by_slug


def apply_changes(conn, changes):
    with conn.cursor() as cur:
        for doc_id, _identifier, old, new in changes:
            # `<=>` is the NULL-safe equality: a filled document has no old path
            cur.execute("UPDATE Document SET file_path = %s WHERE id = %s AND file_path <=> %s", (new, doc_id, old))
    conn.commit()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--apply", action="store_true", help="change the database (dry run without it)")
    parser.add_argument("--fill", action="store_true",
                        help="also give a file_path to documents that have none, when the manifest has a "
                             "downloaded file for their designation (never for restricted types)")
    parser.add_argument("--env-file", default=None, help="database account (default: .env, from this tree or the main one)")
    args = parser.parse_args(argv)
    import pymysql
    from dotenv import dotenv_values
    import testdb
    env = dotenv_values(args.env_file or str(testdb.find_env_file(".env")))
    conn = pymysql.connect(host=env["DB_HOST"], port=int(env.get("DB_PORT") or 3306), user=env["DB_USER"],
                           password=env["DB_PASSWORD"], database=env["DB_NAME"])
    try:
        with conn.cursor() as cur:
            cur.execute("""SELECT d.id, d.identifier, d.file_path, dt.restricted_fulltext, d.zdroj_dat, d.slug, d.url
                           FROM Document d LEFT JOIN DocumentType dt ON dt.id = d.type_id""")
            rows = cur.fetchall()
        manifest = ff.load_manifest()
        changes = plan_changes([row[:5] for row in rows], manifest, fill=args.fill)
        if args.fill:
            records = json.loads((REPO_ROOT / "data" / "database_merged_deduplicated.json").read_text(encoding="utf-8"))
            changes += plan_unidentified(rows, records, manifest)
        for doc_id, identifier, old, new in changes:
            print(f"document {doc_id} ({identifier}): {old} -> {new or 'NULL (no valid file)'}")
        if args.apply and changes:
            apply_changes(conn, changes)
        print(f"{len(changes)} documents {'updated' if args.apply else 'would be updated'} in {env['DB_NAME']}"
              + ("" if args.apply else " (dry run — add --apply)"))
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
