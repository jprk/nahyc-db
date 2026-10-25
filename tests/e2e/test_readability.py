"""Browser scenario: every link on the main pages is readable on the dark
background (the browser's default link blue, #0000EE, is not — found on the
permalink of an expanded catalogue row)."""
from browser_case import BrowserTestCase, database_connection

LINK_COLOURS = """
() => {
    const channel = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    const parse = css => (css.match(/[\\d.]+/g) || []).map(Number);
    const luminance = ([r, g, b]) => 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
    const background = luminance(parse(getComputedStyle(document.body).backgroundColor).slice(0, 3));
    const result = [];
    for (const a of document.querySelectorAll('a')) {
        const box = a.getBoundingClientRect();
        const style = getComputedStyle(a);
        const hasOwnBackground = !['rgba(0, 0, 0, 0)', 'transparent'].includes(style.backgroundColor);
        if (!box.width || !box.height || a.querySelector('img') || hasOwnBackground || !a.textContent.trim()) continue;
        const text = luminance(parse(style.color).slice(0, 3));
        const ratio = (Math.max(text, background) + 0.05) / (Math.min(text, background) + 0.05);
        result.push({text: a.textContent.trim().slice(0, 40), colour: style.color, ratio});
    }
    return result;
}
"""


class LinkReadabilityTestCase(BrowserTestCase):
    MINIMUM_RATIO = 3.0  # WCAG AA for large or UI text; body-size links use 4.5 in practice

    def check(self, page, where):
        unreadable = [(l["text"], l["colour"], round(l["ratio"], 1)) for l in page.evaluate(LINK_COLOURS)
                      if l["ratio"] < self.MINIMUM_RATIO]
        self.assertEqual(unreadable, [], f"links hard to read on {where}")

    def test_links_on_the_main_pages(self):
        page = self.new_page()
        self.goto(page, "/")
        page.locator(".document-row .row-visible").first.click()  # the permalink is in the details
        self.check(page, "the catalogue")
        self.goto(page, "/procesy")
        self.check(page, "the process overview")
        page.locator(".process-node-card").first.click()
        self.check(page, "a process node")
        self.goto(page, "/admin/login")
        self.check(page, "the login page")

    def test_links_on_a_document_page_with_relations(self):
        db = database_connection()
        try:
            with db.cursor() as cur:
                cur.execute("""SELECT d.slug FROM Document d JOIN document_relation r
                               ON r.from_document_id = d.id ORDER BY d.id LIMIT 1""")
                row = cur.fetchone()
        finally:
            db.close()
        if not row:
            self.skipTest("no document with relations in this database")
        page = self.new_page()
        self.goto(page, f"/dokument/{row['slug']}")
        self.check(page, "a document page with relations")
        self.shot(page, "document-with-relations")


if __name__ == "__main__":
    import unittest
    unittest.main()
