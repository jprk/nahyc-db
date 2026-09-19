"""Extraction Agent (doc/PLAN.md §3.2/§3.3 step 2, second half) — pulls
structured fields out of Parser-Agent text into a schema-validated JSON
object, replacing the one-shot LLM calls in `enrich_eu_laws.py`/
`process_laws.py`/`enrich_annotations.py`.

Client-loading, retry-cap, and `response_format=json_object` conventions
copied verbatim from `src/tools/add_eurlex_hydrogen_acts.py`'s
`classify_relevance_with_llm()` — same reason: this script must keep
degrading to "needs_review" (never guess) when `.openapi_key` is
missing, so it must not `exit(1)` the way the interactive-only
`deduplicate_db.py` does.

The one addition this schema has that none of the older enrichment
scripts required: every extraction MUST include a
`verification_evidence` array of verbatim quotes from the source text —
`src/agentic/verification.py:verify_evidence()` is the gate that checks
them before anything downstream trusts this output.
"""
import json
import os
import pathlib
import time

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_API_KEY_PATH = REPO_ROOT / ".openapi_key"
client = None
try:
    with open(_API_KEY_PATH, "r", encoding="utf-8") as _f:
        os.environ["OPENAI_API_KEY"] = _f.read().strip()
    from openai import OpenAI
    client = OpenAI()
except FileNotFoundError:
    pass

MAX_LLM_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2

_EXTRACTION_SYSTEM_PROMPT = """You are a metadata-extraction agent for a Czech/EU hydrogen-technology \
regulatory database. You are given the full text of a legal act and must extract structured \
metadata about it.

Respond with a JSON object with exactly these keys:
- "znacka": the act's official designation/reference number (e.g. "(EU) 2023/1804"), or null if not \
found in the text.
- "nazev": the act's full official title, or null if not found.
- "typ_dokumentu": one of "Nařízení EU", "Směrnice EU", "Rozhodnutí EU", "Zákon", "Vyhláška", "Jiné".
- "gestor": the single institution/Directorate-General explicitly named in the text as responsible for \
or having enacted this act (e.g. "Evropská komise"), or null if the text doesn't state one.
- "verification_evidence": a JSON array of 1-5 short strings, each a VERBATIM quote copied exactly \
from the source text below, that together support the "znacka" and "nazev" values you extracted. \
Every quote MUST appear character-for-character in the source text (aside from whitespace). Do not \
paraphrase, translate, or summarize in this field. If you cannot find supporting verbatim text, \
return an empty array here rather than inventing a quote."""


def extract_with_llm(source_text: str):
    """Returns the parsed extraction dict, or None if the client isn't
    configured or every attempt failed. Callers MUST treat None as
    "unknown" (route to escalate), never as an empty/default record."""
    if client is None:
        return None

    # Truncated, not summarized -- a summary would defeat the point of
    # verbatim-quote verification against the ORIGINAL text.
    user_content = source_text[:12000]

    last_error = None
    for attempt in range(1, MAX_LLM_ATTEMPTS + 1):
        try:
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": _EXTRACTION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.0,
            )
            result = json.loads(completion.choices[0].message.content)
            if not isinstance(result.get("verification_evidence"), list):
                last_error = "verification_evidence missing or not a list"
                if attempt < MAX_LLM_ATTEMPTS:
                    time.sleep(RETRY_BACKOFF_SECONDS * attempt)
                continue
            return result
        except Exception as e:
            last_error = str(e)
            if attempt < MAX_LLM_ATTEMPTS:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)

    print(f"[warn] extraction failed after {MAX_LLM_ATTEMPTS} attempts: {last_error}")
    return None


def extract_with_retry_feedback(source_text: str, failed_quotes=None, llm_extractor=extract_with_llm):
    """Same as `llm_extractor(source_text)`, but when `failed_quotes` is
    non-empty (a prior Verification-Agent pass rejected specific quotes),
    appends them to the prompt so the retry attempt knows exactly what
    to fix -- doc/PLAN.md §3.3 step 3's "retry with the specific failed
    quotes appended" behavior. Injectable `llm_extractor` for tests,
    same convention as `add_eurlex_hydrogen_acts.py:assess_relevance()`.
    """
    if not failed_quotes:
        return llm_extractor(source_text)

    feedback = (
        "\n\nA previous extraction attempt included these quotes in "
        "verification_evidence, but they do NOT appear verbatim in the "
        "source text above -- do not repeat them, and only quote text "
        "that genuinely appears above:\n" + "\n".join(f"- {q!r}" for q in failed_quotes)
    )
    return llm_extractor(source_text + feedback)
