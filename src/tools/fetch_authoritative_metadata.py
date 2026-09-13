"""Fetches each record's authoritative title/description directly from
its own "single point of authority" website — doc/PLAN.md §8, 2026-09-11.

Scope, deliberately narrow (see doc/PLAN.md §8's feasibility research):
only the domains this corpus actually cites with a genuine PER-DOCUMENT
URL, not the ~650+ norm records whose stored URL is just a generic
organization homepage/catalog root (no per-document parser can help
those — the URL itself doesn't identify which document it's for).

- **Law records** (`Haltuf_Dokumenty`/`Sinay_Zakony`/`EU_Transposition_
  Targets`/`V02_Bibliografie`) whose URL is on `eur-lex.europa.eu`
  (`src/sites/eurlex.py`, SPARQL — title only, no description available),
  `zakonyprolidi.cz` (`src/sites/zakonyprolidi.py`, HTML meta tags — title
  + description), or `slov-lex.sk` (`src/sites/slovlex.py`, JSON-LD —
  title only). Every Czech law ("NNN/YYYY Sb." shape) additionally gets
  its citation verified against `src/sites/esbirka.py` — e-Sbírka is the
  real government source of record, but doesn't expose a scrapeable title
  itself (see that module's own docstring), so it only contributes a
  confirmed `zdroj_esbirka_url` reference alongside zakonyprolidi.cz's
  actual title/description text.
- **ČSN-designated norm records** (`Prokop_Normy`/`Haltuf_Dokumenty`/
  `Sinay_Normy`, whether the corpus's own `znacka` already carries a
  `ČSN`/`CSN` prefix or is a bare `EN`/`ISO`/`IEC` designation): looked up
  against `agentura-cas.cz` (Česká agentura pro standardizaci, the actual
  national standards body — `check_csn_validity.py`'s `csnonline.
  agentura-cas.cz` search + `Detailnormy.aspx` detail page), the single
  point of authority for Czech national standards — doc/PLAN.md §9,
  2026-09-13. `technicke-normy-csn.cz` (an independent third-party
  mirror the corpus happens to cite for some norms) is never touched
  directly, still confirmed anti-bot-walled.
  - For an already-`ČSN`-prefixed `znacka`: resolves this record's own
    title (as before), now via `check_csn_validity.find_best_match()`
    (handles catalog-number-suffix/edition-marker formatting mismatches
    and a stale-first-edition tie-break) and records the real
    `Detailnormy.aspx` URL as provenance (previously fell back to the
    record's own, often third-party, URL).
  - For a **bare** `EN`/`ISO`/`IEC` `znacka` (no national prefix at all —
    this record's own identity IS the international original): if
    `agentura-cas.cz` confirms a Czech national adoption exists, this
    record's `nazev_autoritativni` becomes the adoption's own **English**
    title (`Anglický název` — "refers to the original", not a Czech
    label for an international standard) and its `jurisdikce` is
    corrected to `mezinárodní` (`jurisdikce_autoritativni` — see
    `build_unified_db.py`). If **no** existing raw record anywhere in
    the corpus already carries the confirmed ČSN designation, a
    `synthesize` block is written so `build_unified_db.py` can add that
    Czech-adoption record itself, with a reference back to the original
    designation/year (`Zapracované dokumenty` on the detail page) —
    doc/REQUIREMENTS.md's existing `ADOPTS` relation type/
    `link_document_relations_auto.py` mechanism then links the two
    automatically, with no changes needed there.

Idempotent (same convention as `fetch_fulltext.py`): writes to
`data/site_metadata_cache.json`, keyed by URL (or `csn:<znacka>` for ČSN
lookups, which have no per-document URL of their own to key on), skipping
an entry already cached unless `--force`. Never writes into any
`database_*.json` file directly — `build_unified_db.py` reads this cache
and applies it fresh on every run (see doc/PLAN.md §8 for why that
matters: a downstream patch would be silently discarded on rebuild).

Usage:
    .venv/bin/python src/tools/fetch_authoritative_metadata.py [--limit N] [--force]
"""
import argparse
import json
import pathlib
import re
import sys
import time

