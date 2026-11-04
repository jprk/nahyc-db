"""Adapters of stage E2 (doc/DATA_SOURCES.md, odstavec 4.3): proposed acts in the
legislative process — the early signal of what is coming before it is published.
Each adapter is `function(entry, session, since, context)` like those of
harvest_adapters.py and returns `draft` findings.

* veklep_rss — the news feed of VeKLEP (eKLEP pro veřejnost): proposals of Czech
  acts in the interministerial comment procedure. The JSON interface of VeKLEP
  answers the identified robot with a block page (2026-11-04); the feed is read.
* psp_bills — the open data of the Chamber of Deputies (tisky.zip, sbirka.zip,
  poslanci.zip): bills (government and other) of the current term that the Chamber
  has not concluded, with the acts each amends or repeals (`sb_pre`) and its stage.
* senate_bills — the Senate prints from the Chamber's open data (se_tisk.zip; the
  Senate's own site forbids robots): bills of the current Senate term.
* oeil_procedures — the Legislative Observatory of the European Parliament (RSS
  export for "hydrogen"): legislative procedures (COD, CNS, DEA), each checked in the
  Parliament's open data API; a procedure published in the Official Journal is over,
  and so is a delegated act (DEA) without any activity for DEA_QUIET_DAYS.

**One proposal, one candidate.** A Czech bill gets the key `DRAFT-CZ:eklep:<PID>`
when it has a document in eKLEP (tisk_eklep links a Chamber print to it, psp2senat a
Senate print to the Chamber print), else `DRAFT-CZ:psp:<id>` or
`DRAFT-CZ:senat:<id>`; an EU procedure `DRAFT-EU:<reference>`. The findings of
VeKLEP, the Chamber and the Senate about one bill so meet in one candidate.

**Relevance** (draft_tier): tier 1 when the proposal amends or repeals a document of
the database (for VeKLEP read from the title) or its title has a basic search term
(harvest.matches); tier 2 when the title names a subject area of
doc/DATABASE_SCOPE.md (harvest_adapters._SCOPE); any other proposal is no finding —
the rest of the country's legislation. A proposal amending documents of the
database carries their ids (`amends_ids`), so that accepting it gives the draft
document the AMENDS relations.
"""
import datetime
import email.utils
import io
import re
import time
import xml.etree.ElementTree as ET
import zipfile

import harvest
from harvest import Finding

OPENDATA = "https://www.psp.cz/eknih/cdrom/opendata/{}.zip"
BILL_KINDS = ("1", "2")  # druh_tisku: vládní návrh zákona, návrh zákona
SENATE_BILL_KINDS = ("1", "2", "3", "4", "7", "8")  # se_druh_tisku: návrhy zákonů
CHANGE_TYPES = {"31": "mění", "32": "ruší"}
EU_LEGISLATIVE = ("COD", "CNS", "DEA")
EP_API = "https://data.europarl.europa.eu/api/v2/procedures/{}?format=application%2Fld%2Bjson"
EP_DELAY = 2  # data.europarl.europa.eu/robots.txt: Crawl-delay 2
OJ_PUBLISHED = "def/ep-activities/PUBLICATION_OFFICIAL_JOURNAL"
# A delegated act is only scrutinised by the Parliament (objection within 2 + 2 months) and never gets the
# publication event in its data; a DEA procedure without any activity for this long is taken as over.
DEA_QUIET_DAYS = 180


def draft_tier(title, amends, known):
    """1, 2 or None (see the module docstring)."""
    import harvest_adapters as ha
    if any(k in known for k in amends) or harvest.matches(title):
        return 1
    if ha._SCOPE.search(title or ""):
        return 2
    return None


def amended_in_title(title, own_key=None):
    """Czech acts a title names ("…, kterým se mění zákon č. 458/2000 Sb., …")."""
    import citation_closure as cc
    return sorted(k for k in cc.own_keys(None, title or "") if k.startswith("CZ:") and k != own_key)


def _ids(keys, context):
    import citation_closure as cc
    by_key = {}
    for doc_id, identifier, title, _url in context.get("documents", []):
        for k in cc.own_keys(identifier, title):
            by_key.setdefault(k, set()).add(doc_id)
    return sorted({i for k in keys for i in by_key.get(k, ())})


def _draft(entry, key, title, tier, amends, context, **fields):
    known = [k for k in amends if k in context["known"]]
    extra = {"amends": amends} if amends else {}
    if known:
        extra["amends_ids"] = _ids(known, context)
    return Finding(entry["id"], "draft", title, key=key, native_id=key, tier=tier, extra=extra or None, **fields)


