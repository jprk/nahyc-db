"""Imports the EU acts cited (and independently re-verified) by
`populate_eu_transposition.py` (doc/PLAN.md §38) as their own `Document`
records, closing the R1.3 (`IMPLEMENTS`) gap the same way
`add_missing_iso_parents.py` closed R1.4's — doc/PLAN.md §39,
2026-09-18, user-directed.

`link_document_relations_auto.py`'s `find_eu_transposition_pairs()`
finds a citation whose target EU act isn't its own corpus record yet and
logs it to `data/eu_transposition_missing_targets.json`, keyed only by a
bare digit pair (`cited_eu_reference`, e.g. "2001/42/ES") extracted from
free text — deliberately with NO type or date attached, since that
function's own job is just "does a record already exist for this
digit pair", not resolution.

**Deliberately narrow scope, found live**: not every missing-target
digit pair is safe to resolve from the bare pair alone. Two shapes:

- **Directly cited** (the large majority): the national law's OWN
  footnote/annex names this exact act — already independently resolved,
  type-classified, AND date-verified by `populate_eu_transposition.py`
  when it built `data/eu_transposition_cache.json`'s `nazev_eu`/
  `odkaz_eu` fields. This script only ever re-uses THOSE already-
  verified (title, url) pairs — never re-resolves anything itself, and
  never queries EUR-Lex directly. `build_eu_act_registry()` indexes them
  by digit core (both possible year/number orderings, since some are
  pre-2015 "No NNN/YYYY"-style).
- **Secondary/incidental mention** (the rest): a digit pair that only
  appears because ONE OF THE ABOVE ACTS' OWN OFFICIAL TITLE mentions
  another act it amends/repeals (e.g. Regulation (EU) 2018/1999's own
  title lists nine other acts it changes) — `_EU_REF_RE.finditer()` in
  `link_document_relations_auto.py` scans the whole `nazev_eu` text
  blob, so these get swept up too, even though the CITING NATIONAL LAW
  never itself declared them as its own transposition targets. These
  have no independently-verified (title, url) pair, no date to check
  against, and real EU acts of different types collide constantly on a
  bare digit pair (confirmed live, doc/PLAN.md §38: "2011/92" is BOTH
  the EIA directive and an unrelated cheese-PDO regulation) — resolving
  them from the bare pair alone would reopen exactly the bug §38 fixed.
  Logged to `data/eu_transposition_secondary_references.json` instead of
  imported, for a human to decide whether they're worth pursuing
  separately (each would need its own citation context, not a blind
  digit lookup).

Idempotent two ways, both needed (found live, doc/PLAN.md §39 — a
second run to pick up one more target, after a separate fix, silently
DISCARDED the first run's 91 records before this was added): a
candidate whose digit core already matches an existing corpus record
(checked against `data/database_merged_deduplicated.json`) is skipped;
`data/discovered_eu_transposition_targets.json` itself is loaded first
and MERGED with, never overwritten — the corpus JSON isn't a reliable
"already added" signal on its own, since it only reflects whatever
`build_unified_db.py` last read, not necessarily this script's own
most recent output.

Usage:
    .venv/bin/python src/tools/import_eu_transposition_targets.py
"""
import json
import pathlib
import re
import sys

BASE_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent
sys.path.insert(0, str(BASE_DIR))

from link_document_relations_auto import digit_core, _normalized_digit_pair  # noqa: E402

DEDUP_PATH = REPO_ROOT / "data" / "database_merged_deduplicated.json"
CACHE_PATH = REPO_ROOT / "data" / "eu_transposition_cache.json"
MISSING_TARGETS_PATH = REPO_ROOT / "data" / "eu_transposition_missing_targets.json"
OUTPUT_PATH = REPO_ROOT / "data" / "discovered_eu_transposition_targets.json"
SECONDARY_REFERENCES_PATH = REPO_ROOT / "data" / "eu_transposition_secondary_references.json"

SOURCE_NAME = "EU_Transposition_Targets_Import"

_ELI_URL_RE = re.compile(r"/eli/([a-z_]+)/(\d{4})/(\d+)/oj")
_CELEX_URL_RE = re.compile(r"CELEX(?::|%3A)\d(\d{4})([A-Z])(\d+)", re.IGNORECASE)

_ELI_TYPE_MAP = {
    "dir": "Směrnice EU",
    "reg": "Nařízení EU",
    "dec": "Rozhodnutí EU", "dec_impl": "Rozhodnutí EU", "dec_del": "Rozhodnutí EU",
}
_CELEX_LETTER_TYPE_MAP = {"L": "Směrnice EU", "R": "Nařízení EU", "D": "Rozhodnutí EU"}


def build_eu_act_registry(cache):
    """{digit_core: (title, url)} for every INDEPENDENTLY resolved act in
    `data/eu_transposition_cache.json` — both digit orderings indexed
    (see module docstring), first entry for a given core wins. Only
    `status == "fetched"` entries contribute; their `nazev_eu`/
    `odkaz_eu` are newline-aligned lists of equal length by
    construction (`populate_eu_transposition.build_cache_entry()`)."""
    registry = {}
    for entry in cache.values():
        if entry.get("status") != "fetched":
            continue
        titles = entry.get("nazev_eu", "").split("\n")
        urls = entry.get("odkaz_eu", "").split("\n")
        if len(titles) != len(urls):
            continue
        for title, url in zip(titles, urls):
            core = digit_core(url) or digit_core(title)
            if not core:
                continue
            for variant in _normalized_digit_pair(core):
                registry.setdefault(variant, (title, url))
    return registry


