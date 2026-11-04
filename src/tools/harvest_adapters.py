"""Adapters of the monitored sources of stage E1 (doc/DATA_SOURCES.md, odstavec
4.3): the existing screening and checking scripts brought under the runner
(harvest_sources.py). Each adapter is `function(entry, session, since, context)`
and returns a list of harvest.Finding; `context["documents"]` are the documents of
the database as [(id, identifier, title, url)], `context["today"]` the date,
`context["limit"]` (optional) the most a checking adapter looks up in a trial run.

The adapters reuse the functions of the scripts they replace and add nothing to the
way those query their sources:

* eurlex_new — screen_eurlex.py: Cellar titles containing "hydrogen" or "RFNBO",
  kept only for binding acts (CELEX R/L/D) not matching the off-topic patterns of
  add_eurlex_hydrogen_acts.py; the key `EU:year/number` comes from the CELEX.
* esbirka_new — screen_esbirka.py's search for "vodík*" in the e-Sbírka open data.
  A hit is a fragment of an act's text (or a file of a fragment); the act and its
  version are read from the ELI of the node that contains it (`obsahuje-fragment`,
  for a file one step further via `má-binární-soubor`), so the finding gets the key
  `CZ:number/year`. Kept are acts the database lacks whose LAST version still
  contains the word and is not out of effect (2026-11-04: 364 acts contain the word
  in some version). Acts whose metadata title contains it cannot be joined to their
  number and keep their own key with the flag `needs_key` (not when repealed).
* validity_eu, validity_cz — check_validity.py for the Czech and EU acts of the
  database whose cache entry is missing or older than VALIDITY_MAX_AGE days (the
  Czech one also reads the repealing act from zakonyprolidi.cz).
* csn_state, normoff_state — check_csn_validity.py and src/sites/normoff.py for the
  ČSN and STN standards of the database (cache data/norm_validity_cache.json,
  same age limit). Both registries are meant for targeted lookups: the sources run
  on demand (`cadence: on_demand`), never in a scheduled run.
* hytep_new — add_hytep_hydrogen_docs.py: the two document lists of hytep.cz;
  the documents have no designation and are known by their address.
"""
import datetime
import hashlib
import json
import pathlib
import re
import sys
import time

import harvest
from harvest import Finding

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
VALIDITY_MAX_AGE = 30
SLEEP_SECONDS = 1


def _stale(cache, key, today, max_age=VALIDITY_MAX_AGE):
    checked = cache.get(key, {}).get("checked_at")
    return not checked or (datetime.date.fromisoformat(today) - datetime.date.fromisoformat(checked)).days > max_age


def _load(path):
    path = pathlib.Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


# --- EUR-Lex -----------------------------------------------------------------

def eurlex_new(entry, session, since, context):
    import candidates as cd
    import screen_eurlex as se
    from add_eurlex_hydrogen_acts import classify_candidate, is_off_topic
    from check_validity import key_of_celex
    findings, seen = [], set()
    for index, keyword in enumerate(se.HYDROGEN_KEYWORDS):
        if index:
            time.sleep(se.SLEEP_SECONDS)
        bindings = se.run_sparql(session, se.build_query(keyword))
        if len(bindings) >= se.RESULT_LIMIT:
            raise RuntimeError(f"{len(bindings)} results for {keyword!r} = RESULT_LIMIT, the answer is truncated")
        for binding in bindings:
            celex, title = binding["celex"]["value"], binding["title"]["value"]
            key = key_of_celex(celex)
            if celex in seen or key is None or not classify_candidate({"celex": celex}) or is_off_topic(title):
                continue
            seen.add(celex)
            kind = cd.kind_from_celex(celex)
            findings.append(Finding(entry["id"], "new_document", title, key=key, native_id=celex,
                                    designation=cd.designation(key, kind), document_type=cd.EU_TYPES.get(kind),
                                    url=cd.document_url(key, kind, celex), language="CS", jurisdikce="EU",
                                    excerpt=f"CELEX {celex}; title contains {keyword!r}"))
    return findings


# --- e-Sbírka ----------------------------------------------------------------

ESB = "https://slovník.gov.cz/datový/sbírka/pojem/"
ESEL = "https://opendata.eselpoint.gov.cz/esel-esb/eli/cz/sb/"
_ELI_VERSION = re.compile(r"/eli/cz/sb/(\d{4})/(\d+)/(\d{4}-\d{2}-\d{2})")
BATCH = 40
# A hit is a node of an act's text; the answer has one row per hit and version.
ESBIRKA_LIMIT = 20000


def act_key(owner_uri):
    """`CZ:number/year` from the ELI of a node of an act, or None."""
    m = _ELI_VERSION.search(owner_uri or "")
    return f"CZ:{int(m.group(2))}/{m.group(1)}" if m else None


