"""ICS classes (and the ČAS descriptors) of the standards of the database, from
the public catalogue of ČAS (doc/KLICOVA_SLOVA.md).

The International Classification for Standards (ICS, ISO) sorts standards into
fields, groups and subgroups ("71.100.20 Technické plyny"). An EN, ISO or IEC
standard keeps its ICS in every national adoption, so the Czech adoption (ČSN)
in the catalogue of ČAS gives the classes of the STN, DIN EN, ISO, ... edition
of the database too. The detail page of a ČSN (check_csn_validity.fetch_detail())
lists the ICS classes with their Czech names and, for some, the descriptors and
keywords of ČAS.

A standard is looked up by its international designation (`international_part()`:
"STN EN ISO 6145-11/ - 2009.02" -> "EN ISO 6145-11"); national standards with no
European or international counterpart (DIN, VDI, DVGW, CGA, EIGA, ...) are not in
the catalogue and get no ICS here. The answers go to data/ics_cache.json, keyed by
document_terms.document_keys(); a standard not found is stored as such and asked again
only with --refresh.

    .venv/bin/python src/tools/fetch_ics.py --limit 20     # the first 20 not in the cache
    .venv/bin/python src/tools/fetch_ics.py                 # all not in the cache

A standard without a ČSN gets its ICS codes from ISO Open Data (iso_open_data.py) when ISO
lists it, stored under `iso` in its cache entry (the Czech names of the classes come from
the classes seen in the ČAS catalogue).

Low-volume (check_csn_validity.SLEEP_SECONDS between requests, two requests per
standard); reads the database and never writes it.
"""
import argparse
import datetime
import pathlib
import re
import sys
import time

import requests
from bs4 import BeautifulSoup

import check_csn_validity as csn
import document_terms as dterms
import iso_open_data
import norm_title

# the national prefixes of an adoption, in front of the international designation
_NATIONAL = re.compile(r"^(?:ČSN|CSN|STN|TNI|DIN|BS|ÖNORM|OENORM|NF|UNE|SN|PN|SS|NEN|DS|SFS|UNI|I\.S\.|DIN VDE|VDE)\s+", re.I)
_INTERNATIONAL = re.compile(r"^(?:EN|ISO|IEC|CEN|CLC|CENELEC|ETSI)\b", re.I)
_ICS_ITEM = re.compile(r"(\d{2}(?:\.\d{3}(?:\.\d{2})?)?)\s*-\s*")


def international_part(identifier):
    """The European or international designation of a standard ("EN ISO 6145-11"),
    or None for a national one. Drops the national prefixes, the edition date, the
    catalogue number and the amendment suffix ("/A1")."""
    core = csn.strip_catalog_suffix(norm_title.designation_core(identifier or ""))
    core = re.sub(r"\s+", " ", core).strip()
    previous = None
    while previous != core:
        previous = core
        core = _NATIONAL.sub("", core)
    core = core.split("*", 1)[0].strip()                        # "EN IEC 60079-14*VDE 0165-1"
    core = re.sub(r"\s*[:/]\s*(?:19|20)\d{2}$", "", core)       # "ISO 11623:2015"
    core = re.sub(r"\s*/\s*(?:A|AC|AMD)\s*\d+.*$", "", core, flags=re.I)
    core = re.sub(r"\s*\+\s*(?:A|AC|AMD)\s*\d+.*$", "", core, flags=re.I)   # "EN 13136+A1"
    core = core.rstrip("/ ").strip()
    if not _INTERNATIONAL.match(core) or not re.search(r"\d", core):
        return None
    return core


def _norm(text):
    text = csn.split_edition(re.sub(r"\s+", " ", (text or "").strip()))[0]
    return text.upper().replace("/", " ").replace("  ", " ")


def pick(results, international):
    """The ČSN (or TNI) edition of `results` adopting `international`, preferring a
    valid one, or None. "ISO 19880-1" also takes "ČSN EN ISO 19880-1" (the same
    standard adopted through CEN)."""
    target = _norm(international)
    wanted = {"ČSN " + target, "TNI " + target, "ČSN P " + target}
    if target.startswith(("ISO ", "IEC ")):
        wanted |= {"ČSN EN " + target, "TNI EN " + target}
    matches = [r for r in results if _norm(r.get("designation")) in wanted
               and not csn._AMENDMENT_TITLE_RE.match(r.get("title", ""))]
    if not matches:
        return None
    valid = [r for r in matches if r.get("is_valid")]
    return max(valid or matches, key=lambda r: csn._parse_issued(r.get("issued", "")))


def parse_ics(text):
    """[{"code", "name"}] from the ICS field of a detail page, which runs the
    classes together: "43.060.40 - Palivové systémy71.100.20 - Technické plyny"."""
    items = []
    matches = list(_ICS_ITEM.finditer(text or ""))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        items.append({"code": m.group(1), "name": text[m.end():end].strip(" ;,")})
    return items