def parse_act_url(url):
    """(doc_type, year, number) parsed from a `eur-lex.europa.eu` ELI or
    CELEX-style URL, or None if neither shape matches."""
    m = _ELI_URL_RE.search(url)
    if m:
        doc_type = _ELI_TYPE_MAP.get(m.group(1))
        if doc_type:
            return doc_type, int(m.group(2)), int(m.group(3))
    m = _CELEX_URL_RE.search(url)
    if m:
        doc_type = _CELEX_LETTER_TYPE_MAP.get(m.group(2).upper())
        if doc_type:
            return doc_type, int(m.group(1)), int(m.group(3))
    return None


def era_suffix(year):
    """The historically-appropriate abbreviation for the Community/Union
    at the time an act with this adoption year was numbered — EHS
    (EEC) before the 1993 Maastricht Treaty renamed it ES (EC), ES until
    the 2009 Lisbon Treaty renamed it EU. Cosmetic (digit_core() matching
    doesn't depend on it), but a bare "1985/337/EU" would be simply
    false — this corpus's own stated bar is never asserting something
    that isn't true."""
    if year < 1993:
        return "EHS"
    if year < 2009:
        return "ES"
    return "EU"


def build_znacka(year, number):
    return f"{year}/{number}/{era_suffix(year)}"


def build_document_record(title, url, doc_type, znacka):
    return {
        "zdroj_dat": SOURCE_NAME,
        "nazev_cz": title,
        "znacka": znacka,
        "typ_dokumentu": doc_type,
        "sekce": "",
        "kategorie_trida": "",
        "klicova_slova": [],
        "odkaz_hlavni": url,
        "nazev_eu": title,
        "odkaz_eu": url,
        "nazev_sk": "",
        "odkaz_sk": "",
        "platnost": "",
        "ratifikovan": "",
        "gestor": [],
        "jazyk": "",
        "anotace_poznamka": (
            "Doplněno jako chybějící cíl transpozice — akt EU citovaný vlastní "
            "poznámkou pod čarou/přílohou národního zákona, nezávisle ověřený "
            "proti EUR-Lex Cellar (doc/PLAN.md §38/§39)."
        ),
        "jurisdikce": "EU",
    }


def find_missing_eu_act_references(missing_targets):
    """Unique digit cores from `data/eu_transposition_missing_targets.json`
    (deduplicated — the same cited act is often logged once per citing
    national law)."""
    cores = set()
    for item in missing_targets:
        core = digit_core(item.get("cited_eu_reference", ""))
        if core:
            cores.add(core)
    return cores


def existing_corpus_digit_cores(records):
    cores = set()
    for r in records:
        core = digit_core(r.get("znacka", ""))
        if core:
            cores.add(core)
    return cores


def load_previously_discovered():
    """Records this script itself already wrote on an earlier run —
    idempotency at the OUTPUT level, not just at the "does the corpus
    already have this act" check `existing_corpus_digit_cores()` does.
    Found live, doc/PLAN.md §39: without this, a second run (e.g. to
    pick up one more target after `link_document_relations_auto.py`'s
    own digit-matching was separately improved) silently DISCARDED the
    first run's records — `database_merged_deduplicated.json` still had
    them at that point purely because `build_unified_db.py` hadn't been
    re-run yet, which is not something to rely on."""
    if OUTPUT_PATH.exists():
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def main():
    with open(DEDUP_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)
    with open(CACHE_PATH, "r", encoding="utf-8") as f:
        cache = json.load(f)
    with open(MISSING_TARGETS_PATH, "r", encoding="utf-8") as f:
        missing_targets = json.load(f)

    previously_discovered = load_previously_discovered()
    already_discovered_urls = {r["odkaz_hlavni"] for r in previously_discovered}

    registry = build_eu_act_registry(cache)
    existing_cores = existing_corpus_digit_cores(records)
    referenced_cores = find_missing_eu_act_references(missing_targets)

    added = []
    added_by_url = {}
    secondary = []
    for core in sorted(referenced_cores):
        if any(v in existing_cores for v in _normalized_digit_pair(core)):
            continue  # already exists in the corpus under some ordering
        hit = None
        for variant in _normalized_digit_pair(core):
            if variant in registry:
                hit = registry[variant]
                break
        if hit is None:
            secondary.append(core)
            continue
        title, url = hit
        if url in added_by_url or url in already_discovered_urls:
            continue
        parsed = parse_act_url(url)
        if parsed is None:
            secondary.append(core)
            continue
        doc_type, year, number = parsed
        record = build_document_record(title, url, doc_type, build_znacka(year, number))
        added.append(record)
        added_by_url[url] = record

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(previously_discovered + added, f, ensure_ascii=False, indent=2)

    with open(SECONDARY_REFERENCES_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted(secondary), f, ensure_ascii=False, indent=2)

    print(f"{len(referenced_cores)} unikátních citovaných referencí, "
          f"{len(added)} nových záznamů přidáno ({len(previously_discovered) + len(added)} celkem) "
          f"do {OUTPUT_PATH}, "
          f"{len(secondary)} vedlejších/nedohledatelných referencí -> {SECONDARY_REFERENCES_PATH}")


if __name__ == "__main__":
    main()
