"""CLI entry point for the agentic pipeline (`src/agentic/`, doc/PLAN.md
§45, 2026-09-19) — the automated-database-update mechanism §3 describes,
built on the `automation` branch per explicit user direction overriding
§5's earlier "not adopted this pass" decision.

Consumes `data/fulltext_screening_candidates.json` (already built by
`screen_eurlex.py`/`screen_esbirka.py`/`screen_slovlex.py` — step 1 of
§3.3, "source screening", already exists and is NOT rebuilt here) and
runs each not-yet-processed candidate through the LangGraph pipeline
(`src/agentic/graph.py`): Parse -> Extract -> Verify -> Research ->
Reconcile.

Outputs, split by outcome (never merged into one file, so a human
reviewing the review queue never has to also re-derive which records
are safe to auto-ingest):
- reconciliation_action == "new" and not escalated ->
  `data/discovered_agentic_candidates.json`, in the SAME raw-record shape
  every other `discovered_*.json` file already uses (verified against
  `data/discovered_eu_hydrogen_acts.json`), ready for
  `build_unified_db.py` to ingest exactly like its siblings.
- escalated, or reconciliation_action in ("existing", "ambiguous") ->
  `data/agentic_review_queue.json` — the human-in-the-loop destination
  §3.3 step 6 calls for. (A real admin-UI view for this queue is a
  follow-up, not built in this pass — see src/agentic/0README.md.)

A per-URL processed-cache (`data/agentic_pipeline_processed.json`, same
idempotent read-modify-write convention as `fetch_fulltext.py`'s
manifest) means re-running this script only processes NEW candidates,
so it's safe to invoke repeatedly (by hand today; by a scheduler once
one exists).

Usage:
    .venv/bin/python src/tools/run_agentic_pipeline.py --env-file .env.test --limit 5
    .venv/bin/python src/tools/run_agentic_pipeline.py --apply
"""
import argparse
import datetime
import json
import pathlib
import sys

BASE_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from agentic.graph import run_candidate  # noqa: E402
from agentic.reconciliation import get_connection  # noqa: E402
# Reused, not reimplemented -- `add_eurlex_hydrogen_acts.py` already
# hand-tuned this filter against a live batch (doc/PLAN.md §28) and found
# 38/51 raw "hydrogen" keyword matches were administrative ephemera
# (calls for proposals, staff working papers, written questions, annual
# accounts reports) or an unrelated chemical compound, not a binding
# hydrogen-energy act. The Extraction Agent's schema-validated output has
# no equivalent check, so without this the agentic pipeline would
# rediscover the exact same false-positive problem from scratch.
from add_eurlex_hydrogen_acts import classify_candidate, is_off_topic  # noqa: E402

CANDIDATES_PATH = REPO_ROOT / "data" / "fulltext_screening_candidates.json"
PROCESSED_CACHE_PATH = REPO_ROOT / "data" / "agentic_pipeline_processed.json"
DISCOVERED_PATH = REPO_ROOT / "data" / "discovered_agentic_candidates.json"
REVIEW_QUEUE_PATH = REPO_ROOT / "data" / "agentic_review_queue.json"
NOT_RELEVANT_PATH = REPO_ROOT / "data" / "agentic_not_relevant.json"

SOURCE_NAME = "Agentic_Discovery"

# Each top-level key in data/fulltext_screening_candidates.json is written
# by a DIFFERENT screening script and carries a different payload shape
# (doc/AUTOMATION.md odstavec 4.1) — only EUR-Lex entries are actual
# new-document candidates. This table states that per source instead of
# letting it happen by accident: before this existed, e-Sbírka entries
# were skipped only because they happen to carry `uri` rather than `url`
# and so fell through a falsy-URL guard, which would have silently
# started admitting 100 unresolved fragment nodes as documents the moment
# that screener gained a `url` field. A source missing from this table is
# skipped and reported, never processed on a guess — adding a screener
# means adding it here deliberately.
#
# `build_discovered_record()` reads `candidate["url"]` directly, which is
# safe precisely because every source marked processable here is declared
# to carry its URL in that field.
SOURCE_HANDLING = {
    "EUR-Lex": {
        "processable": True,
        "url_field": "url",
        "relevance_filter": "eurlex",
    },
    "e-Sbirka": {
        "processable": False,
        "reason": "screen_esbirka.py emits unresolved LOD fragment nodes "
                  "(`uri`/`snippet`), not documents — which act a fragment belongs "
                  "to is not determinable from the node itself. "
                  "add_esbirka_hydrogen_acts.py is the path that resolves these.",
    },
    "Slov-Lex": {
        "processable": False,
        "reason": "screen_slovlex.py reports link rot among already-known `odkaz_sk` "
                  "URLs — a maintenance report, not new-document discovery. "
                  "Slov-Lex exposes no public full-text search to discover from.",
    },
}


def load_json(path, default):
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)


def partition_candidates(data):
    """Splits the screening file's per-source lists into the candidates
    this pipeline can actually process and the ones it deliberately
    won't, according to SOURCE_HANDLING.

    Returns (processable, skipped_by_source, anomalies), where
    `processable` is a list of (source, candidate, url) tuples.

    Counting covers the WHOLE file regardless of any later `--limit`, so
    a limited run still reports the true shape of its input rather than
    however far it happened to get."""
    processable, skipped, anomalies = [], {}, []
    for source, entries in data.items():
        handling = SOURCE_HANDLING.get(source)
        if handling is None or not handling["processable"]:
            key = source if handling else f"{source} (unknown — not declared in SOURCE_HANDLING)"
            skipped[key] = skipped.get(key, 0) + len(entries)
            continue
        for entry in entries:
            url = entry.get(handling["url_field"])
            if not url:
                # A source declared processable whose entry lacks its own
                # declared URL field is a genuine anomaly, not routine —
                # the screener's output shape has changed under us.
                anomalies.append({"source": source, "missing_field": handling["url_field"],
                                   "entry_keys": sorted(entry.keys())})
                continue
            processable.append((source, entry, url))
    return processable, skipped, anomalies


