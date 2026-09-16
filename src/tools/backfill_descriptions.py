"""SUPERSEDED — doc/PLAN.md §22, 2026-09-17. Do not use for new work; kept
only for its dry-run reporting shape and as a historical record of how
the live database was originally backfilled. This script writes straight
to the live database and, unlike every other stage of the pipeline,
never updates `data/database_merged_deduplicated.json` — so a bare
`init_db.py` re-run (without first re-running `build_unified_db.py`)
silently loses everything it applied. That is exactly the "silently
discarded on next rebuild" failure §17.1 warned about for
`enrich_annotations.py`, and this script turned out to have the same
flaw; it actually happened once, caught and fixed via a full pipeline
rebuild (doc/PLAN.md §20).

`src/tools/build_unified_db.py`'s `apply_authoritative_metadata()` and
`apply_synthesized_summary()` already do this exact job — same cache
files, same `stn:<designation>`/`<designation>` keys, same target
fields — but correctly, through the JSON pipeline: every full rebuild
(`build_unified_db.py` → `deduplicate_db.py` → `init_db.py` →
`load_document_relations.py` → `load_process_layer.py`) re-applies both
caches into a fresh `database_merged_deduplicated.json`, and
`init_db.py`'s own `detect_data_quality_issues()` then computes
`needs_review`/`review_reason` from the *resolved* description, so the
"chybí popis/anotace dokumentu" reason clears itself automatically —
no separate reason-stripping step needed. For any future annotation-
fetch round (the remaining `iso.org`/`dvgw.de`/`webstore.iec.ch`/
`eiga.eu`/`bveg.de` domains from doc/PLAN.md §17.2/§17.7), add the
result to `data/site_metadata_cache.json` or
`data/synthesized_summaries.json` as usual, then run the full pipeline
rebuild above — not this script.

--- Original docstring, for context ---

One-time backfill of the two description tiers onto the live database
— doc/PLAN.md §17, 2026-09-17.

Applies what the fetch/translate/synthesize chain produced, keeping the
two tiers strictly apart:

* **fetched** — the publisher's own scope text, translated to Czech
  (`data/site_metadata_cache.json`, `description` + `description_source`)
  → `Document.popis_autoritativni` AND `Document.description`, and the
  record's "chybí popis/anotace dokumentu" review reason is cleared,
  because it no longer applies.
* **approximate** — a title-derived restatement for standards whose
  publisher publishes no scope at all
  (`data/synthesized_summaries.json`) → `Document.popis_priblizny` ONLY.
  `description` is left empty and `needs_review` stays set: the record
  still has no real description, and the UI marks the summary
  "Přibližné shrnutí, neověřeno".

A record that already has a description is never touched by either tier.

Usage: `.venv/bin/python src/tools/backfill_descriptions.py [--apply]`
(dry-run report only by default; --apply writes to the database)
"""
import argparse
import json
import os
import pathlib
import sys

import pymysql
from dotenv import load_dotenv

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from norm_title import designation_core

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
CACHE_PATH = REPO_ROOT / "data" / "site_metadata_cache.json"
SUMMARIES_PATH = REPO_ROOT / "data" / "synthesized_summaries.json"
load_dotenv(REPO_ROOT / ".env")

MISSING_DESCRIPTION_REASON = "chybí popis/anotace dokumentu"


def get_connection():
    return pymysql.connect(
        host=os.environ["DB_HOST"], port=int(os.environ["DB_PORT"]),
        user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"], cursorclass=pymysql.cursors.DictCursor,
    )


def load_json(path):
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def strip_reason(review_reason, reason):
    """Removes one reason from a "; "-joined review_reason, returning the
    remainder or None. Keeps every other reason intact — a record flagged
    for a garbled designation as well must stay flagged for that."""
    parts = [p.strip() for p in (review_reason or "").split(";") if p.strip()]
    kept = [p for p in parts if p != reason]
    return "; ".join(kept) or None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true",
                         help="write changes to the database (default: dry-run report)")
    args = parser.parse_args()

    cache = load_json(CACHE_PATH)
    summaries = load_json(SUMMARIES_PATH)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT d.id, d.identifier, d.description, d.popis_autoritativni,
               d.popis_priblizny, d.needs_review, d.review_reason
        FROM Document d JOIN DocumentType dt ON d.type_id = dt.id
        WHERE dt.name = 'Norma' AND d.identifier REGEXP '^(STN|TNI)'
    """)
    documents = cur.fetchall()

    fetched_plan, approximate_plan = [], []
    already = 0

    for doc in documents:
        designation = designation_core(doc["identifier"])
        if (doc["description"] or "").strip():
            already += 1
            continue

        entry = cache.get(f"stn:{designation}")
        czech = (entry or {}).get("description", "") or ""
        if czech.strip():
            fetched_plan.append((
                doc["id"], czech.strip(),
                strip_reason(doc["review_reason"], MISSING_DESCRIPTION_REASON)))
            continue

        summary = (summaries.get(designation) or {}).get("popis_priblizny", "")
        if summary.strip() and summary.strip() != (doc["popis_priblizny"] or "").strip():
            approximate_plan.append((doc["id"], summary.strip()))

    print(f"{len(documents)} STN/TNI standards")
    print(f"  already had a description: {already}")
    print(f"  fetched scope -> description + popis_autoritativni: {len(fetched_plan)}")
    print(f"  approximate summary -> popis_priblizny only (stays flagged): {len(approximate_plan)}")
    have_approximate = sum(1 for d in documents
                           if not (d["description"] or "").strip()
                           and (d["popis_priblizny"] or "").strip())
    print(f"  already carried an approximate summary: {have_approximate}")
    unfilled = (len(documents) - already - len(fetched_plan)
                - len(approximate_plan) - have_approximate)
    print(f"  still without either: {unfilled}")

    if not args.apply:
        print("\nDry run — pass --apply to write changes.")
        conn.close()
        return

    for doc_id, czech, review_reason in fetched_plan:
        cur.execute("""UPDATE Document
                       SET description=%s, popis_autoritativni=%s,
                           review_reason=%s, needs_review=%s
                       WHERE id=%s""",
                     (czech, czech, review_reason, 1 if review_reason else 0, doc_id))
    for doc_id, summary in approximate_plan:
        # description deliberately untouched: an approximate summary is
        # not a description, and needs_review stays set.
        cur.execute("UPDATE Document SET popis_priblizny=%s WHERE id=%s", (summary, doc_id))
    conn.commit()
    print(f"\nApplied {len(fetched_plan)} fetched + {len(approximate_plan)} approximate.")
    conn.close()


if __name__ == "__main__":
    main()
