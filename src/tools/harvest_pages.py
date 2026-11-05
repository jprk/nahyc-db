"""Adapters of stage E5 (doc/DATA_SOURCES.md, odstavec 4.3): pages without a feed or an
interface, read as HTML, and two interfaces found while doing so (TRIS search results,
the Have Your Say API). Each adapter is `function(entry, session, since, context)` like
those of harvest_adapters.py.

* ticr_news — the news of the Technical Inspection of the Czech Republic (TIČR), dated
  text blocks of one page; basic and broader terms (pressure and gas equipment are its
  agenda).
* hzs_news — the news of the Fire Rescue Service (HZS ČR), mostly regional; basic terms.
* cmi_oop — the list of measures of general nature (OOP) of the Czech Metrology
  Institute; an OOP with a basic term is tier 1, one on fuel dispensers or gas meters
  tier 2 (dispensers of hydrogen would fall under such a measure).
* md_adr_pages — the ADR pages of the Ministry of Transport with the date each was
  updated; a finding when a page changed since the last applied run (the first run only
  sets the baseline).
* tris_notifications — notified drafts of national technical regulations (TRIS) found
  for "hydrogen" (the search is a POST form); those received in the last year, Czech
  ones tier 1, others tier 2 (signal `draft`). Not run: since 2026-11-05 the site answers
  the search of a robot with "Disallowed by robots.txt" (the source is `prohibited`);
  kept for the case the operator allows it.
* hys_initiatives — initiatives of the Commission (Have Your Say) found for "hydrogen"
  through the API the site itself uses; initiatives not yet adopted as a proposal
  (a proposal is followed by OEIL and EUR-Lex) are drafts in tier 1.
"""
import datetime
import hashlib
import html
import re
import time
import urllib.parse

import harvest
from harvest import Finding

TRIS_SEARCH = "https://technical-regulation-information-system.ec.europa.eu/en/search/results"
TRIS_BASE = "https://technical-regulation-information-system.ec.europa.eu"
TRIS_DAYS = 365
HYS_API = "https://ec.europa.eu/info/law/better-regulation/brpapi/searchInitiatives"
HYS_PAGE = "https://ec.europa.eu/info/law/better-regulation/have-your-say/initiatives/{}_en"
HYS_DONE_STAGES = ("ADOPTION_WORKFLOW",)
CMI_SCOPE = re.compile(r"výdejní stojan|plyn", re.IGNORECASE)
_DATE = r"(\d{1,2})\. ?(\d{1,2})\. ?(20\d\d)"


def _text(fragment):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment or "")).split())


def _iso(day, month, year):
    return f"{year}-{int(month):02d}-{int(day):02d}"


def _hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _page(session, url):
    response = session.get(url, timeout=60)
    response.raise_for_status()
    return response


def _tier(text, broader):
    return 1 if harvest.matches(text) else 2 if broader and harvest.matches(text, broader=True) else None


# --- TIČR ------------------------------------------------------------------------------

def parse_ticr(page_html):
    """[(ISO date, text)] of the news blocks of the TIČR news page. The blocks are
    separated by non-breaking spaces and start with their date ("1.11.2026 Nové …");
    dates inside a block's text do not start a block."""
    body = re.sub(r"<script.*?</script>|<style.*?</style>|<nav.*?</nav>", " ", page_html, flags=re.S)
    raw = re.sub(r"<[^>]+>", " ", body)
    start = raw.find("Aktuality:")
    raw = raw[start + len("Aktuality:"):] if start >= 0 else raw
    news = []
    for block in re.split(r"(?:&nbsp;|\xa0)(?:\s|&nbsp;|\xa0)*", raw):
        text = " ".join(html.unescape(block).split())
        m = re.match(r"^(\d{1,2})\.(\d{1,2})\.(20\d\d)\s*(?:-\s*)?(.+)$", text)
        if m:
            news.append((_iso(m.group(1), m.group(2), m.group(3)), m.group(4)))
    return news


def ticr_news(entry, session, since, context):
    url = entry["access"]["endpoint"]
    findings = []
    for date, text in parse_ticr(_page(session, url).text):
        tier = _tier(text, broader=True)
        if tier:
            findings.append(Finding(entry["id"], "new_document", text[:200], url=url, native_id=_hash(date + text[:120]),
                                    tier=tier, date=date, language="CS", jurisdikce="CZ", excerpt=text[:300]))
    return findings


# --- HZS ČR ----------------------------------------------------------------------------

def hzs_news(entry, session, since, context):
    response = _page(session, entry["access"]["endpoint"])
    findings, seen = [], set()
    for href, inner in re.findall(r'<a[^>]+href="(/[a-z0-9\-]+/[^"/#?]+)"[^>]*>(.*?)</a>', response.text, re.S):
        title = _text(inner)
        url = urllib.parse.urljoin(response.url, href)
        if not title or url in seen or not harvest.matches(title):
            continue
        seen.add(url)
        findings.append(Finding(entry["id"], "new_document", title, url=url, native_id=_hash(url), tier=1,
                                language="CS", jurisdikce="CZ", excerpt="Zpravodajství HZS ČR"))
    return findings


# --- ČMI -------------------------------------------------------------------------------------

