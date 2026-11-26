"""Thematic golden set RFNBO (data/golden/rfnbo.json, doc/RFNBO_POKRYTI.md odstavec 4.1)
against the TEST database (`.env.test`, `h2regdocs_test`), never the real one.

Every item of priority A must be a document of the database (its identifier) or a
candidate in the queue that is still open (new / proposed / deferred); an item of
priority B missing from both only warns. The candidates of
data/rfnbo_candidates.json are first put into the queue (import_listed_candidates,
as `import_listed_candidates.py --apply`) so that the test also passes on a copy of
a database the import has not run on yet; what it inserted is removed at the end."""
import json
import os
import pathlib
import sys
import unittest
import warnings

from dotenv import dotenv_values

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "tools"))
import import_listed_candidates as ilc  # noqa: E402
import testdb  # noqa: E402

GOLDEN = REPO_ROOT / "data" / "golden" / "rfnbo.json"
PENDING = REPO_ROOT / "data" / "rfnbo_candidates.json"
OPEN = ("new", "proposed", "deferred")


class GoldenRfnboFileTestCase(unittest.TestCase):
    def test_file_is_consistent(self):
        items = json.loads(GOLDEN.read_text(encoding="utf-8"))["items"]
        self.assertGreaterEqual(len(items), 20)
        for item in items:
            self.assertIn(item["priority"], ("A", "B"), item["name"])
            self.assertTrue(item["identifiers"] or item["candidate_keys"], item["name"])
        _, pending = ilc.load(PENDING)
        keys = {k for item in items for k in item["candidate_keys"]}
        self.assertLessEqual({c["candidate_key"] for c in pending}, keys,
                             "a candidate of the audit is missing from the golden set")


class GoldenRfnboDatabaseTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            env_path = testdb.find_env_file(".env.test")
        except testdb.TestDbError:
            raise unittest.SkipTest(".env.test not found — no rehearsal database configured")
        env = {**dotenv_values(env_path), **{k: v for k, v in os.environ.items() if k.startswith("DB_")}}
        if env.get("DB_NAME") != "h2regdocs_test":
            raise unittest.SkipTest("the test database is not h2regdocs_test — refusing to guess")
        env["DB_PORT"] = str(env.get("DB_PORT") or 3306)
        cls.conn = testdb.connect(env, autocommit=False)
        source, pending = ilc.load(PENDING)
        with cls.conn.cursor() as cur:
            planned = ilc.plan(cur, source, pending)
            ilc.execute(cur, source, planned)
        cls.conn.commit()
        cls.inserted = [c["candidate_key"] for c, outcome in planned if outcome == "insert"]
        cls.source = source
        with cls.conn.cursor() as cur:
            cur.execute("SELECT identifier FROM Document WHERE identifier IS NOT NULL")
            cls.identifiers = {r[0] for r in cur.fetchall()}
            cur.execute("SELECT candidate_key, status FROM DocumentCandidate WHERE candidate_key IS NOT NULL")
            cls.queue = dict(cur.fetchall())
        cls.items = json.loads(GOLDEN.read_text(encoding="utf-8"))["items"]

    @classmethod
    def tearDownClass(cls):
        with cls.conn.cursor() as cur:
            for key in cls.inserted:
                cur.execute("DELETE FROM DocumentCandidate WHERE candidate_key = %s AND source = %s", (key, cls.source))
        cls.conn.commit()
        cls.conn.close()

    def covered(self, item):
        if any(i in self.identifiers for i in item["identifiers"]):
            return True
        return any(self.queue.get(k) in OPEN for k in item["candidate_keys"])

    def test_priority_a_in_database_or_queue(self):
        missing = [item["name"] for item in self.items if item["priority"] == "A" and not self.covered(item)]
        self.assertEqual(missing, [], "RFNBO items of priority A neither in the database nor in the queue")

    def test_priority_b_warns(self):
        missing = [item["name"] for item in self.items if item["priority"] == "B" and not self.covered(item)]
        if missing:
            warnings.warn("RFNBO items of priority B missing: " + "; ".join(missing))

    def test_second_import_changes_nothing(self):
        source, pending = ilc.load(PENDING)
        with self.conn.cursor() as cur:
            self.assertEqual([o for _, o in ilc.plan(cur, source, pending) if o == "insert"], [])
