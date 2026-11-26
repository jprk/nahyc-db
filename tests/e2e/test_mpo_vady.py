"""Browser scenarios of the defects found on the web on 21. 11. 2026
(doc/MPO_OVERENI_WEBU.md): Z1, the home page counted documents in preparation as
historical; Z2, on a phone the magnifier icon was drawn below the search field.
The data defects Z3–Z5 are covered by tests/test_mpo_vady.py (the test database
is a copy of the live one, where their fixes are written only after the merge)."""
import re

from browser_case import PHONE, BrowserTestCase, database_connection


class MpoDefectsTestCase(BrowserTestCase):
    def test_z1_hero_note_separates_documents_in_preparation(self):
        page = self.new_page()
        self.goto(page, "/")
        note = page.locator(".hero-note").inner_text()
        m = re.search(r"Z toho (\d+) aktuálně platných, (\d+) připravovaných a (\d+) historických "
                      r"\(zrušených nebo nahrazených\)", note)
        self.assertIsNotNone(m, note)
        active, upcoming, historical = (int(g) for g in m.groups())
        total = int(page.locator(".results-title .badge").inner_text())
        self.assertEqual(active + upcoming + historical, total)
        db = database_connection()
        try:
            with db.cursor() as cur:
                cur.execute("SELECT COUNT(DISTINCT d.id) AS c FROM Document d JOIN DocumentVersion dv "
                            "ON dv.document_id = d.id AND dv.is_current = 1 "
                            "WHERE dv.lifecycle_state IN ('draft', 'promulgated')")
                any_upcoming = cur.fetchone()["c"]
        finally:
            db.close()
        if any_upcoming:
            self.assertGreater(upcoming, 0)
        self.shot(page, "z1-hero-note", full_page=False)

    def test_z2_magnifier_inside_the_search_field_on_a_phone(self):
        for viewport in (PHONE, None):
            page = self.new_page(viewport)
            self.goto(page, "/")
            icon = page.locator(".search-icon").bounding_box()
            field = page.locator("input.search-input").bounding_box()
            self.assertIsNotNone(icon)
            centre_y = icon["y"] + icon["height"] / 2
            self.assertTrue(field["y"] < centre_y < field["y"] + field["height"],
                            f"icon {icon} outside the field {field}")
            self.assertTrue(field["x"] <= icon["x"] < field["x"] + 60, f"icon {icon}, field {field}")
            self.shot(page, f"z2-search-{'phone' if viewport else 'desktop'}", full_page=False)
            page.close()