_WORD = re.compile(r"[a-záčďéěíňóřšťúůýž]{3}")


def _split_terms(text):
    """The words of a descriptor field; some ČSN carry catalogue codes there ("BL/BY",
    "KNX.C") instead of words, and those are dropped."""
    return [t.strip() for t in re.split(r"[;,]", text or "") if _WORD.search(t)]


def detail(session, catalog_number):
    r = session.get(f"{csn.DETAIL_URL}?k={catalog_number}", timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    def field(span_id):
        tag = soup.find(id=span_id)
        return tag.get_text(strip=True) if tag else ""

    return {"designation": field("oznaceni"), "ics": parse_ics(field("ics")),
            "descriptors": _split_terms(field("deskriptory")) + _split_terms(field("klicslova")),
            "url": f"{csn.DETAIL_URL}?k={catalog_number}"}


def standards(documents):
    """{doc key: international designation} of the standards among `documents`."""
    out = {}
    keys = dterms.document_keys(documents)
    for doc_id, identifier, url, type_name, *_ in documents:
        if type_name != "Norma":
            continue
        international = international_part(identifier)
        key = keys[doc_id]
        if key and international:
            out[key] = international
    return out


def lookup(session, international, today, sleep=csn.SLEEP_SECONDS):
    results = csn.search(session, international)
    time.sleep(sleep)
    chosen = pick(results, international)
    if not chosen:
        return {"query": international, "found": False, "fetched": today}
    info = detail(session, chosen["catalog_number"])
    time.sleep(sleep)
    return {"query": international, "found": True, "fetched": today, "csn": info["designation"],
            "valid": chosen.get("is_valid"), "url": info["url"], "ics": info["ics"],
            "descriptors": info["descriptors"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--refresh", action="store_true", help="ask again about the standards in the cache")
    parser.add_argument("--limit", type=int, default=None, help="at most this many lookups")
    parser.add_argument("--no-iso", action="store_true", help="skip ISO Open Data for the standards without a ČSN")
    parser.add_argument("--iso-data", default=None, help="the ISO Open Data file (default data/external/...)")
    parser.add_argument("--download-iso", action="store_true", help="download the ISO Open Data file again")
    args = parser.parse_args(argv)
    conn = dterms.connect(args.env_file)
    try:
        documents = dterms.fetch_documents(conn.cursor())
    finally:
        conn.close()
    path = dterms.CACHES["ics"]
    cache = dterms.load_cache(path)
    wanted = standards(documents)
    # a standard not found under an older reading of its designation is asked again
    todo = [k for k in sorted(wanted) if args.refresh or k not in cache
            or (not cache[k].get("found") and cache[k].get("query") != wanted[k])]
    if args.limit is not None:
        todo = todo[:args.limit]
    norms = sum(1 for d in documents if d[3] == "Norma")
    print(f"standards: {norms}, European/international: {len(wanted)}, to look up: {len(todo)}")
    session = requests.Session()
    session.headers["User-Agent"] = csn.USER_AGENT
    today = datetime.date.today().isoformat()
    by_query = {}
    for i, key in enumerate(todo, 1):
        international = wanted[key]
        try:
            entry = by_query.get(international) or lookup(session, international, today)
        except requests.RequestException as error:
            print(f"[warn] {key}: {error}")
            continue
        by_query[international] = entry
        cache[key] = entry
        if i % 10 == 0:
            dterms.save_cache(path, cache)
        print(f"{i}/{len(todo)} {key} -> {entry.get('csn') or 'not found'} "
              f"{' '.join(t['code'] for t in entry.get('ics', []))}", flush=True)
    dterms.save_cache(path, cache)
    found = sum(1 for k in wanted if cache.get(k, {}).get("found"))
    print(f"with a ČSN and ICS: {found} of {len(wanted)}")
    if not args.no_iso:
        added = add_iso_open_data(cache, wanted, args.iso_data, download=args.download_iso)
        dterms.save_cache(path, cache)
        print(f"ICS from ISO Open Data for standards without a ČSN: {added}")
    return 0


def add_iso_open_data(cache, wanted, path=None, download=False, index=None):
    """Adds the ISO record (iso_open_data.summary()) to the cache entries of the standards
    not found in the ČAS catalogue; returns how many got ICS codes."""
    if index is None:
        path = pathlib.Path(path or iso_open_data.DEFAULT_PATH)
        if download or not path.exists():
            iso_open_data.download(path)
        index = iso_open_data.load_index(path)
    added = 0
    for key, international in wanted.items():
        entry = cache.get(key)
        if not entry or entry.get("found"):
            continue
        record = iso_open_data.lookup(index, international)
        entry["iso"] = iso_open_data.summary(record) if record else None
        added += bool(record and record.get("icsCode"))
    return added


if __name__ == "__main__":
    sys.exit(main())
