"""Adapters of stage E3 (doc/DATA_SOURCES.md, odstavec 4.3): technical standards,
metadata only — never the protected texts. Each adapter is
`function(entry, session, since, context)` like those of harvest_adapters.py.

* vestnik_unmz — the monthly Věstník ÚNMZ (PDF at a predictable address): the
  notice on ČSN issued, amended, corrected and withdrawn, the European standards
  approved for direct use as ČSN, the ČSN drafting tasks started (notice
  "o zahájení zpracování návrhů", read column by column) and the European drafts in
  public enquiry (prEN).
* harmonised_standards — the summary lists (XLSX) of harmonised standards of the
  European Commission for the directives that bear on hydrogen installations.
* cps_tpg — the catalogue of the gas technical rules TPG of the Czech Gas Association
  (valid and no longer valid ones).
* sae_crossref — SAE standards on hydrogen from the open Crossref API (prefix 10.4271).
* rss_items — a news feed filtered by the search terms (ÚNMZ news; stage E4 reuses it).

**Keys.** A standard is `NORM:<designation>` as citation_closure.own_keys() reads it
(`ČSN EN 17124` and `EN 17124` are both `NORM:EN 17124`), or, for a national
designation own_keys() does not read (ČSN of a Czech origin, TPG, SAE), `NORM:` with
the designation itself (harvest.norm_key). A draft is `DRAFT-NORM:<designation>`
(prEN) or `DRAFT-NORM:CZ:<task number>` (ČSN being drafted).

**What becomes what.** A standard the database has gets a `state_change` into the
standards cache (data/norm_validity_cache.json; entries are merged, as several
sources add to one standard): a new edition (`platná`), an amendment or correction,
replacement by another standard (`nahrazená`), withdrawal (`zrušená`), harmonisation
under a directive. A standard the database lacks is a `new_document` candidate in
tier 1 when its title names hydrogen (harvest.matches) and in tier 2 when it names a
broader area (tlaková a plynová zařízení, výbuch, nebezpečné věci, …); any other
standard is no finding. A draft revising a standard of the database is tier 1.
"""
import datetime
import io
import json
import re
import time
import urllib.parse

import harvest
from harvest import Finding

VESTNIK = "https://unmz.gov.cz/wp-content/uploads/vestnik-{month}-{yy:02d}.pdf"
VESTNIK_MONTHS = 3  # months looked at (an issue appears during its month or later) …
VESTNIK_ISSUES = 2  # … of which at most this many existing issues are read
CSN_DETAIL = "https://csnonline.agentura-cas.cz/Detailnormy.aspx?k={}"
PUBLISHED = ("VYDANÉ ČSN", "EVROPSKÉ NORMY SCHVÁLENÉ K PŘÍMÉMU POUŽÍVÁNÍ JAKO ČSN")
CHANGED = ("ZMĚNY ČSN", "OPRAVY ČSN")
WITHDRAWN = ("ZRUŠENÉ ČSN",)
ENQUIRY = "NÁVRHY EVROPSKÝCH NOREM PŘEDLOŽENÉ K VEŘEJNÉMU PROJEDNÁNÍ"
SECTIONS = PUBLISHED + CHANGED + WITHDRAWN + (ENQUIRY,)
TASKS_NOTICE = "o zahájení zpracování návrhů českých technických norem"
HARMONISED_BASE = "https://single-market-economy.ec.europa.eu/single-market/goods/european-standards/harmonised-standards/{}_en"
# Directives whose harmonised standards bear on hydrogen installations (doc/DATABASE_SCOPE.md, odstavec 3).
DIRECTIVES = ("pressure-equipment", "equipment-explosive-atmospheres-atex", "gas-appliances",
              "simple-pressure-vessels", "measuring-instruments-mid", "machinery-md")
TPG_VALID = "https://cgoa.cz/to.normativni-dokumenty/platna-tpg"
TPG_INVALID = "https://cgoa.cz/to.normativni-dokumenty/neplatna-tpg"
CROSSREF = "https://api.crossref.org/prefixes/10.4271/works"

