"""Applies the states of doc/DATABASE_SCOPE.md odstavec 5 to the live database
(document_states.py): the current version of a document the validity check
(check_validity.py) found repealed becomes `repealed`, one not yet in effect
`promulgated`, and one the check now finds in effect goes back to `active` (a state
an editor confirmed, app/drafts_admin.py, is kept until a check says otherwise); the
enum of `DocumentVersion.lifecycle_state` is extended when it does not know the new
values. Adds `REPEALS` from the repealing act to the repealed one where the database
has both, and writes those relations to data/document_relations_validity.json for a
rebuild (load_document_relations.py).

Also writes the date of the last check of every document's state
(`Document.status_checked_at`, `status_checked_by`; status_checks.py) where the
caches know a newer one, and creates what the editor pages of prepared documents
need (state_changes.ensure_schema: table DocumentStateChange, relation type
ENACTED_AS) — the migration of doc/MPO_PRIPOMINKY.md krok 3.

Editions of standards (norm_editions.py, 2026-11-20): a new edition of a ČSN that
the check of the catalogue found issued with a later date of effect
(data/norm_validity_cache.json, `upcoming`) is added as a further version in the
state `promulgated`; on its date of effect it becomes the current version and the
edition it replaces `superseded`. The scheduler runs this script on the first day
of every month (deploy/scheduler/h2db-states-monthly.timer), the day on which ČSN
take effect. `--today` plans for another day (a dry run of the switch). When the
edition switched to has another designation, the document is renamed (slug kept)
and the renaming recorded in data/manual_corrections.json, data/fulltext_manifest.json
and data/norm_validity_cache.json (norm_editions.persist()).

Dry run unless --apply; back up the database first.

Usage: .venv/bin/python src/tools/backfill_document_states.py [--apply] [--env-file FILE] [--today YYYY-MM-DD]
"""
import argparse
import datetime
import json

import pymysql

import document_states as ds
import norm_editions
import state_changes
import status_checks


def ensure_states(cursor):
    """Extends the lifecycle_state enum when it lacks a state; True when it did."""
    cursor.execute("SELECT COLUMN_TYPE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() "
                   "AND TABLE_NAME = 'DocumentVersion' AND COLUMN_NAME = 'lifecycle_state'")
    column_type = cursor.fetchone()[0]
    missing = [s for s in ds.STATES if f"'{s}'" not in column_type]
    if not missing:
        return False
    members = ",".join(f"'{s}'" for s in ds.STATES)
    cursor.execute(f"ALTER TABLE DocumentVersion MODIFY COLUMN lifecycle_state ENUM({members}) NOT NULL DEFAULT 'active'")
    return True


def plan_states(rows, cache):
    """[(version id, document id, identifier, old, new)] for the current versions
    `rows` = [(document id, identifier, title, version id, state)] whose state changes."""
    changes = []
    for doc_id, identifier, title, version_id, old in rows:
        base = "draft" if old == "draft" else "active"
        new = ds.current_state(base, identifier, title, cache)
        if new == "active" and not ds.in_effect(identifier, title, cache):
            new = old  # back to `active` only on the check's word, not for want of an entry
        if new != old and old in ("active", "draft", "repealed", "promulgated"):
            changes.append((version_id, doc_id, identifier, old, new))
    return changes


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--apply", action="store_true", help="change the database (dry run without it)")
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--today", default=None, help="the day to plan the editions of standards for (ISO date; "
                                                      "default today)")
    args = parser.parse_args(argv)
    today = args.today or datetime.date.today().isoformat()
    from dotenv import dotenv_values
    import testdb
    env = dotenv_values(args.env_file or str(testdb.find_env_file(".env")))
    conn = pymysql.connect(host=env["DB_HOST"], port=int(env.get("DB_PORT") or 3306), user=env["DB_USER"],
                           password=env["DB_PASSWORD"], database=env["DB_NAME"])
    cache = ds.load_cache()
    try:
        cur = conn.cursor()
        cur.execute("SELECT d.id, d.identifier, d.title, dv.id, dv.lifecycle_state FROM Document d "
                    "JOIN DocumentVersion dv ON dv.document_id = d.id AND dv.is_current = 1")
        rows = cur.fetchall()
        changes = plan_states(rows, cache)
        for _version, doc_id, identifier, old, new in changes:
            print(f"document {doc_id} ({identifier}): {old} -> {new}")
        relations = ds.repeal_relations([(r[1], r[2]) for r in rows], cache)
        ids = {}
        for doc_id, identifier, *_ in rows:
            if identifier:
                ids.setdefault(identifier, doc_id)
        cur.execute("SELECT from_document_id, to_document_id FROM document_relation WHERE relation_type = 'REPEALS'")
        existing = set(cur.fetchall())
        new_relations = [r for r in relations if (ids[r["from_identifier"]], ids[r["to_identifier"]]) not in existing]
        for r in new_relations:
            print(f"REPEALS: {r['from_identifier']} -> {r['to_identifier']}")
        cur.execute("SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() "
                    "AND TABLE_NAME = 'Document' AND COLUMN_NAME = 'status_checked_at'")
        has_columns = bool(cur.fetchone()[0])
        if has_columns:
            cur.execute("SELECT id, identifier, title, status_checked_at FROM Document")
        else:
            cur.execute("SELECT id, identifier, title, NULL FROM Document")
            print("Document.status_checked_at/status_checked_by missing — added with --apply")
        checks = status_checks.plan_checks(cur.fetchall(), status_checks.load_caches())
        by_source = {}
        for _doc_id, _date, label in checks:
            by_source[label] = by_source.get(label, 0) + 1
        editions = norm_editions.apply(cur, status_checks.load(status_checks.NORM_CACHE_PATH), today, write=False)
        for action in editions:
            print(norm_editions.describe(action))
        print(f"last check of the state: {len(checks)} documents get a newer date "
              + (", ".join(f"{label} {n}" for label, n in sorted(by_source.items())) or "—"))
        if args.apply:
            if ensure_states(cur):
                print("lifecycle_state enum extended with " + ", ".join(ds.STATES))
            if status_checks.ensure_columns(cur):
                print("Document.status_checked_at, status_checked_by added")
            for what in state_changes.ensure_schema(cur):
                print(f"created {what}")
            for doc_id, date, label in checks:
                cur.execute("UPDATE Document SET status_checked_at = %s, status_checked_by = %s WHERE id = %s",
                            (date, label, doc_id))
            for version_id, _doc_id, _identifier, _old, new in changes:
                cur.execute("UPDATE DocumentVersion SET lifecycle_state = %s WHERE id = %s", (new, version_id))
            norm_editions.execute(cur, editions)
            for r in new_relations:
                cur.execute("INSERT INTO document_relation (from_document_id, to_document_id, relation_type, note) "
                            "VALUES (%s, %s, 'REPEALS', %s)", (ids[r["from_identifier"]], ids[r["to_identifier"]], r["note"]))
            conn.commit()
            # a standard renamed by the switch keeps its new designation through a rebuild
            for message in norm_editions.persist(editions, today):
                print(message)
            ds.RELATIONS_PATH.write_text(json.dumps(relations, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{len(changes)} states, {len(new_relations)} REPEALS relations, {len(checks)} check dates, "
              f"{len(editions)} changes of editions of standards (on {today}) "
              + (f"written to {env['DB_NAME']}" if args.apply else "(dry run — add --apply)"))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
