"""Screens the e-Sbírka open-data SPARQL endpoint for hydrogen-related
Czech legislation, and reports matches for human review (never auto-
inserted into `data/database_merged_raw.json` — see `doc/PLAN.md` §4).

**Disclosed limitation, found while building this:** e-Sbírka's actual
public REST API (`sbr-externi`, per its own frontend config at
`https://e-sbirka.gov.cz/assets/configs/env.js`) requires registering as
a client with the Ministry of Interior (a manual data-box request, not
something this script can do) and its anonymous endpoint doesn't resolve
publicly. What IS confirmed reachable, public, and unauthenticated
(2026-09-09) is a separate Linked Open Data service at
`https://opendata.eselpoint.gov.cz/sparql`, covering the same underlying
content (individual legal acts and their text, addressable by ELI —
European Legislation Identifier — at
`https://opendata.eselpoint.gov.cz/esel-esb/eli/cz/sb/{year}/{number}`).
That's what this script queries.

**A further, disclosed gap:** a full-text hit inside this graph (a
`právní-akt-fragment`/`-metadata`/`-binární-soubor` node) doesn't reliably
carry a scrapeable back-link to its owning act's ELI/citation in the
rendered page — unlike EUR-Lex's Cellar graph, whose CELEX id is directly
derivable from the matched triple. Resolving "this paragraph belongs to
law X" would need deeper knowledge of the `slovník.gov.cz/datový/sbírka`
vocabulary's inverse properties than this pass invested in. So, unlike
`screen_eurlex.py`, this script does **not** attempt to compute a `znacka`
and diff it against the corpus — every hit is reported as an unresolved
candidate for a human to identify. To avoid the report growing
unboundedly noisy across reruns, hits already recorded in a previous run
are not re-added.

Usage:
    .venv/bin/python src/tools/screen_esbirka.py

Output: `data/fulltext_screening_candidates.json`, key `"e-Sbirka"`.
"""
import datetime
import json
import pathlib
import re
import time

import requests

BASE_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent
CANDIDATES_PATH = REPO_ROOT / "data" / "fulltext_screening_candidates.json"

SPARQL_ENDPOINT = "https://opendata.eselpoint.gov.cz/sparql"
SLEEP_SECONDS = 2
USER_AGENT = "Mozilla/5.0 (compatible; NAHYC-DP004-screening-tool/1.0; +research use, low-volume)"

# Virtuoso's bif:contains needs >=4 leading characters before a wildcard —
# one wildcarded stem catches "vodík"/"vodíku"/"vodíková"/"vodíkových"/...
# in a single query instead of enumerating every inflected form.
HYDROGEN_KEYWORDS = ["vodí*"]
RESULT_LIMIT = 100

_SEARCH_QUERY_TEMPLATE = """
PREFIX bif: <bif:>
SELECT DISTINCT ?s WHERE {{
  ?s ?p ?o .
  FILTER(bif:contains(?o, "'{keyword}'"))
}}
LIMIT {limit}
"""

_SNIPPET_QUERY_TEMPLATE = """
SELECT ?p ?o WHERE {{
  <{uri}> ?p ?o .
}}
LIMIT 20
"""


def build_search_query(keyword, limit=RESULT_LIMIT):
    return _SEARCH_QUERY_TEMPLATE.format(keyword=keyword, limit=limit)


def build_snippet_query(uri):
    return _SNIPPET_QUERY_TEMPLATE.format(uri=uri)


def run_sparql(session, query, accept="application/sparql-results+json", output_param="output"):
    """e-Sbírka's SPARQL endpoint takes the response format via an
    `output` query param (not the `format`/`Accept`-header convention
    EUR-Lex's Cellar uses) — confirmed empirically. Degrades to []
    on any failure, same reasoning as `screen_eurlex.py`."""
    try:
        resp = session.get(SPARQL_ENDPOINT, params={
            output_param: accept,
            # A leading/trailing-whitespace query (our own triple-quoted
            # templates always have one) was empirically found to trip
            # this endpoint's WAF into a 403 — stripped defensively.
            "query": query.strip(),
        }, timeout=30)
        resp.raise_for_status()
        return resp.json().get("results", {}).get("bindings", [])
    except (requests.RequestException, ValueError):
        return []


def extract_keyword_snippet(bindings, keyword_stem):
    """Picks the literal object whose text actually contains the search
    stem, for a human-readable preview — falls back to the first literal
    value found if none match exactly (still better than nothing)."""
    stem = keyword_stem.rstrip("*").lower()
    literals = [b["o"]["value"] for b in bindings
                if b.get("o", {}).get("type") in ("literal", "typed-literal")]
    for lit in literals:
        if stem in lit.lower():
            return lit
    return literals[0] if literals else ""


def load_candidates_file():
    if CANDIDATES_PATH.exists():
        with open(CANDIDATES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_candidates_file(data):
    with open(CANDIDATES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)


def find_new_uris(matched_uris, already_reported_uris):
    """Pure, unit-testable: filters out URIs already recorded in a
    previous run's candidates file."""
    return [uri for uri in matched_uris if uri not in already_reported_uris]


def main():
    candidates_file = load_candidates_file()
    previous = candidates_file.get("e-Sbirka", [])
    already_reported = {c["uri"] for c in previous}

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    new_candidates = []
    for idx, keyword in enumerate(HYDROGEN_KEYWORDS):
        if idx > 0:
            time.sleep(SLEEP_SECONDS)
        print(f"=== querying e-Sbirka open data for {keyword!r} ===")
        bindings = run_sparql(session, build_search_query(keyword))
        matched_uris = [b["s"]["value"] for b in bindings]
        new_uris = find_new_uris(matched_uris, already_reported)
        print(f"  {len(matched_uris)} matches, {len(new_uris)} not already reported")

        for uri in new_uris:
            time.sleep(SLEEP_SECONDS)
            snippet_bindings = run_sparql(session, build_snippet_query(uri))
            snippet = extract_keyword_snippet(snippet_bindings, keyword)
            new_candidates.append({
                "uri": uri,
                "snippet": snippet[:300],
                "matched_keyword": keyword,
                "screened_at": datetime.datetime.now().isoformat(timespec="seconds"),
                "note": "unresolved — could not automatically determine which "
                        "law this fragment belongs to, see module docstring",
            })

    candidates_file["e-Sbirka"] = previous + new_candidates
    save_candidates_file(candidates_file)
    print(f"\nWrote {len(new_candidates)} new candidate(s) to "
          f"{CANDIDATES_PATH.relative_to(REPO_ROOT)} under key \"e-Sbirka\" "
          f"({len(previous)} carried over from earlier runs) — every entry needs "
          f"human triage to identify the actual law before anything is fetched.")


if __name__ == "__main__":
    main()
