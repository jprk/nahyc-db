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
SLEEP_SECONDS = 2
USER_AGENT = "Mozilla/5.0 (compatible; NAHYC-DP004-dedup-tool/1.0; +research use, low-volume)"


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
