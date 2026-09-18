"""Populates `nazev_eu`/`odkaz_eu` for national-law records that don't
have them yet, by extracting the EU acts each law itself declares it
transposes — doc/PLAN.md §38, 2026-09-18.

Both jurisdictions have a formal, structural convention for this
declaration (never a guess, always the law's own text):

- **Czech law** (`zakonyprolidi.cz`): Legislativní pravidla vlády, čl.
  55a, reserves footnote **"1)"** specifically (never "1a)", "2)", ...)
  for the "Zákon [v souladu s právem / zapracovává příslušné předpisy]
  Evropské unie<sup>1</sup>)" declaration — that footnote's text lists
  the exact transposed directives/regulations, one per line. Fetched by
  plain HTTP GET (no anti-bot issue, `src/sites/zakonyprolidi.py`
  precedent).
- **Slovak law** (`slov-lex.sk`): a closing paragraph cross-references
  an annex by number ("Týmto zákonom sa preberajú právne záväzné akty
  Európskej únie uvedené v prílohe č. N"), and that annex is headed
  "ZOZNAM PREBERANÝCH PRÁVNE ZÁVÄZNÝCH AKTOV EURÓPSKEJ ÚNIE" followed by
  a numbered list of the transposed acts. slov-lex.sk serves only a bare
  Angular-SPA shell over plain HTTP (confirmed live, doc/PLAN.md §38) —
  needs Playwright/headless Chromium to render the full text, same
  WAF/JS-rendering precedent as `src/sites/iec.py`/`add_missing_iso_
  parents.py`.

Each citation found is INDEPENDENTLY re-verified against the EUR-Lex
Cellar SPARQL endpoint (`sites.eurlex.resolve_eu_act_by_designation()`)
before being trusted — a citation that doesn't resolve there is logged
and skipped, never guessed into a URL that was never confirmed to exist.
A law with no footnote-1/annex cross-reference at all is a legitimate,
common "this law transposes no EU act" outcome, not an extraction
failure — recorded as `status: "no_transposition"` so a rerun doesn't
keep re-fetching it.

Idempotent, same convention as `fetch_authoritative_metadata.py`: writes
to `data/eu_transposition_cache.json`, keyed by the record's own
`odkaz_hlavni` URL, skipping an entry already cached unless `--force`.
Never writes into any `database_*.json` file directly —
`build_unified_db.py`'s `apply_eu_transposition()` reads this cache and
applies it fresh on every run.

Usage:
    .venv/bin/python src/tools/populate_eu_transposition.py [--limit N] [--force]
"""
import argparse
import html as html_module
import json
import pathlib
import re
import sys
import time

import requests

BASE_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from sites.eurlex import USER_AGENT, resolve_eu_act_by_designation  # noqa: E402

DEDUP_PATH = REPO_ROOT / "data" / "database_merged_deduplicated.json"
CACHE_PATH = REPO_ROOT / "data" / "eu_transposition_cache.json"
SLEEP_SECONDS = 1

TARGET_TYPES = {"Zákon", "Vyhláška", "Nařízení vlády"}

# --- target selection -------------------------------------------------------


def is_target_record(item):
    """A national-law-shaped record with neither `nazev_eu` nor
    `odkaz_eu` populated yet."""
    if (item.get("typ_dokumentu") or "").strip() not in TARGET_TYPES:
        return False
    return not (item.get("nazev_eu") or "").strip() and not (item.get("odkaz_eu") or "").strip()


def record_url(item):
    return (item.get("odkaz_hlavni") or "").strip()


# --- citation-type classification -------------------------------------------

_TYPE_KEYWORD_MAP = {
    "směrnice": "Směrnice EU", "smernica": "Směrnice EU",
    "nařízení": "Nařízení EU", "nariadenie": "Nařízení EU",
    "rozhodnutí": "Rozhodnutí EU", "rozhodnutie": "Rozhodnutí EU",
}


