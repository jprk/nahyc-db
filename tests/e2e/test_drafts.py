"""Browser scenario: prepared documents (app/drafts_admin.py) — the way from the
review list to the drafts, proposing that a draft became the act itself, the
proposer waiting, a second editor confirming (the document page then shows the
new designation, the state and the date of the last check), and a draft
promulgated as another document of the database (`ENACTED_AS`).

Fixtures (two editors, three documents titled `E2E-DRAFT …`) are created in, and
removed from, the TEST database; data/manual_corrections.json and
data/document_relations_editor.json, which the server under test writes in this
worktree, are restored afterwards."""
import pathlib
import re
import sys

from werkzeug.security import generate_password_hash

from browser_case import PHONE, BrowserTestCase, database_connection

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src" / "tools"))
import state_changes  # noqa: E402
import status_checks  # noqa: E402

FILES = [REPO_ROOT / "data" / "manual_corrections.json", REPO_ROOT / "data" / "document_relations_editor.json"]
PASSWORDS = {"e2e_draft_alice": "alice-draft-e2e", "e2e_draft_bob": "bob-draft-e2e"}
DOCS = {"bill": ("E2E-DRAFT 1", "E2E-DRAFT Návrh zákona o vodíkových plnicích stanicích"),
        "pren": ("E2E-DRAFT prEN 9", "E2E-DRAFT Návrh normy pro vodíkové armatury"),
        "en": ("E2E-DRAFT EN 9", "E2E-DRAFT Norma pro vodíkové armatury")}
NEW_DESIGNATION = "9903/2099 Sb."


