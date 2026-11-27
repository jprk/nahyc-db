"""Edition and effect of the versions of Czech and EU legal acts (issue #38).

Every Czech act (`N/RRRR Sb.`) and EU act (directive, regulation, decision) in the
database gets, on its versions (`DocumentVersion`):

* `edition_label` — which text the version is: "původní znění", "znění účinné od
  01.08.2025" (a Czech consolidated version), "konsolidované znění ke dni 01.07.2026"
  (an EU one);
* `effective_date` — the day the version takes effect (ISO date);
* `url` — the version's page at the publisher: e-Sbírka for a Czech act
  (`https://e-sbirka.gov.cz/sb/2001/100/2025-08-01`), EUR-Lex for an EU one.

`Document.effective_date` ("Platnost od"), when empty, gets the day an EU act entered
into force (Cellar: "24.12.2018") or the day a Czech act took effect, marked so
("20.03.2001 (účinnost)": e-Sbírka's open data do not give the day of promulgation).

**Versions from the day the document came into the database** (decision of the
garant, issue #38): the history of an act before that day is in its sources and
is not copied. The first check of an act stores in data/act_versions_cache.json
the day it saw the act (`since`, the day its stored text was downloaded, otherwise
the day of the check) and the versions the source had up to that day (`known`).
The version that applied on `since` describes the text the database already has
(the baseline: the existing version of the document, its fields filled only where
empty, so an editor's values stay); every version the source adds later becomes a
new `DocumentVersion` — in effect today: the current one (`active`), the previous
ones `superseded`; prepared ahead of its date: `promulgated`.

The baseline of an EU act is its original text, the one the database downloaded
(EUR-Lex, the published act): consolidated versions dated up to `since` are not
the stored text and are left out; later ones are added like those of CLP and REACH
(eu_consolidations.py, which keeps those two acts with their whole history; they
are left out here).

**Texts.** Every version the database keeps has its text (issue #38): the baseline
has the text stored before; a later version in effect is downloaded by
refresh_act_versions.py (fetch_fulltext.py) under the manifest field
`zneni_<YYYYMMDD>` (Czech, from the act's page on zakonyprolidi.cz, which shows the
version in effect on the day of the download) or `konsolidace_<YYYYMMDD>` (EU, from
Cellar). The document shows the newest version in effect that has a text.

A repealed act (check_validity.py) gets its baseline filled and nothing else.
Slovak acts are not covered (no source of versions yet).

apply() works from the cache, data/validity_cache.json (the CELEX numbers) and the
manifest only — init_db.py (a rebuild) and backfill_document_states.py run it
without network; refresh_act_versions.py asks the sources and fills the cache.
"""
import datetime
import json
import pathlib
import re

import citation_closure as cc
import eu_consolidations as ec
import state_paths

CACHE_PATH = state_paths.data_file("act_versions_cache.json")
VALIDITY_CACHE_PATH = state_paths.data_file("validity_cache.json")

CZ_FIELD_PREFIX = "zneni_"
EU_FIELD_PREFIX = ec.FIELD_PREFIX
CZ_LABEL_PREFIX = "znění účinné od "
ORIGINAL_LABEL = "původní znění"
LEGAL_TYPES = ("Zákon", "Vyhláška", "Nařízení vlády", "Směrnice EU", "Nařízení EU", "Rozhodnutí EU")
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_COMPARED = ("edition_label", "effective_date", "url", "file_path", "is_current", "lifecycle_state")


def load_cache(path=CACHE_PATH):
    path = pathlib.Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def save_cache(cache, path=CACHE_PATH):
    """One line per act (a small diff when an act gets a new version)."""
    lines = [f" {json.dumps(k, ensure_ascii=False)}: {json.dumps(v, ensure_ascii=False)}"
             for k, v in sorted(cache.items())]
    pathlib.Path(path).write_text("{\n" + ",\n".join(lines) + "\n}\n", encoding="utf-8")


def load_validity(path=VALIDITY_CACHE_PATH):
    path = pathlib.Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


# --- which documents ---------------------------------------------------------------

