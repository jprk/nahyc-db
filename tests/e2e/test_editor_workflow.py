"""Browser scenario: the whole editor review workflow through the real
pages — wrong password, login, proposing a fix, not being allowed to confirm
one's own proposal, a second editor confirming it, and the audit log.

The fixtures (two editors and one document flagged for review) are created
in, and removed from, the TEST database; the base class refuses any other."""
import re

from werkzeug.security import generate_password_hash

from browser_case import BASE_URL, BrowserTestCase, database_connection

TITLE = "E2E fixture: dokument čekající na revizi"
NEW_TEXT = "Popis doplněný editorem při testu v prohlížeči."


class EditorWorkflowTestCase(BrowserTestCase):
    PASSWORDS = {"e2e_alice": "alice-e2e-password", "e2e_bob": "bob-e2e-password"}

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.db = database_connection()
        cls.cleanup()
        with cls.db.cursor() as cur:
            cur.execute("INSERT INTO Document (title, needs_review, review_reason) "
                        "VALUES (%s, 1, 'chybí popis/anotace dokumentu')", (TITLE,))
            cls.document_id = cur.lastrowid
            for username, name in (("e2e_alice", "Alice E2E"), ("e2e_bob", "Bob E2E")):
                cur.execute("INSERT INTO User (username, name, email, password_hash) VALUES (%s, %s, %s, %s)",
                            (username, name, f"{username}@example.test",
                             generate_password_hash(cls.PASSWORDS[username])))

    @classmethod
    def cleanup(cls):
        with cls.db.cursor() as cur:
            cur.execute("DELETE FROM AuditLog WHERE record_id IN (SELECT id FROM Document WHERE title=%s)", (TITLE,))
            cur.execute("DELETE FROM ReviewItem WHERE document_id IN (SELECT id FROM Document WHERE title=%s)", (TITLE,))
            cur.execute("DELETE FROM Document WHERE title=%s", (TITLE,))
            cur.execute("DELETE FROM User WHERE username IN ('e2e_alice', 'e2e_bob')")

    @classmethod
    def tearDownClass(cls):
        db = getattr(cls, "db", None)
        if db:
            cls.cleanup()
            db.close()
        super().tearDownClass()

    def login(self, page, username, password=None):
        self.goto(page, "/admin/login")
        page.fill("#username", username)
        page.fill("#password", password or self.PASSWORDS[username])
        page.click("button[type=submit]")

    def row(self, page):
        return page.locator("table.admin-table tbody tr", has_text=TITLE)

    def test_propose_then_confirm_by_another_editor(self):
        alice = self.new_page()

        # Not logged in: the review list sends the visitor to the login page.
        self.goto(alice, "/admin/review")
        self.assertIn("/admin/login", alice.url)
        self.shot(alice, "01-login")

        # A wrong password is refused with a message, and no session starts.
        self.login(alice, "e2e_alice", "wrong-password")
        self.assertTrue(alice.get_by_text("Neplatné přihlašovací jméno nebo heslo").is_visible())
        self.shot(alice, "02-login-refused")

        # Alice logs in and sees the document waiting for a proposal.
        self.login(alice, "e2e_alice")
        alice.wait_for_url(re.compile(r"/admin/review$"))
        self.assertEqual(self.row(alice).count(), 1)
        self.assertTrue(self.row(alice).get_by_text("Čeká na návrh opravy").is_visible())
        self.shot(alice, "03-review-list")

        # She proposes a description.
        self.row(alice).get_by_role("link", name="Navrhnout opravu").click()
        alice.fill("#anotace_poznamka", NEW_TEXT)
        self.shot(alice, "04-propose-form")
        alice.click("button:has-text('Uložit návrh')")
        alice.wait_for_url(re.compile(r"/admin/review$"))
        self.assertTrue(self.row(alice).get_by_text("Navrženo editorem Alice E2E").is_visible())
        self.assertTrue(self.row(alice).get_by_text("Čeká na jiného editora").is_visible())
        self.assertEqual(self.row(alice).get_by_role("link", name="Posoudit").count(), 0)
        self.shot(alice, "05-proposed")

        # She may not confirm her own proposal, even by typing the address.
        with self.db.cursor() as cur:
            cur.execute("SELECT id, status FROM ReviewItem WHERE document_id=%s", (self.document_id,))
            item = cur.fetchone()
        self.assertEqual(item["status"], "proposed")
        self.expect_status(f"/admin/review/{item['id']}/confirm", 403)
        self.assertEqual(self.goto(alice, f"/admin/review/{item['id']}/confirm").status, 403)

        # Bob, a different editor, sees the proposal as a diff and confirms it.
        bob = self.new_page()
        self.login(bob, "e2e_bob")
        bob.wait_for_url(re.compile(r"/admin/review$"))
        self.assertTrue(self.row(bob).get_by_text("Navrženo editorem Alice E2E").is_visible())
        self.row(bob).get_by_role("link", name="Posoudit").click()
        self.assertTrue(bob.locator("td.diff-new", has_text=NEW_TEXT).is_visible())
        self.shot(bob, "06-confirm-diff")
        bob.click("button:has-text('Potvrdit')")
        bob.wait_for_url(re.compile(r"/admin/review$"))
        self.assertTrue(bob.get_by_text("Oprava potvrzena").is_visible())
        self.assertEqual(self.row(bob).count(), 0, "a confirmed item leaves the review list")
        self.shot(bob, "07-confirmed")

        # The document was changed, the item closed, and the audit log shows who did it.
        with self.db.cursor() as cur:
            cur.execute("SELECT description, needs_review FROM Document WHERE id=%s", (self.document_id,))
            document = cur.fetchone()
            cur.execute("SELECT status FROM ReviewItem WHERE id=%s", (item["id"],))
            status = cur.fetchone()["status"]
        self.assertEqual(document["description"], NEW_TEXT)
        self.assertEqual(document["needs_review"], 0)
        self.assertEqual(status, "confirmed")
        self.goto(bob, "/admin/audit-log")
        self.assertTrue(bob.get_by_text("e2e_bob").first.is_visible() or bob.get_by_text("Bob E2E").first.is_visible())
        self.shot(bob, "08-audit-log")


if __name__ == "__main__":
    import unittest
    unittest.main()
