import pathlib
import sys
import tempfile
import types
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import harvest
import harvest_sources as hs
import source_registry as sr

CALLS = []


def fake_adapter(entry, session, since, context):
    CALLS.append((entry["id"], since))
    return [harvest.Finding(entry["id"], "draft", "Návrh zákona o vodíku", native_id="1"),
            harvest.Finding(entry["id"], "new_document", "Vyhláška", key="CZ:9/2099")]


def failing_adapter(entry, session, since, context):
    raise RuntimeError("source down")


sys.modules["fake_adapters"] = types.SimpleNamespace(ok=fake_adapter, fail=failing_adapter)


class FakeConnection:
    def __init__(self, cursor):
        self._cursor, self.commits, self.rollbacks = cursor, 0, 0

    def cursor(self):
        connection = self

        class Context:
            def __enter__(self):
                return connection._cursor

            def __exit__(self, *exc):
                return False
        return Context()

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class RunnerTestCase(unittest.TestCase):
    def setUp(self):
        CALLS.clear()
        self.entries, _ = sr.load()
        self.tmp = tempfile.TemporaryDirectory()
        self.log = pathlib.Path(self.tmp.name) / "log.jsonl"
        self.out = []

    def tearDown(self):
        self.tmp.cleanup()

    def test_the_plan_skips_sources_without_adapters_manual_and_prohibited_ones(self):
        planned = {e["id"]: reason for e, _, reason in hs.plan(self.entries, {"veklep-odok": "fake_adapters:ok"})}
        self.assertIsNone(planned["veklep-odok"])
        self.assertEqual(planned["ep-oeil"], "no adapter yet")
        self.assertIn("by hand", planned["imo-imdg"])
        self.assertIn("not harvested", planned["iso-tc197"])
        self.assertIn("on demand", planned["sbirka-pp-usc"])

    def test_with_no_adapters_nothing_runs_and_the_skips_are_reported(self):
        records = hs.run(sr.select(self.entries, stage="E2"), {}, apply=False, log_path=self.log, out=self.out.append)
        self.assertEqual(records, [])
        self.assertIn("skipped 5: no adapter yet", self.out)

    def test_a_dry_run_prints_and_logs_without_touching_the_database(self):
        entries = sr.select(self.entries, ["veklep-odok"])
        records = hs.run(entries, {"veklep-odok": "fake_adapters:ok"}, apply=False, log_path=self.log,
                         out=self.out.append)
        self.assertEqual((records[0]["findings"], records[0]["applied"]), (2, False))
        self.assertEqual(records[0]["by_signal"], {"draft": 1, "new_document": 1})
        self.assertTrue(any("veklep-odok:1" in line for line in self.out))
        self.assertEqual(len(harvest.read_log(self.log)), 1)

    def test_an_applied_run_writes_commits_and_the_next_run_continues_from_it(self):
        from test_harvest import Cursor
        connection = FakeConnection(Cursor())
        entries = sr.select(self.entries, ["veklep-odok"])
        adapters = {"veklep-odok": "fake_adapters:ok"}
        first = hs.run(entries, adapters, apply=True, connection=connection, log_path=self.log, out=self.out.append)
        self.assertEqual(first[0]["outcome"], {"inserted": 2})
        self.assertEqual(connection.commits, 1)
        hs.run(entries, adapters, apply=True, connection=connection, log_path=self.log, out=self.out.append)
        self.assertIsNone(CALLS[0][1])
        self.assertEqual(CALLS[1][1], first[0]["at"])

    def test_a_failing_source_is_logged_and_the_others_still_run(self):
        entries = sr.select(self.entries, ["veklep-odok", "ep-oeil"])
        records = hs.run(entries, {"veklep-odok": "fake_adapters:fail", "ep-oeil": "fake_adapters:ok"}, apply=False,
                         log_path=self.log, out=self.out.append)
        self.assertEqual(records[0]["error"], "RuntimeError: source down")
        self.assertEqual(records[1]["findings"], 2)
        self.assertEqual(hs.main.__module__, "harvest_sources")

    def test_the_checklist_lists_manual_sources_unchecked_first(self):
        harvest.log_run({"kind": "manual", "source": "imo-imdg", "applied": True, "note": "ok"}, self.log)
        rows = hs.checklist(self.entries, log_path=self.log, out=self.out.append)
        self.assertEqual(len(rows), sum(1 for e in self.entries if e["stage"] == "manual"))
        self.assertTrue(self.out[-1].split()[-2] == "imo-imdg" or "imo-imdg" in self.out[-1])
        self.assertTrue(self.out[0].startswith("—"))


if __name__ == "__main__":
    unittest.main()
