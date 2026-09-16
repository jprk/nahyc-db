"""One-time backfill of `Document.source_id`/`DocumentSource.name`
("Gestor") for EU-type documents (`Nařízení EU`, `Směrnice EU`,
`Rozhodnutí EU`) — user finding (2026-09-16): `backfill_puvodce.py`'s
"primary responsible ministry" reduction (src/tools/puvodce.py) is right
for national CZ/SK acts, but for an EU act itself the Gestor should be
the EU body that owns it (Directorate-General when known, else the
enacting top-level institution) — not a Czech ministry that happened to
be first in the record's AI-generated `gestor` list, and not the source
data's often-erratic `gestor` list at all. Per user decision (2026-09-16):
consult the authoritative source — EUR-Lex/Cellar — instead, via
`src/sites/eurlex.py`'s `fetch_responsible_gestor()`.

Usage: `.venv/bin/python src/tools/backfill_eu_gestor.py [--apply]`
(dry-run report only by default; --apply writes to the database)
"""
import argparse
import json
import os
import pathlib
import sys
import time

import pymysql
import requests
from dotenv import load_dotenv

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "sites"))
from eurlex import fetch_responsible_gestor

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
load_dotenv(REPO_ROOT / ".env")

EU_TYPES = ("Nařízení EU", "Směrnice EU", "Rozhodnutí EU")
UNRESOLVED_REVIEW_REASON = "EU akt: autoritativní gestor (DG/instituce) se v EUR-Lex/Cellar nepodařilo dohledat"

# Keyed by `Document.url` (the natural stable key — `identifier` is
# blank for a few records, e.g. a slov-lex.sk-only mirror) so
# `init_db.py` can reuse an already-resolved Gestor on a future rebuild
# from JSON without repeating ~44 live Cellar SPARQL queries — same
# idempotent-cache convention as `data/site_metadata_cache.json`
# (`fetch_authoritative_metadata.py`). Only a successful resolution is
# cached; an unresolved record (id=105) is retried on the next run
# rather than cached as a permanent miss.
CACHE_PATH = REPO_ROOT / "data" / "eu_gestor_cache.json"


def load_cache():
    if CACHE_PATH.exists():
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2, sort_keys=True)


def get_connection():
    return pymysql.connect(
        host=os.environ["DB_HOST"], port=int(os.environ["DB_PORT"]),
        user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"], cursorclass=pymysql.cursors.DictCursor,
    )


def append_review_reason(existing, reason):
    existing = (existing or "").strip()
    if not existing:
        return reason
    if reason in existing:
        return existing
    return f"{existing}; {reason}"


def get_or_create_source(cur, name, cache):
    if name in cache:
        return cache[name]
    cur.execute("SELECT id FROM DocumentSource WHERE name=%s", (name,))
    row = cur.fetchone()
    if row:
        cache[name] = row["id"]
        return row["id"]
    cur.execute("INSERT INTO DocumentSource (name) VALUES (%s)", (name,))
    new_id = cur.lastrowid
    cache[name] = new_id
    return new_id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true",
                         help="write changes to the database (default: dry-run report only)")
    args = parser.parse_args()

    conn = get_connection()
    cur = conn.cursor()
    placeholders = ",".join(["%s"] * len(EU_TYPES))
    cur.execute(f"""
        SELECT d.id, d.identifier, d.title, d.url, d.needs_review, d.review_reason,
               dt.name AS type_name, ds.name AS current_source
        FROM Document d
        JOIN DocumentType dt ON d.type_id = dt.id
        LEFT JOIN DocumentSource ds ON d.source_id = ds.id
        WHERE dt.name IN ({placeholders})
        ORDER BY d.id
    """, EU_TYPES)
    documents = cur.fetchall()

    cache = load_cache()
    session = requests.Session()
    resolved_plan = []    # (doc_id, current_source, new_source)
    unresolved_plan = []  # (doc_id, current_source, new_review_reason)
    unchanged = 0

    for i, doc in enumerate(documents):
        gestor = cache.get(doc["url"]) if doc["url"] else None
        if not gestor:
            gestor = fetch_responsible_gestor(
                doc["url"], identifier=doc["identifier"], title=doc["title"],
                type_name=doc["type_name"], session=session)
            if gestor and doc["url"]:
                cache[doc["url"]] = gestor
        if gestor:
            if gestor != doc["current_source"]:
                resolved_plan.append((doc["id"], doc["current_source"], gestor))
            else:
                unchanged += 1
        else:
            new_reason = append_review_reason(doc["review_reason"], UNRESOLVED_REVIEW_REASON)
            if doc["current_source"] is not None or new_reason != doc["review_reason"]:
                unresolved_plan.append((doc["id"], doc["current_source"], new_reason))
            else:
                unchanged += 1
        if (i + 1) % 10 == 0:
            time.sleep(0.5)  # courteous pacing against the public Cellar endpoint

    save_cache(cache)

    print(f"{len(documents)} EU-type documents (Nařízení EU / Směrnice EU / Rozhodnutí EU)")
    print(f"  resolved via EUR-Lex/Cellar, source updated: {len(resolved_plan)}")
    print(f"  unresolved — cleared + flagged for review: {len(unresolved_plan)}")
    print(f"  unchanged: {unchanged}")

    print(f"\n--- {len(resolved_plan)} resolved changes ---")
    for doc_id, old, new in resolved_plan:
        print(f"  id={doc_id}: {old!r} -> {new!r}")

    if unresolved_plan:
        print(f"\n--- {len(unresolved_plan)} unresolved (source cleared, flagged) ---")
        for doc_id, old, _reason in unresolved_plan:
            print(f"  id={doc_id}: {old!r} -> None (needs_review)")

    if not args.apply:
        print("\nDry run — pass --apply to write changes.")
        conn.close()
        return

    source_cache = {}
    for doc_id, _old, new_source in resolved_plan:
        source_id = get_or_create_source(cur, new_source, source_cache)
        cur.execute("UPDATE Document SET source_id=%s WHERE id=%s", (source_id, doc_id))
    for doc_id, _old, new_reason in unresolved_plan:
        cur.execute("UPDATE Document SET source_id=NULL, needs_review=1, review_reason=%s WHERE id=%s",
                     (new_reason, doc_id))
    conn.commit()

    cur.execute("""
        DELETE FROM DocumentSource
        WHERE id NOT IN (SELECT DISTINCT source_id FROM Document WHERE source_id IS NOT NULL)
    """)
    removed = cur.rowcount
    conn.commit()
    print(f"\nApplied {len(resolved_plan)} resolved + {len(unresolved_plan)} unresolved updates. "
          f"Removed {removed} now-orphaned DocumentSource rows.")
    conn.close()


if __name__ == "__main__":
    main()