class DraftWorkflowTestCase(BrowserTestCase):
    @classmethod
    def setUpClass(cls):
        cls.saved = {path: path.read_text(encoding="utf-8") if path.exists() else None for path in FILES}
        cls.db = database_connection()
        with cls.db.cursor() as cur:  # the test copy of the database has them only once the live one has
            state_changes.ensure_schema(cur)
            status_checks.ensure_columns(cur)
        cls.cleanup()
        super().setUpClass()
        with cls.db.cursor() as cur:
            for username in PASSWORDS:
                cur.execute("INSERT INTO User (username, name, email, password_hash) VALUES (%s, %s, %s, %s)",
                            (username, username.replace("e2e_draft_", "").title() + " E2E", f"{username}@example.test",
                             generate_password_hash(PASSWORDS[username])))
            cls.ids = {}
            for name, (identifier, title) in DOCS.items():
                cur.execute("INSERT INTO Document (title, identifier, slug, url, description) VALUES (%s, %s, %s, %s, %s)",
                            (title, identifier, "e2e-draft-" + name, f"https://example.test/{name}", "Popis."))
                cls.ids[name] = cur.lastrowid
                cur.execute("INSERT INTO DocumentVersion (document_id, version, is_current, lifecycle_state) "
                            "VALUES (%s, 1, 1, 'draft')", (cur.lastrowid,))

    @classmethod
    def cleanup(cls):
        with cls.db.cursor() as cur:
            cur.execute("SELECT id FROM Document WHERE title LIKE 'E2E-DRAFT%%'")
            for doc in [r["id"] for r in cur.fetchall()]:
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
                        tuple(PASSWORDS))
            cur.execute("DELETE FROM User WHERE username IN (%s, %s)", tuple(PASSWORDS))

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "db", None):
            cls.cleanup()
            cls.db.close()
        for path, text in cls.saved.items():
            if text is None:
                path.unlink(missing_ok=True)
            else:
                path.write_text(text, encoding="utf-8")
        super().tearDownClass()

    def login(self, page, username):
        self.goto(page, "/admin/login")
        page.fill("#username", username)
        page.fill("#password", PASSWORDS[username])
        page.click("button[type=submit]")

    def open_draft(self, page, title):
        self.goto(page, "/admin/drafts?q=E2E-DRAFT")
        page.locator("table.drafts-table tbody tr", has_text=title).get_by_role("link", name="Otevřít").click()

    def test_a_draft_becomes_the_promulgated_act(self):
        alice = self.new_page()
        self.login(alice, "e2e_draft_alice")
        alice.get_by_role("link", name="Připravované dokumenty").click()
        alice.wait_for_url(re.compile(r"/admin/drafts$"))
        self.open_draft(alice, DOCS["bill"][1])
        alice.fill("#znacka", NEW_DESIGNATION)
        alice.fill("#platnost", "1. 1. 2100")
        alice.fill("#note", "Sbírka zákonů, částka 1/2099")
        self.shot(alice, "01-draft-form")
        alice.click("button:has-text('Navrhnout změnu stavu')")
        self.assertTrue(alice.get_by_text("čeká na potvrzení jiným editorem").first.is_visible())
        self.assertEqual(alice.locator("button:has-text('Potvrdit změnu stavu')").count(), 0)
        self.shot(alice, "02-waiting-for-second-editor")

        bob = self.new_page()
        self.login(bob, "e2e_draft_bob")
        self.goto(bob, "/admin/drafts")
        self.assertTrue(bob.locator("table.drafts-proposed", has_text=NEW_DESIGNATION).is_visible())
        self.open_draft(bob, DOCS["bill"][1])
        bob.click("button:has-text('Potvrdit změnu stavu')")
        self.assertTrue(bob.get_by_text("Změna stavu potvrzena a zapsána").is_visible())
        self.shot(bob, "03-confirmed")
        bob.get_by_role("link", name="stránka dokumentu").click()
        self.assertTrue(bob.locator(".doc-designation", has_text=NEW_DESIGNATION).is_visible())
        self.assertTrue(bob.locator("table.doc-table", has_text="vyhlášený, dosud neúčinný").is_visible())
        self.assertTrue(bob.get_by_text("(editor Bob E2E)").is_visible())
        self.shot(bob, "04-document-page")

    def test_a_draft_promulgated_as_another_document(self):
        page = self.new_page()
        self.login(page, "e2e_draft_bob")
        self.goto(page, "/dokument/e2e-draft-pren")
        page.get_by_role("link", name="Návrh byl vyhlášen — převést").click()
        page.check("input[name=mode][value=act]")
        page.check("input[name=to_state][value=active]")
        page.fill("#target", DOCS["en"][0])
        page.click("button:has-text('Navrhnout změnu stavu')")
        self.assertTrue(page.get_by_text("Vyhlášený předpis").first.is_visible())

        alice = self.new_page()
        self.login(alice, "e2e_draft_alice")
        self.open_draft(alice, DOCS["pren"][1])
        alice.click("button:has-text('Potvrdit změnu stavu')")
        self.goto(alice, "/dokument/e2e-draft-pren")
        self.assertTrue(alice.get_by_text("návrh vyhlášen jako").is_visible())
        self.assertTrue(alice.locator("table.doc-table", has_text="nahrazený").is_visible())
        self.assertEqual(alice.get_by_role("link", name="Návrh byl vyhlášen — převést").count(), 0)
        self.shot(alice, "05-draft-superseded")
        self.goto(alice, "/dokument/e2e-draft-en")
        self.assertTrue(alice.get_by_text("vyhlášené znění návrhu").is_visible())
        self.assertTrue(alice.locator("table.doc-table", has_text="účinný").is_visible())

    def test_phone_width(self):
        phone = self.new_page(PHONE)
        self.login(phone, "e2e_draft_alice")
        for path in ("/admin/drafts", "/dokument/e2e-draft-en"):
            self.goto(phone, path)
            self.assertLessEqual(phone.evaluate("document.documentElement.scrollWidth"), PHONE["width"], path)
        self.goto(phone, f"/admin/drafts/{self.ids['bill']}")
        self.assertLessEqual(phone.evaluate("document.documentElement.scrollWidth"), PHONE["width"])
        self.shot(phone, "06-phone-draft-detail", full_page=False)
