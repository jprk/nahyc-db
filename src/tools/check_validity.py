"""Whether a Czech act or an EU act is still in effect, and what repealed it
(doc/DATABASE_SCOPE.md, odstavec 5; doc/CITATION_CLOSURE.md, odstavec 5).

Sources, both public and without authentication:
- EU acts: the Cellar SPARQL endpoint — `cdm:resource_legal_in-force`,
  `cdm:resource_legal_date_end-of-validity` and the acts that state
  `cdm:resource_legal_repeals_resource_legal` of it. An act is looked up by CELEX
  (`3` + year + `R`/`L`/`D` + number); when the kind of the act is not known, all
  three are tried and an answer is kept only when exactly one exists.
- Czech acts: the e-Sbírka linked open data — the end of effect of the act's last
  consolidated version (`účinnost-znění-do`) and the start of effect of its first
  one; the act that repealed it comes from the act's page on zakonyprolidi.cz
  ("Zrušeno k … (N/RRRR Sb.)"), which e-Sbírka's open data do not carry.

Checked are the candidates of the citation closure (citation_closure.py: missing,
cited by at least two documents, not mainly as amending acts) and every Czech and
EU act in the database. Results are cached in data/validity_cache.json (one entry
per key, with the date of the check); a later run checks only what is not in the
cache or is older than --max-age days. data/citation_closure_candidates.csv gets
the status, the end date and the repealing acts as extra columns.

Usage: .venv/bin/python src/tools/check_validity.py [--env-file FILE] [--max-age DAYS] [--limit N]
"""
import argparse
import csv
import datetime
import json
import pathlib
import re
import time

import requests

import citation_closure as cc

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
CACHE_PATH = REPO_ROOT / "data" / "validity_cache.json"
USER_AGENT = "Mozilla/5.0 (compatible; NAHYC-DP004-validity/1.0; +research use, low-volume)"

CELLAR = "http://publications.europa.eu/webapi/rdf/sparql"
ESBIRKA = "https://opendata.eselpoint.gov.cz/sparql"
ESB = "https://slovník.gov.cz/datový/sbírka/pojem/"
ELI = "https://opendata.eselpoint.gov.cz/esel-esb/eli/cz/sb/{year}/{number}"
ZAKONY = "https://www.zakonyprolidi.cz/cs/{year}-{number}"
KIND_LETTERS = {"regulation": "R", "directive": "L", "decision": "D"}
BATCH = 40

IN_FORCE, NOT_YET, ENDED, UNKNOWN = "účinný", "dosud neúčinný", "zrušený", "nezjištěno"


def celex_candidates(key, kind=None):
    """CELEX numbers an `EU:year/number` key can stand for."""
    year, number = key.split(":", 1)[1].split("/")
    letters = [KIND_LETTERS[kind]] if kind in KIND_LETTERS else ["R", "L", "D"]
    return [f"3{year}{letter}{int(number):04d}" for letter in letters]


def key_of_celex(celex):
    m = re.fullmatch(r"3(\d{4})[RLD](\d{4})", celex or "")
    return f"EU:{m.group(1)}/{int(m.group(2))}" if m else None


def _sparql(session, endpoint, query, output_param="format"):
    response = session.get(endpoint, params={"query": query, output_param: "application/sparql-results+json"},
                           timeout=120)
    response.raise_for_status()
    return response.json()["results"]["bindings"]


