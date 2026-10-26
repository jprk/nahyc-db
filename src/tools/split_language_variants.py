"""Splits the deduplicated records of acts that exist in a Czech and an English
variant into two records each (see language_variants.py), in
data/database_merged_deduplicated.json, and writes the `TRANSLATION_OF`
relations to data/document_relations_variants.json.

Run it after deduplicate_db.py (which merges the two spreadsheet rows of an act
into one record) and before init_db.py. Idempotent, deterministic and offline:
a second run changes nothing. Dry run unless --apply."""
import argparse
import json
import pathlib

import language_variants as lv

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
RAW_PATH = REPO_ROOT / "data" / "database_merged_raw.json"
DEDUPLICATED_PATH = REPO_ROOT / "data" / "database_merged_deduplicated.json"
RELATIONS_PATH = REPO_ROOT / "data" / "document_relations_variants.json"
GESTOR_CACHE_PATH = REPO_ROOT / "data" / "eu_gestor_cache.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, data, indent):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=indent), encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--apply", action="store_true", help="write the files (dry run without it)")
    args = parser.parse_args(argv)
    pairs = lv.variant_pairs(load(RAW_PATH))
    before = load(DEDUPLICATED_PATH)
    after = lv.expand_variants(before, pairs)
    relations = lv.translation_relations(after)
    cache = load(GESTOR_CACHE_PATH)
    additions = lv.gestor_cache_additions(after, cache)
    print(f"{len(pairs)} designations with a Czech and an English row; "
          f"{len(after) - len(before)} records added, {len(relations)} relations, "
          f"{len(additions)} gestor cache entries copied for the English addresses")
    if args.apply:
        write(DEDUPLICATED_PATH, after, 4)
        write(RELATIONS_PATH, relations, 2)
        write(GESTOR_CACHE_PATH, {**cache, **additions}, 2)
        print(f"written: {DEDUPLICATED_PATH.relative_to(REPO_ROOT)}, {RELATIONS_PATH.relative_to(REPO_ROOT)}, "
              f"{GESTOR_CACHE_PATH.relative_to(REPO_ROOT)}")
    else:
        print("(dry run — add --apply)")


if __name__ == "__main__":
    main()
