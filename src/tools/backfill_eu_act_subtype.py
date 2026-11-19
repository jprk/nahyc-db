"""Adds and fills `Document.eu_act_subtype` in an existing database
(doc/MPO_PRIPOMINKY.md, krok 2): delegated / implementing EU acts, as decided by
eu_act_subtype.classify() — the same function init_db.py uses on a rebuild.

* adds the column `Document.eu_act_subtype ENUM('delegated','implementing') NULL`
  when it is missing (doc/konsolidace/Konsolidace-DB-schema.sql);
* sets it for every document whose value differs from classify().

Dry run unless --apply; back up the database first. Running it again changes
nothing. run_tests.py applies it to the test database after each refresh, until
the live database has the column.

Usage: .venv/bin/python src/tools/backfill_eu_act_subtype.py [--apply] [--env-file FILE]
"""
import argparse
import pathlib
import sys

import pymysql

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import eu_act_subtype  # noqa: E402

COLUMN_DDL = "ALTER TABLE Document ADD COLUMN eu_act_subtype ENUM('delegated','implementing') NULL"


def has_column(cur):
    cur.execute("SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() "
                "AND TABLE_NAME = 'Document' AND COLUMN_NAME = 'eu_act_subtype'")
    return cur.fetchone()[0] == 1


def plan(rows):
    """[(id, identifier, old, new)] for the documents whose subtype changes;
    `rows` are (id, identifier, title, url, jurisdikce, current subtype)."""
    changes = []
    for doc_id, identifier, title, url, jurisdikce, current in rows:
        new = eu_act_subtype.classify(title, url, jurisdikce)
        if new != (current or None):
            changes.append((doc_id, identifier, current, new))
    return changes


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--apply", action="store_true", help="change the database (dry run without it)")
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--quiet", action="store_true", help="print only the summary")
    args = parser.parse_args(argv)
    from dotenv import dotenv_values
    import testdb
    env = dotenv_values(args.env_file or str(testdb.find_env_file(".env")))
    conn = pymysql.connect(host=env["DB_HOST"], port=int(env.get("DB_PORT") or 3306), user=env["DB_USER"],
                           password=env["DB_PASSWORD"], database=env["DB_NAME"], charset="utf8mb4")
    try:
        cur = conn.cursor()
        present = has_column(cur)
        added = False
        if args.apply and not present:
            cur.execute(COLUMN_DDL)
            present = added = True
        cur.execute("SELECT id, identifier, title, url, jurisdikce, "
                    + ("eu_act_subtype" if present else "NULL") + " FROM Document ORDER BY id")
        changes = plan(cur.fetchall())
        if not args.quiet:
            for doc_id, identifier, old, new in changes:
                print(f"document {doc_id} {identifier or ''}: {old or '-'} -> {new or '-'}")
        if args.apply:
            for doc_id, _, _, new in changes:
                cur.execute("UPDATE Document SET eu_act_subtype = %s WHERE id = %s", (new, doc_id))
            conn.commit()
        print(("column Document.eu_act_subtype added; " if added else "")
              + ("" if present else "column Document.eu_act_subtype missing (would be added); ")
              + f"{len(changes)} documents " + (f"changed in {env['DB_NAME']}" if args.apply
                                                 else "to change (dry run — add --apply)"))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
