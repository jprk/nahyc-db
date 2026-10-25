"""Browser scenarios: reading a document's text inside the application
(GitHub issue #2) — the EU regulation 2022/869 (record 80) and a Czech act —
and the access rules around it. The runner extracts the clean texts before
the server starts, so these pages exist whenever the downloaded originals do."""
import re

from browser_case import BASE_URL, PHONE, BrowserTestCase, database_connection


class FulltextPageTestCase(BrowserTestCase):
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

    def open_text(self, page, slug):
        """Opens the document page and follows 'Číst text'; skips when this
        machine has no extracted text for it."""
        self.goto(page, f"/dokument/{slug}")
        link = page.get_by_role("link", name="Číst text")
        if link.count() == 0:
            self.skipTest(f"no extracted text for {slug} on this machine")
        link.click()
        page.wait_for_url(re.compile(r"/text$"))

    def test_eu_regulation_2022_869_reads_as_numbered_paragraphs(self):
        page = self.new_page()
        self.open_text(page, "eu-2022-869")
        self.assertIn("2022/869", page.locator("h1.doc-heading").inner_text())
        self.assertTrue(page.get_by_text("závazné znění je vždy na").is_visible())
        article = page.locator("article.fulltext")
        self.assertGreater(article.locator("p.item").count(), 100, "recitals and articles are item paragraphs")
        self.assertEqual(article.locator("table.layout td:first-child:has-text('(1)')").count(), 0,
                         "numbered points are not left as one-row tables")
        for foreign in ("script", "a", "img", "iframe"):
            self.assertEqual(article.locator(foreign).count(), 0, f"<{foreign}> inside the text")
        self.shot(page, "eu-2022-869-top", full_page=False)
        item = article.locator("p.item").first
        item.scroll_into_view_if_needed()
        self.shot(page, "eu-2022-869-recitals", full_page=False)

    def test_czech_act_keeps_its_headings_and_levels(self):
        slug = "183-2006-sb"
        if not self.one(f"SELECT 1 AS x FROM Document WHERE slug='{slug}'"):
            self.skipTest(f"{slug} is not in this database")
        page = self.new_page()
        self.open_text(page, slug)
        article = page.locator("article.fulltext")
        self.assertGreater(article.locator("h3").count(), 10)
        self.assertGreater(article.locator("p.l2").count(), 10)
        self.shot(page, "czech-act-top", full_page=False)

    def test_slovak_act_from_slov_lex_reads_with_parts_paragraphs_and_items(self):
        slug = "124-2000-z-z"
        if not self.one(f"SELECT 1 AS x FROM Document WHERE slug='{slug}'"):
            self.skipTest(f"{slug} is not in this database")
        page = self.new_page()
        self.open_text(page, slug)
        article = page.locator("article.fulltext")
        self.assertIn("124/2000", page.locator("p.doc-designation").inner_text())
        self.assertGreater(article.locator("p.item.d0").count(), 100, "odseky are item paragraphs")
        self.assertGreater(article.locator("p.item.d1").count(), 10, "pismena are one level deeper")
        self.assertGreater(article.locator("p.para").count(), 20, "every paragraf has its section sign")
        self.assertGreater(article.locator("h4").count(), 0, "a paragraf title is a heading")
        for foreign in ("script", "a", "img", "iframe"):
            self.assertEqual(article.locator(foreign).count(), 0, f"<{foreign}> inside the text")
        self.shot(page, "slovak-act-top", full_page=False)

    def test_document_whose_file_is_a_pdf_reads_from_the_html_of_the_same_act(self):
        with self.db.cursor() as cur:
            cur.execute("""SELECT d.slug FROM Document d JOIN DocumentType dt ON dt.id=d.type_id
                           WHERE d.file_path LIKE '%.pdf' AND dt.restricted_fulltext=0 ORDER BY d.id""")
            rows = [r["slug"] for r in cur.fetchall()]
        page = self.new_page()
        for slug in rows:
            self.goto(page, f"/dokument/{slug}")
            if page.get_by_role("link", name="Číst text").count():
                break
        else:
            self.skipTest("no PDF-based document has an extracted text on this machine")
        # the document still offers its PDF original, and the text view next to it
        self.assertTrue(page.get_by_role("link", name="Stažená kopie").is_visible())
        page.get_by_role("link", name="Číst text").click()
        page.wait_for_url(re.compile(r"/text$"))
        article = page.locator("article.fulltext")
        self.assertGreater(article.locator("p").count(), 20)
        for foreign in ("script", "a", "img", "iframe"):
            self.assertEqual(article.locator(foreign).count(), 0, f"<{foreign}> inside the text")
        self.shot(page, "pdf-document-text", full_page=False)

    def test_text_page_fits_a_phone(self):
        page = self.new_page(PHONE)
        self.open_text(page, "eu-2022-869")
        overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        self.shot(page, "eu-2022-869-phone", full_page=False)
        self.assertLessEqual(overflow, 1, "the text page scrolls sideways on a phone")

    def test_paid_standard_has_no_text_page(self):
        document = self.one("""SELECT d.slug FROM Document d JOIN DocumentType dt ON dt.id=d.type_id
                               WHERE d.file_path IS NOT NULL AND dt.restricted_fulltext=1 ORDER BY d.id LIMIT 1""")
        if not document:
            self.skipTest("no restricted document with a downloaded copy")
        page = self.new_page()
        self.expect_status(f"/dokument/{document['slug']}/text", 403)
        self.assertEqual(self.goto(page, f"/dokument/{document['slug']}/text").status, 403)

    def test_raw_download_is_an_attachment_under_a_sandbox_policy(self):
        document = self.one("""SELECT d.id FROM Document d JOIN DocumentType dt ON dt.id=d.type_id
                               WHERE d.file_path LIKE '%.html' AND dt.restricted_fulltext=0 ORDER BY d.id LIMIT 1""")
        page = self.new_page()
        response = page.request.get(f"{BASE_URL}/fulltext/{document['id']}")
        if response.status == 404:
            self.skipTest("the downloaded original is not on this machine")
        self.assertEqual(response.status, 200)
        self.assertTrue(response.headers["content-disposition"].startswith("attachment"))
        self.assertIn("sandbox", response.headers["content-security-policy"])


if __name__ == "__main__":
    import unittest
    unittest.main()
