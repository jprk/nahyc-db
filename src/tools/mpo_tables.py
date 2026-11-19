"""The two tables of regulations the Ministry of Industry and Trade (MPO) sent on
22 May 2026 (doc/MPO_PRIPOMINKY.md, odstavec 2.1): `Předpisy CZ - vodík_MPO.xlsx`
(Czech acts and ČSN standards) and `CDV - evropské právní předpisy_v01.xlsx`
(EU and international acts, standards, technical committees), both dated
30 April 2026. They are the first golden set of the database (doc/MPO_TABULKY.md).

Three steps, each its own subcommand:

* `convert` reads both workbooks (data/20260430_MPO/raw/) into
  data/20260430_MPO/mpo_tables.json: one record per row, with the row's cells,
  whether MPO marked it yellow ("already in the database") and the keys of the
  acts or standards it names (the keys of citation_closure.py: `CZ:349/2015`,
  `EU:2024/1679`, `NORM:EN ISO 11114`).
* `compare` matches every row against a database (read only) and writes
  data/20260430_MPO/mpo_coverage.json: the row is in the database (the documents
  that match it), in the queue of candidates (DocumentCandidate) or to be put
  there, or it has a stated reason why it is neither (it is a technical committee,
  not a document). Rows without a number, technical committees and other cases a
  rule cannot decide come from data/20260430_MPO/mpo_decisions.json.
* `lookup` finds the authoritative title, address and validity of every row
  still missing (zakonyprolidi.cz and e-Sbírka for Czech acts, EUR-Lex/Cellar for
  EU acts, the ČAS catalogue for ČSN standards) and writes the candidates to
  data/20260430_MPO/mpo_candidates.json; `import` writes them into the queue
  (source `mpo`, "MPO/CDV 30. 4. 2026"). A row already in the queue from another
  source keeps its source and gets the MPO row added to its evidence. Dry run
  unless --apply; `import` needs no network.

What a row cannot say about a candidate (its issuer when the column "Nositel" is
wrong, that it is an amendment and of which acts, a nickname such as "LEX OZE II")
comes from the section `_candidates` of mpo_decisions.json. `lookup` asks the
network only for candidates not yet in mpo_candidates.json (`--refresh` asks
again for all); the rows, issuer and these details it always recomputes. `import`
can run any number of times: a candidate of the source `mpo` still waiting for a
decision gets its evidence, validity and issuer refreshed (an issuer an editor has
changed is kept), the keys of the amended acts become the ids of their documents
in that database (`amends_ids`, from which accepting the candidate creates the
AMENDS relations), and a decided or proposed candidate is never touched.

Usage: .venv/bin/python src/tools/mpo_tables.py convert
       .venv/bin/python src/tools/mpo_tables.py compare [--env-file FILE] [--output FILE]
       .venv/bin/python src/tools/mpo_tables.py lookup [--refresh]
       .venv/bin/python src/tools/mpo_tables.py import [--env-file FILE] [--apply]
"""
import argparse
import collections
import html
import json
import pathlib
import re
import sys
import time

TOOLS_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent.parent
sys.path.insert(0, str(TOOLS_DIR))
sys.path.insert(0, str(REPO_ROOT / "src"))

import candidates as cd  # noqa: E402
import citation_closure as cc  # noqa: E402

DATA_DIR = REPO_ROOT / "data" / "20260430_MPO"
RAW_DIR = DATA_DIR / "raw"
TABLES_PATH = DATA_DIR / "mpo_tables.json"
DECISIONS_PATH = DATA_DIR / "mpo_decisions.json"
COVERAGE_PATH = DATA_DIR / "mpo_coverage.json"
CANDIDATES_PATH = DATA_DIR / "mpo_candidates.json"

WORKBOOKS = {"MPO": "Předpisy CZ - vodík_MPO.xlsx", "CDV": "CDV - evropské právní předpisy_v01.xlsx"}
COLUMNS = ("zdroj", "cislo", "nazev", "nositel", "zarazeni", "poznamka")
YELLOW = "FFFFFF00"
SOURCE = "mpo"
SOURCE_LABEL = "MPO/CDV 30. 4. 2026"
STATUSES = {"database": "v databázi", "queue": "ve frontě kandidátů", "reason": "s důvodem, proč chybí"}

