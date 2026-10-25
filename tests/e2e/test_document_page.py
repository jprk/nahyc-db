"""Browser scenarios: the per-document page — one ordinary document, the EU
regulation 2022/869 (record 80 of the main database), and the access rules
for paid standards."""
from browser_case import BASE_URL, BrowserTestCase, database_connection


class DocumentPageTestCase(BrowserTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.db = database_connection()

    @classmethod
    def tearDownClass(cls):
        db = getattr(cls, "db", None)
        if db:
            db.close()
        super().tearDownClass()

    def one(self, sql):
        with self.db.cursor() as cur:
            cur.execute(sql)
            return cur.fetchone()

    def test_the_page_matches_the_row_it_was_opened_from(self):
        page = self.new_page()
        self.goto(page, "/")
        row = page.locator(".document-row").first
        title = row.locator(".doc-title").inner_text().strip()
        row.locator(".row-visible").click()
        row.get_by_text("Detail záznamu").click()
        page.wait_for_url(lambda url: "/dokument/" in url)
        self.assertEqual(page.locator("h1.doc-heading").inner_text().strip(), title)
        self.assertGreaterEqual(page.locator(".doc-panel").count(), 1)
        self.assertTrue(page.get_by_text("Zpět na katalog").is_visible())
        self.shot(page, "document")

    def test_eu_regulation_2022_869(self):
        document = self.one("SELECT slug, title FROM Document WHERE slug='eu-2022-869'")
        if not document:
            self.skipTest("eu-2022-869 is not in this database")
        page = self.new_page()
        self.goto(page, "/dokument/eu-2022-869")
        self.assertIn("2022/869", page.locator("h1.doc-heading").inner_text())
        self.assertTrue(page.get_by_text("Přejít na zdroj").is_visible())
        self.shot(page, "eu-2022-869")

    def test_open_document_offers_its_downloaded_copy(self):
        document = self.one("""SELECT d.slug, d.id FROM Document d JOIN DocumentType dt ON dt.id=d.type_id
                               WHERE d.file_path IS NOT NULL AND dt.restricted_fulltext=0 ORDER BY d.id LIMIT 1""")
        if not document:
            self.skipTest("no open document with a downloaded copy")
        page = self.new_page()
        self.goto(page, f"/dokument/{document['slug']}")
        link = page.get_by_role("link", name="Stažená kopie")
        self.assertTrue(link.is_visible())
        self.assertEqual(page.request.get(BASE_URL + link.get_attribute("href")).status, 200)
        self.shot(page, "document-with-copy")

    def test_paid_standard_shows_no_download_and_the_file_is_forbidden(self):
        document = self.one("""SELECT d.slug, d.id FROM Document d JOIN DocumentType dt ON dt.id=d.type_id
                               WHERE d.file_path IS NOT NULL AND dt.restricted_fulltext=1 ORDER BY d.id LIMIT 1""")
        if not document:
            self.skipTest("no restricted document with a downloaded copy")
        page = self.new_page()
        self.goto(page, f"/dokument/{document['slug']}")
        self.assertTrue(page.get_by_text("Plný text nedostupný").is_visible())
        self.assertEqual(page.get_by_role("link", name="Stažená kopie").count(), 0)
        self.assertEqual(page.request.get(f"{BASE_URL}/fulltext/{document['id']}").status, 403)
        self.shot(page, "document-restricted")

    def test_unknown_document_is_a_clean_404(self):
        page = self.new_page()
        self.expect_status("/dokument/neexistuje", 404)
        self.assertEqual(self.goto(page, "/dokument/neexistuje").status, 404)


if __name__ == "__main__":
    import unittest
    unittest.main()
