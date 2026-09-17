"""Converts `screen_eurlex.py`'s screening candidates into real, verified
Document records — doc/PLAN.md §28, 2026-09-17, user-directed corpus
expansion (feedback: the database is missing documents; a colleague's
AI-model cross-check found "a lot" not in our list, which we're rightly
skeptical of hallucination from).

**The hard rule this whole script exists to enforce**: nothing is ever
added on the strength of a title string or an LLM's say-so. Every
record written here traces to a CELEX id independently re-confirmed,
right now, against the live EUR-Lex Cellar SPARQL endpoint — the same
public, unauthenticated, structured-data source `screen_eurlex.py`/
`src/sites/eurlex.py` already use elsewhere in this pipeline. A
candidate that doesn't resolve live is skipped, not guessed at.

Three deliberate narrowings, each logged separately rather than applied
silently:

1. **Only binding legislative act types** (Regulation/Directive/
   Decision — CELEX type letters R/L/D) are auto-added. A live sample of
   `screen_eurlex.py`'s own candidates included real regulatory acts
   *and* administrative ephemera (calls for proposals, staff working
   papers, annual-accounts reports) that this database shouldn't carry
   as if they were regulation — those go to
   `data/eurlex_administrative_not_imported.json` for visibility, not
   silently discarded.
2. **Re-diffed against the CURRENT `database_merged_raw.json`**, not the
   stale snapshot `screen_eurlex.py` last wrote — this corpus has grown
   since that screening run (normoff/eiga/iec/dvgw work all landed new
   records that could coincidentally overlap).
3. **Title re-fetched live via `src/sites/eurlex.py:extract()`**, never
   taken from the screening snapshot — a candidate whose CELEX no longer
   resolves to any title (withdrawn from Cellar, or the id was never
   quite right) is skipped and logged, not added with a stale title.
4. **Off-topic chemistry/administrative false positives are filtered
   out** — a bare "hydrogen" title match also hits "hydrogen peroxide"
   biocide authorisations, "hydrogen carbonate" (bicarbonate) pesticide
   approvals, "hydrogen cyanide" biocides, "hydrogen phosphate"
   biocides, and the odd customs/competition-case notice that happens to
   name a hydrogen-containing compound — none of these are about
   hydrogen as an energy carrier. Two layers, doc/PLAN.md §28/§29:
   a) a deterministic pattern deny-list (`OFF_TOPIC_TITLE_PATTERNS`
      below), derived from a manually-classified live batch (13/51
      genuinely relevant, 38/51 this kind of false positive);
   b) for whatever the pattern list DOESN'T catch — a new false-positive
      vocabulary the deny-list was never written for — an LLM relevance
      judgment (`classify_relevance_with_llm`) scores the title 0-100 for
      "probability this is off-topic". A high score excludes the same
      way the pattern match does; a low score proceeds to import; a
      score in between (the LLM itself is unsure), or the LLM being
      unreachable, is never guessed at either way — it's queued to
      `data/eurlex_relevance_review_queue.json` for a human to decide.
   Every one of these three outcomes (pattern match, LLM high-confidence
   exclude, LLM/network uncertain) is logged to a file, never silently
   dropped.

Usage:
    .venv/bin/python src/tools/add_eurlex_hydrogen_acts.py [--limit N]

Output: appends verified records to `data/discovered_eu_hydrogen_acts.json`
(loaded by `build_unified_db.py` as an 8th source, same `load_json()` +
`unified_db.extend()` pattern as `eu_transposition_targets.json`), and
writes/updates `data/eurlex_administrative_not_imported.json` (non-
binding act types), `data/eurlex_off_topic_not_imported.json`
(off-topic chemistry/administrative matches, pattern- or LLM-caught),
and `data/eurlex_relevance_review_queue.json` (LLM unsure, or LLM call
unavailable/failed) for candidates found but not imported.
"""
import argparse
import json
import os
import pathlib
import re
import sys
import time

import requests

BASE_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(REPO_ROOT / "src"))

from screen_eurlex import (CANDIDATES_PATH, RAW_DB_PATH,  # noqa: E402
                          celex_candidate_znackas, load_known_znacka_digits,
                          normalize_for_diff)
from sites.eurlex import USER_AGENT, extract, fetch_responsible_gestor  # noqa: E402

