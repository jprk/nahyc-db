"""Fetches a Czech law's authoritative title/description directly from
zakonyprolidi.cz (Sinay_Zakony's and Haltuf_Dokumenty's own per-document
source for Czech legislation).

doc/PLAN.md §8, 2026-09-11: part of the authoritative per-site
title/description extraction feature — see `src/tools/
fetch_authoritative_metadata.py` for the orchestrator that calls this.

Verified live (2026-09-11) against a real per-document URL
(`https://www.zakonyprolidi.cz/cs/2006-183`): the page's `<meta
property="og:title">`/`<meta property="og:description">` tags already
carry exactly the canonical designation+title and a short, informative
description (including repeal/amendment status, e.g. "...zrušeno k
01.01.2024(283/2021 Sb.)") — no anti-bot wall, works with a plain
browser-style User-Agent (an earlier WebFetch-tool-only 403 turned out to
be a tool-specific artifact, not a real site block). `data/fulltext/
{Haltuf_Dokumenty,Sinay_Zakony}/` already has ~140 of these pages cached
locally via `fetch_fulltext.py` — parse that file when given, never
re-fetch what's already on disk.

**Why a third-party site, not the official `e-sbirka.gov.cz`?** See
`src/sites/esbirka.py`'s own docstring — the actual government source's
frontend is an unscrapeable SPA and its LOD graph doesn't expose a plain
title field this session could reach. `fetch_authoritative_metadata.py`
uses THIS module for the title/description text, and `esbirka.py` only to
verify the citation and attach the real government URL as a reference
alongside it — never as a replacement for this module's content.
"""
import requests
from bs4 import BeautifulSoup

USER_AGENT = "Mozilla/5.0 (compatible; NAHYC-DP004-sites-tool/1.0; +research use, low-volume)"


def _parse_html(html):
    soup = BeautifulSoup(html, "html.parser")
    title_tag = soup.find("meta", property="og:title")
    title = title_tag["content"].strip() if title_tag and title_tag.get("content") else None
    if not title:
        title_el = soup.find("title")
        title = title_el.get_text(strip=True) if title_el else None
    if not title:
        return None

    desc_tag = soup.find("meta", property="og:description") or soup.find("meta", attrs={"name": "description"})
    description = desc_tag["content"].strip() if desc_tag and desc_tag.get("content") else None

    return {"title": title, "description": description}


def extract(url, cached_path=None, session=None):
    """Returns {"title": str, "description": str|None} parsed from a
    zakonyprolidi.cz page's og:title/og:description meta tags, or None if
    neither the cached file nor a live fetch yields a parseable title.
    Prefers `cached_path` (already-fetched HTML under data/fulltext/) over
    a network request when given."""
    if cached_path:
        try:
            with open(cached_path, "r", encoding="utf-8", errors="replace") as f:
                html = f.read()
            result = _parse_html(html)
            if result:
                return result
        except OSError:
            pass

    if not url:
        return None
    session = session or requests.Session()
    session.headers.setdefault("User-Agent", USER_AGENT)
    try:
        resp = session.get(url, timeout=20)
        resp.raise_for_status()
    except requests.RequestException:
        return None
    return _parse_html(resp.text)
