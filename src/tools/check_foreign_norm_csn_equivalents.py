"""For every Slovak (STN) or German norm in the Sinay_Normy source whose
designation carries an ISO or EN ISO reference, checks the ČSN online
registry (see check_csn_validity.py) for a currently-valid Czech ("ČSN")
adoption of the SAME international standard.

This is a cross-reference lookup, NOT a merge: an STN or German norm is a
legally distinct document from its Czech ČSN counterpart even when they
share an EN/ISO ancestor (see doc/PLAN.md Step 1 follow-up #8, and the
jurisdikce veto in deduplicate_db.py's build_clusters()) — the two must
never be conflated into one database record. What this script produces is
purely informational: "this foreign norm has/doesn't have a matching valid
Czech standard", for a human (or a later, deliberate schema change) to act
on — it does not modify database_merged_raw.json or the DB itself.

Usage: .venv/bin/python src/tools/check_foreign_norm_csn_equivalents.py
Output: data/20250712_Sinay/sinay_normy_csn_equivalents.json

Queries are deduplicated first (many source rows cite the same standard —
duplicate rows in the source, or a "-"/"–" dash-style formatting variant of
the same designation) to minimize network calls; still rate-limited via
check_csn_validity's SLEEP_SECONDS, so this takes a while (hundreds of
queries at ~2s each) — run it in the background.
"""
import json
import pathlib
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import requests
from check_csn_validity import SLEEP_SECONDS, USER_AGENT, search

BASE_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent
RAW_DB_PATH = REPO_ROOT / "data" / "database_merged_raw.json"
OUTPUT_PATH = REPO_ROOT / "data" / "20250712_Sinay" / "sinay_normy_csn_equivalents.json"

_ISO_EN_CORE_RE = re.compile(
    r"\b((?:EN\s+)?ISO(?:/[A-Z]+)?\s+[\d.\-]+|EN\s+ISO\s+[\d.\-]+|EN\s+\d{3,6}(?:-\d+)*)\b",
    re.IGNORECASE,
)


def extract_iso_en_core(znacka):
    """Pulls an 'ISO <n>', 'EN ISO <n>', or bare 'EN <n>' reference out of
    a foreign designation, e.g. 'STN EN ISO 11114-4/ - 2017.10' ->
    'EN ISO 11114-4'. Returns None if the designation doesn't carry one
    (e.g. a purely national code like 'DASt 007' or 'BVEG Leitfaden ...',
    which has no ISO/EN counterpart to look up at all)."""
    m = _ISO_EN_CORE_RE.search(znacka or "")
    if not m:
        return None
    return re.sub(r"\s+", " ", m.group(1)).strip()


def collect_candidates(raw_records):
    """Groups Sinay_Normy SK/DE records by their (uppercased) ISO/EN core,
    so each distinct standard is only queried once regardless of how many
    source rows cite it."""
    by_query = {}
    for r in raw_records:
        if r.get("zdroj_dat") != "Sinay_Normy":
            continue
        if r.get("jurisdikce") not in ("SK", "DE"):
            continue
        core = extract_iso_en_core(r.get("znacka", ""))
        if not core:
            continue
        query_key = core.upper()
        by_query.setdefault(query_key, {"query": core, "jurisdikce": set(), "source_designations": set()})
        by_query[query_key]["jurisdikce"].add(r["jurisdikce"])
        by_query[query_key]["source_designations"].add(r.get("znacka", ""))
    return by_query


def main():
    with open(RAW_DB_PATH, "r", encoding="utf-8") as f:
        raw_records = json.load(f)

    candidates = collect_candidates(raw_records)
    print(f"{len(candidates)} unique ISO/EN reference(s) to check, "
          f"covering {sum(len(c['source_designations']) for c in candidates.values())} source designations.")

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    results = []
    for i, (query_key, info) in enumerate(sorted(candidates.items())):
        if i > 0:
            time.sleep(SLEEP_SECONDS)
        query = f"ISO {info['query']}" if not info["query"].upper().startswith(("ISO", "EN")) else info["query"]
        try:
            registry_results = search(session, query)
        except Exception as e:
            results.append({
                "query": query, "jurisdikce": sorted(info["jurisdikce"]),
                "source_designations": sorted(info["source_designations"]),
                "status": "lookup_failed", "error": str(e),
            })
            print(f"[{i+1}/{len(candidates)}] {query}: lookup failed ({e})")
            continue

        valid = [r for r in registry_results if r.get("is_valid") and r.get("designation")]
        valid_designations = sorted({r["designation"].strip() for r in valid})

        if len(valid_designations) == 1:
            status = "csn_equivalent_found"
            print(f"[{i+1}/{len(candidates)}] {query}: -> {valid_designations[0]}")
        elif not registry_results:
            status = "no_match"
            print(f"[{i+1}/{len(candidates)}] {query}: no match in registry")
        elif not valid_designations:
            status = "found_but_not_currently_valid"
            print(f"[{i+1}/{len(candidates)}] {query}: found, but no currently-valid ČSN edition")
        else:
            status = "ambiguous_multiple_valid"
            print(f"[{i+1}/{len(candidates)}] {query}: ambiguous ({len(valid_designations)} valid designations)")

        results.append({
            "query": query, "jurisdikce": sorted(info["jurisdikce"]),
            "source_designations": sorted(info["source_designations"]),
            "status": status, "csn_designations": valid_designations,
        })

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    found = sum(1 for r in results if r["status"] == "csn_equivalent_found")
    print(f"\nDone. {found}/{len(results)} have a confirmed, currently-valid ČSN equivalent.")
    print(f"Written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
