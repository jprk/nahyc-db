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

Layout (2026-10-25): every file goes straight into `data/fulltext/`, named
`<designation>__<8 hex digits of its SHA-256>.<ext>` (`flat_name()`); the
spreadsheet a record came from is not part of the path. Files downloaded
before that were moved by `migrate_fulltext_layout.py`.

Idempotent: `data/fulltext_manifest.json` (git-tracked — small metadata,
no document content) records one entry per (source, znacka, URL field).
A record already `fetched` with its local file present is skipped on
rerun unless `--force` is passed.

Usage:
    .venv/bin/python src/tools/fetch_fulltext.py [--limit N] [--force]
    .venv/bin/python src/tools/fetch_fulltext.py --audit [--apply]
    .venv/bin/python src/tools/fetch_fulltext.py --only "Sinay_Zakony|56/2001 Sb.|odkaz_eu"
    .venv/bin/python src/tools/fetch_fulltext.py --host slov-lex.sk
"""
import argparse
import datetime
import hashlib
import json
import pathlib
import re
import time

import requests

import language_variants
from fulltext_keys import first_url, url_designation  # noqa: F401 (first_url is part of this module's API)

BASE_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent
RAW_DB_PATH = REPO_ROOT / "data" / "database_merged_raw.json"
FULLTEXT_DIR = REPO_ROOT / "data" / "fulltext"
MANIFEST_PATH = REPO_ROOT / "data" / "fulltext_manifest.json"
URL_OVERRIDES_PATH = REPO_ROOT / "data" / "fulltext_url_overrides.json"

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


def flat_name(znacka, sha256, ext):
    """File name of a downloaded document inside `data/fulltext/` — one flat
    directory, not one folder per spreadsheet that happened to list it. The
    designation keeps the name readable; the first 8 hex digits of the
    content hash keep two different documents (or two versions of one) from
    ever sharing a name, and make the same content downloaded twice — e.g.
    from `odkaz_hlavni` and `odkaz_eu` — one file."""
    return f"{sanitize_znacka(znacka)}__{sha256[:8]}.{ext}"


def is_fetchable_source(typ_dokumentu):
    return typ_dokumentu != "Norma"


def is_norm_designation(znacka):
    """True when the designation itself is shaped like a technical
    standard (ČSN/STN/DIN/ISO/EN/... prefix) regardless of the record's
    typ_dokumentu — see the R4.1 note above."""
    return bool(_NORM_DESIGNATION_RE.match((znacka or "").strip()))


def manifest_key(zdroj_dat, znacka, url_field):
    return f"{zdroj_dat}|{znacka}|{url_field}"


def load_url_overrides(path=URL_OVERRIDES_PATH):
    """`{manifest key: {"url": ..., "reason": ...}}` — corrections of a URL
    that the source spreadsheet gets wrong (a wrong act type in an ELI, a
    number that does not exist). Kept next to the data instead of editing the
    raw spreadsheets' output: the correction and the reason stay visible and
    survive a rebuild of `database_merged_raw.json`."""
    path = pathlib.Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


# `TXT/PDF/?uri=CELEX:...` or `...?uri=OJ:L_<year><number>` (the Official Journal's
# own id), optionally with the `&qid=...` the EUR-Lex site appends to a copied link.
# Not `OJ:L:2014:096:FULL`: that PDF is a whole issue of the Journal, not one act.
_EURLEX_PDF = re.compile(r"^(https://eur-lex\.europa\.eu/legal-content/[A-Z]{2}/TXT/)PDF"
                         r"(/\?uri=(?:CELEX:[0-9A-Za-z()_\-]+|OJ:L_[0-9]+))(?:&[^#]*)?$")
HTML_SUFFIX = "_html"


def html_alternative(url):
    """The HTML page of the same EUR-Lex document as a `TXT/PDF` address, or
    None. The PDF stays the document's downloadable original; the HTML has the
    structure (articles, paragraphs, lists) that a PDF's page layout does not,
    so the readable text is made from it — see extract_fulltext.py."""
    m = _EURLEX_PDF.match(url or "")
    return f"{m.group(1)}HTML{m.group(2)}" if m else None


# EUR-Lex serves an act in every official language; which one an address gives
# is part of the address. An ELI without a language (`.../oj`) gives English, and
# its `?lang=CS` is ignored; `.../oj/ces` gives Czech. `legal-content` addresses
# carry the language as their second path segment (`/legal-content/CS/TXT/...`).
ELI_LANGUAGE = {"CS": "ces", "SK": "slk", "EN": "eng", "DE": "deu"}
_ELI = re.compile(r"^(https://eur-lex\.europa\.eu/eli/[a-z_]+/\d{4}/\d+/oj)(?:/[a-z]{3})?(?:\?[^#]*)?$")
_LEGAL_CONTENT = re.compile(r"^(https://eur-lex\.europa\.eu/legal-content/)([A-Z]{2})(/.*)$")


def localized_url(url, language):
    """`url` in the document's own language where EUR-Lex lets the address say
    so, else `url` unchanged. `language` is a Document.language code.

    Only an *English* address is changed — an ELI without a language, or a
    `/legal-content/EN/` one — and only for a document that is not English
    (CS, SK, DE): that is the defect this fixes (an act labelled Czech stored
    in English). An address that already names another language is left alone,
    and so is everything for an English or unknown language: a guess must not
    decide which language a document is stored in."""
    if not url or language not in ELI_LANGUAGE or language == "EN":
        return url
    m = _ELI.match(url)
    if m:
        explicit = re.search(r"/oj/([a-z]{3})(?:\?|$)", url)
        return url if explicit and explicit.group(1) != "eng" else f"{m.group(1)}/{ELI_LANGUAGE[language]}"
    m = _LEGAL_CONTENT.match(url)
    if m and m.group(2) == "EN":
        return f"{m.group(1)}{language}{m.group(3)}"
    return url


def record_language(record):
    """The language the pipeline will give this record (init_db's cascade: the
    source domain, a raw `jazyk`, else detection on the title), or None when the
    result is only a guess."""
    from language import detect_language, normalize_raw_language, resolve_domain_language_override
    language = resolve_domain_language_override(record.get("odkaz_hlavni") or record.get("odkaz_eu") or "")
    if language is None:
        language = normalize_raw_language(record.get("jazyk", ""))
    if language is not None:
        return language
    title = record.get("nazev_cz") or record.get("nazev") or ""
    language, confident = detect_language(title, record.get("anotace_poznamka"))
    return language if confident else None


def iter_fetch_targets(raw_data, overrides=None):
    """Yields (record, url_field, url) for every law record with a
    non-empty znacka and a populated URL field. Records with no znacka
    (a small, disclosed residual — see doc/PLAN.md Step 1) are skipped:
    there's no stable key to file them under. A URL listed in `overrides`
    (see load_url_overrides) replaces the one from the record. The English row
    of an act that also has a Czech row is yielded under the designation
    `<znacka> [EN]` (language_variants.py). An EUR-Lex PDF
    address is followed by the address of the same document as HTML
    (`html_alternative`) under the field `<field>_html`."""
    overrides = overrides or {}
    pairs = language_variants.variant_pairs(raw_data)
    for raw_record in raw_data:
        if not is_fetchable_source(raw_record.get("typ_dokumentu", "")):
            continue
        znacka = (raw_record.get("znacka") or "").strip()
        if is_norm_designation(znacka):
            continue
        # the English row of an act that also has a Czech one is a document of its own
        variant = language_variants.variant_designation(raw_record, pairs)
        for url_field in URL_FIELDS:
            url = first_url(raw_record.get(url_field))
            # no znacka: the document is filed under a designation made of this address
            znacka = variant or (url_designation(url) if url else "")
            record = {**raw_record, "znacka": znacka}
            if url:
                override = overrides.get(manifest_key(record["zdroj_dat"], znacka, url_field))
                if override:  # an explicit address wins, language included
                    url = override["url"]
                else:
                    url = localized_url(url, record_language(record))
                yield record, url_field, url
                alternative = html_alternative(url)
                twin = overrides.get(manifest_key(record["zdroj_dat"], znacka, url_field + HTML_SUFFIX))
                if twin:  # e.g. the PDF is a whole Official Journal issue: name the act's own page
                    alternative = twin["url"]
                if alternative:  # a second manifest entry, key field "<field>_html"
                    yield record, url_field + HTML_SUFFIX, alternative


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


def is_permanent_failure(entry):
    """A failure that retrying cannot change: the address leads to a different
    act than the record's (Slov-Lex links of Czech laws point at their Slovak
    equivalents). Skipped by a normal run — each retry costs a browser — unless
    `--force`."""
    return entry.get("status") == "failed" and "is a different act than" in (entry.get("error") or "")


def is_stale(manifest, key, url):
    """A fetched entry whose address is no longer the one the record asks for
    (e.g. now the document's own language): it has to be fetched again."""
    entry = manifest.get(key)
    return bool(entry and entry.get("status") == "fetched" and entry.get("url") != url)


def already_fetched(manifest, key):
    entry = manifest.get(key)
    if not entry or entry.get("status") != "fetched":
        return False
    local_path = entry.get("local_path")
    return bool(local_path) and (REPO_ROOT / local_path).exists()


# What every EUR-Lex act page has once its content has rendered: the `div#text`
# of the original text, the `eli-container` of a consolidated text, or the
# Official Journal's own title class, or the wrapper of a Word file converted to XHTML.
_EURLEX_ACT_MARKER = re.compile(
    r"""id=["'](?:text|TexteOnly)["']|eli-container|oj-doc-ti"""
    # the converted Word file: the classes of its title block, or its first-level headings
    r"""|class=["'](?:Emission|Rfrenceinstitutionnelle|Typedudocument_cp|Titreobjet_cp|Heading1)["']""")


def designation_numbers(znacka):
    """The `N/YYYY` or `YYYY/N` number pairs in a designation ("124/2000 Z. z."
    -> {"124/2000"}, "(EU) 2019/2144" -> {"2019/2144"}), used to check that a
    fetched page is the act the record names and not some other act that the
    source's address happens to lead to."""
    return set(re.findall(r"\d{1,4}/\d{1,4}", znacka or ""))


def is_document_page(url, content, content_type="", znacka=None):
    """(True, "") when `content` is the document that `url` points at, else
    (False, reason). EUR-Lex answers an unknown or mistyped ELI — and a request
    its firewall does not like — with a 200 "Search results" page or an empty
    body; Slov-Lex answers every request with the same empty Angular shell
    unless a browser renders it, and shows an act's history page, not its text,
    for an act with no current version. Storing any of these as the document's
    full text (which is what happened for three EUR-Lex records and for all 27
    Slov-Lex ones) serves the wrong page to every reader. With `znacka`, a
    Slov-Lex page must also carry that designation."""
    if not content:
        return False, "empty response"
    if "pdf" in (content_type or "").lower() or url.lower().split("?")[0].endswith(".pdf"):
        return (True, "") if content[:5] == b"%PDF-" else (False, "not a PDF")
    if "eur-lex.europa.eu" in url:
        head = content[:20000].decode("utf-8", "replace")
        m = re.search(r"<title>(.*?)</title>", head, re.S | re.I)
        if m and "search results" in m.group(1).lower():
            return False, "EUR-Lex returned a search-results page (unknown or mistyped address)"
        text = content.decode("utf-8", "replace")
        if "text/html" in (content_type or "text/html") and not _EURLEX_ACT_MARKER.search(text):
            return False, "EUR-Lex page without the act's text (the content did not render)"
    if "slov-lex.sk" in url:
        text = content.decode("utf-8", "replace")
        if "predpisOznacenie" not in text:
            return False, "Slov-Lex page without the act's text (an empty shell, a history page or a missing act)"
        numbers = designation_numbers(znacka)
        if numbers:
            m = re.search(r"<title>(.*?)</title>", text, re.S | re.I)
            title = m.group(1) if m else ""
            if not any(n in title for n in numbers):
                return False, f"Slov-Lex page is a different act than {znacka} ({title.strip()[:60]!r})"
    return True, ""


def is_waf_challenge(status_code, content):
    """EUR-Lex's firewall answers automated clients with HTTP 202 and an empty
    body (an interstitial that only a real browser completes)."""
    return status_code == 202 or not content


def needs_browser(url, status_code, content):
    """True when plain HTTP cannot give the document: EUR-Lex's firewall
    challenge, or any Slov-Lex page (a single-page app whose HTML is an empty
    shell until a browser runs it)."""
    if "slov-lex.sk" in url:
        return True
    return "eur-lex.europa.eu" in url and is_waf_challenge(status_code, content)


_SLOVLEX_READY = "div.predpis .predpisOznacenie, tr.effectivenessHistoryItem"


def _slovlex_latest_version_url(page):
    """Slov-Lex shows an act that has no current version (repealed) as a
    history page; the newest listed version is the closest thing to its text.
    Returns that version's absolute URL or None."""
    # `td.title` is the version column; the third column ("Novela") links to the
    # amending acts, which are other acts — taking those gave the wrong text.
    hrefs = page.eval_on_selector_all("tr.effectivenessHistoryItem td.title a",
                                      "els => els.map(e => e.href)")
    return hrefs[-1] if hrefs else None


def is_eurlex_pdf(url):
    return "eur-lex.europa.eu" in url and "/TXT/PDF/" in url


def _fetch_eurlex_pdf_with_browser(url, timeout_ms):
    """A PDF cannot be 'rendered', but the firewall that answers plain HTTP with
    a challenge lets a browser context through once it has loaded a page of the
    site; the context's own request client can then download the file."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            context = browser.new_context()
            page = context.new_page()
            page.goto("https://eur-lex.europa.eu/homepage.html", wait_until="domcontentloaded", timeout=timeout_ms)
            page.wait_for_timeout(3000)
            response = context.request.get(url, timeout=timeout_ms * 3)
            return response.status, response.body(), response.headers.get("content-type", "")
        finally:
            browser.close()


def fetch_with_browser(url, timeout_ms=45000):
    """(status, content, content_type) of the page rendered by headless
    Chromium (Playwright, see requirements-optional.txt), or None when
    Playwright is not installed or the browser fails. Used when plain HTTP got
    a firewall challenge (EUR-Lex) or an empty shell (Slov-Lex)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    if is_eurlex_pdf(url):
        try:
            return _fetch_eurlex_pdf_with_browser(url, timeout_ms)
        except Exception:
            return None
    slovlex = "slov-lex.sk" in url
    ready = _SLOVLEX_READY if slovlex else "div#text, #TexteOnly, .eli-container, p.oj-doc-ti"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                page = browser.new_page()
                response = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                try:
                    page.wait_for_selector(ready, timeout=timeout_ms)
                except Exception:
                    pass  # a search/error page has neither; the caller decides
                if slovlex and page.locator("div.predpis .predpisOznacenie").count() == 0:
                    latest = _slovlex_latest_version_url(page)
                    if latest:
                        response = page.goto(latest, wait_until="domcontentloaded", timeout=timeout_ms)
                        try:
                            page.wait_for_selector("div.predpis .predpisOznacenie", timeout=timeout_ms)
                        except Exception:
                            pass
                return (response.status if response else 0, page.content().encode("utf-8"),
                        "text/html; charset=utf-8")
            finally:
                browser.close()
    except Exception:
        return None


def fetch_one(session, record, url_field, url):
    """Performs the actual HTTP GET and returns a manifest entry dict.
    Never raises — network/HTTP failures are recorded as a `failed`
    status so one bad URL doesn't abort the whole run. A response that is
    not the document (a search-results page, an empty body) is a failure
    too, and is never written to disk."""
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
    status, content, content_type = resp.status_code, resp.content, resp.headers.get("Content-Type", "")

    if needs_browser(url, status, content):
        browsed = fetch_with_browser(url)
        if browsed:
            status, content, content_type = browsed

    ok, reason = is_document_page(url, content, content_type, znacka)
    if not ok:
        return {"status": "failed", "url": url, "http_status": status, "error": reason, "fetched_at": now}

    ext = extension_from_url(url, content_type)
    sha256 = hashlib.sha256(content).hexdigest()
    FULLTEXT_DIR.mkdir(parents=True, exist_ok=True)
    local_path = FULLTEXT_DIR / flat_name(znacka, sha256, ext)
    if not local_path.exists():  # same content already stored: nothing to write
        local_path.write_bytes(content)

    return {
        "status": "fetched",
        "url": url,
        "local_path": str(local_path.relative_to(REPO_ROOT)),
        "http_status": status,
        "sha256": sha256,
        "fetched_at": now,
    }


def designation_of(key):
    """The designation inside a manifest key `source|designation|url field`."""
    return key.split("|", 1)[1].rsplit("|", 1)[0]


def audit_manifest(manifest, repo_root=REPO_ROOT, apply=False):
    """Finds `fetched` entries whose stored file is not the document (see
    is_document_page) — downloads from before that check existed — marks them
    `failed` and deletes the file unless another entry still uses it. Returns
    [(key, old local_path, reason)]. Dry run without `apply`."""
    root = pathlib.Path(repo_root)
    bad = []
    for key, entry in sorted(manifest.items()):
        path = entry.get("local_path")
        if entry.get("status") != "fetched" or not path or not (root / path).is_file():
            continue
        content = (root / path).read_bytes()
        # The markers sit deep in a large page, so the whole file is checked.
        ok, reason = is_document_page(entry.get("url", ""), content,
                                      "application/pdf" if path.endswith(".pdf") else "text/html",
                                      designation_of(key))
        if not ok:
            bad.append((key, path, reason))
    if apply:
        for key, path, reason in bad:
            manifest[key] = {"status": "failed", "url": manifest[key].get("url"), "error": reason,
                             "fetched_at": datetime.datetime.now().isoformat(timespec="seconds")}
        still_used = {e.get("local_path") for e in manifest.values() if e.get("status") == "fetched"}
        for path in {p for _, p, _ in bad}:
            if path not in still_used:
                (root / path).unlink()
    return bad


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None,
                         help="fetch at most N documents (for a manual smoke test)")
    parser.add_argument("--force", action="store_true",
                         help="re-fetch even if the manifest already has this entry")
    parser.add_argument("--only", action="append", default=[], metavar="KEY",
                         help="fetch only this manifest key ('source|designation|url field'; repeatable), "
                              "even if already fetched — for repairing single entries without retrying the "
                              "ones that were marked failed on purpose")
    parser.add_argument("--host", default=None, metavar="TEXT",
                         help="fetch only the targets whose URL contains TEXT (e.g. slov-lex.sk) — for "
                              "staged runs; the other hosts keep their manifest entries untouched")
    parser.add_argument("--audit", action="store_true",
                         help="check the already stored files: mark those that are not the document "
                              "(search-results pages, empty files) failed and delete them with --apply; "
                              "then exit (run again without --audit to fetch them from the right address)")
    parser.add_argument("--apply", action="store_true", help="with --audit: really change the manifest and delete")
    args = parser.parse_args()

    if args.audit:
        manifest = load_manifest()
        bad = audit_manifest(manifest, apply=args.apply)
        for key, path, reason in bad:
            print(f"{key}: {path} — {reason}")
        if args.apply:
            save_manifest(manifest)
        print(f"{len(bad)} stored files are not the document" + ("" if args.apply else " (dry run — add --apply)"))
        return

    with open(RAW_DB_PATH, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    # candidates accepted on /admin/candidates are in the database before the next rebuild of the raw data
    accepted_path = REPO_ROOT / "data" / "accepted_candidates.json"
    if accepted_path.exists():
        raw_data = raw_data + list(json.loads(accepted_path.read_text(encoding="utf-8")).values())
    # a confirmed correction (e.g. a wrong designation) changes the manifest key and address too
    import build_unified_db
    corrections = build_unified_db.load_manual_corrections()
    for record in raw_data:
        build_unified_db.apply_manual_corrections(record, corrections)

    manifest = load_manifest()
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    fetched_count = 0
    run_cache = {}  # (znacka, url) -> entry: the same address under two fields is fetched once
    seen_keys = set()  # the raw data can list one (source, designation) twice, with different addresses
    for record, url_field, url in iter_fetch_targets(raw_data, load_url_overrides()):
        key = manifest_key(record["zdroj_dat"], record["znacka"].strip(), url_field)
        if key in seen_keys:
            continue  # the first record decides, as it always did
        seen_keys.add(key)
        if args.only and key not in args.only:
            continue
        if args.host and args.host not in url:
            continue
        if not args.force and not args.only and not is_stale(manifest, key, url) and (
                already_fetched(manifest, key) or is_permanent_failure(manifest.get(key, {}))):
            continue
        if args.limit is not None and fetched_count >= args.limit:
            break

        cached = run_cache.get((record["znacka"].strip(), url))
        if cached:
            print(f"[{record['zdroj_dat']}] {record['znacka']} ({url_field}) -> same address as before, reused")
            manifest[key] = dict(cached)
            save_manifest(manifest)
            continue
        if fetched_count > 0:
            time.sleep(SLEEP_SECONDS)
        print(f"[{record['zdroj_dat']}] {record['znacka']} ({url_field}) -> {url}")
        manifest[key] = fetch_one(session, record, url_field, url)
        if manifest[key]["status"] == "fetched":
            run_cache[(record["znacka"].strip(), url)] = manifest[key]
        print(f"  {manifest[key]['status']}")
        fetched_count += 1
        save_manifest(manifest)

    print(f"\nDone. {fetched_count} URLs fetched this run. "
          f"Manifest: {MANIFEST_PATH.relative_to(REPO_ROOT)} ({len(manifest)} entries total).")


if __name__ == "__main__":
    main()
