"""Browser scenarios: the process view — the overview of the seven nodes and
one node's detail page."""
import re
import unittest

from browser_case import BrowserTestCase


class ProcessViewTestCase(BrowserTestCase):
    def test_overview_shows_the_seven_nodes_and_the_variability_matrix(self):
        page = self.new_page()
        self.goto(page, "/procesy")
        self.assertEqual(page.locator(".process-node-card").count(), 7)
        self.assertGreaterEqual(page.locator("table.doc-table tbody tr").count(), 7)
        self.shot(page, "overview")

    def test_a_node_opens_with_its_sections(self):
        page = self.new_page()
        self.goto(page, "/procesy")
        name = page.locator(".process-node-card h2").first.inner_text().strip()
        page.locator(".process-node-card").first.click()
        page.wait_for_url(re.compile(r"/proces/"))
        self.assertEqual(page.locator("h1.doc-heading").inner_text().strip(), name)
        for section in ("Účel a role procesu", "Průběh procesu", "Vstupy procesu"):
            self.assertTrue(page.get_by_role("heading", name=re.compile(section)).first.is_visible(), section)
        self.shot(page, "node")

    # KNOWN DEFECT, same cause as in test_catalog.py: the header overflows at 390 px.
    @unittest.expectedFailure
    def test_phone_layout_does_not_scroll_sideways(self):
        from browser_case import PHONE
        page = self.new_page(PHONE)
        self.goto(page, "/procesy")
        overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        self.shot(page, "overview-phone")
        self.assertLessEqual(overflow, 1, "the page is wider than the phone screen")


if __name__ == "__main__":
    unittest.main()
