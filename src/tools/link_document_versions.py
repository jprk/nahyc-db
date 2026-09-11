"""Links base-standard/amendment pairs into a single record with a real
version history, instead of two unrelated-looking Document rows that
merely happen to share a title (e.g. "STN EN 13445-2" + its "+A1"
amendment) — see doc/PLAN.md Step 1 follow-up #16.

Standards vs. laws: a norm's amendment (`+A1`, `/A1`, `/AC`) is the SAME
document, a later edition of the same designation — this is exactly what
`DocumentVersion` (with `is_current`) is for, and is what this script
populates. A LAW amended by a separately-numbered act (e.g. "426/2021
Sb." amending "266/1994 Sb.") is NOT the same case: both remain their own
permanently citable Document rows — that relationship instead belongs in
`document_relation`, loaded by `load_document_relations.py` from a small,
hand-curated file (detecting it reliably at corpus scale needs human
judgement, not a title/designation pattern).

Deliberately conservative, same philosophy as deduplicate_db.py's
znacka/jurisdikce vetoes: only groups records that share BOTH a
designation core (after stripping an amendment marker, an edition-date
suffix, and — for grouping only — IEC's "EN" -> "EN IEC" renumbering)
AND jurisdikce, and only acts on a group when there is real, structural
evidence it's genuinely a version pair — either an amendment marker, or
an actual EN/EN-IEC split within the group — never invents a version
history for records that just happen to share a title for an unrelated
reason.

Also handles a second real version-pair shape found auditing the
deferred "ambiguous renaming" duplicate-title bucket (doc/PLAN.md Step 1
follow-up #18): IEC's 2016+ renumbering of a whole standard series folds
its own committee prefix into the EN designation for a later edition —
e.g. "STN EN 60079-11" (2012) -> "STN EN IEC 60079-11" (2025) — the same
underlying standard, confirmed by identical annotations, just renamed
*and* re-edited at once, with no amendment marker at all. Ordering these
can't use `amendment_level()` (neither member has a marker), so
`version_sort_key()` adds the EN-IEC renumbering itself as a second,
purely structural signal (an "EN IEC ..." designation is never older
than a plain "EN ..." one for the same part number) — deliberately not
date-based, for the same reason `amendment_level()` isn't (this corpus's
free-text `platnost` is not reliably the specific edition's real date).

Run AFTER deduplicate_db.py, BEFORE init_db.py. Reads and rewrites
data/database_merged_deduplicated.json in place (same file, still one row
per real document identity — now some rows carry a "versions" list
recording their edition history instead of a single flat record). Also
writes data/orphan_amendment_review_queue.json — records with a real
amendment marker whose base standard was never found anywhere in the
corpus (Step 1 follow-up #19), flagged for later manual tracking-down
rather than silently left unlinked and undiscoverable.
"""
import json
import pathlib
import re

BASE_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent
DEDUP_PATH = REPO_ROOT / "data" / "database_merged_deduplicated.json"
ORPHAN_QUEUE_PATH = REPO_ROOT / "data" / "orphan_amendment_review_queue.json"

_DASH_VARIANTS_RE = re.compile(r"[‐-―−]")  # en/em/figure/horizontal-bar dashes, minus sign
_AMENDMENT_MARKER_RE = re.compile(r"(\+A\d+|/A\d+|/AC)\b", re.IGNORECASE)
# Permissive trailing-edition-date matcher for GROUPING purposes only
# (not the exact-match dedup used by deduplicate_db.py's normalize_znacka)
# — stripping the amendment marker first can remove the "/" that
# normalize_znacka's own suffix regex requires (e.g. "13322-2/A1 – 2003.12"
# -> "13322-2 – 2003.12", no leading "/" left), so this one tolerates a
# bare "- YYYY.MM"/"- YYYY-MM" tail with no required leading slash.
_TRAILING_DATE_ANY_RE = re.compile(r"[/\s]*-\s*\d{4}[.\-]\d{2}\s*$")
# IEC's 2016+ series-renumbering convention: "EN 60079-11" -> "EN IEC
# 60079-11" for a later edition of the SAME standard (see module
# docstring). Folding this narrow, explicit pattern (not a blanket "drop
# every IEC") for GROUPING purposes only lets a genuine pre-/post-rename
# pair share a core; a true EN/IEC split within a group (checked in
# `build_version_groups` via `_has_en_iec_renumbering`) is itself the
# evidence such a group is real, the same role an amendment marker plays
# for the other version-pair shape.
_EN_IEC_RENUMBER_RE = re.compile(r"\bEN\s+IEC\b", re.IGNORECASE)


