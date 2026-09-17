"""Converts `screen_esbirka.py`'s screening candidates into real, verified
Czech-law Document records — doc/PLAN.md §30, 2026-09-17, user-directed
continuation of the corpus-expansion work (§28/§29 did this for EU
legislation; this closes the "Czech national law" item deferred at the
end of that round).

**The technical unlock this script is built on:** `screen_esbirka.py`'s
own docstring, and `src/sites/esbirka.py`'s, both say a full-text hit in
e-Sbírka's LOD graph "doesn't reliably carry a scrapeable back-link to
its owning act" — true of the matched node's OWN (forward) properties,
but a live investigation (2026-09-17) found a working ONE-HOP REVERSE
query instead: `?s <...pojem/obsahuje-fragment> <matched-fragment-uri>`
returns a node whose own URI already has the shape
`.../eli/cz/sb/{year}/{number}/{date}/dokument/...` — the year and
number are sitting right there in the URI path, no vocabulary knowledge
needed beyond that one predicate. A `právní-akt-binární-soubor` hit needs
one extra hop first (`...pojem/má-binární-soubor` to its owning
fragment), then the same reverse-fragment hop. A `právní-akt-metadata`
hit has no such link at all (confirmed empirically) and stays
unresolved, logged for review — never guessed at.

**A second false-positive source found and fixed upstream, not just
here:** `screen_esbirka.py`'s old `"vodí*"` wildcard also matched
"vodítko"/"vodítka"/"vodítek" (elevator/lift guide rails) and "vodicí"
(guide-, as in "vodicí lano") — words that share a 4-letter prefix with
"vodík" but mean something completely unrelated. Fixed at the source
(`HYDROGEN_KEYWORDS = ["vodík*"]`, one more character, still covers
every inflected form of "vodík" needed), but the EXISTING 100-entry
candidates file was collected under the old, looser keyword and still
carries that noise — so this script re-checks defensively with a fixed
`\\bvodík` regex before doing anything else with a candidate.

**Off-topic classification here works on the MATCHED SNIPPET, not the
document's title** — the reverse of `add_eurlex_hydrogen_acts.py`. For
EU acts, an off-topic title (e.g. "...Hydrogen Peroxide Biocidal
Product...") was itself the signal. Here, the matched snippet is
typically a single paragraph/table-cell buried inside a much longer,
topically unrelated act (a 1930s customs-tariff schedule, a decree
implementing road-traffic rules), so the *document title* usually says
nothing about hydrogen at all — on-topic or off — while the actual
matched fragment text always does. A live batch (all 100 pre-existing
candidates) found: the "vodítko" collision (~9 hits), old customs/tariff
schedules and 1920s-1950s trade treaties that list "vodík" only as one
commodity among many in a tariff table (~26 unique acts, almost all of
them), old hydrogen-peroxide chemistry/transport rules ("peroxyd(u)
vodíku" — pre-reform spelling), and exactly 2 genuinely on-topic hits:
traffic-sign 409 "Čerpací stanice vodíku" (hydrogen filling station) in
294/2015 Sb.'s annex and its 205/2025 Sb. amendment.

Two off-topic layers, same architecture as §29's EU version: a
deterministic pattern deny-list first (`OFF_TOPIC_SNIPPET_PATTERNS`),
then an LLM backstop (`classify_relevance_with_llm`) for whatever the
patterns don't already catch, scored 0-100 and split into the same
three outcomes — high score excluded, low score proceeds, the uncertain
middle band (or an unreachable LLM) queued for human review, never
guessed at either way. Every outcome is logged, never silently dropped.

Usage:
    .venv/bin/python src/tools/add_esbirka_hydrogen_acts.py [--limit N]

Output: appends verified records to `data/discovered_cz_hydrogen_acts.json`
(loaded by `build_unified_db.py` as a 9th source), and writes/updates
`data/esbirka_off_topic_not_imported.json` (word-stem collisions, and
pattern-/LLM-caught off-topic acts), `data/esbirka_relevance_review_queue
.json` (LLM unsure/unavailable), and `data/esbirka_unresolved_not_imported
.json` (a fragment/binary-soubor node the reverse SPARQL hop couldn't
map to any act, or a právní-akt-metadata node, or a znacka that no
longer resolves live at zakonyprolidi.cz).
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

from screen_eurlex import load_known_znacka_digits, normalize_for_diff  # noqa: E402
from build_unified_db import classify_law_document_typ  # noqa: E402
from sites.zakonyprolidi import extract as zakonyprolidi_extract  # noqa: E402

CANDIDATES_PATH = REPO_ROOT / "data" / "fulltext_screening_candidates.json"
RAW_DB_PATH = REPO_ROOT / "data" / "database_merged_raw.json"
OUTPUT_PATH = REPO_ROOT / "data" / "discovered_cz_hydrogen_acts.json"
OFF_TOPIC_PATH = REPO_ROOT / "data" / "esbirka_off_topic_not_imported.json"
REVIEW_QUEUE_PATH = REPO_ROOT / "data" / "esbirka_relevance_review_queue.json"
UNRESOLVED_PATH = REPO_ROOT / "data" / "esbirka_unresolved_not_imported.json"

SPARQL_ENDPOINT = "https://opendata.eselpoint.gov.cz/sparql"
USER_AGENT = "Mozilla/5.0 (compatible; NAHYC-DP004-screening-tool/1.0; +research use, low-volume)"
SLEEP_SECONDS = 1
SOURCE_NAME = "CZ_Hydrogen_Discovery"

_OBSAHUJE_FRAGMENT = "https://slovník.gov.cz/datový/sbírka/pojem/obsahuje-fragment"
_MA_BINARNI_SOUBOR = "https://slovník.gov.cz/datový/sbírka/pojem/má-binární-soubor"
_ELI_RE = re.compile(r"/eli/cz/sb/(\d{4})/(\d+)/")

# See module docstring: "vodí*" (screen_esbirka.py's old keyword) also
# matches "vodítko"/"vodítka"/"vodítek"/"vodicí" — this requires the
# actual word "vodík" (any inflection: vodík/vodíku/vodíkem/vodíková/...)
# to appear, word-bounded, before a candidate is considered at all.
_ACTUAL_HYDROGEN_RE = re.compile(r"\bvodík", re.IGNORECASE)

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def run_sparql(session, query):
    """Same endpoint/param convention as `screen_esbirka.py`'s own
    `run_sparql` (duplicated, not imported — this module's own
    established per-site-script convention, see e.g. `screen_eurlex.py`/
    `screen_esbirka.py`/`screen_slovlex.py` each keeping their own copy).
    Degrades to [] on any failure."""
    try:
        resp = session.get(SPARQL_ENDPOINT, params={
            "output": "application/sparql-results+json",
            "query": query.strip(),
        }, timeout=30)
        resp.raise_for_status()
        return resp.json().get("results", {}).get("bindings", [])
    except (requests.RequestException, ValueError):
        return []


def is_actual_hydrogen_mention(snippet):
    """False for the "vodítko"/"vodicí" word-stem collision described in
    the module docstring — True only for an actual "vodík" word form."""
    return bool(_ACTUAL_HYDROGEN_RE.search(snippet or ""))


def strip_html(text):
    """Collapses an e-Sbírka snippet's raw HTML (many hits are literal
    `<table>` markup from old tariff schedules) down to plain text for
    relevance classification — never shown to a human as HTML, never fed
    to the LLM with markup noise obscuring the actual words."""
    return re.sub(r"\s+", " ", _HTML_TAG_RE.sub(" ", text or "")).strip()


def resolve_znacka_for_uri(uri, session):
    """The reverse-hop resolution described in the module docstring.
    Returns (year, number) as strings, or None if this node type isn't
    resolvable at all (`právní-akt-metadata`, or anything unrecognized)
    or the reverse query came back empty (an orphaned/unlinked node —
    happens for a small residual, see doc/PLAN.md §30)."""
    if "právní-akt-fragment" in uri:
        bindings = run_sparql(session, f"SELECT ?s WHERE {{ ?s <{_OBSAHUJE_FRAGMENT}> <{uri}> . }} LIMIT 5")
        for b in bindings:
            m = _ELI_RE.search(b["s"]["value"])
            if m:
                return m.group(1), m.group(2)
        return None

    if "právní-akt-binární-soubor" in uri:
        frag_bindings = run_sparql(session, f"SELECT ?s WHERE {{ ?s <{_MA_BINARNI_SOUBOR}> <{uri}> . }} LIMIT 5")
        for fb in frag_bindings:
            frag_uri = fb["s"]["value"]
            act_bindings = run_sparql(session, f"SELECT ?s WHERE {{ ?s <{_OBSAHUJE_FRAGMENT}> <{frag_uri}> . }} LIMIT 5")
            for ab in act_bindings:
                m = _ELI_RE.search(ab["s"]["value"])
                if m:
                    return m.group(1), m.group(2)
        return None

    return None


def build_znacka(year, number):
    """"294/2015 Sb." from ("2015", "294") — the canonical Czech-law
    znacka shape already used throughout this corpus. Unlike EU CELEX
    ids (two possible year/number orderings depending on era), Czech law
    citations are always "number/year Sb." — no ambiguity to resolve."""
    return f"{int(number)}/{year} Sb."


_LEADING_ZNACKA_RE = re.compile(r"^\s*\d+\s*/\s*\d{4}\s*Sb\.?\s*")


def strip_leading_znacka(title):
    """zakonyprolidi.cz's og:title is "294/2015 Sb. Vyhláška, kterou...",
    but `build_unified_db.py:classify_law_document_typ()`'s "Vyhláška"/
    "Nařízení vlády" patterns are anchored at the START of the string
    (`^\\s*vyhlá...`) — matched against the raw title, the leading
    "294/2015 Sb. " would make every Vyhláška/Nařízení-vlády record
    misclassify as "" (unclear). Strips that prefix before classifying,
    same reasoning as `add_eurlex_hydrogen_acts.py`'s title re-fetch
    discipline: never let a source-specific formatting quirk silently
    corrupt a downstream classifier it wasn't written for."""
    return _LEADING_ZNACKA_RE.sub("", title or "", count=1)


