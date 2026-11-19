"""Catalogue filters added for the MPO comments (doc/MPO_PRIPOMINKY.md, krok 2):
the jurisdiction filter, the grouping of the "Odpovědný orgán / DG" menu,
the EU act subtypes in the type menu and the search synonyms.

Everything here is pure (no database, no Flask); app.py turns it into SQL and
templates. The synonym dictionary and the source groups are data
(data/search_synonyms.json, data/source_groups.json), not code, so an editor can
extend them without touching the application."""
import json
import pathlib
import re
import unicodedata

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SYNONYMS_PATH = REPO_ROOT / "data" / "search_synonyms.json"
SOURCE_GROUPS_PATH = REPO_ROOT / "data" / "source_groups.json"

# ---------------------------------------------------------------- jurisdiction

# Decided by the user (doc/MPO_PRIPOMINKY.md, odstavec 4.3): Slovak documents
# (STN standards, Slovak laws, the Slovak versions of EU acts) are not part of
# the public catalogue. Only a logged-in editor may include them with the
# "zahrnout i slovenskou legislativu" switch (query parameter `sk=1`); see
# is_slovak() / public_condition() for what counts as Slovak. The jurisdiction menu then
# offers "Slovensko"; for everybody else it is not offered and `jurisdikce=sk`
# falls back to the default. "vse" therefore means "everything you may see".
DEFAULT_JURISDICTION = "vse"

# key -> (label, SQL condition on Document d, params)
_KNOWN = ("CZ", "SK", "EU", "mezinárodní")
JURISDICTIONS = {
    "vse": ("Všechny jurisdikce", "", []),
    "cz": ("Česká republika", "d.jurisdikce = %s", ["CZ"]),
    "eu": ("Evropská unie", "d.jurisdikce = %s", ["EU"]),
    "int": ("Mezinárodní", "d.jurisdikce = %s", ["mezinárodní"]),
    "sk": ("Slovensko", "d.jurisdikce = %s", ["SK"]),
    "jine": ("Ostatní státy a neurčené",
             "(d.jurisdikce IS NULL OR d.jurisdikce NOT IN (%s, %s, %s, %s))", list(_KNOWN)),
}
# Choices that only make sense when Slovak documents are included.
SLOVAK_ONLY_JURISDICTIONS = ("sk",)


def resolve_jurisdiction(raw, default=None, include_slovak=True):
    """The effective jurisdiction key for the `jurisdikce` query parameter:
    empty or unknown -> the default; "sk" without the Slovak switch -> the
    default as well."""
    default = default or DEFAULT_JURISDICTION
    raw = (raw or "").strip()
    if raw not in JURISDICTIONS or (not include_slovak and raw in SLOVAK_ONLY_JURISDICTIONS):
        return default
    return raw


def jurisdiction_condition(key):
    """(SQL condition, params) for a resolved key; ("", []) for "everything"."""
    _, condition, params = JURISDICTIONS[key]
    return condition, list(params)


def jurisdiction_options(default=None, include_slovak=True):
    """[(value, label)] for the menu: the default first under the empty value
    (so a plain URL means the default), then every other choice ("Slovensko"
    only with the Slovak switch)."""
    default = default or DEFAULT_JURISDICTION
    options = [("", JURISDICTIONS[default][0])]
    options += [(key, label) for key, (label, _, _) in JURISDICTIONS.items()
                if key != default and (include_slovak or key not in SLOVAK_ONLY_JURISDICTIONS)]
    return options


# ---------------------------------------------------------------- Slovak documents

# A document is Slovak when its jurisdiction is SK (STN/TNI standards adopted
# by ÚNMS SR, Slovak laws and decrees, and the Slovak versions of EU acts the
# Sinay table recorded under SK), or when its designation carries the "[SK]"
# suffix that marks the Slovak version of an EU act (doc/MPO_PRIPOMINKY.md,
# odstavec 4.1, #84: "(EU) 2024/1788 [SK]"), whatever jurisdiction it ends up
# with. The language alone does not decide: German, European and ISO
# standards whose titles came from a Slovak table (language SK) are not
# Slovak legislation and stay public.
SLOVAK_JURISDICTION = "SK"
SLOVAK_SUFFIX = "[SK]"
SLOVAK_SWITCH_PARAM = "sk"


def is_slovak(document):
    """Whether a row (dict with `jurisdikce` and `identifier`) is Slovak."""
    jurisdiction = (document.get("jurisdikce") or "").strip()
    identifier = (document.get("identifier") or "").strip()
    return jurisdiction == SLOVAK_JURISDICTION or identifier.upper().endswith(SLOVAK_SUFFIX)


