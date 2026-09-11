"""Verifies a Czech law's official citation against the e-Sbírka Linked
Open Data endpoint and returns the canonical GOVERNMENT-hosted reference
URL for it.

doc/PLAN.md §8, 2026-09-11: `e-sbirka.gov.cz` is the actual official
"single point of authority" for Czech legislation — unlike
`zakonyprolidi.cz` (a private third-party mirror, see `src/sites/
zakonyprolidi.py`), which is where the real title/description TEXT
extraction still comes from. e-Sbírka itself doesn't support that today:
its own frontend (`https://e-sbirka.gov.cz/sb/{year}/{number}`) is an
unscrapeable Angular SPA (a plain GET returns only an empty `<esel-app>`
shell, confirmed live 2026-09-11), and its REST API (`sbr-externi`, see
`https://e-sbirka.gov.cz/assets/configs/env.js`) requires a
Ministry-of-Interior data-box client registration this project doesn't
have (already documented in `src/tools/screen_esbirka.py`). Its public,
unauthenticated LOD SPARQL endpoint (the same one `screen_esbirka.py`
already uses) DOES expose a per-law node, addressable by ELI and
constructible directly from a znacka — but traced several levels into its
`slovník.gov.cz/datový/sbírka` graph and confirmed (2026-09-11) that the
actual title text lives nowhere as a simple field: the graph is
structured at the individual-paragraph-fragment level (hundreds of nodes
per law), not as a document-metadata record. So this module is,
deliberately, a VERIFICATION step only: it confirms the expected citation
really exists at that ELI node, then returns the human-facing
`e-sbirka.gov.cz` URL as the recorded authoritative reference —
`fetch_authoritative_metadata.py` attaches this as `zdroj_esbirka_url`
alongside the zakonyprolidi.cz-sourced title/description, never in place
of it.

**Future migration path (not built — no API key available yet):** once a
registered e-Sbírka REST API key is obtained, this module is the natural
place to extend into a full title/description SOURCE, replacing
`zakonyprolidi.py`'s content-extraction role for Czech laws — see the
`REST_API_TODO` note below. Keep the same `{"title", "description"}`
return shape if/when that happens, so `fetch_authoritative_metadata.py`'s
dispatch logic doesn't need to change.
"""
import re

import requests

SPARQL_ENDPOINT = "https://opendata.eselpoint.gov.cz/sparql"
USER_AGENT = "Mozilla/5.0 (compatible; NAHYC-DP004-sites-tool/1.0; +research use, low-volume)"

# REST_API_TODO: swap this module to call e-Sbírka's own REST API
# (`sbr-externi`) directly for title/description once a data-box client
# registration is obtained — see module docstring.

_ZNACKA_RE = re.compile(r"(\d+)\s*/\s*(\d{4})\s*Sb\.?", re.IGNORECASE)
_CITACE_PREDICATE = "https://slovník.gov.cz/datový/sbírka/pojem/citace-právního-aktu"

_VERIFY_QUERY_TEMPLATE = """
SELECT ?citace WHERE {{
  <{eli}> <%s> ?citace .
}}
""" % _CITACE_PREDICATE


def eli_from_znacka(znacka):
    """Constructs the e-Sbírka LOD ELI URI from a Czech law znacka like
    "283/2021 Sb." — returns None for anything that doesn't match this
    shape (e.g. EU acts, technical standards, Slovak law "Z. z." refs)."""
    if not znacka:
        return None
    m = _ZNACKA_RE.search(znacka)
    if not m:
        return None
    number, year = m.group(1), m.group(2)
    return f"https://opendata.eselpoint.gov.cz/esel-esb/eli/cz/sb/{year}/{number}"


def reference_url_from_znacka(znacka):
    """The human-facing e-sbirka.gov.cz URL for this law, or None if
    znacka doesn't parse as a Czech law citation."""
    if not znacka:
        return None
    m = _ZNACKA_RE.search(znacka)
    if not m:
        return None
    number, year = m.group(1), m.group(2)
    return f"https://e-sbirka.gov.cz/sb/{year}/{number}"


def _normalize_citation(text):
    return re.sub(r"\s+", " ", text or "").strip().lower()


def _run_sparql(session, query):
    try:
        resp = session.get(SPARQL_ENDPOINT, params={
            "output": "application/sparql-results+json",
            "query": query.strip(),
        }, timeout=30)
        resp.raise_for_status()
        return resp.json().get("results", {}).get("bindings", [])
    except (requests.RequestException, ValueError):
        return []


def verify(znacka, session=None):
    """Queries the e-Sbírka LOD endpoint to confirm this znacka's ELI node
    exists and carries the matching citation. Returns the human-facing
    e-sbirka.gov.cz reference URL if confirmed, or None if znacka doesn't
    parse as a Czech law, the ELI node doesn't exist, or its citation
    doesn't match — never guessed, never returned unconfirmed."""
    eli = eli_from_znacka(znacka)
    if not eli:
        return None
    session = session or requests.Session()
    session.headers.setdefault("User-Agent", USER_AGENT)
    bindings = _run_sparql(session, _VERIFY_QUERY_TEMPLATE.format(eli=eli))
    citace_values = {b["citace"]["value"] for b in bindings if "citace" in b}
    if not any(_normalize_citation(c) == _normalize_citation(znacka) for c in citace_values):
        return None
    return reference_url_from_znacka(znacka)
