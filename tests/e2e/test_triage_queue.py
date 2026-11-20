"""Browser scenario: the automat's work in the candidate queue (doc/FRONTA_AUTOMAT.md)
— the filter of its proposals with the badge "automat", the recommendation of the
model on the detail page with the form prefilled from it, the bulk confirmation of
ticked proposals, and the list and the detail at phone width.

Fixtures (an editor, the technical account `automat` if missing, three candidates
`TEST-E2E-TRIAGE:…`) are created in, and removed from, the TEST database;
data/accepted_candidates.json is restored after the run."""
import json
import pathlib
import sys

from werkzeug.security import generate_password_hash

from browser_case import PHONE, BrowserTestCase, database_connection

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src" / "tools"))
import candidates  # noqa: E402

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
ACCEPTED = REPO_ROOT / "data" / "accepted_candidates.json"
PREFIX = "TEST-E2E-TRIAGE:"
PROPOSED = ["E2E automat: technické pravidlo o vodíkových plnicích stanicích",
            "E2E automat: nařízení o tlakových zařízeních"]
RECOMMENDED = "E2E automat: vyhláška o měřidlech plynu"
EDITOR, PASSWORD = "e2e_triage_carol", "carol-triage-e2e"
MODEL = {"reasoning": "Vyhláška stanoví měřidla k povinnému ověřování, mezi nimi výdejní stojany plynů; okruh 4.",
         "recommendation": "accept", "category": "v_rozsahu", "scope_areas": [4], "document_type": "Vyhláška",
         "puvodce": "Ministerstvo průmyslu a obchodu", "official_title": None, "confidence": 0.9,
         "token_confidence": 0.98}