# A token of a designation: capitals and digits ("EN", "ISO/TS", "60079-28", "+A1"), a token with a digit
# that may hold small letters ("60086-1:2025/prAA:2026"), or the edition mark "ed.".
_TOKEN = re.compile(r"^(?:[A-Z0-9/\-:.+]+|[A-Za-z0-9/\-:.+]*\d[A-Za-z0-9/\-:.+]*|ed\.)$")
_NOISE_LINE = re.compile(r"^(?:\d+|Věstník č\. \d+/\d{4})$")


# --- designations and keys ---------------------------------------------------------

def designation(text, prefix="ČSN"):
    """The designation at the start of `text` ("ČSN EN 60204-1 ed. 3 Bezpečnost …" →
    "ČSN EN 60204-1 ed. 3"): the prefix and the following tokens without small letters."""
    words = text.split()
    if not words or words[0] != prefix:
        return None
    taken = [words[0]]
    for word in words[1:]:
        if not _TOKEN.match(word):
            break
        taken.append(word)
    return " ".join(taken)


def base(designation_text):
    """The designation without the years of its editions ("prEN IEC 60079-101:2026" →
    "prEN IEC 60079-101"), as it is keyed."""
    return re.sub(r":\d{4}(?=$|[/ +])", "", designation_text or "")


def norm_key(designation_text):
    return harvest.norm_key(base(designation_text))


def norm_tier(title, revises_known=False):
    if revises_known or harvest.matches(title):
        return 1
    if harvest.matches(title, broader=True):
        return 2
    return None


# --- Věstník ÚNMZ ---------------------------------------------------------------------

def _clean(lines):
    return [line for line in lines if not _NOISE_LINE.match(line.strip())]


def parse_entries(text):
    """[{section, designation, klass, title, catalog, issued, effective, withdrawn,
    replaced}] of the numbered ČSN entries of the notice on ČSN and of the European
    standards approved for direct use."""
    entries, section, block = [], None, None

    def close():
        if block is not None and section in PUBLISHED + CHANGED + WITHDRAWN:
            entries.append(_entry(section, " ".join(_clean(block)).strip()))
    for line in text.splitlines():
        stripped = line.strip()
        if stripped in SECTIONS or re.match(r"^OZNÁMENÍ č\.", stripped):
            close()
            block = None
            section = stripped if stripped in SECTIONS else None
            continue
        m = re.match(r"^\d+\.\s+(ČSN\b.*)$", stripped)
        if m and section in PUBLISHED + CHANGED + WITHDRAWN:
            close()
            block = [m.group(1)]
        elif block is not None:
            block.append(stripped)
    close()
    return entries


def _entry(section, text):
    main, _, replaced_text = text.partition("K datu její účinnosti se zrušuje")
    name = designation(main) or ""
    body = main[len(name):]
    klass = re.search(r"\((\d{2} \d{4})\)", body)
    catalog = re.search(r"kat\. č\. (\d+)", body)
    title = re.sub(r"\(\d{2} \d{4}\)|kat\. č\. \d+", " ", body)
    title = re.sub(r"\s+", " ", title.split(";")[0]).strip()
    replaced = [designation(replaced_text[m.start():]) for m in re.finditer(r"ČSN\b", replaced_text)]
    find = lambda pattern: (re.search(pattern, text) or [None, None])[1]  # noqa: E731
    return {"section": section, "designation": name, "klass": klass.group(1) if klass else None, "title": title,
            "catalog": catalog.group(1) if catalog else None,
            "issued": (re.search(r"Vydání: ([^;(]+?)\s*(?:;|\(|$)", main) or [None, None])[1],
            "effective": find(r"Účinnost od (\d{4}-\d{2}-\d{2})"), "withdrawn": find(r"Zrušena k (\d{4}-\d{2}-\d{2})"),
            "replaced": sorted({r for r in replaced if r and r != name})}