def version_group_key(znacka, fold_en_iec_renumbering=False):
    """Amendment-marker-and-edition-date-stripped core of a znacka, used
    only to GROUP a base standard with its amendment(s)/later renumbered
    edition — not a general identity key (deduplicate_db.py's
    normalize_znacka/core_znacka remain the ones used for that). With
    `fold_en_iec_renumbering=True`, also folds "EN IEC" -> "EN" (see
    `_EN_IEC_RENUMBER_RE`) so e.g. "STN EN 60079-11" and "STN EN IEC
    60079-11" land on the same core."""
    zn = _DASH_VARIANTS_RE.sub("-", str(znacka))
    zn = _AMENDMENT_MARKER_RE.sub("", zn)
    zn = _TRAILING_DATE_ANY_RE.sub("", zn)
    if fold_en_iec_renumbering:
        zn = _EN_IEC_RENUMBER_RE.sub("EN", zn)
    return " ".join(zn.split()).strip().lower()


def amendment_level(znacka):
    """0 for an unamended base designation; otherwise the amendment's own
    number (e.g. "+A1" -> 1, "+A2" -> 2), or 1 for a marker with no
    number (a corrigendum, "/AC"). Deliberately not date-parsing-based:
    this corpus's own free-text `platnost`/edition-date fields are not
    reliably the version's real publication date (e.g. one base record's
    `platnost` carries an unrelated internal work-item tracking date
    instead)."""
    m = _AMENDMENT_MARKER_RE.search(str(znacka))
    if not m:
        return 0
    digits = re.search(r"\d+", m.group(0))
    return int(digits.group(0)) if digits else 1


def _has_en_iec_renumbering(znacka):
    """True if this designation already carries IEC's post-2016 "EN IEC"
    renumbering — a purely structural signal that this edition is never
    older than a plain "EN ..." sibling of the same part number (see
    module docstring); used both to validate a group and to order it."""
    return bool(_EN_IEC_RENUMBER_RE.search(str(znacka)))


def version_sort_key(znacka):
    """Orders a version group's members: amendment level first (an
    amendment is never older than its base), then whether the
    designation has been through the EN-IEC renumbering (never older
    than a plain "EN ..." sibling). Two independent, purely structural
    signals — never date-based, see amendment_level()/
    _has_en_iec_renumbering()."""
    return (amendment_level(znacka), 1 if _has_en_iec_renumbering(znacka) else 0)


def _norm_title(title):
    return re.sub(r"\s+", " ", (title or "").strip().lower())


def build_version_groups(records):
    """Groups records that share both a version_group_key (with EN-IEC
    renumbering folded in, so a pre-/post-rename pair lands together) and
    jurisdikce, keeping only groups of >= 2 members with real structural
    evidence they're genuinely a version pair — at least one member
    carries an amendment marker, OR the group contains an actual EN/
    EN-IEC split (some member's designation has the renumbering, some
    doesn't) — never a bare coincidental designation-core collision."""
    groups = {}
    for r in records:
        znacka = r.get("znacka") or ""
        if not znacka:
            continue
        key = (version_group_key(znacka, fold_en_iec_renumbering=True), r.get("jurisdikce") or "")
        groups.setdefault(key, []).append(r)

    valid = []
    for members in groups.values():
        if len(members) < 2:
            continue
        has_amendment = any(amendment_level(m["znacka"]) > 0 for m in members)
        en_iec_flags = {_has_en_iec_renumbering(m["znacka"]) for m in members}
        has_en_iec_split = len(en_iec_flags) > 1
        if has_amendment or has_en_iec_split:
            valid.append(members)
    return valid


