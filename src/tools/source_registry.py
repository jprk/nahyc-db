"""The registry of monitored sources, data/monitored_sources.json (doc/DATA_SOURCES.md).

Reading and writing keep the file's hand-made layout (one field per line, `access`
on one line, a blank line before an entry that starts a new group), so that a
script updating a field — check_sources.py writing `verified_at` — changes only
that line in the diff. validate() checks the values against the vocabulary that
doc/DATA_SOURCES.md (odstavce 2 a 4.2) describes; select() picks the sources of a
run of harvest_sources.py.
"""
import json
import pathlib
import re

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
REGISTRY_PATH = REPO_ROOT / "data" / "monitored_sources.json"

FIELDS = ("id", "name", "category", "jurisdiction", "url", "access", "status", "screener", "cadence",
          "priority", "role", "signal", "stage", "adds", "constraints", "verified_at")
CATEGORIES = ("legal_register", "draft_legislation", "standards_body", "treaty_body", "ministry", "regulator",
              "authority", "case_register", "industry_association", "policy_tracker", "metadata_catalogue",
              "press_social")
JURISDICTIONS = ("CZ", "SK", "EU", "DE", "international")
METHODS = ("sparql", "rest_api", "json_api", "rss", "bulk_download", "pdf_pattern", "pdf_index", "html",
           "headless_browser", "none")
STATUSES = ("automated", "ready", "needs_work", "manual_only", "prohibited", "blocked", "rejected")
CADENCES = ("weekly", "monthly", "quarterly", "yearly", "on_demand")
PRIORITIES = ("A", "B", "C")
ROLES = ("P", "L", "N", "M", "E", "S")
SIGNALS = ("new_document", "draft", "state_change", "lookup", "context", "link_check")
STAGES = ("E1", "E2", "E3", "E4", "E5", "E6", "manual")
NOT_HARVESTED = ("prohibited", "rejected")


def load(path=None):
    """(entries, group_starts): the entries in file order and the ids that start a group."""
    text = pathlib.Path(path or REGISTRY_PATH).read_text(encoding="utf-8")
    entries = json.loads(text)
    group_starts = set(re.findall(r'\n\n\s*\{\s*\n\s*"id":\s*"([^"]+)"', text))
    return entries, group_starts


def _value(v):
    return json.dumps(v, ensure_ascii=False, separators=(", ", ": "))


def dumps(entries, group_starts):
    parts = []
    for entry in entries:
        block = "  {\n" + ",\n".join(f'    "{k}": {_value(v)}' for k, v in entry.items()) + "\n  }"
        if parts and entry["id"] in group_starts:
            block = "\n" + block
        parts.append(block)
    return "[\n" + ",\n".join(parts) + "\n]\n"


def save(entries, group_starts, path=None):
    pathlib.Path(path or REGISTRY_PATH).write_text(dumps(entries, group_starts), encoding="utf-8")


def urls(entry):
    """The addresses of a source worth checking: the entry address and the
    endpoint and feed of its access, without templates such as `vestnik-{M}-{YY}.pdf`."""
    found = [entry["url"]]
    for key in ("endpoint", "feed"):
        value = entry["access"].get(key)
        if value and value not in found and "{" not in value:
            found.append(value)
    return found


def validate(entries):
    """Problems of the registry as a list of strings (empty when it is consistent)."""
    problems = []
    seen = set()
    for entry in entries:
        sid = entry.get("id", "?")
        if list(entry) != list(FIELDS):
            problems.append(f"{sid}: fields {list(entry)} differ from {list(FIELDS)}")
            continue
        if sid in seen:
            problems.append(f"{sid}: duplicate id")
        seen.add(sid)
        for field, allowed in (("category", CATEGORIES), ("jurisdiction", JURISDICTIONS), ("status", STATUSES),
                               ("cadence", CADENCES + (None,)), ("priority", PRIORITIES + (None,)),
                               ("stage", STAGES + (None,))):
            if entry[field] not in allowed:
                problems.append(f"{sid}: {field} = {entry[field]!r}")
        if entry["access"].get("method") not in METHODS:
            problems.append(f"{sid}: access.method = {entry['access'].get('method')!r}")
        for field, allowed in (("role", ROLES), ("signal", SIGNALS)):
            if not isinstance(entry[field], list) or any(v not in allowed for v in entry[field]):
                problems.append(f"{sid}: {field} = {entry[field]!r}")
        not_harvested = entry["status"] in NOT_HARVESTED
        if not_harvested and (entry["signal"] or entry["stage"]):
            problems.append(f"{sid}: a {entry['status']} source has a signal or a stage")
        if not not_harvested and not (entry["signal"] and entry["stage"]):
            problems.append(f"{sid}: no signal or stage")
        if (entry["status"] == "manual_only") != (entry["stage"] == "manual"):
            problems.append(f"{sid}: status {entry['status']} with stage {entry['stage']}")
        if entry["status"] != "automated" and entry["verified_at"] is None and entry["id"] != "eru-cz":
            problems.append(f"{sid}: verified_at missing")
    return problems


def select(entries, ids=(), stage=None, cadence=None):
    """The entries a run is about: the named ids (in the given order), or all of a
    stage and/or cadence. Unknown ids raise KeyError."""
    if ids:
        by_id = {e["id"]: e for e in entries}
        missing = [i for i in ids if i not in by_id]
        if missing:
            raise KeyError(", ".join(missing))
        return [by_id[i] for i in ids]
    return [e for e in entries if (stage is None or e["stage"] == stage)
            and (cadence is None or e["cadence"] == cadence)]
