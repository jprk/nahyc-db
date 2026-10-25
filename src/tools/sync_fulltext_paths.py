"""Repairs `Document.file_path` values that point at a file which is no longer
on disk — e.g. after `fetch_fulltext.py --audit --apply` removed a stored
search-results page — by pointing the document at the file the manifest now
has for its designation (the same order `init_db.py` uses: `odkaz_hlavni`,
`odkaz_eu`, `odkaz_sk`), or clearing it when there is none, so that nothing
serves a missing file or a wrong one.

A documents's own `file_path` is touched only when its file is missing; every
other document is left alone. Changes are applied in one transaction.

Usage:
    .venv/bin/python src/tools/sync_fulltext_paths.py            # dry run
    .venv/bin/python src/tools/sync_fulltext_paths.py --apply
"""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import fetch_fulltext as ff  # noqa: E402

REPO_ROOT = ff.REPO_ROOT
FIELD_PRIORITY = ("odkaz_hlavni", "odkaz_eu", "odkaz_sk")


def resolve_by_identifier(manifest, identifier):
    """`local_path` of the best fetched manifest entry for this designation, or None."""
    identifier = (identifier or "").strip()
    for field in FIELD_PRIORITY:
        for key in sorted(manifest):
            source_znacka, _, key_field = key.rpartition("|")
            if key_field != field or source_znacka.split("|", 1)[-1] != identifier:
                continue
            entry = manifest[key]
            if entry.get("status") == "fetched" and entry.get("local_path"):
                return entry["local_path"]
    return None


def plan_changes(rows, manifest, repo_root=REPO_ROOT):
    """[(document id, identifier, old path, new path or None)] for the rows
    `(id, identifier, file_path)` whose file is missing on disk."""
    root = pathlib.Path(repo_root)
    changes = []
    for doc_id, identifier, path in rows:
        if path and not (root / path).is_file():
            changes.append((doc_id, identifier, path, resolve_by_identifier(manifest, identifier)))
    return changes


def apply_changes(conn, changes):
    with conn.cursor() as cur:
        for doc_id, _identifier, old, new in changes:
            cur.execute("UPDATE Document SET file_path = %s WHERE id = %s AND file_path = %s", (new, doc_id, old))
    conn.commit()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--apply", action="store_true", help="change the database (dry run without it)")
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
            cur.execute("SELECT id, identifier, file_path FROM Document WHERE file_path IS NOT NULL")
            rows = cur.fetchall()
        changes = plan_changes(rows, ff.load_manifest())
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
