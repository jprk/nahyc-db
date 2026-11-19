"""Turning a prepared document (a draft, `lifecycle_state = 'draft'`) into the
promulgated act (doc/MPO_PRIPOMINKY.md, krok 3; the editor pages are
app/drafts_admin.py).

A draft ends in one of two ways, and the editor says which:

* **`self`** — the document itself becomes the act: its current version gets the
  state `promulgated` (vyhlášený, dosud neúčinný) or `active` (účinný), and its
  designation, title, address and date of effect may change at the same time
  (a bill gets the number of the Collection, a prEN the designation EN …).
* **`act`** — the act is already in the database as another document: the draft
  is joined to it by `ENACTED_AS` (from the draft to the act), its own current
  version becomes `superseded` (nahrazený), and the act gets the chosen state
  unless it is repealed.

Like every other change of a document by an editor it takes two editors: one
proposes (`DocumentStateChange`, status `proposed`), a second, different one
confirms (CHECK `chk_dsc_distinct_reviewers`); the proposer can withdraw.
The confirmation writes the live database at once and, so that a rebuild keeps
it, data/manual_corrections.json (pipeline fields; `stav_dokumentu` is the state
of the current version, read by init_db.py) and, for `act`,
data/document_relations_editor.json (load_document_relations.py).
"""
import json
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
MANUAL_CORRECTIONS_PATH = REPO_ROOT / "data" / "manual_corrections.json"
EDITOR_RELATIONS_PATH = REPO_ROOT / "data" / "document_relations_editor.json"

MODES = {"self": "dokument se stal vyhlášeným předpisem",
         "act": "vyhlášený předpis je v databázi jako jiný dokument"}
TARGET_STATES = {"promulgated": "vyhlášený, dosud neúčinný", "active": "účinný"}
STATUS_LABELS = {"proposed": "navrženo", "confirmed": "potvrzeno", "withdrawn": "staženo"}
# Pipeline field (data/manual_corrections.json) -> Document column, for the `self` mode.
FIELDS = {"znacka": "identifier", "nazev_cz": "title", "odkaz_hlavni": "url", "platnost": "effective_date"}
RELATION = "ENACTED_AS"

SCHEMA = """
CREATE TABLE IF NOT EXISTS DocumentStateChange (
  id INT AUTO_INCREMENT PRIMARY KEY,
  document_id INT NOT NULL,
  mode ENUM('self','act') NOT NULL,
  from_state VARCHAR(20) NOT NULL,
  to_state ENUM('promulgated','active') NOT NULL,
  target_document_id INT NULL,
  changes_json TEXT NULL,
  note VARCHAR(1000) NULL,
  status ENUM('proposed','confirmed','withdrawn') NOT NULL DEFAULT 'proposed',
  proposed_by_user_id INT NOT NULL,
  proposed_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
  confirmed_by_user_id INT NULL,
  confirmed_at TIMESTAMP NULL,
  KEY idx_dsc_status (status),
  CONSTRAINT fk_dsc_document FOREIGN KEY (document_id) REFERENCES Document (id) ON DELETE CASCADE,
  CONSTRAINT fk_dsc_target FOREIGN KEY (target_document_id) REFERENCES Document (id) ON DELETE SET NULL,
  CONSTRAINT fk_dsc_proposer FOREIGN KEY (proposed_by_user_id) REFERENCES User (id),
  CONSTRAINT fk_dsc_confirmer FOREIGN KEY (confirmed_by_user_id) REFERENCES User (id),
  CONSTRAINT chk_dsc_distinct_reviewers CHECK (confirmed_by_user_id IS NULL OR confirmed_by_user_id <> proposed_by_user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_czech_ci
"""


def _first(row):
    return list(row.values())[0] if isinstance(row, dict) else row[0]


