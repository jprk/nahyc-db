"""EuroVoc descriptors of the EU acts of the database, from Cellar (doc/KLICOVA_SLOVA.md).

EuroVoc is the multilingual thesaurus of the EU; the Publications Office indexes
every act with its descriptors (`cdm:work_is_about_concept_eurovoc`). This
script finds the CELEX number of each EU act of the database (its identifier or
title, citation_closure.own_keys()) and stores the Czech and English labels in
data/eurovoc_cache.json, keyed by document_terms.document_keys():

    {"(EU) 2021/535": {"celex": "32021R0535", "fetched": "2026-11-23",
                       "terms": [{"code": "1252", "cs": "homologace", "en": "approval"}, ...]}}

    .venv/bin/python src/tools/fetch_eurovoc.py            # only acts not in the cache
    .venv/bin/python src/tools/fetch_eurovoc.py --refresh  # all of them again

Reads the database (`--env-file`, the live one by default) and never writes it;
document_terms.py --apply loads the cache.
"""
import argparse
import datetime
import re
import sys
import time

import requests

import check_validity as cv
import citation_closure as cc
import document_terms as dterms

BATCH = 40
# acts whose title in the database names another act than their number (doc/KLICOVA_SLOVA.md,
# odstavec 3.2): their descriptors would describe the other act, so they get none until the
# record is corrected (data/manual_corrections.json); {doc key: reason}. The two found on
# 2026-11-23, (EU) 2023/955 and (EU) 2021/535, are corrected there.
EXCLUDED = {}
# a UN/ECE regulation published in the Official Journal, "[2019/795]" -> CELEX 42019X0795
_UNECE_IDENTIFIER = re.compile(r"^\[(\d{4})/(\d{1,4})\]")
QUERY = """PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
SELECT ?celex ?c ?l WHERE {{
  VALUES ?celex {{ {values} }}
  ?w cdm:resource_legal_id_celex ?celex .
  ?w cdm:work_is_about_concept_eurovoc ?c .
  ?c skos:prefLabel ?l FILTER(lang(?l) IN ("cs", "en"))
}}"""


def eu_acts(documents):
    """{doc key: [CELEX candidates]} of the EU acts among `documents`
    (rows of document_terms.fetch_documents())."""
    acts = {}
    keys = dterms.document_keys(documents)
    for doc_id, identifier, url, type_name, title, *_ in documents:
        if not type_name or not type_name.endswith(" EU"):
            continue
        key = keys[doc_id]
        if not key or key in EXCLUDED:
            continue
        unece = _UNECE_IDENTIFIER.match(identifier or "")
        if unece:
            acts[key] = [f"4{unece.group(1)}X{int(unece.group(2)):04d}"]
            continue
        eu_keys = [k for k in cc.own_keys(identifier, title) if k.startswith("EU:")]
        if eu_keys:
            kind = cv.kind_from_title(title)
            acts[key] = [c for k in eu_keys for c in cv.celex_candidates(k, kind)]
    return acts


def parse_bindings(bindings):
    """{celex: {code: {"cs": label, "en": label}}} from the SPARQL result rows."""
    found = {}
    for row in bindings:
        celex = row["celex"]["value"]
        code = row["c"]["value"].rsplit("/", 1)[-1]
        lang = row["l"].get("xml:lang")
        found.setdefault(celex, {}).setdefault(code, {"cs": None, "en": None})[lang] = row["l"]["value"]
    return found


def fetch(session, celexes, sleep=1.0):
    found = {}
    celexes = sorted(set(celexes))
    for start in range(0, len(celexes), BATCH):
        values = " ".join(f'"{c}"^^<http://www.w3.org/2001/XMLSchema#string>' for c in celexes[start:start + BATCH])
        found.update(parse_bindings(cv._sparql(session, cv.CELLAR, QUERY.format(values=values))))
        time.sleep(sleep)
    return found


def entries(acts, found, today):
    """{doc key: cache entry} for the acts with exactly one CELEX that has descriptors."""
    out = {}
    for key, celexes in acts.items():
        hits = [c for c in celexes if c in found]
        if len(hits) != 1:
            continue
        terms = [{"code": code, "cs": labels["cs"], "en": labels["en"]}
                 for code, labels in sorted(found[hits[0]].items(), key=lambda kv: (kv[1]["cs"] or kv[1]["en"] or ""))]
        out[key] = {"celex": hits[0], "fetched": today, "terms": terms}
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--refresh", action="store_true", help="fetch the acts already in the cache again")
    args = parser.parse_args(argv)
    conn = dterms.connect(args.env_file)
    try:
        documents = dterms.fetch_documents(conn.cursor())
    finally:
        conn.close()
    cache = dterms.load_cache(dterms.CACHES["eurovoc"])
    acts = eu_acts(documents)
    todo = {k: v for k, v in acts.items() if args.refresh or k not in cache}
    print(f"EU acts: {len(acts)}, to fetch: {len(todo)}")
    session = requests.Session()
    found = fetch(session, [c for cs in todo.values() for c in cs])
    new = entries(todo, found, datetime.date.today().isoformat())
    cache.update(new)
    for key in EXCLUDED:
        cache.pop(key, None)
    dterms.save_cache(dterms.CACHES["eurovoc"], cache)
    missing = sorted(set(todo) - set(new))
    print(f"with descriptors: {len(new)}; without: {len(missing)}")
    for key in missing:
        print(f"  no descriptors: {key}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