def classify_citation_type(text):
    """"Směrnice Evropského..." -> "Směrnice EU"; None if the citation
    doesn't start with one of the three known EU-act-type keywords (in
    either Czech or Slovak)."""
    words = (text or "").strip().split(None, 1)
    if not words:
        return None
    key = words[0].strip(".,;:").lower()
    return _TYPE_KEYWORD_MAP.get(key)


# doc/PLAN.md §38: EU acts adopted before ~2000 are cited with a 2-digit
# year ("Směrnice Rady 85/337/EHS") — but Cellar's ELI always indexes
# them under the full 4-digit year ("eli/dir/1985/337/oj"). Confirmed
# live: `eli_candidates_from_designation()` (deliberately generic, used
# elsewhere for values that are already 4-digit) fails on the bare 2-digit
# form, so it's expanded here, scoped to this module only, before
# resolution is attempted — never elsewhere, since a 2-digit number in
# other contexts (a sequence number, not a year) would be wrongly
# "expanded" if this were done globally. Both digit orderings are cited
# in this corpus's footnotes: "85/337/EHS" (year first, directives) and
# "č. 2119/98/ES" (number first, some EP+Council co-decisions numbered
# like pre-2015 regulations) — both are expanded.
_TWO_DIGIT_YEAR_FIRST_RE = re.compile(r"\b(\d{2})(/\d{1,4}/(?:EHS|ES|EEC|ECSC|Euratom))\b")
_TWO_DIGIT_YEAR_LAST_RE = re.compile(r"\b(\d{3,4})(/)(\d{2})(/(?:EHS|ES|EEC|ECSC|Euratom))\b")


def _is_plausible_year(n):
    return 1957 <= n <= 2035


def expand_two_digit_year(text):
    text = _TWO_DIGIT_YEAR_FIRST_RE.sub(lambda m: f"19{m.group(1)}{m.group(2)}", text or "", count=1)

    def repl(m):
        # Only a "number/2-digit-year" citation (e.g. "č. 2119/98/ES") gets
        # expanded here — a genuine "YYYY/NN/xx" (e.g. "2001/42/ES", year
        # first, NN just a short sequence number) must be left alone. The
        # discriminator: the FIRST group is only ever a 2-digit-YEAR
        # citation's leading number when it's NOT itself a plausible year.
        if _is_plausible_year(int(m.group(1))):
            return m.group(0)
        return f"{m.group(1)}{m.group(2)}19{m.group(3)}{m.group(4)}"

    return _TWO_DIGIT_YEAR_LAST_RE.sub(repl, text, count=1)


# Usually a citation's own designation is the FIRST year/number pair in
# its text — but not always: found live, doc/PLAN.md §38, zakonyprolidi.cz
# /cs/2006-262's "... (třetí samostatná směrnice ve smyslu čl. 16 odst. 1
# směrnice 89/391/EHS) (89/656/EHS)." — the framework directive it cross-
# references (89/391/EHS) comes first in the sentence, and the item's OWN
# designation is a bare, standalone "(YY/NNN/EHS)" parenthetical at the
# very end. That trailing bare-designation shape is distinctive enough to
# prefer deterministically over "first in text" when present.
_TRAILING_BARE_DESIGNATION_RE = re.compile(
    r"\((\d{2,4}/\d{1,4}/(?:EHS|ES|EEC|ECSC|Euratom|EU|EÚ))\)\s*\.?\s*$")


def designation_text_for_resolution(citation_text):
    """The substring to actually resolve against Cellar — normally the
    whole citation text (its own designation is the first digit pair
    `eli_candidates_from_designation()`'s search finds), but the citation
    text ITSELF when a trailing bare designation exists (see above),
    since resolving from the substring alone still lets
    `expand_two_digit_year()`/`eli_candidates_from_designation()` find
    exactly that pair first, ahead of any earlier cross-reference."""
    m = _TRAILING_BARE_DESIGNATION_RE.search(citation_text or "")
    return m.group(1) if m else citation_text


# --- Czech extraction (zakonyprolidi.cz) ------------------------------------

