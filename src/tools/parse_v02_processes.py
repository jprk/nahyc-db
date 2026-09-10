"""Parses `doc/NAHYC DP004 V02 - Popis procesů.docx` — the source document
for Konsolidace schema layer B (process nodes U1–U7: branches, steps,
inputs, outputs, subjects, problems) — into `data/v02_processes_parsed.json`.

The document is highly structured (every node section repeats the same 11
H3 subsections, with real Word tables for subjects and — for branched
nodes — branch outputs), confirmed by full-document exploration before
writing this parser (see `doc/PLAN.md` Step 3a). Two real structural
exceptions were found and are handled explicitly, not forced into the
generic pattern:
- **U2** doesn't use lettered "Větev X — ..." branch headings like
  U4/U5/U6/U7 — it uses "Krok 1/2/3/4" headings, with the actual A–D
  branching living as a table *inside* "Krok 2 — Větvení procesu".
- **U5** has a "Průřezově — ATEX klasifikace" H4 that isn't a branch at
  all — it's a modifier applying across all of U5's real branches.

Also extracts the 59-entry bibliography (`[1]`–`[59]`, "Seznam použité
literatury") and the "Mapování procesních uzlů" node→document table —
both feed the layer-C `node_document` link table (see
`src/tools/load_process_layer.py`).

Usage:
    .venv/bin/python src/tools/parse_v02_processes.py
"""
import json
import pathlib
import re

import docx
from docx.table import Table
from docx.text.paragraph import Paragraph

BASE_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent
DOCX_PATH = REPO_ROOT / "doc" / "NAHYC DP004 V02 - Popis procesů.docx"
OUTPUT_PATH = REPO_ROOT / "data" / "v02_processes_parsed.json"

NODE_IDS = ["U1", "U2", "U3", "U4", "U5", "U6", "U7"]

_NODE_HEADING_RE = re.compile(r"^Uzel\s+(U\d)\b")


def parse_node_heading(text):
    """"Uzel U1 — Územní kompatibilita záměru" -> "U1", or None if the
    heading doesn't match the expected pattern."""
    m = _NODE_HEADING_RE.match(text.strip())
    return m.group(1) if m else None

# The 11 H3 subsections every node repeats, in document order.
_SECTION_PURPOSE = "Účel a role procesu"
_SECTION_LEGAL_BASIS = "Právní a regulatorní opora procesu"
_SECTION_TRIGGER = "Spouštěcí podmínky procesu"
_SECTION_INPUTS = "Vstupy procesu"
_SECTION_FLOW = "Průběh procesu (strukturální popis)"
_SECTION_SUBJECTS = "Zapojené subjekty a jejich role"
_SECTION_OUTPUTS = "Výstupy a ukončení procesu"
_SECTION_EDGES = "Vazby na další uzly procesní sítě"
_SECTION_VARIABILITY = "Variabilita procesu podle typu vodíkové instalace"
_SECTION_PROBLEMS = "Typické interpretační nebo procesní problémy"
_SECTION_V01_LINK = "Vazba na databázi V01"


# ---------------------------------------------------------------------
# Small, pure, unit-tested helpers
# ---------------------------------------------------------------------

def looks_like_list_intro_or_wrapup(text):
    """A lead-in sentence introducing a list ("...zahrnují:") or a
    closing remark after one almost always ends with ':' or is a full
    sentence — used to separate real list items from prose when a
    section has NO `List Paragraph`-styled items (see module docstring:
    some sections use real bullets, others just lay items out as plain
    'Normal' paragraphs)."""
    return text.strip().endswith(":")


def extract_list_items(section_paragraphs):
    """`section_paragraphs` is a list of (style_name, text) tuples for one
    H3 section (paragraphs only, no headings/tables). If any paragraph
    uses the `List Paragraph` style, only those count as items (the
    reliable signal). Otherwise every non-empty 'Normal' paragraph that
    doesn't look like an intro/wrap-up sentence counts as one item —
    verified against every node's actual "Vstupy procesu"/"Typické
    problémy" sections before relying on this (see doc/PLAN.md Step 3a)."""
    list_items = [text for style, text in section_paragraphs
                  if style == "List Paragraph" and text.strip()]
    if list_items:
        return list_items
    return [text for style, text in section_paragraphs
            if style == "Normal" and text.strip()
            and not looks_like_list_intro_or_wrapup(text)]


