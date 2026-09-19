"""doc/PLAN.md §3.3 — the actual LangGraph `StateGraph` wiring the agent
roster (§3.2) into the 6-step pipeline: Parse -> Extract -> Verify ->
[retry up to MAX_VERIFICATION_ATTEMPTS | escalate] -> Research (conditional)
-> Reconcile -> [escalate on ambiguous match | done].

Every dependency (parser, LLM extractor, DB connection) is passed into
`build_graph()` as a keyword default, never imported and called directly
inside a node body -- this is what makes the deterministic pieces
(everything except the two real I/O boundaries) testable by injecting a
fake in place of a real fetch/LLM/DB call, same convention as
`add_eurlex_hydrogen_acts.py:assess_relevance(..., llm_classifier=...)`.
"""
import pathlib
import sys

from langgraph.graph import END, StateGraph

BASE_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR.parent))  # src/ on sys.path for `agentic.*`

from agentic import extraction, parser, reconciliation, research, verification  # noqa: E402
from agentic.state import MAX_VERIFICATION_ATTEMPTS, PipelineState, initial_state  # noqa: E402


def build_graph(
    parse_source=parser.parse_source,
    llm_extractor=extraction.extract_with_llm,
    get_connection=reconciliation.get_connection,
    research_applier=research.apply_research,
):
    """Returns a compiled LangGraph app. All four dependencies default to
    the real implementations; tests override some or all of them."""

    def parse_node(state: PipelineState) -> dict:
        url = state["candidate"].get("url")
        raw_text, error = parse_source(url)
        return {"raw_text": raw_text, "parse_error": error}

    def decide_after_parse(state: PipelineState) -> str:
        return "escalate" if state.get("parse_error") else "extract"

    def extract_node(state: PipelineState) -> dict:
        extracted = extraction.extract_with_retry_feedback(
            state["raw_text"], state.get("failed_quotes"), llm_extractor=llm_extractor,
        )
        retry_count = state.get("retry_count", 0) + 1
        if extracted is None:
            return {"extracted": None, "extraction_error": "extraction unavailable or failed",
                     "retry_count": retry_count}
        return {"extracted": extracted, "extraction_error": None, "retry_count": retry_count}

    def verify_node(state: PipelineState) -> dict:
        extracted = state.get("extracted")
        if extracted is None:
            return {"verified": False, "failed_quotes": []}
        verified, failed_quotes = verification.verify_evidence(extracted, state["raw_text"])
        return {"verified": verified, "failed_quotes": failed_quotes}

    def decide_after_verify(state: PipelineState) -> str:
        if state.get("verified"):
            return "research"
        if state.get("retry_count", 0) >= MAX_VERIFICATION_ATTEMPTS:
            return "escalate"
        return "extract"

    def research_node(state: PipelineState) -> dict:
        extracted = state.get("extracted") or {}
        if not research.needs_research(extracted):
            return {"research_applied": False}
        url = state["candidate"].get("url")
        updated = research_applier(extracted, url)
        return {"extracted": updated, "research_applied": True}

    def reconcile_node(state: PipelineState) -> dict:
        extracted = state.get("extracted") or {}
        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                result = reconciliation.reconcile(extracted.get("znacka"), extracted.get("nazev"), cursor)
        finally:
            conn.close()
        return {"reconciliation_action": result["action"], "matched_znacka": result["matched_znacka"]}

    def decide_after_reconcile(state: PipelineState) -> str:
        return "escalate" if state.get("reconciliation_action") == "ambiguous" else "end"

    def escalate_node(state: PipelineState) -> dict:
        if state.get("parse_error"):
            reason = f"parse failed: {state['parse_error']}"
        elif not state.get("verified"):
            reason = (f"verification failed after {state.get('retry_count', 0)} attempt(s): "
                      f"{state.get('failed_quotes')}")
        elif state.get("reconciliation_action") == "ambiguous":
            reason = f"ambiguous match against existing identifier {state.get('matched_znacka')!r}"
        else:
            reason = "escalated"
        return {"escalated": True, "escalation_reason": reason}

    graph = StateGraph(PipelineState)
    graph.add_node("parse", parse_node)
    graph.add_node("extract", extract_node)
    graph.add_node("verify", verify_node)
    graph.add_node("research", research_node)
    graph.add_node("reconcile", reconcile_node)
    graph.add_node("escalate", escalate_node)

    graph.set_entry_point("parse")
    graph.add_conditional_edges("parse", decide_after_parse, {"extract": "extract", "escalate": "escalate"})
    graph.add_edge("extract", "verify")
    graph.add_conditional_edges(
        "verify", decide_after_verify,
        {"extract": "extract", "research": "research", "escalate": "escalate"},
    )
    graph.add_edge("research", "reconcile")
    graph.add_conditional_edges("reconcile", decide_after_reconcile, {"escalate": "escalate", "end": END})
    graph.add_edge("escalate", END)

    return graph.compile()


def run_candidate(candidate, **build_graph_kwargs) -> PipelineState:
    app = build_graph(**build_graph_kwargs)
    return app.invoke(initial_state(candidate))
