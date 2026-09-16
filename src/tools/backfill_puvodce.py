"""One-time backfill of `Document.source_id`/`DocumentSource.name`
("Původce" in the UI) — user finding (2026-09-15): `DocumentSource.name`
was often a whole `gestor` list joined verbatim with ", " (see
`init_db.py`'s `source = ", ".join(gestor)`), including AI-generated
(`enrich_eu_laws.py`) "Gestor CZ" entries that are themselves multi-line
blobs (a Directorate-General list plus free-text commentary, e.g.
"Primární DG \nDG ENER (...)\n\nDalší spolupracující DG: \nDG CLIMA
(...), ..."), never meant to stand as a single institution's name —
"Původce" is supposed to be the one ministry/institution with primary
responsibility ("gesci"), not a concatenation of every co-gestor and
enrichment side-note.

Per user decision (2026-09-15): keep the "primary responsible ministry"
concept (not the formal legal issuer/promulgator, which is a different,
larger question) — reduce each document's source to the FIRST clean
entry of its original `gestor` list, discarding co-gestors and any
blob/commentary entries. Only `Document`s that already have a
`source_id` are touched (104 on the real corpus) — this does not attempt
to backfill Původce for the ~1134 documents (almost entirely `Norma`)
that never had a `gestor` at all; there is no reliable per-document
issuing-body signal for those in this corpus.

**2026-09-16 follow-up, scope split**: for an EU act itself (`Nařízení
EU`/`Směrnice EU`/`Rozhodnutí EU`), a further user finding/decision
established that "the primary responsible ministry" is the wrong
concept entirely — Gestor there should be the responsible EU body, per
`backfill_eu_gestor.py`. The same reasoning applies to a technical
standard, whose Gestor is the standards body that publishes it, per
`backfill_standards_body.py` (doc/PLAN.md §16). All four of those types
are EXCLUDED here (see the `dt.name NOT IN (...)` filter below) so this
script's primary-gestor reduction never overwrites either of those
authoritative results with a Czech ministry that merely happened to be
first in the same record's AI-generated `gestor` list — verified twice
that this would otherwise happen: re-running this script proposed
reverting all 43 resolved EU-act records back to a CZ ministry before
the EU exclusion was added, and 5 ČSN standards from `ČAS` back to
`Ministerstvo průmyslu a obchodu` before `Norma` was added.

This script therefore now owns exactly the national CZ/SK acts
(`Zákon`/`Vyhláška`/`Nařízení vlády`/`Nezařazeno`/…) — the one case
where "which ministry has gesci" is the right question to ask.

Usage: `.venv/bin/python src/tools/backfill_puvodce.py [--apply]`
(dry-run report only by default; --apply writes to the database)
"""
import argparse
import json
import os
import pathlib
import re
import sys

import pymysql
from dotenv import load_dotenv

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from puvodce import ABBREVIATION_MAP, gestor_list, is_clean_institution_name

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
JSON_PATH = REPO_ROOT / "data" / "database_merged_deduplicated.json"
load_dotenv(REPO_ROOT / ".env")

TITLE_FIELDS = ("nazev_cz", "nazev_sk", "nazev_eu", "nazev_autoritativni")


def get_connection():
    return pymysql.connect(
        host=os.environ["DB_HOST"], port=int(os.environ["DB_PORT"]),
        user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"], cursorclass=pymysql.cursors.DictCursor,
    )


def normalize_text(s):
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def load_json_records():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def build_znacka_index(records):
    index = {}
    for item in records:
        z = (item.get("znacka") or "").strip()
        if z:
            index.setdefault(z, []).append(item)
    return index


def primary_gestor(item):
    """First clean entry of `item`'s gestor list, canonicalized through
    ABBREVIATION_MAP, or None if the list is empty or (never observed in
    this corpus, but handled rather than guessed) every entry is a
    blob."""
    for g in gestor_list(item):
        if is_clean_institution_name(g):
            return ABBREVIATION_MAP.get(g, g)
    return None


