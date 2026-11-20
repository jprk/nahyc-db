"""Slovak documents are not listed in the public catalogue, but their pages stay
reachable by address; for a visitor who is not logged in they carry
`<meta name="robots" content="noindex">` and `X-Robots-Tag: noindex`
(doc/MPO_PRIPOMINKY.md, odstavec 5). No database: get_db is a fake."""
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("SECRET_KEY", "unit-test")
import app.app as webapp  # noqa: E402

SLOVAK = {"slug": "zakon-sk", "identifier": "124/2000 Z. z.", "title": "Zákon", "url": "https://slov-lex.sk/x",
          "file_path": "data/fulltext/x.html", "jurisdikce": "SK", "restricted_fulltext": 0}
SLOVAK_VARIANT = {**SLOVAK, "identifier": "(EU) 2024/1788 [SK]", "jurisdikce": "EU"}
CZECH = {**SLOVAK, "identifier": "458/2000 Sb.", "jurisdikce": "CZ"}


def fake_db(row):
    db = mock.MagicMock()
    db.cursor.return_value.__enter__.return_value.fetchone.return_value = row
    return db


class NoindexForTestCase(unittest.TestCase):
    def check(self, document, logged_in):
        with webapp.app.test_request_context("/"):
            if logged_in:
                webapp.session["user_id"] = 1
            return webapp.noindex_for(document)

    def test_slovak_document_for_a_visitor(self):
        self.assertTrue(self.check(SLOVAK, logged_in=False))
        self.assertTrue(self.check(SLOVAK_VARIANT, logged_in=False))

    def test_not_for_a_logged_in_editor(self):
        self.assertFalse(self.check(SLOVAK, logged_in=True))

    def test_not_for_other_documents(self):
        self.assertFalse(self.check(CZECH, logged_in=False))
        self.assertFalse(self.check(None, logged_in=False))


class NoindexPagesTestCase(unittest.TestCase):
    def setUp(self):
        self.client = webapp.app.test_client()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.text = pathlib.Path(self.tmp.name) / "x.html"
        self.text.write_text("<p>Text</p>", encoding="utf-8")
        for patcher in (mock.patch.object(webapp, "get_db_last_updated", return_value=None),
                        mock.patch.object(webapp, "clean_text_path", return_value=self.text),
                        mock.patch.object(webapp, "local_copy_path", return_value=self.text)):
            patcher.start()
            self.addCleanup(patcher.stop)

    def get(self, path, row, logged_in=False):
        if logged_in:
            with self.client.session_transaction() as sess:
                sess["user_id"] = 1
        with mock.patch.object(webapp, "get_db", return_value=fake_db(row)):
            return self.client.get(path)

    def test_text_page_of_a_slovak_document(self):
        response = self.get("/dokument/zakon-sk/text", SLOVAK)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("X-Robots-Tag"), "noindex")
        self.assertIn('<meta name="robots" content="noindex">', response.get_data(as_text=True))

    def test_text_page_of_a_czech_document_is_indexable(self):
        response = self.get("/dokument/zakon-sk/text", CZECH)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.headers.get("X-Robots-Tag"))
        self.assertNotIn('name="robots"', response.get_data(as_text=True))

    def test_editor_sees_no_noindex(self):
        response = self.get("/dokument/zakon-sk/text", SLOVAK, logged_in=True)
        self.assertIsNone(response.headers.get("X-Robots-Tag"))

    def test_downloaded_file_of_a_slovak_document(self):
        response = self.get("/fulltext/1", SLOVAK_VARIANT)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("X-Robots-Tag"), "noindex")
        response.close()

    def test_document_page_of_a_slovak_document(self):
        detail = {"document": {**SLOVAK, "id": 1}, "keywords": [], "versions": [], "relations": [],
                  "process_nodes": []}
        with mock.patch.object(webapp, "get_db", return_value=fake_db(None)), \
                mock.patch.object(webapp, "fetch_document_detail", return_value=detail), \
                mock.patch.object(webapp, "render_template", side_effect=lambda name, **kw: f"noindex={kw['noindex']}"):
            response = self.client.get("/dokument/zakon-sk")
        self.assertEqual(response.headers.get("X-Robots-Tag"), "noindex")
        self.assertEqual(response.get_data(as_text=True), "noindex=True")


if __name__ == "__main__":
    unittest.main()
