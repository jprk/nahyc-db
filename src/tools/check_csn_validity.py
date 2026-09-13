"""Checks the validity status of Czech technical standards (ČSN) against
the free public search at https://csnonline.agentura-cas.cz/podrobne.aspx
(the "Podrobné vyhledávání" — advanced search — page; this is the free
catalog/metadata search, distinct from and NOT governed by the paid
"ČSN online pro jednotlivce" subscription service's Terms of Use, which
only restricts bulk PDF downloads from the authenticated full-text
service). Used to resolve cases like "ČSN ISO 14687" vs "ČSN EN ISO
14687" for the same base ISO number, which our dedup pipeline can flag
but can't decide on its own — only ONE such national-adoption form can be
valid at a time, and this page is the authoritative source for which one.

Usage:
    .venv/bin/python src/tools/check_csn_validity.py "ISO 14687" "ISO 19880-1"

Rate-limited (SLEEP_SECONDS between requests) and meant for occasional,
targeted lookups against our own ambiguous znacka groups — not a bulk
crawler. Each query re-fetches a fresh ASP.NET ViewState, since these are
typically single-use/short-lived.
"""
import re
import sys
import time

import requests
from bs4 import BeautifulSoup

SEARCH_URL = "https://csnonline.agentura-cas.cz/podrobne.aspx"
DETAIL_URL = "https://csnonline.agentura-cas.cz/Detailnormy.aspx"
SLEEP_SECONDS = 2
USER_AGENT = "Mozilla/5.0 (compatible; NAHYC-DP004-dedup-tool/1.0; +research use, low-volume)"

# doc/PLAN.md §9, 2026-09-13: designation-normalization helpers, found by
# live-testing real corpus znacka values against csnonline.agentura-cas.cz.
# A trailing parenthetical catalog/classification number embedded in the
# corpus's own znacka (e.g. "ČSN EN IEC 62282-2-100 (336000)") never
# appears in the site's own designation string.
_CATALOG_SUFFIX_RE = re.compile(r"\s*\(\d+\)\s*$")
# An edition marker can be written "ED.2" (corpus) or "ed. 2" (site) —
# same information, different spacing/case. Split it off so both sides
# can be compared with and without it.
_EDITION_SUFFIX_RE = re.compile(r"\s+ed\.?\s*(\d+)\s*$", re.IGNORECASE)
# An amendment/errata row's "title" is not a real edition title at all —
# never picked as a fallback "most recent" match.
_AMENDMENT_TITLE_RE = re.compile(r"^(Změna|Oprava) ke stažení", re.IGNORECASE)


def strip_catalog_suffix(designation):
    return _CATALOG_SUFFIX_RE.sub("", designation or "").strip()


def split_edition(designation):
    """"ČSN EN IEC 31010 ED.2" -> ("ČSN EN IEC 31010", "2"); no edition
    marker -> (designation, None)."""
    d = (designation or "").strip()
    m = _EDITION_SUFFIX_RE.search(d)
    if m:
        return d[:m.start()].strip(), m.group(1)
    return d, None


def _normalize_designation(text):
    return re.sub(r"\s+", " ", (text or "").strip()).lower()


def _parse_issued(text):
    """"7.2022" -> (2022, 7); unparseable -> (0, 0), sorts first."""
    try:
        month, year = (text or "").split(".")
        return (int(year), int(month))
    except ValueError:
        return (0, 0)


def find_best_match(results, znacka):
    """Picks the single result that best represents `znacka` among a raw
    `search()` result list, or None. Never guesses across a genuinely
    different designation — only resolves *formatting* differences
    (catalog-number suffix, edition-marker spacing) and, when several
    historical editions remain tied on formatting, prefers the currently
    valid one, else the most recent REAL edition (never an amendment/
    errata row's own "title", which isn't a document title at all)."""
    def _tie_break(pool):
        real_editions = [r for r in pool if not _AMENDMENT_TITLE_RE.match(r.get("title", ""))]
        candidates = real_editions or pool
        valid = [r for r in candidates if r.get("is_valid")]
        ranked = valid or candidates
        return max(ranked, key=lambda r: _parse_issued(r.get("issued", "")))

    target_full = _normalize_designation(strip_catalog_suffix(znacka))
    target_base, target_edition = split_edition(target_full)

    exact = [r for r in results
             if _normalize_designation(strip_catalog_suffix(r.get("designation", ""))) == target_full
             and r.get("title")]
    if exact:
        return _tie_break(exact)

    base_matches = [r for r in results if r.get("title")
                     and split_edition(_normalize_designation(r.get("designation", "")))[0] == target_base]
    if not base_matches:
        return None
    if target_edition is not None:
        edition_matches = [r for r in base_matches
                            if split_edition(_normalize_designation(r.get("designation", "")))[1] == target_edition]
        if edition_matches:
            return _tie_break(edition_matches)
    return _tie_break(base_matches)


def _hidden_fields(soup):
    fields = {}
    for name in ("__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION"):
        tag = soup.find(attrs={"name": name})
        fields[name] = tag.get("value", "") if tag else ""
    return fields