def eu_status(session, keys_with_kinds, today):
    """{key: entry} for `[(key, kind)]` from Cellar."""
    wanted = {celex: key for key, kind in keys_with_kinds for celex in celex_candidates(key, kind)}
    found = {}
    celexes = sorted(wanted)
    for start in range(0, len(celexes), BATCH):
        values = " ".join(f'"{c}"^^<http://www.w3.org/2001/XMLSchema#string>' for c in celexes[start:start + BATCH])
        query = f"""PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
SELECT ?celex ?inforce ?end ?repealer WHERE {{
  VALUES ?celex {{ {values} }}
  ?w cdm:resource_legal_id_celex ?celex .
  OPTIONAL {{ ?w cdm:resource_legal_in-force ?inforce }}
  OPTIONAL {{ ?w cdm:resource_legal_date_end-of-validity ?end }}
  OPTIONAL {{ ?r cdm:resource_legal_repeals_resource_legal ?w . ?r cdm:resource_legal_id_celex ?repealer }}
}}"""
        for row in _sparql(session, CELLAR, query):
            celex = row["celex"]["value"]
            entry = found.setdefault(celex, {"in_force": None, "end": None, "repealed_by": set()})
            if "inforce" in row:
                entry["in_force"] = row["inforce"]["value"] in ("1", "true")
            if "end" in row:
                entry["end"] = row["end"]["value"][:10]
            if "repealer" in row:
                repealer = key_of_celex(row["repealer"]["value"])
                if repealer:
                    entry["repealed_by"].add(repealer)
        time.sleep(1)
    result = {}
    for key, kind in keys_with_kinds:
        hits = [(celex, found[celex]) for celex in celex_candidates(key, kind) if celex in found]
        if len(hits) != 1:
            result[key] = {"status": UNKNOWN, "source": "cellar",
                           "note": "no CELEX found" if not hits else "several acts: " + ", ".join(c for c, _ in hits)}
            continue
        celex, entry = hits[0]
        if entry["in_force"] is True:
            status = IN_FORCE
        elif entry["end"] and entry["end"] < today:
            status = ENDED
        else:
            status = UNKNOWN if entry["in_force"] is None else ENDED
        result[key] = {"status": status, "source": "cellar", "celex": celex, "end": entry["end"],
                       "repealed_by": sorted(entry["repealed_by"])}
    return result


def cz_status(session, keys, today):
    """{key: entry} for `CZ:number/year` keys from e-Sbírka (effect) and zakonyprolidi.cz (repealing act)."""
    result = {}
    for start in range(0, len(keys), BATCH):
        chunk = keys[start:start + BATCH]
        nodes = {ELI.format(year=k.split("/")[1], number=k.split(":")[1].split("/")[0]): k for k in chunk}
        values = " ".join(f"<{node}>" for node in nodes)
        query = f"""SELECT ?act ?to ?from WHERE {{
  VALUES ?act {{ {values} }}
  ?act <{ESB}má-poslední-znění> ?last .
  OPTIONAL {{ ?last <{ESB}účinnost-znění-do> ?to }}
  OPTIONAL {{ ?act <{ESB}má-znění> ?version . ?version <{ESB}účinnost-znění-od> ?from }}
}}"""
        rows = _sparql(session, ESBIRKA, query, output_param="output")
        seen = {}
        for row in rows:
            entry = seen.setdefault(nodes[row["act"]["value"]], {"to": None, "from": []})
            if "to" in row:
                entry["to"] = row["to"]["value"][:10]
            if "from" in row:
                entry["from"].append(row["from"]["value"][:10])
        for key in chunk:
            entry = seen.get(key)
            if entry is None:
                result[key] = {"status": UNKNOWN, "source": "e-sbirka", "note": "not in e-Sbírka open data"}
                continue
            first = min((d for d in entry["from"] if not d.startswith("0000")), default=None)
            if entry["to"] and entry["to"] < today:
                status = ENDED
            elif first and first > today:
                status = NOT_YET
            else:
                status = IN_FORCE
            result[key] = {"status": status, "source": "e-sbirka", "end": entry["to"], "effective_from": first,
                           "repealed_by": []}
        time.sleep(1)
    for key, entry in result.items():
        if entry["status"] == ENDED:
            entry["repealed_by"], entry["repealed_on"] = repealing_act(session, key)
            time.sleep(1)
    return result


_REPEALED = re.compile(r"Zrušeno k\s*(\d{1,2})\.(\d{1,2})\.(\d{4})\s*\(\s*(\d{1,4})/(\d{4})\s*Sb\.\s*\)")


