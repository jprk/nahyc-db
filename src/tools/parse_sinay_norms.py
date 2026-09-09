"""Parses the two Sinay raw sources that were never actually processed:
- data/20250712_Sinay/raw/Zoznam_noriem_vodik-11_02_2025.pdf (a static,
  4-column export of technical standards relevant to hydrogen — Slovak
  STN-adopted norms plus foreign/international ones, "frozen" 11.2.2025).
- data/20250712_Sinay/raw/Zoznam_noriem_Vodik_Road_map_Nemecko_Priradenie_STN_VERZIA_2024_06_27b.xlsx
  (the German "Normungsroadmap Wasserstoff" inventory, with a proposed
  mapping onto the Slovak STN system).

Both are lists of NORMS/STANDARDS (not laws), so the output schema mirrors
data/20250303_Prokop/normy_vodik.json's keys (Sekce, Značka, Název,
Kategorie, Platnost, Anotace, Klíčová slova, Link) rather than Haltuf's —
that's the closer match for this kind of content, and "compatible with
both" is satisfied at the level of build_unified_db.py's Prokop-branch
field names, which this can be loaded through with minimal changes. One
key added beyond Prokop's schema: "Jurisdikce" — unlike Prokop's ČSN norms
(implicitly all CZ-valid), this source is majority Slovak (STN) and German
norms, which are NOT valid in Czechia just because they share an EN/ISO
ancestor with a ČSN. See classify_jurisdikce() below and
doc/PLAN.md Step 1 follow-up #8.

Output: data/20250712_Sinay/sinay_normy_processed.json (list, combining
both sources). Records with no extractable title are dropped (mirrors a
handful of PDF rows that turned out to be technical-committee references,
not documents — see the module docstring in build_unified_db.py for the
same convention elsewhere in this pipeline).
"""
import datetime
import json
import pathlib
import re

import openpyxl
import pdfplumber

# ---------------------------------------------------------------------------
# Jurisdiction: a norm's own numbering (e.g. "17124") can be shared across a
# Slovak STN adoption, a German DIN/VDI catalog entry, and a Czech ČSN
# adoption of the SAME underlying EN/ISO standard — but each national
# adoption is its own legally distinct document, only valid in its own
# jurisdiction. An STN or German norm is NOT automatically valid in Czechia
# just because it shares an EN/ISO ancestor with a ČSN (see
# doc/PLAN.md Step 1 follow-up #8) — this field exists so the merge
# pipeline can tell them apart and never conflate them, and so a human
# skimming the data isn't misled into thinking a Slovak-only or
# German-only norm applies in CZ.
# ---------------------------------------------------------------------------
_JURISDICTION_MARKERS = [
    # (regex matched case-insensitively against "znacka kategorie", jurisdiction)
    (r"\bSTN\b", "SK"),
    (r"\bCEN/TC\b|\bCENELEC\b|\bCLC/", "EU"),
    (r"\bEIGA\b", "EU"),
    (r"\bISO/TC\b|\bIEC/TC\b|\bISO\b|\bIEC\b", "mezinárodní"),
    (r"\bDVGW\b|\bDIN\b|\bVDI\b|\bDASt\b|\bDGUV\b|\bBVEG\b|\bBAuA\b|\bNA\b|\bTRBS\b|\bTRGS\b|\bAD[ -]?2000\b|\bAD-Merkblatt\b",
     "DE"),
    (r"\bASTM\b|\bASME\b|\bAPI\b|\bCGA\b|\bANSI\b|\bAIAA\b|\bNFPA\b|\bNASA\b|\bAMPP\b|\bNACE\b", "US"),
    (r"\bCSA\b", "CA"),
    (r"\bBSI\b", "UK"),
    (r"\bAFNOR\b", "FR"),
    (r"\bNEN\b", "NL"),
]


_BARE_EN_DESIGNATION_RE = re.compile(r"^(?:pr|F\s*pr)?EN\s+\d", re.IGNORECASE)


def classify_jurisdikce(znacka, kategorie=""):
    """Best-effort jurisdiction from the designation/issuing-body text.
    Checked in order — STN first (unambiguous, most common), international
    bodies before national ones sharing a token (e.g. avoid "ISO" text
    inside an unrelated committee name matching before the real ISO
    check). Returns "neurčeno" rather than guess when nothing matches —
    same fail-safe philosophy as extract_znacka_from_title() in
    build_unified_db.py.
    """
    znacka = znacka.strip()
    haystack = f"{znacka} {kategorie}"
    for pattern, jurisdikce in _JURISDICTION_MARKERS:
        if re.search(pattern, haystack, re.IGNORECASE):
            return jurisdikce
    # A designation that IS a bare (draft) European Norm number, with no
    # national prefix at all (already ruled out above) — e.g. "EN 1717",
    # "prEN 13480-9", "FprEN 62282-3-400" — is itself a CEN-level document.
    if _BARE_EN_DESIGNATION_RE.match(znacka):
        return "EU"
    return "neurčeno"


