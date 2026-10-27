"""Browser scenario: the candidate pages — the list with a filter, proposing a
candidate's acceptance, the proposer waiting, a second editor confirming (the
document page then exists), and rejecting another candidate with a reason.

Fixtures (two editors and two candidates with keys `TEST-E2E:…`) are created in,
and removed from, the TEST database; data/accepted_candidates.json is not
touched, because the server under test writes to the worktree's own copy, which
the scenario restores."""
import json
import pathlib
import re

from werkzeug.security import generate_password_hash

import sys

from browser_case import BrowserTestCase, database_connection

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src" / "tools"))
import candidates  # noqa: E402

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
ACCEPTED = REPO_ROOT / "data" / "accepted_candidates.json"
TITLE = "E2E kandidát: zákon o zkušebních vodíkových zařízeních"
REJECTED_TITLE = "E2E kandidát k zamítnutí"
PASSWORDS = {"e2e_cand_alice": "alice-cand-e2e", "e2e_cand_bob": "bob-cand-e2e"}


class CandidateWorkflowTestCase(BrowserTestCase):
    @classmethod
    def setUpClass(cls):
        cls.saved_accepted = ACCEPTED.read_text(encoding="utf-8") if ACCEPTED.exists() else None
        cls.db = database_connection()
        with cls.db.cursor() as cur:  # the test copy of the database has the table only once the live one has it
            candidates.ensure_schema(cur)
        cls.cleanup()
        super().setUpClass()
        with cls.db.cursor() as cur:
            for username in PASSWORDS:
                cur.execute("INSERT INTO User (username, name, email, password_hash) VALUES (%s, %s, %s, %s)",
                            (username, username.replace("e2e_cand_", "").title() + " E2E", f"{username}@example.test",
                             generate_password_hash(PASSWORDS[username])))
            for key, title in (("TEST-E2E:1", TITLE), ("TEST-E2E:2", REJECTED_TITLE)):
                cur.execute("INSERT INTO DocumentCandidate (candidate_key, source, designation, title, document_type, "
                            "url, language, jurisdikce, evidence_json, cited_by, validity_status) VALUES "
                            "(%s, 'citation', NULL, %s, 'Zákon', 'https://example.test/e2e', 'CS', 'CZ', %s, 99, 'účinný')",
                            (key, title, json.dumps({"citing_ids": [], "context": "… podle zákona o zkušebních zařízeních …"})))

    @classmethod
    def cleanup(cls):
        with cls.db.cursor() as cur:
            cur.execute("SELECT id, document_id FROM DocumentCandidate WHERE candidate_key LIKE 'TEST-E2E:%%'")
            rows = cur.fetchall()
            for row in rows:
                cur.execute("DELETE FROM AuditLog WHERE table_name = 'DocumentCandidate' AND record_id = %s", (row["id"],))
                if row["document_id"]:
                    for table in ("DocumentKeyword", "DocumentVersion"):
                        cur.execute(f"DELETE FROM {table} WHERE document_id = %s", (row["document_id"],))
                    cur.execute("DELETE FROM AuditLog WHERE table_name = 'Document' AND record_id = %s", (row["document_id"],))
            cur.execute("DELETE FROM DocumentCandidate WHERE candidate_key LIKE 'TEST-E2E:%%'")
            for row in rows:
                if row["document_id"]:
                    cur.execute("DELETE FROM Document WHERE id = %s", (row["document_id"],))
            cur.execute("DELETE FROM User WHERE username IN (%s, %s)", tuple(PASSWORDS))

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "db", None):
            cls.cleanup()
            cls.db.close()
        if cls.saved_accepted is None:
            ACCEPTED.unlink(missing_ok=True)
        else:
            ACCEPTED.write_text(cls.saved_accepted, encoding="utf-8")
        super().tearDownClass()

    def login(self, page, username):
        self.goto(page, "/admin/login")
        page.fill("#username", username)
        page.fill("#password", PASSWORDS[username])
        page.click("button[type=submit]")

    def row(self, page, title):
        return page.locator("table.candidate-table tbody tr", has_text=title)

    def test_propose_confirm_and_reject(self):
        alice = self.new_page()
        self.login(alice, "e2e_cand_alice")
        self.goto(alice, "/admin/candidates?q=E2E")
        self.assertEqual(self.row(alice, TITLE).count(), 1)
        self.shot(alice, "01-candidate-list")

        # Alice proposes acceptance with the metadata the document will get.
        self.row(alice, TITLE).get_by_role("link", name="Otevřít").click()
        alice.fill("#designation", "9002/2099 Sb.")
        alice.select_option("#scope_area", "4")
        self.shot(alice, "02-candidate-detail")
        alice.click("button:has-text('Navrhnout přijetí')")
        alice.wait_for_url(re.compile(r"/admin/candidates$"))
        self.goto(alice, "/admin/candidates?q=E2E")
        self.assertTrue(self.row(alice, TITLE).get_by_text("navržen k přijetí").is_visible())

        # She cannot confirm her own proposal.
        self.row(alice, TITLE).get_by_role("link", name="Otevřít").click()
        self.assertTrue(alice.get_by_text("čeká na potvrzení jiným editorem").is_visible())
        self.assertEqual(alice.locator("button:has-text('Potvrdit přijetí')").count(), 0)
        self.shot(alice, "03-waiting-for-second-editor")

        # Bob confirms; the document exists at once.
        bob = self.new_page()
        self.login(bob, "e2e_cand_bob")
        self.goto(bob, "/admin/candidates?q=E2E")
        self.row(bob, TITLE).get_by_role("link", name="Otevřít").click()
        bob.click("button:has-text('Potvrdit přijetí')")
        self.assertTrue(bob.get_by_text("Kandidát přijat a dokument založen").is_visible())
        self.shot(bob, "04-accepted")
        bob.get_by_role("link", name="založen v databázi").click()
        self.assertTrue(bob.get_by_text("9002/2099 Sb.").first.is_visible())
        self.shot(bob, "05-new-document-page")

        # Bob rejects the other candidate; without a reason it is refused.
        self.goto(bob, "/admin/candidates?q=E2E")
        self.row(bob, REJECTED_TITLE).get_by_role("link", name="Otevřít").click()
        bob.click("button:has-text('Zamítnout')")
        self.assertTrue(bob.get_by_text("Uveďte důvod zamítnutí").is_visible())
        bob.fill("#reject_note", "mimo rozsah databáze")
        bob.click("button:has-text('Zamítnout')")
        bob.wait_for_url(re.compile(r"/admin/candidates$"))
        self.goto(bob, "/admin/candidates?q=E2E&stav=rejected")
        self.assertEqual(self.row(bob, REJECTED_TITLE).count(), 1)
        self.shot(bob, "06-rejected-filter")