def public_condition(alias="d"):
    """(SQL condition, params) true for a document that is NOT Slovak — the
    restriction of everything the public catalogue lists and counts."""
    return (f"NOT (COALESCE({alias}.jurisdikce, '') = %s OR COALESCE({alias}.identifier, '') LIKE %s)",
            [SLOVAK_JURISDICTION, "%" + SLOVAK_SUFFIX])


def wants_slovak(args, logged_in):
    """The Slovak switch: on only for a logged-in editor who asked for it
    (`sk=1`); a visitor's `sk=1` is ignored."""
    return bool(logged_in) and (args.get(SLOVAK_SWITCH_PARAM) or "").strip() == "1"


# ---------------------------------------------------------------- EU act subtype

# Values of Document.eu_act_subtype (src/tools/eu_act_subtype.py decides them);
# offered in the type menu as "podtyp-<value>".
EU_SUBTYPES = {
    "delegated": "Akt v přenesené pravomoci (EU)",
    "implementing": "Prováděcí akt (EU)",
}
SUBTYPE_PREFIX = "podtyp-"


def split_type_filter(raw):
    """(type_id, eu_subtype) from the `type_id` query parameter: a plain id, or
    "podtyp-delegated" / "podtyp-implementing" for an EU act subtype."""
    raw = (raw or "").strip()
    if raw.startswith(SUBTYPE_PREFIX):
        subtype = raw[len(SUBTYPE_PREFIX):]
        return "", (subtype if subtype in EU_SUBTYPES else "")
    return raw, ""


# ---------------------------------------------------------------- synonyms

def normalize(text):
    """Case- and whitespace-insensitive form used to compare a query with an alias."""
    text = unicodedata.normalize("NFC", text or "").replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip().casefold()


_synonym_cache = {}


def load_synonyms(path=SYNONYMS_PATH):
    path = pathlib.Path(path)
    stamp = path.stat().st_mtime
    cached = _synonym_cache.get(path)
    if cached and cached[0] == stamp:
        return cached[1]
    entries = json.loads(path.read_text(encoding="utf-8"))["entries"]
    _synonym_cache[path] = (stamp, entries)
    return entries


def alias_pattern(alias):
    """Matches the alias as whole words, so "RED II" does not fire for "RED III"."""
    return re.compile(r"(?<!\w)" + re.escape(normalize(alias)) + r"(?!\w)")


def match_synonyms(query, entries):
    """The entries any of whose aliases occurs in the query as whole words."""
    q = normalize(query)
    if not q:
        return []
    return [e for e in entries if any(alias_pattern(a).search(q) for a in e.get("aliases", []))]


def expansion(entries):
    """(search_terms, identifiers) of the matched entries, without duplicates,
    in the order of the dictionary."""
    terms, identifiers = [], []
    for entry in entries:
        for term in entry.get("search_terms", []):
            if term not in terms:
                terms.append(term)
        for identifier in entry.get("identifiers", []):
            if identifier not in identifiers:
                identifiers.append(identifier)
    return terms, identifiers


# ---------------------------------------------------------------- source groups

_group_cache = {}


def load_source_groups(path=SOURCE_GROUPS_PATH):
    path = pathlib.Path(path)
    stamp = path.stat().st_mtime
    cached = _group_cache.get(path)
    if cached and cached[0] == stamp:
        return cached[1]
    config = json.loads(path.read_text(encoding="utf-8"))
    _group_cache[path] = (stamp, config)
    return config


def source_group_key(name, jurisdiction, config):
    """Group of a DocumentSource: the explicit entry in the data file, else its
    `jurisdiction` column, else "ostatni"."""
    if name in config["sources"]:
        return config["sources"][name]
    return config.get("jurisdiction_fallback", {}).get(jurisdiction or "", "ostatni")


def group_sources(sources, config):
    """[{'key', 'label', 'sources': [...]}] in the order of the data file, empty
    groups left out; `sources` are rows with name and jurisdiction, kept in the
    order given (alphabetical from the query)."""
    groups = [{"key": g["key"], "label": g["label"], "sources": []} for g in config["groups"]]
    by_key = {g["key"]: g for g in groups}
    for source in sources:
        key = source_group_key(source["name"], source.get("jurisdiction"), config)
        by_key.get(key, by_key["ostatni"])["sources"].append(source)
    return [g for g in groups if g["sources"]]
