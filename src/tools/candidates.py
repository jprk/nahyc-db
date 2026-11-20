"""Candidates for new documents and the decisions about them
(table `DocumentCandidate`, the editor pages under /admin/candidates).

A candidate is a document that some check says the database may be missing:
an act that the texts in the database cite (citation_closure.py), the act that
repealed a document of the database (check_validity.py), a finding of a monitored
source (harvest_sources.py; `source` is then the source's id in
data/monitored_sources.json and the evidence keeps every source that found it), or a
document an editor proposes by hand. Every candidate is identified
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
           "mpo": "MPO/CDV 30. 4. 2026", "manual": "ruční návrh"}
# Subject areas of doc/DATABASE_SCOPE.md odstavec 3.
SCOPE_AREAS = {1: "Výroba vodíku", 2: "Skladování", 3: "Přeprava", 4: "Plnění do vozidel",
               5: "Provoz vozidel", 6: "Využití vodíku mimo vozidla", 7: "Bezpečnost",
               8: "Stavební řízení a umístění", 9: "Energetika", 10: "Životní prostředí"}
LANGUAGES = ("CS", "EN", "SK", "DE")
# The technical account of the automatic triage (triage.py, doc/FRONTA_AUTOMAT.md): it may be the first
# proposer of an acceptance and may reject or defer by approved rules, never log in or confirm.
AUTOMAT_USERNAME = "automat"
AUTOMAT_NAME = "Automatický navrhovatel"
AUTOMAT_EMAIL = "automat@nahyc.invalid"
EU_TYPES = {"regulation": "Nařízení EU", "directive": "Směrnice EU", "decision": "Rozhodnutí EU"}
CELEX_LETTERS = {"regulation": "R", "directive": "L", "decision": "D"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS DocumentCandidate (
  id INT AUTO_INCREMENT PRIMARY KEY,
  candidate_key VARCHAR(120) NULL,
  source VARCHAR(50) NOT NULL,
  `signal` VARCHAR(20) NULL,
  designation VARCHAR(200) NULL,
  title VARCHAR(1000) NULL,
  document_type VARCHAR(100) NULL,
  url VARCHAR(1000) NULL,
  language VARCHAR(10) NULL,
  jurisdikce VARCHAR(20) NULL,
  scope_area TINYINT NULL,
  validity_status VARCHAR(30) NULL,
  evidence_json MEDIUMTEXT NULL,
  cited_by INT NOT NULL DEFAULT 0,
  tier TINYINT NULL,
  occurrences INT NULL,
  status ENUM('new','proposed','accepted','rejected','deferred') NOT NULL DEFAULT 'new',
  decision_note VARCHAR(1000) NULL,
  proposed_by_user_id INT NULL,
  proposed_at TIMESTAMP NULL,
  confirmed_by_user_id INT NULL,
  confirmed_at TIMESTAMP NULL,
  decided_by_user_id INT NULL,
  decided_at TIMESTAMP NULL,
  document_id INT NULL,
  puvodce VARCHAR(768) NULL,
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


# Tables created before the column existed (2026-10-28) get it here.
MIGRATIONS = ("ALTER TABLE DocumentCandidate ADD COLUMN IF NOT EXISTS `signal` VARCHAR(20) NULL AFTER source",
              # 2026-11-04, doc/DATA_SOURCES.md odstavec 8.8: tier 1 is shown by default, tier 2 in a filter
              "ALTER TABLE DocumentCandidate ADD COLUMN IF NOT EXISTS tier TINYINT NULL AFTER cited_by",
              "ALTER TABLE DocumentCandidate ADD COLUMN IF NOT EXISTS occurrences INT NULL AFTER tier",
              # 2026-11-05: a document may belong to several subject areas ("4,7"); scope_area keeps the first
              "ALTER TABLE DocumentCandidate ADD COLUMN IF NOT EXISTS scope_areas VARCHAR(64) NULL AFTER scope_area",
              # 2026-11-05: the evidence carries the contexts of the citation in every citing document (> 64 kB)
              "ALTER TABLE DocumentCandidate MODIFY COLUMN evidence_json MEDIUMTEXT NULL",
              # 2026-11-20, doc/FRONTA_AUTOMAT.md: what the automatic triage (triage.py) found and recommends
              "ALTER TABLE DocumentCandidate ADD COLUMN IF NOT EXISTS triage_rule VARCHAR(60) NULL",
              "ALTER TABLE DocumentCandidate ADD COLUMN IF NOT EXISTS triage_recommendation VARCHAR(10) NULL",
              "ALTER TABLE DocumentCandidate ADD COLUMN IF NOT EXISTS triage_confidence DECIMAL(4,3) NULL",
              "ALTER TABLE DocumentCandidate ADD COLUMN IF NOT EXISTS triage_json MEDIUMTEXT NULL",
              "ALTER TABLE DocumentCandidate ADD COLUMN IF NOT EXISTS triaged_at TIMESTAMP NULL")
# `signal` of a finding (doc/DATA_SOURCES.md odstavec 4.2) as editors read it.
def scope_areas(candidate):
    """The subject areas chosen for a candidate, [int], also of one proposed before
    `scope_areas` existed."""
    listed = (candidate.get("scope_areas") or "").strip()
    if listed:
        return [int(n) for n in listed.split(",") if n.strip().isdigit()]
    return [candidate["scope_area"]] if candidate.get("scope_area") else []


SIGNAL_LABELS = {"new_document": "nový dokument", "draft": "návrh předpisu (připravovaný)",
                 "amendment": "novela dokumentu v databázi"}


def ensure_schema(cursor):
    cursor.execute(SCHEMA)
    for statement in MIGRATIONS:
        cursor.execute(statement)
    # the issuing institution (DocumentSource.name) the document will get; added for the MPO tables (mpo_tables.py)
    cursor.execute("ALTER TABLE DocumentCandidate ADD COLUMN IF NOT EXISTS puvodce VARCHAR(768) NULL AFTER document_id")


def source_labels(registry=None):
    """{source: label} for the candidate pages: the three checks above and the
    monitored sources of the registry by their names."""
    import source_registry
    try:
        entries = registry if registry is not None else source_registry.load()[0]
    except (OSError, ValueError):
        entries = []
    return {**SOURCES, **{e["id"]: e["name"] for e in entries}}


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
                         **{f"context_{part}": text for part, text in (row.get("context_parts") or {}).items()},
                         # {citing document id: {"count", "places": [{"before", "cited", "after", "amendment"}]}}
                         "contexts": {str(doc): places for doc, places in (row.get("contexts") or {}).items()},
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
    cursor.execute("SELECT id, status, evidence_json FROM DocumentCandidate WHERE candidate_key = %s",
                   (candidate["candidate_key"],))
    row = cursor.fetchone()
    old = _evidence(row)
    fresh = dict(candidate["evidence"])
    if old.get("findings"):
        fresh["findings"] = old["findings"]  # what monitored sources found stays with the candidate
    if old.get("mpo_rows") and "mpo_rows" not in fresh:
        fresh["mpo_rows"] = old["mpo_rows"]  # and so do the rows of the MPO tables (mpo_tables.py)
    evidence = json.dumps(fresh, ensure_ascii=False)
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


def _evidence(row):
    if row is None:
        return {}
    raw = row.get("evidence_json") if isinstance(row, dict) else (row[2] if len(row) > 2 else None)
    try:
        return json.loads(raw) if raw else {}
    except ValueError:
        return {}


def upsert_finding(cursor, candidate, finding):
    """Records a finding of a monitored source (harvest.Finding.as_evidence()) with
    its candidate: a new candidate gets the metadata of the finding and the source
    as its `source`; a candidate already reported (by a check or another source)
    only gets the finding added to `evidence.findings` under the source's id, with
    the date it was first seen kept. A decided candidate is not touched. Returns
    "inserted", "updated" or "kept"."""
    cursor.execute("SELECT id, status, evidence_json FROM DocumentCandidate WHERE candidate_key = %s",
                   (candidate["candidate_key"],))
    row = cursor.fetchone()
    if row is not None and (row["status"] if isinstance(row, dict) else row[1]) in ("accepted", "rejected"):
        return "kept"
    evidence = _evidence(row)
    findings = evidence.setdefault("findings", {})
    previous = findings.get(finding["source"], {})
    findings[finding["source"]] = {**finding, "first_seen": previous.get("first_seen", finding["seen"])}
    if finding.get("amends_ids"):  # read by the acceptance, which creates the AMENDS relations
        evidence["amends_ids"] = sorted(set(evidence.get("amends_ids", [])) | set(finding["amends_ids"]))
    payload = json.dumps(evidence, ensure_ascii=False)
    if row is None:
        cursor.execute("""INSERT INTO DocumentCandidate
            (candidate_key, source, `signal`, designation, title, document_type, url, language, jurisdikce,
             evidence_json, tier, occurrences)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                       (candidate["candidate_key"], finding["source"], finding["signal"], candidate.get("designation"),
                        candidate.get("title"), candidate.get("document_type"), candidate.get("url"),
                        candidate.get("language"), candidate.get("jurisdikce"), payload, candidate.get("tier"),
                        candidate.get("occurrences")))
        return "inserted"
    row_id = row["id"] if isinstance(row, dict) else row[0]
    # The tier and the count follow the latest finding; a placeholder title (the designation itself, or none)
    # gives way to a real one, a title an editor may have written is kept; so is a type, a missing one is filled.
    cursor.execute("""UPDATE DocumentCandidate SET evidence_json = %s, tier = COALESCE(%s, tier),
                          occurrences = COALESCE(%s, occurrences),
                          title = CASE WHEN title IS NULL OR title = designation THEN COALESCE(%s, title) ELSE title END,
                          document_type = COALESCE(NULLIF(document_type, ''), %s)
                      WHERE id = %s""",
                   (payload, candidate.get("tier"), candidate.get("occurrences"), candidate.get("title"),
                    candidate.get("document_type"), row_id))
    return "updated"