# --- VeKLEP ----------------------------------------------------------------------

def parse_rss(data):
    """[{title, link, description, guid, date}] of an RSS 2.0 feed, given as bytes so that
    the XML declaration decides the encoding (VeKLEP sends no charset in its header)."""
    items = []
    for item in ET.fromstring(data).iter("item"):
        date = item.findtext("pubDate")
        try:
            date = email.utils.parsedate_to_datetime(date).date().isoformat() if date else None
        except (TypeError, ValueError):
            pass
        items.append({"title": (item.findtext("title") or "").strip(), "link": item.findtext("link"),
                      "description": (item.findtext("description") or "").strip(),
                      "guid": (item.findtext("guid") or "").strip(), "date": date})
    return items


def veklep_rss(entry, session, since, context):
    response = session.get(entry["access"]["endpoint"], timeout=60)
    response.raise_for_status()
    findings = []
    for item in parse_rss(response.content):
        amends = amended_in_title(item["title"])
        tier = draft_tier(item["title"], amends, context["known"])
        if tier is None or not item["guid"]:
            continue
        findings.append(_draft(entry, f"DRAFT-CZ:eklep:{item['guid']}", item["title"], tier, amends, context,
                               url=item["link"], date=item["date"], language="CS", jurisdikce="CZ",
                               excerpt=item["description"][:300]))
    return findings


# --- the Chamber of Deputies and the Senate -----------------------------------------

def unl(archive, name):
    """Rows of a table of the Chamber's open data (windows-1250, "|" separated)."""
    return [line.split("|") for line in archive.read(name).decode("cp1250").splitlines() if line]


def fetch_archive(session, name):
    response = session.get(OPENDATA.format(name), timeout=120)
    response.raise_for_status()
    return zipfile.ZipFile(io.BytesIO(response.content))


def _date(text):
    try:
        return datetime.datetime.strptime(text, "%d.%m.%Y").date().isoformat()
    except ValueError:
        return None


class ChamberData:
    """The tables of tisky.zip, sbirka.zip and poslanci.zip a bill needs."""

    def __init__(self, tisky, sbirka, poslanci):
        self.tisky = {r[0]: r for r in unl(tisky, "tisky.unl")}
        stav_typ = {r[0]: r[1] for r in unl(tisky, "stavy.unl")}
        typ = {r[0]: r[1] for r in unl(tisky, "typ_stavu.unl")}
        self.stage = {sid: typ.get(t, "") for sid, t in stav_typ.items()}
        self.eklep = {r[4]: r[0] for r in unl(tisky, "tisk_eklep.unl") if len(r) > 4}
        acts = {r[0]: f"CZ:{int(r[1])}/{r[2]}" for r in unl(sbirka, "sbirka.unl") if r[1].isdigit()}
        self.changes = {}  # (zdroj, id_tisk) -> [(key, verb)]
        for r in unl(sbirka, "sb_pre.unl"):
            if r[2] in acts and r[3] in CHANGE_TYPES:
                self.changes.setdefault((r[4], r[0]), []).append((acts[r[2]], CHANGE_TYPES[r[3]]))
        self.terms = {r[0]: r[3] for r in unl(poslanci, "organy.unl") if r[3].startswith("PSP")}

    def current_term(self):
        bills = [(_date(r[11]) or "", r[7]) for r in self.tisky.values() if r[1] in BILL_KINDS]
        return max(bills)[1]

    def key(self, id_tisk):
        pid = self.eklep.get(id_tisk)
        return f"DRAFT-CZ:eklep:{pid}" if pid else f"DRAFT-CZ:psp:{id_tisk}"

    def concluded(self, id_tisk):
        return self.stage.get(self.tisky[id_tisk][2]) == "KONEC"

    def url(self, id_tisk):
        r = self.tisky[id_tisk]
        term = self.terms.get(r[7], "PSP")[3:]
        return f"https://www.psp.cz/sqw/historie.sqw?o={term}&t={r[3]}" if term else None


