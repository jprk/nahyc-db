"""Reports candidates for new documents into the table `DocumentCandidate`
(candidates.py), where editors decide about them on /admin/candidates.

Candidates come from the citation closure (citation_closure.py: Czech and EU acts
the texts in the database cite, at least twice, not mainly as amending acts, not
repealed) and from the validity check (check_validity.py: acts that repealed a
document of the database but are missing from it). Titles are looked up in Cellar
(EU) and on zakonyprolidi.cz (Czech acts). A candidate already reported only gets
its evidence refreshed; decisions are kept. Creates the table when it is missing.
Dry run unless --apply.

Usage: .venv/bin/python src/tools/import_candidates.py [--apply] [--env-file FILE] [--minimum K]
"""
import argparse
import collections
import time

import pymysql
import requests

import candidates as cd
import citation_closure as cc
import document_states as ds

USER_AGENT = "Mozilla/5.0 (compatible; NAHYC-DP004-candidates/1.0; +research use, low-volume)"


def collect(documents, texts, cache, minimum):
    rows = cc.closure(documents, texts)
    found = {c["candidate_key"]: c for c in cd.from_closure(rows, cache, minimum)}
    for candidate in cd.from_validity(documents, cache):
        found.setdefault(candidate["candidate_key"], candidate)
    return sorted(found.values(), key=lambda c: (-c["cited_by"], c["candidate_key"]))


def lookup_titles(session, found):
    titles = cd.eu_titles(session, [(c["candidate_key"], c["kind"]) for c in found if c["candidate_key"].startswith("EU:")])
    for candidate in found:
        if candidate["candidate_key"].startswith("CZ:"):
            title = cd.cz_title(session, candidate["candidate_key"])
            titles[candidate["candidate_key"]] = (None, title)
            time.sleep(0.5)
    return titles


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--apply", action="store_true", help="write to the database (dry run without it)")
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--minimum", type=int, default=2, help="cited by at least this many documents")
    args = parser.parse_args(argv)
    documents, texts, database = cc.load_from_database(args.env_file)
    found = collect(documents, texts, ds.load_cache(), args.minimum)
    print(f"{len(found)} candidates: " + ", ".join(f"{k} {v}" for k, v in collections.Counter(
        (c["source"], c["candidate_key"].split(":")[0]) for c in found).items()))
    if not args.apply:
        for c in found[:15]:
            print(f"  {c['cited_by']:3} {c['source']:9} {c['candidate_key']}")
        print("(dry run — add --apply; titles are looked up only then)")
        return
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    titles = lookup_titles(session, found)
    from dotenv import dotenv_values
    import testdb
    env = dotenv_values(args.env_file or str(testdb.find_env_file(".env")))
    conn = pymysql.connect(host=env["DB_HOST"], port=int(env.get("DB_PORT") or 3306), user=env["DB_USER"],
                           password=env["DB_PASSWORD"], database=env["DB_NAME"], cursorclass=pymysql.cursors.DictCursor)
    try:
        with conn.cursor() as cur:
            cd.ensure_schema(cur)
            outcome = collections.Counter(cd.upsert(cur, cd.complete(c, titles)) for c in found)
        conn.commit()
    finally:
        conn.close()
    print(f"{database}: " + ", ".join(f"{v} {k}" for k, v in outcome.items())
          + f"; titles found for {sum(1 for c in found if titles.get(c['candidate_key'], (None, None))[1])}")


if __name__ == "__main__":
    main()