_BRANCH_HEADING_RE = re.compile(r"^(.+?)\s*[—–-]\s*(.+)$")


def split_branch_heading(text):
    """Splits a branch-like heading/cell ("Větev A — Vlastní spotřeba",
    "A — Bez posouzení", "Průřezově — ATEX klasifikace") into (code,
    name) — the code is the last word of whatever precedes the dash
    ("Větev A" -> "A", bare "A" -> "A", "Průřezově" -> "Průřezově").
    Falls back to (text, text) if the dash separator isn't found — never
    raises, since a heading that doesn't fit the pattern should still be
    captured for human review rather than dropped."""
    m = _BRANCH_HEADING_RE.match(text.strip())
    if not m:
        return text.strip(), text.strip()
    prefix, name = m.group(1), m.group(2).strip()
    words = prefix.split()
    code = words[-1] if len(words) > 1 else prefix
    return code, name


def is_krok_heading(h4_text):
    return h4_text.strip().lower().startswith("krok")


def is_cross_cutting_heading(h4_text):
    return h4_text.strip().lower().startswith("průřezově")


def split_problem_text(text):
    """Problem list items are "Title — elaboration" — splits on the
    first em/en-dash; returns (title, full_text). Falls back to
    (None, full_text) if no dash is found (still keeps the content,
    never drops it)."""
    m = re.match(r"^(.+?)\s*[—–]\s*(.+)$", text.strip())
    if not m:
        return None, text.strip()
    return m.group(1).strip(), text.strip()


_SUBJECT_ABBR_RE = re.compile(r"^([A-ZÁ-Ž0-9]{2,10})\s*\(")


def parse_subject_cell(cell_text):
    """"HZS (Hasičský záchranný sbor)" -> ("HZS (Hasičský záchranný
    sbor)", "HZS"); "Investor" -> ("Investor", None). The abbreviation is
    a bonus field (`subject.abbreviation`) — no abbreviation found is not
    an error."""
    name = cell_text.strip()
    m = _SUBJECT_ABBR_RE.match(name)
    return name, (m.group(1) if m else None)


_BIBLIOGRAPHY_ENTRY_RE = re.compile(r"^\[(\d+)\]\s*(.+)$")


def parse_bibliography_line(text):
    """Returns (ref_id, citation_text) for a "[N] ..." bibliography line,
    or None for a category-header line (e.g. "České zákony") that carries
    no bracket number."""
    m = _BIBLIOGRAPHY_ENTRY_RE.match(text.strip())
    if not m:
        return None
    return int(m.group(1)), m.group(2).strip()


# Citation patterns found in practice across "Právní a regulatorní opora"
# prose, the node→document mapping table, and the bibliography itself —
# Czech laws/decrees, EU legislation, technical norms.
_CITATION_PATTERNS = [
    re.compile(r"(?:zákon|vyhlášk[ay]|nařízení vlády)\s+č\.\s*(\d+/\d{4})\s*Sb\.", re.IGNORECASE),
    re.compile(r"\(\s*(?:ES|EU|EÚ)\s*\)\s*(?:č\.\s*)?(\d+/\d{4})"),
    re.compile(r"\b(?:ES|EU|EÚ)\s+č\.\s*(\d+/\d{4})\b"),
    re.compile(r"(\d{4}/\d+/(?:ES|EU|EÚ))"),
    re.compile(r"(ČSN(?:\s+EN)?(?:\s+ISO)?\s+[\d\s]+(?:-\d+)?)(?::\d{4})?"),
    re.compile(r"\b(EN\s+ISO\s+\d+)\b"),
]


def extract_citations(text):
    """Best-effort extraction of law/norm citation substrings from free
    prose — used for "Právní a regulatorní opora" sections and the
    node→document mapping table's example cells. Returns raw matched
    strings for later matching against `Document.identifier` in
    `load_process_layer.py`; never resolves an identifier itself (that's
    the loader's job, with a review-queue fallback for anything
    unmatched)."""
    found = []
    for pattern in _CITATION_PATTERNS:
        for m in pattern.finditer(text):
            found.append(m.group(1).strip())
    return found


# ---------------------------------------------------------------------
# Document-structure walk (thicker orchestration, not unit-tested
# directly — same division as parse_sinay_norms.py's PDF walk)
# ---------------------------------------------------------------------

