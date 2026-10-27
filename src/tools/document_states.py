"""States of documents (doc/DATABASE_SCOPE.md, odstavec 5) from the validity
check (check_validity.py, data/validity_cache.json).

`DocumentVersion.lifecycle_state` keeps its values and gains two:

| value         | state (odstavec 5)            | set by                                   |
|---------------|-------------------------------|------------------------------------------|
| `draft`       | připravovaný                  | init_db.classify_lifecycle_state (text)  |
| `promulgated` | vyhlášený, dosud neúčinný     | this module, from the validity check     |
| `active`      | účinný                        | default                                  |
| `repealed`    | zrušený                       | this module, from the validity check     |
| `superseded`  | nahrazený (an older version)  | init_db.classify_lifecycle_state         |

Only the current version of a document changes; its history stays as it is. A
repealed document is joined to the act that repealed it by `REPEALS` (from the
repealing act to the repealed one), when the database has both; the relations
are written to data/document_relations_validity.json, which
load_document_relations.py reads like the other relation files. init_db.py applies
the same states on a rebuild; backfill_document_states.py applies them to the
live database.
"""
import json
import pathlib

import citation_closure as cc
from language_variants import EN_SUFFIX

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
CACHE_PATH = REPO_ROOT / "data" / "validity_cache.json"
RELATIONS_PATH = REPO_ROOT / "data" / "document_relations_validity.json"

STATES = ("active", "superseded", "draft", "promulgated", "repealed")
LABELS = {"active": "účinný", "superseded": "nahrazený", "draft": "připravovaný",
          "promulgated": "vyhlášený, dosud neúčinný", "repealed": "zrušený"}
_FROM_VALIDITY = {"zrušený": "repealed", "dosud neúčinný": "promulgated"}


def load_cache(path=CACHE_PATH):
    path = pathlib.Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def state_of(identifier, title, cache):
    """The lifecycle state the validity check gives a document (`repealed` or
    `promulgated`), or None when it says nothing beyond the default."""
    for key in sorted(cc.own_keys(identifier, title)):
        state = _FROM_VALIDITY.get(cache.get(key, {}).get("status"))
        if state:
            return state
    return None


def current_state(classified, identifier, title, cache):
    """The state of a current version: the validity check overrides `active`;
    a draft found in the record's own text stays a draft."""
    if classified == "draft":
        return classified
    return state_of(identifier, title, cache) or classified


def repeal_relations(documents, cache):
    """[relation] (load_document_relations.py shape, by identifier) joining every
    repealed document of `documents` — [(identifier, title)] — to the documents
    that repealed it, when they are in the database too. Documents without an
    identifier cannot be named here and are skipped."""
    by_key = {}
    for identifier, title in documents:
        if identifier:
            for key in cc.own_keys(identifier, title):
                by_key.setdefault(key, []).append(identifier)
    relations = []
    for identifier, title in documents:
        if not identifier or state_of(identifier, title, cache) != "repealed":
            continue
        for key in sorted(cc.own_keys(identifier, title)):
            entry = cache.get(key, {})
            ended = entry.get("repealed_on") or entry.get("end")
            note = f"Zrušující předpis podle {entry.get('source')}" + (f"; konec účinnosti {ended}." if ended else ".")
            for successor in entry.get("repealed_by", []):
                names = by_key.get(successor, [])
                # the repealing act once, not each of its language variants
                for successor_identifier in [n for n in names if not n.endswith(EN_SUFFIX)] or names[:1]:
                    relations.append({"from_identifier": successor_identifier, "to_identifier": identifier,
                                      "relation_type": "REPEALS", "note": note})
    unique = {(r["from_identifier"], r["to_identifier"]): r for r in relations}
    return [unique[k] for k in sorted(unique)]
