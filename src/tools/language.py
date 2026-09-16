"""Shared language-code resolution for `Document.language`.

Used by `init_db.py` (initial import from the merged JSON) and
`backfill_language.py` (one-time DB backfill for records imported before
this normalization existed). Only four codes are ever produced — EN, CS,
SK, DE — the only languages actually present in this corpus, confirmed
empirically (2026-09-15) against sample titles from every `jurisdikce`
value: `jurisdikce` alone is not a reliable proxy for language (e.g. many
`DE`/`US`/`mezinárodní`-jurisdikce records have English-language titles),
so detection runs on the title/description text itself.
"""
from langdetect import DetectorFactory, LangDetectException, detect_langs

DetectorFactory.seed = 0  # reproducible detection across runs

TARGET_LANGUAGES = {"en", "cs", "sk", "de"}
LANG_CODE_MAP = {"en": "EN", "cs": "CS", "sk": "SK", "de": "DE"}

# Known messy raw `jazyk` values seen in the source spreadsheets/merged
# JSON — mapped directly, no detection needed.
RAW_LANGUAGE_MAP = {
    "en": "EN", "eng": "EN", "angličtina": "EN", "anglictina": "EN",
    "cs": "CS", "cz": "CS", "čeština": "CS", "cestina": "CS",
    "sk": "SK", "slovenština": "SK", "slovencina": "SK",
    "de": "DE", "němčina": "DE", "nemcina": "DE",
}

CONFIDENCE_THRESHOLD = 0.85

# doc/PLAN.md §23, 2026-09-17 (user-directed): some source systems can
# structurally only ever host documents in one language, regardless of
# what a raw `jazyk` value says or what langdetect guesses from
# title/description text — Czech and Slovak in particular are close
# enough that langdetect regularly misreads a short Czech legal title as
# Slovak. Checked BEFORE normalize_raw_language()/detect_language(): the
# domain fact is not a guess, it overrides even a wrong raw `jazyk` value
# or a confident-but-mistaken detection. Substring match against the
# document's own URL, not `zdroj_dat` — a record can be *about* a source
# without being hosted there.
DOMAIN_LANGUAGE_OVERRIDES = (
    # e-sbirka.gov.cz is the Czech Republic's own official legal-register
    # portal (Sbírka zákonů) — it publishes Czech legislation only; no
    # Slovak-language act has ever appeared there. Confirmed 2026-09-17:
    # 2 of 32 e-sbirka-hosted records in the live corpus were wrongly
    # detected as SK before this override existed.
    ("e-sbirka.gov.cz", "CS"),
)


def resolve_domain_language_override(url):
    """(code) for a handful of source domains that structurally can only
    ever host one language, or None for any other URL (the overwhelming
    majority) — see DOMAIN_LANGUAGE_OVERRIDES above for why this takes
    priority over both normalize_raw_language() and detect_language()."""
    value = (url or "").strip().lower()
    if not value:
        return None
    for domain, code in DOMAIN_LANGUAGE_OVERRIDES:
        if domain in value:
            return code
    return None


def normalize_raw_language(raw):
    """Maps a raw `jazyk` source value to one of EN/CS/SK/DE, or None if
    blank/unrecognized (caller then falls back to detect_language)."""
    value = (raw or "").strip().lower()
    return RAW_LANGUAGE_MAP.get(value)


def _detect_text(text):
    """(code, prob) for the highest-probability EN/CS/SK/DE candidate in
    `text`, or (None, 0.0) if empty/undetectable/no target-language
    candidate at all."""
    text = (text or "").strip()
    if not text:
        return None, 0.0
    try:
        candidates = detect_langs(text)
    except LangDetectException:
        return None, 0.0
    target_candidates = [c for c in candidates if c.lang in TARGET_LANGUAGES]
    if not target_candidates:
        return None, 0.0
    best = max(target_candidates, key=lambda c: c.prob)
    return LANG_CODE_MAP[best.lang], best.prob


def detect_language(title, description=None):
    """Best-effort (code, confident) for a document's language.

    Detection runs on the *title* alone first — empirically (2026-09-15,
    spot-checked against the jurisdikce=SK subset) far more reliable than
    including the description, because many records' description is a
    generic scope/abstract carried over in a *different* language than
    the document itself (e.g. a Slovak-titled EN standard whose stored
    description is the German-language scope text) — concatenating it
    just drowns out the short title with the description's language.
    Description is only consulted as a fallback: when the title alone is
    empty or inconclusive, and only to fill in (or, if it agrees with an
    unconfident title guess, to confirm) — never to override a confident
    title-based result. `confident` is False when nothing reliable could
    be determined and the caller should flag the record for manual review
    instead of silently asserting a guess."""
    title_code, title_prob = _detect_text(title)
    if title_code and title_prob >= CONFIDENCE_THRESHOLD:
        return title_code, True

    desc_code, desc_prob = _detect_text(description)

    if title_code and desc_code == title_code and desc_prob >= CONFIDENCE_THRESHOLD:
        return title_code, True
    if title_code:
        return title_code, False
    if desc_code:
        return desc_code, desc_prob >= CONFIDENCE_THRESHOLD
    return "EN", False