def search(session, query, include_invalid=True):
    """Returns a list of dicts, one per matching standard edition:
    {designation, title, catalog_number, classification_mark,
     issued, withdrawn, is_valid, transposition_method}."""
    r = session.get(SEARCH_URL)
    soup = BeautifulSoup(r.text, "html.parser")
    data = _hidden_fields(soup)
    data.update({
        "__EVENTTARGET": "",
        "__EVENTARGUMENT": "",
        "ctl00$ContentPlaceHolder1$TextBox1": query,
        "ctl00$ContentPlaceHolder1$textboxTridiciZnak": "",
        "ctl00$ContentPlaceHolder1$ceskynazev": "",
        "ctl00$ContentPlaceHolder1$anglickynazev": "",
        "ctl00$ContentPlaceHolder1$TextBox6": "",
        "ctl00$ContentPlaceHolder1$katalog": "",
        "ctl00$ContentPlaceHolder1$TextBox7": "",
        "ctl00$ContentPlaceHolder1$TextBox10": "",
        "ctl00$ContentPlaceHolder1$TextBox11": "",
        "ctl00$ContentPlaceHolder1$stav": "platneineplatne" if include_invalid else "pouzeplatne",
        "ctl00$ContentPlaceHolder1$vestvyd_mes": "",
        "ctl00$ContentPlaceHolder1$vestvyd_rok": "",
        "ctl00$ContentPlaceHolder1$DropDownList1": "znak",
        "ctl00$ContentPlaceHolder1$Button1": "Vyhledej normy",
    })
    r2 = session.post(SEARCH_URL, data=data)
    return _parse_results(r2.text)


def _parse_results(html):
    results = []
    # Each result is rendered as a block of "Label: value" rows ending in
    # action links (Náhled / Údaje k tisku / Detail normy). Rather than
    # depend on a CSS class name that could change, flatten all tags to a
    # delimiter and walk the resulting "Label:" / "value" sequence —
    # each record starts at its "ČSN ..." designation line.
    flat = re.sub(r"<script.*?</script>", " ", html, flags=re.S)
    flat = re.sub(r"<style.*?</style>", " ", flat, flags=re.S)
    flat = re.sub(r"<[^>]+>", "|", flat)
    flat = re.sub(r"\s+", " ", flat)
    parts = [p.strip() for p in flat.split("|") if p.strip()]

    current = None
    i = 0
    while i < len(parts):
        p = parts[i]
        if p.startswith("ČSN "):
            if current:
                results.append(current)
            current = {"designation": p, "title": "", "catalog_number": "",
                       "classification_mark": "", "issued": "", "withdrawn": "",
                       "transposition_method": ""}
            # Next non-empty part is usually the title, unless it's a
            # "Změna ke stažení" (amendment) line — keep as title verbatim.
            if i + 1 < len(parts) and not parts[i + 1].endswith(":"):
                current["title"] = parts[i + 1]
        elif current is not None:
            if p == "Kat. č.:" and i + 1 < len(parts):
                current["catalog_number"] = parts[i + 1]
            elif p == "Třídící znak:" and i + 1 < len(parts):
                current["classification_mark"] = parts[i + 1]
            elif p == "Vydána:" and i + 1 < len(parts):
                current["issued"] = parts[i + 1]
            elif p == "Zrušena:" and i + 1 < len(parts):
                current["withdrawn"] = parts[i + 1]
            elif p == "Způsob převzetí:" and i + 1 < len(parts):
                current["transposition_method"] = parts[i + 1]
        i += 1
    if current:
        results.append(current)

    for r in results:
        r["is_valid"] = not bool(r["withdrawn"])
    return results


def fetch_detail(catalog_number, session):
    """Fetches the per-standard detail page (doc/PLAN.md §9, 2026-09-13),
    a stable, per-document, GET-able page unlike the ephemeral POST-only
    search results — the real "single point of authority" URL to record
    as a title's provenance. Parses labeled <span id="..."> fields (found
    to be stable, not position-dependent): {designation, title, title_en,
    incorporates: [{designation, year}], url}. `incorporates` is the
    registry's own explicit link from a national ČSN adoption back to the
    international standard(s) it adopts ("Zapracované dokumenty" —
    populated only for adoptions, empty list otherwise). Returns None on
    any fetch/parse failure — never raises, never guesses."""
    url = f"{DETAIL_URL}?k={catalog_number}"
    try:
        r = session.get(url, timeout=20)
        r.raise_for_status()
    except requests.RequestException:
        return None
    soup = BeautifulSoup(r.text, "html.parser")

    def field(span_id):
        tag = soup.find(id=span_id)
        return tag.get_text(strip=True) if tag else ""

    designation = field("oznaceni")
    title = field("nazev")
    if not designation or not title:
        return None

    incorporates = []
    grid = soup.find(id="GridView2")
    if grid:
        for row in grid.find_all("tr")[1:]:  # skip header row
            cells = [c.get_text(strip=True) for c in row.find_all("td")]
            if len(cells) >= 3 and cells[1]:
                incorporates.append({"designation": cells[1], "year": cells[2]})

    return {
        "designation": designation,
        "title": title,
        "title_en": field("nazeven") or None,
        "incorporates": incorporates,
        "url": url,
    }


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    for idx, query in enumerate(sys.argv[1:]):
        if idx > 0:
            time.sleep(SLEEP_SECONDS)
        print(f"=== {query} ===")
        results = search(session, query)
        if not results:
            print("  (no matches)")
            continue
        for r in results:
            status = "PLATNÁ" if r["is_valid"] else f"ZRUŠENA {r['withdrawn']}"
            print(f"  {r['designation']} | {r['title'][:70]} | vydána {r['issued']} | {status}")
        print()


if __name__ == "__main__":
    main()
