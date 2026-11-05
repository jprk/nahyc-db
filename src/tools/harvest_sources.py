"""Runs the adapters of the monitored sources (doc/DATA_SOURCES.md, odstavec 4):
picks sources from data/monitored_sources.json by id, stage or cadence, calls the
adapters of each, writes the findings into the candidate queue (harvest.py,
candidates.upsert_finding) or, for state changes, into the cache of their check,
and logs every run of an adapter in data/source_checks.jsonl, also a run that
found nothing.

Adapters are declared in ADAPTERS (source id → "module:function" specs, one per
kind of finding); sources whose adapter is deliberately not run are declared in
DEFERRED with the reason. A source in neither is skipped as "no adapter yet" and
reported, never handled by guess. An adapter is called as
`function(entry, session, since, context)` — `entry` the registry record, `session`
a requests.Session, `since` the time of the adapter's last successful applied run
(or None), `context` {"documents": [(id, identifier, title, url)] of the database,
"known": harvest.known_keys(), "today": ISO date} — and returns a list of
harvest.Finding. One failing adapter is logged with its error and the run goes on.

Sources of the stage `manual` are not run: `--checklist` lists them with the date
of their last check, and `--record ID --note TEXT [--found N]` logs the result of a
check done by hand.

Dry run unless --apply: the database is only read (to know what it has), the
findings are printed and nothing is written but the log entry (marked not applied).

Usage:
  .venv/bin/python src/tools/harvest_sources.py --stage E1 [--apply] [--env-file FILE]
  .venv/bin/python src/tools/harvest_sources.py --cadence weekly [--apply]
  .venv/bin/python src/tools/harvest_sources.py --source eurlex-cellar [--source ...] [--apply]
  .venv/bin/python src/tools/harvest_sources.py --source normoff-stn --limit 5      # trial run
  .venv/bin/python src/tools/harvest_sources.py --checklist
  .venv/bin/python src/tools/harvest_sources.py --record imo-imdg --note "bez změny" [--found 0]
  .venv/bin/python src/tools/harvest_sources.py --lookup is-eia "vodík"     # a lookup on demand, prints only
"""
import argparse
import collections
import datetime
import importlib
import sys

import requests

import harvest
import source_registry

# Source id → adapters (harvest_adapters.py, E1; harvest_drafts.py, E2; harvest_standards.py, E3; harvest_feeds.py, E4;
# harvest_pages.py, E5; harvest_eu_registers.py, E6).
ADAPTERS = {
    "eurlex-cellar": ("harvest_adapters:eurlex_new", "harvest_adapters:validity_eu"),
    "esbirka-lod": ("harvest_adapters:esbirka_new", "harvest_adapters:validity_cz"),
    "csn-online": ("harvest_adapters:csn_state",),
    "normoff-stn": ("harvest_adapters:normoff_state",),
    "hytep": ("harvest_adapters:hytep_new",),
    # stage E2 (harvest_drafts.py)
    "veklep-odok": ("harvest_drafts:veklep_rss",),
    "psp-snemovni-tisky": ("harvest_drafts:psp_bills",),
    "senat-tisky": ("harvest_drafts:senate_bills",),
    "ep-oeil": ("harvest_drafts:oeil_procedures",),
    # stage E3 (harvest_standards.py)
    "vestnik-unmz": ("harvest_standards:vestnik_unmz",),
    "unmz-news": ("harvest_standards:rss_items",),
    "ec-harmonised-standards": ("harvest_standards:harmonised_standards",),
    "cps-tpg": ("harvest_standards:cps_tpg",),
    "sae-standards": ("harvest_standards:sae_crossref",),
    # stage E4 (harvest_feeds.py; plain feeds by harvest_standards.rss_items)
    "acer": ("harvest_standards:rss_items",),
    "mpo-cz": ("harvest_standards:rss_items",),
    "eru-cz": ("harvest_standards:rss_items",),
    "mmr-stavebni-pravo": ("harvest_standards:rss_items",),
    "mzp-cz": ("harvest_standards:rss_items",),
    "cizp": ("harvest_standards:rss_items",),
    "coi": ("harvest_standards:rss_items",),
    "era-railways": ("harvest_standards:rss_items",),
    "suip": ("harvest_feeds:rss_items_broader",),
    "otif-rid": ("harvest_feeds:rss_items_broader",),
    "du-rid": ("harvest_feeds:rss_items_broader", "harvest_feeds:du_rid_page"),
    "ehsp": ("harvest_feeds:ehsp_documents",),
    # stage E5 (harvest_pages.py; lookups on demand in harvest_lookups.py)
    "ticr": ("harvest_pages:ticr_news",),
    "hzs-cr": ("harvest_pages:hzs_news",),
    "cmi-oop": ("harvest_pages:cmi_oop",),
    "md-adr": ("harvest_pages:md_adr_pages",),
    "ec-have-your-say": ("harvest_pages:hys_initiatives",),
    # stage E6 (harvest_eu_registers.py)
    "ec-comitology-register": ("harvest_eu_registers:comitology_documents",),
    "ec-regdel": ("harvest_eu_registers:delegated_acts",),
    "ec-documents-register": ("harvest_eu_registers:commission_documents",),
}
# Sources of the plan whose existing script is deliberately not run by the runner.
DEFERRED = {
    "zakonyprolidi": "covered by esbirka-lod (validity_cz reads the repealing act there)",
    "slovlex-linkcheck": "answers the identified robot with HTTP 403 since 2026-10-28",
    "iec-catalogue": "harvest_iec_publications.py passes AWS WAF Bot Control with a headless browser — decision pending",
    "eiga-publications": "src/sites/eiga.py gets past the site's WAF with a tailored query — decision pending",
    "dvgw-publications": "harvest_dvgw_publications.py presents itself as a desktop browser — decision pending",
    "slovlex-legislativny-proces": "answers the identified robot with HTTP 403 since 2026-10-28",
    "astm-d03": "answers the identified robot with HTTP 403 since 2026-10-28",
    "asme-codes": "the standards pages are a shop without a machine-readable list — checked by hand",
    "vestnik-unms-sr": "an index of PDFs without a stable naming pattern, priority C — not implemented",
    "nfpa-2": "a page rendered only in a browser, robots.txt forbids /en/ — checked by hand",
    "e-legislativa": "the official REST API needs a key from the Ministry of the Interior (registration pending)",
}


