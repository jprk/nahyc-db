"""Checks that the addresses of the monitored sources still answer
(doc/DATA_SOURCES.md, odstavec 4.3, stage E0): the entry address of every source in
data/monitored_sources.json and the endpoint and feed of its access.

Every address gets an outcome: `ok` (2xx), `auth` (401), `blocked` (403/429, or a
bot-protection page), `missing` (404/410), `reachable` (another 4xx — an API
answering a request without parameters), `server_error` (5xx) or `unreachable`
(no answer). A source gets a verdict: `ok`, `as_expected` (a source registered as
`blocked` still is), `blocked` (a source not registered as blocked now is),
`moved` (the entry address redirects to another host),
`endpoint_problem`, `broken` or `skipped` (prohibited sources are not fetched —
their robots.txt forbids it; address templates are not checked).

Every source checked is logged in data/source_checks.jsonl (kind `availability`).
With --apply, `verified_at` of a source whose verdict is `ok` or `as_expected` is
set to today; a source with `verified_at: null` (in use by the pipeline, verified
by running) keeps it. Nothing else in the registry changes: a moved or broken
address is reported for a person to correct.

Usage: .venv/bin/python src/tools/check_sources.py [--source ID ...] [--apply]
"""
import argparse
import collections
import datetime
import sys
import time
import urllib.parse

import requests

import harvest
import source_registry

TIMEOUT = 20
HOST_DELAY = 1.0
CHALLENGE_MARKERS = ("just a moment", "cf-chl", "attention required", "access denied", "request unsuccessful",
                     "bot protection", "captcha")


def outcome(status, body=""):
    if status is None:
        return "unreachable"
    if 200 <= status < 300:
        lowered = (body or "")[:4000].lower()
        return "blocked" if "cf-chl" in lowered or "just a moment..." in lowered else "ok"
    if status == 401:
        return "auth"
    if status in (403, 429) or (status == 503 and any(m in (body or "").lower() for m in CHALLENGE_MARKERS)):
        return "blocked"
    if status in (404, 410):
        return "missing"
    if status >= 500:
        return "server_error"
    return "reachable"


class Fetcher:
    """GETs an address (streaming, at most 64 kB read), keeping a delay per host."""

    def __init__(self, session=None, delay=HOST_DELAY, sleep=time.sleep, clock=time.monotonic):
        self.session = session or requests.Session()
        self.session.headers.setdefault("User-Agent", harvest.USER_AGENT)
        self.delay, self.sleep, self.clock, self.last = delay, sleep, clock, {}

    def __call__(self, url):
        host = urllib.parse.urlsplit(url).hostname
        wait = self.last.get(host, -1e9) + self.delay - self.clock()
        if wait > 0:
            self.sleep(wait)
        try:
            with self.session.get(url, timeout=TIMEOUT, stream=True, allow_redirects=True) as response:
                body = response.raw.read(65536, decode_content=True).decode(response.encoding or "utf-8", "replace")
                result = {"url": url, "status": response.status_code, "final_url": response.url,
                          "outcome": outcome(response.status_code, body)}
        except requests.RequestException as error:
            result = {"url": url, "status": None, "final_url": None, "outcome": "unreachable",
                      "error": f"{type(error).__name__}: {str(error)[:200]}"}
        finally:
            self.last[host] = self.clock()
        return result


def verdict(entry, results):
    main, endpoints = results[0], results[1:]
    if entry["status"] == "blocked" and main["outcome"] in ("blocked", "auth"):
        return "as_expected"
    if main["outcome"] in ("missing", "unreachable", "server_error"):
        return "broken"
    if main["outcome"] in ("blocked", "auth"):
        return "blocked" if entry["status"] != "blocked" else "as_expected"
    if any(r["outcome"] in ("missing", "unreachable", "server_error") for r in endpoints):
        return "endpoint_problem"
    if main.get("final_url") and _host(main["final_url"]) != _host(main["url"]):
        return "moved"
    return "ok"


def _host(url):
    host = urllib.parse.urlsplit(url).hostname or ""
    return host[4:] if host.startswith("www.") else host


def check(entries, fetch, *, apply, today=None, log_path=None, out=print):
    """Checks the entries; returns {source id: verdict} and updates `verified_at` in
    `entries` in place when applying."""
    today = today or datetime.date.today().isoformat()
    verdicts = {}
    for entry in entries:
        if entry["status"] == "prohibited":
            verdicts[entry["id"]] = "skipped"
            continue
        results = [fetch(url) for url in source_registry.urls(entry)]
        result = verdict(entry, results)
        verdicts[entry["id"]] = result
        if apply and result in ("ok", "as_expected") and entry["verified_at"] is not None:
            entry["verified_at"] = today
        harvest.log_run({"kind": "availability", "source": entry["id"], "applied": apply, "verdict": result,
                         "results": results}, log_path)
        if result not in ("ok", "as_expected"):
            details = "; ".join(f"{r['outcome']} {r['status'] or ''} {r['url']}"
                                + (f" → {r['final_url']}" if r.get("final_url") not in (None, r["url"]) else "")
                                for r in results)
            out(f"{result:16} {entry['id']:32} {details}")
    return verdicts


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--source", action="append", help="source id (repeatable); all sources without it")
    parser.add_argument("--apply", action="store_true", help="update verified_at in the registry")
    args = parser.parse_args(argv)
    entries, groups = source_registry.load()
    try:
        selected = source_registry.select(entries, args.source or ())
    except KeyError as error:
        parser.error(f"unknown source: {error}")
    verdicts = check(selected, Fetcher(), apply=args.apply)
    counts = collections.Counter(verdicts.values())
    print(", ".join(f"{n} {v}" for v, n in counts.most_common()))
    if args.apply:
        source_registry.save(entries, groups)
        print("verified_at updated in", source_registry.REGISTRY_PATH)
    return 1 if counts["broken"] or counts["endpoint_problem"] else 0


if __name__ == "__main__":
    sys.exit(main())