OUTPUT_PATH = REPO_ROOT / "data" / "discovered_eu_hydrogen_acts.json"
ADMINISTRATIVE_PATH = REPO_ROOT / "data" / "eurlex_administrative_not_imported.json"
OFF_TOPIC_PATH = REPO_ROOT / "data" / "eurlex_off_topic_not_imported.json"
REVIEW_QUEUE_PATH = REPO_ROOT / "data" / "eurlex_relevance_review_queue.json"
SLEEP_SECONDS = 1

# doc/PLAN.md §29, 2026-09-17, user-directed: an LLM backstop for
# whatever OFF_TOPIC_TITLE_PATTERNS doesn't already catch. Loaded the
# same way `deduplicate_db.py` loads its OpenAI client, but deliberately
# does NOT exit(1) on a missing key file — this script must keep working
# (degrading every LLM-stage candidate to "needs_review", never to a
# guess) even where `.openapi_key` isn't present, unlike deduplicate_db.py
# which is only ever run interactively.
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

# Score is "probability this title is off-topic" (0 = clearly hydrogen-
# as-energy, 100 = clearly something else that just names a hydrogen
# compound). Two thresholds, not one, so a score the LLM itself isn't
# confident about is never silently resolved either way:
#   score >= HIGH_OFF_TOPIC_THRESHOLD  -> excluded, same as a pattern hit
#   score <= LOW_ON_TOPIC_THRESHOLD    -> proceeds to import
#   in between                        -> data/eurlex_relevance_review_queue.json
HIGH_OFF_TOPIC_THRESHOLD = 75
LOW_ON_TOPIC_THRESHOLD = 25

SOURCE_NAME = "EU_Hydrogen_Discovery"

# Only the sector-3 (legislation) single-letter CELEX type codes for a
# binding legislative act — deliberately NOT the full CELEX type-letter
# table (Recommendations, Opinions, ECSC-era acts, ...): a conservative
# allow-list, same "explicit opt-in, not inferred" discipline as
# translate_annotations.py's TRANSLATABLE_DOMAINS.
_CELEX_TYPE_RE = re.compile(r"^\d\d{4}([A-Z])\d{4,}")

BINDING_ACT_TYPES = {
    "R": "Nařízení EU",
    "L": "Směrnice EU",
    "D": "Rozhodnutí EU",
}

# A live full-batch run (2026-09-17, doc/PLAN.md §28) found that a bare
# "hydrogen" title match is dominated by chemistry/administrative acts
# that happen to name a compound containing the word "hydrogen" — NOT
# hydrogen as an energy carrier at all: "hydrogen peroxide" biocide
# authorisations (regulation 528/2012), "potassium/sodium hydrogen
# carbonate" (bicarbonate) and "hydrogen cyanide" pesticide active-
# substance approvals (regulation 1107/2009) and MRLs (regulation
# 396/2005), a "silver-sodium-zirconium hydrogen phosphate" biocide, a
# "sodium hydrogen glutamate" customs-tariff notice, a 2006 hydrogen
# peroxide/perborate cartel decision, and a 1981 customs ruling on a gas
# chromatograph with a "hydrogen generator" accessory. Of 51 live-
# verified binding acts in that run, 38 were this kind of false
# positive — manually confirmed against each title. These patterns
# (Czech + English, the two languages `screen_eurlex.py`/`extract()`
# surface) exclude exactly that vocabulary; genuine hydrogen-energy acts
# (fuel cell/hydrogen joint undertaking, hydrogen-powered vehicle type-
# approval, hydrogen refuelling infrastructure, the hydrogen market
# support mechanism) matched none of them in that same batch. Excluded,
# not silently discarded — logged to `eurlex_off_topic_not_imported.json`
# for visibility, same discipline as the non-binding-type list above.
OFF_TOPIC_TITLE_PATTERNS = [
    r"peroxid",                      # peroxid(u) vodíku / hydrogen peroxide / peroxyoctová
    r"biocid",                       # regulation 528/2012 biocidal-product authorisations
    r"kyanovod[ií]k",                # hydrogen cyanide
    r"hydrogen cyanide",
    r"hydrogenuhličitan",            # potassium/sodium hydrogen carbonate (bicarbonate)
    r"hydrogen carbonate",
    r"bicarbonate",
    r"hydrogenfosforečnan",          # silver-sodium-zirconium hydrogen phosphate
    r"hydrogen phosphate",
    r"hydrogen glutamate",
    r"custom(s|ní) (duties|tariff|sazebník)",
    r"common customs tariff",
]
_OFF_TOPIC_RE = re.compile("|".join(OFF_TOPIC_TITLE_PATTERNS), re.IGNORECASE)