def resolve(spec):
    module, function = spec.split(":")
    return getattr(importlib.import_module(module), function)


def plan(entries, adapters, deferred=None):
    """[(entry, adapter specs or (), reason it is skipped or None)] in registry order."""
    deferred = DEFERRED if deferred is None else deferred
    planned = []
    for entry in entries:
        if not entry["signal"]:
            planned.append((entry, (), f"not harvested ({entry['status']})"))
        elif entry["stage"] == "manual":
            planned.append((entry, (), "checked by hand (--checklist)"))
        elif set(entry["signal"]) <= {"lookup", "context"}:
            planned.append((entry, (), "looked up on demand, not run"))
        elif entry["id"] in adapters:
            specs = adapters[entry["id"]]
            planned.append((entry, (specs,) if isinstance(specs, str) else tuple(specs), None))
        elif entry["id"] in deferred:
            planned.append((entry, (), f"deferred: {entry['id']} — {deferred[entry['id']]}"))
        else:
            planned.append((entry, (), "no adapter yet"))
    return planned


def is_known(finding, known):
    return bool((finding.key and finding.key in known) or (finding.url and "url:" + finding.url.strip() in known))


def run_adapter(entry, adapter, *, session, since, context, apply, connection=None, log_path=None, out=print,
                validity_path=None, norm_path=None, not_imported_path=None):
    """Runs one adapter of a source; returns the logged record."""
    record = {"kind": "harvest", "source": entry["id"], "applied": apply, "since": since, "adapter": adapter,
              "database": context.get("database")}
    try:
        findings = resolve(adapter)(entry, session, since, context)
        record["findings"] = len(findings)
        record["by_signal"] = dict(collections.Counter(f.signal for f in findings))
        if apply:
            outcome = collections.Counter()
            queued = [f for f in findings if f.signal not in ("state_change", "excluded")]
            if queued:
                with connection.cursor() as cursor:
                    outcome.update(harvest.write_findings(cursor, queued, context["known"], harvest.now()))
                connection.commit()
            outcome.update(harvest.apply_state_changes(findings, context["today"], validity_path, norm_path))
            excluded = harvest.record_excluded(findings, harvest.now(), not_imported_path)
            if excluded:
                outcome["excluded"] = excluded
            record["outcome"] = dict(outcome)
        else:
            new = [f for f in findings if f.signal == "state_change" or not is_known(f, context["known"])]
            record["not_known"] = len(new)
            record["by_tier"] = dict(collections.Counter(str(f.tier) for f in new if f.signal != "excluded"))
            for finding in new[:20]:
                tier = f"[{finding.tier}]" if finding.tier else "   "
                out(f"    {finding.signal:12} {tier} {finding.candidate_key():24} {(finding.title or '')[:70]}"
                    + (f" [{finding.state.get('status')}]" if finding.state else "")
                    + (f" — {finding.extra['reason']}" if finding.signal == "excluded" else ""))
            if len(new) > 20:
                out(f"    … and {len(new) - 20} more")
    except Exception as error:  # one adapter must not stop the others
        if apply and connection is not None:
            connection.rollback()
        record["error"] = f"{type(error).__name__}: {error}"
    return harvest.log_run(record, log_path)


def last_run_of(records, source, adapter, database=None):
    """The time of the last successful applied run of `adapter` of `source` into `database`."""
    times = [r["at"] for r in records if r.get("kind") == "harvest" and r.get("source") == source
             and r.get("adapter") == adapter and r.get("applied") and not r.get("error")
             and r.get("database") == database]
    return max(times) if times else None


def candidate_titles(cursor):
    """{candidate key: title} of the candidate queue ({} before the table exists)."""
    try:
        cursor.execute("SELECT candidate_key, title FROM DocumentCandidate WHERE candidate_key IS NOT NULL")
    except Exception:  # the table appears with the first applied run
        return {}
    return {r["candidate_key"]: r["title"] for r in cursor.fetchall() if r["title"]}