def _iter_body_elements(document):
    """Yields ('p', Paragraph) or ('tbl', Table) in document order."""
    for child in document.element.body.iterchildren():
        if child.tag.endswith("}p"):
            yield "p", Paragraph(child, document)
        elif child.tag.endswith("}tbl"):
            yield "tbl", Table(child, document)


def _table_rows(table, skip_header=True):
    rows = table.rows[1:] if skip_header else table.rows
    return [[c.text.strip() for c in row.cells] for row in rows]


def parse_node_flow(flow_elements):
    """Builds the `branches` list for one node's "Průběh procesu"
    section. `flow_elements` is the list of ('p'|'tbl', obj) items
    between that heading and the next H3. Handles the standard
    lettered-branch pattern (U3-U7... actually U1/U3 have no branches at
    all, U4/U6/U7 use plain "Větev X" H4s) plus U2's Krok-based exception
    and U5's cross-cutting "Průřezově" exception."""
    # Does this node use "Krok N" headings (U2's exception)?
    h4_texts = [obj.text for kind, obj in flow_elements
                if kind == "p" and obj.style.name == "Heading 4"]
    if any(is_krok_heading(t) for t in h4_texts):
        return _parse_krok_style_flow(flow_elements)
    if not h4_texts:
        return _parse_linear_flow(flow_elements)
    return _parse_lettered_branch_flow(flow_elements)


def _paragraphs_until_next_heading(elements, start_idx):
    """Collects (style, text) for 'p' elements from start_idx up to (not
    including) the next Heading 3/4, and returns (items, next_idx)."""
    collected = []
    i = start_idx
    while i < len(elements):
        kind, obj = elements[i]
        if kind == "p" and obj.style.name in ("Heading 3", "Heading 4"):
            break
        if kind == "p" and obj.text.strip():
            collected.append((obj.style.name, obj.text.strip()))
        i += 1
    return collected, i


def _parse_linear_flow(flow_elements):
    paragraphs = [(obj.style.name, obj.text.strip()) for kind, obj in flow_elements
                  if kind == "p" and obj.text.strip()]
    steps = extract_list_items(paragraphs)
    return [{
        "branch_code": "MAIN", "branch_name": None, "activation_condition": None,
        "description": None, "output_document": None, "is_default": True,
        "steps": [{"step_number": i + 1, "title": None, "description": s}
                   for i, s in enumerate(steps)],
    }]


def _parse_lettered_branch_flow(flow_elements):
    branches = []
    i = 0
    while i < len(flow_elements):
        kind, obj = flow_elements[i]
        if kind == "p" and obj.style.name == "Heading 4" and not is_cross_cutting_heading(obj.text):
            code, name = split_branch_heading(obj.text)
            body, i = _paragraphs_until_next_heading(flow_elements, i + 1)
            steps = extract_list_items(body)
            branches.append({
                "branch_code": code, "branch_name": name, "activation_condition": None,
                "description": None, "output_document": None, "is_default": False,
                "steps": [{"step_number": j + 1, "title": None, "description": s}
                           for j, s in enumerate(steps)],
            })
        elif kind == "p" and obj.style.name == "Heading 4" and is_cross_cutting_heading(obj.text):
            _, name = split_branch_heading(obj.text)
            body, i = _paragraphs_until_next_heading(flow_elements, i + 1)
            steps = extract_list_items(body)
            # branch_code is VARCHAR(5) -- "Průřezově" itself doesn't
            # fit, unlike the single-letter A/B/C/D codes.
            branches.append({
                "branch_code": "X", "branch_name": name, "activation_condition": None,
                "description": "Průřezová podmínka platící napříč ostatními větvemi tohoto uzlu.",
                "output_document": None, "is_default": False,
                "steps": [{"step_number": j + 1, "title": None, "description": s}
                           for j, s in enumerate(steps)],
            })
        else:
            i += 1
    return branches


