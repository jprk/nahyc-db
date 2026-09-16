"""One-time backfill of `Document.title` for `Norma`-type records
(designation-placement request, 2026-09-15): prefixes each standard's own
designation (`Document.identifier`, e.g. "ČSN EN 17124") to the front of
its title, formatted "<designation> — <title>" — see `norm_title.py` for
why this was needed (the app never displayed `identifier` at all, and a
few Sinay-sourced titles embedded the designation as a trailing
parenthetical instead). Records whose `identifier` isn't a real
designation (no digit — a handful of German industry guidance leaflets
etc. that genuinely have no number) are left untouched, never guessed.

Usage: `.venv/bin/python src/tools/backfill_norm_designation.py [--apply]`
(dry-run report only by default; --apply writes to the database)
"""
import argparse
import os
import pathlib
import sys

import pymysql
from dotenv import load_dotenv

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from norm_title import format_norm_title

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
    cur.execute("""
        SELECT d.id, d.title, d.identifier
        FROM Document d
        JOIN DocumentType dt ON d.type_id = dt.id
        WHERE dt.name = 'Norma'
    """)
    documents = cur.fetchall()

    updates = []  # (id, new_title)
    skipped_no_designation = 0

    for doc in documents:
        new_title, changed = format_norm_title(doc["title"], doc["identifier"])
        if changed:
            updates.append((doc["id"], new_title))
        else:
            skipped_no_designation += 1

    print(f"{len(documents)} Norma documents total")
    print(f"  designation prefixed: {len(updates)}")
    print(f"  skipped (no real designation in identifier): {skipped_no_designation}")

    if not args.apply:
        print("\nDry run — pass --apply to write changes.")
        conn.close()
        return

    for doc_id, new_title in updates:
        cur.execute("UPDATE Document SET title=%s WHERE id=%s", (new_title, doc_id))
    conn.commit()
    print(f"\nApplied {len(updates)} updates.")
    conn.close()


if __name__ == "__main__":
    main()
