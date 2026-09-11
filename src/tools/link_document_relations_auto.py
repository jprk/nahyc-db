"""Mechanically detects two shapes of document-to-document relationship
directly from `data/database_merged_deduplicated.json`, and writes them to
`data/document_relations_auto.json` in the same shape
`load_document_relations.py` already loads (see doc/PLAN.md §6, R1.3/R1.4):

- **R1.4 (standard localization, `ADOPTS`)**: a national (or EU-tier)
  adoption of an international standard — e.g. "STN EN ISO 11114-4"
  ADOPTS "ISO 11114-4" — grouped by `international_core()` (strips the
  national-body prefix, and a further "EN " layer when it's immediately
  followed by ISO/IEC, since "STN EN ISO X"/"EN ISO X"/"ISO X" are all
  ultimately the same underlying standard at three different tiers) and
  by jurisdikce *tier* (mezinárodní/EU vs. a real national code — the
  same three-way split as `Document.jurisdikce_uroven`, computed here
  directly from the JSON's `jurisdikce` field since this runs BEFORE
  `init_db.py`). A group only links when it has at least one
  international/EU "parent" AND at least one national "child" — every
  child gets an `ADOPTS` edge to EVERY parent in its group (a group with
  more than one international edition present gets more than one edge,
  deliberately, rather than guessing which specific edition a child
  adopted).

- **R1.3 (EU transposition, `IMPLEMENTS`)**: a national law whose own
  `nazev_eu`/`odkaz_eu` field cites a *different* EU act (self-citations
  — the record citing its own designation — are excluded) that already
  exists as its own record in the corpus becomes an `IMPLEMENTS` edge.
  Records whose OWN designation is itself EU-act-styled (see
  `is_eu_act_znacka()`) are excluded from the citing side — an EU
  delegated/implementing act citing its own parent directive is a real
  relationship, but EU-to-EU, not R1.3's national-to-EU shape (jurisdikce
  can't be used for this distinction: it's left empty for both national
  laws and EU acts alike in this corpus's law sources, so the designation
  shape is the only reliable signal). When the cited EU act does NOT yet
  exist as a record, the candidate is written to
  `data/eu_transposition_missing_targets.json` instead of silently dropped
  or guessed — same review-queue philosophy as everywhere else in this
  pipeline.

Both mechanisms are deliberately narrow and evidence-based (same
philosophy as deduplicate_db.py's znacka/jurisdikce vetoes and
link_document_versions.py's amendment/EN-IEC checks): a relation is only
emitted when both sides of it are records that already exist in the
corpus, never fabricated.

Run any time after deduplicate_db.py, before load_document_relations.py
(which loads this file's output alongside the hand-curated
data/document_relations.json).
"""
import json
import pathlib
import re

BASE_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent
DEDUP_PATH = REPO_ROOT / "data" / "database_merged_deduplicated.json"
AUTO_RELATIONS_PATH = REPO_ROOT / "data" / "document_relations_auto.json"
MISSING_TARGETS_PATH = REPO_ROOT / "data" / "eu_transposition_missing_targets.json"

# --- R1.4: standard localization ("ADOPTS") --------------------------------

_DASH_VARIANTS_RE = re.compile(r"[‐-―−]")
_EDITION_DATE_SUFFIX_RE = re.compile(r"/\s*-\s*\d{4}\.\d{2}\s*$")
_COLON_YEAR_SUFFIX_RE = re.compile(r"\s*:\s*\d{4}\s*$")
_COLON_YEAR_MONTH_SUFFIX_RE = re.compile(r"\s*:\s*\d{4}-\d{2}\s*$")
_KNOWN_SERIES_SEPARATOR_RES = [  # see deduplicate_db.py
    re.compile(r"\bCSA\s*/?\s*ANSI\b", re.IGNORECASE),
    re.compile(r"\bIGEM\s*/?\s*TD\s*/?\s*1\b", re.IGNORECASE),
]
_EIGA_IGC_PREFIX_RE = re.compile(r"^(?:EIGA\s+Doc\s+|EIGA\s+|IGC\s+Doc\s+)", re.IGNORECASE)
_NATIONAL_PREFIX_RE = re.compile(r"^(?:STN|ČSN|CSN|TNI|DIN|VDE|NF|BS|NEN)\s+", re.IGNORECASE)
_EN_ISO_IEC_RE = re.compile(r"^EN\s+(ISO|IEC)\b", re.IGNORECASE)