_TAG_RE = re.compile(r"<[^>]+>")
_CZ_FOOTNOTE1_RE = re.compile(
    r'<p class="L1 PPC0">\s*<a[^>]*>\s*<i id="pozn1">\s*</i>\s*</a>\s*'
    r'<var>\s*<sup>1</sup>\)\s*</var>(.*?)</p>',
    re.DOTALL,
)


def _strip_tags(fragment):
    text = _TAG_RE.sub(" ", fragment)
    text = html_module.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


# Some footnotes pack more than one citation into a single <br/>-separated
# line (found live, doc/PLAN.md §38, zakonyprolidi.cz/cs/2006-309: "...
# (pátá samostatná směrnice ...). Směrnice Rady 92/57/EHS ze dne ..." —
# two directives, one <br/>). A capitalized act-type keyword starting a
# fresh sentence (after ". ") is a second citation; the SAME keyword
# lowercase mid-sentence (referring back to "the aforementioned
# směrnice") is not, which is exactly what distinguishes the two here.
_EMBEDDED_CITATION_SPLIT_RE = re.compile(r"(?<=\.)\s+(?=(?:Směrnice|Nařízení|Rozhodnutí)\b)")


def _split_embedded_citations(item_text):
    return [part.strip() for part in _EMBEDDED_CITATION_SPLIT_RE.split(item_text) if part.strip()]


def extract_cz_footnote1_items(page_html):
    """Returns the list of individual EU-act citation strings from
    zakonyprolidi.cz's footnote "1)" (see module docstring) — [] if this
    law has no such footnote (a legitimate "no EU transposition" outcome,
    not an extraction failure)."""
    m = _CZ_FOOTNOTE1_RE.search(page_html or "")
    if not m:
        return []
    lines = [_strip_tags(part) for part in re.split(r"<br\s*/?>", m.group(1))]
    items = []
    for line in lines:
        if line:
            items.extend(_split_embedded_citations(line))
    return items


# --- Slovak extraction (slov-lex.sk, Playwright-rendered) -------------------

_SK_XREF_RE = re.compile(
    r"preber\w*\s+právne\s+záväzné\s+akty\s+Európskej\s+únie\s+uveden\w*\s+v\s+prílohe\s+č\.\s*(\d+)",
    re.IGNORECASE,
)
_SK_ANNEX_ITEM_START_RE = re.compile(r"(?:^|\s)\d{1,2}\.\s+(?=Smernica|Nariadenie|Rozhodnutie)")


def _strip_tags_all(page_html):
    text = _TAG_RE.sub(" ", page_html or "")
    text = html_module.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def extract_sk_annex_items(page_html):
    """Returns the list of individual EU-act citation strings from the
    slov-lex.sk "ZOZNAM PREBERANÝCH PRÁVNE ZÁVÄZNÝCH AKTOV EURÓPSKEJ
    ÚNIE" annex (see module docstring) — [] if this law carries no
    cross-reference to such an annex (a legitimate "no EU transposition"
    outcome, not an extraction failure)."""
    text = _strip_tags_all(page_html)
    xref = _SK_XREF_RE.search(text)
    if not xref:
        return []
    annex_no = xref.group(1)
    heading_re = re.compile(
        rf"Príloha č\.\s*{re.escape(annex_no)}\b.{{0,120}}?"
        r"ZOZNAM PREBERANÝCH PRÁVNE ZÁVÄZNÝCH AKTOV EURÓPSKEJ ÚNIE",
        re.DOTALL,
    )
    heading = heading_re.search(text)
    if not heading:
        return []
    start = heading.end()
    # The annex is followed either by the next annex, or by the
    # footnotes section (headed "Poznámky" immediately followed by its
    # own "1)" marker — found live, doc/PLAN.md §38: without this second
    # boundary, the last annex item ran on into the unrelated footnote
    # text that happens to follow it).
    end_re = re.compile(r"Príloha č\.\s*\d+|Poznámky\s+1\)")
    end_match = end_re.search(text[start:])
    section = text[start:start + end_match.start()] if end_match else text[start:start + 8000]
    starts = [m.start() for m in _SK_ANNEX_ITEM_START_RE.finditer(section)]
    items = []
    for i, pos in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(section)
        item_text = section[pos:end]
        item_text = re.sub(r"^\s*\d{1,2}\.\s+", "", item_text).strip()
        if item_text:
            items.append(item_text)
    return items


