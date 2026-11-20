"""Integration test of the pages of prepared documents (app/drafts_admin.py)
against the TEST database (`.env.test`, `h2regdocs_test`), never the real one:
a draft that became the act itself (new designation, state `promulgated`), a draft
promulgated as another document of the database (`ENACTED_AS`, the draft
`superseded`, the act `active`), the proposer not being allowed to confirm, a
withdrawn proposal, refused proposals, the date of the last check on the
document page, and an approved update of a strategy superseding the strategy it
replaces. Fixtures (two editors, documents titled `TEST-DRAFT …`) are created
and removed by the test; data/manual_corrections.json and
data/document_relations_editor.json are redirected to temporary files."""
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

USERS = {"draft_alice": "alice-draft-password", "draft_bob": "bob-draft-password"}
DOCS = {"self": ("TEST-DRAFT 1", "TEST-DRAFT návrh zákona o vodíku"),
        "act": ("TEST-DRAFT/AWI 2", "TEST-DRAFT návrh normy"),
        "target": ("TEST-DRAFT 2", "TEST-DRAFT vydaná norma"),
        "spare": ("TEST-DRAFT 3", "TEST-DRAFT další návrh")}


class DraftWorkflowTestCase(unittest.TestCase):
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
        import state_changes
        import status_checks
        cls.sc = state_changes
        cls.tmp = tempfile.TemporaryDirectory()
        cls._saved_paths = (state_changes.MANUAL_CORRECTIONS_PATH, state_changes.EDITOR_RELATIONS_PATH)
        state_changes.MANUAL_CORRECTIONS_PATH = pathlib.Path(cls.tmp.name) / "corrections.json"
        state_changes.EDITOR_RELATIONS_PATH = pathlib.Path(cls.tmp.name) / "relations.json"
        cls.app = app
        import pymysql
        cls.conn = pymysql.connect(host=os.environ["DB_HOST"], port=int(os.environ["DB_PORT"]),
                                   user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
                                   database=os.environ["DB_NAME"], cursorclass=pymysql.cursors.DictCursor)
        cls.conn.autocommit(True)
        assert os.environ["DB_NAME"] == "h2regdocs_test"
        with cls.conn.cursor() as cur:
            state_changes.ensure_schema(cur)
            status_checks.ensure_columns(cur)
        cls.cleanup()
        cls.ids = {}
        with cls.conn.cursor() as cur:
            for username, password in USERS.items():
                cur.execute("INSERT INTO User (username, name, email, password_hash) VALUES (%s, %s, %s, %s)",
                            (username, username.replace("_", " ").title(), f"{username}@example.test",
                             generate_password_hash(password)))
            for name, (identifier, title) in DOCS.items():
                cur.execute("INSERT INTO Document (title, identifier, slug, url, description) VALUES (%s, %s, %s, %s, 'x')",
                            (title, identifier, "test-draft-" + name, f"https://example.test/{name}"))
                cls.ids[name] = cur.lastrowid
                cur.execute("INSERT INTO DocumentVersion (document_id, version, is_current, lifecycle_state) "
                            "VALUES (%s, 1, 1, 'draft')", (cls.ids[name],))

    @classmethod
    def cleanup(cls):
        with cls.conn.cursor() as cur:
            cur.execute("SELECT id FROM Document WHERE title LIKE 'TEST-DRAFT%%' OR identifier LIKE 'TEST-DRAFT%%' "
                        "OR identifier = '9901/2099 Sb.'")
            docs = [r["id"] for r in cur.fetchall()]
            for doc in docs:
                cur.execute("SELECT id FROM DocumentStateChange WHERE document_id = %s", (doc,))
                for change in cur.fetchall():
                    cur.execute("DELETE FROM AuditLog WHERE table_name = 'DocumentStateChange' AND record_id = %s",
                                (change["id"],))
                cur.execute("DELETE FROM DocumentStateChange WHERE document_id = %s OR target_document_id = %s",
                            (doc, doc))
                cur.execute("DELETE FROM document_relation WHERE from_document_id = %s OR to_document_id = %s",
                            (doc, doc))
                cur.execute("DELETE FROM AuditLog WHERE table_name = 'Document' AND record_id = %s", (doc,))
                cur.execute("DELETE FROM DocumentVersion WHERE document_id = %s", (doc,))
                cur.execute("DELETE FROM Document WHERE id = %s", (doc,))
            cur.execute("DELETE FROM AuditLog WHERE changed_by_user_id IN (SELECT id FROM User WHERE username IN (%s, %s))",
                        tuple(USERS))
            cur.execute("DELETE FROM User WHERE username IN (%s, %s)", tuple(USERS))

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "conn"):
            cls.cleanup()
            if getattr(cls, "created_type", None):
                with cls.conn.cursor() as cur:
                    cur.execute("DELETE FROM DocumentType WHERE id = %s", (cls.created_type,))
            cls.conn.close()
        if hasattr(cls, "_saved_paths"):
            cls.sc.MANUAL_CORRECTIONS_PATH, cls.sc.EDITOR_RELATIONS_PATH = cls._saved_paths
            cls.tmp.cleanup()
        if hasattr(cls, "_saved_environ"):
            os.environ.clear()
            os.environ.update(cls._saved_environ)

    def client_for(self, username):
        client = self.app.test_client()
        client.post("/admin/login", data={"username": username, "password": USERS[username]})
        return client

    def one(self, sql, params=()):
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()

    def state(self, name):
        return self.one("SELECT lifecycle_state FROM DocumentVersion WHERE document_id = %s AND is_current = 1",
                        (self.ids[name],))["lifecycle_state"]

    def open_change(self, name):
        return self.one("SELECT * FROM DocumentStateChange WHERE document_id = %s AND status = 'proposed'",
                        (self.ids[name],))

    def test_not_logged_in_goes_to_the_login(self):
        self.assertEqual(self.app.test_client().get("/admin/drafts").status_code, 302)

    def test_the_list_shows_the_drafts(self):
        page = self.client_for("draft_alice").get("/admin/drafts?q=TEST-DRAFT").get_data(as_text=True)
        self.assertIn(DOCS["spare"][1], page)  # the other drafts may have been converted by now
        self.assertIn("Připravované dokumenty", page)

    def test_a_draft_becomes_the_act_itself(self):
        alice, bob = self.client_for("draft_alice"), self.client_for("draft_bob")
        doc = self.ids["self"]
        alice.post(f"/admin/drafts/{doc}/propose", data={"mode": "self", "to_state": "promulgated",
                                                         "znacka": "9901/2099 Sb.", "nazev_cz": DOCS["self"][1],
                                                         "platnost": "1. 1. 2100", "note": "Sbírka, částka 1"})
        change = self.open_change("self")
        self.assertEqual(json.loads(change["changes_json"]), {"znacka": "9901/2099 Sb.", "platnost": "1. 1. 2100"})
        self.assertEqual(self.state("self"), "draft", "nothing changes before the confirmation")
        self.assertEqual(alice.post(f"/admin/drafts/change/{change['id']}/confirm").status_code, 403)
        bob.post(f"/admin/drafts/change/{change['id']}/confirm")
        row = self.one("SELECT identifier, effective_date, status_checked_at, status_checked_by FROM Document "
                       "WHERE id = %s", (doc,))
        self.assertEqual(row["identifier"], "9901/2099 Sb.")
        self.assertEqual(row["effective_date"], "1. 1. 2100")
        self.assertEqual(row["status_checked_by"], "editor Draft Bob")
        self.assertIsNotNone(row["status_checked_at"])
        self.assertEqual(self.state("self"), "promulgated")
        corrections = json.loads(self.sc.MANUAL_CORRECTIONS_PATH.read_text(encoding="utf-8"))
        self.assertEqual(corrections["TEST-DRAFT 1"]["changes"]["stav_dokumentu"], "promulgated")
        self.assertEqual(corrections["TEST-DRAFT 1"]["changes"]["znacka"], "9901/2099 Sb.")
        self.assertIsNotNone(self.one("SELECT id FROM AuditLog WHERE table_name = 'Document' AND record_id = %s "
                                      "AND action = 'UPDATE'", (doc,)))
        page = self.app.test_client().get("/dokument/test-draft-self").get_data(as_text=True)
        self.assertIn("Poslední kontrola stavu", page)
        self.assertIn("editor Draft Bob", page)

    def test_a_draft_promulgated_as_another_document(self):
        alice, bob = self.client_for("draft_alice"), self.client_for("draft_bob")
        bob.post(f"/admin/drafts/{self.ids['act']}/propose", data={"mode": "act", "to_state": "active",
                                                                   "target": DOCS["target"][0]})
        change = self.open_change("act")
        self.assertEqual(change["target_document_id"], self.ids["target"])
        alice.post(f"/admin/drafts/change/{change['id']}/confirm")
        self.assertEqual(self.state("act"), "superseded")
        self.assertEqual(self.state("target"), "active")
        self.assertIsNotNone(self.one("SELECT id FROM document_relation WHERE from_document_id = %s AND "
                                      "to_document_id = %s AND relation_type = 'ENACTED_AS'",
                                      (self.ids["act"], self.ids["target"])))
        relations = json.loads(self.sc.EDITOR_RELATIONS_PATH.read_text(encoding="utf-8"))
        self.assertIn({"from_identifier": "TEST-DRAFT/AWI 2", "to_identifier": "TEST-DRAFT 2",
                       "relation_type": "ENACTED_AS", "note": "Návrh vyhlášen jako tento předpis (editor)."}, relations)
        page = self.app.test_client().get("/dokument/test-draft-target").get_data(as_text=True)
        self.assertIn("vyhlášené znění návrhu", page)

    def test_an_approved_strategy_update_supersedes_the_strategy(self):
        alice, bob = self.client_for("draft_alice"), self.client_for("draft_bob")
        with self.conn.cursor() as cur:
            cur.execute("SELECT id FROM DocumentType WHERE name = 'Strategie'")
            row = cur.fetchone()
            if row is None:  # the live database may not have the renamed type yet
                cur.execute("INSERT INTO DocumentType (name) VALUES ('Strategie')")
                type_id, self.__class__.created_type = cur.lastrowid, cur.lastrowid
            else:
                type_id = row["id"]
            ids = {}
            for name, state in (("old", "active"), ("new", "draft")):
                cur.execute("INSERT INTO Document (title, slug, url, description, type_id) VALUES (%s, %s, %s, 'x', %s)",
                            (f"TEST-DRAFT strategie {name}", f"test-draft-strategy-{name}",
                             f"https://example.test/strategy-{name}", type_id))
                ids[name] = cur.lastrowid
                cur.execute("INSERT INTO DocumentVersion (document_id, version, is_current, lifecycle_state) "
                            "VALUES (%s, 1, 1, %s)", (ids[name], state))
            cur.execute("INSERT INTO document_relation (from_document_id, to_document_id, relation_type) "
                        "VALUES (%s, %s, 'REPEALS')", (ids["new"], ids["old"]))
        page = self.app.test_client().get("/dokument/test-draft-strategy-new").get_data(as_text=True)
        self.assertIn("má nahradit", page)
        page = self.app.test_client().get("/dokument/test-draft-strategy-old").get_data(as_text=True)
        self.assertIn("má být nahrazen připravovaným dokumentem", page)
        alice.post(f"/admin/drafts/{ids['new']}/propose", data={"mode": "self", "to_state": "active"})
        change = self.one("SELECT * FROM DocumentStateChange WHERE document_id = %s AND status = 'proposed'", (ids["new"],))
        bob.post(f"/admin/drafts/change/{change['id']}/confirm")
        state = "SELECT lifecycle_state FROM DocumentVersion WHERE document_id = %s AND is_current = 1"
        self.assertEqual(self.one(state, (ids["new"],))["lifecycle_state"], "active")
        self.assertEqual(self.one(state, (ids["old"],))["lifecycle_state"], "superseded")
        corrections = json.loads(self.sc.MANUAL_CORRECTIONS_PATH.read_text(encoding="utf-8"))
        old_key = self.sc.correction_key(None, "https://example.test/strategy-old", {})
        self.assertEqual(corrections[old_key]["changes"]["stav_dokumentu"], "superseded")
        page = self.app.test_client().get("/dokument/test-draft-strategy-new").get_data(as_text=True)
        self.assertIn("nahrazuje", page)
        self.assertNotIn("má nahradit", page)

    def test_refused_proposals_and_withdrawing(self):
        alice, bob = self.client_for("draft_alice"), self.client_for("draft_bob")
        doc = self.ids["spare"]
        alice.post(f"/admin/drafts/{doc}/propose", data={"mode": "act", "to_state": "active", "target": "NO SUCH DOC"})
        alice.post(f"/admin/drafts/{doc}/propose", data={"mode": "act", "to_state": "active", "target": DOCS["spare"][0]})
        alice.post(f"/admin/drafts/{doc}/propose", data={"mode": "self", "to_state": "active",
                                                         "znacka": DOCS["target"][0]})
        self.assertIsNone(self.open_change("spare"))
        alice.post(f"/admin/drafts/{doc}/propose", data={"mode": "self", "to_state": "active"})
        change = self.open_change("spare")
        self.assertIsNotNone(change)
        alice.post(f"/admin/drafts/{doc}/propose", data={"mode": "self", "to_state": "promulgated"})
        self.assertEqual(self.one("SELECT COUNT(*) AS n FROM DocumentStateChange WHERE document_id = %s", (doc,))["n"], 1,
                         "one open proposal per document")
        self.assertEqual(bob.post(f"/admin/drafts/change/{change['id']}/withdraw").status_code, 403)
        alice.post(f"/admin/drafts/change/{change['id']}/withdraw")
        self.assertEqual(self.one("SELECT status FROM DocumentStateChange WHERE id = %s", (change["id"],))["status"],
                         "withdrawn")
        self.assertEqual(self.state("spare"), "draft")


if __name__ == "__main__":
    unittest.main()
