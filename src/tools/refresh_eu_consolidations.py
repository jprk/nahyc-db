"""Keeps the consolidated versions of the EU acts of data/eu_consolidated_acts.json
(CLP, REACH) up to date (eu_consolidations.py; doc/CELLAR_FULLTEXT.md, odstavec 7;
doc/PROVOZ.md, odstavec 5.3). Run daily by the scheduler (deploy/scheduler/,
`scheduled_harvest.sh daily`, and in `states` on the first day of every month):

1. asks Cellar (SPARQL, src/sites/eurlex.py) which consolidated versions every act
   has in its language, future ones included, and stores them in
   data/eu_consolidation_cache.json (a failed query keeps what was known);
2. downloads the text of the version in effect on the day when the manifest does
   not have it yet — from Cellar only (fetch_fulltext.fetch_one, field
   `konsolidace_<YYYYMMDD>`) — and extracts its clean text (extract_fulltext.py);
3. writes the versions to the database: the version in effect becomes the current
   one, the previous one `superseded`, a prepared one `promulgated`; the document
   shows the newest text in effect it has (eu_consolidations.apply());
4. moves the date of the last check of the state of the act (`Document.status_checked_at`,
   `status_checked_by`; status_checks.py) to the day Cellar answered — never back
   (doc/MPO_OVERENI_WEBU.md Z5).

Dry run unless --apply: Cellar is asked, but nothing is written, downloaded or
changed. `--today` plans for another day (simulation of 1. 1. 2027). `--offline`
skips Cellar (the cache as it is), `--no-fetch` the download. `--out-dir` and
`--clean-dir` keep the downloaded and extracted files out of data/fulltext/ and
data/fulltext_clean/ (a worktree). `--backup` backs the database up (backup_db.py)
before a write, and only when there is something to write.

Exit status 1 when Cellar did not answer or a download/extraction failed.

Usage: .venv/bin/python src/tools/refresh_eu_consolidations.py [--apply] [--env-file FILE] [--today YYYY-MM-DD]
           [--offline] [--no-fetch] [--out-dir DIR] [--clean-dir DIR] [--backup]
"""
import argparse
import datetime
import pathlib
import subprocess
import sys

import pymysql
import requests

import eu_consolidations as ec
import status_checks
import extract_fulltext
import fetch_fulltext as ff

BASE_DIR = pathlib.Path(__file__).resolve().parent


def missing_texts(targets, manifest, repo_root=ff.REPO_ROOT, out_dir=None):
    """[(record, field, url, key)] of the consolidated versions in effect (fetch
    targets of the field `konsolidace_*`) whose text the manifest lacks — no fetched
    entry, another address, or the file is in neither data/fulltext/ nor `out_dir`."""
    missing = []
    for record, field, url in targets:
        if not field.startswith(ec.FIELD_PREFIX):
            continue
        key = ff.manifest_key(record["zdroj_dat"], record["znacka"].strip(), field)
        entry = manifest.get(key) or {}
        name = pathlib.Path(entry.get("local_path") or "x").name
        present = entry.get("status") == "fetched" and entry.get("url") == url and (
            (pathlib.Path(repo_root) / entry["local_path"]).is_file()
            or (out_dir is not None and (pathlib.Path(out_dir) / name).is_file()))
        if not present:
            missing.append((record, field, url, key))
    return missing


def fetch_and_extract(missing, out_dir=None, clean_dir=None, fetch=ff.fetch_one, extract=extract_fulltext.run):
    """Downloads every missing text (from Cellar, fetch_fulltext.fetch_one), records it
    in the manifest and extracts its clean text. Returns [problem]."""
    problems = []
    manifest = ff.load_manifest()
    session = requests.Session()
    session.headers.update({"User-Agent": ff.USER_AGENT})
    fetched = []
    for record, field, url, key in missing:
        entry = fetch(session, record, field, url, out_dir)
        if entry.get("status") != "fetched":
            problems.append(f"{key}: download failed — {entry.get('error')}")
            print(f"{key}: download failed — {entry.get('error')}")
            continue  # the manifest keeps what it had: a failed attempt must not hide an older text
        manifest[key] = entry
        ff.save_manifest(manifest)
        fetched.append(key)
        print(f"{key}: downloaded {entry['local_path']} ({entry.get('celex')})")
    if fetched:
        stats, failed = extract(apply=True, only=fetched, in_dir=out_dir,
                                output_dir=pathlib.Path(clean_dir) if clean_dir else extract_fulltext.OUTPUT_DIR)
        for label, count in sorted(stats.items()):
            print(f"  clean text: {count} {label}")
        problems += [f"{key}: extraction failed — {message}" for key, message in failed]
    return problems


