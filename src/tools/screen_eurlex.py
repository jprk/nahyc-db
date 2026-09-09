"""Screens the EUR-Lex Cellar SPARQL endpoint for hydrogen-related EU
legislation that isn't in our corpus yet, and reports it for human review
(never auto-inserted into `data/database_merged_raw.json` — see
`doc/PLAN.md` §4).

The Cellar SPARQL endpoint (`http://publications.europa.eu/webapi/rdf/sparql`)
is a public, unauthenticated service operated by the EU Publications Office
— confirmed reachable and query-able (2026-09-09) with a plain
`bif:contains` full-text filter over `cdm:expression_title`. This is the
same "query the real API instead of guessing" pattern already used by
`check_csn_validity.py` for ČSN designations.

Usage:
    .venv/bin/python src/tools/screen_eurlex.py

Output: `data/fulltext_screening_candidates.json`, key `"EUR-Lex"` — a
list of {celex, title, url, matched_keyword, screened_at} for CELEX
numbers not already represented (by numeric act reference) in the corpus.
"""
import datetime
import json
import pathlib
import re
import time

import requests

BASE_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent
RAW_DB_PATH = REPO_ROOT / "data" / "database_merged_raw.json"
CANDIDATES_PATH = REPO_ROOT / "data" / "fulltext_screening_candidates.json"

SPARQL_ENDPOINT = "http://publications.europa.eu/webapi/rdf/sparql"
SLEEP_SECONDS = 2
USER_AGENT = "Mozilla/5.0 (compatible; NAHYC-DP004-screening-tool/1.0; +research use, low-volume)"

HYDROGEN_KEYWORDS = ["hydrogen"]
RESULT_LIMIT = 200

_QUERY_TEMPLATE = """
PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
SELECT DISTINCT ?celex ?title WHERE {{
  ?work cdm:resource_legal_id_celex ?celex .
  ?expr cdm:expression_belongs_to_work ?work .
  ?expr cdm:expression_uses_language <http://publications.europa.eu/resource/authority/language/ENG> .
  ?expr cdm:expression_title ?title .
  FILTER(bif:contains(?title, "'{keyword}'"))
}}
LIMIT {limit}
"""


def build_query(keyword, limit=RESULT_LIMIT):
    return _QUERY_TEMPLATE.format(keyword=keyword, limit=limit)


def run_sparql(session, query):
    """Executes a SPARQL query against the Cellar endpoint. Returns the
    parsed `results.bindings` list, or [] on any failure — a screening
    aid should degrade gracefully, not crash the whole run over one bad
    query."""
    try:
        resp = session.get(SPARQL_ENDPOINT, params={
            "format": "application/sparql-results+json",
            # See screen_esbirka.py's run_sparql for why this is stripped
            # defensively — a leading/trailing-whitespace query was found
            # to trip that endpoint's WAF; harmless precaution here too.
            "query": query.strip(),
        }, timeout=30)
        resp.raise_for_status()
        return resp.json().get("results", {}).get("bindings", [])
    except (requests.RequestException, ValueError):
        return []


_CELEX_RE = re.compile(r"^\d(\d{4})[A-Z](\d{4,})")


def celex_candidate_znackas(celex):
    """A CELEX id encodes sector + year + doc-type + number (e.g.
    "32014R0559" -> year 2014, number 559). Our corpus's own znacka for EU
    acts is extracted from title text as "(EU) YYYY/NUM" (post-2015
    numbering) — returns both that and the older "NUM/YYYY" ordering as
    candidates, normalized to a bare "YYYY/NUM" digit shape, since we
    don't know which numbering convention a given title used without
    reading it. Returns [] for anything that doesn't parse (e.g. non-EU
    sectors, national transposition CELEX ids) — those are reported with
    the raw CELEX id instead of a guessed znacka."""
    m = _CELEX_RE.match(celex)
    if not m:
        return []
    year, number = m.group(1), str(int(m.group(2)))
    return [f"{year}/{number}", f"{number}/{year}"]


def normalize_for_diff(znacka):
    """Reduces a znacka to its bare digit/slash shape for cross-format
    comparison (title-extracted "(EU) 2024/1788" vs. CELEX-derived
    "2024/1788") — deliberately coarser than `deduplicate_db.py`'s
    `core_znacka`, which is not imported here to avoid its module-level
    OpenAI/logging side effects (same reasoning as `analyze_similarities.py`)."""
    return re.sub(r"[^0-9/]", "", znacka or "")


def load_known_znacka_digits(raw_data):
    return {normalize_for_diff(r.get("znacka", "")) for r in raw_data if r.get("znacka")}


def find_new_candidates(bindings, known_digits, keyword):
    """Pure diffing logic, unit-testable without network access."""
    now = datetime.datetime.now().isoformat(timespec="seconds")
    seen_celex = set()
    candidates = []
    for b in bindings:
        celex = b["celex"]["value"]
        if celex in seen_celex:
            continue
        seen_celex.add(celex)
        title = b["title"]["value"]
        candidate_znackas = celex_candidate_znackas(celex)
        if candidate_znackas and any(normalize_for_diff(z) in known_digits for z in candidate_znackas):
            continue  # already in our corpus under some numbering convention
        candidates.append({
            "celex": celex,
            "title": title,
            "url": f"https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:{celex}",
            "matched_keyword": keyword,
            "screened_at": now,
        })
    return candidates


def load_candidates_file():
    if CANDIDATES_PATH.exists():
        with open(CANDIDATES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_candidates_file(data):
    with open(CANDIDATES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)


def main():
    with open(RAW_DB_PATH, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    known_digits = load_known_znacka_digits(raw_data)

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"})

    all_new = []
    for idx, keyword in enumerate(HYDROGEN_KEYWORDS):
        if idx > 0:
            time.sleep(SLEEP_SECONDS)
        print(f"=== querying Cellar for title containing {keyword!r} ===")
        bindings = run_sparql(session, build_query(keyword))
        new_candidates = find_new_candidates(bindings, known_digits, keyword)
        print(f"  {len(bindings)} matches, {len(new_candidates)} not already in the corpus")
        all_new.extend(new_candidates)

    candidates_file = load_candidates_file()
    candidates_file["EUR-Lex"] = all_new
    save_candidates_file(candidates_file)
    print(f"\nWrote {len(all_new)} candidate(s) to {CANDIDATES_PATH.relative_to(REPO_ROOT)} "
          f"under key \"EUR-Lex\" — human review required before any of this is folded "
          f"into build_unified_db.py.")


if __name__ == "__main__":
    main()
