"""Resolves a Slovak technical standard's designation to its record in the
ÚNMS SR registry (`normy.normoff.gov.sk`) and extracts the published
scope text ("Predmet normy").

doc/PLAN.md §17, 2026-09-16: unlike the other `src/sites/` modules, the
corpus does NOT store a per-document URL for these records — all 101 of
them share the catalog root `https://normy.normoff.gov.sk/`, so there is
nothing to fetch directly. This module therefore adds a `resolve()` step
in front of the usual `extract()`: designation -> catalogue entry -> detail
page. That is the "search the site by designation" mechanism doc/PLAN.md
§8 deferred as "a substantially bigger, differently-shaped undertaking",
implemented here for its highest-yield single domain.

Two requests per designation, both cheap and deterministic:

1. `/vyhladavanie-export/?name=<designation>` returns a small CSV of every
   edition of that designation (catalogue number, title, issue date,
   withdrawal date, detail URL). Used in preference to scraping the HTML
   result list: it is structured, stable, and the site offers it itself.
2. `/norma/<catalogue number>/` is the detail page carrying the scope.

Edition choice follows the same rule `check_csn_validity.find_best_match()`
already applies to the Czech registry: prefer the edition that is still in
force, otherwise the most recently issued one. Here "in force" is an
empty `Dátum zrušenia` (withdrawal date) — a data field, not a rendered
label, so no HTML parsing is involved in the decision.

Never guesses: only an EXACT designation match counts (the registry
happily returns near misses for a partial designation), and a record whose
scope cell is empty yields `None` rather than whatever text happens to sit
nearby — an early version of this module silently extracted the page's
"Hore" ("back to top") link that way.
"""
import csv
import io
import re

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://normy.normoff.gov.sk"
EXPORT_URL = f"{BASE_URL}/vyhladavanie-export/"
USER_AGENT = ("Mozilla/5.0 (compatible; NAHYC-DP004-sites-tool/1.0; "
              "+research use, low-volume)")

# CSV column headings as the registry emits them (UTF-8 BOM, ";" separated).
_COL_CATALOGUE = "Katalógové číslo"
_COL_DESIGNATION = "Označenie"
_COL_TITLE = "Názov normy"
_COL_ISSUED = "Dátum vydania"
_COL_WITHDRAWN = "Dátum zrušenia"
_COL_URL = "URL"

_SCOPE_LABEL = "Predmet normy:"
_SK_TITLE_LABEL = "Slovenský názov:"
_EN_TITLE_LABEL = "Anglický názov:"

# A scope shorter than this is navigation chrome or a stray fragment, not
# a real scope statement — the registry leaves the cell empty when it has
# none, and empty cells are what this guards against after whitespace
# collapsing.
MIN_SCOPE_LENGTH = 40


def _session(session=None):
    session = session or requests.Session()
    session.headers.setdefault("User-Agent", USER_AGENT)
    return session


def _catalogue_rows(designation, session):
    """Every registry edition of EXACTLY this designation, newest issue
    date first. [] on any failure — same degrade-quietly convention as the
    other site modules."""
    try:
        response = session.get(EXPORT_URL, params={"name": designation}, timeout=30)
        response.raise_for_status()
    except requests.RequestException:
        return []

    # utf-8-sig: the registry prefixes the CSV with a BOM.
    reader = csv.DictReader(io.StringIO(response.content.decode("utf-8-sig")),
                            delimiter=";")
    rows = [r for r in reader
            if (r.get(_COL_DESIGNATION) or "").strip() == designation.strip()]
    rows.sort(key=lambda r: (r.get(_COL_ISSUED) or ""), reverse=True)
    return rows


def designation_variants(designation):
    """Spellings of the SAME standard to try against the registry, most
    literal first.

    Only whitespace normalisation around the amendment marker is applied:
    this corpus writes "STN EN 16898 + A1" where the registry writes
    "STN EN 16898+A1". Deliberately NOT included is falling back to the
    base standard when an amendment isn't found ("STN EN ISO 11114-1"
    for "STN EN ISO 11114-1/Zmena") — the base is a DIFFERENT document,
    and its scope would describe the wrong thing."""
    designation = (designation or "").strip()
    if not designation:
        return []
    variants = [designation]
    tightened = re.sub(r"\s*\+\s*", "+", designation)
    if tightened != designation:
        variants.append(tightened)
    return variants


def resolve(designation, session=None):
    """The registry edition to use for `designation`, or None when the
    registry has no exact match for any of its `designation_variants()`.
    Prefers an edition still in force (no withdrawal date); falls back to
    the most recently issued one, so a superseded standard still resolves
    to real descriptive text rather than nothing."""
    session = _session(session)
    for variant in designation_variants(designation):
        rows = _catalogue_rows(variant, session)
        if not rows:
            continue
        in_force = [r for r in rows if not (r.get(_COL_WITHDRAWN) or "").strip()]
        return (in_force or rows)[0]
    return None


def _labelled_cell(soup, label):
    """Text of the table cell immediately following the one whose own text
    is `label`. The detail page is a plain two-column table
    (`<td class="...title">Predmet normy:</td><td>...</td>`), so this reads
    the actual structure rather than counting lines in flattened text."""
    for cell in soup.find_all("td"):
        if cell.get_text(strip=True) == label:
            value = cell.find_next_sibling("td")
            if value is None:
                return None
            text = re.sub(r"\s+", " ", value.get_text(" ", strip=True)).strip()
            return text or None
    return None


def extract(url, cached_path=None, session=None):
    """Returns {"title": str, "description": str|None} for a
    `/norma/<id>/` detail URL, or None if the page yields no title.

    `description` is the registry's own "Predmet normy" scope text, left
    as `None` when the record has none (common — the registry only
    publishes a scope for part of its catalogue). `cached_path` is
    accepted for interface consistency with the other site modules and is
    honoured when given."""
    html = None
    if cached_path:
        try:
            with open(cached_path, "r", encoding="utf-8", errors="replace") as f:
                html = f.read()
        except OSError:
            html = None

    if html is None:
        try:
            response = _session(session).get(url, timeout=30)
            response.raise_for_status()
            html = response.text
        except requests.RequestException:
            return None

    soup = BeautifulSoup(html, "html.parser")
    title = _labelled_cell(soup, _SK_TITLE_LABEL) or _labelled_cell(soup, _EN_TITLE_LABEL)
    if not title:
        return None

    scope = _labelled_cell(soup, _SCOPE_LABEL)
    if scope and len(scope) < MIN_SCOPE_LENGTH:
        scope = None
    return {"title": title, "description": scope}


def fetch_by_designation(designation, session=None):
    """Convenience for the orchestrator: resolve + extract in one call.
    Returns the `extract()` dict with the resolved catalogue number and
    detail URL folded in, or None if either step fails."""
    session = _session(session)
    entry = resolve(designation, session=session)
    if not entry:
        return None
    detail_url = (entry.get(_COL_URL) or "").strip() or \
        f"{BASE_URL}/norma/{entry[_COL_CATALOGUE]}/"
    result = extract(detail_url, session=session)
    if not result:
        return None
    result["url"] = detail_url
    result["catalogue_number"] = entry.get(_COL_CATALOGUE)
    result["withdrawn"] = bool((entry.get(_COL_WITHDRAWN) or "").strip())
    return result
