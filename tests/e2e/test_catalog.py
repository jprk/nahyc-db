"""Browser scenarios: the catalogue page — listing, search, filter,
expanding a row, pagination, and the phone layout."""
import re
import unittest

from browser_case import PHONE, BrowserTestCase


class CatalogTestCase(BrowserTestCase):
    def count(self, page):
        return int(page.locator(".results-title .badge").inner_text())

    def test_index_lists_documents_and_shows_the_totals(self):
        page = self.new_page()
        self.goto(page, "/")
        self.assertIn("Katalog", page.title())
        self.assertGreater(page.locator(".document-row").count(), 10)
        total = self.count(page)
        self.assertRegex(page.locator(".hero-subtitle").inner_text(), rf"\b{total}\b")
        self.shot(page, "index-desktop")

    def test_search_narrows_the_result_list(self):
        page = self.new_page()
        self.goto(page, "/")
        everything = self.count(page)
        page.fill("input[name=q]", "vodík")
        page.press("input[name=q]", "Enter")
        page.wait_for_url(re.compile(r"[?&]q="))
        found = self.count(page)
        self.assertTrue(0 < found < everything, f"{found} of {everything}")
        self.shot(page, "search-vodik")

    def test_search_without_a_match_says_so_instead_of_breaking(self):
        page = self.new_page()
        self.goto(page, "/?q=zzzneexistujicidokumentzzz")
        self.assertEqual(self.count(page), 0)
        self.assertEqual(page.locator(".document-row").count(), 0)
        self.shot(page, "search-empty")

    def test_type_filter_keeps_only_that_type(self):
        page = self.new_page()
        self.goto(page, "/")
        select = page.locator("select[name=type_id]")
        label = select.locator("option:not([value=''])").first.inner_text().strip()
        everything = self.count(page)
        select.select_option(label=label)
        page.wait_for_url(re.compile(r"type_id=\d+"))
        self.assertLessEqual(self.count(page), everything)
        types = {t.strip() for t in page.locator(".document-row .type-tag").all_inner_texts()}
        self.assertEqual(types, {label})
        self.shot(page, "filter-type")

    def test_clicking_a_row_expands_its_details(self):
        page = self.new_page()
        self.goto(page, "/")
        row = page.locator(".document-row").first
        self.assertNotIn("expanded", row.get_attribute("class"))
        row.locator(".row-visible").click()
        self.assertIn("expanded", row.get_attribute("class"))
        self.assertTrue(row.locator(".row-details").is_visible())
        self.assertTrue(row.get_by_text("Detail záznamu").is_visible())
        self.shot_element(row, "row-expanded")

    def test_next_page_shows_other_documents(self):
        page = self.new_page()
        self.goto(page, "/")
        if page.locator("a.page-nav[rel=next]").count() == 0:
            self.skipTest("the result list fits on one page")
        first = page.locator(".document-row .doc-title").first.inner_text()
        page.click("a.page-nav[rel=next]")
        page.wait_for_url(re.compile(r"page=2"))
        self.assertNotEqual(page.locator(".document-row .doc-title").first.inner_text(), first)
        self.shot(page, "page-2", full_page=False)

    # KNOWN DEFECT (found by this scenario, 2026-10-25, R2.2): at 390 px the
    # header (logo, four links, funder logo) does not wrap or collapse, so the
    # page is 616 px wide and scrolls sideways; the logo text wraps over three
    # lines on top of the links. Remove the decorator when the header is fixed —
    # the run will report an "unexpected success" to remind whoever does it.
    @unittest.expectedFailure
    def test_phone_layout_does_not_scroll_sideways(self):
        page = self.new_page(PHONE)
        self.goto(page, "/")
        overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        self.shot(page, "index-phone")
        self.assertLessEqual(overflow, 1, "the page is wider than the phone screen")


if __name__ == "__main__":
    unittest.main()