def parse_repealed(page_html):
    """(["CZ:n/y"], "YYYY-MM-DD") from a zakonyprolidi.cz act page, or ([], None)."""
    m = _REPEALED.search(re.sub(r"<[^>]+>", " ", page_html))
    if not m:
        return [], None
    day, month, year, number, act_year = m.groups()
    return [f"CZ:{int(number)}/{act_year}"], f"{year}-{int(month):02d}-{int(day):02d}"


def repealing_act(session, key):
    number, year = key.split(":")[1].split("/")
    try:
        response = session.get(ZAKONY.format(year=year, number=number), timeout=60)
        return parse_repealed(response.text) if response.ok else ([], None)
    except requests.RequestException:
        return [], None


def targets(rows, documents):
    """[(key, kind)] to check: the closure's candidates and the database's own acts."""
    chosen = {}
    for row in rows:
        if (row["family"] in ("CZ", "EU") and not row["in_database"] and row["cited_by"] >= 2
                and row["amendment_share"] < 0.5):
            chosen[row["key"]] = row["kind"]
    for _doc_id, identifier, title in documents:
        for key in cc.own_keys(identifier, title):
            if key.split(":")[0] in ("CZ", "EU"):
                chosen.setdefault(key, kind_from_title(title))
    return sorted(chosen.items())


def kind_from_title(title):
    """The kind of an EU act named by the first such word of its title ("Směrnice …")."""
    m = cc._EU_KIND.search((title or "")[:200])
    if not m:
        return None
    word = m.group(1).lower()
    return next((kind for prefix, kind in cc._KINDS.items() if word.startswith(prefix)), None)


def stale(entry, max_age, today):
    checked = entry.get("checked_at")
    return not checked or (datetime.date.fromisoformat(today) - datetime.date.fromisoformat(checked)).days > max_age


def update_candidates(cache, path=cc.CANDIDATES_PATH):
    """Adds `platnost`, `konec`, `zruseno_predpisem` to the candidates sheet (kept: `rozhodnuti`)."""
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return 0
    fields = [f for f in rows[0] if f not in ("platnost", "konec", "zruseno_predpisem")]
    fields = fields[:fields.index("rozhodnuti")] + ["platnost", "konec", "zruseno_predpisem"] + fields[fields.index("rozhodnuti"):]
    for row in rows:
        key = ("EU:" if row["family"] == "EU" else f"{row['family']}:") + row["designation"].split()[0]
        entry = cache.get(key, {})
        row["platnost"] = entry.get("status", "")
        row["konec"] = entry.get("end", "") or ""
        row["zruseno_predpisem"] = " ".join(entry.get("repealed_by", []))
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--max-age", type=int, default=30, help="recheck cache entries older than this (days)")
    parser.add_argument("--limit", type=int, default=None, help="check at most N keys (a trial run)")
    args = parser.parse_args(argv)
    today = datetime.date.today().isoformat()
    documents, texts, _database = cc.load_from_database(args.env_file)
    rows = cc.closure(documents, texts)
    cache = json.loads(CACHE_PATH.read_text(encoding="utf-8")) if CACHE_PATH.exists() else {}
    todo = [(k, kind) for k, kind in targets(rows, documents) if stale(cache.get(k, {}), args.max_age, today)]
    if args.limit is not None:
        todo = todo[:args.limit]
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    eu = eu_status(session, [(k, kind) for k, kind in todo if k.startswith("EU:")], today)
    cz = cz_status(session, [k for k, _ in todo if k.startswith("CZ:")], today)
    for key, entry in {**eu, **cz}.items():
        cache[key] = {**entry, "checked_at": today}
    CACHE_PATH.write_text(json.dumps(dict(sorted(cache.items())), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"checked {len(todo)} acts ({len(eu)} EU, {len(cz)} CZ); cache: {len(cache)} entries")
    print(f"candidates sheet updated: {update_candidates(cache)} rows")


if __name__ == "__main__":
    main()
