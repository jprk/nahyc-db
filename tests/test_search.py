import unittest
import sys
import os
import re

# Přidání cesty, abychom mohli importovat app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.app import app

class SearchTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_energeticky_zakon_returns_one_record(self):
        # Odeslání dotazu
        response = self.app.get('/?q=Energetický+zákon')
        self.assertEqual(response.status_code, 200)
        
        html = response.data.decode('utf-8')
        
        # Očištění HTML od zbytečných mezer, abychom bezpečně našli titulek
        clean_html = re.sub(r'\s+', ' ', html)

        # Očekáváme, že se zákon 458/2000 Sb. zobrazí v HTML přesně jednou.
        # Původní chyba způsobovala, že se titulek vyrenderoval 3x. Hledáme
        # podle čísla zákona, ne podle přesného znění titulku — deduplikace
        # nyní tento záznam slučuje napříč zdroji (Sinay_Zakony +
        # Haltuf_Dokumenty) a vybírá nejúplnější dostupný název, takže
        # přesný text titulku se může v čase měnit (viz doc/PLAN.md Step 1).
        titles = re.findall(r'<div class="doc-title">([^<]*458/2000 Sb\.[^<]*)</div>', clean_html)

        self.assertEqual(len(titles), 1,
                          f"Očekával se právě jeden výskyt zákona 458/2000 Sb., ale bylo jich nalezeno {len(titles)}: {titles}")


class FulltextRouteTestCase(unittest.TestCase):
    """doc/REQUIREMENTS.md R1.7/R4.1, 2026-09-11: /fulltext/<id> must
    serve a document's locally-cached full text only when its
    DocumentType is not restricted_fulltext (copyrighted/paywalled
    standards) -- an integration test against the live h2regdocs, since
    the access-control decision depends on a live DocumentType JOIN, same
    reasoning as SearchTestCase above."""

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        import pymysql
        from dotenv import load_dotenv
        load_dotenv()
        conn = pymysql.connect(
            host=os.environ["DB_HOST"], port=int(os.environ["DB_PORT"]),
            user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
            database=os.environ["DB_NAME"], cursorclass=pymysql.cursors.DictCursor)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT d.id FROM Document d JOIN DocumentType dt ON d.type_id = dt.id
                WHERE dt.restricted_fulltext = TRUE AND d.file_path IS NOT NULL LIMIT 1
            """)
            self.restricted_with_file = cur.fetchone()
            cur.execute("""
                SELECT d.id FROM Document d JOIN DocumentType dt ON d.type_id = dt.id
                WHERE dt.restricted_fulltext = FALSE AND d.file_path IS NOT NULL LIMIT 1
            """)
            self.open_with_file = cur.fetchone()
            cur.execute("SELECT id FROM Document WHERE file_path IS NULL LIMIT 1")
            self.without_file = cur.fetchone()
        conn.close()

    def test_restricted_type_with_a_file_path_is_forbidden(self):
        if not self.restricted_with_file:
            self.skipTest("no restricted DocumentType row with a file_path in this corpus")
        response = self.app.get(f"/fulltext/{self.restricted_with_file['id']}")
        self.assertEqual(response.status_code, 403)

    def test_open_type_with_a_file_path_is_served(self):
        if not self.open_with_file:
            self.skipTest("no open DocumentType row with a file_path in this corpus")
        response = self.app.get(f"/fulltext/{self.open_with_file['id']}")
        self.assertEqual(response.status_code, 200)
        response.close()

    def test_document_without_a_file_path_is_not_found(self):
        if not self.without_file:
            self.skipTest("every Document row has a file_path in this corpus")
        response = self.app.get(f"/fulltext/{self.without_file['id']}")
        self.assertEqual(response.status_code, 404)

    def test_nonexistent_document_is_not_found(self):
        response = self.app.get("/fulltext/999999999")
        self.assertEqual(response.status_code, 404)


if __name__ == '__main__':
    unittest.main()
