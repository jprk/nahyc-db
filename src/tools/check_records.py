"""Checks the records of the database against the official registers and against
each other (doc/KONTROLA_ZAZNAMU.md).

Why: part of the metadata came from language models (process_laws.py gave the Sinay
survey's bare numbers a Czech title and a description; enrich_annotations.py wrote
descriptions). Two of those titles named another act than the number (#86, #91,
corrected 2026-11-23), one more had been found before ((EU) 2023/1234). The checks:

Official registers
- `eu_*` — an EU act (Cellar): the number exists as exactly one act (`eu_not_found`,
  `eu_ambiguous`); our title names the same act as the official title in the language
  of the document (`eu_title`); the type of the document matches the kind of act
  (`eu_type`); the date in our title is the date of the act (`eu_date`).
- `iso_*` — a standard with an ISO designation (ISO Open Data, iso_open_data.py): ISO
  lists it (`iso_not_found`); a draft we list has been published (`iso_draft_published`);
  the edition is withdrawn or replaced (`iso_withdrawn`); an English title names the same
  standard (`iso_title`).
- `auth_title` — the title differs from the authoritative title we fetched before
  (`nazev_autoritativni`: zakonyprolidi.cz, slov-lex.sk, the ČAS catalogue).

Within the database
- `number_not_in_title` — the number of the identifier is not in the title (standards, Czech acts).
- `bad_identifier` — a standard whose identifier is a piece of another one ("A1/ - 2024.03", "Part 1").
- `title_fragment` — the title of a standard (after its designation) begins with a small letter,
  or a note stands in place of the title.
- `type_vs_title` — the type says "Směrnice EU" and the title begins "Nařízení" (and so on).
- `duplicate_title` — two documents in the same language with nearly the same title and
  different identifiers, not linked as language variants or editions.

Each finding has a severity: `error` (the record names another document or none),
`warning` (to be checked by an editor), `info`. The report goes to
data/record_checks.json; the official titles fetched from Cellar are cached in
data/official_titles_cache.json.

    .venv/bin/python src/tools/check_records.py                 # live DB, read only
    .venv/bin/python src/tools/check_records.py --env-file .env.test --refresh

Reads the database and never writes it.
"""
import argparse
import collections
import datetime
import json
import pathlib
import re
import sys
import time
import unicodedata

import requests

import check_validity as cv
import document_terms as dterms
import fetch_eurovoc
import iso_open_data
import state_paths

REPO_ROOT = dterms.REPO_ROOT
REPORT_PATH = state_paths.data_file("record_checks.json")
TITLES_CACHE = state_paths.data_file("official_titles_cache.json")
LANGUAGES = {"CS": "CES", "EN": "ENG", "SK": "SLK", "DE": "DEU"}
SIMILAR = 0.5       # below: the titles name different documents
DUPLICATE = 0.9     # at or above: two titles are the same
EU_TYPES = {"Nařízení EU": "R", "Směrnice EU": "L", "Rozhodnutí EU": "D"}
TITLE_KINDS = [("nařízení", "R"), ("směrnice", "L"), ("rozhodnutí", "D"), ("nariadenie", "R"), ("smernica", "L"),
               ("rozhodnutie", "D"), ("regulation", "R"), ("directive", "L"), ("decision", "D")]
MONTHS = {m: i for i, m in enumerate(["ledna", "února", "března", "dubna", "května", "června", "července", "srpna",
                                      "září", "října", "listopadu", "prosince"], 1)}
# words of the titles of acts that say nothing about their subject
BOILERPLATE = set("""evropského parlamentu rady komise nařízení směrnice rozhodnutí prováděcí delegované přenesené
pravomoci kterým kterou kterým kterou stanoví mění zrušuje dne text významem pro ehp european parliament council
commission regulation directive decision implementing delegated laying down amending repealing with relevance
text eea európskeho parlamentu rady komisie nariadenie smernica rozhodnutie vykonávacie ktorým ktorou ustanovuje
mení zrušuje významom týkajúci""".split())


