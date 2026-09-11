"""Fetches a Slovak law's authoritative title directly from slov-lex.sk
(Sinay_Zakony's per-document source for Slovak legislation).

doc/PLAN.md §8, 2026-09-11: part of the authoritative per-site
title/description extraction feature — see `src/tools/
fetch_authoritative_metadata.py` for the orchestrator that calls this.

Verified live (2026-09-11) against a real per-document URL
(`https://www.slov-lex.sk/pravne-predpisy/SK/ZZ/2000/124/`, redirecting to
`.../ezbierky/pravne-predpisy/...`): the rendered page is a React SPA
shell with no server-rendered body text, but the `<head>` still carries a
`<script type="application/ld+json">` block with `@type: "Legislation"`
whose `name` field is the full, official designation+title (Slovak
legislation naming convention already folds the subject-matter
description into the official title itself, e.g. "124/2000 Z. z. Vyhláška
Ministerstva vnútra Slovenskej republiky, ktorou sa ustanovujú zásady
požiarnej bezpečnosti..." — so there's no separate short description to
extract here; `description` is always None). No anti-bot wall, works with
a plain browser-style User-Agent and `requests`' own redirect-following
(an earlier WebFetch-tool-only 403 turned out to be a tool-specific
artifact, not a real site block). Falls back to the `<title>` tag
(same content, "| Slov-Lex" suffix stripped) if the JSON-LD block isn't
found or doesn't parse.
"""
import json
import re

import requests
from bs4 import BeautifulSoup

USER_AGENT = "Mozilla/5.0 (compatible; NAHYC-DP004-sites-tool/1.0; +research use, low-volume)"
_TITLE_SUFFIX_RE = re.compile(r"\s*\|\s*Slov-Lex\s*$", re.IGNORECASE)


def _parse_html(html):
    soup = BeautifulSoup(html, "html.parser")

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except (ValueError, TypeError):
            continue
        if isinstance(data, dict) and data.get("@type") == "Legislation" and data.get("name"):
            return {"title": data["name"].strip(), "description": None}

    title_el = soup.find("title")
    if title_el and title_el.get_text(strip=True):
        title = _TITLE_SUFFIX_RE.sub("", title_el.get_text(strip=True)).strip()
        if title:
            return {"title": title, "description": None}

    return None


def extract(url, cached_path=None, session=None):
    """Returns {"title": str, "description": None} parsed from a
    slov-lex.sk page's JSON-LD Legislation block (or its <title> tag as a
    fallback), or None if neither the cached file nor a live fetch yields
    a parseable title. Prefers `cached_path` (already-fetched HTML under
    data/fulltext/) over a network request when given."""
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
        resp = session.get(url, timeout=20, allow_redirects=True)
        resp.raise_for_status()
    except requests.RequestException:
        return None
    return _parse_html(resp.text)