def ensure_schema(cursor):
    """Creates DocumentStateChange and adds `ENACTED_AS` to the relation types when
    missing; returns the list of what it changed (empty when nothing)."""
    changed = []
    cursor.execute("SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() "
                   "AND TABLE_NAME = 'DocumentStateChange'")
    if not _first(cursor.fetchone()):
        cursor.execute(SCHEMA)
        changed.append("table DocumentStateChange")
    cursor.execute("SELECT COLUMN_TYPE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() "
                   "AND TABLE_NAME = 'document_relation' AND COLUMN_NAME = 'relation_type'")
    column_type = _first(cursor.fetchone())
    if f"'{RELATION}'" not in column_type:
        members = column_type[len("enum("):-1] + f",'{RELATION}'"  # the existing types stay as they are
        cursor.execute(f"ALTER TABLE document_relation MODIFY COLUMN relation_type ENUM({members}) NOT NULL")
        changed.append(f"relation type {RELATION}")
    return changed


def read_proposal(form):
    """(proposal, errors) from the editor's form. The proposal is
    {"mode", "to_state", "changes": {pipeline field: value}, "target", "note"};
    the uniqueness of a new designation and the target are checked by the caller."""
    mode = (form.get("mode") or "").strip()
    to_state = (form.get("to_state") or "").strip()
    errors = []
    if mode not in MODES:
        errors.append("Vyberte, jak návrh skončil.")
    if to_state not in TARGET_STATES:
        errors.append("Vyberte stav vyhlášeného předpisu.")
    changes = {}
    if mode == "self":
        changes = {field: (form.get(field) or "").strip() for field in FIELDS}
        changes = {field: value for field, value in changes.items() if value}
    target = (form.get("target") or "").strip()
    if mode == "act" and not target:
        errors.append("Uveďte označení vyhlášeného předpisu, který v databázi už je.")
    note = (form.get("note") or "").strip()[:1000]
    return {"mode": mode, "to_state": to_state, "changes": changes, "target": target if mode == "act" else "",
            "note": note}, errors


def changed_fields(document, changes):
    """Only the fields of `changes` that differ from the document's current values."""
    return {field: value for field, value in changes.items()
            if (document.get(FIELDS[field]) or "") != value}


def correction_key(identifier, url, corrections):
    """The key a document has in data/manual_corrections.json: the entry whose
    confirmed designation is the current one (a designation corrected before),
    else the designation itself, else the key made of its address (`url-<hash>`,
    build_unified_db.correction_key)."""
    if identifier:
        for key, entry in corrections.items():
            if (entry.get("changes") or {}).get("znacka") == identifier and key != identifier:
                return key
        return identifier
    if url:
        from fulltext_keys import first_url, url_designation
        return url_designation(first_url(url))
    return None


def merge_correction(corrections, key, changes, confirmed_by, confirmed_at):
    """Adds `changes` to the entry of `key`, keeping the changes it already has."""
    entry = dict(corrections.get(key) or {})
    entry["changes"] = {**(entry.get("changes") or {}), **changes}
    entry["confirmed_by"] = confirmed_by
    entry["confirmed_at"] = confirmed_at
    corrections[key] = entry
    return corrections


def load_json(path, default):
    path = pathlib.Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def save_corrections(updates, confirmed_by, confirmed_at, path=None):
    """Writes [(key, changes)] into data/manual_corrections.json."""
    path = pathlib.Path(path or MANUAL_CORRECTIONS_PATH)
    corrections = load_json(path, {})
    for key, changes in updates:
        if key:
            merge_correction(corrections, key, changes, confirmed_by, confirmed_at)
    path.write_text(json.dumps(corrections, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def save_relation(from_identifier, to_identifier, note, path=None):
    """Appends an `ENACTED_AS` relation (load_document_relations.py shape) once."""
    path = pathlib.Path(path or EDITOR_RELATIONS_PATH)
    relations = load_json(path, [])
    relation = {"from_identifier": from_identifier, "to_identifier": to_identifier, "relation_type": RELATION,
                "note": note}
    if not any((r["from_identifier"], r["to_identifier"], r["relation_type"]) ==
               (from_identifier, to_identifier, RELATION) for r in relations):
        relations.append(relation)
    path.write_text(json.dumps(relations, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
