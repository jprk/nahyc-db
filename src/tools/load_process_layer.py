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
from norm_title import designation_core  # noqa: E402
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


def reset_bibliography_documents(cursor):
    """doc/PLAN.md §20/§22, 2026-09-17: the `Bibliografický pramen`
    `Document` rows `load_bibliography()` creates are 100% synthetic —
    sourced only from the docx bibliography, never from
    `database_merged_deduplicated.json` — so, unlike every other
    `Document` row, re-deriving them fresh on every run is always
    correct and lossless. Without this, running this script twice in a
    row (without an intervening `init_db.py`, which happens to clear
    them as a side effect of re-TRUNCATing `Document`) duplicate-inserts
    them and collides on the content-derived slug. Confirmed live
    (`information_schema.KEY_COLUMN_USAGE`) that nothing else references
    these rows — `node_document` is already cleared by
    `reset_layer_b_tables()` above, called first."""
    cursor.execute("SELECT id FROM DocumentType WHERE name = %s", (BIBLIOGRAPHY_DOCUMENT_TYPE,))
    row = cursor.fetchone()
    if row is None:
        return  # nothing created yet (e.g. a brand-new database)
    type_id = row[0]
    cursor.execute('''
        DELETE dv FROM DocumentVersion dv
        JOIN Document d ON d.id = dv.document_id
        WHERE d.type_id = %s
    ''', (type_id,))
    cursor.execute("DELETE FROM Document WHERE type_id = %s", (type_id,))


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


# doc/PLAN.md §35, 2026-09-18, user-directed: a bare EU-level norm
# designation ("EN 17124") in the V02 source text should link to EVERY
# national adoption in the corpus that shares it (ČSN, STN, ...), not
# just one — so the process view can show which jurisdictions actually
# have that standard adopted. Only the leading national-standards-body
# token is stripped here; the EN/ISO/IEC-based core that follows it is
# exactly what a bare citation already looks like, so no other rewriting
# is needed.
_NATIONAL_PREFIX_RE = re.compile(r"^(ČSN|CSN|STN|TNI|DIN|VDE|NF|BS|NEN)\s+", re.IGNORECASE)


def strip_national_prefix(text):
    return _NATIONAL_PREFIX_RE.sub("", text or "").strip()


def eu_core_designation(identifier):
    """"ČSN EN 17124" -> "EN 17124"; "STN EN 17124/ - 2022.06" -> "EN
    17124" (via `designation_core()`'s existing edition-suffix strip,
    same one `init_db.py`/`backfill_norm_designation.py` already use,
    THEN the national-prefix strip above); a bare "EN 17124" identifier
    with no prefix at all maps to itself unchanged — so a fan-out lookup
    keyed on this also picks up a genuinely un-prefixed corpus record,
    not just prefixed national adoptions."""
    return strip_national_prefix(designation_core(identifier))


def build_document_lookup(identifiers):
    """`identifiers` is an iterable of every non-null Document.identifier
    in the corpus. Returns (by_digits, by_text, by_eu_core):
    `by_digits`/`by_text` map a normalized core -> the identifier itself
    (single match, as before); `by_eu_core` maps a national-prefix-and-
    edition-stripped core -> the LIST of every identifier sharing it
    (possibly several — ČSN EN 17124 and STN EN 17124 both map to "EN
    17124"). The caller already has an identifier -> id map from the
    same query, so returning identifiers is enough to join back to ids."""
    by_digits, by_text, by_eu_core = {}, {}, {}
    for identifier in identifiers:
        digit_core = document_identifier_digit_core(identifier)
        if digit_core and digit_core not in by_digits:
            by_digits[digit_core] = identifier
        text_core = re.sub(r"\s+", " ", identifier.strip())
        by_text.setdefault(text_core, identifier)
        eu_core = eu_core_designation(identifier)
        if eu_core:
            by_eu_core.setdefault(eu_core, []).append(identifier)
    return by_digits, by_text, by_eu_core


def match_citations(citation_text, by_digits, by_text, by_eu_core):
    """Returns a list of matching `Document.identifier` values — empty
    if none, a single-element list for a law citation or a norm citation
    that already names a specific national adoption (e.g. the
    bibliography spelling out "ČSN EN 17124" itself — matched exactly,
    never fanned out to jurisdictions it didn't name), and possibly
    SEVERAL elements for a bare EU-level norm designation ("EN 17124")
    that more than one national adoption in the corpus shares."""
    kind, core = normalize_citation_core(citation_text)
    if kind == "digits":
        match = by_digits.get(core)
        return [match] if match else []
    if _NATIONAL_PREFIX_RE.match(core):
        exact = by_text.get(core)
        return [exact] if exact else []
    return list(by_eu_core.get(core, []))


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


