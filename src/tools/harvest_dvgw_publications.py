"""One-time (idempotent, re-runnable) harvest of DVGW's own curated
listing/index pages — doc/PLAN.md §26, 2026-09-17.

`dvgw-regelwerk.de` (the actual DVGW Set of Rules catalog — `www.dvgw.de`
itself has no useful content) needs no WAF workaround, but both its
search results AND its documents' detail pages are entirely client-side
JS-rendered — Playwright is required either way (see
`harvest_iec_publications.py` for the same environment-setup story:
`sudo playwright install-deps chromium`, already done for this repo).
Detail pages are paywalled beyond a title and one short subtitle line
(no real per-document scope text), and the site's own free-text search
is unreliable for exact designation lookup — confirmed live: 0 of 7
tested designations (`G 260`, `G 1001`, `G 213`, `G 406`, `GW 129`,
`G 685-1`, `ZP 4110`) appeared anywhere in their own search results,
several queries returning the *identical* generic top hits regardless
of query. So, unlike `normoff.py`/`eiga.py`, there is no live
per-designation search worth building here.

Instead, this harvests DVGW's own curated listing pages, each of which
already carries a one-line description alongside every entry — no
detail-page visit needed at all:

- Three "special topic" pages (`s008` H2 Industry, `s009` H2 Production,
  `s010` H2 Complete edition) — paginated via numbered buttons that
  update the page client-side (no URL change, no `?page=` query param
  support despite appearances).
- Three "index" category listings (DVGW Set of Rules for Gas, for
  Gas/Water, and DVGW Information bulletins) — these load via infinite
  scroll instead, no page-number buttons at all.

**These do NOT cover DVGW's full catalog** — confirmed live, combining
all six sources still only resolves 41 of the corpus's 101 DVGW-cited
designations. Per user direction, that's the intentional scope of this
harvest: the other 60 are not reachable through this site without
guessing, and `fetch_authoritative_metadata.py` records them in
`data/dvgw_unresolved_review_queue.json` rather than silently leaving
them indistinguishable from a record nobody's looked at yet.

Usage:
    .venv/bin/python src/tools/harvest_dvgw_publications.py
"""
import json
import pathlib
import re

from playwright.sync_api import sync_playwright

BASE_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

TOPICS_DIR = REPO_ROOT / "data" / "dvgw_topics"
INDEX_PATH = REPO_ROOT / "data" / "dvgw_publications_index.json"

# (source id, URL, pagination mode) — "buttons" clicks numbered buttons
# until none remain; "scroll" scrolls to the bottom until the item count
# stops growing (this site's two different listing UIs, confirmed live).
SOURCES = [
    ("s008", "https://www.dvgw-regelwerk.de/en/topic/special/s008", "buttons"),
    ("s009", "https://www.dvgw-regelwerk.de/en/topic/special/s009", "buttons"),
    ("s010", "https://www.dvgw-regelwerk.de/en/topic/special/s010", "buttons"),
    ("gas", "https://www.dvgw-regelwerk.de/en/index/dvgwRulesGas", "scroll"),
    ("gaswater", "https://www.dvgw-regelwerk.de/en/index/dvgwRulesGasWater", "scroll"),
    ("info", "https://www.dvgw-regelwerk.de/en/index/dvgwInfo", "scroll"),
]

# "Code of Practice G 100" / "Guideline GW 302-1" -> "G 100" / "GW 302-1"
# — the type-of-document words vary ("Code of Practice", "Guideline",
# "Audit Basis", ...) but the designation is always the trailing
# letters-then-digits token.
_DESIGNATION_RE = re.compile(r"\b([A-Z]{1,3}[\s-]?\d[\d.\-]*)\s*$")


def extract_designation(title):
    m = _DESIGNATION_RE.search(title or "")
    return m.group(1).strip() if m else None


def parse_visible_items(page):
    """Every `<li>` currently in the DOM as {title, description, href} —
    `description` is DVGW's own one-line subtitle (`p.regular span`),
    the only description text this site's listing pages (or, per this
    module's own docstring, paywalled detail pages) ever offer."""
    items = []
    for li in page.query_selector_all("li"):
        link_el = li.query_selector("a[href*='technical-rule']")
        if not link_el:
            continue
        headline = link_el.query_selector("h4")
        title = headline.inner_text().strip() if headline else None
        if not title:
            continue
        desc_el = li.query_selector("p.regular span")
        description = desc_el.inner_text().strip() if desc_el else None
        items.append({"title": title, "description": description,
                     "href": link_el.get_attribute("href")})
    return items


def harvest_by_buttons(page, url):
    page.goto(url, timeout=30000, wait_until="networkidle")
    page.wait_for_timeout(1500)
    items = parse_visible_items(page)
    for page_num in range(2, 50):
        button = next((b for b in page.query_selector_all("button")
                      if b.inner_text().strip() == str(page_num)), None)
        if button is None:
            break
        button.click()
        page.wait_for_timeout(1200)
        items.extend(parse_visible_items(page))
    return items


def harvest_by_scroll(page, url):
    page.goto(url, timeout=30000, wait_until="networkidle")
    page.wait_for_timeout(1500)
    previous_count = -1
    stable_rounds = 0
    for _ in range(60):
        count = len(page.query_selector_all("li"))
        if count == previous_count:
            stable_rounds += 1
            if stable_rounds >= 4:
                break
        else:
            stable_rounds = 0
        previous_count = count
        page.keyboard.press("End")
        page.mouse.wheel(0, 5000)
        page.wait_for_timeout(700)
    return parse_visible_items(page)


def build_index():
    """Aggregates every `data/dvgw_topics/<source_id>.json` into the
    final designation -> {title, description} lookup. A designation
    appearing in more than one source keeps whichever copy was written
    first (`setdefault`) — all sources are simultaneous English-language
    snapshots of the same catalog, not different editions to prefer
    between (unlike IEC's amendment-dated entries)."""
    index = {}
    for source_id, _url, _mode in SOURCES:
        source_file = TOPICS_DIR / f"{source_id}.json"
        if not source_file.exists():
            continue
        with open(source_file, "r", encoding="utf-8") as f:
            items = json.load(f)
        for item in items:
            designation = extract_designation(item["title"])
            if not designation or not item.get("description"):
                continue
            index.setdefault(designation, {"title": item["title"],
                                           "description": item["description"]})
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2, sort_keys=True)
    return index


def main():
    TOPICS_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=USER_AGENT)
        for source_id, url, mode in SOURCES:
            items = (harvest_by_buttons(page, url) if mode == "buttons"
                    else harvest_by_scroll(page, url))
            with open(TOPICS_DIR / f"{source_id}.json", "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
            print(f"[{source_id}] {len(items)} item(s)")
        browser.close()

    index = build_index()
    print(f"\nIndex rebuilt: {len(index)} designation(s) -> "
          f"{INDEX_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
