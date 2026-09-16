"""Loads `data/v02_processes_parsed.json` (produced by
`src/tools/parse_v02_processes.py`) into the Konsolidace schema's layer B
(`node_description`, `node_branch`, `branch_step`, `node_input`,
`node_output`, `subject`, `node_subject`, `node_problem`) and the layer-C
`node_document` link table — see `doc/PLAN.md` Step 3a.

Citation matching (for `node_document` and the bibliography) never
guesses: a citation that doesn't confidently match an existing
`Document.identifier`, and doesn't look like brand-new supporting
material either, goes to `data/process_layer_review_queue.json` instead
of being silently dropped or duplicated — same principle as
`data/dedup_review_queue.json`.

Usage:
    .venv/bin/python src/tools/load_process_layer.py
"""
import json
import pathlib
import re
import sys

import pymysql

BASE_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent
sys.path.insert(0, str(BASE_DIR))

from init_db import get_connection, get_or_create  # noqa: E402
from parse_v02_processes import extract_citations  # noqa: E402
from slug import assign_slugs  # noqa: E402

PARSED_PATH = REPO_ROOT / "data" / "v02_processes_parsed.json"
REVIEW_QUEUE_PATH = REPO_ROOT / "data" / "process_layer_review_queue.json"

BIBLIOGRAPHY_DOCUMENT_TYPE = "Bibliografický pramen"

# Children before parents. `node_document` has `ON DELETE RESTRICT` on
# Document, so it must always be cleared before `init_db.py` truncates
# Document — this script must run AFTER init_db.py, and re-running
# init_db.py alone (without also re-running this script) leaves
# node_document pointing at deleted rows. Layer-B tables are re-derived
# fully from the docx every run, same TRUNCATE-and-reload philosophy as
# init_db.py itself.
RESET_ORDER = ["node_document", "branch_step", "node_branch", "node_input",
               "node_output", "node_subject", "subject", "node_problem",
               "node_description"]


def reset_layer_b_tables(cursor):
    print("Clearing existing layer B / node_document rows...")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    for table in RESET_ORDER:
        cursor.execute(f"TRUNCATE TABLE {table}")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")


# ---------------------------------------------------------------------
# Citation <-> Document.identifier matching (pure, unit-tested)
# ---------------------------------------------------------------------

_BARE_DIGIT_SLASH_RE = re.compile(r"^\d+/\d{4}$")


def normalize_citation_core(text):
    """Two shapes of citation text feed this: a bare "NNN/YYYY" digit
    pair (from `extract_citations`' law/EU regexes) or a norm code like
    "ČSN EN 17124" (already stripped of its ":YYYY" edition suffix by
    `extract_citations`). Returns (kind, core) — `kind` says which
    lookup table to check, since digit-core matching a norm's raw text
    (or vice versa) would be meaningless."""
    text = text.strip()
    if _BARE_DIGIT_SLASH_RE.match(text):
        return "digits", text
    return "text", re.sub(r"\s+", " ", text)


def document_identifier_digit_core(identifier):
    """"283/2021 Sb." -> "283/2021"; "(EU) 2023/1804" -> "2023/1804".
    Returns None if the identifier has no digit/slash pair at all (a
    norm code like "ČSN EN 17124" has none) — such identifiers are only
    matchable via the text-core path."""
    m = re.search(r"\d+/\d{4}", identifier)
    return m.group(0) if m else None


def build_document_lookup(identifiers):
    """`identifiers` is an iterable of every non-null Document.identifier
    in the corpus. Returns (by_digits, by_text) dicts mapping a
    normalized core -> the identifier itself (the caller already has an
    identifier -> id map from the same query, so returning the identifier
    is enough to join back to an id)."""
    by_digits, by_text = {}, {}
    for identifier in identifiers:
        digit_core = document_identifier_digit_core(identifier)
        if digit_core and digit_core not in by_digits:
            by_digits[digit_core] = identifier
        text_core = re.sub(r"\s+", " ", identifier.strip())
        by_text.setdefault(text_core, identifier)
    return by_digits, by_text


