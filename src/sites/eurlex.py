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
(The full-text download, `resolve_celex()`, 2026-11-20, does resolve them —
through `owl:sameAs` of the Cellar resource URI, and only when Cellar gives
exactly one CELEX number.)
"""
import re
import urllib.parse

import requests

SPARQL_ENDPOINT = "http://publications.europa.eu/webapi/rdf/sparql"
USER_AGENT = "Mozilla/5.0 (compatible; NAHYC-DP004-sites-tool/1.0; +research use, low-volume)"

# The trailing "(NN)" is PART of the CELEX id, not noise: EUR-Lex uses it
# to separate acts that would otherwise share a number. Found 2026-09-16
# on Decision (EU) 2018/546 of the European Central Bank, whose CELEX is
# "32018D0010(01)" — the ECB numbers it ECB/2018/10, and the bare
# "32018D0010" is a completely unrelated COMMISSION decision on Danish
# state aid to Aarhus airport. A "\w+" capture silently dropped the
# suffix and resolved that other act instead, which is how the wrong
# title reached `nazev_autoritativni` for that record.
_CELEX_IN_URL_RE = re.compile(r"CELEX(?::|%3A)(\w+(?:\(\d{2}\))?)", re.IGNORECASE)
# For downloading the text, a consolidated version's date ("02022R0869-20250205")
# is part of the id: without it Cellar has no such document. (The metadata
# functions above deliberately work with the number without the date.)
_CELEX_WITH_DATE_IN_URL_RE = re.compile(r"CELEX(?::|%3A)(\w+(?:\(\d{2}\))?(?:-\d{8})?)", re.IGNORECASE)
_ELI_IN_URL_RE = re.compile(r"/eli/([a-z_]+)/(\d{4})/(\d+)/oj")
_OJ_IN_URL_RE = re.compile(r"uri=OJ:(L_\d+)", re.IGNORECASE)

# doc/PLAN.md §16, 2026-09-16 ("Gestor" correctness finding): top-level
# EU institution corporate-body codes, distinguished from Directorate-
# General codes (ENER, MOVE, ENV, GROW, ...) — both shapes appear
# interchangeably as `cdm:work_created_by_agent` values in Cellar (a
# Commission-only implementing act was found putting its DG there too,
# not just in `cdm:resource_legal_responsibility_of_agent`), so this set
# is what lets `fetch_responsible_gestor()` tell the two apart.
_INSTITUTION_CODES_CS = {
    "COM": "Evropská komise",
    "EP": "Evropský parlament",
    "CONSIL": "Rada Evropské unie",
    "ECB": "Evropská centrální banka",
}

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


def resource_uris_from_text(text):
    """Like `resource_uri_from_url()`, but returns every candidate found
    in `text`, in order — needed because a few `Document.url` values in
    this corpus concatenate more than one URL (a known Excel-paste
    artifact, same pattern `fetch_fulltext.py`'s `first_url()` already
    works around elsewhere), and the FIRST one isn't always the one
    Cellar has an `owl:sameAs` record for (e.g. a consolidated-text CELEX
    variant, sector "0", pasted before the original act's own sector-"3"
    CELEX)."""
    if not text:
        return []
    uris = []
    for m in _CELEX_IN_URL_RE.finditer(text):
        uris.append(f"http://publications.europa.eu/resource/celex/{m.group(1).upper()}")
    for m in _ELI_IN_URL_RE.finditer(text):
        uris.append(f"http://publications.europa.eu/resource/eli/{m.group(1)}/{m.group(2)}/{m.group(3)}/oj")
    for m in _OJ_IN_URL_RE.finditer(text):
        uris.append(f"http://publications.europa.eu/resource/oj/{m.group(1)}")
    return uris


_TYPE_LETTER_BY_DOCUMENT_TYPE = {
    "Nařízení EU": "R",
    "Směrnice EU": "L",
    "Rozhodnutí EU": "D",
}

_ELI_TYPE_BY_DOCUMENT_TYPE = {
    "Nařízení EU": "reg",
    "Směrnice EU": "dir",
    "Rozhodnutí EU": "dec",
}

# The sequence number side allows a single digit ("Directive 2006/7/EC",
# the real Bathing Water Directive) — found live, doc/PLAN.md §38: a
# `{2,4}` minimum on both sides silently failed to match this and any
# other single-digit-numbered act at all.
_YEAR_NUMBER_RE = re.compile(r"(\d{2,4})\s*/\s*(\d{1,4})")


def _plausible_year(n):
    return 1957 <= n <= 2035


def celex_candidates_from_designation(text, type_name):
    """Constructs candidate CELEX ids from a free-text designation (an
    `identifier` like "(EU) 2022/869", or — when that's blank, e.g. a
    slov-lex.sk-only record with no stable identifier — the act's number
    as it appears in the document's own title) plus its `DocumentType`
    name. Genuinely ambiguous whether the "YYYY/NNN" pair is
    (year, sequence-number) — the EU's numbering convention flipped this
    ordering by act type and era (pre-2015 regulations were
    "No NNN/YYYY", directives and post-2015 acts are "YYYY/NNNN") — so
    both orderings are returned as candidates when both numbers could
    plausibly be a year; the caller tries each against Cellar rather than
    this function guessing. Returns [] for a type with no CELEX letter
    mapping or a designation with no digit pair at all."""
    type_letter = _TYPE_LETTER_BY_DOCUMENT_TYPE.get(type_name)
    if not type_letter:
        return []
    m = _YEAR_NUMBER_RE.search(text or "")
    if not m:
        return []
    a, b = int(m.group(1)), int(m.group(2))
    candidates = []
    if _plausible_year(a):
        candidates.append(f"3{a}{type_letter}{b:04d}")
    if _plausible_year(b) and b != a:
        candidates.append(f"3{b}{type_letter}{a:04d}")
    return [f"http://publications.europa.eu/resource/celex/{c}" for c in candidates]


def eli_candidates_from_designation(text, type_name):
    """Same idea as `celex_candidates_from_designation()`, but building
    the act's ELI instead. Needed because Cellar does not index every act
    under the CELEX id its own stored URL carries: Decision (EU) 2018/546
    of the ECB is reachable as `eli/dec/2018/546/oj` but not as
    `celex/32018D0010(01)`, even though that is its CELEX. Only the
    year-first reading is offered here — ELI always orders the path as
    year/number, so unlike CELEX there is nothing to disambiguate."""
    eli_type = _ELI_TYPE_BY_DOCUMENT_TYPE.get(type_name)
    if not eli_type:
        return []
    m = _YEAR_NUMBER_RE.search(text or "")
    if not m:
        return []
    candidates = []
    for year, number in ((m.group(1), m.group(2)), (m.group(2), m.group(1))):
        if _plausible_year(int(year)):
            candidates.append(
                f"http://publications.europa.eu/resource/eli/{eli_type}/{int(year)}/{int(number)}/oj")
    return candidates


def resource_uri_from_url(url):
    """First Cellar resource URI `resource_uris_from_text()` finds in
    `url` (a stored `Document.url` normally carries just one), or None."""
    uris = resource_uris_from_text(url)
    return uris[0] if uris else None


_ELI_SAMEAS_TITLE_QUERY_TEMPLATE = """
PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
SELECT ?title ?lang WHERE {{
  ?work owl:sameAs <{resource_uri}> .
  ?expr cdm:expression_belongs_to_work ?work .
  ?expr cdm:expression_uses_language ?langres .
  ?expr cdm:expression_title ?title .
  BIND(STRAFTER(STR(?langres), "/language/") AS ?lang)
  FILTER(?lang IN ("CES", "ENG"))
}}
"""


def _title_from_resource_uri(session, resource_uri):
    bindings = _run_sparql(session, _ELI_SAMEAS_TITLE_QUERY_TEMPLATE.format(resource_uri=resource_uri))
    by_lang = {b["lang"]["value"]: b["title"]["value"] for b in bindings if "lang" in b and "title" in b}
    return by_lang.get("CES") or by_lang.get("ENG")


def resolve_eu_act_by_designation(text, type_name, session=None):
    """doc/PLAN.md §38, 2026-09-18: resolves a verified title + public
    eur-lex.europa.eu URL for an EU act known only from free citation text
    (a national law's own EU-transposition footnote/annex — e.g. "Směrnice
    Evropského parlamentu a Rady 2011/92/EU ze dne 13. prosince 2011 o
    posuzování ..."), not a stored corpus URL. Tries every candidate
    `eli_candidates_from_designation()` returns (both digit orderings —
    pre-2015 regulations are cited "č./No NNN/YYYY" while directives and
    post-2015 acts use "YYYY/NNNN") against Cellar via `owl:sameAs`,
    returning the first that resolves to a real title. None if nothing
    resolves — never guessed, never falls back to constructing a URL
    that was never actually confirmed to exist.

    Falls back to CELEX candidates (`celex_candidates_from_designation()`)
    when no ELI candidate resolves: found live, doc/PLAN.md §38 — several
    older Decisions (e.g. 2002/159/EC) have no `owl:sameAs` record at all
    under their ELI resource URI in Cellar, only under their CELEX one."""
    session = session or requests.Session()
    session.headers.setdefault("User-Agent", USER_AGENT)
    for resource_uri in eli_candidates_from_designation(text, type_name):
        title = _title_from_resource_uri(session, resource_uri)
        if title:
            public_url = resource_uri.replace(
                "http://publications.europa.eu/resource/eli/",
                "https://eur-lex.europa.eu/eli/")
            return {"title": title, "url": public_url}
    for resource_uri in celex_candidates_from_designation(text, type_name):
        title = _title_from_resource_uri(session, resource_uri)
        if title:
            celex = resource_uri.rsplit("/", 1)[-1]
            public_url = f"https://eur-lex.europa.eu/legal-content/CS/TXT/?uri=CELEX:{celex}"
            return {"title": title, "url": public_url}
    return None


_GESTOR_QUERY_TEMPLATE = """
PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
SELECT DISTINCT ?dg ?agent WHERE {{
  ?work owl:sameAs <{resource_uri}> .
  OPTIONAL {{ ?work cdm:resource_legal_responsibility_of_agent ?dg }}
  OPTIONAL {{ ?work cdm:work_created_by_agent ?agent }}
}}
"""

_LABEL_QUERY_TEMPLATE = """
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT ?label ?lang WHERE {{
  <{resource_uri}> skos:prefLabel ?label .
  BIND(LANG(?label) AS ?lang)
  FILTER(?lang IN ("cs", "en"))
}}
"""

_CORPORATE_BODY_PREFIX = "http://publications.europa.eu/resource/authority/corporate-body/"


def _corporate_body_label(session, code):
    bindings = _run_sparql(session, _LABEL_QUERY_TEMPLATE.format(
        resource_uri=_CORPORATE_BODY_PREFIX + code))
    by_lang = {b["lang"]["value"]: b["label"]["value"] for b in bindings if "lang" in b and "label" in b}
    return by_lang.get("cs") or by_lang.get("en") or code


def _gestor_from_resource_uri(session, resource_uri):
    """(dg_label_or_None, resolved_bool) for one Cellar resource URI —
    resolved=False means the URI itself matched no `owl:sameAs` work at
    all (caller should try the next candidate), which is different from
    a real work that simply carries neither signal."""
    bindings = _run_sparql(session, _GESTOR_QUERY_TEMPLATE.format(resource_uri=resource_uri))
    if not bindings:
        return None, False

    def code_of(uri):
        return uri.rsplit("/", 1)[-1]

    dg_codes = {code_of(b["dg"]["value"]) for b in bindings if "dg" in b}
    agent_codes = {code_of(b["agent"]["value"]) for b in bindings if "agent" in b}
    dg_codes |= {c for c in agent_codes if c not in _INSTITUTION_CODES_CS}

    if dg_codes:
        return _corporate_body_label(session, sorted(dg_codes)[0]), True

    institution_codes = agent_codes & set(_INSTITUTION_CODES_CS)
    if not institution_codes:
        return None, True
    if institution_codes == {"EP", "CONSIL"}:
        return "Evropský parlament a Rada Evropské unie", True
    return _INSTITUTION_CODES_CS[sorted(institution_codes)[0]], True


def fetch_responsible_gestor(url, identifier=None, title=None, type_name=None, session=None):
    """Returns the single Czech-language institution/Directorate-General
    name responsible for the EU act identified by `url` (and, as a
    fallback when `url` carries no resolvable EUR-Lex/Cellar reference —
    a slov-lex.sk-only mirror, or a URL Cellar has no record for —
    `identifier`/`title` + `type_name` to construct a candidate CELEX id;
    see `celex_candidates_from_designation()`), or None if nothing
    resolves. Per doc/PLAN.md §16 (2026-09-16 user decision): DG when the
    authoritative data has one, else the enacting top-level institution.

    Priority per resolved work: `cdm:resource_legal_responsibility_of_agent`
    (the DG Cellar itself calls "responsible") first; else any
    `cdm:work_created_by_agent` value that ISN'T one of the top-level
    institution codes (a Commission-only implementing act was found
    carrying its DG only there); else the enacting institution(s) from
    `work_created_by_agent` (typically "Evropská komise" alone for a
    delegated/implementing act, or "Evropský parlament a Rada Evropské
    unie" for a co-decided one)."""
    session = session or requests.Session()
    session.headers.setdefault("User-Agent", USER_AGENT)

    candidates = resource_uris_from_text(url)
    for text in (identifier, title):
        if text:
            candidates += celex_candidates_from_designation(text, type_name)
            candidates += eli_candidates_from_designation(text, type_name)

    for resource_uri in candidates:
        label, resolved = _gestor_from_resource_uri(session, resource_uri)
        if resolved:
            return label
    return None


# --- The text of an act from Cellar (doc/MPO_PRIPOMINKY.md, 2026-11-19) ------
# EUR-Lex answers automated clients with a firewall challenge (HTTP 202); the
# Publications Office's own repository, Cellar, serves the same documents to
# any client by content negotiation on the work's CELEX URI. The language is
# negotiated with Accept-Language (ISO 639-2/B code), the format with Accept.
# A work with several items (an act and its annexes in separate files) answers
# 300 with a list of them; the main document is always `DOC_1`.
CELLAR_CELEX_URI = "http://publications.europa.eu/resource/celex/{celex}"
_LANGUAGE_IN_URL_RE = re.compile(r"/legal-content/([A-Z]{2})/")
_ELI_LANGUAGE_RE = re.compile(r"/eli/.+/oj/([a-z]{3})(?:[/?#]|$)")
_CELLAR_LANGUAGES = {"CS": "ces", "SK": "slk", "EN": "eng", "DE": "deu", "PL": "pol", "FR": "fra"}
_MAIN_ITEM_RE = re.compile(r'href="(http://publications\.europa\.eu/resource/cellar/[^"]+/DOC_1)"')
_ITEM_RE = re.compile(r'href="http://publications\.europa\.eu/resource/cellar/[^"]+/(DOC_\d+)"')
HTML_FORMATS = ("application/xhtml+xml", "text/html")
# Cellar files the PDF of an act under one of these profiles (PDF/A-1a for most acts);
# a plain `application/pdf` is the last resort — it is how Cellar serves e.g. the
# Czech special edition of an act from before 2004 (1999/92/ES), under no profile.
PDF_FORMATS = ("application/pdf;type=pdfa1a", "application/pdf;type=pdf1x", "application/pdf;type=pdfa2a",
               "application/pdf;type=pdfa1b", "application/pdf;type=pdfx", "application/pdf")


def cellar_language(url):
    """The Cellar language code of the EUR-Lex address `url`: its `legal-content/XX/`
    segment or the language of its ELI (`.../oj/ces`); English when it names none
    (what EUR-Lex itself serves then)."""
    m = _LANGUAGE_IN_URL_RE.search(url or "")
    if m and m.group(1) in _CELLAR_LANGUAGES:
        return _CELLAR_LANGUAGES[m.group(1)]
    m = _ELI_LANGUAGE_RE.search(url or "")
    return m.group(1) if m else "eng"


_RESOURCE_CELEX_QUERY_TEMPLATE = """
PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
SELECT DISTINCT ?celex WHERE {{
  ?work owl:sameAs <{resource_uri}> .
  ?work cdm:resource_legal_id_celex ?celex .
}}
"""


def celex_of_resource(resource_uri, session=None):
    """The CELEX number of the work Cellar knows as `resource_uri` (an ELI
    `http://publications.europa.eu/resource/eli/reg/2018/858/oj` or an Official
    Journal act `http://publications.europa.eu/resource/oj/L_202302413`), or None
    when Cellar has no such work or gives more than one number (never guessed)."""
    session = session or requests.Session()
    session.headers.setdefault("User-Agent", USER_AGENT)
    bindings = _run_sparql(session, _RESOURCE_CELEX_QUERY_TEMPLATE.format(resource_uri=resource_uri))
    numbers = {b["celex"]["value"] for b in bindings if "celex" in b}
    # a consolidated version (sector 0) is a different text than the act itself
    numbers = {n for n in numbers if not n.startswith("0")} or numbers
    return numbers.pop() if len(numbers) == 1 else None


_CELEX_LETTER_BY_ELI_TYPE = {"reg": "R", "reg_impl": "R", "reg_del": "R",
                             "dir": "L", "dir_impl": "L", "dir_del": "L",
                             "dec": "D", "dec_impl": "D", "dec_del": "D"}


def _celex_of_eli_by_number(eli_type, year, number, session=None):
    """The CELEX number an ELI must have (`reg/2021/535` -> 32021R0535), for a
    work Cellar has not linked to its ELI (Regulation (EU) 2021/535, found
    2026-11-20) — accepted only when Cellar's title of that CELEX names the
    act's number `year/number`; else None."""
    letter = _CELEX_LETTER_BY_ELI_TYPE.get(eli_type)
    if not letter:
        return None
    celex = f"3{year}{letter}{int(number):04d}"
    session = session or requests.Session()
    session.headers.setdefault("User-Agent", USER_AGENT)
    bindings = _run_sparql(session, _TITLE_QUERY_TEMPLATE.format(celex=celex))
    titles = [b["title"]["value"] for b in bindings if "title" in b]
    return celex if any(f"{year}/{int(number)}" in title for title in titles) else None


def resolve_celex(url, session=None):
    """The CELEX number of the act the EUR-Lex address `url` names: the number in
    the address itself, else the one Cellar gives for its ELI (`/eli/reg/2018/858/oj`)
    or its Official Journal id (`?uri=OJ:L_202302413`). None for anything else —
    e.g. `?uri=OJ:L:2014:096:FULL`, a whole issue of the Journal, not one act."""
    m = _CELEX_WITH_DATE_IN_URL_RE.search(url or "")
    if m:
        return m.group(1)
    m = _ELI_IN_URL_RE.search(url or "")
    if m:
        return (celex_of_resource(
            f"http://publications.europa.eu/resource/eli/{m.group(1)}/{m.group(2)}/{m.group(3)}/oj", session)
            or _celex_of_eli_by_number(m.group(1), m.group(2), m.group(3), session))
    m = _OJ_IN_URL_RE.search(url or "")
    if m:
        return celex_of_resource(f"http://publications.europa.eu/resource/oj/{m.group(1)}", session)
    return None


def wants_pdf(url):
    """True for an EUR-Lex address of a PDF (`.../TXT/PDF/?uri=...`)."""
    return "/TXT/PDF/" in (url or "")


def fetch_cellar(url, session=None, timeout=60):
    """The document the EUR-Lex address `url` names, downloaded from Cellar by
    content negotiation in the language of the address — a PDF for a `TXT/PDF`
    address, else XHTML (or HTML) — as a dict `status`, `content`, `content_type`,
    `celex`, `items` (how many files the manifestation has: an act whose annexes
    are separate files has more than one, and only `DOC_1`, the main one, is
    returned). None when the address names no act Cellar can identify, or Cellar
    has no manifestation of it in that language and format. EUR-Lex itself is
    never contacted."""
    session = session or requests.Session()
    celex = resolve_celex(url, session)
    if not celex:
        return None
    formats = PDF_FORMATS if wants_pdf(url) else HTML_FORMATS
    headers = {"Accept-Language": cellar_language(url), "User-Agent": USER_AGENT}
    for accept in formats:
        items = 1
        try:
            resp = session.get(CELLAR_CELEX_URI.format(celex=urllib.parse.quote(celex, safe="")), timeout=timeout,
                               headers={**headers, "Accept": accept})
            if resp.status_code == 300:
                listed = _MAIN_ITEM_RE.findall(resp.text)
                items = len(set(_ITEM_RE.findall(resp.text))) or 1
                if not listed:
                    continue
                resp = session.get(listed[0], timeout=timeout, headers={**headers, "Accept": accept})
        except requests.RequestException:
            continue
        if resp.status_code == 200 and resp.content:
            return {"status": resp.status_code, "content": resp.content,
                    "content_type": resp.headers.get("Content-Type", accept), "celex": celex, "items": items}
    return None


def fetch_cellar_document(url, session=None, timeout=60):
    """(status, content, content type) of `fetch_cellar()`, or None."""
    found = fetch_cellar(url, session, timeout)
    return (found["status"], found["content"], found["content_type"]) if found else None
