"""One-time backfill of `Document.source_id`/`DocumentSource.name`
("Gestor") for documents of type `Norma` — doc/PLAN.md §16 (2026-09-16).

Repairs a `doc/REQUIREMENTS.md` R1.6 regression: after
`backfill_puvodce.py` reduced the raw `gestor` lists to one institution
and `backfill_eu_gestor.py` resolved EU acts against EUR-Lex/Cellar, only
108 of 1 238 documents had any issuing body — 5 of 1 104 standards — and
`DocumentSource` held no standard-setting body at all, which R1.6 names
explicitly. The designation each standard already carries identifies its
publisher; see `standards_body.py` for the curated mapping and for which
designations are deliberately left unresolved.

Scoped to `dt.name = 'Norma'` so it cannot fight the other two backfills
over the same rows — the same exclusion discipline `backfill_puvodce.py`
needed once `backfill_eu_gestor.py` existed (verified there: without it,
re-running the earlier script proposed reverting all 43 resolved EU
records back to a Czech ministry).

Usage: `.venv/bin/python src/tools/backfill_standards_body.py [--apply]`
(dry-run report only by default; --apply writes to the database)
"""
import argparse
import os
import pathlib
import sys
from collections import Counter

import pymysql
from dotenv import load_dotenv

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from standards_body import resolve_standards_body

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
load_dotenv(REPO_ROOT / ".env")


def get_connection():
    return pymysql.connect(
        host=os.environ["DB_HOST"], port=int(os.environ["DB_PORT"]),
        user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"], cursorclass=pymysql.cursors.DictCursor,
    )


def get_or_create_source(cur, name, cache):
    if name in cache:
        return cache[name]
    cur.execute("SELECT id FROM DocumentSource WHERE name=%s", (name,))
    row = cur.fetchone()
    if row:
        cache[name] = row["id"]
        return row["id"]
    cur.execute("INSERT INTO DocumentSource (name) VALUES (%s)", (name,))
    cache[name] = cur.lastrowid
    return cache[name]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true",
                         help="write changes to the database (default: dry-run report only)")
    args = parser.parse_args()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT d.id, d.identifier, ds.name AS current_source
        FROM Document d
        JOIN DocumentType dt ON d.type_id = dt.id
        LEFT JOIN DocumentSource ds ON d.source_id = ds.id
        WHERE dt.name = 'Norma'
        ORDER BY d.id
    """)
    documents = cur.fetchall()

    plan = []          # (doc_id, current_source, new_source)
    unresolved = []    # (doc_id, identifier)
    unchanged = 0

    for doc in documents:
        body = resolve_standards_body(doc["identifier"])
        if not body:
            unresolved.append((doc["id"], doc["identifier"]))
        elif body != doc["current_source"]:
            plan.append((doc["id"], doc["current_source"], body))
        else:
            unchanged += 1

    print(f"{len(documents)} Norma documents")
    print(f"  issuing body resolved from designation, source updated: {len(plan)}")
    print(f"  already correct: {unchanged}")
    print(f"  no recognized designation, left without a Gestor: {len(unresolved)}")

    bodies = Counter(new for _, _, new in plan)
    if bodies:
        print(f"\n--- {len(bodies)} distinct issuing bodies in this run ---")
        for name, n in bodies.most_common():
            print(f"  {n:5d}  {name}")

    if unresolved:
        print(f"\n--- {len(unresolved)} unresolved ---")
        for doc_id, identifier in unresolved:
            print(f"  id={doc_id}: {identifier!r}")

    if not args.apply:
        print("\nDry run — pass --apply to write changes.")
        conn.close()
        return

    source_cache = {}
    for doc_id, _old, new_source in plan:
        source_id = get_or_create_source(cur, new_source, source_cache)
        cur.execute("UPDATE Document SET source_id=%s WHERE id=%s", (source_id, doc_id))
    conn.commit()

    cur.execute("""
        DELETE FROM DocumentSource
        WHERE id NOT IN (SELECT DISTINCT source_id FROM Document WHERE source_id IS NOT NULL)
    """)
    removed = cur.rowcount
    conn.commit()
    print(f"\nApplied {len(plan)} updates. Removed {removed} now-orphaned DocumentSource rows.")
    conn.close()


if __name__ == "__main__":
    main()