def version_of(owner_uri):
    """The ELI of the version (`…/eli/cz/sb/year/number/date`) a node belongs to."""
    m = _ELI_VERSION.search(owner_uri or "")
    return f"{ESEL}{m.group(1)}/{m.group(2)}/{m.group(3)}" if m else None


def hits_query(keyword, limit):
    return f"""SELECT DISTINCT ?owner ?hit WHERE {{
  ?hit ?p ?o . FILTER(bif:contains(?o, "'{keyword}'"))
  {{ ?owner <{ESB}obsahuje-fragment> ?hit }} UNION
  {{ ?fragment <{ESB}má-binární-soubor> ?hit . ?owner <{ESB}obsahuje-fragment> ?fragment }}
}} LIMIT {limit}"""


def titles_query(keyword):
    return f"""SELECT ?s ?title ?repealed WHERE {{
  ?s <{ESB}citace-názvu-znění-právního-aktu> ?title . FILTER(bif:contains(?title, "'{keyword}'"))
  OPTIONAL {{ ?s <{ESB}datum-zrušení> ?repealed }}
}} LIMIT 1000"""


def last_versions(session, keys, run_sparql):
    """{key: (ELI of the last version, end of its effect or None)}."""
    found = {}
    for start in range(0, len(keys), BATCH):
        chunk = keys[start:start + BATCH]
        nodes = {f"{ESEL}{k.split('/')[1]}/{k.split(':')[1].split('/')[0]}": k for k in chunk}
        values = " ".join(f"<{n}>" for n in nodes)
        query = f"""SELECT ?act ?last ?to WHERE {{ VALUES ?act {{ {values} }}
  ?act <{ESB}má-poslední-znění> ?last . OPTIONAL {{ ?last <{ESB}účinnost-znění-do> ?to }} }}"""
        for row in run_sparql(session, query):
            found[nodes[row["act"]["value"]]] = (row["last"]["value"], (row.get("to") or {}).get("value"))
        time.sleep(SLEEP_SECONDS)
    return found


def _plain(text):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text or "")).strip()


