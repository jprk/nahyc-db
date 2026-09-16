"""Shared "Gestor" (issuing/responsible institution) resolution.

Used by `init_db.py` (initial import) and `backfill_puvodce.py`/
`backfill_eu_gestor.py` (one-time DB backfills for records imported
before this normalization existed). For a CZ/SK national act, Gestor is
a single institution — the primary `gestor` — not the whole raw `gestor`
list joined verbatim (which is what `init_db.py` used to do), and not a
bare two/three-letter abbreviation when the same institution already has
a full-name form elsewhere in the corpus. See `backfill_puvodce.py`'s
module docstring for the full background (user finding, 2026-09-15) and
the "primary responsible ministry" vs. "formal legal issuer" scoping
decision.

For an EU act itself (`Nařízení EU`/`Směrnice EU`/`Rozhodnutí EU`), per a
follow-up user finding/decision (2026-09-16): Gestor should be the EU
body that owns it — the source data's `gestor` list is not a reliable
signal here either (see `backfill_eu_gestor.py`'s module docstring) — so
`resolve_gestor()` consults `data/eu_gestor_cache.json` (populated by
`backfill_eu_gestor.py`/`src/sites/eurlex.py` against the authoritative
EUR-Lex/Cellar endpoint) instead of `gestor_list()`/`ABBREVIATION_MAP`
for those three types.
"""
import json

# Bare-abbreviation source names found in the raw `gestor` data, mapped
# to the full name already used elsewhere in the corpus for the same
# institution — merged so "MPO" and "Ministerstvo průmyslu a obchodu"
# don't end up as two different DocumentSource rows. "MZ" has no
# existing full-name row to merge into; verified by content (a record
# citing "Zákon o ochraně veřejného zdraví" — the Public Health
# Protection Act) rather than guessed, since "MZ" could otherwise be
# misread as Ministerstvo zemědělství (Agriculture), a different,
# already-present ministry.
ABBREVIATION_MAP = {
    "MD": "Ministerstvo dopravy",
    "MMR": "Ministerstvo pro místní rozvoj",
    "MPO": "Ministerstvo průmyslu a obchodu",
    "MV": "Ministerstvo vnitra",
    "MZ": "Ministerstvo zdravotnictví",
    "MŽP": "Ministerstvo životního prostředí",
}


def gestor_list(item):
    """Normalizes a merged-JSON record's `gestor` field (a list, or —
    for a handful of older records — a bare string) to a clean list of
    non-blank entries."""
    g = item.get("gestor", [])
    if isinstance(g, str):
        g = [g]
    return [x.strip() for x in g if x and x.strip()]


def is_clean_institution_name(name):
    """A real institution name in this corpus is always a short,
    single-line string — the AI-enrichment (`enrich_eu_laws.py`) blobs
    (the only "dirty" shape ever found here) always contain a newline,
    carrying a Directorate-General list plus free-text commentary
    alongside the real institution name. Length is a second, cheap
    safety net."""
    return bool(name) and "\n" not in name and len(name) <= 100


def resolve_puvodce(item):
    """Returns the single primary institution for this record: the
    first clean entry of its `gestor` list, canonicalized through
    ABBREVIATION_MAP, or None if there is none (blank gestor, or —
    never observed in this corpus, but handled rather than guessed —
    every entry is a blob)."""
    for g in gestor_list(item):
        if is_clean_institution_name(g):
            return ABBREVIATION_MAP.get(g, g)
    return None


EU_ACT_TYPES = ("Nařízení EU", "Směrnice EU", "Rozhodnutí EU")


def load_eu_gestor_cache(repo_root):
    """Loads `data/eu_gestor_cache.json` (see module docstring), keyed by
    `Document.url` — empty dict if the cache doesn't exist yet (no EU
    acts resolved this run; caller falls back to `resolve_puvodce()`,
    same as before this feature existed)."""
    path = repo_root / "data" / "eu_gestor_cache.json"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_gestor(item, doc_type, url, eu_gestor_cache):
    """Returns (gestor_or_None, unresolved_eu_act). For one of
    EU_ACT_TYPES, looks up `url` in `eu_gestor_cache` (see
    `backfill_eu_gestor.py` for how that cache is populated) instead of
    the CZ-ministry `gestor` list — `unresolved_eu_act` is True when the
    type is an EU act but its `url` has no cache entry (caller should
    flag it for review, same as `backfill_eu_gestor.py` does for a live
    miss, rather than silently falling back to a CZ ministry that would
    be the wrong kind of institution entirely). For every other type,
    behaves exactly like `resolve_puvodce()`."""
    if doc_type in EU_ACT_TYPES:
        gestor = eu_gestor_cache.get(url) if url else None
        return gestor, gestor is None
    return resolve_puvodce(item), False
