"""Verification Agent (doc/PLAN.md §3.2/§3.3 step 3) — deterministic,
NOT a second LLM call. Rejects any Extraction Agent output whose
`verification_evidence` quotes don't appear verbatim (after light
normalization) in the source text the Extraction Agent was actually
given.

This is the gate none of the pre-existing enrichment scripts
(`enrich_eu_laws.py`, `process_laws.py`, `enrich_annotations.py`) have —
it's what would have caught the untrustworthy 281->165 dedup run.
"""
import re
from typing import Dict, List, Tuple


def normalize_text(text: str) -> str:
    """Collapse whitespace and lowercase, so a quote that merely differs
    by a line-wrap or a double space still matches. Deliberately does
    NOT strip punctuation or accents — a quote that changes wording
    should fail verification, not be forgiven by normalization."""
    return re.sub(r"\s+", " ", text.strip().lower())


def verify_evidence(extracted: Dict, source_text: str) -> Tuple[bool, List[str]]:
    """Checks every string in `extracted["verification_evidence"]`
    against `source_text`. Returns (all_verified, failed_quotes).

    An extraction with a missing/empty `verification_evidence` array
    fails closed (verified=False) — silence is not evidence.
    """
    quotes = extracted.get("verification_evidence") if extracted else None
    if not quotes:
        return False, ["<missing verification_evidence>"]

    normalized_source = normalize_text(source_text or "")
    failed = [q for q in quotes if normalize_text(q) not in normalized_source]
    return (len(failed) == 0), failed
