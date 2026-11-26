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

The designation of the document follows the edition in effect (decision of
2026-11-20, doc/MPO_PRIPOMINKY.md, odstavec 5.1; doc/PROVOZ.md, odstavec 5.2):
when the switch makes current an edition whose designation differs from the
document's identifier (ČSN EN 13445-2+A1 -> ČSN EN 13445-2, or "+A1" appears),
`Document.identifier` becomes that designation, and so does the designation at the
head of its title; an identifier that already reads so stays as it is. The slug
(permanent address) does not change. The edition replaced keeps its designation
in `DocumentVersion.edition_label` (when it had none, the edition the standards
cache lists as current, else the old identifier). A designation another document
has (compared by the database, i.e. under utf8mb4_czech_ci) blocks the renaming;
the switch happens anyway and the conflict is reported. The address of the
document follows the edition, too, when it was the catalogue page of the old one.

A renaming must survive a rebuild from JSON: persist() records it in
data/manual_corrections.json (`znacka`, the pinned `slug`, the new address; a
document renamed before gets its existing correction updated, the intermediate
designation in `renamed_from`, so relations stored under it follow), renames the
document's keys in data/fulltext_manifest.json and moves its entry in
data/norm_validity_cache.json to the new designation.
"""
import datetime
import json
import pathlib
import re
import state_paths

NORM_TYPE = "Norma"
PROMULGATED = "promulgated"
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
CORRECTIONS_PATH = state_paths.data_file("manual_corrections.json")
MANIFEST_PATH = state_paths.data_file("fulltext_manifest.json")
NORM_CACHE_PATH = state_paths.data_file("norm_validity_cache.json")
DETAIL_URL = "https://csnonline.agentura-cas.cz/Detailnormy.aspx?k={}"
_LABEL_ISSUE = re.compile(r"\s*\(vydání [^)]*\)\s*$")


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


def designation_of(label):
    """"ČSN EN 13445-2 (vydání 12.2026)" -> "ČSN EN 13445-2"; None for no label."""
    designation = _LABEL_ISSUE.sub("", re.sub(r"\s+", " ", label or "")).strip()
    return designation or None


def same_designation(a, b):
    return re.sub(r"\s+", " ", a or "").strip().casefold() == re.sub(r"\s+", " ", b or "").strip().casefold()


def renamed_identifier(identifier, label):
    """The designation the document gets when the edition `label` becomes current,
    or None when its identifier already reads so (or the label has none)."""
    designation = designation_of(label)
    if not designation or same_designation(designation, identifier):
        return None
    return designation


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
      `rename_to` is the new identifier (None when it stays), `from_label` the
      label the replaced version gets when it has none, `old_url`/`new_url` the
      catalogue pages of the two editions (when the cache knows them).
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
            switch = {"action": "switch", "document_id": doc_id, "to_version_id": current["id"],
                      "to_version": current["version"], "from_version_id": None,
                      "edition_label": current["edition_label"], "effective_date": current["effective_date"]}
        elif current is None or not is_iso(current["effective_date"]) or current["effective_date"] <= newest["effective_date"]:
            switch = {"action": "switch", "document_id": doc_id, "to_version_id": newest["id"],
                      "to_version": newest["version"], "from_version_id": current["id"] if current else None,
                      "edition_label": newest["edition_label"], "effective_date": newest["effective_date"]}
        else:
            continue
        switch.update(_switch_details(identifier, switch, current if switch["from_version_id"] else None,
                                      cache.get(cache_key(identifier)) or {}))
        actions.append(switch)
    return actions


def _switch_details(identifier, switch, replaced, entry):
    """rename_to, from_label, old_url, new_url of a switch (see plan())."""
    details = {"identifier": identifier, "rename_to": renamed_identifier(identifier, switch["edition_label"]),
               "from_label": None, "old_url": None, "new_url": None}
    if replaced is not None and not replaced["edition_label"]:
        current = {"designation": entry.get("designation"), "issued": entry.get("issued")}
        details["from_label"] = edition_label(current) if current["designation"] else identifier
    upcoming = entry.get("upcoming")
    if (replaced is not None and isinstance(upcoming, dict) and edition_label(upcoming) == switch["edition_label"]
            and entry.get("catalog_number") and upcoming.get("url")):
        details["old_url"] = DETAIL_URL.format(entry["catalog_number"])
        details["new_url"] = upcoming["url"]
    return details


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


def check_collisions(cursor, actions):
    """Marks a renaming the database would refuse: another document has the new
    designation, compared under the column's collation (utf8mb4_czech_ci), which
    the unique index uq_document_identifier enforces. Sets `rename_blocked_by`
    (the other document's id) and clears `rename_to`."""
    for a in actions:
        if a["action"] == "switch" and a.get("rename_to"):
            cursor.execute("SELECT id FROM Document WHERE identifier = %s AND id <> %s ORDER BY id",
                           (a["rename_to"], a["document_id"]))
            rows = _rows(cursor.fetchall())
            if rows:
                a["rename_blocked_by"], a["blocked_name"], a["rename_to"] = rows[0][0], a["rename_to"], None
    return actions


def retitled(title, old_identifier, new_identifier):
    """The title with the old designation at its head replaced by the new one
    ("ČSN EN 13445-2+A1 — Materiály" -> "ČSN EN 13445-2 — Materiály", the form
    init_db.py gives the title of a standard); other titles unchanged."""
    from norm_title import designation_core
    old_core = designation_core(old_identifier) or old_identifier
    new_core = designation_core(new_identifier) or new_identifier
    title = title or ""
    if title.startswith(old_core + " — "):
        return new_core + title[len(old_core):]
    return title


def _rename(cursor, a):
    """Renames the document of switch `a`; records what changed in `a["renamed"]`."""
    cursor.execute("SELECT identifier, title, slug, url FROM Document WHERE id = %s", (a["document_id"],))
    identifier, title, slug, url = _rows(cursor.fetchall())[0]
    new_title = retitled(title, identifier, a["rename_to"])
    cursor.execute("UPDATE Document SET identifier = %s, title = %s WHERE id = %s",
                   (a["rename_to"], new_title, a["document_id"]))
    a["renamed"] = {"old": identifier, "new": a["rename_to"], "slug": slug, "title": new_title}


def execute(cursor, actions):
    """Writes `actions` (plan()) to the database. A `switch` of an `add`ed version
    (no id yet) finds it by its number; a switch renames the document and moves
    its address to the new edition's page as plan() says (`renamed`,
    `url_changed` are set on the action for persist())."""
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
                if a.get("from_label"):
                    cursor.execute("UPDATE DocumentVersion SET edition_label = %s WHERE id = %s "
                                   "AND (edition_label IS NULL OR edition_label = '')",
                                   (a["from_label"], a["from_version_id"]))
            cursor.execute("UPDATE DocumentVersion SET is_current = 1, lifecycle_state = 'active' WHERE id = %s",
                           (to_id,))
            if a.get("rename_to"):
                _rename(cursor, a)
            if a.get("new_url"):
                cursor.execute("UPDATE Document SET url = %s WHERE id = %s AND url = %s",
                               (a["new_url"], a["document_id"], a["old_url"]))
                a["url_changed"] = bool(cursor.rowcount)
                cursor.execute("UPDATE Document SET zdroj_autoritativni_url = %s WHERE id = %s "
                               "AND zdroj_autoritativni_url = %s", (a["new_url"], a["document_id"], a["old_url"]))
                a["url_changed"] = a["url_changed"] or bool(cursor.rowcount)


def describe(action):
    if action["action"] == "add":
        return (f"document {action['document_id']}: new edition {action['edition_label']!r} "
                f"(in effect from {action['effective_date']}) added as version {action['version']}, promulgated")
    if action["action"] == "drop":
        return f"document {action['document_id']}: edition {action['edition_label']!r} no longer listed, removed"
    text = (f"document {action['document_id']}: edition {action['edition_label']!r} in effect since "
            f"{action['effective_date']}, now the current version")
    if action.get("rename_to"):
        text += f"; identifier {action['identifier']!r} -> {action['rename_to']!r} (slug unchanged)"
    elif action.get("rename_blocked_by"):
        text += (f"; identifier {action['identifier']!r} NOT renamed to {action['blocked_name']!r}, "
                 f"document {action['rename_blocked_by']} has it")
    if action.get("from_label"):
        text += f"; the replaced version keeps the label {action['from_label']!r}"
    if action.get("new_url"):
        text += f"; address {action['old_url']} -> {action['new_url']} (if the document has the old one)"
    return text


def apply(cursor, cache, today, write=True):
    """Plans and (with `write`) executes the changes; returns the actions. A
    renaming another document's designation blocks is reported, not done."""
    actions = check_collisions(cursor, plan(fetch_documents(cursor), cache, today))
    if write:
        execute(cursor, actions)
    return actions


def _load_json(path):
    path = pathlib.Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def record_correction(corrections, old, new, slug=None, new_url=None, today=None, edition=None):
    """Records in `corrections` (data/manual_corrections.json, in place) that the
    document with identifier `old` is now `new` (with its slug pinned) and/or has
    the address `new_url`: in the correction keyed by `old`, or — when the document
    was renamed before — in the correction that gave it the identifier `old`, with
    `old` added to its `renamed_from` (who confirmed an existing correction stays,
    the reason gets a sentence). Returns the key."""
    key = next((k for k, e in corrections.items() if (e.get("changes") or {}).get("znacka") == old), old)
    if key not in corrections:
        corrections[key] = {"changes": {}, "confirmed_at": today or datetime.date.today().isoformat(),
                            "confirmed_by": "norm_editions.py (přepnutí normy na nové vydání)"}
    entry = corrections[key]
    changes = entry.setdefault("changes", {})
    notes = []
    if new != old:
        changes["znacka"] = new
        if slug:
            changes.setdefault("slug", slug)
        if key != old:
            entry["renamed_from"] = sorted(set(entry.get("renamed_from", [])) | {old})
        notes.append(f"Dnem účinnosti nového vydání{f' {edition}' if edition else ''} se označení dokumentu "
                     f"změnilo z {old} na {new} (označení účinného vydání, doc/PROVOZ.md, odstavec 5.2); "
                     f"trvalá adresa (slug) zůstává.")
    if new_url:
        changes["zdroj_autoritativni_url"] = new_url
        notes.append(f"Odkaz vede na stránku účinného vydání{f' {edition}' if edition else ''} v katalogu ČAS.")
    for note in notes:
        if note not in (entry.get("reason") or ""):
            entry["reason"] = f"{entry['reason']} {note}" if entry.get("reason") else note
    return key


def rename_manifest_keys(manifest, old, new):
    """Renames the keys `<source>|<old>|<field>` of data/fulltext_manifest.json (in
    place); returns how many."""
    renamed = 0
    for key in list(manifest):
        source, _, rest = key.partition("|")
        designation, _, field = rest.rpartition("|")
        if designation == old and f"{source}|{new}|{field}" not in manifest:
            manifest[f"{source}|{new}|{field}"] = manifest.pop(key)
            renamed += 1
    return renamed


def move_cache_entry(cache, old, new):
    """Moves the standards cache entry of `old` to `new` (in place), so the next
    run finds the renamed document's editions; True when it did."""
    if cache_key(old) in cache and cache_key(new) not in cache:
        cache[cache_key(new)] = cache.pop(cache_key(old))
        return True
    return False


def persist(actions, today=None, corrections_path=CORRECTIONS_PATH, manifest_path=MANIFEST_PATH,
            cache_path=NORM_CACHE_PATH):
    """Writes the renamings and address changes execute() made to the data files a
    rebuild reads (see the module docstring); returns [message]."""
    done = [a for a in actions if a["action"] == "switch" and (a.get("renamed") or a.get("url_changed"))]
    if not done:
        return []
    corrections, manifest, cache = _load_json(corrections_path), _load_json(manifest_path), _load_json(cache_path)
    messages = []
    for a in done:
        renamed = a.get("renamed") or {"old": a["identifier"], "new": a["identifier"], "slug": None}
        old, new = renamed["old"], renamed["new"]
        key = record_correction(corrections, old, new, renamed["slug"], a["new_url"] if a.get("url_changed") else None,
                                today, a["edition_label"])
        messages.append(f"data/manual_corrections.json: {key!r}"
                        + (f" -> {new!r} (slug {renamed['slug']!r})" if new != old else "")
                        + (f", address {a['new_url']}" if a.get("url_changed") else ""))
        if new != old:
            n = rename_manifest_keys(manifest, old, new)
            if n:
                messages.append(f"data/fulltext_manifest.json: {n} keys renamed to {new!r}")
            if move_cache_entry(cache, old, new):
                messages.append(f"data/norm_validity_cache.json: {cache_key(old)} -> {cache_key(new)}")
    pathlib.Path(corrections_path).write_text(json.dumps(corrections, ensure_ascii=False, indent=2) + "\n",
                                              encoding="utf-8")
    pathlib.Path(manifest_path).write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
                                           encoding="utf-8")
    pathlib.Path(cache_path).write_text(json.dumps(dict(sorted(cache.items())), ensure_ascii=False, indent=1) + "\n",
                                        encoding="utf-8")
    return messages


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
