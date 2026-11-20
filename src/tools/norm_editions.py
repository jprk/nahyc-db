"""Editions of standards issued with a later date of effect (doc/MPO_PRIPOMINKY.md,
odstavec 5, 2026-11-20; doc/PROVOZ.md, odstavec 5.2).

The ČAS catalogue lists a newly issued ČSN as valid from its date of issue, while
the edition it replaces stays in force until the new one takes effect, usually on
the first day of the next month (ČSN EN 13445-1 to -11: issued 1. 12. 2026, in
effect from 1. 1. 2027). The database keeps both: the edition in force is the
current version of the document, the new one a further, not current version in
the state `promulgated` (vyhlášený, dosud neúčinný) with its date of effect
(`DocumentVersion.effective_date`, ISO date) and designation (`edition_label`).
On its date of effect the new edition becomes the current version (`active`) and
the previous one `superseded`. A new standard without an earlier edition is a
document whose only, current version is `promulgated` until that date.

Where the new edition comes from:

* the check of the state of ČSN (harvest_adapters.csn_state, monthly, through
  check_csn_validity.editions()) writes it to data/norm_validity_cache.json as
  `upcoming` of the standard's entry (`NORM:<designation>`), and `upcoming: null`
  when the catalogue no longer lists one;
* a candidate standard (mpo_tables.py lookup) carries it in its evidence
  (`upcoming_edition`), and accepting the candidate (app/candidates_admin.py)
  creates the version at once.

apply() — run by backfill_document_states.py (live database, after each check and
by the scheduler on the first day of every month) and by init_db.py (a rebuild) —
adds the version of a new edition the cache knows, removes a not yet effective
version the cache no longer lists, and switches the editions whose date of effect
has come. Only documents of the type Norma are touched, and only versions with an
ISO date of effect, so the free-text dates of other versions never trigger it.
The identifier of the document stays as it is (open question in
doc/MPO_PRIPOMINKY.md, odstavec 5.3).
"""
import re

NORM_TYPE = "Norma"
PROMULGATED = "promulgated"
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def is_iso(date):
    return bool(date) and bool(_ISO.match(str(date)))


def cache_key(identifier):
    return f"NORM:{(identifier or '').strip()}"


def edition_label(edition):
    """"ČSN EN 13445-1 (vydání 12.2026)" for an edition of check_csn_validity.editions()
    (`designation`) or of a candidate's evidence (`edition`)."""
    designation = re.sub(r"\s+", " ", edition.get("designation") or edition.get("edition") or "").strip()
    issued = edition.get("issued")
    return f"{designation} (vydání {issued})" if issued else designation


def upcoming_of(identifier, cache):
    """The edition not yet in effect that the standards cache knows for a document:
    a dict, None when the last check found none, or the string "unknown" when the
    cache does not say (no entry, or an entry of another source)."""
    entry = cache.get(cache_key(identifier))
    if not entry or "upcoming" not in entry:
        return "unknown"
    return entry["upcoming"]


def plan(documents, cache, today):
    """The changes for `documents` = [(document id, identifier, [version])], a version
    being a dict with id, version, edition_label, effective_date, is_current,
    lifecycle_state. Returns [action], each a dict with `action`:

    * `add` — document_id, version, edition_label, effective_date: a new edition the
      cache knows, not yet among the versions;
    * `drop` — version_id: a not yet effective, not current version whose edition
      the cache no longer lists (cancelled or replaced by another);
    * `switch` — document_id, to_version_id, from_version_id (or None): the date of
      effect has come; `to` becomes current and `active`, `from` `superseded`.
    """
    actions = []
    for doc_id, identifier, versions in documents:
        versions = [dict(v) for v in versions]
        upcoming = upcoming_of(identifier, cache)
        pending = [v for v in versions if not v["is_current"] and v["lifecycle_state"] == PROMULGATED
                   and is_iso(v["effective_date"])]
        if isinstance(upcoming, dict) and is_iso(upcoming.get("effective_from")):
            label = edition_label(upcoming)
            if not any(v["edition_label"] == label for v in versions):
                number = max((v["version"] for v in versions), default=0) + 1
                actions.append({"action": "add", "document_id": doc_id, "version": number,
                                "edition_label": label, "effective_date": upcoming["effective_from"]})
                versions.append({"id": None, "version": number, "edition_label": label,
                                 "effective_date": upcoming["effective_from"], "is_current": False,
                                 "lifecycle_state": PROMULGATED, "document_id": doc_id})
        if upcoming != "unknown":
            listed = edition_label(upcoming) if isinstance(upcoming, dict) else None
            for v in pending:
                if v["edition_label"] != listed and v["effective_date"] > today:
                    actions.append({"action": "drop", "version_id": v["id"], "document_id": doc_id,
                                    "edition_label": v["edition_label"]})
                    versions.remove(v)
        current = next((v for v in versions if v["is_current"]), None)
        due = [v for v in versions if v["lifecycle_state"] == PROMULGATED and is_iso(v["effective_date"])
               and v["effective_date"] <= today and (not v["is_current"] or v is current)]
        if not due:
            continue
        newest = max(due, key=lambda v: (v["effective_date"], v["version"]))
        if newest is current:
            actions.append({"action": "switch", "document_id": doc_id, "to_version_id": current["id"],
                            "to_version": current["version"], "from_version_id": None,
                            "edition_label": current["edition_label"], "effective_date": current["effective_date"]})
        elif current is None or not is_iso(current["effective_date"]) or current["effective_date"] <= newest["effective_date"]:
            actions.append({"action": "switch", "document_id": doc_id, "to_version_id": newest["id"],
                            "to_version": newest["version"], "from_version_id": current["id"] if current else None,
                            "edition_label": newest["edition_label"], "effective_date": newest["effective_date"]})
    return actions