# --- text helpers -----------------------------------------------------------

def _fold(text):
    text = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def words(text):
    """The subject words of a title: four letters or more, no boilerplate, no diacritics."""
    folded_boiler = {_fold(w) for w in BOILERPLATE}
    return {w for w in re.findall(r"[a-z]{4,}", _fold(text)) if w not in folded_boiler}


def similarity(a, b):
    """The share of the subject words of the shorter title found in the other one (0–1)."""
    wa, wb = words(a), words(b)
    if not wa or not wb:
        return None
    return len(wa & wb) / min(len(wa), len(wb))


def title_date(text):
    """The date of an act named in a Czech title ("ze dne 10. května 2023"), ISO, or None."""
    m = re.search(r"ze dne\s+(\d{1,2})\.\s*([a-zúéěíáčřžš]+)\s+(\d{4})", (text or "").replace("\xa0", " "))
    if not m or m.group(2) not in MONTHS:
        return None
    return f"{m.group(3)}-{MONTHS[m.group(2)]:02d}-{int(m.group(1)):02d}"


def title_kind(text):
    """The kind of EU act ("R", "L", "D") the title begins with, or None."""
    head = re.sub(r"^\(?\s*(EU|EÚ|ES|EHS)\)?\s*[\d/]+\s*[-–—]\s*", "", (text or "").strip(), flags=re.I)
    first = head.split()[0].lower() if head.split() else ""
    for prefix in ("prováděcí", "delegované", "vykonávacie", "delegované", "commission", "council"):
        if first == prefix and len(head.split()) > 1:
            first = head.split()[1].lower()
    for word, kind in TITLE_KINDS:
        if first.startswith(word):
            return kind
    return None


def identifier_numbers(identifier):
    """The numbers of an identifier a title must repeat: "(EU) 2023/955" -> ["2023/955", "955/2023"]
    (an older act is cited "č. 1907/2006"); "ČSN EN ISO 15330" -> ["15330"]."""
    ident = re.sub(r"\[[A-Z]{2}\]", "", identifier or "")
    m = re.search(r"(\d{4})\s*/\s*(\d{1,4})", ident)
    if m and re.search(r"EU|EÚ|ES|EHS|EC|EEC", ident):
        return [f"{m.group(1)}/{m.group(2)}", f"{m.group(2)}/{m.group(1)}"]
    m = re.search(r"(\d{1,4})\s*/\s*(\d{4})\s*Sb", ident)
    if m:
        return [f"{m.group(1)}/{m.group(2)}"]
    ident = re.sub(r"[-–:]\s*(19|20)\d{2}\b.*$", "", ident)  # "AS 2022-1983", "ISO 9809-1:2019"
    m = re.search(r"(\d{3,6}(?:-\d+)*)", ident)
    return [m.group(1)] if m else []


# an identifier that is a piece of another one: "/ - 2024.08", "A1/ - 2024.03", "Part 1", "AC"
_FRAGMENT_IDENTIFIER = re.compile(r"^\s*(/|[-–]|A\d+\b|AC\b|Amd\b|Part\s+\d|Časť\s+\d|Teil\s+\d|\d+\s*$)", re.I)


def _compact(text):
    return re.sub(r"\s+", "", (text or "").replace("\xa0", " "))


# --- official data ----------------------------------------------------------

CELLAR_QUERY = """PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
SELECT ?celex ?date ?lang ?title WHERE {{
  VALUES ?celex {{ {values} }}
  ?w cdm:resource_legal_id_celex ?celex .
  OPTIONAL {{ ?w cdm:work_date_document ?date }}
  OPTIONAL {{ ?e cdm:expression_belongs_to_work ?w ; cdm:expression_title ?title ;
               cdm:expression_uses_language ?l .
             VALUES ?l {{ <http://publications.europa.eu/resource/authority/language/CES>
                         <http://publications.europa.eu/resource/authority/language/ENG>
                         <http://publications.europa.eu/resource/authority/language/SLK>
                         <http://publications.europa.eu/resource/authority/language/DEU> }}
             BIND(STRAFTER(STR(?l), "language/") AS ?lang) }}
}}"""


