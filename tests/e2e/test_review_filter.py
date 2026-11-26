"""Browser scenario: the editors' filter "Ke kontrole" in the catalogue
(parameter `kontrola`). A visitor does not see it, and the parameter changes
neither the list nor the exports; a logged-in editor narrows the list by the
reason of the review flag, combines it with the type filter, and exports the
narrowed list as a work list with the reasons.

The expected numbers come from SQL written here, independently of the
application. The editor account is a fixture created in, and removed from,
the TEST database; the base class refuses any other."""
import csv
import io
import json
import re

from werkzeug.security import generate_password_hash

from browser_case import BASE_URL, PHONE, BrowserTestCase, database_connection

PUBLIC = "NOT (COALESCE(d.jurisdikce, '') = 'SK' OR COALESCE(d.identifier, '') LIKE '%%[SK]')"
ACTS = ("SELECT COUNT(DISTINCT COALESCE(tr.to_document_id, d.id)) AS c FROM Document d "
        "LEFT JOIN document_relation tr ON tr.from_document_id = d.id AND tr.relation_type = 'TRANSLATION_OF' "
        f"WHERE {PUBLIC}")
LANGUAGE = "d.needs_review = 1 AND d.review_reason LIKE '%%jazyk dokumentu byl automaticky odhadnut%%'"
USERNAME, PASSWORD = "e2e_review_editor", "review-editor-e2e-password"
LABEL = "Ke kontrole"