def psp_bills(entry, session, since, context):
    data = ChamberData(fetch_archive(session, "tisky"), fetch_archive(session, "sbirka"),
                       fetch_archive(session, "poslanci"))
    term = data.current_term()
    findings = []
    for id_tisk, r in sorted(data.tisky.items(), key=lambda kv: int(kv[0])):
        if r[1] not in BILL_KINDS or r[7] != term or data.concluded(id_tisk):
            continue
        title = r[15] or r[10]
        changes = data.changes.get(("1", id_tisk), [])
        amends = sorted({k for k, _ in changes} | set(amended_in_title(title)))
        tier = draft_tier(title, amends, context["known"])
        if tier is None:
            continue
        stage = data.stage.get(r[2], "")
        verbs = "; ".join(f"{verb} {k.split(':')[1]} Sb." for k, verb in changes[:8])
        findings.append(_draft(entry, data.key(id_tisk), title, tier, amends, context, url=data.url(id_tisk),
                               date=_date(r[11]), language="CS", jurisdikce="CZ",
                               excerpt=f"sněmovní tisk {r[3]}, stav: {stage}" + (f"; {verbs}" if verbs else "")))
    return findings


def senate_bills(entry, session, since, context):
    senate = fetch_archive(session, "se_tisk")
    data = ChamberData(fetch_archive(session, "tisky"), fetch_archive(session, "sbirka"),
                       fetch_archive(session, "poslanci"))
    prints = unl(senate, "se_tisk.unl")
    to_chamber = {r[1]: r[0] for r in unl(senate, "psp2senat.unl")}
    term = str(max(int(r[4]) for r in prints if r[4].isdigit()))
    findings = []
    for r in prints:
        id_tisk, kind, number, period, short, title = r[0], r[1], r[3], r[4], r[5], (r[6] if len(r) > 6 else "")
        if kind not in SENATE_BILL_KINDS or period != term:
            continue
        chamber = to_chamber.get(id_tisk)
        if chamber in data.tisky and data.concluded(chamber):
            continue
        title = title or short
        changes = data.changes.get(("2", id_tisk), []) or data.changes.get(("1", chamber), [])
        amends = sorted({k for k, _ in changes} | set(amended_in_title(title)))
        tier = draft_tier(title, amends, context["known"])
        if tier is None:
            continue
        key = data.key(chamber) if chamber in data.tisky else f"DRAFT-CZ:senat:{id_tisk}"
        findings.append(_draft(entry, key, title, tier, amends, context,
                               url=data.url(chamber) if chamber in data.tisky else None,
                               language="CS", jurisdikce="CZ",
                               excerpt=f"senátní tisk {number} ({period}. funkční období)"
                                       + (f", sněmovní tisk {data.tisky[chamber][3]}" if chamber in data.tisky else "")))
    return findings


# --- the Legislative Observatory ------------------------------------------------------

def procedure_type(reference):
    m = re.search(r"\(([A-Z]+)\)$", reference or "")
    return m.group(1) if m else None


def procedure_state(session, reference):
    """(Czech or English title, published in the Official Journal?, date of the last
    activity) from the EP API."""
    year, rest = reference.split("/", 1)
    response = session.get(EP_API.format(f"{year}-{rest.split('(')[0]}"), timeout=60,
                           headers={"Accept": "application/ld+json"})
    response.raise_for_status()
    process = response.json()["data"][0]
    titles = process.get("process_title", {})
    activities = process.get("consists_of", [])
    events = {e.get("had_activity_type") for e in activities}
    last = max((e.get("activity_date") or "" for e in activities), default="") or None
    return titles.get("cs") or titles.get("en"), OJ_PUBLISHED in events, last


def procedure_over(kind, published, last, today):
    if published:
        return True
    if kind == "DEA" and last:
        quiet = datetime.date.fromisoformat(today) - datetime.date.fromisoformat(last[:10])
        return quiet.days > DEA_QUIET_DAYS
    return False


def oeil_procedures(entry, session, since, context):
    response = session.get(entry["access"]["endpoint"], timeout=90)
    response.raise_for_status()
    findings = []
    for item in parse_rss(response.content):
        reference = item["title"]
        if procedure_type(reference) not in EU_LEGISLATIVE:
            continue
        time.sleep(EP_DELAY)
        title, published, last = procedure_state(session, reference)
        if procedure_over(procedure_type(reference), published, last, context["today"]):
            continue
        findings.append(Finding(entry["id"], "draft", title or item["description"], key=f"DRAFT-EU:{reference}",
                                native_id=reference, tier=1, url=item["link"], date=item["date"], language="CS",
                                jurisdikce="EU", excerpt=f"{reference}: {item['description']}"
                                + (f"; poslední událost {last[:10]}" if last else "")))
    return findings