def act_of(identifier, title, language, validity, excluded=()):
    """{"family", "key", ...} of a document that is a Czech or EU act, or None.
    Czech: one key `CZ:n/y`, a Czech document. EU: one key `EU:y/n` whose CELEX
    number the validity check found (data/validity_cache.json)."""
    identifier = (identifier or "").strip()
    if not identifier or identifier in excluded:
        return None
    keys = cc.own_keys(identifier, title)
    if len(keys) != 1:
        return None
    key = next(iter(keys))
    family = key.split(":")[0]
    if family == "CZ" and (language or "CS").upper() == "CS" and "[" not in identifier:
        number, year = key.split(":")[1].split("/")
        return {"family": "CZ", "key": key, "number": int(number), "year": int(year)}
    if family == "EU":
        celex = (validity.get(key) or {}).get("celex")
        if celex:
            return {"family": "EU", "key": key, "celex": celex, "language": (language or "CS").upper()}
    return None


def czech_date(iso):
    return ec.czech_date(iso)


def esbirka_page(number, year, date=None):
    return f"https://e-sbirka.gov.cz/sb/{year}/{number}" + (f"/{date}" if date else "")


def zakony_page(number, year):
    return f"https://www.zakonyprolidi.cz/cs/{year}-{number}"


def field_of(family, date):
    return (CZ_FIELD_PREFIX if family == "CZ" else EU_FIELD_PREFIX) + date.replace("-", "")


# --- the cache: what the sources said ------------------------------------------------

def record_check(cache, identifier, act, found, since, today):
    """Stores in `cache` (in place) what a source said of an act on `today`. `found` =
    {"first_effective": date, "versions": [{"id", "date"}]} (Czech: ids are the dates
    of the versions; EU: the CELEX numbers of the consolidated versions). The first
    check of an act also stores `since` and the versions known up to it; a later one
    never changes them. Returns the ids of the versions new since the previous check."""
    entry = cache.get(identifier)
    versions = sorted((v for v in found["versions"] if _ISO.match(v.get("date") or "")),
                      key=lambda v: (v["date"], v["id"]))
    if entry is None:
        entry = {"family": act["family"], "key": act["key"], "since": since,
                 "known": [v["id"] for v in versions if v["date"] <= since]}
        before = None
    else:
        before = {v["id"] for v in entry.get("versions", [])}
    entry.update({"first_effective": found.get("first_effective") or entry.get("first_effective"),
                  "versions": versions, "checked_at": today})
    if act["family"] == "EU":
        entry.update({"celex": act["celex"], "language": act["language"]})
    cache[identifier] = entry
    return [] if before is None else [v["id"] for v in versions if v["id"] not in before]


def baseline_date(entry):
    """The day the baseline version took effect: Czech — the newest version known at
    `since`; EU — the entry into force of the original act."""
    if entry["family"] == "EU":
        return entry.get("first_effective")
    known = set(entry.get("known", []))
    dates = [v["date"] for v in entry.get("versions", []) if v["id"] in known]
    return max(dates) if dates else entry.get("first_effective")


def later_versions(entry):
    """The versions the source added after `since`, oldest first."""
    known = set(entry.get("known", []))
    base = baseline_date(entry) or ""
    return [v for v in entry.get("versions", []) if v["id"] not in known and v["date"] > base]


def desired_versions(identifier, act, entry, manifest, today):
    """The versions the document of an act should have on `today`, oldest first
    (dicts like eu_consolidations.desired_versions(), with `field` of the text)."""
    base = baseline_date(entry)
    if act["family"] == "CZ":
        first = entry.get("first_effective")
        baseline = {"edition_label": ORIGINAL_LABEL if base and base == first
                    else (CZ_LABEL_PREFIX + czech_date(base) if base else None),
                    "effective_date": base,
                    "url": esbirka_page(act["number"], act["year"], base) if base else None}
    else:
        baseline = {"edition_label": ORIGINAL_LABEL, "effective_date": base,
                    "url": ec.eurlex_page(act["celex"], act["language"])}
    versions = [{"key": "baseline", "field": None, "file_path": None, **baseline}]
    for v in later_versions(entry):
        field = field_of(act["family"], v["date"])
        _key, found = ec.manifest_entry(manifest, identifier, field)
        if act["family"] == "CZ":
            label, url = CZ_LABEL_PREFIX + czech_date(v["date"]), esbirka_page(act["number"], act["year"], v["date"])
        else:
            label, url = ec.edition_label(v["date"]), ec.eurlex_page(v["id"], act["language"])
        versions.append({"key": v["id"], "field": field, "edition_label": label, "effective_date": v["date"],
                         "url": url, "file_path": found["local_path"] if found else None})
    applying = [v for v in versions[1:] if v["effective_date"] <= today]
    current = applying[-1] if applying else versions[0]
    for v in versions:
        v["is_current"] = v is current
        if v is not versions[0] and v["effective_date"] > today:
            v["lifecycle_state"] = "promulgated"
        else:
            v["lifecycle_state"] = "active" if v is current else "superseded"
    return versions


