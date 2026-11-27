"""Edition and effect of the versions of Czech and EU legal acts (issue #38;
act_versions.py). Run daily by the scheduler (scheduled_harvest.sh daily):

1. asks the sources which versions every Czech and EU act of the database has —
   e-Sbírka linked open data (the versions of a Czech act and the day each takes
   effect) and Cellar (the entry into force of an EU act and its consolidated
   versions in the document's language) — and stores the answers in
   data/act_versions_cache.json (an act the source did not answer for keeps what
   was known);
2. downloads the text of a version newer than the stored one once it is in effect
   (fetch_fulltext.fetch_one: a Czech act from zakonyprolidi.cz, an EU act from
   Cellar) and extracts its clean text (extract_fulltext.py);
3. writes the versions to the database (act_versions.apply()): the edition, the
   day of effect and the publisher's page of the baseline version (only where
   empty), the later versions, the text the document shows and an empty
   "Platnost od".

Dry run unless --apply: the sources are asked, nothing is written, downloaded or
changed. `--offline` skips the sources (the cache as it is), `--no-fetch` the
download, `--only` limits the run to some identifiers (a trial). `--out-dir` and
`--clean-dir` keep the downloaded and extracted files out of data/fulltext/ and
data/fulltext_clean/ (a worktree). `--backup` backs the database up (backup_db.py)
before a write, and only when there is something to write.

Exit status 1 when a source did not answer or a download/extraction failed.

Usage: .venv/bin/python src/tools/refresh_act_versions.py [--apply] [--env-file FILE] [--today YYYY-MM-DD]
           [--offline] [--no-fetch] [--only IDENTIFIER ...] [--out-dir DIR] [--clean-dir DIR] [--backup]
"""
import argparse
import datetime
import pathlib
import re
import subprocess
import sys
import time

import pymysql
import requests

import act_versions as av
import check_validity as cv
import eu_consolidations as ec
import fetch_fulltext as ff
import refresh_eu_consolidations as rec

BASE_DIR = pathlib.Path(__file__).resolve().parent
ESB = cv.ESB
BATCH = 40


def czech_versions(session, acts, sparql=cv._sparql):
    """{key: {"first_effective", "versions"}} of Czech acts [(key, number, year)] from
    e-Sbírka; a key missing from the answer is left out (the caller keeps the cache)."""
    result = {}
    for start in range(0, len(acts), BATCH):
        chunk = acts[start:start + BATCH]
        nodes = {cv.ELI.format(year=year, number=number): key for key, number, year in chunk}
        query = f"""SELECT ?act ?from WHERE {{
  VALUES ?act {{ {' '.join(f'<{n}>' for n in nodes)} }}
  ?act <{ESB}má-znění> ?version . ?version <{ESB}účinnost-znění-od> ?from
}}"""
        try:
            rows = sparql(session, cv.ESBIRKA, query, output_param="output")
        except (requests.RequestException, ValueError, KeyError) as error:
            print(f"e-Sbírka did not answer for {len(chunk)} acts: {error}")
            continue
        dates = {}
        for row in rows:
            date = row["from"]["value"][:10]
            if not date.startswith("0000"):
                dates.setdefault(nodes[row["act"]["value"]], set()).add(date)
        for key, found in dates.items():
            result[key] = {"first_effective": min(found), "versions": [{"id": d, "date": d} for d in sorted(found)]}
        time.sleep(1)
    return result


def eu_entry_into_force(session, celexes, sparql=cv._sparql):
    """{celex: the earliest entry into force} from Cellar; a failed batch is left out."""
    result = {}
    for start in range(0, len(celexes), BATCH):
        chunk = celexes[start:start + BATCH]
        values = " ".join(f'"{c}"^^<http://www.w3.org/2001/XMLSchema#string>' for c in chunk)
        query = f"""PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
SELECT ?celex (MIN(?eif) AS ?first) WHERE {{
  VALUES ?celex {{ {values} }}
  ?w cdm:resource_legal_id_celex ?celex . ?w cdm:resource_legal_date_entry-into-force ?eif
}} GROUP BY ?celex"""
        try:
            rows = sparql(session, cv.CELLAR, query)
        except (requests.RequestException, ValueError, KeyError) as error:
            print(f"Cellar did not answer for {len(chunk)} acts: {error}")
            continue
        for row in rows:
            result[row["celex"]["value"]] = row["first"]["value"][:10]
        time.sleep(1)
    return result


def query_sources(documents, session, consolidated=None):
    """{identifier: found} (act_versions.record_check()) of the `documents`."""
    if consolidated is None:
        sys.path.insert(0, str(BASE_DIR.parent))
        from sites.eurlex import consolidated_versions as consolidated
    found = {}
    czech = {}
    for identifier, doc in documents.items():
        act = doc["act"]
        if act["family"] == "CZ":
            czech.setdefault(act["key"], []).append(identifier)
    answers = czech_versions(session, [(key, int(key.split(":")[1].split("/")[0]), int(key.split("/")[1]))
                                       for key in sorted(czech)])
    for key, identifiers in czech.items():
        for identifier in identifiers:
            if key in answers:
                found[identifier] = answers[key]
    eu = {i: d["act"] for i, d in documents.items() if d["act"]["family"] == "EU"}
    effects = eu_entry_into_force(session, sorted({a["celex"] for a in eu.values()}))
    for identifier, act in sorted(eu.items()):
        language = ec.CELLAR_LANGUAGE.get(act["language"], "ces")
        versions = consolidated(act["celex"], language, session=session)
        if versions is None or act["celex"] not in effects:
            print(f"{identifier}: Cellar did not answer, keeping what was known")
            continue
        found[identifier] = {"first_effective": effects[act["celex"]],
                             "versions": [{"id": c["celex"], "date": c["date"]} for c in versions]}
        time.sleep(0.5)
    return found