def match_citation(citation_text, by_digits, by_text):
    """Returns the matching `Document.identifier`, or None."""
    kind, core = normalize_citation_core(citation_text)
    if kind == "digits":
        return by_digits.get(core)
    return by_text.get(core)


# ---------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------

def load_parsed_data():
    with open(PARSED_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_document_identifier_map(cursor):
    cursor.execute("SELECT id, identifier FROM Document WHERE identifier IS NOT NULL")
    return {identifier: doc_id for doc_id, identifier in cursor.fetchall()}


def load_node_description(cursor, node_id, description):
    cursor.execute("""
        INSERT INTO node_description
        (node_id, purpose, role_in_phase, trigger_condition, key_decision_point, v01_link_description)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (node_id, description.get("purpose"), description.get("role_in_phase"),
          description.get("trigger_condition"), description.get("key_decision_point"),
          description.get("v01_link_description")))


def load_node_branches(cursor, node_id, branches):
    for branch in branches:
        cursor.execute("""
            INSERT INTO node_branch
            (node_id, branch_code, branch_name, activation_condition, description,
             output_document, is_default)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (node_id, branch["branch_code"], branch["branch_name"],
              branch["activation_condition"], branch["description"],
              branch["output_document"], branch["is_default"]))
        branch_id = cursor.lastrowid
        for step in branch["steps"]:
            cursor.execute("""
                INSERT INTO branch_step (branch_id, step_number, title, description)
                VALUES (%s, %s, %s, %s)
            """, (branch_id, step["step_number"], step["title"], step["description"]))


def load_node_inputs(cursor, node_id, inputs):
    for item in inputs:
        cursor.execute("""
            INSERT INTO node_input (node_id, seq_no, description, is_specific_to_hydrogen)
            VALUES (%s, %s, %s, %s)
        """, (node_id, item["seq_no"], item["description"], item["is_specific_to_hydrogen"]))


def load_node_outputs(cursor, node_id, outputs):
    for item in outputs:
        cursor.execute("""
            INSERT INTO node_output (node_id, document_name, description, enables_next_node,
                                      is_project_blocking)
            VALUES (%s, %s, %s, %s, %s)
        """, (node_id, item["document_name"], item["description"],
              item["enables_next_node"], item["is_project_blocking"]))


def load_node_subjects(cursor, node_id, subjects):
    for item in subjects:
        subject_id = get_or_create(cursor, "subject", {"name": item["name"]},
                                    extra_insert_cols={"abbreviation": item["abbreviation"]})
        try:
            cursor.execute("""
                INSERT INTO node_subject (node_id, subject_id, process_role)
                VALUES (%s, %s, %s)
            """, (node_id, subject_id, item["process_role"]))
        except pymysql.err.IntegrityError:
            pass  # same subject already linked to this node (uq_ns)


def load_node_problems(cursor, node_id, problems):
    for item in problems:
        cursor.execute("""
            INSERT INTO node_problem (node_id, seq_no, problem_title, description)
            VALUES (%s, %s, %s, %s)
        """, (node_id, item["seq_no"], item["title"], item["description"]))


def load_node_document_links(cursor, node_id, citations, by_digits, by_text,
                              doc_id_by_identifier, review_items):
    seen = set()
    for citation in citations:
        if citation in seen:
            continue
        seen.add(citation)
        identifier = match_citation(citation, by_digits, by_text)
        if identifier is None:
            review_items.append({"kind": "unmatched_node_citation", "node_id": node_id,
                                  "citation": citation})
            continue
        document_id = doc_id_by_identifier[identifier]
        try:
            cursor.execute("""
                INSERT INTO node_document (node_id, document_id, link_type, is_primary_basis)
                VALUES (%s, %s, 'LEGAL_BASIS', FALSE)
            """, (node_id, document_id))
        except pymysql.err.IntegrityError:
            pass  # already linked (uq_ndoc: node_id, document_id, link_type)


def load_bibliography(cursor, bibliography, by_digits, by_text, doc_id_by_identifier, review_items):
    """Every bibliography entry either already matches a Document (no
    action needed) or is genuinely new supporting material (HYTEP/EHTA/
    academic/internal deliverables — gets a new Document row) or looks
    like a law/norm citation that just didn't match, which is NOT
    auto-created (risk of a near-duplicate row) and goes to the review
    queue instead.

    doc/PLAN.md §16, 2026-09-16: the rows created here need a
    `Document.slug` too. `init_db.py` assigns slugs over its own import
    only, and this script runs after it, so without this pass these
    bibliography entries would be the one slice of the corpus with no
    permanent URL — invisible to `/dokument/<slug>`."""
    new_document_ids = []
    for entry in bibliography:
        text = entry["text"]
        citations_in_entry = extract_citations(text)
        matched_identifier = None
        for c in citations_in_entry:
            matched_identifier = match_citation(c, by_digits, by_text)
            if matched_identifier:
                break
        if matched_identifier:
            continue
        if citations_in_entry:
            review_items.append({"kind": "unmatched_bibliography_citation",
                                  "ref_id": entry["ref_id"], "text": text})
            continue
        type_id = get_or_create(cursor, "DocumentType", {"name": BIBLIOGRAPHY_DOCUMENT_TYPE})
        cursor.execute("""
            INSERT INTO Document (title, type_id, jurisdikce)
            VALUES (%s, %s, NULL)
        """, (text[:1000], type_id))
        document_id = cursor.lastrowid
        new_document_ids.append((document_id, text[:1000]))
        # Same invariant Step 2 established for every Document: exactly
        # one current version, even with no real version history.
        cursor.execute("""
            INSERT INTO DocumentVersion (document_id, version, is_current)
            VALUES (%s, 1, TRUE)
        """, (document_id,))

    # Slugs are assigned in one pass over these rows, using the same
    # content-derived ordering `slug.assign_slugs()` applies everywhere
    # else. These entries have no designation, so each resolves to a
    # hash of its own title and is stable across rebuilds.
    if new_document_ids:
        for doc_id, slug in assign_slugs((i, None, t) for i, t in new_document_ids).items():
            cursor.execute("UPDATE Document SET slug=%s WHERE id=%s", (slug, doc_id))


def main():
    parsed = load_parsed_data()
    conn = get_connection()
    cursor = conn.cursor()

    reset_layer_b_tables(cursor)
    conn.commit()

    doc_id_by_identifier = fetch_document_identifier_map(cursor)
    by_digits, by_text = build_document_lookup(doc_id_by_identifier.keys())
    review_items = []

    for node_id, node in parsed["nodes"].items():
        load_node_description(cursor, node_id, node["description"])
        load_node_branches(cursor, node_id, node["branches"])
        load_node_inputs(cursor, node_id, node["inputs"])
        load_node_outputs(cursor, node_id, node["outputs"])
        load_node_subjects(cursor, node_id, node["subjects"])
        load_node_problems(cursor, node_id, node["problems"])

        citations = list(node["legal_basis_citations"])
        citations.extend(parsed["node_document_examples"].get(node_id, []))
        load_node_document_links(cursor, node_id, citations, by_digits, by_text,
                                  doc_id_by_identifier, review_items)

    load_bibliography(cursor, parsed["bibliography"], by_digits, by_text,
                       doc_id_by_identifier, review_items)

    conn.commit()

    with open(REVIEW_QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump(review_items, f, ensure_ascii=False, indent=2)

    print(f"Loaded layer B for {len(parsed['nodes'])} nodes.")
    print(f"{len(review_items)} item(s) need human review -> "
          f"{REVIEW_QUEUE_PATH.relative_to(REPO_ROOT)}")
    conn.close()


if __name__ == "__main__":
    main()
