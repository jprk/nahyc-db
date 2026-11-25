"""Assigns the areas of the catalogue (data/areas.json, areas.py, doc/OBLASTI.md) to
every document: creates the tables `Area` and `DocumentArea` when missing and
rewrites the areas of the documents whose areas change. The original keywords are
not touched. Prints the breakdown (documents per area), the documents that got only
the fallback area (uncertain) and the keywords no rule knows. Idempotent; run after
every rebuild (init_db.py) and after documents are added. Dry run unless --apply.

Usage: .venv/bin/python src/tools/assign_areas.py [--apply] [--env-file FILE] [--uncertain] [--quiet]
"""
import argparse
import collections

import pymysql

import areas


def report(rules, documents, quiet=False, uncertain=False):
    assigned = {d["id"]: rules.assign(d) for d in documents}
    counts = collections.Counter(code for found in assigned.values() for code in found)
    names = {a["code"]: a["name"] for a in rules.areas}
    lines = []
    if not quiet:
        lines.append("documents per area:")
        for area in rules.areas:
            lines.append(f"  {counts.get(area['code'], 0):5}  {area['code']:22} {names[area['code']]}")
        origins = collections.Counter(next(iter(found.values())) if len(set(found.values())) == 1 else "mixed"
                                      for found in assigned.values())
        lines.append("documents by origin of their areas: " + ", ".join(f"{k} {v}" for k, v in sorted(origins.items())))
        unknown = rules.unknown_keywords(k for d in documents for k in d["keywords"])
        lines.append(f"keywords no rule knows: {len(unknown)}" + ("" if not unknown else " — " + "; ".join(unknown)))
    fallback = [d for d in documents if list(assigned[d["id"]]) == [rules.fallback]]
    lines.append(f"uncertain (fallback area only): {len(fallback)} documents")
    if uncertain:
        for d in sorted(fallback, key=lambda d: d["id"]):
            lines.append(f"  #{d['id']} {d['identifier'] or ''} — {(d['title'] or '')[:110]}")
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--apply", action="store_true", help="write the areas")
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--uncertain", action="store_true", help="list the documents with the fallback area only")
    parser.add_argument("--quiet", action="store_true", help="only the summary line")
    args = parser.parse_args(argv)
    from dotenv import dotenv_values
    import testdb
    env = dotenv_values(args.env_file or str(testdb.find_env_file(".env")))
    conn = pymysql.connect(host=env["DB_HOST"], port=int(env.get("DB_PORT") or 3306), user=env["DB_USER"],
                           password=env["DB_PASSWORD"], database=env["DB_NAME"], charset="utf8mb4")
    rules = areas.load()
    try:
        cur = conn.cursor()
        documents = areas.load_documents(cur)
        for line in report(rules, documents, quiet=args.quiet, uncertain=args.uncertain):
            print(line)
        changes = areas.plan(rules, documents, areas.current(cur))
        if args.apply:
            areas.execute(cur, rules, changes)
            conn.commit()
        print(f"{len(changes)} of {len(documents)} documents get new areas "
              + (f"(written to {env['DB_NAME']})" if args.apply else "(dry run — add --apply)"))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
