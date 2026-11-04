import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))
import check_sources as cs
import harvest


def entry(sid, status="ready", url="https://a.test/", endpoint=None, verified="2026-09-20"):
    return {"id": sid, "status": status, "url": url, "access": {"method": "rss", "endpoint": endpoint},
            "verified_at": verified}


def result(url, status, final=None):
    return {"url": url, "status": status, "final_url": final or url, "outcome": cs.outcome(status)}


class OutcomeTestCase(unittest.TestCase):
    def test_status_codes(self):
        self.assertEqual([cs.outcome(s) for s in (200, 401, 403, 429, 404, 410, 400, 405, 500, None)],
                         ["ok", "auth", "blocked", "blocked", "missing", "missing", "reachable", "reachable",
                          "server_error", "unreachable"])

    def test_bot_protection_pages(self):
        self.assertEqual(cs.outcome(200, "<title>Just a moment...</title>"), "blocked")
        self.assertEqual(cs.outcome(200, "<title>Požadavek byl zablokován</title>"), "blocked")
        self.assertEqual(cs.outcome(503, "Briefly unavailable for scheduled maintenance"), "server_error")
        self.assertEqual(cs.outcome(503, "Attention Required! | Cloudflare"), "blocked")


class VerdictTestCase(unittest.TestCase):
    def test_verdicts(self):
        url, feed = "https://a.test/", "https://a.test/feed"
        cases = [
            (entry("a"), [result(url, 200), result(feed, 200)], "ok"),
            (entry("a"), [result(url, 200, "https://b.test/")], "moved"),
            (entry("a"), [result(url, 200, "https://www.a.test/x")], "ok"),
            (entry("a"), [result(url, 404)], "broken"),
            (entry("a"), [result(url, 200), result(feed, 404)], "endpoint_problem"),
            (entry("a"), [result(url, 200), result(feed, 405)], "ok"),
            (entry("a"), [result(url, 403)], "blocked"),
            (entry("a", "blocked"), [result(url, 403)], "as_expected"),
            (entry("a", "blocked"), [result(url, 200)], "ok"),
        ]
        for e, results, expected in cases:
            self.assertEqual(cs.verdict(e, results), expected, results)


class CheckTestCase(unittest.TestCase):
    def test_check_logs_updates_verified_at_and_skips_prohibited_sources(self):
        answers = {"https://ok.test/": 200, "https://gone.test/": 404, "https://cf.test/": 403,
                   "https://live.test/": 200}
        fetched = []

        def fetch(url):
            fetched.append(url)
            return result(url, answers[url])
        entries = [entry("ok", url="https://ok.test/"), entry("gone", url="https://gone.test/"),
                   entry("cf", "blocked", url="https://cf.test/"), entry("live", "automated", url="https://live.test/",
                                                                         verified=None),
                   entry("forbidden", "prohibited", url="https://no.test/")]
        out = []
        with tempfile.TemporaryDirectory() as tmp:
            log = pathlib.Path(tmp) / "log.jsonl"
            verdicts = cs.check(entries, fetch, apply=True, today="2026-10-28", log_path=log, out=out.append)
            records = harvest.read_log(log)
        self.assertEqual(verdicts, {"ok": "ok", "gone": "broken", "cf": "as_expected", "live": "ok",
                                    "forbidden": "skipped"})
        self.assertNotIn("https://no.test/", fetched)
        self.assertEqual([e["verified_at"] for e in entries], ["2026-10-28", "2026-09-20", "2026-10-28", None,
                                                               "2026-09-20"])
        self.assertEqual(len(records), 4)
        self.assertTrue(all(r["kind"] == "availability" for r in records))
        self.assertEqual(len(out), 1)
        self.assertTrue(out[0].startswith("broken"))

    def test_a_dry_run_changes_nothing_in_the_registry(self):
        e = entry("ok", url="https://ok.test/")
        with tempfile.TemporaryDirectory() as tmp:
            cs.check([e], lambda url: result(url, 200), apply=False, today="2026-10-28",
                     log_path=pathlib.Path(tmp) / "log.jsonl", out=lambda line: None)
        self.assertEqual(e["verified_at"], "2026-09-20")


class FetcherTestCase(unittest.TestCase):
    def test_requests_to_one_host_are_spaced(self):
        class Raw:
            def read(self, *args, **kwargs):
                return b"<html>ok</html>"

        class Response:
            status_code, encoding, raw = 200, "utf-8", Raw()

            def __init__(self, url):
                self.url = url

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        class Session:
            headers = {}

            def get(self, url, **kwargs):
                return Response(url)
        clock = [0.0]
        slept = []
        fetch = cs.Fetcher(Session(), delay=1.0, sleep=lambda s: (slept.append(s), clock.__setitem__(0, clock[0] + s)),
                           clock=lambda: clock[0])
        self.assertEqual(fetch("https://a.test/1")["outcome"], "ok")
        fetch("https://a.test/2")
        fetch("https://b.test/1")
        self.assertEqual(slept, [1.0])


if __name__ == "__main__":
    unittest.main()
