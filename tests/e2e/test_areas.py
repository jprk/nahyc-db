"""Browser scenario of the areas of the catalogue (doc/OBLASTI.md): the filter
"Oblast" offers a few dozen Czech areas instead of the source keywords, choosing
one narrows the list to documents tagged with it, and the document page shows the
areas, not the original German/Slovak keywords. run_tests.py writes the areas to
the test database (assign_areas.py among TEST_DB_MIGRATIONS)."""
import re

from browser_case import PHONE, BrowserTestCase

AREA = "Ochrana před výbuchem"


class AreasTestCase(BrowserTestCase):
    def test_filter_offers_the_areas(self):
        for viewport, name in ((None, "desktop"), (PHONE, "phone")):
            page = self.new_page(viewport)
            self.goto(page, "/")
            options = page.locator("select[name=oblast] option").all_inner_texts()
            self.assertTrue(20 <= len(options) - 1 <= 40, options)
            self.assertFalse([o for o in options if re.search(r"Explosionsschutz|STN|Norm \(", o)], options)
            self.assertEqual(page.locator("select[name=keyword_id]").count(), 0)
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
            self.assertIn("Plnicí stanice a infrastruktura paliv", tags)
            self.assertFalse([t for t in tags if t in ("Befüllungsanlagen", "Produktzertifizierung")], tags)
            self.shot(page, f"areas-document-{name}", full_page=False)
            page.close()

    def test_original_keywords_still_searchable(self):
        page = self.new_page()
        self.goto(page, "/?q=Befüllungsanlagen")
        self.assertGreater(int(page.locator(".results-title .badge").inner_text()), 0)
