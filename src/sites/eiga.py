"""Resolves an EIGA (European Industrial Gases Association) publication
code to its entry in the eiga.eu publications listing and extracts its
title and scope text.

doc/PLAN.md §24, 2026-09-17: like `normoff.py`, the corpus does NOT store
a per-document URL for these records — every one of them shares the
`https://www.eiga.eu/` homepage as its `url` — so this module adds a
`resolve()` step in front of the usual `extract()`.

Unlike `normoff.py`'s registry, there is no separate detail page: the
listing itself (`GET /publications/?_sf_s=<digits>`) already carries each
result's scope text, in a "READ MORE" `<div>` that is present in the raw
HTML (not JS-rendered — the site just hides it with inline `display:none`
until clicked). Getting to that query took two failed approaches first,
recorded here because the failure mode is worth knowing about for the
next domain: the site's own `<form>` markup advertises `_sf_search[]`/
`_sft_ct_doc_cats[]` fields (Search & Filter Pro's default naming), and
even its own documented AJAX endpoint
(`?sfid=1550&sf_action=get_data&sf_data=results`) — both accepted, both
returned HTTP 200, and both silently ignored the query and returned the
unfiltered default listing. The parameter that actually filters,
`_sf_s=<digits>` on `/publications/` directly, was found by the user, not
by reading the page's own form markup.

The site's own search is minimum-3-digits and, below that or for a
number with no current match, returns unrelated fuzzy full-text hits
rather than nothing (confirmed live 2026-09-17: querying "100" returned
10 unrelated documents; "121" — a corpus designation with no current
match — returned 2 unrelated ones). Trusting "the first result" would
therefore silently attach the wrong document's description to the wrong
record. `extract()` guards against this by verifying the result's OWN
leading number, parsed from its title, against the query digits embedded
in the URL itself — never guessed, never "close enough".
"""
import io
import re
import urllib.parse

import pdfplumber
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.eiga.eu"
PUBLICATIONS_URL = f"{BASE_URL}/publications/"
USER_AGENT = ("Mozilla/5.0 (compatible; NAHYC-DP004-sites-tool/1.0; "
              "+research use, low-volume)")

# Below this many digits, or for a number with no current document, the
# site returns fuzzy full-text matches instead of nothing (site's own
# help text: "type three digits") — a query this short is certain to be
# useless, so resolve() skips the request entirely rather than relying
# purely on extract()'s exact-match verification to catch it.
MIN_QUERY_DIGITS = 3

# A PDF-extracted lead shorter than this is a cover-page fragment
# ("EIGA", a logo caption, a revision date), not real scope text.
MIN_PDF_LEAD_LENGTH = 40

_PREFIX_WORDS_RE = re.compile(r"\b(?:EIGA|IGC)\b", re.IGNORECASE)
_CODE_RE = re.compile(r"(\d+)")
_TITLE_NUMBER_RE = re.compile(r"^\D*(\d+)\s*/")


def _session(session=None):
    session = session or requests.Session()
    session.headers.setdefault("User-Agent", USER_AGENT)
    return session


def normalize_designation(znacka):
    """"EIGA DOC 246" -> "246", "EIGA IGC Doc 100/20" -> "100". Strips
    only the corpus's own EIGA/IGC label words — "Doc"/"DOC"/"TB"/"PP"/
    etc. are the document TYPE, kept as part of the site's own title, not
    stripped — and returns the first digit run found (the site's own
    numbering convention, confirmed live: "DOC 246 / 23", "TB 33 / 19").
    Returns None when no digit run is found at all (e.g. a blank
    designation) — never guessed at."""
    text = _PREFIX_WORDS_RE.sub(" ", znacka or "")
    m = _CODE_RE.search(text)
    return m.group(1) if m else None


def build_search_url(code):
    return f"{PUBLICATIONS_URL}?{urllib.parse.urlencode({'_sf_s': code})}"