def parse_enquiry(text):
    """[{designation, title, committee, deadline}] of the prEN in public enquiry."""
    start = text.find(ENQUIRY)
    if start < 0:
        return []
    end = text.find("OZNÁMENÍ č.", start)
    found, current = [], None
    for line in _clean(text[start:end if end > 0 else None].splitlines()):
        line = line.strip()
        first = line.split()[0] if line else ""
        # a draft standard (prEN …) or a draft amendment of a standard (EN …:2024/prA1:2026)
        starts = re.match(r"^(?:F?prEN|prCEN|prETS|prTS)$", first) or (
            first in ("EN", "CEN", "CLC", "HD") and "/pr" in (designation(line, first) or ""))
        if starts:
            if current:
                found.append(current)
            name = designation(line, first)
            rest = line.split(None, len(name.split()))[-1] if len(line.split()) > len(name.split()) else ""
            committee = re.search(r"((?:CEN|CLC|CEN/CLC)/(?:TC|JTC|SS|SR|BT) ?\w+|ETSI\b\S*)", rest)
            deadline = re.search(r"(\d{4}-\d{2}-\d{2})\s*$", rest)
            title = rest[:committee.start()] if committee else rest
            current = {"designation": name, "title": title.strip(), "committee": committee.group(1) if committee else None,
                       "deadline": deadline.group(1) if deadline else None}
        elif current and line and not line.startswith(("Označení", "Údaje", "v období", "CEN", "CENELEC", "ETSI")):
            current["title"] += " " + re.sub(r"\s*\((?:ISO|IEC)/[^)]*\)?", "", line)
    if current:
        found.append(current)
    for item in found:
        title = re.sub(r"\s+", " ", item["title"]).split(" Vydání:")[0]  # the last entry runs into the next part
        item["title"] = re.sub(r"\s*\((?:ISO|IEC)/(?:DIS|FDIS|CD)[^)]*\)", "", title).strip()
    return found


def parse_tasks(pdf):
    """[{task, title, adopts}] of the notice on ČSN drafting tasks started, read from
    the columns left of "Termíny" (the right columns hold the drafters' addresses). The
    notice starts on the page with its title and the header "Termíny"; the following
    pages continue the table without the header, up to the next notice."""
    tasks, cut, current = [], None, None
    for page in pdf.pages:
        text = page.extract_text() or ""
        if cut is None:
            if TASKS_NOTICE not in text or "Termíny" not in text:
                continue
            cut = next(w["x0"] for w in page.extract_words() if w["text"] == "Termíny") - 1
        elif not re.search(r"\d{2}/\d{4}/\d{2}", text):
            break
        ended = False
        for line in _clean((page.crop((0, 0, cut, page.height)).extract_text() or "").splitlines()):
            line = line.strip()
            if re.match(r"^OZNÁMENÍ č\. \d+/\d+", line) and tasks:
                ended = True
                break
            m = re.match(r"^(\d{2}/\d{4}/\d{2})\s+(.*)$", line)
            if m:
                current = {"task": m.group(1), "title": m.group(2), "adopts": "", "in_documents": False}
                tasks.append(current)
            elif current:
                if line.startswith("Přejímané mezinárodní dokumenty:"):
                    current["in_documents"] = True
                    line = line.split(":", 1)[1]
                line = re.sub(r"TNK:\s*(?:\d+|-)\s*", "", line).strip()
                if current["in_documents"]:
                    current["adopts"] += " " + line
                elif line:
                    current["title"] += " " + line
        if ended:
            break
    for task in tasks:
        task["title"] = re.sub(r"\s+", " ", task["title"]).strip()
        task["adopts"] = sorted(set(re.findall(r"\b(?:EN|ISO|IEC)(?: [A-Z/]+)* [\d\-]+(?:/A\d+)?(?::\d{4})?", task["adopts"])))
        del task["in_documents"]
    return tasks


def _issues(today):
    year, month = today.year, today.month
    for _ in range(VESTNIK_MONTHS):
        yield month, year % 100
        month, year = (12, year - 1) if month == 1 else (month - 1, year)


