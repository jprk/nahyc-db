"""Fetches HYTEP's (Česká vodíková technologická platforma / Czech
Hydrogen Technology Platform) own curated document listings and adds
them as real, verified Document records — doc/PLAN.md §31, 2026-09-17,
continuation of §28/§29/§30's corpus-expansion work into the "lower-
level guidance/methodologies" leg (HYTEP/EHTA/MPO/ERÚ/ÚNMZ, deferred at
§28.6). A live investigation this round found: EHTA is a one-off
teacher-training programme with no documents at all (dropped); ERÚ and
ÚNMZ currently publish nothing hydrogen-specific (both checked live,
neither pursued further); MPO has exactly 2 core strategy documents,
added by hand in `data/mpo_hydrogen_strategy_documents.json` (same
`eu_transposition_targets.json` convention — a 2-document yield doesn't
justify a scraper); HYTEP has ~21 real documents on a clean, unblocked
site, which is what this script fetches.

**Unlike `add_eurlex_hydrogen_acts.py`/`add_esbirka_hydrogen_acts.py`,
this source needs no off-topic relevance filter.** Those two screen a
full-text keyword search that inevitably surfaces incidental, unrelated
matches (a chemical compound sharing the word "hydrogen", a customs
tariff schedule). HYTEP's two listing pages
(`/o-vodiku/klicove-dokumenty`, `/o-vodiku/publikace-hytep`) are
themselves a hydrogen-industry association's own curated "key
documents"/"our publications" pages — by construction, everything on
them is already about hydrogen. What this script verifies instead is
existence (does the link still resolve, live, right now) and
uniqueness (is this a new URL, not already in the corpus) — the same
"real URL, independently confirmed" discipline as every other source
added this session, just without a topical relevance question to
answer.

**Two specific documents are deliberately skipped, not just
deduplicated after the fact**: "Vodíková strategie České republiky
(2021)" and "Aktualizace Vodíkové strategie České republiky (2024)"
also appear in HYTEP's listing (as PDF mirrors), but MPO — the actual
approving ministry — hosts the authoritative original, already added
via `data/mpo_hydrogen_strategy_documents.json`. Preferring the
authoritative host over a third-party mirror is the same choice already
made elsewhere in this pipeline (e.g. `eur-lex.europa.eu` over a mirror,
`e-sbirka.gov.cz` as the recorded authoritative reference alongside
`zakonyprolidi.cz`'s content) — cheaper and more precise to skip a known
duplicate at the source than to rely on `deduplicate_db.py`'s semantic
merge to clean it up downstream.

Usage:
    .venv/bin/python src/tools/add_hytep_hydrogen_docs.py

Output: `data/discovered_hytep_hydrogen_docs.json` (loaded by
`build_unified_db.py` as a further source).
"""
import json
import pathlib
import re
import sys
import time

import requests
from bs4 import BeautifulSoup

BASE_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

RAW_DB_PATH = REPO_ROOT / "data" / "database_merged_raw.json"
OUTPUT_PATH = REPO_ROOT / "data" / "discovered_hytep_hydrogen_docs.json"
UNRESOLVED_PATH = REPO_ROOT / "data" / "hytep_unresolved_not_imported.json"

LISTING_PAGES = [
    "https://www.hytep.cz/o-vodiku/klicove-dokumenty",
    "https://www.hytep.cz/o-vodiku/publikace-hytep",
]
USER_AGENT = "Mozilla/5.0 (compatible; NAHYC-DP004-screening-tool/1.0; +research use, low-volume)"
SLEEP_SECONDS = 1
SOURCE_NAME = "HYTEP"

# See module docstring: the authoritative host (MPO) is used instead —
# matched by a distinctive filename fragment, not the full URL, so a
# harmless HYTEP-side rename doesn't silently stop excluding these.
SKIP_URL_FRAGMENTS = ["Vodikova-strategie_CZ_G_2021", "Vodikova-strategie-CR-2024"]

_STRATEGY_RE = re.compile(r"strategi|akčn\w*\s+plán|cestovní mapa|road ?map", re.IGNORECASE)
_STUDY_RE = re.compile(r"studi|katalog|catalogue|report|případová", re.IGNORECASE)
_METHODOLOGY_RE = re.compile(r"instrukce|metodik|methodology|position paper|policy paper|doporučení|recommendations",
                             re.IGNORECASE)
_EU_RE = re.compile(r"\bEU\b|evropsk", re.IGNORECASE)


def extract_document_links(html, base_url):
    """Pulls (title, url) pairs from a HYTEP listing page. Each real
    document has TWO anchor tags sharing the same href — a generic
    "zobrazit [.pdf]" button (no real title) and a second one carrying
    `data-link-type="url"` with the actual, human-written document title
    as its link text — only the second is used. Pure function, no
    network access, unit-testable against a saved fixture."""
    soup = BeautifulSoup(html, "html.parser")
    seen_urls = set()
    links = []
    for a in soup.select('a[data-link-type="url"]'):
        url = (a.get("href") or "").strip()
        title = a.get_text(strip=True)
        if not url or not title or url in seen_urls:
            continue
        seen_urls.add(url)
        links.append({"title": title, "url": url})
    return links


