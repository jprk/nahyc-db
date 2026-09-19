"""Research Agent (doc/PLAN.md §3.2/§3.3 step 4) — runs ONLY when a
verified extraction still has null fields the existing authoritative-
source tools can fill; replaces `search_agent.py` (generic DuckDuckGo
search) with the same real, structured EUR-Lex Cellar lookups already
used by `add_eurlex_hydrogen_acts.py`/`backfill_eu_gestor.py`, instead
of a new tool-calling layer -- the actual data source, not a wrapper
around a search engine.

Deliberately narrow: only fills `nazev`/`gestor` for a EUR-Lex-sourced
candidate. Anything else stays null and the record is still `needs_review`
-- never guessed at.
"""
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
from sites.eurlex import extract, fetch_responsible_gestor  # noqa: E402


def needs_research(extracted: dict) -> bool:
    if not extracted:
        return False
    return not extracted.get("nazev") or not extracted.get("gestor")


def apply_research(extracted: dict, url: str, session=None) -> dict:
    """Returns a NEW dict with any missing `nazev`/`gestor` filled in
    from live EUR-Lex Cellar lookups where possible. Fields that still
    can't be resolved are left as-is (None/missing) -- this agent fills
    gaps, it doesn't invent data."""
    result = dict(extracted)

    if not result.get("nazev"):
        meta = extract(url, session=session)
        if meta and meta.get("title"):
            result["nazev"] = meta["title"]

    if not result.get("gestor"):
        gestor = fetch_responsible_gestor(
            url,
            identifier=result.get("znacka"),
            title=result.get("nazev"),
            type_name=result.get("typ_dokumentu"),
            session=session,
        )
        if gestor:
            result["gestor"] = gestor

    return result