class ReviewFilterTestCase(BrowserTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.db = database_connection()
        cls.cleanup()
        with cls.db.cursor() as cur:
            cur.execute("INSERT INTO User (username, name, email, password_hash) VALUES (%s, %s, %s, %s)",
                        (USERNAME, "Editor kontroly E2E", f"{USERNAME}@example.test",
                         generate_password_hash(PASSWORD)))

    @classmethod
    def cleanup(cls):
        with cls.db.cursor() as cur:
            cur.execute("DELETE FROM User WHERE username = %s", (USERNAME,))

    @classmethod
    def tearDownClass(cls):
        db = getattr(cls, "db", None)
        if db:
            cls.cleanup()
            db.close()
        super().tearDownClass()

    @classmethod
    def one(cls, sql, params=()):
        with cls.db.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()

    def count(self, page):
        return int(page.locator(".results-title .badge").inner_text())

    def login(self, page):
        self.goto(page, "/admin/login")
        page.fill("#username", USERNAME)
        page.fill("#password", PASSWORD)
        page.click("button[type=submit]")
        page.wait_for_url(lambda url: "/admin/login" not in url)

    def option_counts(self, page):
        """{value: count} read from the labels "Odhadnutý jazyk (50)"."""
        counts = {}
        for option in page.locator("select[name=kontrola] option").all():
            match = re.search(r"\((\d+)\)\s*$", option.inner_text())
            if match:
                counts[option.get_attribute("value")] = int(match.group(1))
        return counts

    def test_visitor_neither_sees_nor_uses_the_filter(self):
        page = self.new_page()
        self.goto(page, "/")
        everything = self.count(page)
        self.assertEqual(page.locator("select[name=kontrola]").count(), 0)
        self.assertEqual(page.get_by_text(LABEL, exact=True).count(), 0)
        self.goto(page, "/?kontrola=vse")
        self.assertEqual(self.count(page), everything)
        self.goto(page, "/?kontrola=jazyk&type_id=")
        self.assertEqual(self.count(page), everything)

        plain = json.loads(page.request.get(BASE_URL + "/export/json").text())
        forged = json.loads(page.request.get(BASE_URL + "/export/json?kontrola=jazyk").text())
        self.assertEqual(len(forged), len(plain))
        self.assertNotIn("review_reason", forged[0])
        self.assertNotIn("review_reason", page.request.get(BASE_URL + "/export/csv?kontrola=vse").text())
        self.assertNotIn("review_reason", page.request.get(BASE_URL + "/export/xml?kontrola=vse").text())

    def test_editor_filters_combines_and_exports(self):
        page = self.new_page()
        self.login(page)
        self.goto(page, "/")
        menu = page.get_by_label(LABEL)
        self.assertTrue(menu.is_visible())
        counts = self.option_counts(page)
        self.assertEqual(set(counts), {"vse", "oprava", "kontrola-zaznamu", "jazyk", "popis"})
        flagged = self.one(f"{ACTS} AND d.needs_review = 1")["c"]
        self.assertEqual(counts["vse"], flagged)
        self.assertEqual(counts["jazyk"], self.one(f"{ACTS} AND {LANGUAGE}")["c"])
        self.assertEqual(counts["kontrola-zaznamu"],
                         self.one(f"{ACTS} AND d.needs_review = 1 AND d.review_reason LIKE '%%Kontrola záznamů%%'")["c"])
        self.shot_element(page.locator(".search-glass-panel"), "editor-filters")

        menu.select_option("jazyk")
        page.wait_for_url(re.compile(r"kontrola=jazyk"))
        self.assertEqual(self.count(page), counts["jazyk"])
        self.assertEqual(page.get_by_label(LABEL).input_value(), "jazyk")
        self.shot(page, "editor-language", full_page=False)

        # combined with the type: the most frequent type among these documents
        top = self.one(f"SELECT d.type_id, COUNT(*) AS n FROM Document d WHERE {PUBLIC} AND {LANGUAGE} "
                       "AND d.type_id IS NOT NULL GROUP BY d.type_id ORDER BY n DESC LIMIT 1")
        page.locator("select[name=type_id]").select_option(str(top["type_id"]))
        page.wait_for_url(re.compile(r"type_id=\d+"))
        self.assertIn("kontrola=jazyk", page.url)
        expected = self.one(f"{ACTS} AND {LANGUAGE} AND d.type_id = %s", (top["type_id"],))["c"]
        self.assertEqual(self.count(page), expected)
        self.assertGreater(expected, 0)
        # the counts at the choices follow the other filters
        self.assertEqual(self.option_counts(page)["jazyk"], expected)

        # the export of the narrowed list is the editor's work list
        href = page.locator("a.btn-secondary", has_text="JSON").get_attribute("href")
        self.assertIn("kontrola=jazyk", href)
        rows = json.loads(page.request.get(BASE_URL + "/export/json?kontrola=jazyk").text())
        self.assertEqual(len(rows), self.one(f"SELECT COUNT(*) AS c FROM Document d WHERE {PUBLIC} AND {LANGUAGE}")["c"])
        self.assertTrue(rows)
        for row in rows:
            self.assertIn("jazyk dokumentu byl automaticky odhadnut", row["review_reason"])
            self.assertIn("/dokument/", row["record_url"])
        table = list(csv.DictReader(io.StringIO(page.request.get(BASE_URL + "/export/csv?kontrola=oprava").text())))
        self.assertEqual(len(table), self.one(
            f"SELECT COUNT(*) AS c FROM Document d WHERE {PUBLIC} AND d.needs_review = 1 AND "
            "(d.review_reason LIKE '%%useknutý fragment%%' OR d.review_reason LIKE '%%není platné označení%%' "
            "OR d.review_reason LIKE '%%autoritativní gestor%%')")["c"])
        self.assertIn("review_reason", table[0] if table else {"review_reason": ""})
        self.assertIn("<review_reason>", page.request.get(BASE_URL + "/export/xml?kontrola=popis").text())

        # paging keeps the filter
        self.goto(page, "/?kontrola=popis")
        self.assertEqual(self.count(page), counts["popis"])
        if page.locator("a.page-nav[rel=next]").count():
            self.assertIn("kontrola=popis", page.locator("a.page-nav[rel=next]").get_attribute("href"))

    def test_phone(self):
        page = self.new_page(PHONE)
        self.login(page)
        self.goto(page, "/?kontrola=kontrola-zaznamu")
        overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        self.shot_element(page.locator(".search-glass-panel"), "editor-filters-phone")
        self.shot(page, "editor-records-phone", full_page=False)
        self.assertLessEqual(overflow, 1, "the page is wider than the phone screen")
        self.assertTrue(page.get_by_label(LABEL).is_visible())