# --- proposals and decisions (the editor pages and the automatic triage alike) ----

def validate_proposal(cur, metadata, areas, document_types, own_designation=None):
    """(metadata, errors) of a proposal of acceptance: the same checks for an editor's
    form (candidates_admin.read_metadata) and for the automatic triage (triage.py).
    `metadata` has designation, title, document_type, url, language, jurisdikce,
    puvodce, decision_note; `areas` are the chosen subject areas."""
    metadata = {field: (str(metadata.get(field) or "")).strip() for field in
                ("designation", "title", "document_type", "url", "language", "jurisdikce", "puvodce", "decision_note")}
    errors = []
    if not metadata["title"]:
        errors.append("Název je povinný.")
    if metadata["document_type"] not in document_types:
        errors.append("Vyberte typ dokumentu.")
    if metadata["language"] not in LANGUAGES:
        errors.append("Vyberte jazyk.")
    # a document may belong to several subject areas; the first chosen one is also kept in `scope_area`
    areas = sorted({int(n) for n in areas if str(n).strip().isdigit() and int(n) in SCOPE_AREAS})
    metadata["scope_area"] = areas[0] if areas else 0
    metadata["scope_areas"] = ",".join(map(str, areas))
    if not areas:
        errors.append("Vyberte alespoň jeden věcný okruh (DATABASE_SCOPE.md, odstavec 3).")
    if metadata["designation"] and metadata["designation"] != own_designation:
        cur.execute("SELECT id FROM Document WHERE identifier = %s", (metadata["designation"],))
        if cur.fetchone():
            errors.append(f"Dokument s označením {metadata['designation']} už v databázi je.")
    return metadata, errors


