"""Lookups on demand (stage E5, doc/DATA_SOURCES.md odstavec 4.3): sources that are not
run regularly but searched when an editor needs them — for one document or for the
place of a project. `harvest_sources.py --lookup SOURCE "query"` prints the results;
nothing is written. Each lookup is `function(session, query)` and returns
[{title, url, detail}].

* sbirka_pp_usc — the collection of regulations of regions and municipalities
  (sbirkapp.gov.cz): regulations whose title contains the query, newest first.
* is_eia — the EIA information system of CENIA: projects found by the quick search
  (the form needs the session of the page and all its fields; first page of results).
* echa_chem — substances in ECHA CHEM (its internal JSON interface, not documented).
* data_europa — datasets of data.europa.eu (search API).
* gesetze — German acts whose title contains the query (gii-toc.xml), for comparison only.
"""
import html
import re
import urllib.parse
import xml.etree.ElementTree as ET


def _text(fragment):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment or "")).split())


def sbirka_pp_usc(session, query):
    response = session.get("https://sbirkapp.gov.cz/vyhledavani/vysledek",
                           params={"hlavni_typ": "pp", "nazev": query}, timeout=60)
    response.raise_for_status()
    results = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", response.text, re.S):
        cells = [_text(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
        href = re.search(r'href="([^"]+)"', row)
        if len(cells) >= 4:
            results.append({"title": f"{cells[2]} {cells[1]}: {cells[3]}", "detail": f"{cells[0]}; " + "; ".join(cells[4:7]),
                            "url": urllib.parse.urljoin(response.url, href.group(1)) if href else None})
    return results


def is_eia(session, query):
    url = "https://portal.cenia.cz/eiasea/view/eia100_cr?lang=cs"
    page = session.get(url, timeout=60)
    page.raise_for_status()
    fields = {}
    for tag in re.findall(r"<input[^>]*>", page.text):
        name = re.search(r'name="([^"]+)"', tag)
        if name:
            value = re.search(r'value="([^"]*)"', tag)
            fields[name.group(1)] = value.group(1) if value else ""
    fields.update({"typHledani": "rychle", "quickSearch": query})
    response = session.post(url, data=fields, timeout=60)
    response.raise_for_status()
    results = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", response.text, re.S):
        code = re.search(r"\b([A-Z]{3}\d{3,4})\b", _text(row))
        href = re.search(r'href="([^"]*detail[^"]*)"', row)
        cells = [_text(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
        if code and len(cells) >= 2:
            title = next((c for c in cells if c and c != code.group(1)), "")
            results.append({"title": f"{code.group(1)} {title}", "detail": "; ".join(c for c in cells[2:5] if c),
                            "url": urllib.parse.urljoin(response.url, href.group(1)) if href else url})
    total = re.search(r"záznamů:\s*(\d+)", _text(response.text))
    if total and int(total.group(1)) > len(results):
        results.append({"title": f"… celkem {total.group(1)} záznamů, zobrazena první strana", "detail": "", "url": url})
    return results


def echa_chem(session, query):
    response = session.get("https://chem.echa.europa.eu/api-substance/v1/substance",
                           params={"pageIndex": 1, "pageSize": 20, "searchText": query}, timeout=60)
    response.raise_for_status()
    results = []
    for item in response.json().get("items", []):
        index = item.get("substanceIndex", {})
        results.append({"title": index.get("rmlName"), "detail": f"EC {index.get('rmlEc')}, CAS {index.get('rmlCas')}",
                        "url": f"https://chem.echa.europa.eu/{index.get('rmlId')}"})
    return results


def data_europa(session, query):
    response = session.get("https://data.europa.eu/api/hub/search/search", params={"q": query, "limit": 20},
                           timeout=60)
    response.raise_for_status()
    results = []
    for item in response.json()["result"]["results"]:
        title = item.get("title") or {}
        title = title.get("en") or title.get("cs") or next(iter(title.values()), "") if isinstance(title, dict) else title
        country = (item.get("country") or {}).get("label", "")
        results.append({"title": title, "detail": country,
                        "url": f"https://data.europa.eu/data/datasets/{item.get('id')}"})
    return results


def gesetze(session, query):
    response = session.get("https://www.gesetze-im-internet.de/gii-toc.xml", timeout=60)
    response.raise_for_status()
    results = []
    for item in ET.fromstring(response.content).iter("item"):
        title = (item.findtext("title") or "").strip()
        if query.lower() in title.lower():
            link = (item.findtext("link") or "").strip()
            results.append({"title": title, "detail": "Gesetze im Internet (jen ke srovnání)",
                            "url": link.replace("/xml.zip", "/") if link else None})
    return results


LOOKUPS = {"sbirka-pp-usc": sbirka_pp_usc, "is-eia": is_eia, "echa-chem": echa_chem,
           "data-europa-search": data_europa, "gesetze-im-internet": gesetze}
