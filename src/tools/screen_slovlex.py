"""Screens the Slovak legislation links already present in
`data/database_merged_raw.json` (`odkaz_sk`) for broken/moved URLs, and
reports them for human review (see `doc/PLAN.md` §4).

**Disclosed limitation, found while building this:** unlike EUR-Lex and
e-Sbírka, Slov-Lex has no confirmed public API or full-text search
endpoint (confirmed 2026-09-09) — its search UI at
`slov-lex.sk/ezbierky-fe/...` is a JS single-page app with no plain-HTTP
fallback for search (only a paid third-party service, LexAPI/LexDATA,
offers programmatic full-text search over it). `static.slov-lex.sk` is a
real, server-rendered fallback, but it's a browse-by-year/number archive,
not searchable by keyword — useless for discovering new documents, and
our own data has no separate Slovak act number field to construct a
per-document URL from for records missing `odkaz_sk` in the first place
(that field only ever appears already paired with a URL, sourced from
`process_laws.py`'s enrichment).

So, unlike `screen_eurlex.py`/`screen_esbirka.py`, this script does
**not** attempt keyword-based discovery of new documents. What it does
instead — the one thing that's both genuinely useful and honestly
achievable here — is check that every `odkaz_sk` link we already have
still resolves, since `slov-lex.sk` is known to redirect/reorganize its
URL structure over time (confirmed: a direct `pravne-predpisy/...` link
now 301-redirects twice before landing).

Usage:
    .venv/bin/python src/tools/screen_slovlex.py

Output: `data/fulltext_screening_candidates.json`, key `"Slov-Lex"` —
only the broken links (not a status dump of every link checked).
"""
import datetime
import json
import pathlib
import time

import requests

BASE_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent
RAW_DB_PATH = REPO_ROOT / "data" / "database_merged_raw.json"
CANDIDATES_PATH = REPO_ROOT / "data" / "fulltext_screening_candidates.json"

SLEEP_SECONDS = 1
USER_AGENT = "Mozilla/5.0 (compatible; NAHYC-DP004-screening-tool/1.0; +research use, low-volume)"


def iter_sk_urls(raw_data):
    """Yields (record, url) for every record with a populated
    `odkaz_sk`. Not restricted to a single `zdroj_dat` — any source could
    in principle carry one, though today only Sinay_Zakony does."""
    for record in raw_data:
        url = (record.get("odkaz_sk") or "").strip()
        if url:
            yield record, url


def check_url(session, url):
    """Follows redirects and reports the final outcome. Never raises —
    a connection failure is just as reportable a "broken" result as an
    HTTP error status."""
    try:
        resp = session.get(url, timeout=15, allow_redirects=True)
        return {
            "ok": resp.status_code < 400,
            "http_status": resp.status_code,
            "final_url": resp.url,
            "error": None,
        }
    except requests.RequestException as exc:
        return {"ok": False, "http_status": None, "final_url": None, "error": str(exc)}


def load_candidates_file():
    if CANDIDATES_PATH.exists():
        with open(CANDIDATES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_candidates_file(data):
    with open(CANDIDATES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)


def main():
    with open(RAW_DB_PATH, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    broken = []
    checked = 0
    for record, url in iter_sk_urls(raw_data):
        if checked > 0:
            time.sleep(SLEEP_SECONDS)
        checked += 1
        result = check_url(session, url)
        if not result["ok"]:
            print(f"BROKEN: [{record.get('zdroj_dat')}] {record.get('znacka')} -> {url} "
                  f"({result['http_status'] or result['error']})")
            broken.append({
                "zdroj_dat": record.get("zdroj_dat", ""),
                "znacka": record.get("znacka", ""),
                "url": url,
                "http_status": result["http_status"],
                "error": result["error"],
                "checked_at": datetime.datetime.now().isoformat(timespec="seconds"),
                "note": "odkaz_sk no longer resolves — needs re-checking against slov-lex.sk",
            })

    candidates_file = load_candidates_file()
    candidates_file["Slov-Lex"] = broken
    save_candidates_file(candidates_file)
    print(f"\nChecked {checked} Slovak link(s), {len(broken)} broken. "
          f"Wrote to {CANDIDATES_PATH.relative_to(REPO_ROOT)} under key \"Slov-Lex\".")


if __name__ == "__main__":
    main()
