"""Candidates for new documents and the decisions about them
(table `DocumentCandidate`, the editor pages under /admin/candidates).

A candidate is a document that some check says the database may be missing:
an act that the texts in the database cite (citation_closure.py), the act that
repealed a document of the database (check_validity.py), later a find of a
grabber, or a document an editor proposes by hand. Every candidate is identified
by the same key the checks use (`CZ:505/1990`, `EU:2003/87`, see
citation_closure.own_keys), so a later run of a check only refreshes the evidence
of a candidate it has already reported and never asks again about one an editor
has rejected. Decisions are kept: they are the documented negative results that
doc/DATABASE_SCOPE.md (odstavec 6) asks for.

States: `new` → `proposed` (an editor proposes acceptance, with the metadata the
document will get) → `accepted` (a second, different editor confirms; the document
is created in the database at once); `rejected` and `deferred` need one editor;
both can be reopened (back to `new`).
"""
import json
import re
import time

import citation_closure as cc

STATES = ("new", "proposed", "accepted", "rejected", "deferred")
OPEN_STATES = ("new", "proposed", "deferred")
SOURCES = {"citation": "citace v textech databáze", "validity": "nástupce zrušeného dokumentu",
           "manual": "ruční návrh"}
# Subject areas of doc/DATABASE_SCOPE.md odstavec 3.
SCOPE_AREAS = {1: "Výroba vodíku", 2: "Skladování", 3: "Přeprava", 4: "Plnění do vozidel",
               5: "Provoz vozidel", 6: "Využití vodíku mimo vozidla", 7: "Bezpečnost",
               8: "Stavební řízení a umístění", 9: "Energetika", 10: "Životní prostředí"}