# --- fetching ----------------------------------------------------------------


def fetch_cz_page(url, session):
    resp = session.get(url, timeout=20)
    resp.raise_for_status()
    return resp.text


def fetch_sk_page(url, playwright_browser):
    page = playwright_browser.new_page(user_agent=USER_AGENT)
    try:
        page.goto(url, timeout=30000, wait_until="networkidle")
        return page.content()
    finally:
        page.close()


# --- resolution ---------------------------------------------------------------


_ALL_TYPE_NAMES = ("Směrnice EU", "Nařízení EU", "Rozhodnutí EU")

# doc/PLAN.md §38: EU acts of DIFFERENT types are numbered independently
# within the same year, so a "YYYY/NNN" digit pair genuinely can (and,
# found live, does) belong to two completely unrelated acts depending on
# type — "2011/92" is both Directive 2011/92/EU (EIA) and Regulation (EU)
# No 92/2011 (an unrelated cheese-PDO amendment). A type-fallback attempt
# is therefore only ever accepted if the resolved act's own "ze dne ..."
# date matches the citation's own stated date — this is checked for
# EVERY resolution, not just fallbacks, as a general safety net.
_SK_MONTH_TO_CS = {
    "januára": "ledna", "februára": "února", "marca": "března", "apríla": "dubna",
    "mája": "května", "júna": "června", "júla": "července", "augusta": "srpna",
    "septembra": "září", "októbra": "října", "novembra": "listopadu", "decembra": "prosince",
}
_DATE_RE = re.compile(r"\b(\d{1,2})\.\s*([a-záäčďéíľĺňóôŕšťúýž]+)\s*(\d{4})\b", re.IGNORECASE)


def extract_date_signal(text):
    """(day_without_leading_zero, czech_month_name, year) from a citation's
    own "z/ze dne D. <month> YYYY" clause, translating a Slovak month name
    to its Czech equivalent (the resolved title is always Czech-or-English,
    never Slovak) — or None if no such date is found in the text at all."""
    m = _DATE_RE.search(text or "")
    if not m:
        return None
    day, month, year = m.groups()
    return day.lstrip("0") or "0", _SK_MONTH_TO_CS.get(month.lower(), month.lower()), year


def title_matches_date(title, date_signal):
    """True if `date_signal` is None (nothing to check against — never
    blocks a match just because the citation text itself had no
    parseable date) or if that exact day+month+year appears in `title`."""
    if not date_signal:
        return True
    day, month, year = date_signal
    pattern = re.compile(rf"{day}\.\s*{re.escape(month)}\s*{year}", re.IGNORECASE)
    return bool(pattern.search(title or ""))


def resolve_citations(raw_items, session):
    """Re-verifies every raw citation string against EUR-Lex Cellar.
    Returns (resolved, unresolved) — resolved is a list of
    {"title":, "url":} dicts, unresolved is a list of the raw citation
    strings that didn't classify, didn't resolve, or resolved to a
    date-mismatched (see `title_matches_date()`) act — logged, never
    silently dropped.

    Tries the citation's own stated act type first, then falls back to
    the other two: Cellar's ELI path segment doesn't always match the
    act's own title wording — found live, doc/PLAN.md §38, for
    "Regulation (EU) 2021/1187" whose own title literally reads
    "Směrnice Evropského parlamentu a Rady (EU) 2021/1187 ..." in
    Czech, yet only resolves under `eli/reg/...`, not `eli/dir/...`.
    Every candidate (primary or fallback) still needs Cellar to actually
    return a title AND that title's date to match the citation's own —
    never guessed, never accepted on digit-pair coincidence alone."""
    resolved, unresolved = [], []
    for raw in raw_items:
        expanded = expand_two_digit_year(designation_text_for_resolution(raw))
        date_signal = extract_date_signal(raw)
        primary = classify_citation_type(raw)
        candidates = [primary] + [t for t in _ALL_TYPE_NAMES if t != primary] if primary else list(_ALL_TYPE_NAMES)
        act = None
        for type_name in candidates:
            candidate_act = resolve_eu_act_by_designation(expanded, type_name, session=session)
            if candidate_act and title_matches_date(candidate_act["title"], date_signal):
                act = candidate_act
                break
        if act:
            resolved.append(act)
        else:
            unresolved.append(raw)
    return resolved, unresolved