def is_off_topic(title):
    """True when a (live, re-verified) title matches known chemistry/
    administrative false-positive vocabulary rather than hydrogen as an
    energy carrier — see OFF_TOPIC_TITLE_PATTERNS above for the batch
    this was derived from."""
    return bool(_OFF_TOPIC_RE.search(title or ""))


_RELEVANCE_SYSTEM_PROMPT = """You are a relevance classifier for a Czech/EU hydrogen-technology \
regulatory database. The database tracks hydrogen ONLY as an energy carrier / fuel: hydrogen \
production, storage, transport, refuelling infrastructure, fuel cells, hydrogen-powered vehicles, \
and the hydrogen energy market.

Every title you are given already passed a keyword search for "hydrogen"/"vodík" and already \
passed a filter for binding EU legislative act types (Regulation/Directive/Decision) — so it IS a \
real, binding EU act, and it DOES contain that keyword. Your only job is to judge whether the act \
is actually ABOUT hydrogen as an energy carrier, or whether "hydrogen" only appears because of an \
unrelated chemical compound name (hydrogen peroxide, hydrogen carbonate/bicarbonate, hydrogen \
cyanide, hydrogen phosphate, ...), a biocide/pesticide/plant-protection-product authorisation, a \
customs tariff classification, a competition/antitrust case, or similar administrative matter with \
no connection to hydrogen energy.

Respond with a JSON object: {"off_topic_probability": <integer 0-100>, "reasoning": "<one short \
sentence>"}. 0 means certainly about hydrogen as an energy carrier; 100 means certainly unrelated \
(just a compound name or administrative matter). Use the full range, including the middle, when \
genuinely unsure."""


def classify_relevance_with_llm(title, matched_keyword=None, celex=None):
    """Scores a title 0-100 for "probability this is off-topic" (see
    HIGH_OFF_TOPIC_THRESHOLD/LOW_ON_TOPIC_THRESHOLD). Returns
    {"off_topic_probability": int, "reasoning": str}, or None if the
    client isn't configured or every attempt failed — callers MUST treat
    None as "unknown" (route to human review), never default it to
    either on-topic or off-topic."""
    if client is None:
        return None

    user_content = json.dumps({
        "title": title,
        "matched_keyword": matched_keyword,
        "celex": celex,
    }, ensure_ascii=False)

    last_error = None
    for attempt in range(1, MAX_LLM_ATTEMPTS + 1):
        try:
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": _RELEVANCE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.0,
            )
            result = json.loads(completion.choices[0].message.content)
            score = result.get("off_topic_probability")
            if not isinstance(score, (int, float)) or not (0 <= score <= 100):
                last_error = f"invalid off_topic_probability: {score!r}"
                if attempt < MAX_LLM_ATTEMPTS:
                    time.sleep(RETRY_BACKOFF_SECONDS * attempt)
                continue
            return {"off_topic_probability": int(round(score)),
                    "reasoning": result.get("reasoning", "")}
        except Exception as e:
            last_error = str(e)
            if attempt < MAX_LLM_ATTEMPTS:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)

    print(f"[warn] relevance classification failed after {MAX_LLM_ATTEMPTS} attempts: {last_error}")
    return None


def assess_relevance(title, matched_keyword=None, celex=None, llm_classifier=classify_relevance_with_llm):
    """Combines the deterministic pattern deny-list with the LLM
    backstop into one verdict: "off_topic" (pattern hit, or LLM
    high-confidence), "on_topic" (LLM low-confidence off-topic), or
    "needs_review" (LLM score in the uncertain middle band, or the LLM
    couldn't be reached/didn't return a usable score at all — an
    unknown is never resolved as if it were a confident verdict).
    `llm_classifier` is injectable for tests."""
    if is_off_topic(title):
        return {"verdict": "off_topic", "method": "pattern", "score": None, "reasoning": None}

    result = llm_classifier(title, matched_keyword, celex)
    if result is None:
        return {"verdict": "needs_review", "method": "llm_unavailable", "score": None, "reasoning": None}

    score = result["off_topic_probability"]
    if score >= HIGH_OFF_TOPIC_THRESHOLD:
        verdict = "off_topic"
    elif score <= LOW_ON_TOPIC_THRESHOLD:
        verdict = "on_topic"
    else:
        verdict = "needs_review"
    return {"verdict": verdict, "method": "llm", "score": score, "reasoning": result["reasoning"]}