def plan_status_checks(cursor, config, cache):
    """[(document id, date, label)] of the acts of `config` whose date of the last
    check of the state the refreshed `cache` moves forward (status_checks.plan_checks())."""
    identifiers = [act["identifier"] for act in config]
    if not identifiers:
        return []
    cursor.execute("SELECT id, identifier, title, status_checked_at FROM Document WHERE identifier IN ("
                   + ", ".join(["%s"] * len(identifiers)) + ")", identifiers)
    return status_checks.plan_checks(cursor.fetchall(), status_checks.load_caches(consolidations=cache))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--apply", action="store_true", help="write the cache, download, change the database")
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--today", default=None, help="the day to plan for (ISO date; default today)")
    parser.add_argument("--offline", action="store_true", help="do not ask Cellar, use the cache as it is")
    parser.add_argument("--no-fetch", action="store_true", help="do not download the texts")
    parser.add_argument("--out-dir", default=None, metavar="DIR", help="store downloads in DIR (fetch_fulltext.py)")
    parser.add_argument("--clean-dir", default=None, metavar="DIR", help="store clean texts in DIR")
    parser.add_argument("--backup", action="store_true", help="back the database up before writing to it")
    args = parser.parse_args(argv)
    today = args.today or datetime.date.today().isoformat()
    status = 0

    config, cache = ec.load_config(), ec.load_cache()
    if not args.offline:
        messages, failed = ec.refresh(config, cache, datetime.date.today().isoformat())
        for message in messages:
            print(message)
        if failed:
            status = 1
        if args.apply:
            ec.save_cache(cache)

    targets = list(ff.load_targets(ec.fetch_targets(config, cache, today)))
    missing = missing_texts(targets, ff.load_manifest(), out_dir=args.out_dir)
    for _record, _field, url, key in missing:
        print(f"{key}: text of the version in effect not downloaded yet ({url})"
              + ("" if args.apply and not args.no_fetch else " — would be downloaded"))
    if missing and args.apply and not args.no_fetch:
        if fetch_and_extract(missing, args.out_dir, args.clean_dir):
            status = 1

    from dotenv import dotenv_values
    import testdb
    env = dotenv_values(args.env_file or str(testdb.find_env_file(".env")))
    conn = pymysql.connect(host=env["DB_HOST"], port=int(env.get("DB_PORT") or 3306), user=env["DB_USER"],
                           password=env["DB_PASSWORD"], database=env["DB_NAME"], charset="utf8mb4")
    try:
        cur = conn.cursor()
        actions = ec.apply(cur, today, write=False, config=config, cache=cache)
        for action in actions:
            print(ec.describe(action))
        writes = [a for a in actions if a["action"] != "skip"]
        checks = plan_status_checks(cur, config, cache)
        for doc_id, date, label in checks:
            print(f"document {doc_id}: last check of the state {date} ({label})")
        if args.apply and checks:
            status_checks.ensure_columns(cur)
            for doc_id, date, label in checks:
                cur.execute("UPDATE Document SET status_checked_at = %s, status_checked_by = %s WHERE id = %s",
                            (date, label, doc_id))
            conn.commit()
        if args.apply and writes:
            if args.backup:
                subprocess.run([sys.executable, str(BASE_DIR / "backup_db.py"), "--reason", "before_eu_consolidations"]
                               + (["--env-file", args.env_file] if args.env_file else []), check=True)
            if ec.ensure_schema(cur):
                print("DocumentVersion.url added")
            ec.execute(cur, writes)
            conn.commit()
        print(f"{len(writes)} changes of consolidated versions (on {today}) "
              + (f"written to {env['DB_NAME']}" if args.apply else "(dry run — add --apply)"))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return status


if __name__ == "__main__":
    sys.exit(main())