def fetch_cellar(session, celexes, cache, today, sleep=1.0, refresh=False):
    """Fills `cache` — {celex: {"exists", "date", "titles": {lang: title}, "fetched"}} — for `celexes`."""
    todo = sorted(c for c in set(celexes) if refresh or c not in cache)
    for start in range(0, len(todo), 30):
        batch = todo[start:start + 30]
        values = " ".join(f'"{c}"^^<http://www.w3.org/2001/XMLSchema#string>' for c in batch)
        for celex in batch:
            cache[celex] = {"exists": False, "date": None, "titles": {}, "fetched": today}
        for row in cv._sparql(session, cv.CELLAR, CELLAR_QUERY.format(values=values)):
            entry = cache[row["celex"]["value"]]
            entry["exists"] = True
            if "date" in row:
                entry["date"] = row["date"]["value"][:10]
            if "title" in row:
                entry["titles"][row["lang"]["value"]] = " ".join(row["title"]["value"].split())
        time.sleep(sleep)
    return cache


# --- the checks -------------------------------------------------------------

def finding(doc, check, severity, detail, **evidence):
    return {"id": doc["id"], "identifier": doc["identifier"], "slug": doc.get("slug"), "check": check,
            "severity": severity, "detail": detail, **evidence}


def check_eu(doc, celexes, cellar):
    out = []
    hits = [c for c in celexes if cellar.get(c, {}).get("exists")]
    if not hits:
        return [finding(doc, "eu_not_found", "error", "Číslo aktu v Cellaru neexistuje.", celex=celexes)]
    if len(hits) > 1:
        kind = EU_TYPES.get(doc["type"])
        narrowed = [c for c in hits if kind and c[5] == kind]
        if len(narrowed) != 1:
            return [finding(doc, "eu_ambiguous", "warning", "Číslu odpovídá více aktů: " + ", ".join(hits), celex=hits)]
        hits = narrowed
    celex = hits[0]
    entry = cellar[celex]
    url = f"https://eur-lex.europa.eu/legal-content/{doc['language'] or 'CS'}/ALL/?uri=CELEX:{celex}"
    official = entry["titles"].get(LANGUAGES.get(doc["language"] or "CS", "CES")) or entry["titles"].get("ENG")
    if official:
        score = similarity(doc["title"], official)
        if score is not None and score < SIMILAR:
            out.append(finding(doc, "eu_title", "error",
                               "Název v databázi popisuje jiný akt než úřední název.",
                               celex=celex, score=round(score, 2), title=doc["title"], official=official, url=url))
    kind = EU_TYPES.get(doc["type"])
    if kind and celex[5] in "RLD" and celex[5] != kind:
        out.append(finding(doc, "eu_type", "warning",
                           f"Typ dokumentu „{doc['type']}“ neodpovídá druhu aktu ({celex}).", celex=celex, url=url))
    ours = title_date(doc["title"])
    if ours and entry.get("date") and ours != entry["date"]:
        out.append(finding(doc, "eu_date", "error", f"Datum v názvu {ours} se liší od data aktu {entry['date']}.",
                           celex=celex, url=url))
    return out


