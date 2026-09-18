"""Imports the missing international-tier ISO parent standard for a
national (ČSN/STN/DIN/...) adoption that has no such record in the
corpus yet — doc/PLAN.md §37, 2026-09-18, user-directed follow-up to
the R1.4 (`ADOPTS`) coverage-gap investigation.

**What this closes**: `link_document_relations_auto.py`'s R1.4 mechanism
only creates an `ADOPTS` edge when BOTH a national adoption AND its
international/EU-tier parent already exist as separate `Document`
records — by design, it never fabricates the parent. Investigation
found 106 of the corpus's national ISO-derived standards (out of 134
candidates) have no such parent record at all: the source spreadsheets
(Prokop_Normy/Sinay_Normy) only ever catalogued the national adoption,
never the bare international standard as its own line item. This
script closes that specific gap by importing the missing parent
records — `link_document_relations_auto.py` itself is unchanged and
will pick up the new `ADOPTS` edges automatically on its next run.

**The technical unlock**: `iso.org` returns HTTP 403 to a plain
`requests`/`curl` fetch (confirmed live, matching the earlier §17.7
finding) — but, like `iec.ch`'s AWS WAF Bot Control challenge (§25),
headless Chromium via Playwright passes it cleanly (confirmed live:
both `iso.org/standard/<id>.html` and `iso.org/search.html?q=...` return
real HTTP 200 content). This reopens a source this project had
previously written off as blocked.

**Matching discipline, same "never guess" principle as everywhere else
in this pipeline**: for each missing designation (e.g. "ISO 17268"),
searches `iso.org/search.html?q=<number>` and accepts ONLY a result
whose visible label is an EXACT, anchored match of
`"{prefix} {number}:<year>"` — this deliberately excludes:
- a different part of a multi-part standard ("17268-1"/"17268-2" when
  the target is bare "17268"),
- a draft still in development ("ISO/DIS 17268-2" doesn't match the
  anchored "ISO 17268:" shape at all),
- a corrigendum/amendment of the base edition ("ISO/IEC
  80079-20-1:2017/Cor 1:2018" has trailing text after the year that the
  anchored pattern rejects).
When more than one clean-matching edition year is found, the newest is
used (deterministic, not a guess between them). A designation with no
clean match at all is logged, never fabricated.

**Two designations are deliberately excluded before any search
happens**: `STN EN ISO 11114-1/Zmena` and `DIN EN ISO 11114-1/A1` are
amendment MARKERS of ISO 11114-1, not a missing base standard — a bare
"ISO 11114-1" parent already exists in the corpus and is already
correctly linked to its main national editions; `iso_search_target()`
simply fails to parse these (the amendment suffix breaks the expected
"{prefix} {number}" shape), which is the correct outcome, not a bug to
fix here.

Usage:
    .venv/bin/python src/tools/add_missing_iso_parents.py [--limit N]

Output: `data/discovered_iso_parent_standards.json` (loaded by
`build_unified_db.py` as a further source), and
`data/iso_parent_unresolved.json` for designations that either don't
parse as a searchable ISO-family target or found no clean live match.
"""
import argparse
import json
import pathlib
import re
import sys

from playwright.sync_api import sync_playwright

BASE_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent
sys.path.insert(0, str(BASE_DIR))

from link_document_relations_auto import international_core, jurisdikce_tier  # noqa: E402

DEDUP_PATH = REPO_ROOT / "data" / "database_merged_deduplicated.json"
OUTPUT_PATH = REPO_ROOT / "data" / "discovered_iso_parent_standards.json"
UNRESOLVED_PATH = REPO_ROOT / "data" / "iso_parent_unresolved.json"

SEARCH_URL_TEMPLATE = "https://www.iso.org/search.html?q={query}"
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
SOURCE_NAME = "ISO_Catalog"

_ISO_TARGET_RE = re.compile(r"^p?\s*(iso(?:/iec|/ts|/tr)?)\s+([\d\-]+)$")
_PREFIX_DISPLAY = {"iso": "ISO", "iso/iec": "ISO/IEC", "iso/ts": "ISO/TS", "iso/tr": "ISO/TR"}


def iso_search_target(core):
    """`core` is an `international_core()` value (e.g. "iso 17268",
    "iso/ts 19870", or an amendment-suffixed "iso 11114-1/a1"). Returns
    (display_prefix, number) for a genuine base-standard designation, or
    None for anything that doesn't cleanly parse as one — including,
    deliberately, an amendment/corrigendum-suffixed core (see module
    docstring)."""
    m = _ISO_TARGET_RE.match(core)
    if not m:
        return None
    return _PREFIX_DISPLAY[m.group(1)], m.group(2)


def find_matching_iso_result(results, prefix, number):
    """`results` is a list of (url, label) pairs from a search page.
    Returns (url, label) for the highest-year label that is an EXACT,
    anchored match of "{prefix} {number}:<year>" — never a part/draft/
    corrigendum/amendment (see module docstring for why the anchoring
    excludes each of those) — or None if no clean match exists."""
    pattern = re.compile(rf"^{re.escape(prefix)} {re.escape(number)}:(\d{{4}})$")
    best, best_year = None, -1
    for url, label in results:
        m = pattern.match((label or "").strip())
        if m:
            year = int(m.group(1))
            if year > best_year:
                best_year, best = year, (url, label.strip())
    return best


