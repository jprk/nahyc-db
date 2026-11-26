"""The last check of a document's state (doc/MPO_PRIPOMINKY.md, krok 3): when, and
by what, the validity or the state of a document was last verified.

The checks of the harvesting runner (harvest_sources.py) and of check_validity.py
write one entry per checked document into two caches, each with `checked_at` and
`source`:

* data/validity_cache.json — Czech and EU acts (`CZ:…`, `EU:…`; e-Sbírka, Cellar);
* data/norm_validity_cache.json — standards (`NORM:…`; ČSN online, Normoff,
  Věstník ÚNMZ, the Commission's lists of harmonised standards).

The consolidated versions of the EU acts kept up to date by
refresh_eu_consolidations.py (CLP, REACH; data/eu_consolidation_cache.json) are a
check of the act in Cellar too: their `checked_at` counts as a check of
EUR-Lex (Cellar) (doc/MPO_OVERENI_WEBU.md Z5: CLP showed the date of the last
validity check, 27. 10., although its consolidations were renewed on 20. 11.).

data/source_checks.jsonl logs runs of sources, not documents, so it is not read
here: a run that checked a document has already written that document's entry.

An entry counts as a check only when it states a result (`status`): `nezjištěno`
(the source did not answer about the document) and entries without a status (a
harmonised-standards listing alone says nothing about validity) are not a
verification of the state. An editor's confirmed change of state
(app/drafts_admin.py) is a check too, of the source `editor`.

The result is kept in `Document.status_checked_at` (DATE) and
`Document.status_checked_by` (who or what checked, in Czech, for the document
page): init_db.py fills them on a rebuild, backfill_document_states.py in the live
database, never moving a date back.
"""
import json
import pathlib

import citation_closure as cc

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
VALIDITY_CACHE_PATH = REPO_ROOT / "data" / "validity_cache.json"
NORM_CACHE_PATH = REPO_ROOT / "data" / "norm_validity_cache.json"
CONSOLIDATION_CACHE_PATH = REPO_ROOT / "data" / "eu_consolidation_cache.json"

SOURCE_LABELS = {
    "e-sbirka": "e-Sbírka",
    "cellar": "EUR-Lex (Cellar)",
    "zakonyprolidi": "Zákony pro lidi",
    "csnonline": "ČSN online",
    "normoff": "Normoff (ÚNMS SR)",
    "vestnik-unmz": "Věstník ÚNMZ",
    "ec-harmonised-standards": "seznamy harmonizovaných norem EK",
}
INCONCLUSIVE = {None, "", "nezjištěno"}
# DDL of the two columns, applied by ensure_columns() (and in doc/konsolidace/Konsolidace-DB-schema.sql)
COLUMNS = (("status_checked_at", "DATE NULL"), ("status_checked_by", "VARCHAR(100) NULL"))


def load(path):
    path = pathlib.Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def merge_consolidation_checks(cache, consolidations):
    """Adds the checks of the consolidated versions (`consolidations` = the content of
    data/eu_consolidation_cache.json, {celex: {identifier, checked_at, …}}) to
    `cache` (in place): the act's validity entry gets the newer `checked_at`, with the
    source `cellar`; an act without one gets an entry of its own. Returns `cache`."""
    for entry in consolidations.values():
        checked = (entry.get("checked_at") or "")[:10]
        if not checked or not entry.get("identifier"):
            continue
        for key in cc.own_keys(entry["identifier"], None):
            known = cache.get(key) or {}
            if (known.get("checked_at") or "")[:10] >= checked:
                continue
            status = known.get("status")
            cache[key] = {**known, "checked_at": checked, "source": "cellar",
                          "status": status if status not in INCONCLUSIVE else "konsolidované znění"}
    return cache


def load_caches(validity_path=None, norm_path=None, consolidation_path=None, consolidations=None):
    """Both caches merged into one {key: entry} (their keys never overlap), with the
    checks of the consolidated versions (merge_consolidation_checks(); `consolidations`
    replaces the file, refresh_eu_consolidations.py passes the cache it has just
    refreshed)."""
    cache = {**load(validity_path or VALIDITY_CACHE_PATH), **load(norm_path or NORM_CACHE_PATH)}
    if consolidations is None:
        consolidations = load(consolidation_path or CONSOLIDATION_CACHE_PATH)
    return merge_consolidation_checks(cache, consolidations)


def keys_of(identifier, title):
    """The cache keys of a document: those citation_closure reads from its
    identifier (or title) and, for a national standard, `NORM:<designation>`."""
    keys = set(cc.own_keys(identifier, title))
    if identifier:
        import harvest  # the national designations of standards (ČSN, TPG, SAE, …)
        national = harvest.norm_key(identifier) if harvest.NATIONAL_STANDARD.match(identifier.strip()) else None
        if national:
            keys.add(national)
    return keys


def label(source):
    return SOURCE_LABELS.get(source, source or "kontrola platnosti")


def last_check(identifier, title, cache):
    """(ISO date, label) of the latest conclusive check of a document, or None."""
    best = None
    for key in keys_of(identifier, title):
        entry = cache.get(key) or {}
        checked = (entry.get("checked_at") or "")[:10]
        if not checked or entry.get("status") in INCONCLUSIVE:
            continue
        if best is None or checked > best[0]:
            best = (checked, label(entry.get("source")))
    return best


def newer(found, stored_at):
    """True when the check `found` (date, label) is newer than the stored date
    (a date, an ISO string or None): a date never moves back."""
    if found is None:
        return False
    return stored_at is None or found[0] > str(stored_at)[:10]


def plan_checks(rows, cache):
    """[(document id, date, label)] for the documents `rows` =
    [(document id, identifier, title, stored date)] whose last check is newer
    than the stored one."""
    changes = []
    for doc_id, identifier, title, stored_at in rows:
        found = last_check(identifier, title, cache)
        if newer(found, stored_at):
            changes.append((doc_id, found[0], found[1]))
    return changes


def ensure_columns(cursor):
    """Adds the two columns to Document when they are missing; True when it did."""
    added = False
    for name, ddl in COLUMNS:
        cursor.execute("SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() "
                       "AND TABLE_NAME = 'Document' AND COLUMN_NAME = %s", (name,))
        row = cursor.fetchone()
        if not (row[0] if not isinstance(row, dict) else list(row.values())[0]):
            cursor.execute(f"ALTER TABLE Document ADD COLUMN {name} {ddl}")
            added = True
    return added


def editor_label(name):
    return f"editor {name}" if name else "editor"