def build_cache_entry(resolved, unresolved, raw_items, domain):
    if not raw_items:
        return {"status": "no_transposition", "domain": domain}
    if not resolved:
        return {"status": "unresolved", "domain": domain, "raw_items": raw_items}
    return {
        "status": "fetched",
        "domain": domain,
        "nazev_eu": "\n".join(a["title"] for a in resolved),
        "odkaz_eu": "\n".join(a["url"] for a in resolved),
        "unresolved_citations": unresolved,
    }


# --- orchestration -------------------------------------------------------------


def load_cache():
    if CACHE_PATH.exists():
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2, sort_keys=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None,
                         help="perform at most N new lookups (for a manual smoke test)")
    parser.add_argument("--force", action="store_true",
                         help="re-fetch even if the cache already has this entry")
    args = parser.parse_args()

    with open(DEDUP_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)

    targets = [r for r in records if is_target_record(r) and record_url(r)]
    cache = load_cache()

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    cz_targets = [r for r in targets if "zakonyprolidi.cz" in record_url(r)]
    sk_targets = [r for r in targets if "slov-lex.sk" in record_url(r)]

    processed = 0

    for r in cz_targets:
        if args.limit is not None and processed >= args.limit:
            break
        url = record_url(r)
        if url in cache and not args.force:
            continue
        print(f"[zakonyprolidi] {r.get('znacka')} -> {url}")
        try:
            page_html = fetch_cz_page(url, session)
        except requests.RequestException as exc:
            print(f"  fetch failed: {exc}")
            cache[url] = {"status": "fetch_failed", "domain": "zakonyprolidi.cz"}
            processed += 1
            continue
        raw_items = extract_cz_footnote1_items(page_html)
        resolved, unresolved = resolve_citations(raw_items, session)
        for u in unresolved:
            print(f"  UNRESOLVED: {u[:100]}")
        cache[url] = build_cache_entry(resolved, unresolved, raw_items, "zakonyprolidi.cz")
        processed += 1
        time.sleep(SLEEP_SECONDS)

    if sk_targets and (args.limit is None or processed < args.limit):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            for r in sk_targets:
                if args.limit is not None and processed >= args.limit:
                    break
                url = record_url(r)
                if url in cache and not args.force:
                    continue
                print(f"[slov-lex] {r.get('znacka')} -> {url}")
                try:
                    page_html = fetch_sk_page(url, browser)
                except Exception as exc:  # noqa: BLE001 - Playwright raises its own exception types
                    print(f"  fetch failed: {exc}")
                    cache[url] = {"status": "fetch_failed", "domain": "slov-lex.sk"}
                    processed += 1
                    continue
                raw_items = extract_sk_annex_items(page_html)
                resolved, unresolved = resolve_citations(raw_items, session)
                for u in unresolved:
                    print(f"  UNRESOLVED: {u[:100]}")
                cache[url] = build_cache_entry(resolved, unresolved, raw_items, "slov-lex.sk")
                processed += 1
            browser.close()

    save_cache(cache)
    fetched = sum(1 for e in cache.values() if e.get("status") == "fetched")
    no_transposition = sum(1 for e in cache.values() if e.get("status") == "no_transposition")
    unresolved_status = sum(1 for e in cache.values() if e.get("status") == "unresolved")
    failed = sum(1 for e in cache.values() if e.get("status") == "fetch_failed")
    print(f"\n{processed} nových záznamů zpracováno. Cache celkem: {len(cache)} "
          f"(fetched={fetched}, no_transposition={no_transposition}, "
          f"unresolved={unresolved_status}, fetch_failed={failed}) -> {CACHE_PATH}")


if __name__ == "__main__":
    main()
