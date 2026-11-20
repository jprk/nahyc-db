"""Golden set from the tables of MPO and CDV (30 April 2026, doc/MPO_TABULKY.md)
against the TEST database (`.env.test`, `h2regdocs_test`), never the real one.

Every row of both tables must be (a) a document of the database, (b) a candidate
in the queue (DocumentCandidate, or a document an accepted candidate became), or
(c) have a stated reason in data/20260430_MPO/mpo_decisions.json why it is
neither. The status each row should have is committed in
data/20260430_MPO/mpo_coverage.json; a row recorded as a document that is no
longer found means a document was lost.

The test first puts the candidates of data/20260430_MPO/mpo_candidates.json into
the queue (mpo_tables.write_candidates, the same as `mpo_tables.py import
--apply`, no network), so that it also passes on a copy of a database the import
has not run on yet; what it added or changed is undone again at the end. A second
import must change nothing (the import is idempotent), and the amendments in the
queue carry the ids of the documents they amend (AMENDS on acceptance)."""
import json
import os
import pathlib
import sys
import unittest

from dotenv import dotenv_values

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "tools"))
import candidates as cd  # noqa: E402
import testdb  # noqa: E402
import mpo_tables as mt  # noqa: E402


class MpoGoldenSetTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            env_path = testdb.find_env_file(".env.test")
        except testdb.TestDbError:
            raise unittest.SkipTest(".env.test not found — no rehearsal database configured")
        env = {**dotenv_values(env_path), **{k: v for k, v in os.environ.items() if k.startswith("DB_")}}
        if env.get("DB_NAME") != "h2regdocs_test":
            raise unittest.SkipTest("the test database is not h2regdocs_test — refusing to guess")
        import pymysql
        env["DB_PORT"] = str(env.get("DB_PORT") or 3306)
        cls.conn = testdb.connect(env, cursorclass=pymysql.cursors.DictCursor, autocommit=False)
        found = mt.load_candidates()
        with cls.conn.cursor() as cur:
            cd.ensure_schema(cur)  # a copy of a database without the columns of the MPO import gets them
            cur.execute("SELECT id, candidate_key, evidence_json, puvodce, validity_status, `signal` "
                        "FROM DocumentCandidate")
            before = {r["candidate_key"]: r for r in cur.fetchall()}
            snapshot = mt.load_snapshot(cur)
            planned = [c for c in found if not snapshot.documents_for_key(c["candidate_key"], c["designation"])]
            cls.outcome = mt.write_candidates(cur, planned)
        cls.conn.commit()
        cls.planned = planned
        cls.before = before
        with cls.conn.cursor() as cur:
            cls.snapshot = mt.load_snapshot(cur)
        cls.coverage = json.loads(mt.COVERAGE_PATH.read_text(encoding="utf-8"))["rows"]
        cls.decisions = mt.load_decisions()
        cls.rows = {r["id"]: r for r in mt.load_rows()}
        cls.designations = {c["candidate_key"]: c["designation"] for c in found}

    @classmethod
    def tearDownClass(cls):
        with cls.conn.cursor() as cur:
            for key, outcome in cls.outcome.items():
                if outcome == "inserted":
                    cur.execute("DELETE FROM DocumentCandidate WHERE candidate_key = %s AND source = %s",
                                (key, mt.SOURCE))
                elif outcome in ("evidence", "refreshed"):
                    old = cls.before[key]
                    cur.execute("UPDATE DocumentCandidate SET evidence_json = %s, puvodce = %s, validity_status = %s, "
                                "`signal` = %s WHERE id = %s", (old["evidence_json"], old["puvodce"],
                                                               old["validity_status"], old["signal"], old["id"]))
        cls.conn.commit()
        cls.conn.close()

    def current(self, committed):
        row = self.rows[committed["id"]]
        return mt.classify(row, self.decisions.get(row["id"], {}), self.snapshot)

    def test_the_rows_in_the_database_are_still_there(self):
        for committed in self.coverage:
            if committed["status"] == "database":
                with self.subTest(row=committed["id"], cislo=committed["cislo"]):
                    self.assertTrue(self.current(committed)["documents"],
                                    f"{committed['id']} {committed['cislo'] or committed['nazev']}: no document "
                                    f"any more (was {[d['identifier'] for d in committed['documents']]})")

    def test_the_rows_in_the_queue_are_candidates_or_documents(self):
        for committed in self.coverage:
            for entry in committed["candidates"]:
                key = entry["key"]
                with self.subTest(row=committed["id"], key=key):
                    designation = self.designations.get(key)
                    self.assertTrue(key in self.snapshot.candidates
                                    or self.snapshot.documents_for_key(key, designation),
                                    f"{committed['id']}: {key} is neither a candidate nor a document")

    def test_the_mpo_rows_are_in_the_evidence_of_the_candidates(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT candidate_key, evidence_json FROM DocumentCandidate WHERE evidence_json LIKE %s",
                        ('%"mpo_rows"%',))
            tagged = {r["candidate_key"] for r in cur.fetchall()}
        for committed in self.coverage:
            for entry in committed["candidates"]:
                if not self.snapshot.documents_for_key(entry["key"], self.designations.get(entry["key"])):
                    with self.subTest(key=entry["key"]):
                        self.assertIn(entry["key"], tagged)

    def test_a_second_import_changes_nothing(self):
        with self.conn.cursor() as cur:
            again = mt.write_candidates(cur, self.planned)
        self.conn.rollback()
        self.assertEqual({k: v for k, v in again.items() if v != "kept"}, {})

    def test_the_lex_oze_amendments_amend_the_energy_acts(self):
        amended = set(self.snapshot.documents_for_key("CZ:458/2000") + self.snapshot.documents_for_key("CZ:165/2012"))
        self.assertTrue(amended)
        with self.conn.cursor() as cur:
            for key in ("CZ:19/2023", "CZ:469/2023", "CZ:87/2025"):
                cur.execute("SELECT `signal`, evidence_json FROM DocumentCandidate WHERE candidate_key = %s", (key,))
                row = cur.fetchone()
                if row is None:  # already a document
                    continue
                with self.subTest(key=key):
                    evidence = json.loads(row["evidence_json"])
                    self.assertEqual(row["signal"], "amendment")
                    self.assertTrue(amended <= set(evidence["amends_ids"]))
                    self.assertTrue(evidence["alias"].startswith("LEX OZE"))

    def test_the_issuer_of_191_2022_is_the_labour_ministry(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT puvodce FROM DocumentCandidate WHERE candidate_key = 'CZ:191/2022'")
            row = cur.fetchone()
        if row is not None:
            self.assertEqual(row["puvodce"], "Ministerstvo práce a sociálních věcí")

    def test_every_other_row_states_why_it_is_not_a_document(self):
        for committed in self.coverage:
            with self.subTest(row=committed["id"]):
                self.assertIn(committed["status"], mt.STATUSES)
                if committed["status"] == "reason":
                    self.assertTrue(self.decisions.get(committed["id"], {}).get("reason"))


if __name__ == "__main__":
    unittest.main()
