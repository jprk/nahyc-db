"""Looks up an IEC-designated corpus record against the local index built
by `src/tools/harvest_iec_publications.py` — doc/PLAN.md §25, 2026-09-17.

Unlike every other `src/sites/` module, this one makes NO live request at
all. `www.iec.ch` (needed to resolve a designation in the first place —
IEC designations don't encode which of its ~224 technical committees
publishes them, so there is no per-designation live search) sits behind
an AWS WAF Bot Control "challenge" that a plain `requests`/`curl` client
cannot pass — confirmed live. Passing it needs a real browser
(Playwright + headless Chromium, confirmed live too), which is too heavy
to run on every `fetch_authoritative_metadata.py` invocation for a
handful of records. So the browser-driven harvest is a separate,
one-time (or periodically re-run) step; this module is the light
everyday consumer of its output, exactly the same "cache is built once,
reapplied cheaply forever after" shape `data/site_metadata_cache.json`
itself already has one level up.

`normalize_designation()` mirrors `harvest_iec_publications.py`'s own
`reference_base()` on the corpus side: strips the Sinay-style edition
suffix ("IEC 60092-506/ - 2003.06" -> "IEC 60092-506") and a "prEN "
prefix (the corpus's own marker for "draft European adoption of an IEC
document", not part of the IEC document's own identity — "prEN IEC
63341-2" -> "IEC 63341-2"). A designation for a draft/not-yet-published
IEC document correctly finds nothing in the index (it isn't in any
committee's PUBLISHED list yet) — not guessed at.
"""
import json
import pathlib
import re

BASE_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent
INDEX_PATH = REPO_ROOT / "data" / "iec_publications_index.json"

_SINAY_EDITION_SUFFIX_RE = re.compile(r"/\s*-\s*\d{4}\.\d{2}$")
_PR_EN_PREFIX_RE = re.compile(r"^pr\s*EN\s+", re.IGNORECASE)
# The corpus writes the document-type marker slash-joined ("IEC/TR",
# "IEC/TS", "IEC/PAS"); IEC's own catalog (and this module's harvested
# index, built directly from it) writes it space-separated ("IEC TR",
# "IEC TS", "IEC PAS") — confirmed live, e.g. the harvested Reference
# for the corpus's "IEC/TR 62351-13" is "IEC TR 62351-13:2016".
_SLASH_TYPE_MARKER_RE = re.compile(r"^IEC/(TR|TS|PAS)\b", re.IGNORECASE)


def normalize_designation(znacka):
    """"IEC/TR 62351-13/ - 2016.08" -> "IEC TR 62351-13"; "prEN IEC
    63341-2" -> "IEC 63341-2"; already-bare "IEC 62351-14" unchanged.
    Returns None for a blank designation."""
    text = (znacka or "").strip()
    if not text:
        return None
    text = _SINAY_EDITION_SUFFIX_RE.sub("", text).strip()
    text = _PR_EN_PREFIX_RE.sub("", text).strip()
    text = _SLASH_TYPE_MARKER_RE.sub(lambda m: f"IEC {m.group(1).upper()}", text)
    return text or None


def load_index(path=None):
    """The harvested {reference_base: {title, description, ...}} index,
    or {} if it hasn't been built yet (harvest_iec_publications.py never
    ran) — never raises, same degrade-quietly convention as every other
    site module's network failure path."""
    index_path = pathlib.Path(path) if path else INDEX_PATH
    if not index_path.exists():
        return {}
    with open(index_path, "r", encoding="utf-8") as f:
        return json.load(f)


def lookup(znacka, index):
    """Returns {"title": str, "description": str|None} for `znacka`, or
    None when its normalized designation isn't in `index` at all (not
    yet published, or simply not one of this corpus's harvested
    committees' publications)."""
    designation = normalize_designation(znacka)
    if designation is None:
        return None
    entry = index.get(designation)
    if entry is None:
        return None
    return {"title": entry.get("title"), "description": entry.get("description")}