def resolve(designation, session=None):
    """{"code", "url"} for `designation`'s normalized code, or None when
    it has no digit run at all or is too short for the site's own search
    to do anything but return noise (see MIN_QUERY_DIGITS). Pure — makes
    no request itself; `extract()` does the actual fetch+verify against
    the URL this returns."""
    code = normalize_designation(designation)
    if code is None or len(code) < MIN_QUERY_DIGITS:
        return None
    return {"code": code, "url": build_search_url(code)}


def _parse_results(html):
    """Every `.list-item` on a publications page as (title, description,
    pdf_url) — `description` is the "READ MORE" text when present (None
    otherwise), `pdf_url` is the download link, absolute. [] if the page
    has no results at all."""
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for item in soup.select(".list-item"):
        title_el = item.select_one(".list-title")
        if not title_el:
            continue
        title = re.sub(r"\s+", " ", title_el.get_text(" ", strip=True)).strip()

        description = None
        desc_el = item.select_one("div[id^='content']")
        if desc_el:
            text = re.sub(r"\s+", " ", desc_el.get_text(" ", strip=True)).strip()
            description = text or None

        pdf_url = None
        pdf_el = item.select_one("a.list-download")
        if pdf_el and pdf_el.get("href"):
            pdf_url = urllib.parse.urljoin(BASE_URL, pdf_el["href"])

        items.append((title, description, pdf_url))
    return items


def _query_digits_from_url(url):
    params = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    values = params.get("_sf_s")
    return values[0] if values else None


def _select_exact_match(items, code):
    """The one item whose title's OWN leading number equals `code`
    exactly, or None if that isn't exactly one item — a page with a
    single result is trusted outright (the common case: the query
    matched precisely one current document); a page with several is only
    trusted if exactly one of them actually carries this code, never the
    first/best-looking one."""
    if len(items) == 1:
        return items[0]
    exact = [item for item in items
             for m in [_TITLE_NUMBER_RE.match(item[0])]
             if m and m.group(1) == code]
    return exact[0] if len(exact) == 1 else None


def _extract_pdf_lead(pdf_url, session):
    """Best-effort lead paragraph from a PDF's first page — fallback for
    the rare listing entry with no visible "READ MORE" text. Many EIGA
    PDFs' first page is a cover/title page with little real prose, so
    this legitimately returns None often; never raises."""
    try:
        response = session.get(pdf_url, timeout=30)
        response.raise_for_status()
    except requests.RequestException:
        return None
    try:
        with pdfplumber.open(io.BytesIO(response.content)) as pdf:
            if not pdf.pages:
                return None
            text = pdf.pages[0].extract_text() or ""
    except Exception:
        return None
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) >= MIN_PDF_LEAD_LENGTH else None


def extract(url, cached_path=None, session=None):
    """Returns {"title": str, "description": str|None} for a
    `resolve()`-built search URL, or None if nothing on the page matches
    it exactly. `cached_path` is accepted for interface consistency with
    the other site modules and is honoured when given."""
    html = None
    if cached_path:
        try:
            with open(cached_path, "r", encoding="utf-8", errors="replace") as f:
                html = f.read()
        except OSError:
            html = None

    session = _session(session)
    if html is None:
        try:
            response = session.get(url, timeout=30)
            response.raise_for_status()
            html = response.text
        except requests.RequestException:
            return None

    items = _parse_results(html)
    if not items:
        return None

    code = _query_digits_from_url(url)
    match = _select_exact_match(items, code) if code else None
    if match is None:
        return None
    title, description, pdf_url = match
    if not title:
        return None
    if description is None and pdf_url:
        description = _extract_pdf_lead(pdf_url, session)
    return {"title": title, "description": description}


def fetch_by_designation(designation, session=None):
    """Convenience for the orchestrator: resolve + extract in one call.
    Returns the `extract()` dict with the resolved URL folded in, or
    None if either step fails."""
    session = _session(session)
    entry = resolve(designation, session=session)
    if entry is None:
        return None
    result = extract(entry["url"], session=session)
    if result is None:
        return None
    result["url"] = entry["url"]
    return result