def check_iso(doc, international, index):
    record = iso_open_data.lookup(index, international)
    if record is None:
        if international.startswith("ISO"):
            return [finding(doc, "iso_not_found", "warning", f"ISO normu „{international}“ neuvádí.")]
        return []
    summary = iso_open_data.summary(record)
    out = []
    stage = record.get("currentStage") or 0
    draft = re.match(r"ISO/(AWI|PWI|NP|WD|CD|DIS|FDIS)\b", international)
    if draft and iso_open_data.PUBLISHED <= stage < iso_open_data.WITHDRAWN:
        out.append(finding(doc, "iso_draft_published", "warning",
                           f"Návrh {international} ISO vydala jako {record['reference']} ({record.get('publicationDate')}).",
                           **summary))
    if stage >= iso_open_data.WITHDRAWN:
        out.append(finding(doc, "iso_withdrawn", "info",
                           f"Poslední vydání {record['reference']} ISO zrušila (stav {stage}).", **summary))
    if (doc["language"] or "") == "EN" and summary.get("title_en"):
        score = similarity(doc["title"], summary["title_en"])
        if score is not None and score < SIMILAR:
            # a project may change its title before it is published
            severity = "warning" if draft or stage < iso_open_data.PUBLISHED else "error"
            out.append(finding(doc, "iso_title", severity, "Název v databázi se liší od názvu normy v ISO.",
                               score=round(score, 2), title=doc["title"], official=summary["title_en"], **summary))
    return out


def check_authoritative(doc):
    official = doc.get("nazev_autoritativni")
    if not official:
        return []
    score = similarity(doc["title"], official)
    if score is None or score >= SIMILAR:
        return []
    return [finding(doc, "auth_title", "error", "Název se liší od autoritativního názvu ze zdrojového webu.",
                    score=round(score, 2), title=doc["title"], official=official, url=doc.get("zdroj_autoritativni_url"))]


def check_internal(doc):
    """The number check applies to standards (their title begins with the designation) and
    Czech acts; a Slovak act and a Commission communication do not repeat their number, and
    an EU act is compared with its official title."""
    out = []
    numbers = identifier_numbers(doc["identifier"]) if (doc["type"] == "Norma" or "Sb." in (doc["identifier"] or "")) else []
    title = _compact(doc["title"])
    if numbers and not any(_compact(n) in title for n in numbers):
        out.append(finding(doc, "number_not_in_title", "warning",
                           f"Číslo {numbers[0]} z označení v názvu není.", title=doc["title"]))
    if doc["type"] == "Norma" and _FRAGMENT_IDENTIFIER.match(doc["identifier"] or ""):
        out.append(finding(doc, "bad_identifier", "error",
                           "Označení je úlomek (část jiného označení nebo jiného řádku zdroje), ne označení normy.",
                           title=doc["title"]))
    subject = doc["title"].split(" — ", 1)[1] if " — " in doc["title"] else ""
    if doc["type"] == "Norma" and subject[:1].islower():
        out.append(finding(doc, "title_fragment", "warning",
                           "Název normy začíná malým písmenem, nejspíš je useknutý.", title=doc["title"]))
    if re.match(r"^\s*(Poznámka|Pozn\.|Note|Anmerkung)\b", subject or doc["title"], re.I):
        out.append(finding(doc, "title_fragment", "warning", "Místo názvu je poznámka.", title=doc["title"]))
    kind = EU_TYPES.get(doc["type"])
    found = title_kind(doc["title"])
    if kind and found and kind != found:
        out.append(finding(doc, "type_vs_title", "warning",
                           f"Typ „{doc['type']}“ neodpovídá názvu.", title=doc["title"]))
    return out


def check_duplicates(documents, linked):
    """Pairs of documents in the same language with nearly the same title and different
    identifiers, not linked (`linked`: set of frozenset({id, id}))."""
    out = []
    by_language = collections.defaultdict(list)
    for doc in documents:
        ws = words(doc["title"])
        if len(ws) >= 4:
            by_language[doc["language"] or ""].append((doc, ws))
    for docs in by_language.values():
        for i, (a, wa) in enumerate(docs):
            for b, wb in docs[i + 1:]:
                if frozenset((a["id"], b["id"])) in linked or a["identifier"] == b["identifier"]:
                    continue
                score = len(wa & wb) / max(len(wa), len(wb))
                if score >= DUPLICATE and not _editions(a["identifier"], b["identifier"]):
                    out.append(finding(a, "duplicate_title", "warning",
                                       f"Téměř shodný název má dokument #{b['id']} ({b['identifier']}).",
                                       other_id=b["id"], other_identifier=b["identifier"], score=round(score, 2),
                                       title=a["title"], other_title=b["title"]))
    return out


