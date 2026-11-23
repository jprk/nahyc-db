"""ISO Open Data: the metadata of every ISO deliverable (doc/KLICOVA_SLOVA.md, doc/KONTROLA_ZAZNAMU.md).

The web pages of iso.org refuse automated clients (HTTP 403), but ISO publishes the
metadata of all its deliverables as open data, a JSON Lines file on its own storage
(https://www.iso.org/open-data.html, about 80 MB, refreshed weekly): reference,
English and French title, ICS codes, scope (abstract), technical committee, stage,
publication date and the editions it replaces or is replaced by.

    path = iso_open_data.download()            # data/external/, not in git
    index = iso_open_data.load_index(path)
    iso_open_data.lookup(index, "ISO 19880-1")  # the current edition

`lookup()` resolves a designation without a year to the current published edition
(stage 60.60 to 90.99), else to the latest one; a draft designation ("ISO/DIS 19884") to the
project under that reference.
"""
import json
import pathlib
import re
import urllib.request

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
URL = ("https://isopublicstorageprod.blob.core.windows.net/opendata/_latest/"
       "iso_deliverables_metadata/json/iso_deliverables_metadata.jsonl")
DEFAULT_PATH = REPO_ROOT / "data" / "external" / "iso_deliverables_metadata.jsonl"
PUBLISHED = 6060  # stage 60.60, International Standard published
WITHDRAWN = 9599  # stage 95.99; 90.xx (under review, confirmed) are published editions in force
_DRAFT = re.compile(r"^ISO/(?:AWI|PWI|NP|WD|CD|DIS|FDIS|PRF)\s+(?:(TS|TR|PAS)\s+)?", re.I)


def download(path=DEFAULT_PATH, url=URL):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with urllib.request.urlopen(url, timeout=600) as response, open(tmp, "wb") as out:
        while chunk := response.read(1 << 20):
            out.write(chunk)
    tmp.replace(path)
    return path


def base_reference(reference):
    """"ISO 19880-1:2020/Amd 1:2023" -> "ISO 19880-1"; "ISO/IEC 27001:2022" -> "ISO/IEC 27001";
    a note or an edition date of our designations ("ISO 19884 (súbor)", "ISO 11326/ - 2024.011") goes."""
    ref = re.sub(r"\s+", " ", (reference or "").strip())
    ref = re.sub(r"\s*\([^)]*\)\s*$", "", ref)
    ref = re.sub(r"\s*/?\s*[-–—]\s*(19|20)\d{2}(\.\d+)?\s*$", "", ref)
    ref = ref.split("/Amd")[0].split("/Cor")[0].split("/DAmd")[0]
    ref = re.sub(r":\s*\d{4}(-\d{2})?$", "", ref)
    return ref.strip().upper()


def _number(reference):
    """The kind and number of a base reference without its stage: "ISO/AWI TR 19884-2" -> ("TR", "19884-2")."""
    m = re.match(r"^ISO(?:/IEC)?(?:/(?:AWI|PWI|NP|WD|CD|DIS|FDIS|PRF))?(?:[/ ](TS|TR|PAS|IWA))?\s+(\S+)$", reference)
    return (m.group(1) or "", m.group(2)) if m else None


def load_index(path=DEFAULT_PATH):
    """{base reference: [records]} of the deliverables that are not an amendment or corrigendum;
    under `(kind, number)` keys too, so that "ISO 19885-2" finds the project "ISO/AWI 19885-2"."""
    index = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)
            reference = record.get("reference") or ""
            if record.get("supplementType") or re.search(r"/(Amd|Cor|DAmd)", reference):
                continue
            base = base_reference(reference)
            index.setdefault(base, []).append(record)
            number = _number(base)
            if number:
                index.setdefault(number, []).append(record)
    return index


def _rank(record):
    stage = record.get("currentStage") or 0
    published = PUBLISHED <= stage < WITHDRAWN
    return (published, record.get("publicationDate") or "", record.get("currentStage") or 0)


def lookup(index, designation):
    """The record a designation stands for, or None."""
    key = base_reference(designation)
    candidates = index.get(key)
    draft = _DRAFT.match(key)
    if not candidates and draft:  # "ISO/DIS TR 19884" is listed as "ISO/TR 19884" once published
        kind = draft.group(1)
        candidates = index.get(f"ISO/{kind.upper()} {key[draft.end():]}" if kind else f"ISO {key[draft.end():]}")
    if not candidates and _number(key):
        candidates = index.get(_number(key))
    if not candidates:
        return None
    return max(candidates, key=_rank)


def summary(record):
    """The fields the database uses, from an ISO record."""
    return {"reference": record.get("reference"), "iso_id": record.get("id"),
            "title_en": (record.get("title") or {}).get("en"), "ics": record.get("icsCode") or [],
            "committee": record.get("ownerCommittee"), "stage": record.get("currentStage"),
            "published": record.get("publicationDate"),
            "url": f"https://www.iso.org/standard/{record.get('id')}.html"}
