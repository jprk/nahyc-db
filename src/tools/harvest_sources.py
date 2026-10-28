"""Runs the adapters of the monitored sources (doc/DATA_SOURCES.md, odstavec 4):
picks sources from data/monitored_sources.json by id, stage or cadence, calls the
adapter of each, writes the findings into the candidate queue (harvest.py,
candidates.upsert_finding) and logs every run in data/source_checks.jsonl, also a
run that found nothing.

Adapters are declared in ADAPTERS (source id → "module:function"); a source
without one is skipped and reported, never handled by guess. An adapter is called
as `function(entry, session, since)` — `entry` the registry record, `session` a
requests.Session, `since` the time of the source's last successful applied run
(or None) — and returns a list of harvest.Finding. One failing source is logged
with its error and the run goes on.

Sources of the stage `manual` are not run: `--checklist` lists them with the date
of their last check, and `--record ID --note TEXT [--found N]` logs the result of a
check done by hand.

Dry run (findings printed, nothing written, the run logged as not applied) unless --apply.

Usage:
  .venv/bin/python src/tools/harvest_sources.py --stage E2 [--apply] [--env-file FILE]
  .venv/bin/python src/tools/harvest_sources.py --cadence weekly [--apply]
  .venv/bin/python src/tools/harvest_sources.py --source veklep-odok [--source ...] [--apply]
  .venv/bin/python src/tools/harvest_sources.py --checklist
  .venv/bin/python src/tools/harvest_sources.py --record imo-imdg --note "bez změny" [--found 0]
"""
import argparse
import collections
import importlib
import sys

import requests

import harvest
import source_registry

# Source id → "module:function" of its adapter. Filled from stage E1 on.
ADAPTERS = {}


def resolve(spec):
    module, function = spec.split(":")
    return getattr(importlib.import_module(module), function)


def plan(entries, adapters):
    """[(entry, adapter spec or None, reason it is skipped or None)] in registry order."""
    planned = []
    for entry in entries:
        if not entry["signal"]:
            planned.append((entry, None, f"not harvested ({entry['status']})"))
        elif entry["stage"] == "manual":
            planned.append((entry, None, "checked by hand (--checklist)"))
        elif set(entry["signal"]) <= {"lookup", "context"}:
            planned.append((entry, None, "looked up on demand, not run"))
        elif entry["id"] not in adapters:
            planned.append((entry, None, "no adapter yet"))
        else:
            planned.append((entry, adapters[entry["id"]], None))
    return planned


def run_source(entry, adapter, *, session, since, apply, connection=None, log_path=None, out=print):
    """Runs one source; returns the logged record."""
    record = {"kind": "harvest", "source": entry["id"], "applied": apply, "since": since, "adapter": adapter}
    try:
        findings = resolve(adapter)(entry, session, since)
        record["findings"] = len(findings)
        record["by_signal"] = dict(collections.Counter(f.signal for f in findings))
        if apply:
            with connection.cursor() as cursor:
                outcome = harvest.write_findings(cursor, findings, harvest.known_keys(cursor), harvest.now())
            connection.commit()
            record["outcome"] = dict(outcome)
        else:
            for finding in findings[:20]:
                out(f"    {finding.signal:12} {finding.candidate_key():28} {(finding.title or '')[:80]}")
            if len(findings) > 20:
                out(f"    … and {len(findings) - 20} more")
    except Exception as error:  # one source must not stop the others
        if apply and connection is not None:
            connection.rollback()
        record["error"] = f"{type(error).__name__}: {error}"
    return harvest.log_run(record, log_path)


def run(entries, adapters, *, apply, connection=None, log_path=None, session=None, out=print):
    """Runs the planned sources; returns the logged records."""
    session = session or requests.Session()
    session.headers.setdefault("User-Agent", harvest.USER_AGENT)
    last = harvest.last_runs(harvest.read_log(log_path))
    records, skipped = [], collections.Counter()
    for entry, adapter, reason in plan(entries, adapters):
        if reason:
            skipped[reason] += 1
            continue
        since = last.get(entry["id"], {}).get("at")
        out(f"{entry['id']} ({adapter}, since {since or 'the beginning'})")
        record = run_source(entry, adapter, session=session, since=since, apply=apply, connection=connection,
                            log_path=log_path, out=out)
        out(f"  → {record.get('error') or record.get('outcome') or str(record.get('findings')) + ' findings'}")
        records.append(record)
    for reason, count in sorted(skipped.items()):
        out(f"skipped {count}: {reason}")
    return records


def checklist(entries, log_path=None, out=print):
    """The sources of the stage `manual` with the date of their last check."""
    last = harvest.last_runs(harvest.read_log(log_path), kind="manual", successful=False)
    rows = [(last.get(e["id"], {}).get("at", "—")[:10], e) for e in entries if e["stage"] == "manual"]
    for checked, entry in sorted(rows, key=lambda r: (r[0] != "—", r[0])):
        out(f"{checked:10}  {entry['priority'] or '-'}  {entry['id']:32} {entry['url']}")
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    what = parser.add_mutually_exclusive_group(required=True)
    what.add_argument("--source", action="append", help="source id (repeatable)")
    what.add_argument("--stage", choices=source_registry.STAGES[:-1])
    what.add_argument("--cadence", choices=source_registry.CADENCES)
    what.add_argument("--checklist", action="store_true", help="list the sources checked by hand")
    what.add_argument("--record", metavar="ID", help="log a check done by hand")
    parser.add_argument("--note", help="with --record: what the check found")
    parser.add_argument("--found", type=int, default=0, help="with --record: number of new documents")
    parser.add_argument("--apply", action="store_true", help="write findings to the database (dry run without it)")
    parser.add_argument("--env-file", default=None)
    args = parser.parse_args(argv)
    entries, _ = source_registry.load()
    if args.checklist:
        checklist(entries)
        return 0
    if args.record:
        entry = source_registry.select(entries, [args.record])[0]
        if not args.note:
            parser.error("--record needs --note")
        harvest.log_run({"kind": "manual", "source": entry["id"], "applied": True, "findings": args.found,
                         "note": args.note})
        print(f"{entry['id']}: logged")
        return 0
    try:
        selected = source_registry.select(entries, args.source or (), args.stage, args.cadence)
    except KeyError as error:
        parser.error(f"unknown source: {error}")
    connection = None
    if args.apply:
        import candidates as cd
        connection, database = harvest.connect(args.env_file)
        with connection.cursor() as cursor:
            cd.ensure_schema(cursor)
        connection.commit()
        print(f"writing to {database}")
    try:
        records = run(selected, ADAPTERS, apply=args.apply, connection=connection)
    finally:
        if connection is not None:
            connection.close()
    if not args.apply and records:
        print("(dry run — add --apply to write the findings)")
    return 1 if any(r.get("error") for r in records) else 0


if __name__ == "__main__":
    sys.exit(main())