def is_skipped_duplicate(url):
    """True for the two Vodíková strategie ČR mirrors — see module
    docstring for why these are skipped rather than added and later
    deduplicated."""
    return any(fragment in url for fragment in SKIP_URL_FRAGMENTS)


def classify_hytep_document_typ(title):
    """Best-effort categorization for HYTEP's non-binding guidance/
    strategy material — deliberately not `build_unified_db.py:
    classify_law_document_typ()`, which only recognizes binding-act
    vocabulary (Zákon/Vyhláška/EU act types) that none of this content
    uses. Returns "" (falls back to init_db.py's FALLBACK_DOCUMENT_TYPE)
    when genuinely unclear, same "never force-guess" discipline as the
    function it's modeled after. Order matters: a title like
    "Strategická výzkumná agenda" matches both the strategy and study
    patterns — strategy is checked first since "strategická" is the
    title's own primary descriptor."""
    if _STRATEGY_RE.search(title or ""):
        return "Strategický dokument"
    if _METHODOLOGY_RE.search(title or ""):
        return "Metodika"
    if _STUDY_RE.search(title or ""):
        return "Studie"
    return ""


def classify_jurisdikce(title):
    """"EU" for a title naming the EU/Evropská... explicitly, "CZ"
    otherwise — HYTEP is fundamentally a Czech national platform, so
    Czech-scope is the reasonable default for anything not explicitly
    EU-labelled. Best-effort/informational, like the type classifier
    above."""
    return "EU" if _EU_RE.search(title or "") else "CZ"


def load_json(path):
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def build_document_record(title, url):
    """The full Document-shape dict. No formal reference number exists
    for this kind of material (a strategy/study/position paper isn't
    cited like a law or a CELEX act), so `znacka` is deliberately left
    empty — dedup for this source is by exact URL match instead (see
    `main()`), not `znacka`-digit diffing like the EU/CZ-law sources."""
    return {
        "zdroj_dat": SOURCE_NAME,
        "nazev_cz": title,
        "znacka": "",
        "typ_dokumentu": classify_hytep_document_typ(title),
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
            f"Nalezeno v seznamu dokumentů České vodíkové technologické platformy "
            f"(HYTEP, doc/PLAN.md §31), ověřeno živě před doplněním."),
        "jurisdikce": classify_jurisdikce(title),
    }


def main():
    with open(RAW_DB_PATH, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    known_urls = {r.get("odkaz_hlavni", "") for r in raw_data if r.get("odkaz_hlavni")}

    already_added = load_json(OUTPUT_PATH)
    already_added_urls = {r["odkaz_hlavni"] for r in already_added if r.get("odkaz_hlavni")}
    unresolved = load_json(UNRESOLVED_PATH)
    unresolved_urls = {r["url"] for r in unresolved}

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    added, skipped_duplicate_source, skipped_known, skipped_unresolved = [], 0, 0, 0
    all_links = []
    for page_url in LISTING_PAGES:
        resp = session.get(page_url, timeout=30)
        resp.raise_for_status()
        links = extract_document_links(resp.text, page_url)
        print(f"{page_url}: {len(links)} document link(s) found")
        all_links.extend(links)
        time.sleep(SLEEP_SECONDS)

    seen_this_run = set()
    for link in all_links:
        url, title = link["url"], link["title"]
        if url in seen_this_run:
            continue
        seen_this_run.add(url)

        if is_skipped_duplicate(url):
            skipped_duplicate_source += 1
            continue

        if url in known_urls or url in already_added_urls:
            skipped_known += 1
            continue

        try:
            resp = session.head(url, timeout=20, allow_redirects=True)
            if resp.status_code >= 400 or resp.status_code == 405:
                resp = session.get(url, timeout=20, stream=True)
            ok = resp.status_code == 200
        except requests.RequestException:
            ok = False
        time.sleep(SLEEP_SECONDS)

        if not ok:
            if url not in unresolved_urls:
                unresolved.append({"url": url, "title": title, "reason": "did not resolve live (HTTP error)"})
                unresolved_urls.add(url)
            skipped_unresolved += 1
            print(f"[skip] {title[:70]}: no longer resolves live")
            continue

        record = build_document_record(title, url)
        added.append(record)
        already_added_urls.add(url)
        print(f"[add] {record['typ_dokumentu'] or '(?)'}: {title[:70]}")

    save_json(UNRESOLVED_PATH, unresolved)
    all_added = already_added + added
    save_json(OUTPUT_PATH, all_added)

    print(f"\n{len(added)} new record(s) added this run "
          f"({skipped_duplicate_source} skipped as MPO-authoritative duplicates, "
          f"{skipped_known} already in corpus, "
          f"{skipped_unresolved} no longer resolvable live).")
    print(f"{len(all_added)} total in {OUTPUT_PATH.relative_to(REPO_ROOT)}; "
          f"{len(unresolved)} unresolved candidate(s) logged in "
          f"{UNRESOLVED_PATH.relative_to(REPO_ROOT)}.")


if __name__ == "__main__":
    main()
