"""Consolidated versions of EU acts (doc/CELLAR_FULLTEXT.md, odstavec 7;
doc/MPO_PRIPOMINKY.md, odstavec 5.1; decision of 2026-11-20).

For an act listed in data/eu_consolidated_acts.json (CLP and REACH so far) the
database shows the consolidated version in effect today, not the original text,
and follows every new consolidation. Each version is a `DocumentVersion` of the
act's one Document:

* the original text (2008/2006) — `edition_label` from the list ("původní znění
  (Úř. věst. L 353, 31. 12. 2008)"), the date of its entry into force, the stored
  text it always had (`file_path`), the EUR-Lex page of the act (`url`); state
  `superseded` once a consolidated version applies (it is never deleted);
* every consolidated version Cellar has in the document's language
  (`02008R1272-20260701`) — "konsolidované znění ke dni 1. 7. 2026", its date, its
  EUR-Lex page; the one in effect today is the current version (`active`), the
  older ones `superseded`, those prepared ahead of their date `promulgated`;
* `file_path` of a consolidated version is its text when it has been downloaded
  (data/fulltext_manifest.json, field `konsolidace_<YYYYMMDD>`). Only the version
  in effect is downloaded (fetch_fulltext.py, from Cellar only); historical
  versions link to EUR-Lex.

`Document.file_path` — the text the document page shows — is the newest version in
effect that has a downloaded text: the current consolidation once it is fetched,
until then the previous one (or the original).

Where the state comes from, so that it survives a rebuild from JSON:

* data/eu_consolidated_acts.json — which acts (CELEX, `identifier` of the
  Document, language, the original text's label and date); adding an act there
  is all it takes to switch the mechanism on for it;
* data/eu_consolidation_cache.json — the consolidated versions Cellar listed at
  the last check (refresh_eu_consolidations.py writes it);
* data/fulltext_manifest.json — the downloaded texts.

apply() is run by init_db.py (a rebuild), backfill_document_states.py (monthly
states) and refresh_eu_consolidations.py (daily: Cellar, download, extraction,
database). It works from those three files only and never goes to the network.
"""
import datetime
import json
import pathlib
import re

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = REPO_ROOT / "data" / "eu_consolidated_acts.json"
CACHE_PATH = REPO_ROOT / "data" / "eu_consolidation_cache.json"
MANIFEST_PATH = REPO_ROOT / "data" / "fulltext_manifest.json"

FIELD_PREFIX = "konsolidace_"
ORIGINAL_FIELDS = ("odkaz_hlavni", "odkaz_eu", "odkaz_sk")
CELLAR_LANGUAGE = {"CS": "ces", "SK": "slk", "EN": "eng", "DE": "deu"}
LABEL_PREFIX = "konsolidované znění ke dni "
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _load(path, default):
    path = pathlib.Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def load_config(path=CONFIG_PATH):
    """The acts of data/eu_consolidated_acts.json (list of dicts)."""
    return _load(path, {}).get("acts", [])


def load_cache(path=CACHE_PATH):
    return _load(path, {})


def save_cache(cache, path=CACHE_PATH):
    """Writes the cache with one line per consolidated version (a small diff when one is added)."""
    parts = []
    for celex, entry in sorted(cache.items()):
        head = {k: v for k, v in entry.items() if k != "consolidations"}
        lines = [json.dumps(c, ensure_ascii=False) for c in entry.get("consolidations", [])]
        body = json.dumps(head, ensure_ascii=False)[1:-1]
        parts.append(f' {json.dumps(celex)}: {{{body}, "consolidations": [\n  '
                     + ",\n  ".join(lines) + "\n ]}")
    pathlib.Path(path).write_text("{\n" + ",\n".join(parts) + "\n}\n", encoding="utf-8")


def load_manifest(path=MANIFEST_PATH):
    return _load(path, {})


def czech_date(iso):
    """"2026-07-01" -> "1. 7. 2026"."""
    year, month, day = iso.split("-")
    return f"{int(day)}. {int(month)}. {year}"


def edition_label(iso):
    return LABEL_PREFIX + czech_date(iso)


def field_of(consolidation):
    """Manifest field of a consolidated version: "konsolidace_20260701"."""
    return FIELD_PREFIX + consolidation["date"].replace("-", "")