def celex_document_type_letter(celex):
    """The single CELEX type letter for a standard sector-3 legislative
    id ("32014R0559" -> "R"), or None for anything that doesn't match
    that shape (OJ "C" series notices, multi-letter preparatory-act ids,
    ...) — never guessed, treated as non-binding by the caller."""
    m = _CELEX_TYPE_RE.match(celex)
    return m.group(1) if m else None


def classify_candidate(candidate):
    """The Czech `typ_dokumentu` string for a binding act type, or None
    when this CELEX id isn't one of the explicitly whitelisted types."""
    letter = celex_document_type_letter(candidate["celex"])
    return BINDING_ACT_TYPES.get(letter)


def build_znacka(celex):
    """"(EU) 2014/559" from "32014R0559" — the canonical modern EU-act
    znacka shape already used elsewhere in this corpus (confirmed
    against real records: `Nařízení EU`/`Směrnice EU` both store
    "(EU) YYYY/NNN"). Unlike `celex_candidates_from_designation()`
    elsewhere (which has to guess between two possible year/number
    orderings from free text), there's no ambiguity here — the CELEX id
    itself already encodes year and number unambiguously."""
    m = re.match(r"^\d(\d{4})[A-Z](\d{4,})", celex)
    if not m:
        return None
    year, number = m.group(1), str(int(m.group(2)))
    return f"(EU) {year}/{number}"


