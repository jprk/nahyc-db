"""Applies the states of doc/DATABASE_SCOPE.md odstavec 5 to the live database
(document_states.py): the current version of a document the validity check
(check_validity.py) found repealed becomes `repealed`, one not yet in effect
`promulgated`, and one that no longer is either goes back to `active`; the enum of
`DocumentVersion.lifecycle_state` is extended when it does not know the new values.
Adds `REPEALS` from the repealing act to the repealed one where the database has
both, and writes those relations to data/document_relations_validity.json for a
rebuild (load_document_relations.py). Dry run unless --apply; back up the database
first.

Usage: .venv/bin/python src/tools/backfill_document_states.py [--apply] [--env-file FILE]
"""
import argparse
import json

import pymysql

import document_states as ds


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
        if new != old and old in ("active", "draft", "repealed", "promulgated"):
            changes.append((version_id, doc_id, identifier, old, new))
    return changes


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--apply", action="store_true", help="change the database (dry run without it)")
    parser.add_argument("--env-file", default=None)
    args = parser.parse_args(argv)
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
        if args.apply:
            if ensure_states(cur):
                print("lifecycle_state enum extended with " + ", ".join(ds.STATES))
            for version_id, _doc_id, _identifier, _old, new in changes:
                cur.execute("UPDATE DocumentVersion SET lifecycle_state = %s WHERE id = %s", (new, version_id))
            for r in new_relations:
                cur.execute("INSERT INTO document_relation (from_document_id, to_document_id, relation_type, note) "
                            "VALUES (%s, %s, 'REPEALS', %s)", (ids[r["from_identifier"]], ids[r["to_identifier"]], r["note"]))
            conn.commit()
            ds.RELATIONS_PATH.write_text(json.dumps(relations, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{len(changes)} states, {len(new_relations)} REPEALS relations "
              + (f"written to {env['DB_NAME']}" if args.apply else "(dry run — add --apply)"))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