def in_effect_target(identifier, act, entry, today):
    """(field, address) of the later version in effect on `today`, or None (the
    baseline is in effect, or the act has no later version yet)."""
    applying = [v for v in later_versions(entry) if v["date"] <= today]
    if not applying:
        return None
    v = applying[-1]
    if act["family"] == "CZ":
        return field_of("CZ", v["date"]), zakony_page(act["number"], act["year"])
    return field_of("EU", v["date"]), ec.text_address(v["id"], act["language"])


# --- the database ------------------------------------------------------------------

def fetch_documents(cursor, validity, excluded):
    """{identifier: {"id", "file_path", "effective_date", "act", "versions"}} of the
    Czech and EU acts in the database (eu_consolidations.fetch_documents() shape)."""
    url = "dv.url" if ec.has_url_column(cursor) else "NULL"
    marks = ",".join(["%s"] * len(LEGAL_TYPES))
    cursor.execute(f"SELECT d.id, d.identifier, d.title, d.language, d.file_path, d.effective_date, dv.id, "
                   f"dv.version, dv.edition_label, dv.effective_date, {url}, dv.file_path, dv.is_current, "
                   f"dv.lifecycle_state FROM Document d JOIN DocumentType t ON t.id = d.type_id "
                   f"LEFT JOIN DocumentVersion dv ON dv.document_id = d.id "
                   f"WHERE t.name IN ({marks}) ORDER BY d.id, dv.version", LEGAL_TYPES)
    documents = {}
    for (doc_id, identifier, title, language, doc_file, doc_effective, version_id, version, label, effective,
         version_url, version_file, is_current, state) in ec._rows(cursor.fetchall()):
        act = act_of(identifier, title, language, validity, excluded)
        if act is None:
            continue
        doc = documents.setdefault(identifier.strip(), {"id": doc_id, "file_path": doc_file,
                                                        "effective_date": doc_effective, "act": act,
                                                        "versions": []})
        if version_id is not None:
            doc["versions"].append({"id": version_id, "version": version, "edition_label": label,
                                    "effective_date": effective, "url": version_url, "file_path": version_file,
                                    "is_current": bool(is_current), "lifecycle_state": state})
    return documents


def _changes(existing, wanted, keys):
    return {k: (existing.get(k), wanted[k]) for k in keys
            if (bool(existing.get(k)) if k == "is_current" else existing.get(k)) != wanted[k]}


def plan(documents, cache, manifest, today):
    """The changes for the acts of `documents` that the cache knows, in the actions of
    eu_consolidations.plan() (`add`, `update`, `file`), plus `effective` (document_id,
    old, new: `Document.effective_date`)."""
    actions = []
    for identifier, doc in sorted(documents.items()):
        entry = cache.get(identifier)
        if entry is None or entry.get("family") != doc["act"]["family"]:
            continue
        act = doc["act"]
        existing = sorted(doc["versions"], key=lambda v: v["version"])
        current = next((v for v in existing if v["is_current"]), None)
        repealed = current is not None and current["lifecycle_state"] == "repealed"
        wanted = desired_versions(identifier, act, entry, manifest, today)
        later = {v["url"]: v for v in wanted[1:]}
        own = [v for v in existing if v.get("url") in later]
        others = [v for v in existing if v not in own]
        number = max((v["version"] for v in existing), default=0)
        info = {"document_id": doc["id"], "identifier": identifier}
        # the baseline: the version the document had (the current one, else the first); only empty fields
        base = current if current in others else (others[0] if others else None)
        # its text: the one the document shows, unless that is already a later version's
        # (a rebuild shows the newest text at once); then the text stored from the source record
        later_files = {w["file_path"] for w in wanted[1:] if w["file_path"]}
        first = {**wanted[0], "file_path": doc["file_path"] if doc["file_path"] not in later_files
                 else ec.original_file(manifest, identifier)}
        if base is None:
            number += 1
            actions.append({"action": "add", **info, "version": number, **{k: first[k] for k in _COMPARED}})
        else:
            keys = [k for k in ("edition_label", "effective_date", "url", "file_path") if not base.get(k) and first[k]]
            if not repealed:
                keys += ["is_current", "lifecycle_state"]
            changes = _changes(base, first, keys)
            if changes:
                actions.append({"action": "update", **info, "version_id": base["id"], "version": base["version"],
                                "edition_label": base.get("edition_label") or first["edition_label"],
                                "changes": changes})
        shown_file = (base or {}).get("file_path") or first["file_path"] or doc["file_path"]
        if not repealed:
            for w in wanted[1:]:
                match = next((v for v in own if v["url"] == w["url"]), None)
                if w["file_path"] is None and match and match.get("file_path"):
                    w = {**w, "file_path": match["file_path"]}  # a text stored before is kept
                if match is None:
                    number += 1
                    actions.append({"action": "add", **info, "version": number, **{k: w[k] for k in _COMPARED}})
                else:
                    changes = _changes(match, w, _COMPARED)
                    if changes:
                        actions.append({"action": "update", **info, "version_id": match["id"],
                                        "version": match["version"], "edition_label": w["edition_label"],
                                        "changes": changes})
                if w["file_path"] and w["effective_date"] <= today:
                    shown_file = w["file_path"]
            if shown_file and shown_file != doc["file_path"]:
                actions.append({"action": "file", **info, "old": doc["file_path"], "new": shown_file})
        effect = entry.get("first_effective")
        if effect and not (doc.get("effective_date") or "").strip():
            text = czech_date(effect)
            # the field is "Platnost od": an EU act's entry into force is that day; e-Sbírka's
            # open data give a Czech act's day of effect only, so the value says so
            new = f"{text} (účinnost)" if act["family"] == "CZ" else text
            actions.append({"action": "effective", **info, "old": doc.get("effective_date"), "new": new})
    return actions