import requests

BASE_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(BASE_DIR))

from sites import eurlex, zakonyprolidi, slovlex, esbirka  # noqa: E402
from check_csn_validity import (  # noqa: E402
    search as csn_search,
    find_best_match as csn_find_best_match,
    fetch_detail as csn_fetch_detail,
    strip_catalog_suffix as csn_strip_catalog_suffix,
    USER_AGENT as CSN_USER_AGENT,
)
from init_db import resolve_file_path, load_fulltext_manifest  # noqa: E402

RAW_DB_PATH = REPO_ROOT / "data" / "database_merged_raw.json"
CACHE_PATH = REPO_ROOT / "data" / "site_metadata_cache.json"

SLEEP_SECONDS = 1
USER_AGENT = "Mozilla/5.0 (compatible; NAHYC-DP004-sites-tool/1.0; +research use, low-volume)"

LAW_SOURCES = {"Haltuf_Dokumenty", "Sinay_Zakony", "EU_Transposition_Targets", "V02_Bibliografie"}
# doc/PLAN.md §9: sources whose znacka may cite a Czech-adoptable norm —
# widened from Prokop_Normy-only so a bare EN/ISO/IEC designation found
# only in Haltuf_Dokumenty/Sinay_Normy (e.g. "EN 17339") is attempted too.
CSN_ELIGIBLE_SOURCES = {"Prokop_Normy", "Haltuf_Dokumenty", "Sinay_Normy"}
_CSN_PREFIX_RE = re.compile(r"^(ČSN|CSN)\s+", re.IGNORECASE)
# A bare designation with no national-body prefix at all is the
# international original itself (mirrors link_document_relations_auto.py's
# own national-prefix exclusion logic).
_INTL_DESIGNATION_RE = re.compile(r"^(EN|ISO|IEC)\b", re.IGNORECASE)
# Corpus data-quality workaround (doc/PLAN.md §9): some corpus znacka
# carry a spurious "EN" before "ISO"/"IEC" that the real ČSN designation
# doesn't have (confirmed live for "ČSN EN ISO 19880-1"/"ČSN EN ISO
# 14687" -> real designation is "ČSN ISO ..."). Only ever used as a
# fallback retry, never the first attempt, and only accepted if it
# yields an unambiguous match.
_EN_ISO_IEC_RE = re.compile(r"^EN\s+(ISO|IEC)\b", re.IGNORECASE)
# Same three-way jurisdikce split as build_unified_db.py's
# resolve_prokop_jurisdikce() (duplicated per that module's own stated
# convention — each consumer keeps its own copy rather than cross-import
# between independent pipeline stages): bare ISO/IEC is "mezinárodní",
# bare EN (with or without a following ISO/IEC) is "EU".
_BARE_ISO_IEC_RE = re.compile(r"^(?:ISO|IEC)(?:/[A-Z]+)?\s+\d", re.IGNORECASE)
_SITE_MODULES = {
    "eur-lex.europa.eu": eurlex,
    "zakonyprolidi.cz": zakonyprolidi,
    "slov-lex.sk": slovlex,
}


def _sources(item):
    return [s.strip() for s in (item.get("zdroj_dat") or "").split(", ") if s.strip()]


def is_law_record(item):
    return any(s in LAW_SOURCES for s in _sources(item))


def is_csn_norm_record(item):
    znacka = (item.get("znacka") or "").strip()
    if not any(s in CSN_ELIGIBLE_SOURCES for s in _sources(item)):
        return False
    if _CSN_PREFIX_RE.match(znacka):
        return True
    return bool(_INTL_DESIGNATION_RE.match(znacka))


def is_bare_international_znacka(znacka):
    znacka = (znacka or "").strip()
    return bool(_INTL_DESIGNATION_RE.match(znacka)) and not _CSN_PREFIX_RE.match(znacka)


def bare_jurisdikce_tier(znacka):
    """"mezinárodní" for a bare ISO/IEC designation, "EU" for a bare EN
    one (with or without a following ISO/IEC) — only meaningful when
    `is_bare_international_znacka()` is already true."""
    return "mezinárodní" if _BARE_ISO_IEC_RE.match((znacka or "").strip()) else "EU"