def vestnik_findings(entry, text, pdf, issue, context):
    known, findings = context["known"], []
    source = entry["id"]
    for item in parse_entries(text):
        key = norm_key(item["designation"])
        if not key:
            continue
        common = {"source": "vestnik-unmz", "issue": issue, "catalog_number": item["catalog"]}
        if item["section"] in WITHDRAWN:
            if key in known:
                findings.append(Finding(source, "state_change", item["designation"], key=key,
                                        state={**common, "status": "zrušená", "withdrawn": item["withdrawn"]}))
            continue
        if item["section"] in CHANGED:
            if key in known:
                findings.append(Finding(source, "state_change", item["designation"], key=key,
                                        state={**common, "status": "platná", "last_change": item["section"].split()[0].lower(),
                                               "change_issued": item["issued"]}))
            continue
        replaced_known = [r for r in item["replaced"] if norm_key(r) in known and norm_key(r) != key]
        for old in replaced_known:
            findings.append(Finding(source, "state_change", old, key=norm_key(old),
                                    state={**common, "status": "nahrazená", "replaced_by": item["designation"]}))
        if key in known:
            findings.append(Finding(source, "state_change", item["designation"], key=key,
                                    state={**common, "status": "platná",
                                           "edition": item["issued"] or item["effective"]}))
            continue
        tier = norm_tier(item["title"], bool(replaced_known))
        if tier:
            findings.append(Finding(source, "new_document", item["title"], key=key, native_id=key,
                                    designation=item["designation"], document_type="Norma", tier=tier,
                                    url=CSN_DETAIL.format(item["catalog"]) if item["catalog"] else None,
                                    language="CS", jurisdikce="CZ", date=item["effective"],
                                    excerpt=f"Věstník ÚNMZ {issue}: {item['section'].lower()}; vydání {item['issued'] or '—'}"
                                    + (f"; nahrazuje {', '.join(item['replaced'])}" if item["replaced"] else "")))
    for item in parse_enquiry(text):
        target = norm_key(re.sub(r"/pr\w+.*$", "", re.sub(r"^F?pr", "", item["designation"])))
        revises = target in known
        tier = norm_tier(item["title"], revises)
        if not tier:
            continue
        extra = {"revises": target, "amends_ids": _ids(target, context)} if revises else None
        findings.append(Finding(source, "draft", item["title"], key=f"DRAFT-NORM:{base(item['designation'])}",
                                native_id=item["designation"], designation=item["designation"], document_type="Norma",
                                tier=tier, language="EN", jurisdikce="EU", extra=extra,
                                excerpt=f"Věstník ÚNMZ {issue}: veřejné projednání, {item['committee'] or ''}, "
                                        f"lhůta {item['deadline'] or '—'}"))
    for task in (parse_tasks(pdf) if pdf is not None else []):
        targets = [norm_key(a.split(":")[0]) for a in task["adopts"]]
        revises = [t for t in targets if t in known]
        tier = norm_tier(task["title"], bool(revises))
        if not tier:
            continue
        extra = {"adopts": task["adopts"]}
        if revises:
            extra.update(revises=revises[0], amends_ids=_ids(revises[0], context))
        findings.append(Finding(source, "draft", task["title"], key=f"DRAFT-NORM:CZ:{task['task']}",
                                native_id=task["task"], document_type="Norma", tier=tier, language="CS",
                                jurisdikce="CZ", extra=extra,
                                excerpt=f"Věstník ÚNMZ {issue}: zahájení zpracování návrhu ČSN, úkol {task['task']}"
                                        + (f"; přejímá {', '.join(task['adopts'])}" if task["adopts"] else "")))
    return findings


def _ids(key, context):
    import citation_closure as cc
    return sorted(doc_id for doc_id, identifier, title, _url in context.get("documents", [])
                  if key in cc.own_keys(identifier, title) or harvest.norm_key(identifier or "") == key)


def vestnik_unmz(entry, session, since, context):
    import pdfplumber
    today = datetime.date.fromisoformat(context["today"])
    findings, read = [], []
    for month, yy in _issues(today):
        if len(read) == VESTNIK_ISSUES:
            break
        url = VESTNIK.format(month=month, yy=yy)
        response = session.get(url, timeout=120)
        time.sleep(1)
        if response.status_code == 404 or not response.content.startswith(b"%PDF"):
            continue
        response.raise_for_status()
        with pdfplumber.open(io.BytesIO(response.content)) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
            findings += vestnik_findings(entry, text, pdf, f"{month}/{yy:02d}", context)
        read.append(url)
    if not read:
        raise RuntimeError("no issue of Věstník ÚNMZ found for the last months")
    return findings


# --- harmonised standards ---------------------------------------------------------------