def eurlex_page(celex, language="CS"):
    """The EUR-Lex page of a document (an act or one of its consolidated versions)."""
    return f"https://eur-lex.europa.eu/legal-content/{language}/TXT/?uri=CELEX:{celex}"


def text_address(celex, language="CS"):
    """The address fetch_fulltext.py downloads (from Cellar, src/sites/eurlex.py):
    the HTML of the consolidated version in the document's language."""
    return f"https://eur-lex.europa.eu/legal-content/{language}/TXT/HTML/?uri=CELEX:{celex}"


def consolidations_of(act, cache):
    """The consolidated versions of `act` the cache knows, after its original text."""
    entry = cache.get(act["celex"]) or {}
    original = (act.get("original") or {}).get("effective_date") or ""
    return [c for c in entry.get("consolidations", []) if _ISO.match(c.get("date", "")) and c["date"] > original]


def in_effect(consolidations, today):
    """The consolidated version that applies on `today` (the newest one dated no
    later), or None."""
    applying = [c for c in consolidations if c["date"] <= today]
    return max(applying, key=lambda c: c["date"]) if applying else None


def refresh(config, cache, today, session=None, query=None):
    """Asks Cellar for the consolidated versions of every act of `config` and stores
    them in `cache` (in place). A failed query keeps what the cache had. Returns
    (messages, failed CELEX numbers)."""
    if query is None:
        import sys
        sys.path.insert(0, str(REPO_ROOT / "src"))
        from sites.eurlex import consolidated_versions as query
    messages, failed = [], []
    for act in config:
        language = CELLAR_LANGUAGE.get(act.get("language", "CS"), "ces")
        found = query(act["celex"], language, session=session)
        if found is None:
            failed.append(act["celex"])
            messages.append(f"{act['celex']} ({act.get('name') or act['identifier']}): Cellar did not answer, "
                            f"keeping the {len((cache.get(act['celex']) or {}).get('consolidations', []))} "
                            f"versions known before")
            continue
        known = {c["celex"] for c in (cache.get(act["celex"]) or {}).get("consolidations", [])}
        new = [c for c in found if c["celex"] not in known]
        cache[act["celex"]] = {"identifier": act["identifier"], "language": language, "checked_at": today,
                               "consolidations": found}
        current = in_effect(consolidations_of(act, cache), today)
        coming = [c for c in consolidations_of(act, cache) if c["date"] > today]
        messages.append(f"{act['celex']} ({act.get('name') or act['identifier']}): {len(found)} consolidated versions"
                        f", in effect {current['celex'] if current else '—'}"
                        + (f", prepared {', '.join(c['celex'] for c in coming)}" if coming else "")
                        + (f"; new since the last check: {', '.join(c['celex'] for c in new)}" if known and new else ""))
    return messages, failed


def manifest_entry(manifest, identifier, field):
    """(key, entry) of the fetched manifest entry `<source>|<identifier>|<field>`, or (None, None)."""
    for key in sorted(manifest):
        source_designation, _, key_field = key.rpartition("|")
        if key_field == field and source_designation.partition("|")[2] == identifier:
            entry = manifest[key]
            if entry.get("status") == "fetched" and entry.get("local_path"):
                return key, entry
    return None, None


def original_file(manifest, identifier):
    """The stored text of the act's original version (the fields of the source
    record, in the order init_db.py uses)."""
    for field in ORIGINAL_FIELDS:
        _key, entry = manifest_entry(manifest, identifier, field)
        if entry:
            return entry["local_path"]
    return None


def act_of(identifier, config):
    return next((a for a in config if a["identifier"] == (identifier or "").strip()), None)


def displayed_file(identifier, manifest, today, config=None, cache=None):
    """The text a document of a listed act shows: the newest consolidated version in
    effect on `today` with a downloaded text; None when the act is not listed or no
    such text exists (the caller keeps the original's)."""
    config = load_config() if config is None else config
    act = act_of(identifier, config)
    if act is None:
        return None
    cache = load_cache() if cache is None else cache
    for c in sorted(consolidations_of(act, cache), key=lambda c: c["date"], reverse=True):
        if c["date"] > today:
            continue
        _key, entry = manifest_entry(manifest, act["identifier"], field_of(c))
        if entry:
            return entry["local_path"]
    return None


