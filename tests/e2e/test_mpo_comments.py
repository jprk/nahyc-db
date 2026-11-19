"""Browser scenarios: the comments of the Ministry of Industry and Trade (MPO) on
result V01 (doc/MPO_PRIPOMINKY.md, odstavec 2), each replayed as the ministry
would have met it — duplicates in the result list, missing delegated acts,
abbreviated and misassigned originators, a stale note and internal notes in
public descriptions. The test database is a copy of the live one, where the
data fixes of krok 0 are written; krok 2 added the interface changes."""
import re

from browser_case import BASE_URL, PHONE, BrowserTestCase, database_connection

STALE_NOTE = "Stav ke dni 30.6.2025"


class MpoCommentsTestCase(BrowserTestCase):
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

    def all(self, sql, params=()):
        with self.db.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()

    def one(self, sql, params=()):
        rows = self.all(sql, params)
        return rows[0] if rows else None

    def count(self, page):
        return int(page.locator(".results-title .badge").inner_text())

    def row_identifiers(self, page):
        return [r.get_attribute("data-identifier") for r in page.locator(".document-row").all()]

    def assert_one_row_per_act(self, page):
        identifiers = [i for i in self.row_identifiers(page) if i]
        self.assertEqual(len(identifiers), len(set(identifiers)), f"duplicate rows: {identifiers}")
        self.assertEqual([i for i in identifiers if i.endswith("[EN]")], [],
                         "an English variant has its own row")
        if page.locator("a.page-nav[rel=next]").count() == 0:
            self.assertEqual(self.count(page), page.locator(".document-row").count())

    # připomínka 1 -------------------------------------------------------------
    def test_ecb_originator_no_longer_returns_duplicates(self):
        page = self.new_page()
        self.goto(page, "/")
        options = [o.strip() for o in page.locator("select[name=source_id] option").all_inner_texts()]
        ecb = self.one("SELECT id FROM DocumentSource WHERE name = 'Evropská centrální banka'")
        if ecb:
            self.goto(page, f"/?source_id={ecb['id']}")
            self.assert_one_row_per_act(page)
            if self.count(page) == 0:
                # the only ECB decision (2018/546) is out of scope since krok 0,
                # and an originator without documents is not offered at all
                self.assertNotIn("Evropská centrální banka", options)
        self.shot(page, "ecb-originator")
        self.goto(page, "/?q=2018%2F546")
        self.assert_one_row_per_act(page)
        self.assertLessEqual(self.count(page), 1)

    # připomínka 2 + 3 ---------------------------------------------------------
    def test_rfnbo_returns_one_row_per_act_and_the_delegated_acts(self):
        page = self.new_page()
        self.goto(page, "/")
        page.fill("input[name=q]", "RFNBO")
        page.press("input[name=q]", "Enter")
        page.wait_for_url(re.compile(r"[?&]q=RFNBO"))
        self.assert_one_row_per_act(page)
        identifiers = self.row_identifiers(page)
        for wanted in ("(EU) 2023/1184", "(EU) 2023/1185", "(EU) 2023/2413"):
            self.assertIn(wanted, identifiers)
        self.assertIn("RFNBO", page.locator(".synonym-note").inner_text())
        delegated = page.locator('.document-row[data-identifier="(EU) 2023/1185"] .subtype-tag')
        self.assertEqual(delegated.inner_text().strip(), "Akt v přenesené pravomoci (EU)")
        self.shot(page, "rfnbo")

        red3 = page.locator('.document-row[data-identifier="(EU) 2023/2413"]')
        chips = [c.strip() for c in red3.locator(".lang-chip").all_inner_texts()]
        self.assertEqual(chips, ["CS", "EN"])
        self.shot_element(red3, "rfnbo-red3-row")
        red3.locator(".lang-chip", has_text="EN").click()
        page.wait_for_url(lambda url: "/dokument/" in url)
        self.assertIn("[EN]", page.locator(".doc-meta").inner_text())
        self.shot(page, "rfnbo-red3-english", full_page=False)

    def test_type_menu_offers_delegated_acts(self):
        page = self.new_page()
        self.goto(page, "/")
        select = page.locator("select[name=type_id]")
        labels = [o.strip() for o in select.locator("option").all_inner_texts()]
        self.assertIn("Akt v přenesené pravomoci (EU)", labels)
        self.assertIn("Prováděcí akt (EU)", labels)
        select.select_option(label="Akt v přenesené pravomoci (EU)")
        page.wait_for_url(re.compile(r"type_id=podtyp-delegated"))
        self.assert_one_row_per_act(page)
        identifiers = self.row_identifiers(page)
        for wanted in ("(EU) 2023/1184", "(EU) 2023/1185", "(EU) 2018/674", "(EU) 2019/1745", "(EU) 2025/656"):
            self.assertIn(wanted, identifiers)
        tags = {t.strip() for t in page.locator(".document-row .subtype-tag").all_inner_texts()}
        self.assertEqual(tags, {"Akt v přenesené pravomoci (EU)"})
        self.assertEqual(page.locator(".document-row .subtype-tag").count(), page.locator(".document-row").count())
        self.shot(page, "filter-delegated")

    # připomínka 4 -------------------------------------------------------------
    def test_originator_menu_is_grouped_and_has_no_abbreviations(self):
        page = self.new_page()
        self.goto(page, "/")
        select = page.locator("select[name=source_id]")
        options = [o.strip() for o in select.locator("option").all_inner_texts()]
        self.assertIn("Ministerstvo dopravy", options)
        self.assertNotIn("MD", options)
        # the abbreviations of Czech ministries the spreadsheets used (DNV, by
        # contrast, is the real name of that company)
        ministries = {"MD", "MPO", "MŽP", "MMR", "MPSV", "MV", "MF", "MZ", "MZe", "MZd"}
        self.assertEqual([o for o in options if o in ministries], [],
                         "a ministry abbreviation in the originator menu")
        groups = [g.get_attribute("label") for g in select.locator("optgroup").all()]
        for wanted in ("Česká republika", "Evropská unie", "Mezinárodní organizace",
                       "Normalizační a odborné organizace"):
            self.assertIn(wanted, groups)
        czech = select.locator('optgroup[label="Česká republika"] option').all_inner_texts()
        self.assertIn("Ministerstvo dopravy", [o.strip() for o in czech])
        self.assertTrue(all(o.strip().startswith("Ministerstvo") for o in czech), czech)
        self.shot_element(page.locator(".search-glass-panel"), "filters")

    def test_jurisdiction_filter(self):
        # Slovak documents and the choice "Slovensko" are for logged-in editors
        # only (tests/e2e/test_slovak_documents.py).
        page = self.new_page()
        self.goto(page, "/")
        select = page.locator("select[name=jurisdikce]")
        labels = [o.strip() for o in select.locator("option").all_inner_texts()]
        self.assertNotIn("Slovensko", labels)
        select.select_option(label="Česká republika")
        page.wait_for_url(re.compile(r"jurisdikce=cz"))
        expected = self.one("""SELECT COUNT(*) AS c FROM Document d WHERE d.jurisdikce = 'CZ' AND NOT EXISTS
            (SELECT 1 FROM document_relation r WHERE r.from_document_id = d.id
             AND r.relation_type = 'TRANSLATION_OF')""")["c"]
        self.assertEqual(self.count(page), expected)
        self.assert_one_row_per_act(page)
        self.shot(page, "jurisdiction-cz")

    # připomínka 5 -------------------------------------------------------------
    def test_railway_act_belongs_to_the_ministry_of_transport(self):
        page = self.new_page()
        self.goto(page, "/?q=dr%C3%A1h%C3%A1ch")
        for identifier in ("266/1994 Sb.", "426/2021 Sb."):
            row = page.locator(f'.document-row[data-identifier="{identifier}"]')
            self.assertEqual(row.count(), 1, identifier)
            self.assertEqual(row.locator(".source-text").inner_text().strip(), "Ministerstvo dopravy")
        self.shot(page, "railway-act")
        slug = self.one("SELECT slug FROM Document WHERE identifier = '266/1994 Sb.'")["slug"]
        self.goto(page, f"/dokument/{slug}")
        self.assertIn("Ministerstvo dopravy", page.locator(".doc-meta").inner_text())
        self.assertNotIn("Ministerstvo průmyslu", page.locator(".doc-meta").inner_text())
        self.shot(page, "railway-act-page", full_page=False)

    # připomínka 6 -------------------------------------------------------------
    def test_energy_act_and_red3_pages_have_no_stale_note(self):
        page = self.new_page()
        rows = self.all("""SELECT d.slug, d.identifier FROM Document d
            WHERE d.identifier IN ('458/2000 Sb.', '(EU) 2023/2413', '(EU) 2023/2413 [EN]')""")
        self.assertGreaterEqual(len(rows), 2)
        for row in rows:
            self.goto(page, f"/dokument/{row['slug']}")
            text = page.locator("body").inner_text()
            self.assertNotIn(STALE_NOTE, text, row["identifier"])
            self.assertNotIn("čeká se na podpis", text, row["identifier"])
            self.shot(page, "stale-note-" + row["slug"], full_page=False)
        self.goto(page, "/?q=Stav+ke+dni+30.6.2025")
        self.assertEqual(self.count(page), 0)

    # připomínka 6, obecně ----------------------------------------------------
    def test_no_public_description_mentions_the_development_log(self):
        leaked = self.one("""SELECT COUNT(*) AS c FROM Document WHERE description LIKE '%%doc/PLAN.md%%'
            OR popis_priblizny LIKE '%%doc/PLAN.md%%' OR title LIKE '%%doc/PLAN.md%%'""")["c"]
        self.assertEqual(leaked, 0)
        page = self.new_page()
        self.goto(page, "/?q=doc%2FPLAN.md")
        self.assertEqual(self.count(page), 0)
        for row in self.all("SELECT slug FROM Document WHERE title LIKE 'Vodíková strategie%%' ORDER BY id"):
            self.goto(page, f"/dokument/{row['slug']}")
            self.assertNotIn("PLAN.md", page.locator("body").inner_text())
            self.shot(page, "strategy-" + row["slug"], full_page=False)
        self.assertNotIn("doc/PLAN.md", page.request.get(BASE_URL + "/export/json").text())

    # telefon ------------------------------------------------------------------
    def test_phone_layout_with_language_links(self):
        page = self.new_page(PHONE)
        self.goto(page, "/?q=RFNBO")
        overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        self.shot(page, "rfnbo-phone")
        self.assertLessEqual(overflow, 1, "the page is wider than the phone screen")
        self.assertGreaterEqual(page.locator(".lang-chip").count(), 2)