def snippets(session, uris, keyword, run_sparql):
    """{uri: plain text of its literal that contains the keyword (else its first one)}."""
    stem, texts = keyword.rstrip("*").lower(), {}
    for start in range(0, len(uris), BATCH // 2):
        values = " ".join(f"<{u}>" for u in uris[start:start + BATCH // 2])
        for row in run_sparql(session, f"SELECT ?s ?o WHERE {{ VALUES ?s {{ {values} }} ?s ?p ?o FILTER(isLiteral(?o)) }}"):
            text, uri = _plain(row["o"]["value"]), row["s"]["value"]
            if not texts.get(uri) or (stem in text.lower() and stem not in texts[uri].lower()):
                texts[uri] = text
        time.sleep(SLEEP_SECONDS)
    return texts


def _in_effect(end, today):
    return not end or end.startswith("0000") or end[:10] >= today


def esbirka_new(entry, session, since, context):
    import screen_esbirka as sb
    keyword, today, known = sb.HYDROGEN_KEYWORDS[0], context["today"], context["known"]
    rows = sb.run_sparql(session, hits_query(keyword, ESBIRKA_LIMIT))
    if not rows:
        raise RuntimeError("no answer from the e-Sbírka open data (or no hit at all)")
    if len(rows) >= ESBIRKA_LIMIT:
        raise RuntimeError(f"{len(rows)} results = the limit {ESBIRKA_LIMIT}, the answer is truncated")
    hits = {}  # key -> {version ELI: [hit uris]}
    for row in rows:
        owner = row["owner"]["value"]
        key = act_key(owner)
        if key:
            hits.setdefault(key, {}).setdefault(version_of(owner), []).append(row["hit"]["value"])
    unknown = sorted(k for k in hits if k not in known)
    last = last_versions(session, unknown, sb.run_sparql)
    kept = {}
    for key in unknown:
        version, end = last.get(key, (None, None))
        if version in hits[key] and _in_effect(end, today):
            kept[key] = hits[key][version]
    time.sleep(SLEEP_SECONDS)
    titled = [row for row in sb.run_sparql(session, titles_query(keyword)) if not row.get("repealed")
              or row["repealed"]["value"][:10] >= today]
    text = snippets(session, [uris[0] for uris in kept.values()], keyword, sb.run_sparql)
    findings = []
    for key, uris in sorted(kept.items()):
        number, year = key.split(":")[1].split("/")
        findings.append(Finding(entry["id"], "new_document", f"{number}/{year} Sb.", key=key, native_id=key,
                                designation=f"{number}/{year} Sb.", language="CS", jurisdikce="CZ",
                                url=f"https://www.zakonyprolidi.cz/cs/{year}-{number}",
                                excerpt=f"{text.get(uris[0], '')[:300]} (poslední znění, {len(uris)} míst v textu)"))
    for row in titled:
        title, uri = _plain(row["title"]["value"]), row["s"]["value"]
        findings.append(Finding(entry["id"], "new_document", title[:200], url=uri,
                                native_id=hashlib.sha256(uri.encode("utf-8")).hexdigest()[:12],
                                language="CS", jurisdikce="CZ", excerpt=f"název předpisu: {title[:300]}"))
    return findings


# --- validity of Czech and EU acts --------------------------------------------

def _validity_targets(context, family):
    import check_validity as cv
    import citation_closure as cc
    cache = _load(harvest.VALIDITY_CACHE_PATH)
    chosen = {}
    for _doc_id, identifier, title, _url in context["documents"]:
        for key in cc.own_keys(identifier, title):
            if key.startswith(family + ":") and _stale(cache, key, context["today"]):
                chosen.setdefault(key, cv.kind_from_title(title))
    targets = sorted(chosen.items())
    return targets[:context["limit"]] if context.get("limit") else targets


def _state_findings(entry, results):
    return [Finding(entry["id"], "state_change", key, key=key, state=state, excerpt=state.get("status"))
            for key, state in sorted(results.items())]


def validity_eu(entry, session, since, context):
    import check_validity as cv
    return _state_findings(entry, cv.eu_status(session, _validity_targets(context, "EU"), context["today"]))


def validity_cz(entry, session, since, context):
    import check_validity as cv
    keys = [key for key, _kind in _validity_targets(context, "CZ")]
    return _state_findings(entry, cv.cz_status(session, keys, context["today"]))


# --- standards ------------------------------------------------------------------

def _standards(context, prefix):
    cache = _load(harvest.NORM_CACHE_PATH)
    designations = sorted({identifier.strip() for _doc_id, identifier, _title, _url in context["documents"]
                           if identifier and identifier.strip().startswith(prefix + " ")})
    stale = [d for d in designations if _stale(cache, f"NORM:{d}", context["today"])]
    return stale[:context["limit"]] if context.get("limit") else stale


def csn_state(entry, session, since, context):
    import check_csn_validity as csn
    findings = []
    for index, designation in enumerate(_standards(context, "ČSN")):
        if index:
            time.sleep(csn.SLEEP_SECONDS)
        # search() takes the base designation without "ČSN" (fetch_authoritative_metadata.csn_core)
        query = csn.split_edition(csn.strip_catalog_suffix(re.sub(r"^ČSN\s+", "", designation)))[0]
        best = csn.find_best_match(csn.search(session, query), designation)
        if best is None:
            state = {"status": "nezjištěno", "source": "csnonline", "note": "no exact match"}
        else:
            state = {"status": "platná" if best["is_valid"] else "zrušená", "source": "csnonline",
                     "designation": best["designation"], "issued": best["issued"], "withdrawn": best["withdrawn"],
                     "catalog_number": best["catalog_number"]}
        findings.append(Finding(entry["id"], "state_change", designation, key=f"NORM:{designation}", state=state,
                                excerpt=state["status"]))
    return findings


def normoff_state(entry, session, since, context):
    from sites import normoff
    findings = []
    for index, designation in enumerate(_standards(context, "STN")):
        if index:
            time.sleep(SLEEP_SECONDS)
        row = normoff.resolve(designation, session)
        if row is None:
            state = {"status": "nezjištěno", "source": "normoff", "note": "no exact match"}
        else:
            withdrawn = (row.get(normoff._COL_WITHDRAWN) or "").strip()
            state = {"status": "zrušená" if withdrawn else "platná", "source": "normoff",
                     "designation": row.get(normoff._COL_DESIGNATION), "issued": row.get(normoff._COL_ISSUED),
                     "withdrawn": withdrawn or None, "url": row.get(normoff._COL_URL)}
        findings.append(Finding(entry["id"], "state_change", designation, key=f"NORM:{designation}", state=state,
                                excerpt=state["status"]))
    return findings


# --- HYTEP ------------------------------------------------------------------------

def hytep_new(entry, session, since, context):
    import add_hytep_hydrogen_docs as hy
    findings = []
    for index, page in enumerate(hy.LISTING_PAGES):
        if index:
            time.sleep(hy.SLEEP_SECONDS)
        response = session.get(page, timeout=30)
        response.raise_for_status()
        for link in hy.extract_document_links(response.text, page):
            if hy.is_skipped_duplicate(link["url"]):
                continue
            findings.append(Finding(entry["id"], "new_document", link["title"], url=link["url"],
                                    native_id=hashlib.sha256(link["url"].encode("utf-8")).hexdigest()[:12],
                                    document_type=hy.classify_hytep_document_typ(link["title"]) or None,
                                    language="CS", jurisdikce=hy.classify_jurisdikce(link["title"]),
                                    excerpt=f"Seznam dokumentů HYTEP: {page}"))
    return findings