def load_node_document_links(cursor, node_id, citations, by_digits, by_text, by_eu_core,
                              doc_id_by_identifier, review_items):
    """doc/PLAN.md §35, 2026-09-18: a bare EU-level citation links to
    EVERY jurisdiction's adoption it matches, one `node_document` row
    per identifier — not just the first one found."""
    seen = set()
    for citation in citations:
        if citation in seen:
            continue
        seen.add(citation)
        identifiers = match_citations(citation, by_digits, by_text, by_eu_core)
        if not identifiers:
            review_items.append({"kind": "unmatched_node_citation", "node_id": node_id,
                                  "citation": citation})
            continue
        for identifier in identifiers:
            document_id = doc_id_by_identifier[identifier]
            try:
                cursor.execute("""
                    INSERT INTO node_document (node_id, document_id, link_type, is_primary_basis)
                    VALUES (%s, %s, 'LEGAL_BASIS', FALSE)
                """, (node_id, document_id))
            except pymysql.err.IntegrityError:
                pass  # already linked (uq_ndoc: node_id, document_id, link_type)


def load_bibliography(cursor, bibliography, by_digits, by_text, by_eu_core, doc_id_by_identifier,
                      review_items):
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
    permanent URL — invisible to `/dokument/<slug>`.

    Returns `{ref_id: [document_id, ...]}` for every entry that resolved
    to one or more Documents (matched — possibly several jurisdictions,
    doc/PLAN.md §35 — or newly created, always exactly one then) —
    doc/PLAN.md Step 1 (2026-09-17): `load_node_bibliography_links`
    needs this to turn a node's "[N]" citations into `link_type='SOURCE'`
    `node_document` rows. An entry that went to the review queue
    (unmatched citation) has no id here — `load_node_bibliography_links`
    reports that as its own, separate review item rather than silently
    skipping the link."""
    document_ids_by_ref_id = {}
    new_document_ids = []
    for entry in bibliography:
        ref_id = entry["ref_id"]
        text = entry["text"]
        citations_in_entry = extract_citations(text)
        matched_identifiers = []
        for c in citations_in_entry:
            matched_identifiers = match_citations(c, by_digits, by_text, by_eu_core)
            if matched_identifiers:
                break
        if matched_identifiers:
            document_ids_by_ref_id[ref_id] = [doc_id_by_identifier[i] for i in matched_identifiers]
            continue
        if citations_in_entry:
            review_items.append({"kind": "unmatched_bibliography_citation",
                                  "ref_id": ref_id, "text": text})
            continue
        type_id = get_or_create(cursor, "DocumentType", {"name": BIBLIOGRAPHY_DOCUMENT_TYPE})
        cursor.execute("""
            INSERT INTO Document (title, type_id, jurisdikce)
            VALUES (%s, %s, NULL)
        """, (text[:1000], type_id))
        document_id = cursor.lastrowid
        document_ids_by_ref_id[ref_id] = [document_id]
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

    return document_ids_by_ref_id


def load_node_bibliography_links(cursor, node_id, ref_ids, document_ids_by_ref_id, review_items):
    """Links `node_id` to the bibliography entries its own prose cites
    via "[N]" markers, as `link_type='SOURCE'` — distinct from the
    `LEGAL_BASIS` links `load_node_document_links` creates from the
    "Právní a regulatorní opora"/node→document-mapping citations. Must
    run AFTER `load_bibliography`, whose `ref_id -> [Document.id, ...]`
    map this depends on; a ref_id with no entry there (its bibliography
    citation itself went unmatched) is reported here rather than
    silently dropped. doc/PLAN.md §35: one row per matched jurisdiction,
    same as `load_node_document_links`."""
    for ref_id in ref_ids:
        document_ids = document_ids_by_ref_id.get(ref_id)
        if not document_ids:
            review_items.append({"kind": "unresolved_node_bibliography_ref",
                                  "node_id": node_id, "ref_id": ref_id})
            continue
        for document_id in document_ids:
            try:
                cursor.execute("""
                    INSERT INTO node_document (node_id, document_id, link_type, is_primary_basis)
                    VALUES (%s, %s, 'SOURCE', FALSE)
                """, (node_id, document_id))
            except pymysql.err.IntegrityError:
                pass  # already linked (uq_ndoc: node_id, document_id, link_type)


def load_node_edges(cursor, node_id, edges, review_items):
    """Fills the still-`NULL` `description` of an EXISTING `node_edge`
    row — the 15-row static seed in `Konsolidace-DB-schema.sql` already
    encodes `direction`/`character`, this only adds the docx's own prose
    for that edge. A `BIDIRECTIONAL` seed row is described from BOTH
    nodes' sections in the docx (e.g. U2→U5 and U5→U2), so a second call
    appends rather than overwrites, unless the text is a near-duplicate
    already present. A docx edge with NO matching seed row in either
    direction (e.g. U1→U5, present in the docx but not the static seed)
    is a real discrepancy — flagged for human reconciliation, never
    silently inserted with a guessed `direction`/`character`."""
    for edge in edges:
        to_node_id = edge["to_node_id"]
        description = edge["description"]
        cursor.execute("""
            SELECT id, description FROM node_edge
            WHERE (from_node_id=%s AND to_node_id=%s)
               OR (from_node_id=%s AND to_node_id=%s AND direction='BIDIRECTIONAL')
        """, (node_id, to_node_id, to_node_id, node_id))
        row = cursor.fetchone()
        if row is None:
            review_items.append({"kind": "unmatched_node_edge", "from_node_id": node_id,
                                  "to_node_id": to_node_id, "description": description})
            continue
        edge_id, existing = row
        if existing and description in existing:
            continue
        merged = description if not existing else f"{existing} {description}"
        cursor.execute("UPDATE node_edge SET description=%s WHERE id=%s", (merged, edge_id))


def load_node_variability(cursor, node_id, variability, review_items):
    """Fills the still-`NULL` `specifics` of an EXISTING `node_variability`
    row — the 28-row 4×7 seed already covers every node × installation
    type pair (confirmed: `parse_v02_processes.py` extracts exactly 28
    docx rows too), so every call here is expected to match; a miss goes
    to the review queue rather than being silently dropped, since it
    would mean the docx and the static seed have actually diverged.

    Existence is checked with a `SELECT` before the `UPDATE`, not via the
    `UPDATE`'s own affected-rows count: MariaDB's default client reports
    *changed* rows, not *matched* rows, so on a second run — where
    `specifics` is already set to the same value — every row would
    otherwise look unmatched even though it plainly isn't (doc/PLAN.md
    §22, found by re-running this script twice in a row)."""
    for item in variability:
        code = item["installation_type_code"]
        specifics = item["specifics"]
        cursor.execute("""
            SELECT nv.id FROM node_variability nv
            JOIN installation_type it ON it.id = nv.installation_type_id
            WHERE nv.node_id = %s AND it.code = %s
        """, (node_id, code))
        row = cursor.fetchone()
        if row is None:
            review_items.append({"kind": "unmatched_node_variability", "node_id": node_id,
                                  "installation_type_code": code})
            continue
        cursor.execute("UPDATE node_variability SET specifics = %s WHERE id = %s",
                       (specifics, row[0]))


def main():
    parsed = load_parsed_data()
    conn = get_connection()
    cursor = conn.cursor()

    reset_layer_b_tables(cursor)
    reset_bibliography_documents(cursor)
    conn.commit()

    doc_id_by_identifier = fetch_document_identifier_map(cursor)
    by_digits, by_text, by_eu_core = build_document_lookup(doc_id_by_identifier.keys())
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
        load_node_document_links(cursor, node_id, citations, by_digits, by_text, by_eu_core,
                                  doc_id_by_identifier, review_items)

        load_node_edges(cursor, node_id, node.get("edges", []), review_items)
        load_node_variability(cursor, node_id, node.get("variability", []), review_items)

    document_ids_by_ref_id = load_bibliography(cursor, parsed["bibliography"], by_digits, by_text,
                                               by_eu_core, doc_id_by_identifier, review_items)

    # Second pass: SOURCE links depend on load_bibliography's ref_id ->
    # Document.id map, which only exists once every bibliography entry
    # has been matched or created above.
    for node_id, node in parsed["nodes"].items():
        load_node_bibliography_links(cursor, node_id, node.get("bibliography_refs", []),
                                     document_ids_by_ref_id, review_items)

    conn.commit()

    with open(REVIEW_QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump(review_items, f, ensure_ascii=False, indent=2)

    print(f"Loaded layer B for {len(parsed['nodes'])} nodes.")
    print(f"{len(review_items)} item(s) need human review -> "
          f"{REVIEW_QUEUE_PATH.relative_to(REPO_ROOT)}")
    conn.close()


if __name__ == "__main__":
    main()
