"""Moves the provenance notes out of the public description in the live database
(doc/MPO_PRIPOMINKY.md, krok 0).

The scripts that added documents found by screening (add_eurlex_hydrogen_acts.py,
add_esbirka_hydrogen_acts.py, add_hytep_hydrogen_docs.py, add_missing_iso_parents.py,
import_eu_transposition_targets.py) wrote where a record came from ("Nalezeno
screeningem EUR-Lex Cellar (…, doc/PLAN.md §28) …") into `anotace_poznamka`, which
init_db.py turns into `Document.description` — the public description of the
document. They now write it to `provenance`, and init_db.py to `Document.provenance`,
which no public page shows. This script does the same for the live database:

* adds the column `Document.provenance` when it is missing;
* moves a description that is only such a note to `provenance` and flags the
  document as missing a description (the reason init_db.py gives);
* gives the two records of data/mpo_hydrogen_strategy_documents.json (the national
  hydrogen strategy and its update) the description and provenance that file now
  holds, matched by title.

Dry run unless --apply; back up the database first.

Usage: .venv/bin/python src/tools/backfill_provenance.py [--apply] [--env-file FILE]
"""
import argparse
import json
import pathlib
import re

import pymysql

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
STRATEGY_PATH = REPO_ROOT / "data" / "mpo_hydrogen_strategy_documents.json"
PROVENANCE_NOTE = re.compile(r"^(Nalezeno |Doplněno jako chybějící )")
MISSING_DESCRIPTION = "chybí popis/anotace dokumentu"


def review_flags(review_reason, description):
    """needs_review/review_reason after the description changed: the reason
    "chybí popis/anotace dokumentu" (init_db.detect_data_quality_issues()) is added
    when the description is now empty and dropped when it is not; the other reasons
    the document has (some set by later backfills) stay."""
    reasons = [r for r in (review_reason or "").split("; ") if r and r != MISSING_DESCRIPTION]
    if not (description or "").strip():
        reasons.append(MISSING_DESCRIPTION)
    return bool(reasons), ("; ".join(reasons) or None)


def plan(rows, strategies):
    """Returns [(id, new_description, provenance)] for the documents to change.
    `rows` are (id, title, description, provenance); `strategies` maps a title to
    (description, provenance)."""
    changes = []
    for doc_id, title, description, provenance in rows:
        text = (description or "").strip()
        if title in strategies:
            new_description, new_provenance = strategies[title]
            if (text, provenance) != (new_description, new_provenance):
                changes.append((doc_id, new_description, new_provenance))
        elif PROVENANCE_NOTE.match(text):
            changes.append((doc_id, None, text))
    return changes


def load_strategies(path=STRATEGY_PATH):
    records = json.loads(path.read_text(encoding="utf-8"))
    return {r["nazev_cz"]: (r["anotace_poznamka"], r["provenance"]) for r in records if r.get("provenance")}


def ensure_column(cur):
    cur.execute("SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() "
                "AND TABLE_NAME = 'Document' AND COLUMN_NAME = 'provenance'")
    if cur.fetchone():
        return False
    cur.execute("ALTER TABLE Document ADD COLUMN provenance TEXT NULL")
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--apply", action="store_true", help="change the database (dry run without it)")
    parser.add_argument("--env-file", default=None)
    args = parser.parse_args(argv)
    from dotenv import dotenv_values
    import testdb
    env = dotenv_values(args.env_file or str(testdb.find_env_file(".env")))
    conn = pymysql.connect(host=env["DB_HOST"], port=int(env.get("DB_PORT") or 3306), user=env["DB_USER"],
                           password=env["DB_PASSWORD"], database=env["DB_NAME"], charset="utf8mb4")
    try:
        cur = conn.cursor()
        added = ensure_column(cur) if args.apply else False
        cur.execute("SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() "
                    "AND TABLE_NAME = 'Document' AND COLUMN_NAME = 'provenance'")
        has_column = cur.fetchone()[0] == 1
        cur.execute("SELECT id, review_reason, title, description, "
                    + ("provenance" if has_column else "NULL") + " FROM Document")
        rows = cur.fetchall()
        reasons = {r[0]: r[1] for r in rows}
        changes = plan([(r[0], r[2], r[3], r[4]) for r in rows], load_strategies())
        for doc_id, description, provenance in changes:
            print(f"document {doc_id}: description -> {'(empty)' if not description else description[:60]!r}; "
                  f"provenance <- {provenance[:60]!r}")
        if args.apply:
            for doc_id, description, provenance in changes:
                needs_review, reason = review_flags(reasons[doc_id], description)
                cur.execute("UPDATE Document SET description = %s, provenance = %s, needs_review = %s, "
                            "review_reason = %s WHERE id = %s",
                            (description, provenance, needs_review, reason, doc_id))
            conn.commit()
        print(("column Document.provenance added; " if added else "")
              + f"{len(changes)} documents " + (f"changed in {env['DB_NAME']}" if args.apply
                                                 else "to change (dry run — add --apply)"))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
