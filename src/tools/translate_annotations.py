"""Translates fetched scope texts in `data/site_metadata_cache.json` into
Czech — doc/PLAN.md §17, 2026-09-16.

The registry entries `src/sites/normoff.py` brings back are in the
standard's own language (measured on the real corpus: 60 English, 31
Slovak), but this database's annotations are written in Czech regardless
of the document's own language.

This is **translation, not authorship**. The model is given the fetched
text and asked to render it in Czech, nothing else: no summarising, no
filling gaps, no explaining. That distinction is what keeps the result in
`popis_autoritativni` ("verified from the source") rather than in
`popis_priblizny` ("approximate, unverified") — see §17.4.

The original is never overwritten. Each translated entry keeps:

    description          the Czech text (what flows into the pipeline)
    description_source   the publisher's own wording, verbatim
    description_source_lang   detected language of that original

so any translation can be re-checked against what it came from. Without
that, a translation error would be indistinguishable from a bad source
and there would be nothing to audit against.

Usage: `.venv/bin/python src/tools/translate_annotations.py [--apply] [--limit N]`
(dry-run report only by default; --apply writes the cache)
"""
import argparse
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from language import detect_language

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
CACHE_PATH = REPO_ROOT / "data" / "site_metadata_cache.json"
API_KEY_PATH = REPO_ROOT / ".openapi_key"

MODEL = "gpt-4o-mini"
SLEEP_SECONDS = 0.4

SYSTEM_PROMPT = """Jsi odborný překladatel technických norem do češtiny.

Dostaneš text předmětu (scope) technické normy v cizím jazyce. Přelož ho
do češtiny.

Závazná pravidla:
- Překládej POUZE to, co je v zadaném textu. Nic nepřidávej, nedoplňuj,
  nevysvětluj ani nezobecňuj.
- Nic nevynechávej a text nezkracuj do shrnutí — jde o překlad, ne o
  anotaci.
- Zachovej odborné termíny, označení norem (např. "EN 13611:2019"),
  čísla, jednotky a odkazy na články beze změny.
- Pokud je vstup už česky, vrať ho beze změny.
- Neuváděj žádný úvod typu "Tato norma..." navíc, pokud tam není.

Vrať JSON: {"preklad": "<český text>"}"""


def get_client():
    if not API_KEY_PATH.exists():
        raise FileNotFoundError(f"API key file {API_KEY_PATH.name} not found.")
    import os
    from openai import OpenAI
    os.environ.setdefault("OPENAI_API_KEY", API_KEY_PATH.read_text(encoding="utf-8").strip())
    return OpenAI()


def load_cache():
    with open(CACHE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_cache(cache):
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2, sort_keys=True)


# Domains whose fetched text is expected to be in a foreign language and
# is therefore in scope for translation. An allow-list rather than "any
# entry that doesn't look Czech": `detect_language()` reads a short Czech
# legal title ("Zákon č. 266/1994 Sb. - Zákon o dráhách") as Slovak, so a
# detector-only rule pulled zakonyprolidi.cz entries — already Czech, from
# a Czech source — into the batch. A new domain opts in here deliberately.
TRANSLATABLE_DOMAINS = {"normy.normoff.gov.sk", "eiga.eu", "iec.ch", "dvgw.de"}


def needs_translation(entry):
    """True when this entry carries a fetched description from a
    translatable domain that is not already Czech and has not already
    been translated."""
    if entry.get("domain") not in TRANSLATABLE_DOMAINS:
        return False
    description = (entry.get("description") or "").strip()
    if not description:
        return False
    if entry.get("description_source"):
        return False          # already translated on an earlier run
    return detect_language(description)[0] != "CS"


def translate(client, text):
    """The Czech rendering of `text`, or None if the model returns
    nothing usable — never a partial or silently-empty result."""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": SYSTEM_PROMPT},
                  {"role": "user", "content": text}],
        response_format={"type": "json_object"},
        temperature=0.0,
        timeout=60,
    )
    payload = json.loads(response.choices[0].message.content)
    translated = (payload.get("preklad") or "").strip()
    return translated or None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true",
                         help="write the cache (default: dry-run report only)")
    parser.add_argument("--limit", type=int, default=None,
                         help="translate at most N entries (for a smoke test)")
    args = parser.parse_args()

    cache = load_cache()
    pending = [(key, entry) for key, entry in sorted(cache.items())
               if needs_translation(entry)]

    print(f"{len(cache)} cache entries; {len(pending)} carry a non-Czech fetched description")
    if not pending:
        print("Nothing to translate.")
        return

    from collections import Counter
    langs = Counter(detect_language(e["description"])[0] for _, e in pending)
    print(f"  source languages: {dict(langs)}")

    if not args.apply:
        print("\n--- first 3 (dry run) ---")
        for key, entry in pending[:3]:
            print(f"  {key}\n      {entry['description'][:150]}")
        print("\nDry run — pass --apply to translate and write the cache.")
        return

    client = get_client()
    done = failed = 0
    for key, entry in pending[:args.limit]:
        original = entry["description"]
        try:
            czech = translate(client, original)
        except Exception as exc:                      # noqa: BLE001 — report, never abort the batch
            print(f"  FAILED {key}: {exc}")
            failed += 1
            continue
        if not czech:
            print(f"  FAILED {key}: empty translation")
            failed += 1
            continue
        entry["description_source"] = original
        entry["description_source_lang"] = detect_language(original)[0]
        entry["description"] = czech
        done += 1
        if done % 10 == 0:
            save_cache(cache)
            print(f"  … {done} translated")
        time.sleep(SLEEP_SECONDS)

    save_cache(cache)
    print(f"\nTranslated {done}, failed {failed} -> {CACHE_PATH}")


if __name__ == "__main__":
    main()