def merge_version_group(members):
    """Merges a version group into one record: the highest-ranked member's
    (see version_sort_key) own fields (title, annotation, kategorie, url,
    ...) become the record's current/top-level fields (same convention as
    Document.effective_date elsewhere — reflects the CURRENT edition),
    keywords are unioned, and a "versions" list records every member's own
    designation/edition date/current flag for init_db.py to load as
    separate DocumentVersion rows."""
    ordered = sorted(members, key=lambda m: version_sort_key(m["znacka"]))
    current = ordered[-1]

    merged = dict(current)
    keywords = []
    seen_kw = set()
    for m in ordered:
        for kw in (m.get("klicova_slova") or []):
            if kw not in seen_kw:
                seen_kw.add(kw)
                keywords.append(kw)
    merged["klicova_slova"] = keywords

    sources = sorted({m.get("zdroj_dat", "") for m in ordered if m.get("zdroj_dat")})
    merged["zdroj_dat"] = ", ".join(sources)

    merged["versions"] = [
        {
            "znacka": m.get("znacka", ""),
            "edition_label": m.get("znacka", ""),
            "effective_date": m.get("platnost", ""),
            "is_current": m is current,
        }
        for m in ordered
    ]
    return merged


def link_document_versions(records):
    """Returns a new list: version groups collapsed to one merged record
    each (with a "versions" list), every other record untouched."""
    groups = build_version_groups(records)
    grouped_ids = {id(m) for group in groups for m in group}
    result = [merge_version_group(group) for group in groups]
    result.extend(r for r in records if id(r) not in grouped_ids)
    return result


def find_orphan_amendments(records):
    """Records that carry a real amendment marker (see amendment_level())
    but never joined a valid version group — meaning their base standard
    was never collected from any source, so there is nothing to link
    them to (confirmed corpus-wide, not just within their own
    jurisdikce — see doc/PLAN.md Step 1 follow-up #18/#19). Returned so
    a human can track down and add the missing base later, without
    silently leaving them unflagged."""
    groups = build_version_groups(records)
    grouped_ids = {id(m) for group in groups for m in group}
    return [r for r in records
            if id(r) not in grouped_ids and amendment_level(r.get("znacka") or "") > 0]


def main():
    if not DEDUP_PATH.exists():
        print(f"Vstupní soubor neexistuje: {DEDUP_PATH}")
        return

    with open(DEDUP_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)

    before = len(records)
    groups = build_version_groups(records)
    orphans = find_orphan_amendments(records)
    linked = link_document_versions(records)

    with open(DEDUP_PATH, "w", encoding="utf-8") as f:
        json.dump(linked, f, ensure_ascii=False, indent=2)

    with open(ORPHAN_QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump([
            {
                "znacka": r.get("znacka", ""),
                "nazev_cz": r.get("nazev_cz", ""),
                "jurisdikce": r.get("jurisdikce", ""),
                "note": "Amendment marker present but no base standard found anywhere in the "
                        "corpus (checked across all jurisdikce) — source never collected the "
                        "base edition this amends.",
            }
            for r in orphans
        ], f, ensure_ascii=False, indent=2)

    print(f"Načteno {before} záznamů, nalezeno {len(groups)} skupin vydání/novel "
          f"({sum(len(g) for g in groups)} záznamů), sloučeno na {len(linked)} celkem.")
    for group in groups:
        titles = {_norm_title(m.get("nazev_cz")) for m in group}
        label = next(iter(titles)) if len(titles) == 1 else "/".join(titles)
        print(f"  - {label[:70]}: " + ", ".join(m.get("znacka", "") for m in
              sorted(group, key=lambda m: version_sort_key(m["znacka"]))))
    print(f"{len(orphans)} osiřelá(ch) novela/oprava bez nalezeného základu -> {ORPHAN_QUEUE_PATH}")


if __name__ == "__main__":
    main()