_STAMP = re.compile(r"znění\s+(\d{2})\.(\d{2})\.(\d{4})")


def stated_version(content):
    """The day the version shown on a zakonyprolidi.cz page took effect ("znění
    01.11.2026 - 31.12.2026" -> "2026-11-01"), or None."""
    m = _STAMP.search(re.sub(r"<[^>]+>", " ", content))
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None


def verified_fetch(session, record, field, url, out_dir=None, fetch=ff.fetch_one):
    """fetch_fulltext.fetch_one(), and for a Czech version (`zneni_<YYYYMMDD>`) the
    page must state that version: a page showing another one (downloaded a day
    late, or the site not updated yet) is a failure and is not recorded."""
    entry = fetch(session, record, field, url, out_dir)
    if entry.get("status") != "fetched" or not field.startswith(av.CZ_FIELD_PREFIX):
        return entry
    name = pathlib.Path(entry["local_path"]).name
    stored = pathlib.Path(out_dir) / name if out_dir and (pathlib.Path(out_dir) / name).is_file() \
        else ff.REPO_ROOT / entry["local_path"]
    wanted = field[len(av.CZ_FIELD_PREFIX):]
    wanted = f"{wanted[:4]}-{wanted[4:6]}-{wanted[6:]}"
    stated = stated_version(stored.read_text(encoding="utf-8", errors="replace"))
    if stated != wanted:
        return {"status": "failed", "url": url, "http_status": entry.get("http_status"),
                "fetched_at": entry.get("fetched_at"),
                "error": f"the page shows the version of {stated or 'an unknown day'}, not of {wanted}"}
    return entry


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--apply", action="store_true", help="write the cache, download, change the database")
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--today", default=None, help="the day to plan for (ISO date; default today)")
    parser.add_argument("--offline", action="store_true", help="do not ask the sources, use the cache as it is")
    parser.add_argument("--no-fetch", action="store_true", help="do not download the texts")
    parser.add_argument("--only", nargs="+", default=None, metavar="IDENTIFIER", help="only these documents")
    parser.add_argument("--out-dir", default=None, metavar="DIR", help="store downloads in DIR (fetch_fulltext.py)")
    parser.add_argument("--clean-dir", default=None, metavar="DIR", help="store clean texts in DIR")
    parser.add_argument("--backup", action="store_true", help="back the database up before writing to it")
    args = parser.parse_args(argv)
    real_today = datetime.date.today().isoformat()
    today = args.today or real_today
    status = 0

    from dotenv import dotenv_values
    import testdb
    env = dotenv_values(args.env_file or str(testdb.find_env_file(".env")))
    conn = pymysql.connect(host=env["DB_HOST"], port=int(env.get("DB_PORT") or 3306), user=env["DB_USER"],
                           password=env["DB_PASSWORD"], database=env["DB_NAME"], charset="utf8mb4")
    try:
        cur = conn.cursor()
        validity = av.load_validity()
        documents = av.fetch_documents(cur, validity, av.excluded_identifiers())
        if args.only:
            documents = {i: d for i, d in documents.items() if i in set(args.only)}
        cache, manifest = av.load_cache(), ec.load_manifest()
        print(f"{len(documents)} acts: {sum(d['act']['family'] == 'CZ' for d in documents.values())} Czech, "
              f"{sum(d['act']['family'] == 'EU' for d in documents.values())} EU")

        if not args.offline:
            session = requests.Session()
            session.headers["User-Agent"] = cv.USER_AGENT
            found = query_sources(documents, session)
            missing = sorted(set(documents) - set(found))
            if missing:
                status = 1
                print(f"no answer for {len(missing)} acts: {', '.join(missing[:20])}"
                      + (" …" if len(missing) > 20 else ""))
            for identifier, answer in sorted(found.items()):
                doc = documents[identifier]
                since = av.since_of(doc["file_path"], manifest, real_today)
                new = av.record_check(cache, identifier, doc["act"], answer, since, real_today)
                if new:
                    print(f"{identifier}: new versions in the source: {', '.join(new)}")
            if args.apply:
                av.save_cache(cache)

        targets = av.fetch_targets(cache, today)
        if args.only:
            targets = {i: t for i, t in targets.items() if i in set(args.only)}
        records = list(ff.load_targets(consolidations={**targets, **ec.fetch_targets(today=today)}))
        records = [r for r in records if r[0]["znacka"] in targets]
        missing_texts = rec.missing_texts(records, manifest, out_dir=args.out_dir,
                                          prefixes=(av.CZ_FIELD_PREFIX, av.EU_FIELD_PREFIX))
        for _record, _field, url, key in missing_texts:
            print(f"{key}: text of the version in effect not downloaded yet ({url})"
                  + ("" if args.apply and not args.no_fetch else " — would be downloaded"))
        if missing_texts and args.apply and not args.no_fetch:
            if rec.fetch_and_extract(missing_texts, args.out_dir, args.clean_dir, fetch=verified_fetch):
                status = 1
            manifest = ec.load_manifest()

        actions = av.plan(documents, cache, manifest, today)
        for action in actions:
            print(av.describe(action))
        if args.apply and actions:
            if args.backup:
                subprocess.run([sys.executable, str(BASE_DIR / "backup_db.py"), "--reason", "before_act_versions"]
                               + (["--env-file", args.env_file] if args.env_file else []), check=True)
            if ec.ensure_schema(cur):
                print("DocumentVersion.url added")
            av.execute(cur, actions)
            conn.commit()
        print(f"{len(actions)} changes of the versions of legal acts (on {today}) "
              + (f"written to {env['DB_NAME']}" if args.apply else "(dry run — add --apply)"))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return status


if __name__ == "__main__":
    sys.exit(main())