def _parse_krok_style_flow(flow_elements):
    """U2's exception: "Krok 1"/"Krok 3"/"Krok 4" are sequential MAIN
    steps; the real A-D branching lives in a table inside "Krok 2"."""
    main_steps = []
    lettered_branches = []
    i = 0
    while i < len(flow_elements):
        kind, obj = flow_elements[i]
        if kind == "p" and obj.style.name == "Heading 4":
            krok_text = obj.text
            body, next_i = _paragraphs_until_next_heading(flow_elements, i + 1)
            # A table belonging to this Krok sits among the elements we
            # just consumed as "body" positions — re-scan that slice for
            # a table (Krok 2's branching table).
            table_obj = next(
                (o for k, o in flow_elements[i + 1:next_i] if k == "tbl"), None)
            if table_obj is not None:
                for row in _table_rows(table_obj):
                    branch_cell, condition_cell, flow_cell = (row + ["", "", ""])[:3]
                    code, name = split_branch_heading(branch_cell)
                    lettered_branches.append({
                        "branch_code": code, "branch_name": name,
                        "activation_condition": condition_cell or None,
                        "description": flow_cell or None, "output_document": None,
                        "is_default": False,
                        "steps": [{"step_number": 1, "title": None, "description": flow_cell}],
                    })
            else:
                prose = [text for style, text in body if text]
                if prose:
                    main_steps.append(" ".join(prose))
            i = next_i
        else:
            i += 1
    main_branch = {
        "branch_code": "MAIN", "branch_name": None, "activation_condition": None,
        "description": None, "output_document": None, "is_default": True,
        "steps": [{"step_number": i + 1, "title": None, "description": s}
                   for i, s in enumerate(main_steps)],
    }
    return [main_branch] + lettered_branches


def parse_node_outputs(output_elements, summary_output_text):
    """Branched nodes have a "Větev"/"Výstupní dokument" table; linear
    nodes (U1/U3) only have prose — for those, `document_name` comes from
    the node's own summary-table "Výstup procesu" cell (parsed
    separately, passed in here) rather than being fabricated."""
    table_obj = next((o for k, o in output_elements if k == "tbl"), None)
    if table_obj is not None:
        outputs = []
        for row in _table_rows(table_obj):
            branch_cell, doc_cell = (row + ["", ""])[:2]
            code, _ = split_branch_heading(branch_cell) if branch_cell else (None, None)
            outputs.append({"branch_code": code, "document_name": doc_cell,
                             "description": None, "enables_next_node": None,
                             "is_project_blocking": False})
        return outputs
    prose = " ".join(text for k, o in output_elements if k == "p"
                      for text in [o.text.strip()] if text)
    return [{"branch_code": None,
             "document_name": summary_output_text or "Výstup procesu",
             "description": prose or None, "enables_next_node": None,
             "is_project_blocking": False}]


def parse_summary_table(table):
    """Maps the per-node "Tabulka: Přehled" 2-column summary table
    (label -> value) to the subset of node_description columns it
    actually covers — confirmed identical labels across all 7 nodes
    (minor "orgán"/"orgány"/"subjekty" wording variance in one row this
    parser doesn't use)."""
    rows = {row.cells[0].text.strip(): row.cells[1].text.strip()
            for row in table.rows[1:]}
    return {
        "purpose": rows.get("Účel procesu"),
        "role_in_phase": rows.get("Role v předrealizační fázi"),
        "trigger_condition": rows.get("Spouštěcí podmínka"),
        "key_decision_point": rows.get("Klíčový rozhodovací bod"),
        "_output_summary": rows.get("Výstup procesu"),
    }


