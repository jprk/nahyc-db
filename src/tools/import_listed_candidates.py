"""Puts a hand-checked list of candidates into the queue (`DocumentCandidate`,
/admin/candidates): a JSON file with `source` and `candidates`, each with the
fields of the queue (candidate_key, designation, title, document_type, url,
language, jurisdikce, validity_status, puvodce, scope_area, evidence). First
used for the missing items of the RFNBO audit (data/rfnbo_candidates.json,
doc/RFNBO_POKRYTI.md).

A candidate already in the queue (any state, any source) is kept as it is, and
so is one whose designation is already a document of the database — the
decisions of editors and of the automat are never touched. Idempotent. Dry run
unless --apply.

Usage: .venv/bin/python src/tools/import_listed_candidates.py FILE [--apply] [--env-file FILE]
"""
import argparse
import json
import pathlib

import pymysql

import candidates as cd


def load(path):
    data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    return data["source"], data["candidates"]


def plan(cursor, source, found):
    """[(candidate, outcome)] — outcome "insert", "in queue (<status>)" or "in database (#id)"."""
    result = []
    for c in found:
        cursor.execute("SELECT status FROM DocumentCandidate WHERE candidate_key = %s", (c["candidate_key"],))
        row = cursor.fetchone()
        if row:
            result.append((c, f"in queue ({row[0]})"))
            continue
        cursor.execute("SELECT id FROM Document WHERE identifier = %s", (c["designation"],))
        row = cursor.fetchone()
        result.append((c, f"in database (#{row[0]})" if row else "insert"))
    return result


def execute(cursor, source, planned):
    for c, outcome in planned:
        if outcome != "insert":
            continue
        cursor.execute("""INSERT INTO DocumentCandidate
            (candidate_key, source, designation, title, document_type, url, language, jurisdikce,
             scope_area, validity_status, evidence_json, cited_by, puvodce)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0, %s)""",
                       (c["candidate_key"], source, c.get("designation"), c.get("title"), c.get("document_type"),
                        c.get("url"), c.get("language"), c.get("jurisdikce"), c.get("scope_area"),
                        c.get("validity_status"), json.dumps(c.get("evidence") or {}, ensure_ascii=False),
                        c.get("puvodce")))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("file")
    parser.add_argument("--apply", action="store_true", help="write to the database (dry run without it)")
    parser.add_argument("--env-file", default=None)
    args = parser.parse_args(argv)
    source, found = load(args.file)
    from dotenv import dotenv_values
    import testdb
    env = dotenv_values(args.env_file or str(testdb.find_env_file(".env")))
    conn = pymysql.connect(host=env["DB_HOST"], port=int(env.get("DB_PORT") or 3306), user=env["DB_USER"],
                           password=env["DB_PASSWORD"], database=env["DB_NAME"], charset="utf8mb4")
    try:
        cur = conn.cursor()
        planned = plan(cur, source, found)
        for c, outcome in planned:
            print(f"{c['candidate_key']:22} {c.get('designation') or '':16} {outcome}")
        inserts = sum(1 for _, o in planned if o == "insert")
        if args.apply and inserts:
            execute(cur, source, planned)
            conn.commit()
        print(f"{inserts} candidates of the source {source} "
              + (f"inserted into {env['DB_NAME']}" if args.apply else "to insert (dry run — add --apply)"))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
