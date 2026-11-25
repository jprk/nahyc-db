"""Browser scenario of the areas of the catalogue (doc/OBLASTI.md): the filter
"Oblast" offers a few dozen Czech areas instead of the source categories, choosing
one narrows the list to documents tagged with it, and the document page shows the
areas, not the German/Slovak categories of the source surveys. run_tests.py writes the areas to
the test database (assign_areas.py among TEST_DB_MIGRATIONS)."""
import re

from browser_case import PHONE, BrowserTestCase, database_connection

AREA = "Ochrana před výbuchem"


class AreasTestCase(BrowserTestCase):
    def test_filter_offers_the_areas(self):
        for viewport, name in ((None, "desktop"), (PHONE, "phone")):
            page = self.new_page(viewport)
            self.goto(page, "/")
            options = page.locator("select[name=oblast] option").all_inner_texts()
            self.assertTrue(20 <= len(options) - 1 <= 40, options)
            self.assertFalse([o for o in options if re.search(r"Explosionsschutz|STN|Norm \(", o)], options)
            self.assertEqual(page.locator("select[name=category_id]").count(), 0)
            self.assertNotIn("Oblast dosud neurčena", options, "the editors' worklist is not a public area")
            page.select_option("select[name=oblast]", label=AREA)
            page.wait_for_url(re.compile(r"[?&]oblast=vybuch"))
            count = int(page.locator(".results-title .badge").inner_text())
            self.assertGreater(count, 10)
            rows = page.locator(".document-row")
            for i in range(min(rows.count(), 10)):
                self.assertIn(AREA, rows.nth(i).locator(".keyword-tag").all_inner_texts())
            self.shot(page, f"areas-filter-{name}", full_page=False)
            self.shot_element(page.locator(".filters-grid"), f"areas-filter-box-{name}")
            page.close()

    def test_document_page_shows_areas(self):
        for viewport, name in ((None, "desktop"), (PHONE, "phone")):
            page = self.new_page(viewport)
            self.goto(page, "/dokument/iso-19885-2")
            tags = page.locator(".keyword-tag").all_inner_texts()
            self.assertIn("Plnicí stanice", tags)
            self.assertFalse([t for t in tags if t in ("Befüllungsanlagen", "Produktzertifizierung")], tags)
            self.shot(page, f"areas-document-{name}", full_page=False)
            page.close()

    def test_source_categories_still_searchable(self):
        page = self.new_page()
        self.goto(page, "/?q=Befüllungsanlagen")
        self.assertGreater(int(page.locator(".results-title .badge").inner_text()), 0)

    def test_old_keyword_link_still_works(self):
        """src/tools/migrate_vocabulary.py renamed Keyword to SourceCategory with the same ids:
        an old link `?keyword_id=N` is redirected to `?category_id=N` and filters the same documents."""
        conn = database_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT c.id, COUNT(*) AS n FROM SourceCategory c JOIN DocumentSourceCategory dc "
                            "ON dc.category_id = c.id WHERE c.name = 'Befüllungsanlagen' GROUP BY c.id")
                row = cur.fetchone()
        finally:
            conn.close()
        self.assertIsNotNone(row)
        page = self.new_page()
        self.goto(page, f"/?keyword_id={row['id']}")
        self.assertRegex(page.url, rf"[?&]category_id={row['id']}\b")
        self.assertNotIn("keyword_id", page.url)
        count = int(page.locator(".results-title .badge").inner_text())
        self.assertGreater(count, 0)
        self.assertLessEqual(count, row["n"])
