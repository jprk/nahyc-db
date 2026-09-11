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
znacka/jurisdikce vetoes: only groups records that share BOTH an
amendment-marker-stripped designation core AND jurisdikce, and only acts
on a group when at least one member actually carries an amendment marker
— never invents a version history for records that just happen to share
a title for an unrelated reason.

Run AFTER deduplicate_db.py, BEFORE init_db.py. Reads and rewrites
data/database_merged_deduplicated.json in place (same file, still one row
per real document identity — now some rows carry a "versions" list
recording their edition history instead of a single flat record).
"""
import json
import pathlib
import re

BASE_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent
DEDUP_PATH = REPO_ROOT / "data" / "database_merged_deduplicated.json"

_DASH_VARIANTS_RE = re.compile(r"[‐-―−]")  # en/em/figure/horizontal-bar dashes, minus sign
_AMENDMENT_MARKER_RE = re.compile(r"(\+A\d+|/A\d+|/AC)\b", re.IGNORECASE)
# Permissive trailing-edition-date matcher for GROUPING purposes only
# (not the exact-match dedup used by deduplicate_db.py's normalize_znacka)
# — stripping the amendment marker first can remove the "/" that
# normalize_znacka's own suffix regex requires (e.g. "13322-2/A1 – 2003.12"
# -> "13322-2 – 2003.12", no leading "/" left), so this one tolerates a
# bare "- YYYY.MM"/"- YYYY-MM" tail with no required leading slash.
_TRAILING_DATE_ANY_RE = re.compile(r"[/\s]*-\s*\d{4}[.\-]\d{2}\s*$")


def version_group_key(znacka):
    """Amendment-marker-and-edition-date-stripped core of a znacka, used
    only to GROUP a base standard with its amendment(s) — not a general
    identity key (deduplicate_db.py's normalize_znacka/core_znacka remain
    the ones used for that)."""
    zn = _DASH_VARIANTS_RE.sub("-", str(znacka))
    zn = _AMENDMENT_MARKER_RE.sub("", zn)
    zn = _TRAILING_DATE_ANY_RE.sub("", zn)
    return " ".join(zn.split()).strip().lower()


def amendment_level(znacka):
    """0 for an unamended base designation; otherwise the amendment's own
    number (e.g. "+A1" -> 1, "+A2" -> 2), or 1 for a marker with no
    number (a corrigendum, "/AC"). Used ONLY to order a group's members
    (an amendment is, by definition, never older than the base it
    amends) — deliberately not date-parsing-based: this corpus's own
    free-text `platnost`/edition-date fields are not reliably the
    version's real publication date (e.g. one base record's `platnost`
    carries an unrelated internal work-item tracking date instead)."""
    m = _AMENDMENT_MARKER_RE.search(str(znacka))
    if not m:
        return 0
    digits = re.search(r"\d+", m.group(0))
    return int(digits.group(0)) if digits else 1


def _norm_title(title):
    return re.sub(r"\s+", " ", (title or "").strip().lower())


def build_version_groups(records):
    """Groups records that share both a version_group_key and jurisdikce,
    keeping only groups of >= 2 members where at least one carries a real
    amendment marker (the signal that this is genuinely a base+amendment
    situation, not a coincidental designation-core collision)."""
    groups = {}
    for r in records:
        znacka = r.get("znacka") or ""
        if not znacka:
            continue
        key = (version_group_key(znacka), r.get("jurisdikce") or "")
        groups.setdefault(key, []).append(r)
    return [members for members in groups.values()
            if len(members) > 1 and any(amendment_level(m["znacka"]) > 0 for m in members)]


def merge_version_group(members):
    """Merges a version group into one record: the highest-amendment-level
    member's own fields (title, annotation, kategorie, url, ...) become
    the record's current/top-level fields (same convention as
    Document.effective_date elsewhere — reflects the CURRENT edition),
    keywords are unioned, and a "versions" list records every member's own
    designation/edition date/current flag for init_db.py to load as
    separate DocumentVersion rows."""
    ordered = sorted(members, key=lambda m: amendment_level(m["znacka"]))
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


def main():
    if not DEDUP_PATH.exists():
        print(f"Vstupní soubor neexistuje: {DEDUP_PATH}")
        return

    with open(DEDUP_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)

    before = len(records)
    linked = link_document_versions(records)
    groups = build_version_groups(records)

    with open(DEDUP_PATH, "w", encoding="utf-8") as f:
        json.dump(linked, f, ensure_ascii=False, indent=2)

    print(f"Načteno {before} záznamů, nalezeno {len(groups)} skupin vydání/novel "
          f"({sum(len(g) for g in groups)} záznamů), sloučeno na {len(linked)} celkem.")
    for group in groups:
        titles = {_norm_title(m.get("nazev_cz")) for m in group}
        label = next(iter(titles)) if len(titles) == 1 else "/".join(titles)
        print(f"  - {label[:70]}: " + ", ".join(m.get("znacka", "") for m in
              sorted(group, key=lambda m: amendment_level(m["znacka"]))))


if __name__ == "__main__":
    main()