def match_records(doc, znacka_index, all_records):
    """Returns the list of JSON records this Document corresponds to:
    exact `identifier`==`znacka` match when unique, else a title-prefix
    fallback (needed for the ~13 records without a stable `identifier`,
    e.g. the CZ/SK split pair sharing one source row — doc/PLAN.md §15)."""
    ident = (doc["identifier"] or "").strip()
    if ident and len(znacka_index.get(ident, [])) == 1:
        return znacka_index[ident]

    title_prefix = normalize_text(doc["title"])[:40]
    if not title_prefix:
        return []
    candidates = []
    for item in all_records:
        for field in TITLE_FIELDS:
            v = normalize_text(item.get(field) or "")
            if v and (v.startswith(title_prefix) or title_prefix.startswith(v[:40])):
                candidates.append(item)
                break
    return candidates


def get_or_create_source(cur, name, cache):
    if name in cache:
        return cache[name]
    cur.execute("SELECT id FROM DocumentSource WHERE name=%s", (name,))
    row = cur.fetchone()
    if row:
        cache[name] = row["id"]
        return row["id"]
    cur.execute("INSERT INTO DocumentSource (name) VALUES (%s)", (name,))
    new_id = cur.lastrowid
    cache[name] = new_id
    return new_id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true",
                         help="write changes to the database (default: dry-run report only)")
    args = parser.parse_args()

    records = load_json_records()
    znacka_index = build_znacka_index(records)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT d.id, d.identifier, d.title, ds.name AS current_source
        FROM Document d
        JOIN DocumentSource ds ON d.source_id = ds.id
        LEFT JOIN DocumentType dt ON d.type_id = dt.id
        WHERE dt.name IS NULL
           OR dt.name NOT IN ('Nařízení EU', 'Směrnice EU', 'Rozhodnutí EU', 'Norma')
    """)
    documents = cur.fetchall()

    plan = []  # (doc_id, current_source, new_source)
    unmatched = []
    ambiguous = []

    for doc in documents:
        candidates = match_records(doc, znacka_index, records)
        if not candidates:
            # No JSON match, but a bare-abbreviation source (see
            # ABBREVIATION_MAP) can still be canonicalized without it.
            abbrev_source = ABBREVIATION_MAP.get(doc["current_source"])
            if abbrev_source:
                plan.append((doc["id"], doc["current_source"], abbrev_source))
            else:
                unmatched.append(doc)
            continue
        primaries = {primary_gestor(c) for c in candidates}
        primaries.discard(None)
        if len(primaries) > 1:
            ambiguous.append((doc, primaries))
            continue
        new_source = next(iter(primaries), None)
        if not new_source:
            unmatched.append(doc)
            continue
        if new_source != doc["current_source"]:
            plan.append((doc["id"], doc["current_source"], new_source))

    print(f"{len(documents)} documents with a source_id")
    print(f"  to update: {len(plan)}")
    print(f"  unchanged (already a single clean institution): "
          f"{len(documents) - len(plan) - len(unmatched) - len(ambiguous)}")
    print(f"  unmatched against JSON (left untouched): {len(unmatched)}")
    print(f"  ambiguous — candidates disagree on primary gestor (left untouched): {len(ambiguous)}")

    if unmatched:
        print("\n--- unmatched ---")
        for d in unmatched:
            print(f"  id={d['id']} title={d['title'][:60]!r}")
    if ambiguous:
        print("\n--- ambiguous ---")
        for d, primaries in ambiguous:
            print(f"  id={d['id']} title={d['title'][:60]!r} candidates={primaries}")

    print(f"\n--- {len(plan)} planned changes ---")
    for doc_id, old, new in plan:
        print(f"  id={doc_id}: {old[:60]!r} -> {new!r}")

    if not args.apply:
        print("\nDry run — pass --apply to write changes.")
        conn.close()
        return

    source_cache = {}
    for doc_id, _old, new_source in plan:
        source_id = get_or_create_source(cur, new_source, source_cache)
        cur.execute("UPDATE Document SET source_id=%s WHERE id=%s", (source_id, doc_id))
    conn.commit()

    cur.execute("""
        DELETE FROM DocumentSource
        WHERE id NOT IN (SELECT DISTINCT source_id FROM Document WHERE source_id IS NOT NULL)
    """)
    removed = cur.rowcount
    conn.commit()
    print(f"\nApplied {len(plan)} updates. Removed {removed} now-orphaned DocumentSource rows.")
    conn.close()


if __name__ == "__main__":
    main()
