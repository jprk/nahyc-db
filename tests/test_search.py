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


class ExportRouteTestCase(unittest.TestCase):
    """doc/REQUIREMENTS.md R2.5/R4.1, 2026-09-11: /export/<fmt> exports the
    filtered result set in csv/json/xml, metadata-only (no file_path leak
    -- see FulltextRouteTestCase above for that channel's own access
    control). Integration test against the live h2regdocs, same reasoning
    as SearchTestCase/FulltextRouteTestCase."""

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_csv_export_returns_200_with_csv_content_type(self):
        response = self.app.get('/export/csv')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content_type.startswith('text/csv'))

    def test_json_export_returns_200_with_json_content_type(self):
        response = self.app.get('/export/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content_type.startswith('application/json'))

    def test_xml_export_returns_200_with_xml_content_type(self):
        response = self.app.get('/export/xml')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content_type.startswith('application/xml'))

    def test_invalid_format_returns_400(self):
        response = self.app.get('/export/pdf')
        self.assertEqual(response.status_code, 400)

    def test_type_id_filter_reduces_exported_row_count(self):
        import csv
        import io
        unfiltered = self.app.get('/export/csv')
        rows_all = list(csv.reader(io.StringIO(unfiltered.data.decode('utf-8'))))

        type_response = self.app.get('/')
        html = type_response.data.decode('utf-8')
        m = re.search(r'name="type_id"[^>]*>.*?<option value="(\d+)"', html, re.DOTALL)
        self.assertIsNotNone(m, "no real type_id option found on the index page to filter by")
        type_id = m.group(1)

        filtered = self.app.get(f'/export/csv?type_id={type_id}')
        rows_filtered = list(csv.reader(io.StringIO(filtered.data.decode('utf-8'))))
        # header row + N data rows in both -- filtered must not exceed unfiltered.
        self.assertLessEqual(len(rows_filtered), len(rows_all))

    def test_no_exported_row_leaks_a_file_path(self):
        import csv
        import io
        import json
        from xml.etree import ElementTree

        csv_resp = self.app.get('/export/csv')
        for row in csv.DictReader(io.StringIO(csv_resp.data.decode('utf-8'))):
            self.assertNotIn('file_path', row)
            for value in row.values():
                self.assertNotIn('data/fulltext/', value or '')

        json_resp = self.app.get('/export/json')
        rows = json.loads(json_resp.data)
        for row in rows:
            self.assertNotIn('file_path', row)
            self.assertNotIn('restricted_fulltext', row)
            self.assertNotIn('id', row)

        xml_resp = self.app.get('/export/xml')
        root = ElementTree.fromstring(xml_resp.data)
        for doc_el in root:
            tags = {child.tag for child in doc_el}
            self.assertNotIn('file_path', tags)
            self.assertNotIn('restricted_fulltext', tags)


if __name__ == '__main__':
    unittest.main()