class TriageQueueTestCase(BrowserTestCase):
    @classmethod
    def setUpClass(cls):
        cls.saved_accepted = ACCEPTED.read_text(encoding="utf-8") if ACCEPTED.exists() else None
        cls.db = database_connection()
        with cls.db.cursor() as cur:
            candidates.ensure_schema(cur)
        cls.cleanup()
        super().setUpClass()
        with cls.db.cursor() as cur:
            automat = candidates.automat_id(cur, create=True)
            cur.execute("INSERT INTO User (username, name, email, password_hash) VALUES (%s, 'Carol E2E', %s, %s)",
                        (EDITOR, f"{EDITOR}@example.test", generate_password_hash(PASSWORD)))
            for n, title in enumerate(PROPOSED):
                triage = {"rule": "R4-tpg", "action": "propose", "note": "Technické pravidlo TPG.", "at": "2026-11-20T10:00:00",
                          "applied_action": "propose", "model": None}
                cur.execute("""INSERT INTO DocumentCandidate (candidate_key, source, title, document_type, url, language,
                                   jurisdikce, puvodce, scope_area, scope_areas, evidence_json, status, decision_note,
                                   proposed_by_user_id, proposed_at, triage_rule, triage_recommendation, triage_json)
                               VALUES (%s, 'cps-tpg', %s, 'Norma', 'https://example.test/tpg', 'CS', 'CZ',
                                   'Český plynárenský svaz (ČPS)', 4, '4', '{}', 'proposed', 'Automat (R4-tpg): TPG',
                                   %s, NOW(), 'R4-tpg', 'accept', %s)""",
                            (f"{PREFIX}{n}", title, automat, json.dumps(triage, ensure_ascii=False)))
            triage = {"rule": "R9-model", "action": "recommend", "note": "Model: přijmout.", "at": "2026-11-20T10:00:00",
                      "model": MODEL}
            cur.execute("""INSERT INTO DocumentCandidate (candidate_key, source, designation, title, document_type, url,
                               language, jurisdikce, evidence_json, cited_by, validity_status, triage_rule,
                               triage_recommendation, triage_confidence, triage_json)
                           VALUES (%s, 'citation', '9104/2099 Sb.', %s, 'Nezařazeno', 'https://example.test/m', 'CS', 'CZ',
                               '{}', 4, 'účinný', 'R9-model', 'accept', 0.9, %s)""",
                        (f"{PREFIX}rec", RECOMMENDED, json.dumps(triage, ensure_ascii=False)))

    @classmethod
    def cleanup(cls):
        with cls.db.cursor() as cur:
            cur.execute("SELECT id, document_id FROM DocumentCandidate WHERE candidate_key LIKE %s", (PREFIX + "%",))
            rows = cur.fetchall()
            for row in rows:
                cur.execute("DELETE FROM AuditLog WHERE table_name = 'DocumentCandidate' AND record_id = %s", (row["id"],))
                if row["document_id"]:
                    for table in ("DocumentKeyword", "DocumentVersion"):
                        cur.execute(f"DELETE FROM {table} WHERE document_id = %s", (row["document_id"],))
                    cur.execute("DELETE FROM AuditLog WHERE table_name = 'Document' AND record_id = %s", (row["document_id"],))
            cur.execute("DELETE FROM DocumentCandidate WHERE candidate_key LIKE %s", (PREFIX + "%",))
            for row in rows:
                if row["document_id"]:
                    cur.execute("DELETE FROM Document WHERE id = %s", (row["document_id"],))
            cur.execute("DELETE FROM DocumentSource WHERE name = 'Český plynárenský svaz (ČPS)' "
                        "AND id NOT IN (SELECT source_id FROM Document WHERE source_id IS NOT NULL)")
            cur.execute("DELETE FROM User WHERE username = %s", (EDITOR,))

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

    def login(self, page):
        self.goto(page, "/admin/login")
        page.fill("#username", EDITOR)
        page.fill("#password", PASSWORD)
        page.click("button[type=submit]")

    def row(self, page, title):
        return page.locator("table.candidate-table tbody tr", has_text=title)

    def test_automat_proposals_recommendation_and_bulk_confirmation(self):
        page = self.new_page()
        self.login(page)
        self.goto(page, "/admin/candidates?automat=navrhy&q=E2E+automat")
        for title in PROPOSED:
            self.assertEqual(self.row(page, title).count(), 1)
            self.assertTrue(self.row(page, title).locator(".automat-badge").is_visible())
        self.assertEqual(self.row(page, RECOMMENDED).count(), 0)
        self.shot(page, "01-automat-proposals")

        # the recommendation of the model, the form prefilled from it
        self.goto(page, "/admin/candidates?automat=doporuceni&doporuceni=accept&q=E2E+automat")
        self.assertTrue(self.row(page, RECOMMENDED).locator(".triage-accept").is_visible())
        self.row(page, RECOMMENDED).get_by_role("link", name="Otevřít").click()
        self.assertTrue(page.get_by_text("Doporučení automatu").is_visible())
        self.assertTrue(page.get_by_text("výdejní stojany plynů").is_visible())
        self.assertEqual(page.locator("#document_type").input_value(), "Vyhláška")
        self.assertEqual(page.locator("#puvodce").input_value(), "Ministerstvo průmyslu a obchodu")
        self.assertTrue(page.locator("input[name=scope_area][value='4']").is_checked())
        self.shot(page, "02-model-recommendation")

        # tick both proposals of the automat and confirm them at once
        self.goto(page, "/admin/candidates?automat=navrhy&q=E2E+automat")
        page.check("#pick-all")
        page.click("button:has-text('Potvrdit přijetí vybraných')")
        self.assertTrue(page.get_by_text("Hromadně potvrzeno přijetí: 2.").is_visible())
        self.goto(page, "/admin/candidates?stav=accepted&q=E2E+automat")
        for title in PROPOSED:
            self.assertEqual(self.row(page, title).count(), 1)
        self.shot(page, "03-bulk-confirmed")

    def test_phone_width(self):
        phone = self.new_page(PHONE)
        self.login(phone)
        for path in ("/admin/candidates", "/admin/candidates?automat=doporuceni&q=E2E+automat"):
            self.goto(phone, path)
            self.assertLessEqual(phone.evaluate("document.documentElement.scrollWidth"), PHONE["width"], path)
        self.shot(phone, "04-phone-list")
        self.row(phone, RECOMMENDED).get_by_role("link", name="Otevřít").click()
        self.assertLessEqual(phone.evaluate("document.documentElement.scrollWidth"), PHONE["width"])
        self.shot(phone, "05-phone-detail")
