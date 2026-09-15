"""Fetches full text for law records that already carry a real per-document
URL (`odkaz_hlavni`/`odkaz_eu`/`odkaz_sk` in `data/database_merged_raw.json`)
and caches it locally under `data/fulltext/` (git-ignored — see
`doc/PLAN.md` §4).

**Only laws are in scope.** Records classified as `typ_dokumentu ==
"Norma"` (technical norms — ČSN/STN/EN/ISO/DIN) are skipped
unconditionally: their URLs are generic catalog roots, not per-document
links, and the actual standard text is copyrighted/paywalled (confirmed
via the ČSN registry's own Terms of Use — see `check_csn_validity.py`'s
docstring). This script must never be extended to fetch norm text.
Source-agnostic since doc/PLAN.md §15 (2026-09-15) — gated on the
record's own classified type, not which spreadsheet it came from.
`is_norm_designation()` adds a second, independent guard (2026-09-11,
doc/REQUIREMENTS.md R4.1): a law record can still carry a handful of
stray norm citations of its own, which the `typ_dokumentu` check alone
would miss.

Idempotent: `data/fulltext_manifest.json` (git-tracked — small metadata,
no document content) records one entry per (source, znacka, URL field).
A record already `fetched` with its local file present is skipped on
rerun unless `--force` is passed.

Usage:
    .venv/bin/python src/tools/fetch_fulltext.py [--limit N] [--force]
"""
import argparse
import datetime
import hashlib
import json
import pathlib
import re
import time

import requests

BASE_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent
RAW_DB_PATH = REPO_ROOT / "data" / "database_merged_raw.json"
FULLTEXT_DIR = REPO_ROOT / "data" / "fulltext"
MANIFEST_PATH = REPO_ROOT / "data" / "fulltext_manifest.json"

URL_FIELDS = ("odkaz_hlavni", "odkaz_eu", "odkaz_sk")

# doc/REQUIREMENTS.md R4.1, 2026-09-11: a typ_dokumentu != "Norma" check
# alone is not a reliable guard — found in practice that some law records
# (e.g. from Haltuf_Dokumenty) also carry a handful of stray norm
# citations of their own (e.g. "ISO 14687", "ČSN EN 17127",
# "DIN EN ISO 22734"), each already fetched before this fix (harmless in
# practice — the URLs were public catalog/e-shop listing pages, not paid
# full text, but still the wrong shape of content to treat as this
# pipeline's cached "full text"). A record's own designation shape is an
# independent second check — same precedent as
# link_document_relations_auto.py's is_eu_act_znacka().
_NORM_DESIGNATION_RE = re.compile(
    r"^(?:ČSN|CSN|STN|TNI|DIN|VDE|NF|BS|NEN|ISO|IEC|EN)\b", re.IGNORECASE
)

SLEEP_SECONDS = 1
USER_AGENT = "Mozilla/5.0 (compatible; NAHYC-DP004-fulltext-tool/1.0; +research use, low-volume)"


def sanitize_znacka(znacka):
    """Turns a znacka into a filesystem-safe filename fragment. Not meant
    to be reversible — the manifest, not the filename, is the source of
    truth for which record a file belongs to."""
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", znacka.strip())
    return safe.strip("_") or "unnamed"


def is_fetchable_source(typ_dokumentu):
    return typ_dokumentu != "Norma"


def is_norm_designation(znacka):
    """True when the designation itself is shaped like a technical
    standard (ČSN/STN/DIN/ISO/EN/... prefix) regardless of the record's
    typ_dokumentu — see the R4.1 note above."""
    return bool(_NORM_DESIGNATION_RE.match((znacka or "").strip()))


def manifest_key(zdroj_dat, znacka, url_field):
    return f"{zdroj_dat}|{znacka}|{url_field}"