def build_context(connection, today=None, database=None):
    docs, titles = [], {}
    if connection is not None:
        with connection.cursor() as cursor:
            docs = harvest.documents(cursor)
            titles = candidate_titles(cursor)
    return {"documents": docs, "known": harvest.known_keys(docs), "database": database,
            "candidate_titles": titles, "today": today or datetime.date.today().isoformat()}


def run(entries, adapters, *, apply, connection=None, log_path=None, session=None, out=print, context=None,
        deferred=None, validity_path=None, norm_path=None, not_imported_path=None):
    """Runs the planned sources; returns the logged records."""
    session = session or requests.Session()
    session.headers.setdefault("User-Agent", harvest.USER_AGENT)
    records_so_far = harvest.read_log(log_path)
    planned = plan(entries, adapters, deferred)
    if context is None and any(specs for _e, specs, _r in planned):
        context = build_context(connection)
    records, skipped = [], collections.Counter()
    for entry, specs, reason in planned:
        if reason:
            skipped[reason] += 1
            continue
        for adapter in specs:
            since = last_run_of(records_so_far, entry["id"], adapter, context.get("database"))
            out(f"{entry['id']} ({adapter}, since {since or 'the beginning'})")
            record = run_adapter(entry, adapter, session=session, since=since, context=context, apply=apply,
                                 connection=connection, log_path=log_path, out=out, validity_path=validity_path,
                                 norm_path=norm_path, not_imported_path=not_imported_path)
            out(f"  → {record.get('error') or record.get('outcome') or str(record.get('findings')) + ' findings'}")
            records.append(record)
    for reason, count in sorted(skipped.items()):
        out(f"skipped {count}: {reason}" if not reason.startswith("deferred") else f"skipped: {reason}")
    return records


def checklist(entries, log_path=None, out=print):
    """The sources of the stage `manual` with the date of their last check."""
    last = harvest.last_runs(harvest.read_log(log_path), kind="manual", successful=False)
    rows = [(last.get(e["id"], {}).get("at", "—")[:10], e) for e in entries if e["stage"] == "manual"]
    for checked, entry in sorted(rows, key=lambda r: (r[0] != "—", r[0])):
        out(f"{checked:10}  {entry['priority'] or '-'}  {entry['id']:32} {entry['url']}")
    return rows


def lookup(source, query, session=None, out=print):
    """Prints what a lookup on demand finds (harvest_lookups.LOOKUPS)."""
    import harvest_lookups
    if source not in harvest_lookups.LOOKUPS:
        out(f"no lookup for {source}; available: {', '.join(sorted(harvest_lookups.LOOKUPS))}")
        return 2
    session = session or requests.Session()
    session.headers.setdefault("User-Agent", harvest.USER_AGENT)
    results = harvest_lookups.LOOKUPS[source](session, query)
    for item in results:
        out(f"- {item['title']}" + (f" — {item['detail']}" if item.get("detail") else "") + (f"\n  {item['url']}" if item.get("url") else ""))
    out(f"{len(results)} results from {source} for {query!r}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    what = parser.add_mutually_exclusive_group(required=True)
    what.add_argument("--source", action="append", help="source id (repeatable)")
    what.add_argument("--stage", choices=source_registry.STAGES[:-1])
    what.add_argument("--cadence", choices=source_registry.CADENCES)
    what.add_argument("--checklist", action="store_true", help="list the sources checked by hand")
    what.add_argument("--record", metavar="ID", help="log a check done by hand")
    what.add_argument("--lookup", nargs=2, metavar=("ID", "QUERY"),
                      help="search a source looked up on demand (harvest_lookups.py); prints, writes nothing")
    parser.add_argument("--note", help="with --record: what the check found")
    parser.add_argument("--found", type=int, default=0, help="with --record: number of new documents")
    parser.add_argument("--limit", type=int, default=None,
                        help="a trial run: checking adapters look up at most N documents")
    parser.add_argument("--apply", action="store_true", help="write findings to the database (dry run without it)")
    parser.add_argument("--env-file", default=None)
    args = parser.parse_args(argv)
    entries, _ = source_registry.load()
    if args.checklist:
        checklist(entries)
        return 0
    if args.lookup:
        return lookup(*args.lookup)
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
    connection, database = harvest.connect(args.env_file)
    if args.apply:
        import candidates as cd
        with connection.cursor() as cursor:
            cd.ensure_schema(cursor)
        connection.commit()
        print(f"writing to {database}")
    else:
        print(f"reading {database} (dry run)")
    try:
        context = build_context(connection, database=database)
        context["limit"] = args.limit
        records = run(selected, ADAPTERS, apply=args.apply, connection=connection, context=context)
    finally:
        if connection is not None:
            connection.close()
    if not args.apply and records:
        print("(dry run — add --apply to write the findings)")
    return 1 if any(r.get("error") for r in records) else 0


if __name__ == "__main__":
    sys.exit(main())