def store_proposal(cur, candidate_id, metadata, user_id):
    cur.execute("""UPDATE DocumentCandidate SET designation = %s, title = %s, document_type = %s, url = %s,
                       language = %s, jurisdikce = %s, puvodce = %s, scope_area = %s, scope_areas = %s,
                       decision_note = %s,
                       status = 'proposed',
                       proposed_by_user_id = %s, proposed_at = NOW(), confirmed_by_user_id = NULL,
                       confirmed_at = NULL
                   WHERE id = %s""",
                (metadata["designation"] or None, metadata["title"], metadata["document_type"],
                 metadata["url"] or None, metadata["language"], metadata["jurisdikce"] or None,
                 metadata["puvodce"] or None, metadata["scope_area"], metadata["scope_areas"],
                 metadata["decision_note"] or None, user_id, candidate_id))


def store_decision(cur, candidate_id, new_status, note, user_id):
    """A decision of one editor (or of the automat): rejected, deferred, or back to new."""
    cur.execute("""UPDATE DocumentCandidate SET status = %s, decision_note = %s, decided_by_user_id = %s,
                       decided_at = NOW(), proposed_by_user_id = IF(%s = 'new', NULL, proposed_by_user_id)
                   WHERE id = %s""", (new_status, note or None, user_id, new_status, candidate_id))


def audit(cur, candidate_id, action, old, new, user_id):
    cur.execute("""INSERT INTO AuditLog (table_name, record_id, action, old_value_json, new_value_json,
                                         changed_by_user_id)
                   VALUES ('DocumentCandidate', %s, %s, %s, %s, %s)""",
                (candidate_id, action, json.dumps(old, ensure_ascii=False, default=str),
                 json.dumps(new, ensure_ascii=False, default=str), user_id))


def automat_id(cur, create=False):
    """The id of the technical account `automat`, created (inactive, with a password hash
    no password matches) when `create`; None when it does not exist yet."""
    cur.execute("SELECT id FROM User WHERE username = %s", (AUTOMAT_USERNAME,))
    row = cur.fetchone()
    if row:
        return row["id"] if isinstance(row, dict) else row[0]
    if not create:
        return None
    # "!" is no hash werkzeug can produce, so check_password_hash() is False for every password;
    # is_active = 0 makes the login refuse the account before the password is even checked.
    cur.execute("INSERT INTO User (username, name, email, password_hash, is_active) VALUES (%s, %s, %s, '!', 0)",
                (AUTOMAT_USERNAME, AUTOMAT_NAME, AUTOMAT_EMAIL))
    return cur.lastrowid