def first_url(raw_value):
    """Some Haltuf odkaz_* cells hold two URLs joined by an embedded
    newline (an Excel line-break artifact, e.g. the EUR-Lex PDF link
    followed by an unrelated informational page) — only the first is a
    real, fetchable document link; sending the whole blob 404s. Splits
    on any whitespace and returns the first token, or "" for blank/None."""
    parts = (raw_value or "").split()
    return parts[0] if parts else ""


def iter_fetch_targets(raw_data):
    """Yields (record, url_field, url) for every law record with a
    non-empty znacka and a populated URL field. Records with no znacka
    (a small, disclosed residual — see doc/PLAN.md Step 1) are skipped:
    there's no stable key to file them under."""
    for record in raw_data:
        if not is_fetchable_source(record.get("typ_dokumentu", "")):
            continue
        znacka = (record.get("znacka") or "").strip()
        if not znacka or is_norm_designation(znacka):
            continue
        for url_field in URL_FIELDS:
            url = first_url(record.get(url_field))
            if url:
                yield record, url_field, url


def extension_from_url(url, content_type=None):
    m = re.search(r"\.(pdf|html?|xml)(?:[?#]|$)", url, re.IGNORECASE)
    if m:
        ext = m.group(1).lower()
        return "html" if ext == "htm" else ext
    if content_type:
        if "pdf" in content_type:
            return "pdf"
        if "html" in content_type:
            return "html"
        if "xml" in content_type:
            return "xml"
    return "bin"


def load_manifest():
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_manifest(manifest):
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2, sort_keys=True)


def already_fetched(manifest, key):
    entry = manifest.get(key)
    if not entry or entry.get("status") != "fetched":
        return False
    local_path = entry.get("local_path")
    return bool(local_path) and (REPO_ROOT / local_path).exists()


def fetch_one(session, record, url_field, url):
    """Performs the actual HTTP GET and returns a manifest entry dict.
    Never raises — network/HTTP failures are recorded as a `failed`
    status so one bad URL doesn't abort the whole run."""
    zdroj_dat = record["zdroj_dat"]
    znacka = record["znacka"].strip()
    now = datetime.datetime.now().isoformat(timespec="seconds")
    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as exc:
        return {
            "status": "failed",
            "url": url,
            "http_status": getattr(exc.response, "status_code", None),
            "error": str(exc),
            "fetched_at": now,
        }

    ext = extension_from_url(url, resp.headers.get("Content-Type", ""))
    out_dir = FULLTEXT_DIR / zdroj_dat
    out_dir.mkdir(parents=True, exist_ok=True)
    local_path = out_dir / f"{sanitize_znacka(znacka)}__{url_field}.{ext}"
    local_path.write_bytes(resp.content)

    return {
        "status": "fetched",
        "url": url,
        "local_path": str(local_path.relative_to(REPO_ROOT)),
        "http_status": resp.status_code,
        "sha256": hashlib.sha256(resp.content).hexdigest(),
        "fetched_at": now,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None,
                         help="fetch at most N documents (for a manual smoke test)")
    parser.add_argument("--force", action="store_true",
                         help="re-fetch even if the manifest already has this entry")
    args = parser.parse_args()

    with open(RAW_DB_PATH, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    manifest = load_manifest()
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    fetched_count = 0
    for record, url_field, url in iter_fetch_targets(raw_data):
        key = manifest_key(record["zdroj_dat"], record["znacka"].strip(), url_field)
        if not args.force and already_fetched(manifest, key):
            continue
        if args.limit is not None and fetched_count >= args.limit:
            break

        if fetched_count > 0:
            time.sleep(SLEEP_SECONDS)
        print(f"[{record['zdroj_dat']}] {record['znacka']} ({url_field}) -> {url}")
        manifest[key] = fetch_one(session, record, url_field, url)
        print(f"  {manifest[key]['status']}")
        fetched_count += 1
        save_manifest(manifest)

    print(f"\nDone. {fetched_count} URLs fetched this run. "
          f"Manifest: {MANIFEST_PATH.relative_to(REPO_ROOT)} ({len(manifest)} entries total).")


if __name__ == "__main__":
    main()