def parse_docx(docx_path):
    document = docx.Document(str(docx_path))
    elements = list(_iter_body_elements(document))

    nodes = {}
    node_document_examples = {}
    bibliography = []

    # --- per-node sections ---
    current_node = None
    section = None
    section_start = None
    node_ranges = []  # (node_id, start_idx, end_idx)
    for idx, (kind, obj) in enumerate(elements):
        heading_node_id = parse_node_heading(obj.text) if (kind == "p" and obj.style.name == "Heading 2") else None
        if heading_node_id:
            if current_node:
                node_ranges.append((current_node, section_start, idx))
            current_node = heading_node_id
            section_start = idx
        elif kind == "p" and obj.style.name == "Heading 2" and current_node:
            node_ranges.append((current_node, section_start, idx))
            current_node = None
    if current_node:
        node_ranges.append((current_node, section_start, len(elements)))

    for node_id, start, end in node_ranges:
        node_elements = elements[start:end]
        sections = {}
        i = 0
        cur_section = None
        cur_start = 0
        boundaries = []
        for i, (kind, obj) in enumerate(node_elements):
            if kind == "p" and obj.style.name == "Heading 3":
                if cur_section:
                    boundaries.append((cur_section, cur_start, i))
                cur_section = obj.text.strip()
                cur_start = i + 1
        if cur_section:
            boundaries.append((cur_section, cur_start, len(node_elements)))
        for name, s, e in boundaries:
            sections[name] = node_elements[s:e]

        summary_table = None
        for kind, obj in node_elements:
            if kind == "tbl" and obj.rows[0].cells[0].text.strip() == "Položka":
                summary_table = obj
        description = parse_summary_table(summary_table) if summary_table else {}
        output_summary = description.pop("_output_summary", None)

        v01_link_paras = sections.get(_SECTION_V01_LINK, [])
        description["v01_link_description"] = " ".join(
            o.text.strip() for k, o in v01_link_paras
            if k == "p" and o.text.strip() and o.style.name != "Caption")

        input_paras = [(o.style.name, o.text.strip()) for k, o in sections.get(_SECTION_INPUTS, [])
                        if k == "p" and o.text.strip()]
        inputs = extract_list_items(input_paras)

        problem_paras = [(o.style.name, o.text.strip()) for k, o in sections.get(_SECTION_PROBLEMS, [])
                          if k == "p" and o.text.strip()]
        problems = extract_list_items(problem_paras)

        subjects_table = next((o for k, o in sections.get(_SECTION_SUBJECTS, []) if k == "tbl"), None)
        subjects = []
        if subjects_table is not None:
            for row in _table_rows(subjects_table):
                subj_cell, role_cell = (row + ["", ""])[:2]
                name, abbr = parse_subject_cell(subj_cell)
                subjects.append({"name": name, "abbreviation": abbr, "process_role": role_cell})

        legal_paras = [o.text.strip() for k, o in sections.get(_SECTION_LEGAL_BASIS, [])
                       if k == "p" and o.text.strip()]
        legal_citations = []
        for text in legal_paras:
            legal_citations.extend(extract_citations(text))

        branches = parse_node_flow(sections.get(_SECTION_FLOW, []))
        outputs = parse_node_outputs(sections.get(_SECTION_OUTPUTS, []), output_summary)

        nodes[node_id] = {
            "description": description,
            "inputs": [{"seq_no": i + 1, "description": d, "is_specific_to_hydrogen": False}
                        for i, d in enumerate(inputs)],
            "branches": branches,
            "subjects": subjects,
            "outputs": outputs,
            "problems": [dict(zip(("title", "description"), split_problem_text(p)), seq_no=i + 1)
                          for i, p in enumerate(problems)],
            "legal_basis_citations": sorted(set(legal_citations)),
        }

    # --- node -> document mapping table ---
    for idx, (kind, obj) in enumerate(elements):
        if kind == "p" and "Mapování procesních uzlů" in obj.text:
            for k2, o2 in elements[idx + 1:idx + 4]:
                if k2 == "tbl":
                    for row in _table_rows(o2):
                        node_cell, _, examples_cell = (row + ["", "", ""])[:3]
                        node_id = node_cell.split("—")[0].strip()
                        node_document_examples[node_id] = extract_citations(examples_cell)
                    break
            break

    # --- bibliography ---
    in_biblio = False
    for kind, obj in elements:
        if kind == "p" and "Seznam použité literatury" in obj.text:
            in_biblio = True
            continue
        if in_biblio and kind == "p" and obj.text.strip():
            parsed = parse_bibliography_line(obj.text)
            if parsed:
                bibliography.append({"ref_id": parsed[0], "text": parsed[1]})

    return {"nodes": nodes, "node_document_examples": node_document_examples,
            "bibliography": bibliography}


def main():
    result = parse_docx(DOCX_PATH)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    n_branches = sum(len(n["branches"]) for n in result["nodes"].values())
    n_steps = sum(len(b["steps"]) for n in result["nodes"].values() for b in n["branches"])
    n_inputs = sum(len(n["inputs"]) for n in result["nodes"].values())
    n_outputs = sum(len(n["outputs"]) for n in result["nodes"].values())
    n_subjects = sum(len(n["subjects"]) for n in result["nodes"].values())
    n_problems = sum(len(n["problems"]) for n in result["nodes"].values())
    print(f"Parsed {len(result['nodes'])} nodes: {n_branches} branches, {n_steps} steps, "
          f"{n_inputs} inputs, {n_outputs} outputs, {n_subjects} subject-links, "
          f"{n_problems} problems, {len(result['bibliography'])} bibliography entries.")
    print(f"Wrote {OUTPUT_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