def parse_summary_list(rows):
    """[{directive, reference, designation, title, start, end}] of a summary list (rows of
    the XLSX as tuples)."""
    header = next((i for i, r in enumerate(rows) if r and "Reference and title" in " ".join(str(c) for c in r if c)), None)
    if header is None:
        raise ValueError("no header row in the summary list")
    names = [str(c or "").split(" Provision")[0].strip() for c in rows[header]]
    col = {name: names.index(name) for name in names if name}
    found = []
    for r in rows[header + 1:]:
        cell = r[col["Reference and title"]] if len(r) > col["Reference and title"] else None
        if not cell:
            continue
        reference, _, title = str(cell).partition("\n")
        found.append({"directive": str(r[col["Legislation"]] or ""), "reference": reference.strip(),
                      "designation": re.sub(r":\d{4}.*$", "", reference.strip()), "title": " ".join(title.split()),
                      "start": r[col["Start of legal effect"]] or None, "end": r[col["End of legal effect"]] or None})
    return found


def harmonised_standards(entry, session, since, context):
    import openpyxl
    known, by_key, without = context["known"], {}, []
    for slug in DIRECTIVES:
        page = session.get(HARMONISED_BASE.format(slug), timeout=60)
        page.raise_for_status()
        link = re.search(r'href="([^"]+\.xlsx[^"]*)"', page.text)
        time.sleep(1)
        if not link:  # 2026-11-04: simple pressure vessels have the summary list as PDF only
            without.append(slug)
            continue
        data = session.get(urllib.parse.urljoin(page.url or HARMONISED_BASE.format(slug),
                                                link.group(1).replace("&amp;", "&")), timeout=120)
        data.raise_for_status()
        time.sleep(1)
        workbook = openpyxl.load_workbook(io.BytesIO(data.content), read_only=True)
        for item in parse_summary_list(list(workbook.worksheets[0].iter_rows(values_only=True))):
            key = norm_key(item["designation"])
            if key:
                by_key.setdefault(key, []).append(item)
    if len(without) == len(DIRECTIVES):
        raise RuntimeError("no summary list (XLSX) on any page of the directives")
    findings = []
    for key, items in sorted(by_key.items()):
        current = [i for i in items if not i["end"]]
        if key in known:
            findings.append(Finding(entry["id"], "state_change", items[0]["designation"], key=key,
                                    state={"source": "ec-harmonised-standards", "harmonised": [
                                        {"directive": i["directive"], "reference": i["reference"], "start": i["start"],
                                         "end": i["end"]} for i in items]}))
        elif current and harvest.matches(current[-1]["title"]):
            item = current[-1]
            findings.append(Finding(entry["id"], "new_document", item["title"], key=key, native_id=key,
                                    designation=item["reference"], document_type="Norma", tier=1, language="EN",
                                    jurisdikce="EU", excerpt=f"harmonizovaná norma: {item['directive']}, od {item['start']}"))
    return findings


# --- TPG ------------------------------------------------------------------------------------

_TPG = re.compile(r"^(TPG|TDG|TIN) \d{3} \d{2}(?: \S+)?$")


def parse_tpg(html):
    """[{designation, title, approved, valid_from, note}] of a TPG catalogue page."""
    cells = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).strip()
             for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", html, re.S)]
    found, i = [], 0
    while i < len(cells):
        if _TPG.match(cells[i]):
            dates, note, j = [], None, i + 2
            while j < len(cells) and not _TPG.match(cells[j]):
                if re.match(r"^\d{1,2}\. ?\d{1,2}\. ?\d{4}$", cells[j]):
                    dates.append(cells[j])
                elif cells[j].startswith(("nahrazen", "zrušen")):
                    note = cells[j]
                j += 1
            title = cells[i + 1] if i + 1 < len(cells) else ""
            title = re.sub(r"\s*\((?:nahrazuj|mění|ruší)[^)]*\)?\s*$", "", title)  # "(nahrazují TPG … schválená …)"
            title = title[len(cells[i]):].strip() if title.startswith(cells[i]) else title
            found.append({"designation": cells[i], "title": title,
                          "approved": dates[0] if dates else None, "valid_from": dates[1] if len(dates) > 1 else None,
                          "note": note})
            i = j
        else:
            i += 1
    return found