# A live batch (doc/PLAN.md §30, 2026-09-17) manually classified every
# resolvable act among screen_esbirka.py's 100 pre-existing candidates:
# 26 were customs-tariff schedules or 1920s-1950s bilateral trade/rail
# treaties that list "vodík" only as one commodity among many in a
# tariff table, several more were 1930s hydrogen-peroxide transport
# rules ("peroxyd(u) vodíku" — pre-orthographic-reform spelling), and
# exactly 2 (294/2015 Sb. and its 205/2025 Sb. amendment) were genuinely
# about hydrogen as an energy carrier (a road-sign category for hydrogen
# filling stations). These patterns exclude that false-positive
# vocabulary; classification runs on the matched SNIPPET, not the
# document title (see module docstring for why).
OFF_TOPIC_SNIPPET_PATTERNS = [
    r"celn[ íý]",                    # celní sazebník/sazby, various inflections
    r"sazebník",
    r"clu prost",
    r"peroxyd\w*\s+vodíku",          # pre-reform spelling of hydrogen peroxide
    r"superoxyd\w*\s+vodíku",
    r"obchodní (úmluva|smlouva|dohoda)",  # old bilateral trade treaties
]
_OFF_TOPIC_RE = re.compile("|".join(OFF_TOPIC_SNIPPET_PATTERNS), re.IGNORECASE)