def fetch_documents(cursor):
    """[(document id, identifier, [version])] of the standards in the database."""
    cursor.execute("SELECT d.id, d.identifier, dv.id, dv.version, dv.edition_label, dv.effective_date, "
                   "dv.is_current, dv.lifecycle_state FROM Document d "
                   "JOIN DocumentType dt ON dt.id = d.type_id AND dt.name = %s "
                   "JOIN DocumentVersion dv ON dv.document_id = d.id ORDER BY d.id, dv.version", (NORM_TYPE,))
    documents = {}
    for doc_id, identifier, version_id, version, label, effective, is_current, state in _rows(cursor.fetchall()):
        documents.setdefault(doc_id, (doc_id, identifier, []))[2].append(
            {"id": version_id, "version": version, "edition_label": label, "effective_date": effective,
             "is_current": bool(is_current), "lifecycle_state": state})
    return list(documents.values())


def _rows(rows):
    return [tuple(r.values()) if isinstance(r, dict) else r for r in rows]


def execute(cursor, actions):
    """Writes `actions` (plan()) to the database. A `switch` of an `add`ed version
    (no id yet) finds it by its number."""
    for a in actions:
        if a["action"] == "add":
            cursor.execute("INSERT INTO DocumentVersion (document_id, version, edition_label, effective_date, "
                           "is_current, lifecycle_state) VALUES (%s, %s, %s, %s, 0, %s)",
                           (a["document_id"], a["version"], a["edition_label"], a["effective_date"], PROMULGATED))
        elif a["action"] == "drop":
            cursor.execute("DELETE FROM DocumentVersion WHERE id = %s", (a["version_id"],))
        elif a["action"] == "switch":
            to_id = a["to_version_id"]
            if to_id is None:
                cursor.execute("SELECT id FROM DocumentVersion WHERE document_id = %s AND version = %s",
                               (a["document_id"], a["to_version"]))
                to_id = _rows(cursor.fetchall())[0][0]
            if a["from_version_id"]:
                cursor.execute("UPDATE DocumentVersion SET is_current = 0, lifecycle_state = 'superseded' "
                               "WHERE id = %s", (a["from_version_id"],))
            cursor.execute("UPDATE DocumentVersion SET is_current = 1, lifecycle_state = 'active' WHERE id = %s",
                           (to_id,))


def describe(action):
    if action["action"] == "add":
        return (f"document {action['document_id']}: new edition {action['edition_label']!r} "
                f"(in effect from {action['effective_date']}) added as version {action['version']}, promulgated")
    if action["action"] == "drop":
        return f"document {action['document_id']}: edition {action['edition_label']!r} no longer listed, removed"
    return (f"document {action['document_id']}: edition {action['edition_label']!r} in effect since "
            f"{action['effective_date']}, now the current version")


def apply(cursor, cache, today, write=True):
    """Plans and (with `write`) executes the changes; returns the actions."""
    actions = plan(fetch_documents(cursor), cache, today)
    if write:
        execute(cursor, actions)
    return actions


def candidate_versions(evidence, today):
    """The versions of a document created from a candidate standard (app/candidates_admin.py):
    [(version, edition_label, effective_date, is_current, lifecycle_state)] from its
    evidence (mpo_tables.csn_metadata: `edition`, `issued`, `effective_from`,
    `upcoming_edition`), or None when the evidence says nothing about editions."""
    if not evidence.get("effective_from") and not evidence.get("upcoming_edition"):
        return None
    current = {"edition": evidence.get("edition"), "issued": evidence.get("issued")}
    effective = evidence.get("effective_from")
    state = PROMULGATED if is_iso(effective) and effective > today else "active"
    versions = [(1, edition_label(current) if current["edition"] else None, effective, 1, state)]
    upcoming = evidence.get("upcoming_edition")
    if upcoming and is_iso(upcoming.get("effective_from")):
        versions.append((2, edition_label(upcoming), upcoming["effective_from"], 0, PROMULGATED))
    return versions
