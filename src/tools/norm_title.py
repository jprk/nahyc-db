"""Shared title/designation formatting for `Document` rows of type
`Norma` (used by `init_db.py` and `backfill_norm_designation.py`).

User finding (2026-09-15): technical-standard titles never surface their
own designation number (`Document.identifier`, e.g. "ČSN EN 17124") — the
app has never queried or displayed that column at all, only `title`,
which for most `Norma` records (esp. anything from Sinay's dataset) is
just the plain description with no number. A handful of Sinay records DO
carry the designation, but only ever embedded inside the title text
itself, and always as a trailing "(DESIGNATION:YYYY)" parenthetical
rather than a leading label. Law/EU-act titles are a different, working
case (their designation is naturally part of the legislative phrasing,
e.g. "Nařízení ... (EU) 2023/1184 ze dne ...") and are intentionally out
of scope here — this module is Norma-specific.
"""
import re

_EDITION_SUFFIX_RE = re.compile(r"\s*/?\s*-\s*\d{4}(\.\d{2})?\s*$")
_HAS_DIGIT_RE = re.compile(r"\d")


def designation_core(identifier):
    """Strips a trailing edition/date artifact (e.g. "/ - 2016.08") left
    over from Sinay's PDF-parsed `znacka` — the same pattern
    `deduplicate_db.py`'s `normalize_znacka()` strips for clustering, but
    never rewrites in the stored `identifier` value itself."""
    return _EDITION_SUFFIX_RE.sub("", identifier or "").strip()


def is_real_designation(identifier):
    """A handful of `identifier` values are not real designations at all
    — either NULL, or (for records whose source data has no number, e.g.
    a BVEG/AGBF German industry guidance leaflet) a raw fallback copy of
    the title/a fragment of it. Every genuine standard designation found
    in this corpus contains at least one digit (STN/ČSN/DIN/ISO/IEC/...
    always number their documents); that's a reliable, simple filter —
    confirmed by manually reviewing every record it excludes (2026-09-15,
    26 records, all confirmed to genuinely lack a designation)."""
    return bool(identifier) and bool(_HAS_DIGIT_RE.search(identifier))


def _strip_designation_from_title(title, core):
    """Removes one leading or trailing occurrence of `core` from `title`
    — bare, or (the only shape actually found in this corpus) wrapped in
    parentheses with an optional ":YYYY" edition year, e.g.
    "(IEC/TR 62351-13:2016)" — along with adjoining punctuation/
    whitespace, so it isn't shown twice once the caller prefixes the
    canonical designation."""
    title = title.strip()
    if not core:
        return title
    esc = re.escape(core)

    trailing_paren_re = re.compile(
        r"\(\s*" + esc + r"(\s*:\s*\d{4})?\s*\)\s*$", re.IGNORECASE)
    m = trailing_paren_re.search(title)
    if m:
        return title[:m.start()].rstrip(" .,-–—").strip()

    trailing_re = re.compile(
        r"[\s.,\-–—:]+" + esc + r"\s*$", re.IGNORECASE)
    m = trailing_re.search(title)
    if m:
        candidate = title[:m.start()].rstrip(" .,-–—")
        if candidate:
            return candidate.strip()

    leading_re = re.compile(
        r"^\s*" + esc + r"[\s.,\-–—:]*", re.IGNORECASE)
    m = leading_re.match(title)
    if m:
        return title[m.end():].strip()

    return title


def format_norm_title(title, identifier):
    """Returns (new_title, changed). When `identifier` is a real
    designation (see is_real_designation), returns
    "<designation core> — <title, with any duplicate leading/trailing
    designation text stripped>"; otherwise returns `title` unchanged —
    there is genuinely no number to show, never fabricated."""
    title = (title or "").strip()
    identifier = (identifier or "").strip()
    if not is_real_designation(identifier):
        return title, False
    core = designation_core(identifier) or identifier
    cleaned = _strip_designation_from_title(title, core) or title
    return f"{core} — {cleaned}", True