def execute(cursor, actions):
    ec.execute(cursor, [a for a in actions if a["action"] != "effective"])
    for a in actions:
        if a["action"] == "effective":
            cursor.execute("UPDATE Document SET effective_date = %s WHERE id = %s", (a["new"], a["document_id"]))


def describe(a):
    if a["action"] == "effective":
        return f"document {a['document_id']} ({a['identifier']}): Platnost od {a['old']!r} -> {a['new']!r}"
    return ec.describe(a)


def excluded_identifiers(config=None):
    """The acts eu_consolidations.py keeps with their whole history (CLP, REACH)."""
    config = ec.load_config() if config is None else config
    return {a["identifier"] for a in config}


def apply(cursor, today=None, write=True, cache=None, manifest=None, validity=None, config=None):
    """Plans and (with `write`) executes the changes from the data files; returns the actions."""
    today = today or datetime.date.today().isoformat()
    cache = load_cache() if cache is None else cache
    manifest = ec.load_manifest() if manifest is None else manifest
    validity = load_validity() if validity is None else validity
    documents = fetch_documents(cursor, validity, excluded_identifiers(config))
    actions = plan(documents, cache, manifest, today)
    if write:
        execute(cursor, actions)
    return actions


def fetch_targets(cache=None, today=None):
    """{identifier: (manifest field, address)} of the later versions in effect whose
    text fetch_fulltext.py downloads (one per act)."""
    cache = load_cache() if cache is None else cache
    today = today or datetime.date.today().isoformat()
    targets = {}
    for identifier, entry in cache.items():
        act = act_from_entry(entry)
        target = in_effect_target(identifier, act, entry, today)
        if target:
            targets[identifier] = target
    return targets


def act_from_entry(entry):
    if entry["family"] == "CZ":
        number, year = entry["key"].split(":")[1].split("/")
        return {"family": "CZ", "key": entry["key"], "number": int(number), "year": int(year)}
    return {"family": "EU", "key": entry["key"], "celex": entry["celex"], "language": entry.get("language", "CS")}


def displayed_file(identifier, manifest, today, cache=None):
    """The text of the newest later version in effect on `today` that has one, or
    None (the document keeps the text it had) — for init_db.py."""
    cache = load_cache() if cache is None else cache
    entry = cache.get((identifier or "").strip())
    if not entry:
        return None
    for v in reversed(later_versions(entry)):
        if v["date"] > today:
            continue
        _key, found = ec.manifest_entry(manifest, identifier.strip(), field_of(entry["family"], v["date"]))
        if found:
            return found["local_path"]
    return None


def since_of(file_path, manifest, today):
    """The day the stored text `file_path` was downloaded (the manifest), else `today`."""
    dates = [(e.get("fetched_at") or "")[:10] for e in manifest.values()
             if file_path and e.get("status") == "fetched" and e.get("local_path") == file_path]
    dates = [d for d in dates if _ISO.match(d)]
    return min(dates) if dates else today