def international_core(znacka):
    """Strips a national-body prefix, then a leading "EN " ONLY when an
    ISO/IEC designation follows it — "STN EN ISO 11114-4"/"EN ISO
    11114-4"/"ISO 11114-4" all reduce to "iso 11114-4". A bare "EN 1717"
    (no ISO/IEC after it) is left alone — it IS the origin, not a
    re-badging of something else."""
    zn = str(znacka)
    for pattern in _KNOWN_SERIES_SEPARATOR_RES:
        zn = pattern.sub(lambda m: re.sub(r"[\s/]", "", m.group(0)), zn)
    zn = _EIGA_IGC_PREFIX_RE.sub("", zn)
    zn = _DASH_VARIANTS_RE.sub("-", zn)
    zn = " ".join(zn.split()).strip()
    zn = _EDITION_DATE_SUFFIX_RE.sub("", zn)
    zn = _COLON_YEAR_MONTH_SUFFIX_RE.sub("", zn)
    zn = _COLON_YEAR_SUFFIX_RE.sub("", zn)
    zn = _NATIONAL_PREFIX_RE.sub("", zn).strip()
    zn = _EN_ISO_IEC_RE.sub(lambda m: m.group(1), zn)
    return zn.strip().lower()


def jurisdikce_tier(jurisdikce):
    """Mirrors Document.jurisdikce_uroven's GENERATED expression (see
    doc/konsolidace/Konsolidace-DB-schema.sql) — computed here directly
    from the JSON's jurisdikce field, since this script runs before
    init_db.py. Returns "mezinárodní", "EU", "národní", or None
    (unknown/neurčeno — never guessed)."""
    j = (jurisdikce or "").strip()
    if j == "mezinárodní":
        return "mezinárodní"
    if j == "EU":
        return "EU"
    if not j or j == "neurčeno":
        return None
    return "národní"


def find_localization_pairs(records):
    """Returns a list of (child_record, parent_record) ADOPTS pairs."""
    groups = {}
    for r in records:
        znacka = r.get("znacka") or ""
        if not znacka or "\n" in znacka:
            continue
        key = international_core(znacka)
        if key:
            groups.setdefault(key, []).append(r)

    pairs = []
    for members in groups.values():
        if len(members) < 2:
            continue
        parents = [m for m in members if jurisdikce_tier(m.get("jurisdikce")) in ("mezinárodní", "EU")]
        children = [m for m in members if jurisdikce_tier(m.get("jurisdikce")) == "národní"]
        if not parents or not children:
            continue
        for child in children:
            for parent in parents:
                pairs.append((child, parent))
    return pairs


# --- R1.3: EU transposition ("IMPLEMENTS") ---------------------------------

_EU_REF_RE = re.compile(
    # "(EU) č. NNN/YYYY" (pre-2015 numbering) or "(EU) YYYY/NNN" (2015+
    # numbering) -- both orders appear for real in this corpus. "EC" is
    # the English abbreviation for the same body "ES" names in Czech
    # (both appear in this corpus depending on source language).
    r"\((?:EU|ES|EC|EÚ|EEC|EHS)\)\s*(?:č\.\s*|No\s*)?(\d+/\d+)"
    r"|(\d{4}/\d+/(?:ES|EC|EU|EÚ|EEC|EHS))",
    re.IGNORECASE,
)


def digit_core(znacka):
    """"283/2021 Sb." -> "283/2021"; "(EU) 2023/1804" -> "2023/1804";
    "2019/692/EU" -> "2019/692". None if no digit/year pair at all."""
    text = znacka or ""
    m = re.search(r"\d+/\d{4}", text)
    if m:
        return m.group(0)
    m = re.search(r"\d{4}/\d+", text)
    if m:
        return m.group(0)
    return None


def _normalized_digit_pair(ref_text):
    """A digit-core extracted from free text can appear as 'NNN/YYYY' or
    'YYYY/NNN' depending on style — returns both orderings so either can
    be matched against a real digit_core()."""
    m = re.match(r"(\d+)/(\d+)", ref_text)
    if not m:
        return {ref_text}
    a, b = m.groups()
    return {f"{a}/{b}", f"{b}/{a}"}


_EU_ACT_ZNACKA_RE = re.compile(
    r"^\((?:EU|ES|EC|EÚ|EEC|EHS)\)|/(?:EU|ES|EC|EÚ|EEC|EHS)\s*$", re.IGNORECASE
)


def is_eu_act_znacka(znacka):
    """True when a record's OWN designation is itself styled as an EU act
    ("(EU) 2023/1184", "2019/692/EU") rather than a national law ("458/2000
    Sb.") or a standard. Used instead of jurisdikce_tier() to identify
    EU-to-EU citations (e.g. a delegated act citing its own parent
    directive) because in this corpus jurisdikce is left empty for BOTH
    national laws and EU acts alike (Sinay_Zakony/Haltuf_Dokumenty never
    populate it) — the designation shape is the only reliable signal."""
    return bool(_EU_ACT_ZNACKA_RE.search(str(znacka or "")))