def is_off_topic(snippet):
    """True when a matched snippet matches known customs/tariff/trade-
    treaty/old-chemistry vocabulary rather than hydrogen as an energy
    carrier — see OFF_TOPIC_SNIPPET_PATTERNS above for the batch this
    was derived from."""
    return bool(_OFF_TOPIC_RE.search(snippet or ""))


_RELEVANCE_SYSTEM_PROMPT = """You are a relevance classifier for a Czech/EU hydrogen-technology \
regulatory database. The database tracks hydrogen ONLY as an energy carrier / fuel: hydrogen \
production, storage, transport, refuelling infrastructure, fuel cells, hydrogen-powered vehicles, \
and the hydrogen energy market.

You are given a short snippet of Czech legal text — a single matched fragment (a paragraph, table \
row, or clause) from a much longer Czech law, which was found because it contains the word \
"vodík" (hydrogen) somewhere in that fragment. The snippet, NOT the surrounding act's overall \
subject, is what you must judge: many hits come from an otherwise-unrelated act (e.g. a customs \
tariff schedule, a road-traffic decree) where only this one fragment happens to mention hydrogen. \
Judge whether THIS FRAGMENT is substantively about hydrogen as an energy carrier (e.g. hydrogen \
vehicles, hydrogen refuelling infrastructure, hydrogen production/storage/transport, fuel cells), \
or whether "vodík" only appears because of an unrelated chemical mention (hydrogen peroxide, an \
industrial-gas customs-tariff listing that happens to include hydrogen among many other gases, a \
generic chemistry enumeration) or an administrative/historical matter (old customs tariffs, \
bilateral trade treaties) with no connection to hydrogen energy.

Respond with a JSON object: {"off_topic_probability": <integer 0-100>, "reasoning": "<one short \
sentence>"}. 0 means certainly about hydrogen as an energy carrier; 100 means certainly unrelated. \
Use the full range, including the middle, when genuinely unsure."""

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
HIGH_OFF_TOPIC_THRESHOLD = 75
LOW_ON_TOPIC_THRESHOLD = 25


