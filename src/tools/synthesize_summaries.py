"""Writes an approximate Czech summary for standards whose publisher
publishes no scope text — doc/PLAN.md §17, 2026-09-17.

The fallback tier, and deliberately the LAST one. `src/sites/normoff.py`
fetches the registry's own "Predmet normy" wherever it exists (91 of 126
designations); this covers the remainder — 29 records the registry knows
but publishes no scope for, and 5 whose designation it has no exact match
for (amendments and collection markers such as "/A1", "/Zmena",
"(súbor)").

**These summaries are derived from the standard's title and nothing
else**, because nothing else exists for them: no scope from the
publisher, and no full text (standards are copyrighted — `fetch_fulltext.py`
skips `typ_dokumentu == "Norma"` unconditionally, see doc/PLAN.md §4). A
title-derived summary is therefore a restatement, not a source, and the
whole design here keeps that visible:

* it is written to `data/synthesized_summaries.json`, NOT to
  `data/site_metadata_cache.json` — that cache means "fetched from the
  source", and mixing generated text into it would destroy the one
  distinction this section exists to preserve;
* `build_unified_db.py` applies it to `popis_priblizny`, never to
  `popis_autoritativni` or `description`;
* the UI renders it as "Přibližné shrnutí, neověřeno" and the record
  keeps `needs_review` set.

The prompt is correspondingly narrow. §13's fabricated annotation — a
confident paragraph about vehicle *emissions* for a regulation on
hydrogen vehicle *safety* — came from a model asked what a designation
"usually" covers. Here the model is told to restate the title's own
subject and explicitly forbidden to add thresholds, figures, procedures
or applicability claims the title does not state.

Usage: `.venv/bin/python src/tools/synthesize_summaries.py [--apply] [--limit N]`
(dry-run report only by default; --apply writes the summaries file)
"""
import argparse
import json
import os
import pathlib
import sys
import time

import pymysql
from dotenv import load_dotenv

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from norm_title import designation_core

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
CACHE_PATH = REPO_ROOT / "data" / "site_metadata_cache.json"
SUMMARIES_PATH = REPO_ROOT / "data" / "synthesized_summaries.json"
API_KEY_PATH = REPO_ROOT / ".openapi_key"
load_dotenv(REPO_ROOT / ".env")

MODEL = "gpt-4o-mini"
SLEEP_SECONDS = 0.4

SYSTEM_PROMPT = """Jsi odborník na technickou normalizaci. Dostaneš
označení a název technické normy. Napiš česky 1–2 věty, které čtenáři
řeknou, čeho se norma týká.

Máš k dispozici POUZE název normy. Nic jiného o ní nevíš.

Závazná pravidla:
- Vyjdi VÝHRADNĚ z názvu. Přeformuluj, co už název říká, do souvislé věty.
- NEUVÁDĚJ žádné konkrétní údaje, které v názvu nejsou: žádné číselné
  hodnoty, meze, tlaky, teploty, rozměry, zkušební postupy, lhůty ani
  výčty zařízení nebo látek.
- NETVRDÍ, na co se norma vztahuje nebo nevztahuje, pokud to název
  neříká.
- Nepiš, že norma „stanovuje požadavky“ na něco konkrétního, pokud to
  název neuvádí — drž se předmětu, který název pojmenovává.
- Nepiš úvodní fráze typu „Tato norma je důležitá…“ ani hodnocení.
- Žádný text navíc, jen to shrnutí.

Vrať JSON: {"shrnuti": "<český text>"}"""


def get_connection():
    return pymysql.connect(
        host=os.environ["DB_HOST"], port=int(os.environ["DB_PORT"]),
        user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"], cursorclass=pymysql.cursors.DictCursor,
    )


def get_client():
    if not API_KEY_PATH.exists():
        raise FileNotFoundError(f"API key file {API_KEY_PATH.name} not found.")
    from openai import OpenAI
    os.environ.setdefault("OPENAI_API_KEY", API_KEY_PATH.read_text(encoding="utf-8").strip())
    return OpenAI()