def cps_tpg(entry, session, since, context):
    known, findings = context["known"], []
    pages = {}
    for name, url in (("valid", TPG_VALID), ("invalid", TPG_INVALID)):
        response = session.get(url, timeout=60)
        response.raise_for_status()
        pages[name] = parse_tpg(response.text)
        time.sleep(1)
    if not pages["valid"]:
        raise RuntimeError("no TPG found in the catalogue (has the page changed?)")
    for item in pages["valid"]:
        key = norm_key(item["designation"])
        if key in known:
            findings.append(Finding(entry["id"], "state_change", item["designation"], key=key,
                                    state={"source": "cps-tpg", "status": "platná", "approved": item["approved"],
                                           "valid_from": item["valid_from"]}))
            continue
        findings.append(Finding(entry["id"], "new_document", f"{item['designation']} {item['title']}", key=key,
                                native_id=key, designation=item["designation"], document_type="Norma",
                                tier=1 if harvest.matches(item["title"]) else 2, url=TPG_VALID, language="CS",
                                jurisdikce="CZ", excerpt=f"schváleno {item['approved'] or '—'}, platnost od {item['valid_from'] or '—'}"))
    valid = {norm_key(i["designation"]) for i in pages["valid"]}
    for item in pages["invalid"]:
        key = norm_key(item["designation"])
        if key in known and key not in valid:
            findings.append(Finding(entry["id"], "state_change", item["designation"], key=key,
                                    state={"source": "cps-tpg", "status": "zrušená", "note": item["note"]}))
    return findings


# --- SAE (Crossref) ---------------------------------------------------------------------------

# Hydrogen as a materials problem (embrittlement, plating), not as an energy carrier.
SAE_OFF_TOPIC = re.compile(r"embrittlement|plating|cadmium|zinc|electrodeposit", re.IGNORECASE)


def sae_designation(doi):
    """"10.4271/j2601_202005" → "SAE J2601"; the date suffix and the revision letters of
    a revision ("ams2401k" → "SAE AMS2401") are dropped, so revisions share one key."""
    suffix = re.sub(r"_\d{6}$", "", doi.split("/", 1)[1]).upper()
    suffix = re.sub(r"^([A-Z]+\d+(?:-\d+)?)[A-Z]{1,2}$", r"\1", suffix)
    return "SAE " + suffix


def sae_crossref(entry, session, since, context):
    response = session.get(CROSSREF, params={"filter": "type:standard", "query.bibliographic": "hydrogen",
                                             "rows": 500}, timeout=60)
    response.raise_for_status()
    message = response.json()["message"]
    if message["total-results"] > len(message["items"]):
        raise RuntimeError(f"{message['total-results']} results, only {len(message['items'])} read")
    findings, seen = [], set()
    for work in message["items"]:
        title = " ".join((work.get("title") or [""])[0].split())
        name = sae_designation(work["DOI"])
        key = norm_key(name)
        if key in seen or key in context["known"] or not harvest.matches(title) or SAE_OFF_TOPIC.search(title):
            continue
        seen.add(key)
        # ground-vehicle standards (J) are the scope of the database; aerospace and other series are tier 2
        tier = 1 if re.match(r"SAE J\d", name) else 2
        findings.append(Finding(entry["id"], "new_document", title, key=key, native_id=key, designation=name,
                                document_type="Norma", tier=tier, url=work.get("URL"), language="EN",
                                jurisdikce="international", excerpt=f"DOI {work['DOI']}"))
    return findings


# --- news feeds ------------------------------------------------------------------------------

def rss_items(entry, session, since, context, broader=False):
    """Items of a news feed (`access.feed`, else `access.endpoint`) whose title or description has a basic
    search term (tier 1); with `broader`, also those with a broader one (tier 2). News of
    an authority whose own agenda a broader term names (metrology at ÚNMZ) would all
    match it, so feeds take the basic terms only by default."""
    import harvest_drafts as hd
    response = session.get(entry["access"].get("feed") or entry["access"]["endpoint"], timeout=60)
    response.raise_for_status()
    findings = []
    for item in hd.parse_rss(response.content):
        text = f"{item['title']} {item['description']}"
        tier = 1 if harvest.matches(text) else 2 if broader and harvest.matches(text, broader=True) else None
        if tier is None or not item["link"]:
            continue
        findings.append(Finding(entry["id"], "new_document", item["title"], url=item["link"].strip(),
                                native_id=item["guid"] or None, tier=tier, date=item["date"],
                                language="CS" if entry["jurisdiction"] == "CZ" else None,
                                jurisdikce=entry["jurisdiction"] if entry["jurisdiction"] in ("CZ", "EU") else None,
                                excerpt=item["description"][:300]))
    return findings