def cmi_oop(entry, session, since, context):
    response = _page(session, entry["access"]["endpoint"])
    findings, seen = [], set()
    for href, oop, inner in re.findall(r'<a[^>]+href="([^"]*(0111-OOP-C\d+-\d+)[^"]*)"[^>]*>(.*?)</a>',
                                       response.text, re.S):
        title = _text(inner)
        tier = 1 if harvest.matches(title) else 2 if CMI_SCOPE.search(title) else None
        if oop in seen or not tier:
            continue
        seen.add(oop)
        findings.append(Finding(entry["id"], "new_document", f"OOP {oop}: {title}", key=None, native_id=oop,
                                url=urllib.parse.urljoin(response.url, href), tier=tier, document_type="Metodika",
                                language="CS", jurisdikce="CZ", excerpt=f"Opatření obecné povahy ČMI {oop} — {title}"))
    return findings


# --- MD: ADR ------------------------------------------------------------------------------------

def parse_dated_pages(page_html, after="Nákladní doprava"):
    """[(title, ISO date)] of "<title> DD. MM. YYYY" pairs of a hub page's text."""
    text = _text(re.sub(r"<script.*?</script>|<style.*?</style>", " ", page_html, flags=re.S))
    start = text.find(after)
    text = text[start + len(after):] if start >= 0 else text
    pairs = re.findall(r"([A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][^.]*?(?:\d+\.\d+\.\d+[^.]*?)?)\s+" + _DATE, text)
    return [(" ".join(t.split()), _iso(d, m, y)) for t, d, m, y in pairs if len(t) < 120]


def md_adr_pages(entry, session, since, context):
    response = _page(session, entry["url"])
    if since is None:
        return []  # the first applied run only sets the baseline
    findings = []
    for title, date in parse_dated_pages(response.text):
        if date > since[:10]:
            findings.append(Finding(entry["id"], "new_document", f"MD, ADR: aktualizace stránky „{title}“ ({date})",
                                    url=response.url, native_id=_hash(title + date), tier=2, date=date, language="CS",
                                    jurisdikce="CZ",
                                    excerpt="Stránka byla aktualizována; zkontrolovat, zda nepřináší nové znění ADR, "
                                            "mnohostrannou dohodu nebo stanovisko."))
    return findings


# --- TRIS ---------------------------------------------------------------------------------------

def parse_tris(page_html):
    """[{country, reference, title, received, standstill, url}] of TRIS search results."""
    found = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", page_html, re.S):
        cells = [_text(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
        href = re.search(r'href="(/en/notification/\d+)"', row)
        if len(cells) < 5 or not re.match(r"20\d\d/\d+/[A-Z]{2}", cells[1]):
            continue
        dates = [re.match(r"(\d{2})-(\d{2})-(\d{4})", c) for c in cells[3:5]]
        found.append({"country": cells[0], "reference": cells[1], "title": re.sub(r"^Title:\s*", "", cells[2]),
                      "received": _iso(*dates[0].groups()) if dates[0] else None,
                      "standstill": _iso(*dates[1].groups()) if dates[1] else None,
                      "url": TRIS_BASE + href.group(1) if href else None})
    return found


def tris_notifications(entry, session, since, context):
    response = session.post(TRIS_SEARCH, data={"search_terms": "hydrogen", "search_type": "full", "op": "Search"},
                            timeout=90)
    response.raise_for_status()
    notifications = parse_tris(response.text)
    if not notifications and "no results" not in response.text.lower():
        raise RuntimeError("no notification read from the TRIS results (has the page changed?)")
    oldest = (datetime.date.fromisoformat(context["today"]) - datetime.timedelta(days=TRIS_DAYS)).isoformat()
    findings = []
    for item in notifications:
        if (item["received"] or "") < oldest:
            continue
        czech = item["reference"].endswith("/CZ")
        findings.append(Finding(entry["id"], "draft", item["title"], key=f"DRAFT-TRIS:{item['reference']}",
                                native_id=item["reference"], url=item["url"], tier=1 if czech else 2,
                                date=item["received"], language="EN", jurisdikce="CZ" if czech else "EU",
                                excerpt=f"TRIS {item['reference']} ({item['country']}), přijato {item['received']}, "
                                        f"konec lhůty {item['standstill']}"))
    return findings


# --- Have Your Say ----------------------------------------------------------------------------

def hys_initiatives(entry, session, since, context):
    findings, page = [], 0
    while True:
        response = session.get(HYS_API, params={"text": "hydrogen", "language": "EN", "page": page, "size": 50},
                               timeout=60)
        response.raise_for_status()
        result = response.json()["initiativeResultDtoPage"]
        for item in result["content"]:
            stages = [s.get("frontEndStage") for s in item.get("currentStatuses") or []]
            if item.get("initiativeStatus") != "ACTIVE" or any(s in HYS_DONE_STAGES for s in stages):
                continue
            ident = int(item["id"])
            feedback = next((s for s in item.get("currentStatuses") or [] if s.get("receivingFeedbackStatus")), {})
            findings.append(Finding(entry["id"], "draft", item.get("shortTitle", "").strip(),
                                    key=f"DRAFT-EU:hys:{ident}", native_id=str(ident), url=HYS_PAGE.format(ident),
                                    tier=1, language="EN", jurisdikce="EU",
                                    excerpt=f"Have Your Say {item.get('reference')}: {item.get('foreseenActType')}, "
                                            f"fáze {', '.join(s for s in stages if s)}, připomínky "
                                            f"{feedback.get('receivingFeedbackStatus', '—')}"))
        page += 1
        if page >= result.get("totalPages", 1):
            break
        time.sleep(1)
    return findings
