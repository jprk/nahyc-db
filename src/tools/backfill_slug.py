"""One-time backfill of `Document.slug` — doc/PLAN.md §16 (2026-09-16).

Gives every document a stable, content-derived public identifier so the
per-document page can be linked, bookmarked and quoted without breaking
on the next pipeline rebuild (`Document.id` is reassigned on every run —
see `src/tools/slug.py` for the full background).

Assignment runs over the WHOLE corpus in one pass rather than per record,
because collision suffixes have to be handed out in a content-derived
order to stay reproducible; `slug.assign_slugs()` owns that rule and
`init_db.py` calls the same function on a rebuild.

Usage: `.venv/bin/python src/tools/backfill_slug.py [--apply]`
(dry-run report only by default; --apply writes to the database)
"""
import argparse
import os
import pathlib
import sys

import pymysql
from dotenv import load_dotenv

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from slug import assign_slugs

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
load_dotenv(REPO_ROOT / ".env")


def get_connection():
    return pymysql.connect(
        host=os.environ["DB_HOST"], port=int(os.environ["DB_PORT"]),
        user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"], cursorclass=pymysql.cursors.DictCursor,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true",
                         help="write changes to the database (default: dry-run report only)")
    args = parser.parse_args()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, identifier, title, slug FROM Document ORDER BY id")
    documents = cur.fetchall()

    slugs = assign_slugs((d["id"], d["identifier"], d["title"]) for d in documents)

    plan = [(d["id"], d["slug"], slugs[d["id"]])
            for d in documents if d["slug"] != slugs[d["id"]]]
    unchanged = len(documents) - len(plan)
    hashed = sum(1 for s in slugs.values() if s.startswith("doc-"))

    print(f"{len(documents)} documents")
    print(f"  slug to write: {len(plan)}")
    print(f"  already correct: {unchanged}")
    print(f"  derived from a designation: {len(slugs) - hashed}")
    print(f"  derived from a title hash (no real designation): {hashed}")

    if plan:
        print("\n--- first 15 ---")
        for doc_id, old, new in plan[:15]:
            print(f"  id={doc_id:5}: {old!r} -> {new!r}")

    assert len(set(slugs.values())) == len(slugs), "slug collision — assign_slugs is broken"

    if not args.apply:
        print("\nDry run — pass --apply to write changes.")
        conn.close()
        return

    for doc_id, _old, new_slug in plan:
        cur.execute("UPDATE Document SET slug=%s WHERE id=%s", (new_slug, doc_id))
    conn.commit()
    print(f"\nApplied {len(plan)} updates.")
    conn.close()


if __name__ == "__main__":
    main()
