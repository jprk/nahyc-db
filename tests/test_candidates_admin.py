"""Integration test of the candidate pages (app/candidates_admin.py) against the
TEST database (`.env.test`, `h2regdocs_test`), never the real one: proposing a
candidate, the proposer not being allowed to confirm, a second editor confirming
(the document is created at once), rejecting with and without a reason,
deferring and reopening, and a manual proposal. Fixtures (two editors and test
candidates with keys starting `TEST:`) are created and removed by the test;
data/accepted_candidates.json is redirected to a temporary file."""
import json
import os
import pathlib
import sys
import tempfile
import unittest

from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src" / "tools"))
import testdb  # noqa: E402

TITLE = "Testovací kandidát: zákon o zkoušení kandidátů"
MANUAL_TITLE = "Testovací ručně navržený dokument"
USERS = {"cand_alice": "alice-cand-password", "cand_bob": "bob-cand-password"}


class CandidateWorkflowTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        env_test = testdb.find_env_file(".env.test")
        if not env_test or not pathlib.Path(env_test).exists():
            raise unittest.SkipTest(".env.test not found — no rehearsal database configured")
        cls._saved_environ = dict(os.environ)
        load_dotenv(env_test, override=True)
        if os.environ.get("DB_NAME") != "h2regdocs_test":
            raise unittest.SkipTest(".env.test does not point at h2regdocs_test — refusing to guess")
        from app.app import app
        import candidates_admin
        cls.candidates_admin = candidates_admin
        cls.tmp = tempfile.TemporaryDirectory()
        cls._saved_path = candidates_admin.ACCEPTED_PATH
        candidates_admin.ACCEPTED_PATH = pathlib.Path(cls.tmp.name) / "accepted.json"
        cls.app = app
        import pymysql
        cls.conn = pymysql.connect(host=os.environ["DB_HOST"], port=int(os.environ["DB_PORT"]),
                                   user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
                                   database=os.environ["DB_NAME"], cursorclass=pymysql.cursors.DictCursor)
        cls.conn.autocommit(True)
        assert os.environ["DB_NAME"] == "h2regdocs_test"
        import candidates as cd
        with cls.conn.cursor() as cur:
            cd.ensure_schema(cur)
        cls.cleanup()
        with cls.conn.cursor() as cur:
            for username, password in USERS.items():
                cur.execute("INSERT INTO User (username, name, email, password_hash) VALUES (%s, %s, %s, %s)",
                            (username, username.replace("_", " ").title(), f"{username}@example.test",
                             generate_password_hash(password)))
            cur.execute("SELECT id FROM Document WHERE identifier IS NOT NULL ORDER BY id LIMIT 1")
            cls.repealed_id = cur.fetchone()["id"]

    @classmethod
    def cleanup(cls):
        with cls.conn.cursor() as cur:
            cur.execute("SELECT id, document_id FROM DocumentCandidate WHERE candidate_key LIKE 'TEST:%%' "
                        "OR title IN (%s, %s)", (TITLE, MANUAL_TITLE))
            rows = cur.fetchall()
            ids = [r["id"] for r in rows]
            docs = [r["document_id"] for r in rows if r["document_id"]]
            cur.execute("SELECT id FROM Document WHERE title IN (%s, %s)", (TITLE, MANUAL_TITLE))
            docs += [r["id"] for r in cur.fetchall()]
            for doc in set(docs):
                cur.execute("DELETE FROM AuditLog WHERE table_name = 'Document' AND record_id = %s", (doc,))
                cur.execute("DELETE FROM DocumentKeyword WHERE document_id = %s", (doc,))
                cur.execute("DELETE FROM DocumentVersion WHERE document_id = %s", (doc,))
            for candidate in ids:
                cur.execute("DELETE FROM AuditLog WHERE table_name = 'DocumentCandidate' AND record_id = %s", (candidate,))
            cur.execute("DELETE FROM DocumentCandidate WHERE candidate_key LIKE 'TEST:%%' OR title IN (%s, %s)",
                        (TITLE, MANUAL_TITLE))
            for doc in set(docs):
                cur.execute("DELETE FROM Document WHERE id = %s", (doc,))
            cur.execute("DELETE FROM AuditLog WHERE changed_by_user_id IN (SELECT id FROM User WHERE username IN (%s, %s))",
                        tuple(USERS))
            cur.execute("DELETE FROM User WHERE username IN (%s, %s)", tuple(USERS))

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "conn"):
            cls.cleanup()
            cls.conn.close()
        if hasattr(cls, "_saved_path"):
            cls.candidates_admin.ACCEPTED_PATH = cls._saved_path
            cls.tmp.cleanup()
        if hasattr(cls, "_saved_environ"):
            os.environ.clear()
            os.environ.update(cls._saved_environ)

    def client_for(self, username):
        client = self.app.test_client()
        client.post("/admin/login", data={"username": username, "password": USERS[username]})
        return client

    def insert_candidate(self, key, **fields):
        evidence = json.dumps(fields.pop("evidence", {"citing_ids": [], "context": "test"}))
        with self.conn.cursor() as cur:
            cur.execute("INSERT INTO DocumentCandidate (candidate_key, source, designation, title, document_type, url, "
                        "language, jurisdikce, evidence_json, cited_by) VALUES (%s, 'citation', %s, %s, 'Zákon', "
                        "'https://example.test/x', 'CS', 'CZ', %s, 3)",
                        (key, fields.get("designation"), fields.get("title", TITLE), evidence))
            return cur.lastrowid

    def candidate(self, candidate_id):
        with self.conn.cursor() as cur:
            cur.execute("SELECT * FROM DocumentCandidate WHERE id = %s", (candidate_id,))
            return cur.fetchone()

    def test_not_logged_in_goes_to_the_login(self):
        response = self.app.test_client().get("/admin/candidates")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login", response.headers["Location"])

    def test_acceptance_needs_a_second_editor_and_creates_the_document(self):
        candidate_id = self.insert_candidate("TEST:1", designation="9001/2099 Sb.",
                                             evidence={"repeals_ids": [self.repealed_id]})
        alice, bob = self.client_for("cand_alice"), self.client_for("cand_bob")
        self.assertIn(TITLE, alice.get("/admin/candidates?stav=all").get_data(as_text=True))
        form = {"designation": "9001/2099 Sb.", "title": TITLE, "document_type": "Zákon", "url": "https://example.test/x",
                "language": "CS", "jurisdikce": "CZ", "scope_area": ["9", "7"], "decision_note": "patří do bezpečnosti"}
        alice.post(f"/admin/candidates/{candidate_id}/propose", data=form)
        self.assertEqual(self.candidate(candidate_id)["status"], "proposed")
        # several subject areas: all of them kept, the first (lowest) one also in `scope_area`
        self.assertEqual((self.candidate(candidate_id)["scope_areas"], self.candidate(candidate_id)["scope_area"]),
                         ("7,9", 7))
        self.assertIn("Energetika", bob.get(f"/admin/candidates/{candidate_id}").get_data(as_text=True))
        self.assertEqual(alice.post(f"/admin/candidates/{candidate_id}/confirm").status_code, 403)
        bob.post(f"/admin/candidates/{candidate_id}/confirm")
        row = self.candidate(candidate_id)
        self.assertEqual(row["status"], "accepted")
        with self.conn.cursor() as cur:
            cur.execute("SELECT d.identifier, d.title, d.slug, dt.name AS type FROM Document d "
                        "JOIN DocumentType dt ON dt.id = d.type_id WHERE d.id = %s", (row["document_id"],))
            document = cur.fetchone()
            cur.execute("SELECT lifecycle_state FROM DocumentVersion WHERE document_id = %s AND is_current = 1",
                        (row["document_id"],))
            version = cur.fetchone()
            cur.execute("SELECT k.keyword FROM DocumentKeyword dk JOIN Keyword k ON k.id = dk.keyword_id "
                        "WHERE dk.document_id = %s", (row["document_id"],))
            keywords = [r["keyword"] for r in cur.fetchall()]
            cur.execute("SELECT COUNT(*) AS n FROM document_relation WHERE from_document_id = %s AND to_document_id = %s "
                        "AND relation_type = 'REPEALS'", (row["document_id"], self.repealed_id))
            repeals = cur.fetchone()["n"]
            cur.execute("SELECT action FROM AuditLog WHERE table_name = 'DocumentCandidate' AND record_id = %s ORDER BY id",
                        (candidate_id,))
            actions = [r["action"] for r in cur.fetchall()]
            cur.execute("DELETE FROM document_relation WHERE from_document_id = %s", (row["document_id"],))
        self.assertEqual((document["identifier"], document["title"], document["type"]), ("9001/2099 Sb.", TITLE, "Zákon"))
        self.assertTrue(document["slug"])
        self.assertEqual(version["lifecycle_state"], "active")
        self.assertEqual(sorted(keywords), ["Bezpečnost", "Energetika"])
        self.assertEqual(repeals, 1)
        self.assertEqual(actions, ["PROPOSE", "CONFIRM"])
        accepted = json.loads(self.candidates_admin.ACCEPTED_PATH.read_text(encoding="utf-8"))
        self.assertEqual(accepted["TEST:1"]["znacka"], "9001/2099 Sb.")
        self.assertEqual(accepted["TEST:1"]["klicova_slova"], ["Bezpečnost", "Energetika"])
        self.assertIn("založen", bob.get(f"/admin/candidates/{candidate_id}").get_data(as_text=True))

    def test_the_detail_shows_where_every_citing_document_cites_the_candidate(self):
        place = {"before": "postupuje se podle zákona č. ", "cited": "9001/2099 Sb.", "after": ", o zkušebnictví", "amendment": False}
        candidate_id = self.insert_candidate("TEST:contexts", evidence={
            "citing_ids": [self.repealed_id], "context": "x",
            "contexts": {str(self.repealed_id): {"count": 5, "places": [place, {**place, "amendment": True}, place]}}})
        page = self.client_for("cand_alice").get(f"/admin/candidates/{candidate_id}").get_data(as_text=True)
        self.assertIn("<mark>9001/2099 Sb.</mark>", page)
        self.assertIn("(5× v textu)", page)
        self.assertIn("další výskyty (4)", page)
        self.assertIn("ve výčtu novel", page)
        self.assertIn("a dalších 2 výskytů", page)

    def test_a_draft_found_by_a_source_becomes_a_draft_document(self):
        evidence = {"findings": {"veklep-odok": {"source": "veklep-odok", "signal": "draft", "title": TITLE,
                                                 "url": "https://example.test/veklep/1", "date": "2026-10-20",
                                                 "excerpt": "návrh zákona o zkoušení", "seen": "2026-10-28T00:00:00",
                                                 "first_seen": "2026-10-28T00:00:00", "needs_key": True}}}
        with self.conn.cursor() as cur:
            cur.execute("INSERT INTO DocumentCandidate (candidate_key, source, `signal`, title, document_type, url, "
                        "language, jurisdikce, evidence_json) VALUES ('TEST:draft', 'veklep-odok', 'draft', %s, "
                        "'Zákon', 'https://example.test/veklep/1', 'CS', 'CZ', %s)", (TITLE, json.dumps(evidence)))
            candidate_id = cur.lastrowid
        alice, bob = self.client_for("cand_alice"), self.client_for("cand_bob")
        page = alice.get(f"/admin/candidates/{candidate_id}").get_data(as_text=True)
        self.assertIn("Nálezy ve sledovaných zdrojích (1)", page)
        self.assertIn("VeKLEP", page)
        self.assertIn("návrh předpisu", page)
        self.assertIn("doplnit ručně", page)
        self.assertIn(TITLE, alice.get("/admin/candidates?zdroj=veklep-odok").get_data(as_text=True))
        alice.post(f"/admin/candidates/{candidate_id}/propose",
                   data={"designation": "", "title": TITLE, "document_type": "Zákon", "url": "https://example.test/veklep/1",
                         "language": "CS", "jurisdikce": "CZ", "scope_area": "1", "decision_note": ""})
        bob.post(f"/admin/candidates/{candidate_id}/confirm")
        row = self.candidate(candidate_id)
        self.assertEqual(row["status"], "accepted")
        with self.conn.cursor() as cur:
            cur.execute("SELECT lifecycle_state FROM DocumentVersion WHERE document_id = %s AND is_current = 1",
                        (row["document_id"],))
            self.assertEqual(cur.fetchone()["lifecycle_state"], "draft")

    def test_tiers_and_an_amendment_of_a_document_of_the_database(self):
        with self.conn.cursor() as cur:
            cur.execute("INSERT INTO DocumentCandidate (candidate_key, source, `signal`, title, document_type, url, "
                        "language, jurisdikce, evidence_json, tier, occurrences) VALUES ('TEST:tier2', 'esbirka-lod', "
                        "'new_document', 'Testovací kandidát pásma 2', 'Zákon', 'https://example.test/t2', 'CS', 'CZ', "
                        "'{}', 2, 1)")
            cur.execute("INSERT INTO DocumentCandidate (candidate_key, source, `signal`, title, document_type, url, "
                        "language, jurisdikce, evidence_json, tier, occurrences) VALUES ('TEST:amends', 'esbirka-lod', "
                        "'amendment', %s, 'Zákon', 'https://example.test/n', 'CS', 'CZ', %s, 1, 5)",
                        (TITLE, json.dumps({"amends_ids": [self.repealed_id]})))
            candidate_id = cur.lastrowid
        alice, bob = self.client_for("cand_alice"), self.client_for("cand_bob")
        default = alice.get("/admin/candidates?q=Testovací").get_data(as_text=True)
        self.assertIn(TITLE, default)
        self.assertNotIn("Testovací kandidát pásma 2", default)
        self.assertIn("Testovací kandidát pásma 2", alice.get("/admin/candidates?q=Testovací&pasmo=2").get_data(as_text=True))
        page = alice.get(f"/admin/candidates/{candidate_id}").get_data(as_text=True)
        self.assertIn("novela dokumentu v databázi", page)
        self.assertIn("Mění tyto dokumenty databáze", page)
        alice.post(f"/admin/candidates/{candidate_id}/propose",
                   data={"designation": "9004/2099 Sb.", "title": TITLE, "document_type": "Zákon",
                         "url": "https://example.test/n", "language": "CS", "jurisdikce": "CZ", "scope_area": "9",
                         "decision_note": ""})
        bob.post(f"/admin/candidates/{candidate_id}/confirm")
        row = self.candidate(candidate_id)
        with self.conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS n FROM document_relation WHERE from_document_id = %s AND to_document_id = %s "
                        "AND relation_type = 'AMENDS'", (row["document_id"], self.repealed_id))
            amends = cur.fetchone()["n"]
            cur.execute("DELETE FROM document_relation WHERE from_document_id = %s", (row["document_id"],))
        self.assertEqual((row["status"], amends), ("accepted", 1))

    def test_a_proposal_without_title_type_or_area_is_refused(self):
        candidate_id = self.insert_candidate("TEST:2", title="Testovací kandidát bez okruhu")
        alice = self.client_for("cand_alice")
        alice.post(f"/admin/candidates/{candidate_id}/propose",
                   data={"title": "x", "document_type": "Zákon", "language": "CS", "scope_area": ""})
        self.assertEqual(self.candidate(candidate_id)["status"], "new")

    def test_rejecting_needs_a_reason_and_one_editor_and_can_be_reopened(self):
        candidate_id = self.insert_candidate("TEST:3", title="Testovací kandidát k zamítnutí")
        alice = self.client_for("cand_alice")
        alice.post(f"/admin/candidates/{candidate_id}/reject", data={"decision_note": ""})
        self.assertEqual(self.candidate(candidate_id)["status"], "new")
        alice.post(f"/admin/candidates/{candidate_id}/reject", data={"decision_note": "mimo rozsah"})
        row = self.candidate(candidate_id)
        self.assertEqual((row["status"], row["decision_note"]), ("rejected", "mimo rozsah"))
        alice.post(f"/admin/candidates/{candidate_id}/reopen")
        self.assertEqual(self.candidate(candidate_id)["status"], "new")
        alice.post(f"/admin/candidates/{candidate_id}/defer", data={"decision_note": "později"})
        self.assertEqual(self.candidate(candidate_id)["status"], "deferred")

    def test_a_manual_proposal_waits_for_a_second_editor(self):
        alice = self.client_for("cand_alice")
        alice.post("/admin/candidates/new", data={"designation": "", "title": MANUAL_TITLE, "document_type": "Metodika",
                                                   "url": "https://example.test/m", "language": "CS", "jurisdikce": "CZ",
                                                   "scope_area": "1", "decision_note": ""})
        with self.conn.cursor() as cur:
            cur.execute("SELECT * FROM DocumentCandidate WHERE title = %s", (MANUAL_TITLE,))
            row = cur.fetchone()
        self.assertEqual((row["source"], row["status"]), ("manual", "proposed"))
        self.assertEqual(alice.post(f"/admin/candidates/{row['id']}/confirm").status_code, 403)


if __name__ == "__main__":
    unittest.main()