def find_eu_transposition_pairs(records):
    """Returns (pairs, missing) — pairs is a list of (national_record,
    eu_record) IMPLEMENTS edges where the cited EU act already exists as
    its own record; missing is a list of (national_record, cited_ref_text)
    where it doesn't. R1.3 asks specifically for EU-directive-to-NATIONAL-
    law transposition links — citing records whose OWN designation is
    itself EU-act-styled (see is_eu_act_znacka()) are excluded, so an EU
    delegated/implementing act citing its own parent directive (a real,
    but EU-to-EU, not R1.3's national-to-EU shape) is correctly left out.
    jurisdikce is deliberately NOT used for this filter: it's empty for
    both national laws and EU acts alike in this corpus's law sources."""
    by_digit_core = {}
    for r in records:
        dc = digit_core(r.get("znacka") or "")
        if dc:
            by_digit_core.setdefault(dc, []).append(r)

    pairs, missing = [], []
    for r in records:
        znacka = (r.get("znacka") or "").strip()
        if not znacka or "\n" in znacka:
            continue  # no usable identifier to be the "from" side of any relation
        if is_eu_act_znacka(znacka):
            continue
        text = f"{r.get('nazev_eu') or ''} {r.get('odkaz_eu') or ''}"
        own_core = digit_core(r.get("znacka") or "")
        seen_refs = set()
        # A citation can mention several EU acts (e.g. "...amending
        # Regulations (EC) No 715/2009, (EU) 2019/942 and..."); check
        # EVERY match, not just the first — the first one is often the
        # record's own self-citation (harmless, but must not cause later,
        # genuinely different references in the same text to be skipped).
        for m in _EU_REF_RE.finditer(text):
            ref = m.group(1) or m.group(2)
            ref_digits = re.search(r"\d+/\d+", ref)
            if not ref_digits:
                continue
            candidates = _normalized_digit_pair(ref_digits.group(0))
            if own_core in candidates or ref_digits.group(0) in seen_refs:
                continue  # self-citation, or an already-handled duplicate mention
            seen_refs.add(ref_digits.group(0))
            target = None
            for cand in candidates:
                if cand in by_digit_core:
                    target = by_digit_core[cand][0]
                    break
            if target is not None and target is not r:
                pairs.append((r, target))
            else:
                missing.append((r, ref))
    return pairs, missing


def _relation_entry(from_rec, to_rec, relation_type, note):
    return {
        "from_identifier": from_rec.get("znacka", ""),
        "to_identifier": to_rec.get("znacka", ""),
        "relation_type": relation_type,
        "note": note,
    }


def main():
    if not DEDUP_PATH.exists():
        print(f"Vstupní soubor neexistuje: {DEDUP_PATH}")
        return

    with open(DEDUP_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)

    localization_pairs = find_localization_pairs(records)
    transposition_pairs, missing_targets = find_eu_transposition_pairs(records)

    relations = [
        _relation_entry(child, parent, "ADOPTS",
                         "Národní/EU adopce mezinárodní normy (stejné mezinárodní jádro značky) "
                         "— viz doc/PLAN.md §6, R1.4.")
        for child, parent in localization_pairs
    ] + [
        _relation_entry(national, eu_act, "IMPLEMENTS",
                         "Národní zákon cituje tento akt EU ve vlastním poli nazev_eu/odkaz_eu "
                         "— viz doc/PLAN.md §6, R1.3.")
        for national, eu_act in transposition_pairs
    ]

    with open(AUTO_RELATIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(relations, f, ensure_ascii=False, indent=2)

    with open(MISSING_TARGETS_PATH, "w", encoding="utf-8") as f:
        json.dump([
            {"znacka": r.get("znacka", ""), "nazev_cz": r.get("nazev_cz", ""),
             "cited_eu_reference": ref}
            for r, ref in missing_targets
        ], f, ensure_ascii=False, indent=2)

    print(f"R1.4 (ADOPTS): {len(localization_pairs)} hran.")
    print(f"R1.3 (IMPLEMENTS): {len(transposition_pairs)} hran, {len(missing_targets)} kandidátů "
          f"s chybějícím cílem -> {MISSING_TARGETS_PATH}")
    print(f"Celkem {len(relations)} vztahů zapsáno do {AUTO_RELATIONS_PATH}")


if __name__ == "__main__":
    main()
