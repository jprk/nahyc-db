"""Looks up a DVGW-designated corpus record against the local index
built by `src/tools/harvest_dvgw_publications.py` — doc/PLAN.md §26,
2026-09-17.

Same shape as `src/sites/iec.py`: makes no live request at all, just
reads the harvested index. `dvgw-regelwerk.de`'s search is unreliable
for exact designation lookup (confirmed live — see the harvester's own
docstring) and its detail pages are paywalled beyond a one-line
subtitle, so there is no live per-designation resolution worth doing
here; the harvested index only covers 41 of the corpus's 101 DVGW-cited
designations to begin with (DVGW's own curated listings, not the full
catalog) — a designation not in it is correctly left unresolved, not
guessed at.
"""
import json
import pathlib
import re

BASE_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent
INDEX_PATH = REPO_ROOT / "data" / "dvgw_publications_index.json"

# The corpus marks a record's status in parentheses ("G 260 (A)" =
# "Arbeitsblatt" i.e. still current, "(M)" = "Merkblatt"/guideline) —
# not part of the designation DVGW's own catalog uses to key it.
_STATUS_SUFFIX_RE = re.compile(r"\s*\([AM]\)\s*$")


def normalize_designation(znacka):
    """"G 260 (A)" -> "G 260". Returns None for a blank designation."""
    text = (znacka or "").strip()
    if not text:
        return None
    text = _STATUS_SUFFIX_RE.sub("", text).strip()
    return text or None


def load_index(path=None):
    index_path = pathlib.Path(path) if path else INDEX_PATH
    if not index_path.exists():
        return {}
    with open(index_path, "r", encoding="utf-8") as f:
        return json.load(f)


def lookup(znacka, index):
    """Returns {"title": str, "description": str} for `znacka`, or None
    when its normalized designation isn't in `index` — the expected,
    common case (60 of 101 corpus DVGW designations), never guessed
    past."""
    designation = normalize_designation(znacka)
    if designation is None:
        return None
    entry = index.get(designation)
    if entry is None:
        return None
    return {"title": entry.get("title"), "description": entry.get("description")}