def load_json(path):
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def build_document_record(candidate, doc_type, titles, gestor):
    """The full Document-shape dict — same field set as
    `data/eu_transposition_targets.json`'s hand-curated records, no
    extra bookkeeping keys (idempotency across runs of this script is
    handled by checking `znacka` against what's already in
    `OUTPUT_PATH`/the corpus, not a side-channel marker field). `jazyk`
    deliberately left blank (unlike that hand-curated file): this is a
    bulk, automated path, so language is left to the same
    `detect_language()`/`normalize_raw_language()` machinery every other
    bulk-imported record already goes through, not hand-asserted per
    record."""
    znacka = build_znacka(candidate["celex"]) or ""
    return {
        "zdroj_dat": SOURCE_NAME,
        "nazev_cz": titles["primary"],
        "znacka": znacka,
        "typ_dokumentu": doc_type,
        "sekce": "",
        "kategorie_trida": "",
        "klicova_slova": [],
        "odkaz_hlavni": candidate["url"],
        "nazev_eu": titles["primary"],
        "odkaz_eu": candidate["url"],
        "nazev_sk": "",
        "odkaz_sk": "",
        "platnost": "",
        "ratifikovan": "",
        "gestor": [gestor] if gestor else [],
        "jazyk": "",
        "anotace_poznamka": (
            f"Nalezeno screeningem EUR-Lex Cellar (klíčové slovo "
            f"{candidate['matched_keyword']!r}, doc/PLAN.md §28), ověřeno "
            f"živě proti CELEX {candidate['celex']} před doplněním."),
        "jurisdikce": "EU",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int, default=None,
                         help="process at most N candidates (for a manual smoke test)")
    args = parser.parse_args()

    with open(CANDIDATES_PATH, "r", encoding="utf-8") as f:
        candidates = json.load(f).get("EUR-Lex", [])

    with open(RAW_DB_PATH, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    known_digits = load_known_znacka_digits(raw_data)

    already_added = load_json(OUTPUT_PATH)
    already_added_digits = {normalize_for_diff(r["znacka"]) for r in already_added if r.get("znacka")}
    administrative = load_json(ADMINISTRATIVE_PATH)
    administrative_celex = {r["celex"] for r in administrative}
    off_topic = load_json(OFF_TOPIC_PATH)
    off_topic_celex = {r["celex"] for r in off_topic}
    review_queue = load_json(REVIEW_QUEUE_PATH)
    review_celex = {r["celex"] for r in review_queue}

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    added = []
    skipped_type = skipped_known = skipped_unresolved = 0
    skipped_off_topic = skipped_needs_review = 0
    processed = 0

    for candidate in candidates:
        if args.limit is not None and processed >= args.limit:
            break
        celex = candidate["celex"]
        processed += 1

        doc_type = classify_candidate(candidate)
        if doc_type is None:
            if celex not in administrative_celex:
                administrative.append(candidate)
                administrative_celex.add(celex)
            skipped_type += 1
            continue

        # Re-diff against the CURRENT corpus AND this run's own
        # already-added output (the latter guards against a duplicate if
        # this script is re-run before a full pipeline rebuild folds its
        # previous output back into database_merged_raw.json) — not the
        # stale screening snapshot, which the corpus has grown past
        # since screen_eurlex.py last ran.
        candidate_znackas = celex_candidate_znackas(celex)
        if candidate_znackas and any(
                normalize_for_diff(z) in known_digits or normalize_for_diff(z) in already_added_digits
                for z in candidate_znackas):
            skipped_known += 1
            continue

        # Re-fetch live — never trust the screening snapshot's title.
        result = extract(candidate["url"], session=session)
        if not result or not result.get("title"):
            skipped_unresolved += 1
            print(f"[skip] {celex}: no longer resolves via Cellar title query")
            time.sleep(SLEEP_SECONDS)
            continue

        # Checked against the freshly re-fetched title, not the
        # screening snapshot's — same "never trust the stale snapshot"
        # discipline as the title/gestor fetch itself. Pattern match
        # first (free, deterministic); LLM backstop only for whatever
        # the pattern list doesn't already catch.
        relevance = assess_relevance(result["title"], candidate.get("matched_keyword"), celex)

        if relevance["verdict"] == "off_topic":
            if celex not in off_topic_celex:
                off_topic.append({**candidate, "live_title": result["title"],
                                   "detection_method": relevance["method"],
                                   "llm_score": relevance["score"],
                                   "llm_reasoning": relevance["reasoning"]})
                off_topic_celex.add(celex)
            skipped_off_topic += 1
            print(f"[skip] {celex}: off-topic ({relevance['method']}): {result['title'][:70]}")
            time.sleep(SLEEP_SECONDS)
            continue

        if relevance["verdict"] == "needs_review":
            if celex not in review_celex:
                review_queue.append({**candidate, "live_title": result["title"],
                                      "detection_method": relevance["method"],
                                      "llm_score": relevance["score"],
                                      "llm_reasoning": relevance["reasoning"]})
                review_celex.add(celex)
            skipped_needs_review += 1
            print(f"[skip] {celex}: needs human review ({relevance['method']}, "
                  f"score={relevance['score']}): {result['title'][:70]}")
            time.sleep(SLEEP_SECONDS)
            continue

        gestor = fetch_responsible_gestor(candidate["url"], session=session)
        record = build_document_record(candidate, doc_type, {"primary": result["title"]}, gestor)
        added.append(record)
        # Extend in-memory state too, not just on disk — a later
        # candidate in the SAME run for the same act (unlikely, but
        # possible if screen_eurlex.py's two keywords both matched it)
        # must not be double-added.
        already_added_digits.add(normalize_for_diff(record["znacka"]))
        print(f"[add] {celex} -> {doc_type}: {result['title'][:70]}")
        time.sleep(SLEEP_SECONDS)

    save_json(ADMINISTRATIVE_PATH, administrative)
    save_json(OFF_TOPIC_PATH, off_topic)
    save_json(REVIEW_QUEUE_PATH, review_queue)
    all_added = already_added + added
    save_json(OUTPUT_PATH, all_added)

    print(f"\n{len(added)} new record(s) added this run "
          f"({skipped_type} non-binding type, {skipped_known} already in corpus, "
          f"{skipped_off_topic} off-topic (pattern or LLM), "
          f"{skipped_needs_review} needs human review (LLM unsure/unavailable), "
          f"{skipped_unresolved} no longer resolvable live).")
    print(f"{len(all_added)} total in {OUTPUT_PATH.relative_to(REPO_ROOT)}; "
          f"{len(administrative)} administrative candidate(s) logged in "
          f"{ADMINISTRATIVE_PATH.relative_to(REPO_ROOT)}; "
          f"{len(off_topic)} off-topic candidate(s) logged in "
          f"{OFF_TOPIC_PATH.relative_to(REPO_ROOT)}; "
          f"{len(review_queue)} candidate(s) awaiting human review in "
          f"{REVIEW_QUEUE_PATH.relative_to(REPO_ROOT)}.")


if __name__ == "__main__":
    main()
