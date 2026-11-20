"""Browser scenario: Slovak documents are not in the public catalogue
(doc/MPO_PRIPOMINKY.md, odstavec 4.3, decided by the user). A visitor sees no
Slovak document in the list, the search, the menus, the counts, the exports
or the relation lists; the page of a Slovak document still opens from its
address and says it is not listed. A logged-in editor gets the switch
"Zahrnout i slovenskou legislativu" and with it everything.

The editor account is a fixture created in, and removed from, the TEST
database; the base class refuses any other."""
import json
import re

from werkzeug.security import generate_password_hash

from browser_case import BASE_URL, PHONE, BrowserTestCase, database_connection

SLOVAK = "(d.jurisdikce = 'SK' OR d.identifier LIKE '%%[SK]')"
NOT_TRANSLATION = ("NOT EXISTS (SELECT 1 FROM document_relation tr WHERE tr.from_document_id = d.id "
                   "AND tr.relation_type = 'TRANSLATION_OF')")
USERNAME, PASSWORD = "e2e_sk_editor", "sk-editor-e2e-password"
SWITCH = "Zahrnout i slovenskou legislativu"


class SlovakDocumentsTestCase(BrowserTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.db = database_connection()
        cls.cleanup()
        with cls.db.cursor() as cur:
            cur.execute("INSERT INTO User (username, name, email, password_hash) VALUES (%s, %s, %s, %s)",
                        (USERNAME, "Editor SK E2E", f"{USERNAME}@example.test", generate_password_hash(PASSWORD)))
        cls.acts = cls.one(f"SELECT COUNT(*) AS c FROM Document d WHERE {NOT_TRANSLATION}")["c"]
        cls.slovak_acts = cls.one(f"SELECT COUNT(*) AS c FROM Document d WHERE {NOT_TRANSLATION} AND {SLOVAK}")["c"]
        cls.slovak_slugs = {r["slug"] for r in cls.all(f"SELECT slug FROM Document d WHERE {SLOVAK}")}
        # one row per act: a Slovak text of an EU act (TRANSLATION_OF) sits in the row of its Czech text
        cls.slovak_heads = {r["slug"] for r in cls.all(
            "SELECT d.slug FROM document_relation r JOIN Document s ON s.id = r.from_document_id "
            "JOIN Document d ON d.id = r.to_document_id WHERE r.relation_type = 'TRANSLATION_OF' "
            "AND " + SLOVAK.replace("d.", "s."))}

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
    def all(cls, sql, params=()):
        with cls.db.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()

    @classmethod
    def one(cls, sql, params=()):
        rows = cls.all(sql, params)
        return rows[0] if rows else None

    def count(self, page):
        return int(page.locator(".results-title .badge").inner_text())

    def row_slugs(self, page):
        return {r.get_attribute("data-slug") for r in page.locator(".document-row").all()}

    def login(self, page):
        self.goto(page, "/admin/login")
        page.fill("#username", USERNAME)
        page.fill("#password", PASSWORD)
        page.click("button[type=submit]")
        page.wait_for_url(lambda url: "/admin/login" not in url)

    def test_visitor_sees_no_slovak_documents(self):
        page = self.new_page()
        self.goto(page, "/")
        public = self.acts - self.slovak_acts
        self.assertEqual(self.count(page), public)
        self.assertIn(f"Prohledejte {public} ", page.locator(".hero-subtitle").inner_text())
        self.assertEqual(page.get_by_text(SWITCH).count(), 0)
        jurisdictions = [o.strip() for o in page.locator("select[name=jurisdikce] option").all_inner_texts()]
        self.assertNotIn("Slovensko", jurisdictions)
        groups = [g.get_attribute("label") for g in page.locator("select[name=source_id] optgroup").all()]
        self.assertNotIn("Slovensko", groups)
        sources = " ".join(page.locator("select[name=source_id] option").all_inner_texts())
        self.assertNotIn("ÚNMS SR", sources)
        self.assertNotIn("Slovenskej republiky", sources)
        self.shot(page, "visitor-catalogue", full_page=False)

        # a search for Slovak standards finds none, a forged parameter changes nothing
        self.goto(page, "/?q=STN")
        self.assertEqual(self.row_slugs(page) & self.slovak_slugs, set())
        self.shot(page, "visitor-search-stn", full_page=False)
        self.goto(page, "/?sk=1&jurisdikce=sk")
        self.assertEqual(self.count(page), public)

        rows = json.loads(page.request.get(BASE_URL + "/export/json?sk=1").text())
        self.assertFalse([r for r in rows if "Slovenskej republiky" in r["source_name"]
                          or "ÚNMS SR" in r["source_name"]])
        self.assertNotIn("ÚNMS SR", page.request.get(BASE_URL + "/export/csv").text())
        self.assertNotIn("ÚNMS SR", page.request.get(BASE_URL + "/export/xml").text())

    def test_direct_link_and_relations(self):
        page = self.new_page()
        slovak = self.one("SELECT slug, identifier FROM Document WHERE identifier LIKE 'STN EN 1555-1%%'") \
            or self.one(f"SELECT slug, identifier FROM Document d WHERE {SLOVAK} ORDER BY id LIMIT 1")
        self.goto(page, f"/dokument/{slovak['slug']}")
        self.assertIn("Slovenský dokument", page.locator(".slovak-note").inner_text())
        self.shot(page, "visitor-slovak-page", full_page=False)

        related = self.one(f"""SELECT d.slug, o.slug AS other FROM document_relation r
            JOIN Document d ON d.id = r.to_document_id JOIN Document o ON o.id = r.from_document_id
            WHERE NOT {SLOVAK} AND (o.jurisdikce = 'SK' OR o.identifier LIKE '%%[SK]')
            ORDER BY d.identifier LIMIT 1""")
        if related:
            self.goto(page, f"/dokument/{related['slug']}")
            self.assertEqual(page.locator(f'a[href$="/dokument/{related["other"]}"]').count(), 0)
            self.shot(page, "visitor-related-page")

        node = self.one(f"""SELECT nd.node_id, d.slug FROM node_document nd JOIN Document d ON d.id = nd.document_id
            WHERE {SLOVAK} ORDER BY nd.node_id LIMIT 1""")
        if node:
            self.goto(page, f"/proces/{node['node_id']}")
            self.assertEqual(page.locator(f'a[href$="/dokument/{node["slug"]}"]').count(), 0)

        # the editor sees the same relations
        self.login(page)
        if related:
            self.goto(page, f"/dokument/{related['slug']}")
            self.assertGreaterEqual(page.locator(f'a[href$="/dokument/{related["other"]}"]').count(), 1)
        if node:
            self.goto(page, f"/proces/{node['node_id']}")
            self.assertGreaterEqual(page.locator(f'a[href$="/dokument/{node["slug"]}"]').count(), 1)

    def test_editor_includes_slovak_documents_with_the_switch(self):
        page = self.new_page()
        self.login(page)
        self.goto(page, "/")
        self.assertEqual(self.count(page), self.acts - self.slovak_acts)
        switch = page.get_by_label(SWITCH)
        self.assertFalse(switch.is_checked())
        self.shot_element(page.locator(".search-glass-panel"), "editor-filters")
        switch.check()
        page.wait_for_url(re.compile(r"[?&]sk=1"))
        self.assertTrue(page.get_by_label(SWITCH).is_checked())
        self.assertEqual(self.count(page), self.acts)
        self.assertIn(f"Prohledejte {self.acts} ", page.locator(".hero-subtitle").inner_text())
        groups = [g.get_attribute("label") for g in page.locator("select[name=source_id] optgroup").all()]
        self.assertIn("Slovensko", groups)

        page.locator("select[name=jurisdikce]").select_option(label="Slovensko")
        page.wait_for_url(re.compile(r"jurisdikce=sk"))
        self.assertIn("sk=1", page.url)
        # the Slovak documents of their own plus the rows of EU acts with a Slovak text
        self.assertEqual(self.count(page), self.slovak_acts + len(self.slovak_heads))
        self.assertLessEqual(self.row_slugs(page), self.slovak_slugs | self.slovak_heads)
        self.shot(page, "editor-slovakia", full_page=False)

        # the exports follow the switch and the page ("strana 2" keeps it as well)
        rows = json.loads(page.request.get(BASE_URL + "/export/json?sk=1&jurisdikce=sk").text())
        self.assertEqual(len(rows), self.one(f"SELECT COUNT(*) AS c FROM Document d WHERE {SLOVAK}")["c"])
        if page.locator("a.page-nav[rel=next]").count():
            self.assertIn("sk=1", page.locator("a.page-nav[rel=next]").get_attribute("href"))

    def test_phone(self):
        page = self.new_page(PHONE)
        self.login(page)
        self.goto(page, "/?sk=1")
        overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        self.shot_element(page.locator(".search-glass-panel"), "editor-filters-phone")
        self.assertLessEqual(overflow, 1, "the page is wider than the phone screen")
        self.assertTrue(page.get_by_label(SWITCH).is_visible())