# Abbreviations of the column "Nositel" for the institutions that issue the Czech acts.
INSTITUTIONS = {"MPO": "Ministerstvo průmyslu a obchodu", "ERÚ": "Energetický regulační úřad",
                "ČBÚ": "Český báňský úřad", "MŽP": "Ministerstvo životního prostředí", "MV": "Ministerstvo vnitra",
                "MMR": "Ministerstvo pro místní rozvoj", "MF": "Ministerstvo financí",
                "MPSV": "Ministerstvo práce a sociálních věcí"}
NATIONAL_PREFIXES = ("ČSN", "STN", "DIN", "BS", "NF", "ÖNORM")
_HYPHENS = str.maketrans({"‑": "-", "‐": "-", "–": "-", " ": " "})


# --- convert ------------------------------------------------------------------

def clean(value):
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value).translate(_HYPHENS)).strip()
    return text or None


def read_workbook(path, table):
    """[row] of the first sheet of `path`; the header is the first row."""
    import openpyxl
    sheet = openpyxl.load_workbook(path).worksheets[0]
    rows = []
    for cells in sheet.iter_rows(min_row=2):
        values = [clean(c.value) for c in cells[:len(COLUMNS)]]
        if not any(values):
            continue
        number = cells[0].row
        yellow = any(c.fill is not None and c.fill.fill_type and c.fill.fgColor.rgb == YELLOW for c in cells[:3])
        row = {"id": f"{table}-{number:02d}", "table": table, "sheet": sheet.title, "row": number,
               **dict(zip(COLUMNS, values)), "yellow": yellow}
        row["keys"] = row_keys(row)
        rows.append(row)
    return rows


_EU_NUMBER = re.compile(r"(\d{1,4})/(\d{1,4})/(?:EU|ES|EHS)\b")
_CZ_NUMBER = re.compile(r"^(\d{1,4})/(\d{4})(?:\s*Sb\.)?$")


def norm_designation(text):
    """`ČSN EN 60079 (řada)` → `ČSN EN 60079`, `ISO 19880-3:2018` → `ISO 19880-3`."""
    text = re.sub(r"\(řada\)", "", text or "")
    text = re.sub(r":\d{4}\b", "", text)
    return re.sub(r"\s+", " ", text).strip()


def row_keys(row):
    """The keys of the acts or standards a row names in its column "Číslo předpisu";
    [] when it has no number or the number is a technical committee."""
    number = row.get("cislo") or ""
    m = _CZ_NUMBER.match(number)
    if m and row["table"] == "MPO":
        return [f"CZ:{int(m.group(1))}/{int(m.group(2))}"]
    m = _EU_NUMBER.search(number)
    if m:
        first, second = m.group(1), m.group(2)
        if len(first) == 4 and 1950 <= int(first) <= 2035:  # (EU) 2019/776: year first
            return [f"EU:{int(first)}/{int(second)}"]
        return [f"EU:{int(second)}/{int(first)}"]  # 1302/2014/EU: number first
    found = [c for c in cc.citations(norm_designation(number)) if c.family == "NORM"]
    if found and "/TC" not in number:
        return [found[0].key]
    return []