EU_TYPES = {"regulation": "Nařízení EU", "directive": "Směrnice EU", "decision": "Rozhodnutí EU"}
CELEX_LETTERS = {"regulation": "R", "directive": "L", "decision": "D"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS DocumentCandidate (
  id INT AUTO_INCREMENT PRIMARY KEY,
  candidate_key VARCHAR(120) NULL,
  source VARCHAR(50) NOT NULL,
  designation VARCHAR(200) NULL,
  title VARCHAR(1000) NULL,
  document_type VARCHAR(100) NULL,
  url VARCHAR(1000) NULL,
  language VARCHAR(10) NULL,
  jurisdikce VARCHAR(20) NULL,
  scope_area TINYINT NULL,
  validity_status VARCHAR(30) NULL,
  evidence_json TEXT NULL,
  cited_by INT NOT NULL DEFAULT 0,
  status ENUM('new','proposed','accepted','rejected','deferred') NOT NULL DEFAULT 'new',
  decision_note VARCHAR(1000) NULL,
  proposed_by_user_id INT NULL,
  proposed_at TIMESTAMP NULL,
  confirmed_by_user_id INT NULL,
  confirmed_at TIMESTAMP NULL,
  decided_by_user_id INT NULL,
  decided_at TIMESTAMP NULL,
  document_id INT NULL,
  created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_candidate_key (candidate_key),
  KEY idx_candidate_status (status),
  CONSTRAINT fk_dc_proposer FOREIGN KEY (proposed_by_user_id) REFERENCES User (id),
  CONSTRAINT fk_dc_confirmer FOREIGN KEY (confirmed_by_user_id) REFERENCES User (id),
  CONSTRAINT fk_dc_decider FOREIGN KEY (decided_by_user_id) REFERENCES User (id),
  CONSTRAINT fk_dc_document FOREIGN KEY (document_id) REFERENCES Document (id) ON DELETE SET NULL,
  CONSTRAINT chk_dc_distinct_reviewers CHECK (confirmed_by_user_id IS NULL OR confirmed_by_user_id <> proposed_by_user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_czech_ci
"""


def ensure_schema(cursor):
    cursor.execute(SCHEMA)


# --- what a key looks like as a document ----------------------------------

def _eu_parts(key):
    year, number = key.split(":", 1)[1].split("/")
    return int(year), int(number)


def designation(key, kind=None):
    """The designation a document of `key` gets, written the way the database
    writes it, so that citation_closure.own_keys() reads the same key back:
    `505/1990 Sb.`, `(EU) 2019/943`, `(ES) č. 715/2009`, `2003/87/ES`."""
    family = key.split(":", 1)[0]
    if family == "CZ":
        return f"{key.split(':', 1)[1]} Sb."
    if family != "EU":
        return key.split(":", 1)[1]
    year, number = _eu_parts(key)
    body = "EU" if year >= 2010 else ("ES" if year >= 1993 else "EHS")
    if kind == "regulation":
        return f"(EU) {year}/{number}" if year >= 2015 else f"({body}) č. {number}/{year}"
    return f"{year}/{number}/{body}"


def celex(key, kind):
    if not key.startswith("EU:") or kind not in CELEX_LETTERS:
        return None
    year, number = _eu_parts(key)
    return f"3{year}{CELEX_LETTERS[kind]}{number:04d}"


def document_url(key, kind=None, cached_celex=None):
    """Where the document is read: EUR-Lex (Czech version) or zakonyprolidi.cz, the
    two sites fetch_fulltext.py downloads from."""
    if key.startswith("CZ:"):
        number, year = key.split(":", 1)[1].split("/")
        return f"https://www.zakonyprolidi.cz/cs/{year}-{number}"
    number = cached_celex or celex(key, kind)
    return f"https://eur-lex.europa.eu/legal-content/CS/TXT/?uri=CELEX:{number}" if number else None


def czech_type(title):
    """The DocumentType of a Czech act from its title."""
    text = (title or "").lower()
    for start, name in (("nařízení vlády", "Nařízení vlády"), ("zákon", "Zákon"), ("ústavní zákon", "Zákon"),
                        ("vyhláška", "Vyhláška")):
        if text.startswith(start) or re.match(r"^\d+/\d{4} sb\.\s+" + start, text):
            return name
    return "Nezařazeno"


def kind_from_celex(number):
    letter = (re.fullmatch(r"3\d{4}([RLD])\d{4}", number or "") or [None, None])[1]
    return {v: k for k, v in CELEX_LETTERS.items()}.get(letter)


# --- candidates from the checks --------------------------------------------

def from_closure(rows, cache, minimum=2):
    """Candidates from the citation closure: missing Czech and EU acts, cited by at
    least `minimum` documents, not mainly as amending acts, and not repealed."""
    found = []
    for row in rows:
        if row["family"] not in ("CZ", "EU") or row["in_database"] or row["cited_by"] < minimum \
                or row["amendment_share"] >= 0.5:
            continue
        validity = cache.get(row["key"], {})
        if validity.get("status") == "zrušený":
            continue
        kind = kind_from_celex(validity.get("celex")) or row["kind"]
        found.append({
            "candidate_key": row["key"], "source": "citation", "kind": kind,
            "validity_status": validity.get("status"), "cited_by": row["cited_by"],
            "evidence": {"citing_ids": row["citing_ids"], "context": row["context"],
                         "amendment_share": row["amendment_share"], "celex": validity.get("celex")},
        })
    return found


def from_validity(documents, cache):
    """Candidates from the validity check: an act that repealed a document of the
    database but is not in the database itself. `documents` = [(id, identifier, title)]."""
    present, repealed_by = set(), {}
    for doc_id, identifier, title in documents:
        keys = cc.own_keys(identifier, title)
        present |= keys
        for key in keys:
            for successor in cache.get(key, {}).get("repealed_by", []):
                repealed_by.setdefault(successor, set()).add(doc_id)
    found = []
    for key, repealed in sorted(repealed_by.items()):
        if key in present or key.split(":")[0] not in ("CZ", "EU"):
            continue
        validity = cache.get(key, {})
        found.append({
            "candidate_key": key, "source": "validity", "kind": kind_from_celex(validity.get("celex")),
            "validity_status": validity.get("status"), "cited_by": 0,
            "evidence": {"repeals_ids": sorted(repealed), "celex": validity.get("celex")},
        })
    return found


# --- titles -----------------------------------------------------------------

CELLAR = "http://publications.europa.eu/webapi/rdf/sparql"
ZAKONY = "https://www.zakonyprolidi.cz/cs/{year}-{number}"


def eu_titles(session, keys_with_kinds, batch=40):
    """{key: (celex, Czech title)} from Cellar; all three kinds are tried when the
    kind is unknown, and a title is kept only when exactly one act matches."""
    from check_validity import celex_candidates
    wanted = {c: key for key, kind in keys_with_kinds for c in celex_candidates(key, kind)}
    titles = {}
    numbers = sorted(wanted)
    for start in range(0, len(numbers), batch):
        values = " ".join(f'"{c}"^^<http://www.w3.org/2001/XMLSchema#string>' for c in numbers[start:start + batch])
        query = f"""PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
SELECT ?celex ?title WHERE {{
  VALUES ?celex {{ {values} }}
  ?work cdm:resource_legal_id_celex ?celex .
  ?expr cdm:expression_belongs_to_work ?work ; cdm:expression_title ?title ;
        cdm:expression_uses_language <http://publications.europa.eu/resource/authority/language/CES> .
}}"""
        response = session.get(CELLAR, params={"query": query, "format": "application/sparql-results+json"},
                               timeout=120)
        response.raise_for_status()
        for row in response.json()["results"]["bindings"]:
            titles.setdefault(row["celex"]["value"], row["title"]["value"])
        time.sleep(1)
    result = {}
    for key, kind in keys_with_kinds:
        hits = [(c, titles[c]) for c in celex_candidates(key, kind) if c in titles]
        if len(hits) == 1:
            result[key] = hits[0]
    return result


def cz_title(session, key):
    """The title of a Czech act from its zakonyprolidi.cz page (`<title>`), or None."""
    number, year = key.split(":", 1)[1].split("/")
    try:
        response = session.get(ZAKONY.format(year=year, number=number), timeout=60)
    except Exception:
        return None
    m = re.search(r"<title>(.*?)</title>", response.text or "", re.S) if response.ok else None
    if not m:
        return None
    title = re.sub(r"\s+", " ", m.group(1)).strip()
    title = re.sub(r"\s*[|–-]\s*Zákony pro lidi.*$", "", title)
    return re.sub(rf"^{number}/{year} Sb\.\s*", "", title) or None


def complete(candidate, titles):
    """The candidate with its document metadata: designation, title, type, address,
    language and jurisdiction."""
    key, kind = candidate["candidate_key"], candidate.get("kind")
    celex_number, title = titles.get(key, (candidate["evidence"].get("celex"), None))
    if key.startswith("EU:"):
        kind = kind or kind_from_celex(celex_number)
        return {**candidate, "kind": kind, "designation": designation(key, kind), "title": title,
                "document_type": EU_TYPES.get(kind, "Nezařazeno"), "url": document_url(key, kind, celex_number),
                "language": "CS", "jurisdikce": "EU",
                "evidence": {**candidate["evidence"], "celex": celex_number}}
    return {**candidate, "designation": designation(key), "title": title, "document_type": czech_type(title),
            "url": document_url(key), "language": "CS", "jurisdikce": "CZ"}


# --- writing ----------------------------------------------------------------

def upsert(cursor, candidate):
    """Inserts a candidate, or refreshes the evidence of one already reported. The
    decision and the metadata an editor may have changed are never touched; a
    rejected or accepted candidate is not reopened. Returns "inserted",
    "updated" or "kept"."""
    cursor.execute("SELECT id, status FROM DocumentCandidate WHERE candidate_key = %s", (candidate["candidate_key"],))
    row = cursor.fetchone()
    evidence = json.dumps(candidate["evidence"], ensure_ascii=False)
    if row is None:
        cursor.execute("""INSERT INTO DocumentCandidate
            (candidate_key, source, designation, title, document_type, url, language, jurisdikce,
             validity_status, evidence_json, cited_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                       (candidate["candidate_key"], candidate["source"], candidate.get("designation"),
                        candidate.get("title"), candidate.get("document_type"), candidate.get("url"),
                        candidate.get("language"), candidate.get("jurisdikce"), candidate.get("validity_status"),
                        evidence, candidate.get("cited_by", 0)))
        return "inserted"
    status = row["status"] if isinstance(row, dict) else row[1]
    row_id = row["id"] if isinstance(row, dict) else row[0]
    if status in ("accepted", "rejected"):
        return "kept"
    cursor.execute("UPDATE DocumentCandidate SET evidence_json = %s, cited_by = %s, validity_status = %s WHERE id = %s",
                   (evidence, candidate.get("cited_by", 0), candidate.get("validity_status"), row_id))
    return "updated"