BASE_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent
SINAY_DIR = REPO_ROOT / "data" / "20250712_Sinay"

PDF_PATH = SINAY_DIR / "raw" / "Zoznam_noriem_vodik-11_02_2025.pdf"
XLSX_PATH = SINAY_DIR / "raw" / "Zoznam_noriem_Vodik_Road_map_Nemecko_Priradenie_STN_VERZIA_2024_06_27b.xlsx"
OUTPUT_PATH = SINAY_DIR / "sinay_normy_processed.json"


# ---------------------------------------------------------------------------
# PDF: Zoznam_noriem_vodik-11_02_2025.pdf
#
# A 4-column table (Designation | Title | Verification URL | Note) with no
# gridlines, so pdfplumber's own table detection finds nothing — reconstruct
# columns from word x-positions instead. Each logical row's title/URL/note
# can wrap across several visual lines; a row's boundaries are anchored by
# the Designation column, which never wraps EXCEPT for the trailing
# "YYYY.MM" date suffix on long designations, handled as a special case
# below (found by testing against the real file: ~1/26 rows would otherwise
# split into a bogus extra row with an empty title).
# ---------------------------------------------------------------------------

_PDF_COLUMNS = [
    ("designation", 0, 175),
    ("title", 175, 550),
    ("url", 550, 700),
    ("note", 700, 10_000),
]
_DATE_FRAGMENT_RE = re.compile(r"^\d{4}\.\d{2}$")
_PAGE_FOOTER_RE = re.compile(r"\s*Strana\s+\d+\s+z\s+\d+\s*$")
_DESIGNATION_DATE_RE = re.compile(r"(\d{4})\.(\d{2})\s*$")


def _pdf_column_of(x0):
    for name, lo, hi in _PDF_COLUMNS:
        if lo <= x0 < hi:
            return name
    return None


def _group_into_lines(words, tolerance=2.0):
    """Groups words with close 'top' (y-position) values into visual
    lines, returned as [(top, joined_text), ...] in top-to-bottom order."""
    words = sorted(words, key=lambda w: w["top"])
    lines = []
    current_top = None
    current_words = []
    for w in words:
        if current_top is None or abs(w["top"] - current_top) <= tolerance:
            current_words.append(w)
            current_top = current_top if current_top is not None else w["top"]
        else:
            lines.append((current_top, " ".join(x["text"] for x in sorted(current_words, key=lambda x: x["x0"]))))
            current_words = [w]
            current_top = w["top"]
    if current_words:
        lines.append((current_top, " ".join(x["text"] for x in sorted(current_words, key=lambda x: x["x0"]))))
    return lines


def _parse_pdf_page(page, header_top_max=85):
    words = [w for w in page.extract_words() if w["top"] > header_top_max]
    by_column = {"designation": [], "title": [], "url": [], "note": []}
    for w in words:
        column = _pdf_column_of(w["x0"])
        if column:
            by_column[column].append(w)

    designation_lines = _group_into_lines(by_column["designation"])
    # Merge a bare "YYYY.MM" continuation line into the previous
    # designation — it's the wrapped tail of a long designation, not a
    # new row's start.
    merged = []
    for top, text in designation_lines:
        if merged and _DATE_FRAGMENT_RE.match(text.strip()):
            prev_top, prev_text = merged[-1]
            merged[-1] = (prev_top, f"{prev_text} {text.strip()}")
        else:
            merged.append((top, text))
    designation_lines = merged

    rows = []
    for i, (top, text) in enumerate(designation_lines):
        row_bottom = designation_lines[i + 1][0] if i + 1 < len(designation_lines) else float("inf")
        rows.append({"designation": text, "_top": top, "_bottom": row_bottom,
                     "title": [], "url": [], "note": []})

    for column in ("title", "url", "note"):
        for top, text in _group_into_lines(by_column[column]):
            for row in rows:
                if row["_top"] - 3 <= top < row["_bottom"] - 1:
                    row[column].append(text)
                    break

    for row in rows:
        for column in ("title", "url", "note"):
            row[column] = " ".join(row[column])
        row["note"] = _PAGE_FOOTER_RE.sub("", row["note"]).strip()
        del row["_top"], row["_bottom"]
    return rows