def classify_relevance_with_llm(snippet, znacka=None):
    """Same contract as `add_eurlex_hydrogen_acts.py`'s function of the
    same name (own client instance, own prompt): returns
    {"off_topic_probability": int, "reasoning": str}, or None if the
    client isn't configured or every attempt failed. Callers MUST treat
    None as "unknown" (route to human review), never as a guess."""
    if client is None:
        return None

    user_content = json.dumps({"snippet": snippet, "znacka": znacka}, ensure_ascii=False)

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


def assess_relevance(snippet, znacka=None, llm_classifier=classify_relevance_with_llm):
    """Same three-way verdict as `add_eurlex_hydrogen_acts.py`'s function
    of the same name: "off_topic" (pattern hit, or LLM high-confidence),
    "on_topic" (LLM low-confidence off-topic), or "needs_review" (LLM
    uncertain, or unreachable/unusable — never resolved as a guess)."""
    if is_off_topic(snippet):
        return {"verdict": "off_topic", "method": "pattern", "score": None, "reasoning": None}

    result = llm_classifier(snippet, znacka)
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


def load_json(path):
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def build_document_record(znacka, title, doc_type, url, candidate, snippet):
    """The full Document-shape dict — same field set as
    `add_eurlex_hydrogen_acts.py`'s records. No gestor lookup available
    from either e-Sbírka's LOD graph or zakonyprolidi.cz for a freshly-
    discovered act, so `gestor` is left as an empty list rather than
    guessed. `jazyk` deliberately blank, same reasoning as the EU
    version — left to the corpus-wide `detect_language()` pass."""
    return {
        "zdroj_dat": SOURCE_NAME,
        "nazev_cz": title,
        "znacka": znacka,
        "typ_dokumentu": doc_type,
        "sekce": "",
        "kategorie_trida": "",
        "klicova_slova": [],
        "odkaz_hlavni": url,
        "nazev_eu": "",
        "odkaz_eu": "",
        "nazev_sk": "",
        "odkaz_sk": "",
        "platnost": "",
        "ratifikovan": "",
        "gestor": [],
        "jazyk": "",
        "anotace_poznamka": (
            f"Nalezeno screeningem e-Sbírky (odpovídající fragment: "
            f"{snippet[:150]!r}, doc/PLAN.md §30), ověřeno živě proti "
            f"zakonyprolidi.cz před doplněním."),
        "jurisdikce": "CZ",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int, default=None,
                         help="process at most N candidates (for a manual smoke test)")
    args = parser.parse_args()

    with open(CANDIDATES_PATH, "r", encoding="utf-8") as f:
        candidates = json.load(f).get("e-Sbirka", [])

    with open(RAW_DB_PATH, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    known_digits = load_known_znacka_digits(raw_data)

    already_added = load_json(OUTPUT_PATH)
    already_added_digits = {normalize_for_diff(r["znacka"]) for r in already_added if r.get("znacka")}
    off_topic = load_json(OFF_TOPIC_PATH)
    off_topic_uris = {r["uri"] for r in off_topic}
    review_queue = load_json(REVIEW_QUEUE_PATH)
    review_uris = {r["uri"] for r in review_queue}
    unresolved = load_json(UNRESOLVED_PATH)
    unresolved_uris = {r["uri"] for r in unresolved}

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    added = []
    skipped_word_stem = skipped_node_unresolved = skipped_known = skipped_duplicate_in_run = 0
    skipped_off_topic = skipped_needs_review = skipped_title_unresolved = 0
    processed = 0

    # Duplicate hits of the SAME act are common (a widely-cited act's
    # provision can turn up under many "znění"/version dates) — cache
    # each znacka's verdict within this run so a repeat hit doesn't
    # redo an LLM call or a zakonyprolidi.cz fetch that's already settled.
    verdict_cache = {}

    for candidate in candidates:
        if args.limit is not None and processed >= args.limit:
            break
        uri = candidate["uri"]
        processed += 1

        snippet = strip_html(candidate.get("snippet", ""))

        if not is_actual_hydrogen_mention(snippet):
            if uri not in off_topic_uris:
                off_topic.append({**candidate, "detection_method": "word_stem_mismatch",
                                   "llm_score": None, "llm_reasoning": None})
                off_topic_uris.add(uri)
            skipped_word_stem += 1
            continue

        resolved = resolve_znacka_for_uri(uri, session)
        time.sleep(SLEEP_SECONDS)
        if resolved is None:
            if uri not in unresolved_uris:
                unresolved.append({**candidate, "reason": "no owning act found via reverse SPARQL hop"})
                unresolved_uris.add(uri)
            skipped_node_unresolved += 1
            continue

        year, number = resolved
        znacka = build_znacka(year, number)

        if normalize_for_diff(znacka) in known_digits or normalize_for_diff(znacka) in already_added_digits:
            skipped_known += 1
            continue

        if znacka in verdict_cache:
            # Another fragment of the SAME act, already classified this
            # run (common — a widely-cited act's provision can turn up
            # under many "znění"/version-date URIs). Its verdict was
            # already acted on (added, logged off-topic/review, or its
            # title fetch already failed) — nothing new to do.
            skipped_duplicate_in_run += 1
            continue

        relevance = assess_relevance(snippet, znacka)
        verdict_cache[znacka] = relevance

        if relevance["verdict"] == "off_topic":
            if uri not in off_topic_uris:
                off_topic.append({**candidate, "znacka": znacka,
                                   "detection_method": relevance["method"],
                                   "llm_score": relevance["score"],
                                   "llm_reasoning": relevance["reasoning"]})
                off_topic_uris.add(uri)
            skipped_off_topic += 1
            print(f"[skip] {znacka}: off-topic ({relevance['method']}): {snippet[:70]}")
            continue

        if relevance["verdict"] == "needs_review":
            if uri not in review_uris:
                review_queue.append({**candidate, "znacka": znacka,
                                      "detection_method": relevance["method"],
                                      "llm_score": relevance["score"],
                                      "llm_reasoning": relevance["reasoning"]})
                review_uris.add(uri)
            skipped_needs_review += 1
            print(f"[skip] {znacka}: needs human review ({relevance['method']}, "
                  f"score={relevance['score']}): {snippet[:70]}")
            continue

        # on-topic: fetch the real title live — never trust the snippet
        # or any assumed title, same discipline as add_eurlex_hydrogen_acts.py.
        url = f"https://www.zakonyprolidi.cz/cs/{year}-{number}"
        result = zakonyprolidi_extract(url, session=session)
        time.sleep(SLEEP_SECONDS)
        if not result or not result.get("title"):
            if uri not in unresolved_uris:
                unresolved.append({**candidate, "znacka": znacka,
                                    "reason": "no longer resolves live at zakonyprolidi.cz"})
                unresolved_uris.add(uri)
            skipped_title_unresolved += 1
            continue

        title = result["title"]
        doc_type = classify_law_document_typ(strip_leading_znacka(title))
        record = build_document_record(znacka, title, doc_type, url, candidate, snippet)
        added.append(record)
        already_added_digits.add(normalize_for_diff(znacka))
        print(f"[add] {znacka} -> {doc_type or '(?)'}: {title[:70]}")

    save_json(OFF_TOPIC_PATH, off_topic)
    save_json(REVIEW_QUEUE_PATH, review_queue)
    save_json(UNRESOLVED_PATH, unresolved)
    all_added = already_added + added
    save_json(OUTPUT_PATH, all_added)

    print(f"\n{len(added)} new record(s) added this run "
          f"({skipped_word_stem} word-stem mismatch (\"vodítko\"/\"vodicí\"), "
          f"{skipped_node_unresolved} node unresolvable via SPARQL, "
          f"{skipped_known} already in corpus, "
          f"{skipped_duplicate_in_run} duplicate of an act already classified this run, "
          f"{skipped_off_topic} off-topic (pattern or LLM), "
          f"{skipped_needs_review} needs human review, "
          f"{skipped_title_unresolved} no longer resolvable live at zakonyprolidi.cz).")
    print(f"{len(all_added)} total in {OUTPUT_PATH.relative_to(REPO_ROOT)}; "
          f"{len(off_topic)} off-topic candidate(s) logged in "
          f"{OFF_TOPIC_PATH.relative_to(REPO_ROOT)}; "
          f"{len(review_queue)} candidate(s) awaiting human review in "
          f"{REVIEW_QUEUE_PATH.relative_to(REPO_ROOT)}; "
          f"{len(unresolved)} unresolved candidate(s) logged in "
          f"{UNRESOLVED_PATH.relative_to(REPO_ROOT)}.")


if __name__ == "__main__":
    main()
