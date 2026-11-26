"""Cleans the standards-body stage stamps out of the live database
(doc/MPO_OVERENI_WEBU.md Z3, 2026-11-21).

The Sinay standards spreadsheet carried, for DIN/ISO standards and their drafts,
German/Slovak stage stamps where the web shows the effective date ("Platnost od":
"Arbeitsdokument (Work Item)-Pracovný dokument (pracovná položka)"), a German
"not available yet" note as the description ("noch nocht vorhanden") and a dated
Slovak stage note as a source category ("Stav k 02/2025: v príprave"). init_db.py no longer
stores them (normalize_effective_date(), is_placeholder_description(),
is_status_keyword()); this script applies the same rules to an existing database:

* `Document.effective_date` and `DocumentVersion.effective_date` → normalize_effective_date()
  (a published standard keeps "od MM/RRRR", a draft or work item nothing);
* a placeholder description → empty, flagged for review as a rebuild flags it
  ("chybí popis/anotace dokumentu");
* the links to a stage-note source category are deleted, then the category itself
  (SourceCategory/DocumentSourceCategory — run migrate_vocabulary.py first).

The lifecycle state is not touched (it was classified from the raw stamp).
Idempotent. Dry run unless --apply; back up the database first (backup_db.py).

Usage: .venv/bin/python src/tools/fix_norm_stage_fields.py [--apply] [--env-file FILE]
"""
import argparse

import pymysql

import init_db

MISSING_DESCRIPTION = "chybí popis/anotace dokumentu"


def plan(cursor):
    """{"documents": [(id, column, old, new)], "versions": [(id, old, new)],
    "reviews": [(id, needs_review, review_reason)], "categories": [(id, name, links)]}."""
    documents, reviews = [], []
    cursor.execute("SELECT id, effective_date, description, needs_review, review_reason FROM Document")
    for doc_id, effective, description, needs_review, reason in cursor.fetchall():
        if effective is not None and init_db.normalize_effective_date(effective) != effective:
            documents.append((doc_id, "effective_date", effective, init_db.normalize_effective_date(effective)))
        if description and init_db.is_placeholder_description(description):
            documents.append((doc_id, "description", description, ""))
            reasons = [r for r in (reason or "").split("; ") if r]
            if MISSING_DESCRIPTION not in reasons:
                reasons.append(MISSING_DESCRIPTION)
            reviews.append((doc_id, 1, "; ".join(reasons)))
    versions = []
    cursor.execute("SELECT id, effective_date FROM DocumentVersion WHERE effective_date IS NOT NULL")
    for version_id, effective in cursor.fetchall():
        new = init_db.normalize_effective_date(effective) or None
        if new != effective:
            versions.append((version_id, effective, new))
    categories = []
    cursor.execute("SELECT c.id, c.name, COUNT(dc.document_id) FROM SourceCategory c "
                   "LEFT JOIN DocumentSourceCategory dc ON dc.category_id = c.id GROUP BY c.id, c.name")
    for category_id, name, links in cursor.fetchall():
        if init_db.is_status_keyword(name):
            categories.append((category_id, name, links))
    return {"documents": documents, "versions": versions, "reviews": reviews, "categories": categories}


def execute(cursor, changes):
    for doc_id, column, _old, new in changes["documents"]:
        cursor.execute(f"UPDATE Document SET {column} = %s WHERE id = %s", (new, doc_id))
    for doc_id, needs_review, reason in changes["reviews"]:
        cursor.execute("UPDATE Document SET needs_review = %s, review_reason = %s WHERE id = %s",
                       (needs_review, reason, doc_id))
    for version_id, _old, new in changes["versions"]:
        cursor.execute("UPDATE DocumentVersion SET effective_date = %s WHERE id = %s", (new, version_id))
    for category_id, _category, _links in changes["categories"]:
        cursor.execute("DELETE FROM DocumentSourceCategory WHERE category_id = %s", (category_id,))
        cursor.execute("DELETE FROM SourceCategory WHERE id = %s", (category_id,))


def summary(changes):
    effective = [c for c in changes["documents"] if c[1] == "effective_date"]
    lines = [f"effective_date: {len(effective)} documents "
             f"({sum(1 for c in effective if c[3])} → od MM/RRRR, {sum(1 for c in effective if not c[3])} → empty)",
             f"description (placeholder → empty, flagged for review): "
             f"{sum(1 for c in changes['documents'] if c[1] == 'description')} documents",
             f"DocumentVersion.effective_date: {len(changes['versions'])} versions"]
    for _id, name, links in changes["categories"]:
        lines.append(f"source category {name!r}: deleted with {links} links")
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--apply", action="store_true", help="write the changes")
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--verbose", action="store_true", help="list every change")
    args = parser.parse_args(argv)
    from dotenv import dotenv_values
    import testdb
    env = dotenv_values(args.env_file or str(testdb.find_env_file(".env")))
    conn = pymysql.connect(host=env["DB_HOST"], port=int(env.get("DB_PORT") or 3306), user=env["DB_USER"],
                           password=env["DB_PASSWORD"], database=env["DB_NAME"], charset="utf8mb4")
    try:
        cur = conn.cursor()
        changes = plan(cur)
        if args.verbose:
            for doc_id, column, old, new in changes["documents"]:
                print(f"document {doc_id} {column}: {old!r} -> {new!r}")
        for line in summary(changes):
            print(line)
        if args.apply:
            execute(cur, changes)
            conn.commit()
        print(f"written to {env['DB_NAME']}" if args.apply else "(dry run — add --apply)")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
