"""Parser Agent (doc/PLAN.md §3.2/§3.3 step 2, first half) — turns a raw
source document (already-fetched local file, or a live URL) into clean
text for the Extraction Agent to read and the Verification Agent to
quote-check against.

Not a VLM/layout-model parser as §3.2 originally envisioned (LlamaParse/
Docling/Marker) — this repo's real inputs (EUR-Lex/e-Sbirka law full
text, already fetched by `fetch_fulltext.py`, or a live EUR-Lex "TXT"
HTML page) are digitally-native PDF/HTML, not scans, so a layout model
would be solving a problem this corpus doesn't have. `pdfplumber`
(already a pinned dependency, same extraction call as
`src/sites/eiga.py:_extract_pdf_lead()`) and `BeautifulSoup` (also
already pinned) cover it.
"""
import io
import pathlib

import requests
from bs4 import BeautifulSoup

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "data" / "fulltext_manifest.json"
USER_AGENT = "Mozilla/5.0 (compatible; NAHYC-DP004-fulltext-tool/1.0; +research use, low-volume)"


def _local_path_for_url(url, manifest):
    """`fetch_fulltext.py`'s manifest is keyed by `zdroj_dat|znacka|url_field`,
    not by URL -- a screening candidate has neither, so this looks up by
    the manifest ENTRY's own "url" value instead. Returns a repo-relative
    Path, or None if nothing fetched matches."""
    for entry in manifest.values():
        if entry.get("status") == "fetched" and entry.get("url") == url:
            local_path = entry.get("local_path")
            if local_path and (REPO_ROOT / local_path).exists():
                return REPO_ROOT / local_path
    return None


def _load_manifest():
    if MANIFEST_PATH.exists():
        import json
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def extract_text_from_pdf_bytes(data: bytes) -> str:
    import pdfplumber
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def extract_text_from_html_bytes(data: bytes) -> str:
    soup = BeautifulSoup(data, "html.parser")
    return soup.get_text(separator="\n")


def parse_source(url: str, session=None):
    """Returns (raw_text, error). Never raises -- a fetch/parse failure
    is data for the pipeline (routes to `escalate`), not a crash.

    Prefers an already-fetched local copy (`fetch_fulltext.py`'s
    manifest) over a live re-fetch, matching this project's "don't
    hammer the source twice" convention already used elsewhere.
    """
    manifest = _load_manifest()
    local_path = _local_path_for_url(url, manifest)
    if local_path is not None:
        data = local_path.read_bytes()
        suffix = local_path.suffix.lower()
    else:
        session = session or requests.Session()
        session.headers.setdefault("User-Agent", USER_AGENT)
        try:
            resp = session.get(url, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as exc:
            return None, f"fetch failed: {exc}"
        data = resp.content
        content_type = resp.headers.get("Content-Type", "")
        suffix = ".pdf" if "pdf" in content_type else ".html"

    try:
        if suffix == ".pdf":
            text = extract_text_from_pdf_bytes(data)
        else:
            text = extract_text_from_html_bytes(data)
    except Exception as exc:  # pdfplumber/bs4 can raise a variety of types
        return None, f"parse failed: {exc}"

    text = text.strip()
    if not text:
        return None, "parsed empty text"
    return text, None