def build_document_record(prefix, number, title, url):
    """The full Document-shape dict — matches the field convention of
    the corpus's EXISTING bare-ISO records exactly (`gestor`/`jazyk`
    left blank there too; `nazev_cz` is the fetched page title verbatim,
    same "DESIGNATION:YEAR Title" shape `page.title()` already returns)."""
    znacka = f"{prefix} {number}"
    return {
        "zdroj_dat": SOURCE_NAME,
        "nazev_cz": title,
        "znacka": znacka,
        "typ_dokumentu": "Norma",
        "sekce": "",
        "kategorie_trida": "",
        "klicova_slova": [],
        "odkaz_hlavni": url,
        "nazev_eu": "",
        "odkaz_eu": "",
        "nazev_sk": "",
        "odkaz_sk": "",
        "platnost": "",
        "ratifikovan": "",
        "gestor": [],
        "jazyk": "",
        "anotace_poznamka": (
            f"Doplněno jako chybějící mezinárodní rodičovský standard pro existující "
            f"národní adopci (doc/PLAN.md §37) — nalezeno a ověřeno živě na iso.org."),
        "jurisdikce": "mezinárodní",
    }


def find_missing_international_cores(records):
    """Returns {core: representative_znacka} for every group of national
    ISO-derived standards that has no international/EU-tier sibling
    present in the corpus at all — the exact gap R1.4 can't close on its
    own. Pure, reused from the investigation that found this gap."""
    iso_word_re = re.compile(r"\bISO\b", re.IGNORECASE)
    candidates = [r for r in records if r.get("typ_dokumentu") == "Norma"
                  and iso_word_re.search(r.get("znacka") or "")]
    national_candidates = [r for r in candidates if jurisdikce_tier(r.get("jurisdikce")) == "národní"]

    groups = {}
    for r in records:
        znacka = r.get("znacka") or ""
        if not znacka or "\n" in znacka:
            continue
        key = international_core(znacka)
        if key:
            groups.setdefault(key, []).append(r)

    missing = {}
    for r in national_candidates:
        core = international_core(r.get("znacka") or "")
        members = groups.get(core, [])
        if any(jurisdikce_tier(m.get("jurisdikce")) in ("mezinárodní", "EU") for m in members):
            continue
        missing.setdefault(core, r.get("znacka"))
    return missing


def load_json(path):
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int, default=None,
                         help="process at most N designations (for a manual smoke test)")
    args = parser.parse_args()

    with open(DEDUP_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)
    missing_cores = find_missing_international_cores(records)
    print(f"{len(missing_cores)} missing international-standard group(s) found in the corpus.")

    already_added = load_json(OUTPUT_PATH)
    already_added_znackas = {r["znacka"] for r in already_added if r.get("znacka")}
    unresolved = load_json(UNRESOLVED_PATH)
    unresolved_cores = {r["core"] for r in unresolved}

    added, skipped_unparseable, skipped_known, skipped_no_match = [], 0, 0, 0
    processed = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=USER_AGENT)
        page = context.new_page()

        for core, znacka in missing_cores.items():
            if args.limit is not None and processed >= args.limit:
                break
            processed += 1

            target = iso_search_target(core)
            if target is None:
                if core not in unresolved_cores:
                    unresolved.append({"core": core, "znacka": znacka,
                                        "reason": "does not parse as a base ISO-family designation "
                                                  "(likely an amendment/corrigendum marker)"})
                    unresolved_cores.add(core)
                skipped_unparseable += 1
                continue

            prefix, number = target
            candidate_znacka = f"{prefix} {number}"
            if candidate_znacka in already_added_znackas:
                skipped_known += 1
                continue

            resp = page.goto(SEARCH_URL_TEMPLATE.format(query=number), timeout=20000,
                             wait_until="networkidle")
            results = page.eval_on_selector_all(
                'a[href*="/standard/"]', "els => els.map(e => [e.href, e.textContent.trim()])")
            match = find_matching_iso_result(results, prefix, number)

            if match is None:
                if core not in unresolved_cores:
                    unresolved.append({"core": core, "znacka": znacka,
                                        "reason": f"no clean live match for '{prefix} {number}' "
                                                  f"among {len(results)} search result(s)"})
                    unresolved_cores.add(core)
                skipped_no_match += 1
                print(f"[skip] {candidate_znacka}: no clean match on iso.org")
                continue

            url, label = match
            page.goto(url, timeout=20000, wait_until="domcontentloaded")
            title = page.title()
            if not title:
                if core not in unresolved_cores:
                    unresolved.append({"core": core, "znacka": znacka,
                                        "reason": f"matched {url} but it returned no title live"})
                    unresolved_cores.add(core)
                skipped_no_match += 1
                continue

            record = build_document_record(prefix, number, title, url)
            added.append(record)
            already_added_znackas.add(candidate_znacka)
            print(f"[add] {candidate_znacka}: {title[:70]}")

        browser.close()

    save_json(UNRESOLVED_PATH, unresolved)
    all_added = already_added + added
    save_json(OUTPUT_PATH, all_added)

    print(f"\n{len(added)} new record(s) added this run "
          f"({skipped_unparseable} unparseable/amendment marker, "
          f"{skipped_known} already in corpus, "
          f"{skipped_no_match} no clean live match).")
    print(f"{len(all_added)} total in {OUTPUT_PATH.relative_to(REPO_ROOT)}; "
          f"{len(unresolved)} unresolved candidate(s) logged in "
          f"{UNRESOLVED_PATH.relative_to(REPO_ROOT)}.")


if __name__ == "__main__":
    main()