def fetch_targets(config=None, cache=None, today=None):
    """{identifier: (manifest field, address)} of the consolidated version in effect
    for every listed act — what fetch_fulltext.py downloads besides the source
    records' own addresses."""
    config = load_config() if config is None else config
    cache = load_cache() if cache is None else cache
    today = today or datetime.date.today().isoformat()
    targets = {}
    for act in config:
        current = in_effect(consolidations_of(act, cache), today)
        if current:
            targets[act["identifier"]] = (field_of(current), text_address(current["celex"], act.get("language", "CS")))
    return targets


def desired_versions(act, cache, manifest, today):
    """The versions the document of `act` should have on `today`, oldest first:
    dicts with key (the CELEX number), edition_label, effective_date, url,
    file_path, is_current, lifecycle_state."""
    language = act.get("language", "CS")
    consolidations = consolidations_of(act, cache)
    current = in_effect(consolidations, today)
    original = act.get("original") or {}
    versions = [{"key": act["celex"], "edition_label": original.get("label") or "původní znění",
                 "effective_date": original.get("effective_date"), "url": eurlex_page(act["celex"], language),
                 "file_path": original_file(manifest, act["identifier"]), "is_current": current is None,
                 "lifecycle_state": "active" if current is None else "superseded"}]
    for c in sorted(consolidations, key=lambda c: c["date"]):
        _key, entry = manifest_entry(manifest, act["identifier"], field_of(c))
        versions.append({"key": c["celex"], "edition_label": edition_label(c["date"]), "effective_date": c["date"],
                         "url": eurlex_page(c["celex"], language), "file_path": entry["local_path"] if entry else None,
                         "is_current": c is current,
                         "lifecycle_state": "promulgated" if c["date"] > today
                         else ("active" if c is current else "superseded")})
    return versions


_COMPARED = ("edition_label", "effective_date", "url", "file_path", "is_current", "lifecycle_state")


def _matches(existing, wanted, is_original):
    if existing.get("url"):
        return existing["url"] == wanted["url"]
    if existing.get("edition_label") == wanted["edition_label"]:
        return True
    # the version a rebuild (or the import) created before the act was listed: no address,
    # no consolidation label — it is the original text
    return is_original and not (existing.get("edition_label") or "").startswith(LABEL_PREFIX)


def plan(documents, config, cache, manifest, today):
    """The changes for the documents of the listed acts. `documents` =
    {identifier: {"id", "file_path", "versions": [dict with id, version,
    edition_label, effective_date, url, file_path, is_current, lifecycle_state]}}.
    Returns [action], each a dict with `action`:

    * `update` — version_id, document_id, changes {column: (old, new)};
    * `add` — document_id, version and the columns of a new version;
    * `file` — document_id, old, new: the text the document shows;
    * `skip` — document_id, reason (a repealed act is left as it is).
    """
    actions = []
    for act in config:
        doc = documents.get(act["identifier"])
        if doc is None or act["celex"] not in cache:
            continue
        existing = sorted(doc["versions"], key=lambda v: v["version"])
        current = next((v for v in existing if v["is_current"]), None)
        if current is not None and current["lifecycle_state"] == "repealed":
            actions.append({"action": "skip", "document_id": doc["id"], "identifier": act["identifier"],
                            "reason": "the act is repealed (check_validity.py); its versions are left as they are"})
            continue
        unmatched = list(existing)
        number = max((v["version"] for v in existing), default=0)
        for i, wanted in enumerate(desired_versions(act, cache, manifest, today)):
            match = next((v for v in unmatched if _matches(v, wanted, i == 0)), None)
            if match is None:
                number += 1
                actions.append({"action": "add", "document_id": doc["id"], "identifier": act["identifier"],
                                "version": number, **{k: wanted[k] for k in _COMPARED}})
                continue
            unmatched.remove(match)
            if wanted["file_path"] is None and match.get("file_path"):
                wanted = {**wanted, "file_path": match["file_path"]}  # a text stored before is kept
            changes = {k: (match.get(k), wanted[k]) for k in _COMPARED
                       if (bool(match.get(k)) if k == "is_current" else match.get(k)) != wanted[k]}
            if changes:
                actions.append({"action": "update", "version_id": match["id"], "version": match["version"],
                                "document_id": doc["id"], "identifier": act["identifier"],
                                "edition_label": wanted["edition_label"], "changes": changes})
        shown = displayed_file(act["identifier"], manifest, today, config, cache) \
            or original_file(manifest, act["identifier"]) or doc["file_path"]
        if shown != doc["file_path"]:
            actions.append({"action": "file", "document_id": doc["id"], "identifier": act["identifier"],
                            "old": doc["file_path"], "new": shown})
    return actions


