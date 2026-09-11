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
- **`Prokop_Normy`'s ČSN-designated norm records** ("ČSN ..." znacka):
  looked up against the existing `check_csn_validity.py` registry
  (`csnonline.agentura-cas.cz` — free, not anti-bot-walled, unlike
  `technicke-normy-csn.cz`, which this script never touches) for the
  matching designation's own title.

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
from check_csn_validity import search as csn_search, USER_AGENT as CSN_USER_AGENT  # noqa: E402
from init_db import resolve_file_path, load_fulltext_manifest  # noqa: E402

RAW_DB_PATH = REPO_ROOT / "data" / "database_merged_raw.json"
CACHE_PATH = REPO_ROOT / "data" / "site_metadata_cache.json"

SLEEP_SECONDS = 1
USER_AGENT = "Mozilla/5.0 (compatible; NAHYC-DP004-sites-tool/1.0; +research use, low-volume)"

LAW_SOURCES = {"Haltuf_Dokumenty", "Sinay_Zakony", "EU_Transposition_Targets", "V02_Bibliografie"}
_CSN_PREFIX_RE = re.compile(r"^(ČSN|CSN)\s+", re.IGNORECASE)
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
    return "Prokop_Normy" in _sources(item) and bool(_CSN_PREFIX_RE.match((item.get("znacka") or "").strip()))


def csn_core(znacka):
    """"ČSN ISO 14687" -> "ISO 14687" — check_csn_validity.py's search()
    expects the base designation, not the ČSN-prefixed form (see its own
    usage docstring)."""
    return _CSN_PREFIX_RE.sub("", (znacka or "").strip())


def _normalize_designation(text):
    return re.sub(r"\s+", " ", (text or "").strip()).lower()


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
    """Searches csnonline.agentura-cas.cz for this ČSN designation's own
    core number and returns {"title": ...} only for the result whose
    designation matches THIS record's znacka exactly (normalized) — never
    guesses from a partial/ambiguous match. None if no exact match."""
    query = csn_core(znacka)
    if not query:
        return None
    try:
        results = csn_search(session, query)
    except requests.RequestException:
        return None
    target = _normalize_designation(znacka)
    for r in results:
        if _normalize_designation(r.get("designation", "")) == target and r.get("title"):
            return {"title": r["title"], "description": None}
    return None


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
            if url in cache and not args.force:
                continue
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
            if key in cache and not args.force:
                continue
            print(f"[csnonline] {znacka}")
            result = fetch_csn_metadata(znacka, csn_session)
            cache[key] = {
                "title": result["title"] if result else None,
                "description": None,
                "domain": "csnonline.agentura-cas.cz",
                "znacka": znacka,
                "zdroj_esbirka_url": None,
                "status": "fetched" if result else "failed",
            }
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