def csn_core(znacka):
    """"ČSN ISO 14687" -> "ISO 14687" — check_csn_validity.py's search()
    expects the base designation, not the ČSN-prefixed form (see its own
    usage docstring). A no-op for an already-bare designation."""
    return _CSN_PREFIX_RE.sub("", (znacka or "").strip())


def record_url(item):
    """Same precedence as init_db.py's own `url` field: odkaz_hlavni ->
    odkaz_eu -> odkaz_sk, first non-empty wins."""
    for field in ("odkaz_hlavni", "odkaz_eu", "odkaz_sk"):
        url = (item.get(field) or "").strip()
        if url:
            return url
    return ""


def dispatch_site_module(url):
    for domain, module in _SITE_MODULES.items():
        if domain in url:
            return module
    return None


def load_cache():
    if CACHE_PATH.exists():
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2, sort_keys=True)


def fetch_csn_metadata(znacka, session):
    """Searches agentura-cas.cz (csnonline) for this ČSN designation and
    returns the best match (see check_csn_validity.find_best_match() for
    the formatting-tolerant matching rules — never guesses across a
    genuinely different designation) plus its Detailnormy.aspx detail
    page. Also tries the corpus's own spurious-"EN" quirk as a last-resort
    fallback (see module docstring) — this corpus-data-quality bug shows
    up on BOTH bare ("EN ISO 19880-1") and already-ČSN-prefixed ("ČSN EN
    ISO 19880-1") znacka, so the fallback isn't restricted to the bare
    case; only the "record's own title should switch to English" logic
    (see main()) is. Returns None if nothing resolves.

    Return shape: {"title", "description", "zdroj_autoritativni_url",
    "incorporates", "csn_designation", "title_en"} — "title_en"/
    "incorporates" are only meaningful for a bare-znacka lookup."""
    znacka = (znacka or "").strip()
    bare = is_bare_international_znacka(znacka)
    query = csn_strip_catalog_suffix(csn_core(znacka))
    if not query:
        return None
    match_target = znacka if not bare else f"ČSN {query}"
    try:
        results = csn_search(session, query)
    except requests.RequestException:
        return None
    best = csn_find_best_match(results, match_target)

    if best is None and _EN_ISO_IEC_RE.match(query):
        stripped_query = _EN_ISO_IEC_RE.sub(lambda m: m.group(1), query)
        try:
            results2 = csn_search(session, stripped_query)
        except requests.RequestException:
            results2 = []
        best = csn_find_best_match(results2, f"ČSN {stripped_query}")

    if best is None:
        return None

    detail = None
    if best.get("catalog_number"):
        detail = csn_fetch_detail(best["catalog_number"], session)

    return {
        "title": best["title"],
        "description": None,
        "zdroj_autoritativni_url": (detail or {}).get("url"),
        "incorporates": (detail or {}).get("incorporates") or [],
        "csn_designation": best.get("designation"),
        "title_en": (detail or {}).get("title_en") if bare else None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None,
                         help="perform at most N new lookups (for a manual smoke test)")
    parser.add_argument("--force", action="store_true",
                         help="re-fetch even if the cache already has this entry")
    args = parser.parse_args()

    with open(RAW_DB_PATH, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    manifest = load_fulltext_manifest()
    cache = load_cache()
    # Several raw records (duplicate rows across a source's own repeated
    # citations) can share the exact same cache key (a URL, or "csn:
    # <znacka>") — with --force, re-processing the same key more than
    # once in a single run doesn't just waste a request, it can silently
    # clobber a `synthesize` block a PRIOR iteration for this same key
    # just wrote (found live, doc/PLAN.md §9): once the first hit adds
    # the confirmed ČSN designation to `existing_znacka`, a later
    # duplicate for the same key sees it as "already exists" and writes
    # a synthesize-less entry over the first one. Each unique key is
    # therefore handled at most once per invocation, regardless of
    # --force (which still means "ignore what's on disk from a PREVIOUS
    # run", not "reprocess a key already handled this run").
    processed_keys = set()

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    csn_session = requests.Session()
    csn_session.headers.update({"User-Agent": CSN_USER_AGENT})

    processed = 0
    for item in raw_data:
        if args.limit is not None and processed >= args.limit:
            break

        znacka = (item.get("znacka") or "").strip()
        url = record_url(item)
        module = dispatch_site_module(url) if url else None

        if is_law_record(item) and module is not None:
            if url in processed_keys:
                continue
            if url in cache and not args.force:
                continue
            processed_keys.add(url)
            cached_path = resolve_file_path(item, manifest)
            local_path = str(REPO_ROOT / cached_path) if cached_path else None
            print(f"[{module.__name__.rsplit('.', 1)[-1]}] {znacka} -> {url}")
            result = module.extract(url, cached_path=local_path, session=session)
            esbirka_url = esbirka.verify(znacka, session=session)
            cache[url] = {
                "title": result["title"] if result else None,
                "description": (result or {}).get("description"),
                "domain": module.__name__.rsplit(".", 1)[-1],
                "znacka": znacka,
                "zdroj_esbirka_url": esbirka_url,
                "status": "fetched" if result else "failed",
            }
            processed += 1
            if not local_path:
                time.sleep(SLEEP_SECONDS)
            continue

        if is_csn_norm_record(item):
            key = f"csn:{znacka}"
            if key in processed_keys:
                continue
            if key in cache and not args.force:
                continue
            processed_keys.add(key)
            print(f"[csnonline] {znacka}")
            result = fetch_csn_metadata(znacka, csn_session)
            entry = {
                "title": None,
                "description": None,
                "domain": "csnonline.agentura-cas.cz",
                "znacka": znacka,
                "zdroj_esbirka_url": None,
                "zdroj_autoritativni_url": None,
                "status": "failed",
            }
            if result:
                bare = is_bare_international_znacka(znacka)
                entry.update({
                    "status": "fetched",
                    "zdroj_autoritativni_url": result.get("zdroj_autoritativni_url"),
                })
                if bare:
                    # This record's own znacka IS the international
                    # original — its title stays in English, and its
                    # jurisdikce is corrected accordingly (doc/PLAN.md §9).
                    entry["title"] = result.get("title_en")
                    entry["jurisdikce_autoritativni"] = bare_jurisdikce_tier(znacka)
                    csn_designation = result.get("csn_designation")
                    if csn_designation:
                        # Always propose the synthesize block — whether
                        # it actually needs to add anything is decided
                        # solely by build_unified_db.py's own
                        # synthesize_csn_adoption_records(), checked
                        # against the FRESH unified_db it just built from
                        # the 6 real sources on every single run (doc/
                        # PLAN.md §9 follow-up: checking against THIS
                        # script's own raw_data snapshot was circular and
                        # fragile — database_merged_raw.json is rebuilt
                        # from scratch every run and never natively
                        # contains a synthesized record on its own, so a
                        # "already present" check here would silently
                        # stop proposing it after the very first
                        # successful synthesis, and a later from-scratch
                        # rebuild would then lose the record for good).
                        entry["synthesize"] = {
                            "zdroj_dat": "CSN_Adoption_AgenturaCAS",
                            "znacka": csn_designation,
                            "typ_dokumentu": "Norma",
                            "nazev_cz": result["title"],
                            "jurisdikce": "CZ",
                            "odkaz_hlavni": result.get("zdroj_autoritativni_url") or "",
                            "nazev_autoritativni": result["title"],
                            "zdroj_autoritativni_url": result.get("zdroj_autoritativni_url"),
                        }
                else:
                    entry["title"] = result.get("title")
            cache[key] = entry
            processed += 1
            time.sleep(SLEEP_SECONDS)
            continue

    save_cache(cache)
    fetched = sum(1 for v in cache.values() if v.get("status") == "fetched")
    print(f"\nDone. {processed} new lookup(s) this run. "
          f"{fetched}/{len(cache)} cache entries carry a real title -> "
          f"{CACHE_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