def load_json(path, default):
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_summaries(summaries):
    with open(SUMMARIES_PATH, "w", encoding="utf-8") as f:
        json.dump(summaries, f, ensure_ascii=False, indent=2, sort_keys=True)


def find_candidates(conn, cache):
    """Standards with no description that the fetch tier could not fill —
    either the registry publishes no scope for them, or it has no exact
    match for their designation. Returns [(designation, title, why)].

    Prefers the registry's own title when there is one: it is the
    publisher's wording, without the corpus's designation prefix and
    edition suffix."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT d.identifier, d.title
            FROM Document d JOIN DocumentType dt ON d.type_id = dt.id
            WHERE dt.name = 'Norma'
              AND (d.description IS NULL OR TRIM(d.description) = '')
              AND d.identifier REGEXP '^(STN|TNI)'
            ORDER BY d.identifier
        """)
        rows = cur.fetchall()

    candidates = []
    for row in rows:
        designation = designation_core(row["identifier"])
        entry = cache.get(f"stn:{designation}")
        if entry and (entry.get("description") or "").strip():
            continue                      # the fetch tier covered this one
        if entry and entry.get("status") == "fetched":
            title, why = entry.get("title") or row["title"], "registry publishes no scope"
        else:
            title, why = row["title"], "designation not found in the registry"
        candidates.append((designation, title, why))
    return candidates


def synthesize(client, designation, title):
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": SYSTEM_PROMPT},
                  {"role": "user", "content": f"Označení: {designation}\nNázev: {title}"}],
        response_format={"type": "json_object"},
        temperature=0.0,
        timeout=60,
    )
    payload = json.loads(response.choices[0].message.content)
    return (payload.get("shrnuti") or "").strip() or None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true",
                         help="write data/synthesized_summaries.json (default: dry-run)")
    parser.add_argument("--limit", type=int, default=None,
                         help="synthesize at most N (for a smoke test)")
    args = parser.parse_args()

    cache = load_json(CACHE_PATH, {})
    summaries = load_json(SUMMARIES_PATH, {})
    conn = get_connection()
    candidates = find_candidates(conn, cache)
    conn.close()

    pending = [c for c in candidates if c[0] not in summaries]
    print(f"{len(candidates)} standards the fetch tier could not fill; "
          f"{len(pending)} without a summary yet")
    from collections import Counter
    print("  reasons:", dict(Counter(why for _, _, why in candidates)))

    if not pending:
        print("Nothing to synthesize.")
        return

    if not args.apply:
        print("\n--- first 5 (dry run; input is the title and nothing else) ---")
        for designation, title, why in pending[:5]:
            print(f"  {designation}\n      [{why}] {title[:110]}")
        print("\nDry run — pass --apply to generate and write.")
        return

    client = get_client()
    done = failed = 0
    for designation, title, why in pending[:args.limit]:
        try:
            summary = synthesize(client, designation, title)
        except Exception as exc:                     # noqa: BLE001 — report, never abort the batch
            print(f"  FAILED {designation}: {exc}")
            failed += 1
            continue
        if not summary:
            print(f"  FAILED {designation}: empty summary")
            failed += 1
            continue
        summaries[designation] = {
            "popis_priblizny": summary,
            "derived_from_title": title,
            "reason": why,
            "model": MODEL,
            # Recorded so a reader (and a later audit) can see this text
            # had no source beyond the title.
            "basis": "title-only",
        }
        done += 1
        if done % 10 == 0:
            save_summaries(summaries)
            print(f"  … {done} written")
        time.sleep(SLEEP_SECONDS)

    save_summaries(summaries)
    print(f"\nSynthesized {done}, failed {failed} -> {SUMMARIES_PATH}")


if __name__ == "__main__":
    main()