def _editions(a, b):
    """Two identifiers of editions or parts of the same series ("ISO 11114-1" / "ISO 11114-2")."""
    na, nb = re.findall(r"\d+", a or ""), re.findall(r"\d+", b or "")
    return bool(na and nb and na != nb)


# --- running ----------------------------------------------------------------

def load(cursor):
    cursor.execute("SELECT d.id, d.identifier, d.slug, d.title, d.language, dt.name, d.nazev_autoritativni, "
                   "d.zdroj_autoritativni_url, d.url FROM Document d LEFT JOIN DocumentType dt ON dt.id = d.type_id")
    documents = [{"id": r[0], "identifier": r[1], "slug": r[2], "title": r[3] or "", "language": r[4], "type": r[5],
                  "nazev_autoritativni": r[6], "zdroj_autoritativni_url": r[7], "url": r[8]}
                 for r in cursor.fetchall()]
    cursor.execute("SELECT from_document_id, to_document_id FROM document_relation")
    linked = {frozenset(r) for r in cursor.fetchall()}
    return documents, linked


def run(documents, linked, cellar, iso_index):
    import fetch_ics
    rows = [(d["id"], d["identifier"], d["url"], d["type"], d["title"], d["language"], None, None) for d in documents]
    acts = fetch_eurovoc.eu_acts(rows)
    keys = dterms.document_keys(rows)
    findings = []
    for doc in documents:
        key = keys[doc["id"]]
        if key in acts:
            findings += check_eu(doc, acts[key], cellar)
        if doc["type"] == "Norma":
            international = fetch_ics.international_part(doc["identifier"])
            if international:
                findings += check_iso(doc, international, iso_index)
        findings += check_authoritative(doc)
        findings += check_internal(doc)
    findings += check_duplicates(documents, linked)
    order = {"error": 0, "warning": 1, "info": 2}
    findings.sort(key=lambda f: (order[f["severity"]], f["check"], f["id"]))
    return findings, acts


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--refresh", action="store_true", help="fetch the official titles from Cellar again")
    parser.add_argument("--iso-data", default=None)
    parser.add_argument("--report", default=str(REPORT_PATH))
    args = parser.parse_args(argv)
    conn = dterms.connect(args.env_file)
    try:
        documents, linked = load(conn.cursor())
    finally:
        conn.close()
    iso_path = pathlib.Path(args.iso_data or iso_open_data.DEFAULT_PATH)
    if not iso_path.exists():
        iso_open_data.download(iso_path)
    iso_index = iso_open_data.load_index(iso_path)
    rows = [(d["id"], d["identifier"], d["url"], d["type"], d["title"], d["language"], None, None) for d in documents]
    acts = fetch_eurovoc.eu_acts(rows)
    cellar = dterms.load_cache(TITLES_CACHE)
    today = datetime.date.today().isoformat()
    fetch_cellar(requests.Session(), [c for cs in acts.values() for c in cs], cellar, today, refresh=args.refresh)
    dterms.save_cache(TITLES_CACHE, cellar)
    findings, _ = run(documents, linked, cellar, iso_index)
    report = {"checked_at": today, "documents": len(documents),
              "counts": dict(collections.Counter(f"{f['severity']}:{f['check']}" for f in findings)),
              "findings": findings}
    pathlib.Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for name, n in sorted(report["counts"].items()):
        print(f"{name:32s} {n:5d}")
    print(f"{len(findings)} findings over {len({f['id'] for f in findings})} documents -> {args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