def convert():
    rows = []
    for table, name in WORKBOOKS.items():
        rows += read_workbook(RAW_DIR / name, table)
    TABLES_PATH.write_text(json.dumps({"_popis": "Řádky tabulek MPO a CDV ze dne 30. 4. 2026 "
                                                 "(src/tools/mpo_tables.py convert).",
                                       "rows": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{TABLES_PATH.relative_to(REPO_ROOT)}: " + ", ".join(
        f"{t} {n} rows" for t, n in collections.Counter(r["table"] for r in rows).items()))


def load_rows():
    return json.loads(TABLES_PATH.read_text(encoding="utf-8"))["rows"]


def load_decisions():
    return {k: v for k, v in json.loads(DECISIONS_PATH.read_text(encoding="utf-8")).items()
            if not k.startswith("_")}


def load_candidate_details():
    """{candidate key: details} from the section `_candidates` of mpo_decisions.json."""
    return json.loads(DECISIONS_PATH.read_text(encoding="utf-8")).get("_candidates", {})


# --- matching -------------------------------------------------------------------

def norm_parts(designation):
    """(national prefix or None, number such as `19880-1`) of a standard's designation."""
    text = norm_designation(designation).translate(_HYPHENS)
    found = [c for c in cc.citations(text) if c.family == "NORM"]
    if not found:
        return None, None
    first = text.split()[0] if text else ""
    national = first if first in NATIONAL_PREFIXES else None
    return national, found[0].display.split()[-1]


class Snapshot:
    """What `compare` needs to know about a database: its documents by key, by
    identifier and as standards, and its candidates by key."""

    def __init__(self, documents, candidates):
        self.documents = {d["id"]: d for d in documents}
        self.by_key = collections.defaultdict(list)
        self.by_identifier = collections.defaultdict(list)
        self.norms = []
        for d in documents:
            for key in cc.own_keys(d["identifier"], d["title"]):
                self.by_key[key].append(d["id"])
            if d["identifier"]:
                self.by_identifier[d["identifier"].strip()].append(d["id"])
                national, number = norm_parts(d["identifier"])
                if number and d["type"] == "Norma":
                    self.norms.append((national, number, d["id"]))
        self.candidates = {c["candidate_key"]: c for c in candidates if c["candidate_key"]}

    def norm_documents(self, designation):
        """Documents of the standard `designation` in the same national adoption (a
        ČSN for a ČSN, an international one for an international one): the exact
        number, else, for a series (no part number), its parts."""
        national, number = norm_parts(designation)
        if not number:
            return []
        same = [(n, i) for nat, n, i in self.norms if nat == national]
        exact = [i for n, i in same if n == number]
        return exact or [i for n, i in same if n.startswith(number + "-")]

    def documents_for_key(self, key, designation=None):
        """Documents of one key; a standard is matched by its designation (a ČSN only by a ČSN)."""
        if key.startswith("NORM:"):
            return self.norm_documents(designation or key[5:])
        return self.by_key.get(key, [])

    def documents_of(self, row, decision):
        """{key: [document id]} for the keys of a row, and the documents named in its decision."""
        per_key = {key: self.documents_for_key(key, row.get("cislo")) for key in row_keys_with(row, decision)}
        named = []
        for identifier in decision.get("identifiers", []):
            named += self.by_identifier.get(identifier, [])
        for prefix in decision.get("title_prefixes", []):
            named += [i for i, d in self.documents.items() if (d["title"] or "").startswith(prefix)]
        return per_key, named


def row_keys_with(row, decision):
    return decision.get("keys") or row["keys"]


def candidate_key_of(designation):
    keys = sorted(cc.own_keys(designation, None))
    return keys[0] if keys else None


def classify(row, decision, snapshot):
    """The coverage record of one row."""
    keys = row_keys_with(row, decision)
    per_key, named = snapshot.documents_of(row, decision)
    document_ids = sorted(set(named + [i for ids in per_key.values() for i in ids]))
    record = {"id": row["id"], "table": row["table"], "row": row["row"], "cislo": row["cislo"], "nazev": row["nazev"],
              "yellow": row["yellow"], "keys": keys, "status": None, "documents": [], "candidates": [],
              "reason": decision.get("reason"), "note": decision.get("note")}
    for doc_id in document_ids:
        d = snapshot.documents[doc_id]
        record["documents"].append({"id": doc_id, "identifier": d["identifier"], "title": (d["title"] or "")[:160]})
    # every key without a document is a candidate; a standard by its own (national) designation
    queue_keys = [candidate_key_of(row["cislo"]) if key.startswith("NORM:") else key
                  for key, ids in per_key.items() if not ids]
    queue_keys += [candidate_key_of(d) for d in decision.get("extra_candidates", [])]
    for key in queue_keys:
        existing = snapshot.candidates.get(key)
        record["candidates"].append({"key": key, "existing_id": existing["id"] if existing else None,
                                     "existing_source": existing["source"] if existing else None,
                                     "existing_status": existing["status"] if existing else None})
    if document_ids:
        record["status"] = "database"
    elif record["candidates"]:
        record["status"] = "queue"
    elif record["reason"]:
        record["status"] = "reason"
    else:
        record["status"] = None  # a row nobody has decided about: the golden test fails on it
    return record


def load_snapshot(cursor):
    cursor.execute("""SELECT d.id, d.identifier, d.title, t.name AS type FROM Document d
                      LEFT JOIN DocumentType t ON t.id = d.type_id""")
    documents = [dict(r) for r in cursor.fetchall()]
    try:
        cursor.execute("SELECT id, candidate_key, source, status, document_id FROM DocumentCandidate")
        candidates = [dict(r) for r in cursor.fetchall()]
    except Exception:  # the table is created by the first import of candidates
        candidates = []
    return Snapshot(documents, candidates)


def connect(env_file):
    import pymysql
    import testdb
    env = testdb.read_env(env_file or testdb.find_env_file(".env"))
    return testdb.connect(env, cursorclass=pymysql.cursors.DictCursor), env["DB_NAME"]


def coverage(snapshot, rows=None, decisions=None):
    rows = rows if rows is not None else load_rows()
    decisions = decisions if decisions is not None else load_decisions()
    return [classify(row, decisions.get(row["id"], {}), snapshot) for row in rows]


def compare(env_file, output=None):
    conn, database = connect(env_file)
    try:
        with conn.cursor() as cur:
            snapshot = load_snapshot(cur)
    finally:
        conn.close()
    records = coverage(snapshot)
    output = pathlib.Path(output or COVERAGE_PATH)
    output.write_text(json.dumps({
        "_popis": f"Pokrytí tabulek MPO a CDV v databázi {database} (src/tools/mpo_tables.py compare). "
                  "status: database = dokument je v databázi, queue = předpis je ve frontě kandidátů nebo do ní "
                  "patří (candidates; existing_id prázdné = vloží jej import), reason = řádek není dokumentem "
                  "(důvod v reason).",
        "rows": records}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    counts = collections.Counter(r["status"] for r in records)
    print(f"{database}: " + ", ".join(f"{STATUSES.get(s, 'nerozhodnuto')} {n}" for s, n in counts.items()))
    for r in records:
        if r["status"] is None:
            print(f"  undecided: {r['id']} {r['cislo']} {r['nazev']}")
    return records


# --- lookup ---------------------------------------------------------------------

def scope_area(row):
    """A suggestion of the subject area (doc/DATABASE_SCOPE.md, odstavec 3) from the
    row's note and issuer; the editor confirms or changes it."""
    note = (row.get("poznamka") or "").lower()
    if "zásobník" in note:
        return 2
    if "bezpečnost" in note:
        return 7
    if (row.get("nositel") or "").startswith(("ERÚ", "MPO/ERÚ")) or "energ" in (row.get("nazev") or "").lower():
        return 9
    return None


def issuer(row):
    """The institution of the column "Nositel" (its first one when there are more)."""
    first = re.split(r"\s*/\s*", row.get("nositel") or "")[0].strip()
    return INSTITUTIONS.get(first)


def cz_metadata(session, key):
    import check_validity
    from sites import esbirka, zakonyprolidi
    number, year = key.split(":", 1)[1].split("/")
    designation = f"{number}/{year} Sb."
    url = cd.document_url(key)
    page = zakonyprolidi.extract(url, session=session) or {}
    text = page.get("description") or page.get("title") or ""
    title = re.sub(rf"^.*?č\.\s*{number}/{year}\s*Sb\.\s*-\s*", "", text)
    title = re.sub(rf"^{number}/{year}\s*Sb\.\s*", "", title).strip()
    repeal_note = re.search(r"\s+-\s+(zrušeno k .*)$", title)
    title = (title[:repeal_note.start()] if repeal_note else title).strip() or None
    validity = check_validity.cz_status(session, [key], time.strftime("%Y-%m-%d")).get(key, {})
    return {"designation": designation, "title": title, "document_type": cd.czech_type(title), "url": url,
            "jurisdikce": "CZ", "language": "CS", "validity_status": validity.get("status"),
            "evidence": {"esbirka_url": esbirka.verify(designation, session=session),
                         "repeal_note": repeal_note.group(1) if repeal_note else None,
                         "title_source": url if title else None, "validity": validity}}


def eu_metadata(session, key):
    import check_validity
    from sites import eurlex
    for kind in ("regulation", "directive", "decision"):
        url = cd.document_url(key, kind)
        page = eurlex.extract(url, session=session)
        if page:
            break
    else:
        return {"designation": cd.designation(key), "title": None, "url": None, "jurisdikce": "EU", "language": "CS",
                "document_type": "Nezařazeno", "validity_status": None, "evidence": {}}
    validity = check_validity.eu_status(session, [(key, kind)], time.strftime("%Y-%m-%d")).get(key, {})
    return {"designation": cd.designation(key, kind), "title": page["title"].replace(" ", " "),
            "document_type": cd.EU_TYPES[kind], "url": url, "jurisdikce": "EU", "language": "CS",
            "validity_status": validity.get("status"),
            "evidence": {"celex": cd.celex(key, kind), "title_source": url, "validity": validity}}


def csn_metadata(session, designation):
    import check_csn_validity as csn
    national, number = norm_parts(designation)
    query = designation.split(" ", 1)[1]
    results = csn.search(session, query)
    best = csn.find_best_match(results, designation)
    if best and not best["is_valid"]:
        # a designation without its edition ("ČSN EN 60079-1") matches its first, withdrawn edition exactly;
        # a valid later edition of the same designation ("ČSN EN 60079-1 ed. 3") is the one meant
        base = csn.split_edition(csn.strip_catalog_suffix(designation))[0].lower()
        later = [r for r in results if r.get("is_valid") and r.get("title")
                 and not csn._AMENDMENT_TITLE_RE.match(r["title"])
                 and csn.split_edition(re.sub(r"\s+", " ", r["designation"]).lower())[0] == base]
        if later:
            best = max(later, key=lambda r: csn._parse_issued(r.get("issued", "")))
    detail = csn.fetch_detail(best["catalog_number"], session) if best and best.get("catalog_number") else None
    title = (detail or best or {}).get("title")
    return {"designation": designation, "title": html.unescape(title) if title else None, "document_type": "Norma",
            "url": detail["url"] if detail else None, "jurisdikce": "CZ", "language": "CS",
            "validity_status": ("platná" if best["is_valid"] else "zrušená") if best else None,
            "evidence": {"title_source": detail["url"] if detail else None,
                         "edition": best.get("designation") if best else None,
                         "issued": best.get("issued") if best else None,
                         "incorporates": (detail or {}).get("incorporates")}}


def fetch_metadata(session, key, designation):
    """Title, address and validity of one candidate from its authoritative source."""
    if key.startswith("CZ:"):
        return cz_metadata(session, key)
    if key.startswith("EU:"):
        return eu_metadata(session, key)
    return csn_metadata(session, designation)


def apply_details(candidate, row, details):
    """The issuer, subject area and evidence a candidate gets from its first MPO row,
    overridden by its details in mpo_decisions.json (`_candidates`)."""
    key = candidate["candidate_key"]
    if key.startswith("NORM:"):
        puvodce = "Česká agentura pro standardizaci (ČAS)"
    else:
        puvodce = issuer(row) if row["table"] == "MPO" else None
    candidate.update({"source": SOURCE, "puvodce": details.get("puvodce", puvodce),
                      "scope_area": details.get("scope_area", scope_area(row))})
    if details.get("signal"):
        candidate["signal"] = details["signal"]
    for field in ("alias", "amends", "basis"):
        if details.get(field):
            candidate["evidence"][field] = details[field]
    return candidate


def lookup(refresh=False):
    """Writes mpo_candidates.json: the network metadata of a candidate already there
    is reused unless `refresh`; its rows, issuer and details are always recomputed."""
    import requests
    records = json.loads(COVERAGE_PATH.read_text(encoding="utf-8"))["rows"]
    rows = {r["id"]: r for r in load_rows()}
    decisions = load_decisions()
    details = load_candidate_details()
    known = {} if refresh or not CANDIDATES_PATH.exists() else {c["candidate_key"]: c for c in load_candidates()}
    session = requests.Session()
    session.headers["User-Agent"] = cd_user_agent()
    found = {}
    fetched = 0
    for record in records:
        row = rows[record["id"]]
        extra = {candidate_key_of(d): d for d in decisions.get(record["id"], {}).get("extra_candidates", [])}
        for entry in record["candidates"]:
            key = entry["key"]
            if key in found:
                found[key]["evidence"]["mpo_rows"].append(mpo_evidence(row))
                continue
            if key in known:
                metadata = {k: v for k, v in known[key].items() if k not in ("source", "puvodce", "scope_area", "signal")}
                metadata["evidence"] = {k: v for k, v in metadata["evidence"].items()
                                        if k not in ("mpo_rows", "alias", "amends", "basis")}
            else:
                metadata = fetch_metadata(session, key, extra.get(key) or norm_designation(row["cislo"]))
                fetched += 1
                print(f"  {key:24} {metadata['validity_status'] or '-':14} "
                      f"{(metadata['title'] or '— NO TITLE —')[:90]}")
                time.sleep(1)
            metadata["candidate_key"] = key
            metadata["evidence"]["mpo_rows"] = [mpo_evidence(row)]
            found[key] = apply_details(metadata, row, details.get(key, {}))
    CANDIDATES_PATH.write_text(json.dumps({
        "_popis": f"Kandidáti ze zdroje „{SOURCE_LABEL}“ s autoritativním názvem, adresou a platností "
                  "(src/tools/mpo_tables.py lookup); vkládá je src/tools/mpo_tables.py import.",
        "candidates": sorted(found.values(), key=lambda c: c["candidate_key"])},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(found)} candidates ({fetched} looked up), {sum(1 for c in found.values() if c['title'])} with a title")


def cd_user_agent():
    import import_candidates
    return import_candidates.USER_AGENT


def mpo_evidence(row):
    return {"row": row["id"], "sheet": row["sheet"], "cislo": row["cislo"], "nazev": row["nazev"],
            "nositel": row["nositel"], "zdroj": row["zdroj"], "poznamka": row["poznamka"]}


# --- import ---------------------------------------------------------------------

def load_candidates():
    return json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))["candidates"]


def amends_ids(candidate, snapshot):
    """The ids of the documents of the acts a candidate amends (`evidence.amends`)
    in the database of `snapshot`; an amended act not in the database is left out."""
    ids = set()
    for key in candidate["evidence"].get("amends", []):
        ids.update(snapshot.documents_for_key(key))
    return sorted(ids)


def planned_outcome(candidate, existing):
    """What write_candidates does with a candidate, from the queue row of its key
    (None when it is not there): `inserted`, `refreshed` (own source, not decided),
    `evidence` (another source's candidate gets the MPO rows) or `kept`."""
    if existing is None:
        return "inserted"
    if existing["status"] in ("accepted", "rejected", "proposed"):
        return "kept"
    if existing["source"] == SOURCE:
        return "refreshed"
    return "evidence"


def write_candidates(cursor, found, snapshot=None):
    """Puts the candidates into DocumentCandidate; returns {key: outcome}, see
    planned_outcome (`refreshed` and `evidence` become `kept` when nothing changed).
    Running it again changes nothing."""
    cd.ensure_schema(cursor)
    snapshot = snapshot or load_snapshot(cursor)
    outcome = {}
    for c in found:
        evidence_new = dict(c["evidence"])
        ids = amends_ids(c, snapshot)
        if ids:
            evidence_new["amends_ids"] = ids
        evidence_new["puvodce_navrh"] = c["puvodce"]  # tells a later run whether an editor changed the issuer
        cursor.execute("SELECT id, source, status, evidence_json, puvodce, validity_status, `signal` "
                       "FROM DocumentCandidate WHERE candidate_key = %s", (c["candidate_key"],))
        row = cursor.fetchone()
        action = planned_outcome(c, row)
        if action == "inserted":
            cursor.execute("""INSERT INTO DocumentCandidate
                (candidate_key, source, `signal`, designation, title, document_type, url, language, jurisdikce,
                 scope_area, validity_status, evidence_json, cited_by, puvodce)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0, %s)""",
                           (c["candidate_key"], SOURCE, c.get("signal"), c["designation"], c["title"],
                            c["document_type"], c["url"], c["language"], c["jurisdikce"], c["scope_area"],
                            c["validity_status"], json.dumps(evidence_new, ensure_ascii=False), c["puvodce"]))
        elif action == "refreshed":
            old = json.loads(row["evidence_json"] or "{}")
            # what other tools added (findings of monitored sources) stays; the editor's issuer stays
            evidence = {**{k: v for k, v in old.items() if k not in evidence_new and k != "amends_ids"},
                        **evidence_new}
            if "amends_ids" in old and "amends_ids" not in evidence_new:
                evidence["amends_ids"] = old["amends_ids"]
            editor_changed = row["puvodce"] not in (None, old.get("puvodce_navrh"))
            puvodce = row["puvodce"] if editor_changed else c["puvodce"]
            values = (json.dumps(evidence, ensure_ascii=False), c["validity_status"], puvodce,
                      c.get("signal") or row["signal"])
            if values == (row["evidence_json"], row["validity_status"], row["puvodce"], row["signal"]):
                action = "kept"
            else:
                cursor.execute("UPDATE DocumentCandidate SET evidence_json = %s, validity_status = %s, puvodce = %s, "
                               "`signal` = %s WHERE id = %s", values + (row["id"],))
        elif action == "evidence":
            evidence = json.loads(row["evidence_json"] or "{}")
            before = json.dumps(evidence, ensure_ascii=False, sort_keys=True)
            evidence["mpo_rows"] = c["evidence"]["mpo_rows"]
            if ids:
                evidence["amends_ids"] = sorted(set(evidence.get("amends_ids", [])) | set(ids))
            if (json.dumps(evidence, ensure_ascii=False, sort_keys=True) == before
                    and (row["puvodce"] or c["puvodce"]) == row["puvodce"]):
                action = "kept"
            else:
                cursor.execute("UPDATE DocumentCandidate SET evidence_json = %s, puvodce = COALESCE(puvodce, %s) "
                               "WHERE id = %s", (json.dumps(evidence, ensure_ascii=False), c["puvodce"], row["id"]))
        outcome[c["candidate_key"]] = action
    return outcome


def import_candidates(env_file, apply):
    found = load_candidates()
    conn, database = connect(env_file)
    try:
        with conn.cursor() as cur:
            snapshot = load_snapshot(cur)
            planned = [c for c in found if not snapshot.documents_for_key(c["candidate_key"], c["designation"])]
            for c in planned:
                existing = snapshot.candidates.get(c["candidate_key"])
                state = f"{planned_outcome(c, existing)}" + (f" ({existing['source']}, {existing['status']})"
                                                              if existing else "")
                amended = amends_ids(c, snapshot)
                print(f"  {c['candidate_key']:26} {state:30} {(c['title'] or '')[:70]}"
                      + (f"  AMENDS {amended}" if amended else ""))
            skipped = len(found) - len(planned)
            if not apply:
                counts = collections.Counter(planned_outcome(c, snapshot.candidates.get(c["candidate_key"]))
                                             for c in planned)
                print(f"{database}: {len(planned)} candidates, " + ", ".join(f"{v} {k}" for k, v in counts.items())
                      + f"; {skipped} already documents (dry run — add --apply)")
                return None
            outcome = write_candidates(cur, planned, snapshot)
        conn.commit()
    finally:
        conn.close()
    print(f"{database}: " + ", ".join(f"{v} {k}" for k, v in collections.Counter(outcome.values()).items())
          + f"; {skipped} already documents")
    return outcome


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("command", choices=("convert", "compare", "lookup", "import"))
    parser.add_argument("--env-file", default=None, help="database to read (compare) or write (import); default .env")
    parser.add_argument("--apply", action="store_true", help="import: write to the database (dry run without it)")
    parser.add_argument("--refresh", action="store_true", help="lookup: ask the network again also for the "
                                                                "candidates already in mpo_candidates.json")
    parser.add_argument("--output", default=None, help="compare: write the coverage here instead of "
                                                         "data/20260430_MPO/mpo_coverage.json")
    args = parser.parse_args(argv)
    if args.command == "convert":
        convert()
    elif args.command == "compare":
        compare(args.env_file, args.output)
    elif args.command == "lookup":
        lookup(args.refresh)
    else:
        import_candidates(args.env_file, args.apply)


if __name__ == "__main__":
    main()