def _pdf_row_to_record(row):
    designation = row["designation"].strip()
    title = row["title"].strip()
    note = row["note"].strip()

    if note.lower().startswith("prijatá v sústave"):
        kategorie = "STN (prijatá v sústave)"
    else:
        kategorie = note

    platnost = ""
    m = _DESIGNATION_DATE_RE.search(designation)
    if m:
        year, month = m.groups()
        platnost = f"od {month}/{year}"

    return {
        "Sekce": "",
        "Značka": designation,
        "Název": title,
        "Kategorie": kategorie,
        "Jurisdikce": classify_jurisdikce(designation, kategorie),
        "Platnost": platnost,
        "Anotace": "",
        "Klíčová slova": "-",
        # URLs never legitimately contain whitespace — a wrapped URL split
        # across two visual lines in the PDF gets a stray space inserted
        # when the lines are rejoined (e.g. ".../standards.h tml"); strip
        # it entirely rather than just at the ends.
        "Link": re.sub(r"\s+", "", row["url"]),
    }


def parse_pdf(path=PDF_PATH):
    records = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            for row in _parse_pdf_page(page):
                if row["title"].strip():
                    records.append(_pdf_row_to_record(row))
    return records


# ---------------------------------------------------------------------------
# XLSX: Zoznam_noriem_Vodik_Road_map_Nemecko_Priradenie_STN_VERZIA_2024_06_27b.xlsx
#
# Sheet "NRM H2_Bestandsanalyse", header on row 14, data from row 15. A wide
# matrix of "AG x.x.x <topic>" applicability-flag columns (24-80) follows
# the bibliographic columns (1-15) — used here only to derive keywords.
# ---------------------------------------------------------------------------

_XLSX_SHEET = "NRM H2_Bestandsanalyse"
_XLSX_HEADER_ROW = 14
_XLSX_DATA_START_ROW = 15
_XLSX_AG_COLUMN_RANGE = range(24, 64)  # AG 1.1.1 .. AG 5.3 (UAK/AK summary columns 64-80 excluded — redundant, coarser)


def _xlsx_cell(ws, row, col):
    val = ws.cell(row=row, column=col).value
    if val is None:
        return ""
    return str(val).strip()


def _format_ausgabedatum(value):
    if value is None:
        return ""
    if isinstance(value, datetime.datetime):
        return value.strftime("%Y-%m")
    return str(value).strip()


def parse_xlsx(path=XLSX_PATH):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb[_XLSX_SHEET]

    ag_headers = {}
    for col in _XLSX_AG_COLUMN_RANGE:
        header = ws.cell(row=_XLSX_HEADER_ROW, column=col).value
        if header:
            # "AG 1.1.1 Elektrolyse" -> "Elektrolyse"
            ag_headers[col] = re.sub(r"^AG\s+[\d.]+\s*", "", header).strip()

    records = []
    for row_idx in range(_XLSX_DATA_START_ROW, ws.max_row + 1):
        stn_designation = _xlsx_cell(ws, row_idx, 3)
        foreign_designation = _xlsx_cell(ws, row_idx, 2)
        znacka = stn_designation or foreign_designation
        if not znacka:
            continue

        stn_title = _xlsx_cell(ws, row_idx, 5)
        title_en = _xlsx_cell(ws, row_idx, 10)
        title_de = _xlsx_cell(ws, row_idx, 9)
        if title_en and title_en != "Kein englischer Titel vorhanden":
            fallback_title = title_en
        else:
            fallback_title = title_de
        nazev = stn_title or fallback_title
        if not nazev:
            continue

        pub_form = _xlsx_cell(ws, row_idx, 1)
        committee = _xlsx_cell(ws, row_idx, 15)
        kategorie = pub_form
        if committee:
            kategorie = f"{pub_form} ({committee})" if pub_form else committee

        status = _xlsx_cell(ws, row_idx, 13) or _xlsx_cell(ws, row_idx, 7)
        issue_date = _format_ausgabedatum(ws.cell(row=row_idx, column=11).value)
        platnost = " / ".join(p for p in (status, issue_date) if p)

        anotace = _xlsx_cell(ws, row_idx, 14)

        keywords = [ag_headers[col] for col in _XLSX_AG_COLUMN_RANGE
                    if ag_headers.get(col) and _xlsx_cell(ws, row_idx, col).lower() == "x"]
        klicova_slova = ", ".join(keywords) if keywords else "-"

        # If the STN column (3) is populated, that's direct evidence of a
        # Slovak adoption — more reliable than the general heuristic.
        jurisdikce = "SK" if stn_designation else classify_jurisdikce(znacka, kategorie)

        records.append({
            "Sekce": "",
            "Značka": znacka,
            "Název": nazev,
            "Kategorie": kategorie,
            "Jurisdikce": jurisdikce,
            "Platnost": platnost,
            "Anotace": anotace,
            "Klíčová slova": klicova_slova,
            "Link": "",
        })
    return records


def main():
    pdf_records = parse_pdf()
    xlsx_records = parse_xlsx()

    print(f"PDF ({PDF_PATH.name}): {len(pdf_records)} records with a title extracted.")
    print(f"XLSX ({XLSX_PATH.name}): {len(xlsx_records)} records with a title extracted.")

    combined = pdf_records + xlsx_records
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=4)

    print(f"Done. {len(combined)} total records written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
