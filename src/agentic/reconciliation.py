"""Reconciliation Agent (doc/PLAN.md §3.2/§3.3 step 5) — deterministic
`identifier` match first, heuristic title-similarity fallback second;
**never auto-merges**, only classifies as "new" / "existing" /
"ambiguous" for a human (or a downstream ingestion script that already
has its own overlay-not-overwrite discipline) to act on.

Replaces `deduplicate_db.py`'s dedup logic for THIS pipeline's own
candidates only -- it does not touch `deduplicate_db.py` itself.
`reference_number` (§3.2's term) is this schema's `Document.identifier`
(== `znacka` in the raw JSON pipeline, per `doc/konsolidace/
Konsolidace-DB-schema.sql` line 21-23).

The "semantic fallback" §3.2 calls for is deliberately a plain
title-token-overlap heuristic, not an embeddings/cosine-similarity
re-implementation -- honestly labeled as a heuristic (see
`title_overlap_score()`), proportionate to what this reconciliation
step actually needs (a second, coarser signal for the human doing final
triage), not a second full ML subsystem.
"""
import os
import pathlib
import re
import sys

import pymysql
from dotenv import load_dotenv

BASE_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "tools"))
from link_document_relations_auto import digit_core  # noqa: E402

# Above this token-overlap ratio, two titles are flagged "ambiguous"
# (possibly the same act under a slightly different title) rather than
# silently treated as unrelated "new" candidates.
TITLE_OVERLAP_AMBIGUOUS_THRESHOLD = 0.6

_WORD_RE = re.compile(r"\w+", re.UNICODE)


def get_connection(env_file=".env"):
    load_dotenv(REPO_ROOT / env_file, override=True)
    return pymysql.connect(
        host=os.environ["DB_HOST"], port=int(os.environ["DB_PORT"]),
        user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"], autocommit=False,
    )


def title_overlap_score(a: str, b: str) -> float:
    """Jaccard overlap of lowercased word sets -- a deliberately simple,
    honestly-labeled heuristic (see module docstring), not semantic
    similarity."""
    words_a = set(_WORD_RE.findall((a or "").lower()))
    words_b = set(_WORD_RE.findall((b or "").lower()))
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)


def reconcile(identifier, title, cursor):
    """Queries the LIVE database (via an already-open DB-API `cursor` --
    injectable for tests, matching this project's mocked-cursor
    convention) and returns one of:
      {"action": "existing", "matched_znacka": "..."}   -- exact identifier match
      {"action": "ambiguous", "matched_znacka": "..."}  -- similar title, no exact id match
      {"action": "new", "matched_znacka": None}          -- no plausible match found
    """
    core = digit_core(identifier) if identifier else None
    if core:
        cursor.execute("SELECT identifier FROM Document WHERE identifier IS NOT NULL")
        for (existing_identifier,) in cursor.fetchall():
            if digit_core(existing_identifier) == core:
                return {"action": "existing", "matched_znacka": existing_identifier}

    if title:
        cursor.execute("SELECT identifier, title FROM Document")
        best_score, best_identifier = 0.0, None
        for existing_identifier, existing_title in cursor.fetchall():
            score = title_overlap_score(title, existing_title)
            if score > best_score:
                best_score, best_identifier = score, existing_identifier
        if best_score >= TITLE_OVERLAP_AMBIGUOUS_THRESHOLD:
            return {"action": "ambiguous", "matched_znacka": best_identifier}

    return {"action": "new", "matched_znacka": None}