def build_discovered_record(source, candidate, extracted):
    """Same field shape as `data/discovered_eu_hydrogen_acts.json`'s
    real entries -- see src/tools/run_agentic_pipeline.py's own
    module docstring for the reference record this was checked against.
    """
    url = candidate.get("url", "")
    title = extracted.get("nazev") or candidate.get("title", "")
    return {
        "zdroj_dat": SOURCE_NAME,
        "nazev_cz": title,
        "znacka": extracted.get("znacka") or "",
        "typ_dokumentu": extracted.get("typ_dokumentu") or "",
        "sekce": "",
        "kategorie_trida": "",
        "klicova_slova": [candidate["matched_keyword"]] if candidate.get("matched_keyword") else [],
        "odkaz_hlavni": url,
        "nazev_eu": title if source == "EUR-Lex" else "",
        "odkaz_eu": url if source == "EUR-Lex" else "",
        "nazev_sk": title if source == "Slov-Lex" else "",
        "odkaz_sk": url if source == "Slov-Lex" else "",
        "platnost": "",
        "ratifikovan": "",
        "gestor": [extracted["gestor"]] if extracted.get("gestor") else [],
        "jazyk": "",
        "anotace_poznamka": (
            f"Nalezeno a ověřeno agentic pipeline (doc/PLAN.md §45, {source}); "
            f"verification_evidence: {extracted.get('verification_evidence')}"
        ),
        "jurisdikce": "EU" if source == "EUR-Lex" else "SK" if source == "Slov-Lex" else "CZ",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--env-file", default=".env",
                         help="passed through to the Reconciliation Agent's DB connection "
                              "(default: .env; use .env.test for a rehearsal run)")
    parser.add_argument("--limit", type=int, default=None,
                         help="process at most this many not-yet-processed candidates")
    parser.add_argument("--apply", action="store_true",
                         help="write output files (default: dry run, prints a summary only)")
    args = parser.parse_args()

    processed = load_json(PROCESSED_CACHE_PATH, {})
    discovered = load_json(DISCOVERED_PATH, [])
    review_queue = load_json(REVIEW_QUEUE_PATH, [])
    not_relevant = load_json(NOT_RELEVANT_PATH, [])

    def conn_factory():
        return get_connection(env_file=args.env_file)

    candidates, skipped_by_source, anomalies = partition_candidates(
        load_json(CANDIDATES_PATH, {}))

    processed_count = 0
    for source, candidate, url in candidates:
        if url in processed:
            continue
        if args.limit is not None and processed_count >= args.limit:
            break

        if SOURCE_HANDLING[source].get("relevance_filter") == "eurlex":
            doc_type = classify_candidate(candidate)
            if doc_type is None or is_off_topic(candidate.get("title", "")):
                reason = "not a binding act type" if doc_type is None else "off-topic title pattern"
                not_relevant.append({"url": url, "source": source, "title": candidate.get("title"),
                                      "reason": reason})
                processed[url] = {"processed_at": datetime.datetime.now().isoformat(timespec="seconds"),
                                   "outcome": "not_relevant"}
                processed_count += 1
                print(f"[skip] {candidate.get('title', url)} -- {reason}")
                continue

        tagged_candidate = dict(candidate, source=source)
        result = run_candidate(tagged_candidate, get_connection=conn_factory)
        processed_count += 1
        now = datetime.datetime.now().isoformat(timespec="seconds")

        outcome = {
            "url": url,
            "source": source,
            "escalated": result.get("escalated", False),
            "escalation_reason": result.get("escalation_reason"),
            "reconciliation_action": result.get("reconciliation_action"),
            "processed_at": now,
        }

        is_clean_new = not result.get("escalated") and result.get("reconciliation_action") == "new"
        if is_clean_new:
            discovered.append(build_discovered_record(source, candidate, result.get("extracted") or {}))
            print(f"[new] {candidate.get('title', url)}")
        else:
            outcome["candidate"] = candidate
            outcome["extracted"] = result.get("extracted")
            review_queue.append(outcome)
            print(f"[review] {candidate.get('title', url)} -- {outcome['escalation_reason'] or outcome['reconciliation_action']}")

        processed[url] = {"processed_at": now, "outcome": "new" if is_clean_new else "queued"}

    for skipped_source, count in sorted(skipped_by_source.items()):
        if not count:
            continue
        reason = (SOURCE_HANDLING.get(skipped_source) or {}).get(
            "reason", "source not declared processable")
        print(f"[source skipped] {skipped_source}: {count} entr(ies) — {reason}")
    for anomaly in anomalies:
        print(f"[anomaly] {anomaly['source']} entry has no '{anomaly['missing_field']}' field "
              f"(keys present: {', '.join(anomaly['entry_keys'])}) — screener output shape may have changed")

    print(f"\nProcessed {processed_count} candidate(s); "
          f"{len(discovered)} total discovered, {len(review_queue)} total in review queue, "
          f"{len(not_relevant)} total not relevant.")

    if args.apply:
        save_json(PROCESSED_CACHE_PATH, processed)
        save_json(DISCOVERED_PATH, discovered)
        save_json(REVIEW_QUEUE_PATH, review_queue)
        save_json(NOT_RELEVANT_PATH, not_relevant)
        print("Written (--apply).")
    else:
        print("Dry run -- pass --apply to write output files.")


if __name__ == "__main__":
    main()
