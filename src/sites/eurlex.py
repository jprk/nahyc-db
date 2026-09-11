"""Fetches an EU act's authoritative title directly from the EUR-Lex
Cellar SPARQL endpoint — the same public, unauthenticated service
`src/tools/screen_eurlex.py` already queries to screen for NEW candidates.
Reused here for a different purpose: resolving the canonical title for a
record we already have in the corpus, not discovering new ones.

doc/PLAN.md §8, 2026-09-11: part of the authoritative per-site
title/description extraction feature — see `src/tools/
fetch_authoritative_metadata.py` for the orchestrator that calls this.

Scope, honestly bounded: only extracts a CELEX id from a URL that already
carries one EXPLICITLY (`?uri=CELEX:32014R1300` style, confirmed the
majority shape for `Haltuf_Dokumenty`'s stored `eur-lex.europa.eu` links).
ELI-style URLs (`.../eli/dir/2019/692/oj`) and bare Official-Journal
references (`?uri=OJ:L_202302413`) are NOT resolved by this module — no
verified, non-guessing SPARQL path from those shapes to a CELEX id was
found; `extract()` returns None for them rather than guessing one.
"""
import re

import requests

SPARQL_ENDPOINT = "http://publications.europa.eu/webapi/rdf/sparql"
USER_AGENT = "Mozilla/5.0 (compatible; NAHYC-DP004-sites-tool/1.0; +research use, low-volume)"

_CELEX_IN_URL_RE = re.compile(r"CELEX(?::|%3A)(\w+)", re.IGNORECASE)

# Prefers the Czech-language expression title, falling back to English --
# this corpus is Czech-oriented, but not every EU act has a Czech
# expression indexed in Cellar. The "^^xsd:string" datatype annotation on
# the CELEX literal is NOT cosmetic -- found by testing against the real
# endpoint: a plain, untyped string literal silently matches nothing, even
# for a CELEX id confirmed to exist via a keyword search (this endpoint's
# celex property is itself typed xsd:string in the graph, and its
# Virtuoso-backed literal comparison apparently requires the query side to
# match that type explicitly).
_TITLE_QUERY_TEMPLATE = """
PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT ?title ?lang WHERE {{
  ?work cdm:resource_legal_id_celex "{celex}"^^xsd:string .
  ?expr cdm:expression_belongs_to_work ?work .
  ?expr cdm:expression_uses_language ?langres .
  ?expr cdm:expression_title ?title .
  BIND(STRAFTER(STR(?langres), "/language/") AS ?lang)
  FILTER(?lang IN ("CES", "ENG"))
}}
"""


def celex_from_url(url):
    """Extracts a CELEX id from a "?uri=CELEX:..." (or URL-encoded
    "CELEX%3A...") style EUR-Lex URL, or None if the URL doesn't carry one
    explicitly -- see module docstring for the shapes deliberately left
    unresolved."""
    if not url:
        return None
    m = _CELEX_IN_URL_RE.search(url)
    return m.group(1) if m else None


def _run_sparql(session, query):
    """Executes a SPARQL query against the Cellar endpoint. Returns the
    parsed `results.bindings` list, or [] on any failure -- degrades
    gracefully, same convention as screen_eurlex.py's own run_sparql()."""
    try:
        resp = session.get(SPARQL_ENDPOINT, params={
            "format": "application/sparql-results+json",
            "query": query.strip(),
        }, timeout=30)
        resp.raise_for_status()
        return resp.json().get("results", {}).get("bindings", [])
    except (requests.RequestException, ValueError):
        return []


def extract(url, cached_path=None, session=None):
    """Returns {"title": str, "description": None} for a CELEX-bearing
    EUR-Lex URL (preferring the Czech expression title, else English), or
    None if no CELEX id could be extracted from the URL or the endpoint
    returned nothing. `cached_path` is accepted only for interface
    consistency with the other src/sites modules -- unused here, since
    this is a live structured-data query (SPARQL), not an HTML page parse,
    so there's no local file to read instead. No description is available
    from this source (Cellar's bibliographic metadata doesn't carry a
    free-text abstract) -- title-only is still a real improvement over
    today's spreadsheet-derived title."""
    celex = celex_from_url(url)
    if not celex:
        return None
    session = session or requests.Session()
    session.headers.setdefault("User-Agent", USER_AGENT)
    bindings = _run_sparql(session, _TITLE_QUERY_TEMPLATE.format(celex=celex))
    if not bindings:
        return None
    by_lang = {b["lang"]["value"]: b["title"]["value"] for b in bindings if "lang" in b and "title" in b}
    title = by_lang.get("CES") or by_lang.get("ENG")
    if not title:
        return None
    return {"title": title, "description": None}