def _rows(rows):
    return [tuple(r.values()) if isinstance(r, dict) else r for r in rows]


def has_url_column(cursor):
    cursor.execute("SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() "
                   "AND TABLE_NAME = 'DocumentVersion' AND COLUMN_NAME = 'url'")
    return bool(_rows(cursor.fetchall())[0][0])


def ensure_schema(cursor):
    """Adds DocumentVersion.url (the EUR-Lex page of the version) when missing; True when it did."""
    if has_url_column(cursor):
        return False
    cursor.execute("ALTER TABLE DocumentVersion ADD COLUMN url VARCHAR(500) NULL AFTER effective_date")
    return True


def fetch_documents(cursor, config):
    """{identifier: document} (see plan()) of the listed acts present in the database."""
    identifiers = [a["identifier"] for a in config]
    if not identifiers:
        return {}
    url = "dv.url" if has_url_column(cursor) else "NULL"
    marks = ",".join(["%s"] * len(identifiers))
    cursor.execute(f"SELECT d.id, d.identifier, d.file_path, dv.id, dv.version, dv.edition_label, dv.effective_date, "
                   f"{url}, dv.file_path, dv.is_current, dv.lifecycle_state FROM Document d "
                   f"LEFT JOIN DocumentVersion dv ON dv.document_id = d.id "
                   f"WHERE d.identifier IN ({marks}) ORDER BY d.id, dv.version", identifiers)
    documents = {}
    for (doc_id, identifier, doc_file, version_id, version, label, effective, version_url, version_file,
         is_current, state) in _rows(cursor.fetchall()):
        doc = documents.setdefault(identifier, {"id": doc_id, "file_path": doc_file, "versions": []})
        if version_id is not None:
            doc["versions"].append({"id": version_id, "version": version, "edition_label": label,
                                    "effective_date": effective, "url": version_url, "file_path": version_file,
                                    "is_current": bool(is_current), "lifecycle_state": state})
    return documents


def execute(cursor, actions):
    if any(a["action"] in ("add", "update") for a in actions):
        ensure_schema(cursor)
    for a in actions:
        if a["action"] == "add":
            cursor.execute("INSERT INTO DocumentVersion (document_id, version, edition_label, effective_date, url, "
                           "file_path, is_current, lifecycle_state) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                           (a["document_id"], a["version"], a["edition_label"], a["effective_date"], a["url"],
                            a["file_path"], int(a["is_current"]), a["lifecycle_state"]))
        elif a["action"] == "update":
            columns = sorted(a["changes"])
            values = [int(a["changes"][c][1]) if c == "is_current" else a["changes"][c][1] for c in columns]
            cursor.execute(f"UPDATE DocumentVersion SET {', '.join(f'{c} = %s' for c in columns)} WHERE id = %s",
                           values + [a["version_id"]])
        elif a["action"] == "file":
            cursor.execute("UPDATE Document SET file_path = %s WHERE id = %s", (a["new"], a["document_id"]))


def describe(a):
    who = f"document {a['document_id']} ({a['identifier']})"
    if a["action"] == "add":
        return (f"{who}: version {a['version']} {a['edition_label']!r} added, {a['lifecycle_state']}"
                + (", current" if a["is_current"] else "") + (f", text {a['file_path']}" if a["file_path"] else ""))
    if a["action"] == "update":
        changed = ", ".join(f"{k} {old!r} -> {new!r}" for k, (old, new) in sorted(a["changes"].items()))
        return f"{who}: version {a['version']} ({a['edition_label']}): {changed}"
    if a["action"] == "file":
        return f"{who}: shown text {a['old']} -> {a['new']}"
    return f"{who}: skipped, {a['reason']}"


def apply(cursor, today, write=True, config=None, cache=None, manifest=None):
    """Plans and (with `write`) executes the changes from the three data files; returns the actions."""
    config = load_config() if config is None else config
    cache = load_cache() if cache is None else cache
    manifest = load_manifest() if manifest is None else manifest
    actions = plan(fetch_documents(cursor, config), config, cache, manifest, today)
    if write:
        execute(cursor, actions)
    return actions
