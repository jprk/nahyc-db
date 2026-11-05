"""Adapters of stage E6 (doc/DATA_SOURCES.md, odstavec 4.3): three registers of the
European Commission that are applications rendered in the browser. None of them is
behind a protection against robots and robots.txt allows them; the adapters call the
JSON interfaces the applications themselves call (found 2026-11-05 by loading each
application once in a headless browser), the way they call them — with the session
and its CSRF token where the application uses one.

* comitology_documents — the comitology register: documents of the committees (above
  all draft implementing acts), the newest REGISTER_SIZE by creation date (about four
  weeks), kept when the title or the committee names hydrogen and the title is not one
  of the chemical false positives of EUR-Lex (hydrogen peroxide biocides, …).
* delegated_acts — the register of delegated acts: acts found for "hydrogen", "RFNBO"
  and "non-biological origin" that are not yet published (planned, in consultation,
  adopted and under scrutiny) are drafts in tier 1.
* commission_documents — the register of Commission documents: COM and C documents of
  the last COMMISSION_DAYS days whose title names hydrogen; tier 2, as EUR-Lex and the
  Legislative Observatory follow the proposals and acts as well.
"""
import datetime
import re
import time

import harvest
from harvest import Finding

COMITOLOGY_SEARCH = "https://ec.europa.eu/transparency/comitology-register/core/api/front/documents/search"
COMITOLOGY_DOCUMENT = "https://ec.europa.eu/transparency/comitology-register/screen/documents/{}/{}/consult?lang=en"
REGISTER_SIZE = 500
REGDEL = "https://webgate.ec.europa.eu/regdel/"
REGDEL_TERMS = ("hydrogen", "RFNBO", "non-biological origin")
DOCUMENTS_SEARCH = "https://ec.europa.eu/transparency/documents-register/api/groupSearch"
COMMISSION_DAYS = 90
COMMISSION_TYPES = ("COM", "C")
DOCUMENTS_PAGES = 10


def _off_topic(title):
    from add_eurlex_hydrogen_acts import is_off_topic
    return is_off_topic(title)


def comitology_documents(entry, session, since, context):
    response = session.post(COMITOLOGY_SEARCH, params={"page": 0, "size": REGISTER_SIZE, "sort": "creationDate,desc"},
                            json={"reset": False}, timeout=120)
    response.raise_for_status()
    findings = []
    for doc in response.json()["content"]:
        title = " ".join((doc.get("title") or "").split())
        if not harvest.matches(f"{title} {doc.get('committeeTitle', '')}") or _off_topic(title):
            continue
        kind = (doc.get("documentType") or {}).get("label", "").replace("label.", "").replace("_", " ")
        signal = "draft" if "draft" in kind else "new_document"
        ref = doc["documentReference"]
        findings.append(Finding(entry["id"], signal, title, key=f"DRAFT-EU:comitology:{ref}" if signal == "draft" else None,
                                native_id=ref, url=COMITOLOGY_DOCUMENT.format(ref, doc.get("version", 1)),
                                tier=1 if signal == "draft" else 2, date=(doc.get("creationDate") or "")[:10] or None,
                                language="EN", jurisdikce="EU",
                                excerpt=f"Komitologie {doc.get('meetingCode') or ''}: {kind}; výbor {doc.get('committeeTitle')}"))
    return findings


def _regdel_session(session):
    """The register expects the session of its page and the CSRF token it sets."""
    session.get(REGDEL + "web/security/status", timeout=60).raise_for_status()
    token = session.cookies.get("XSRF-TOKEN")
    if not token:
        raise RuntimeError("the register of delegated acts set no CSRF token")
    return {"X-XSRF-TOKEN": token}


def delegated_acts(entry, session, since, context):
    headers = _regdel_session(session)
    seen, findings = set(), []
    for term in REGDEL_TERMS:
        body = {"rowsPerPage": 200, "firstRowOffset": 0, "startDate": None, "endDate": None, "basicActList": [],
                "policyAreaList": [], "authorList": [], "statusIdList": [], "typeOfActIdList": [], "phaseIdList": [],
                "eventTypeList": [], "sourceList": [], "privacyList": [], "keywordList": [], "expertGroupIds": [],
                "agencyIdList": [], "committeesRoleList": [], "committeesNameCodeList": [], "language": "en",
                "simpleSearchName": term}
        response = session.post(REGDEL + "web/delegatedActs", json=body, headers=headers, timeout=60)
        response.raise_for_status()
        for act in response.json().get("list", []):
            if act["id"] in seen or act.get("delegatedActStatus") == "PUBLISHED":
                continue
            seen.add(act["id"])
            title = " ".join((act.get("completeTitle") or act.get("shortTitle") or "").split())
            findings.append(Finding(entry["id"], "draft", title, key=f"DRAFT-EU:regdel:{act['id']}",
                                    native_id=str(act["id"]), url=f"{REGDEL}#/delegatedActs/{act['id']}", tier=1,
                                    language="EN", jurisdikce="EU",
                                    excerpt=f"Akt v přenesené pravomoci {act.get('cCode') or ''}, stav "
                                            f"{act.get('delegatedActStatus')}; základní akt "
                                            f"{(act.get('basicAct') or {}).get('code', '—')}"))
        time.sleep(1)
    return findings


def _document_title(doc):
    for attachment in doc.get("attachments") or []:
        for version in (attachment.get("linguisticVersions") or {}).values():
            if version.get("title"):
                return " ".join(version["title"].split())
    return doc.get("title") or doc.get("reference")


def commission_documents(entry, session, since, context):
    oldest = (datetime.date.fromisoformat(context["today"]) - datetime.timedelta(days=COMMISSION_DAYS)).isoformat()
    findings = []
    for page in range(1, DOCUMENTS_PAGES + 1):
        body = {"categories": [], "types": [], "departments": [], "language": "en",
                "keywordsSearchType": "AT_LEAST_ONE", "target": "TITLE_AND_CONTENT", "sortBy": "DOCUMENT_DATE_DESC",
                "isRegular": True, "keywords": "hydrogen", "reference": "", "page": page}
        response = session.post(DOCUMENTS_SEARCH, params={"size": 50, "page": page}, json=body, timeout=90)
        response.raise_for_status()
        documents = response.json().get("documents", [])
        for doc in documents:
            date = (doc.get("date") or "")[:10]
            title = _document_title(doc)
            if date < oldest or doc.get("category") not in COMMISSION_TYPES or not harvest.matches(title) \
                    or _off_topic(title):
                continue
            signal = "draft" if doc.get("category") == "COM" else "new_document"
            findings.append(Finding(entry["id"], signal, title[:300], key=f"DRAFT-EU:comdoc:{doc['reference']}"
                                    if signal == "draft" else None, native_id=doc["reference"], url=doc.get("url"),
                                    tier=2, date=date, language="EN", jurisdikce="EU",
                                    excerpt=f"Registr dokumentů Komise {doc['reference']} ({doc.get('responsibleDepartment')})"))
        if not documents or (documents[-1].get("date") or "")[:10] < oldest:
            break
        time.sleep(1)
    return findings
