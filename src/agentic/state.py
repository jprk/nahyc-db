"""Shared state schema for the LangGraph `StateGraph` implementing
doc/PLAN.md §3's agentic architecture — doc/PLAN.md §45, 2026-09-19,
user-directed (explicitly overriding §5's earlier "not adopted this
pass" decision, on this `automation` branch only).

One `PipelineState` instance flows through every node
(Parser → Extraction → Verification → [retry|escalate] → Research →
Reconciliation → HITL) — LangGraph merges each node's returned dict into
the running state, so a node only needs to return the keys it changes.
"""
from typing import Any, Dict, List, Optional, TypedDict


class Candidate(TypedDict, total=False):
    """The input record from a source-screening file (`data/
    fulltext_screening_candidates.json`, `screen_eurlex.py`/`screen_
    esbirka.py`/`screen_slovlex.py`) — deliberately the SAME shape those
    scripts already produce, not a new one."""
    title: str
    url: str
    celex: Optional[str]
    matched_keyword: Optional[str]
    source: str  # "EUR-Lex" | "e-Sbirka" | "Slov-Lex"


class PipelineState(TypedDict, total=False):
    # --- input -----------------------------------------------------------
    candidate: Candidate

    # --- Parser Agent (src/agentic/parser.py) -----------------------------
    raw_text: Optional[str]
    parse_error: Optional[str]

    # --- Extraction Agent (src/agentic/extraction.py) ---------------------
    extracted: Optional[Dict[str, Any]]
    extraction_error: Optional[str]

    # --- Verification Agent (src/agentic/verification.py) -----------------
    verified: bool
    failed_quotes: List[str]
    retry_count: int

    # --- Research Agent (src/agentic/research.py) --------------------------
    research_applied: bool

    # --- Reconciliation Agent (src/agentic/reconciliation.py) --------------
    reconciliation_action: Optional[str]  # "new" | "existing" | "ambiguous"
    matched_znacka: Optional[str]

    # --- Human-in-the-loop -------------------------------------------------
    escalated: bool
    escalation_reason: Optional[str]


MAX_VERIFICATION_ATTEMPTS = 3


def initial_state(candidate: Candidate) -> PipelineState:
    return PipelineState(
        candidate=candidate,
        raw_text=None,
        parse_error=None,
        extracted=None,
        extraction_error=None,
        verified=False,
        failed_quotes=[],
        retry_count=0,
        research_applied=False,
        reconciliation_action=None,
        matched_znacka=None,
        escalated=False,
        escalation_reason=None,
    )
