"""Tests for the in-app text view and the hardened raw download (GitHub
issue #2): /dokument/<slug>/text, clean_text_path() and /fulltext/<id>.
The database is faked and the file locations are temporary, so unlike
test_search.py nothing here depends on the live corpus or on data/fulltext/."""
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import app.app as appmod  # noqa: E402

CLEAN = '<h3>Předmět úpravy</h3>\n<p class="l2"><span class="num">(1)</span> Text<sup>1)</sup>.</p>\n'


class FakeCursor:
    def __init__(self, row):
        self.row = row

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, *args, **kwargs):
        pass

    def fetchone(self):
        return self.row


class FakeDb:
    def __init__(self, row):
        self.row = row

    def cursor(self):
        return FakeCursor(self.row)


class FulltextViewTestCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = pathlib.Path(tmp.name).resolve()
        self.raw_dir = self.root / "data" / "fulltext"
        self.clean_dir = self.root / "data" / "fulltext_clean"
        (self.raw_dir / "S").mkdir(parents=True)
        (self.clean_dir / "S").mkdir(parents=True)
        (self.raw_dir / "S" / "a.html").write_text("<html><script>alert(1)</script></html>", encoding="utf-8")
        (self.clean_dir / "S" / "a.html").write_text(CLEAN, encoding="utf-8")
        (self.raw_dir / "S" / "p.pdf").write_bytes(b"%PDF-1.4 test")
        for name, value in (("REPO_ROOT", self.root), ("FULLTEXT_DIR", self.raw_dir),
                            ("CLEAN_TEXT_DIR", self.clean_dir)):
            patcher = mock.patch.object(appmod, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.client = appmod.app.test_client()

    def _db(self, row):
        patcher = mock.patch.object(appmod, "get_db", return_value=FakeDb(row))
        patcher.start()
        self.addCleanup(patcher.stop)

    @staticmethod
    def _row(file_path="data/fulltext/S/a.html", restricted=0):
        return {"id": 1, "slug": "nv-116-2016", "identifier": "116/2016 Sb.", "title": "Nařízení vlády",
                "url": "https://www.zakonyprolidi.cz/cs/2016-116", "file_path": file_path,
                "restricted_fulltext": restricted,
                # base.html's footer context processor reads the same fake cursor.
                "last_updated": None}

    # --- clean_text_path -------------------------------------------------
    def test_clean_text_path_finds_the_mirrored_file(self):
        self.assertEqual(appmod.clean_text_path("data/fulltext/S/a.html"), self.clean_dir / "S" / "a.html")

    def test_clean_text_path_is_none_without_file_path_or_clean_copy(self):
        self.assertIsNone(appmod.clean_text_path(None))
        self.assertIsNone(appmod.clean_text_path(""))
        (self.raw_dir / "S" / "b.html").write_text("x", encoding="utf-8")
        self.assertIsNone(appmod.clean_text_path("data/fulltext/S/b.html"))

    def test_clean_text_path_ignores_pdfs_and_paths_outside_the_download_dir(self):
        self.assertIsNone(appmod.clean_text_path("data/fulltext/S/p.pdf"))
        self.assertIsNone(appmod.clean_text_path("data/fulltext/../fulltext_clean/S/a.html"))
        self.assertIsNone(appmod.clean_text_path("../../etc/passwd"))

    def test_local_copy_path_is_none_when_the_file_is_not_on_this_machine(self):
        self.assertEqual(appmod.local_copy_path("data/fulltext/S/a.html"), self.raw_dir / "S" / "a.html")
        self.assertIsNone(appmod.local_copy_path("data/fulltext/S/not-downloaded.html"))
        self.assertIsNone(appmod.local_copy_path(None))
        self.assertIsNone(appmod.local_copy_path(""))
        self.assertIsNone(appmod.local_copy_path("../../etc/passwd"))

    # --- the buttons on the document page --------------------------------
    def _document_page(self, file_path, restricted=0):
        detail = {"document": {**self._row(file_path, restricted), "description": None, "popis_priblizny": None,
                               "language": None, "effective_date": None, "jurisdikce": None,
                               "jurisdikce_uroven": None, "needs_review": 0, "review_reason": None,
                               "updated_at": None, "type_name": "Zákon", "source_name": None, "id": 1},
                  "keywords": [], "versions": [], "relations": [], "process_nodes": []}
        self._db(self._row())
        patcher = mock.patch.object(appmod, "fetch_document_detail", return_value=detail)
        patcher.start()
        self.addCleanup(patcher.stop)
        response = self.client.get("/dokument/nv-116-2016")
        self.assertEqual(response.status_code, 200)
        body = response.data.decode("utf-8")
        return "Číst text" in body, "Stažená kopie" in body, "Plný text nedostupný" in body

    def test_both_buttons_when_the_copy_and_its_clean_text_exist(self):
        self.assertEqual(self._document_page("data/fulltext/S/a.html"), (True, True, False))

    def test_only_the_download_when_the_text_has_not_been_extracted_yet(self):
        (self.raw_dir / "S" / "b.html").write_text("x", encoding="utf-8")
        self.assertEqual(self._document_page("data/fulltext/S/b.html"), (False, True, False))

    def test_no_download_button_when_the_recorded_file_is_not_on_this_machine(self):
        self.assertEqual(self._document_page("data/fulltext/S/not-downloaded.html"), (False, False, False))

    def test_restricted_type_shows_only_the_lock(self):
        self.assertEqual(self._document_page("data/fulltext/S/a.html", restricted=1), (False, False, True))

    # --- /dokument/<slug>/text -------------------------------------------
    def test_text_page_renders_the_clean_text_unescaped_inside_the_app(self):
        self._db(self._row())
        response = self.client.get("/dokument/nv-116-2016/text")
        self.assertEqual(response.status_code, 200)
        body = response.data.decode("utf-8")
        self.assertIn("<h3>Předmět úpravy</h3>", body)
        self.assertIn('<span class="num">(1)</span>', body)
        self.assertIn("116/2016 Sb.", body)
        self.assertIn("https://www.zakonyprolidi.cz/cs/2016-116", body)
        self.assertNotIn("alert(1)", body)

    def test_restricted_type_is_forbidden_even_with_a_clean_copy(self):
        self._db(self._row(restricted=1))
        self.assertEqual(self.client.get("/dokument/nv-116-2016/text").status_code, 403)

    def test_unknown_slug_and_missing_clean_copy_are_not_found(self):
        self._db(None)
        self.assertEqual(self.client.get("/dokument/neexistuje/text").status_code, 404)
        self._db(self._row(file_path="data/fulltext/S/p.pdf"))
        self.assertEqual(self.client.get("/dokument/nv-116-2016/text").status_code, 404)
        self._db(self._row(file_path=None))
        self.assertEqual(self.client.get("/dokument/nv-116-2016/text").status_code, 404)

    # --- /fulltext/<id> --------------------------------------------------
    def test_raw_html_is_an_attachment_with_a_sandbox_policy(self):
        self._db(self._row())
        response = self.client.get("/fulltext/1")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["Content-Disposition"].startswith("attachment"))
        self.assertIn("sandbox", response.headers["Content-Security-Policy"])
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        response.close()

    def test_pdf_is_still_inline_and_not_sandboxed(self):
        self._db(self._row(file_path="data/fulltext/S/p.pdf"))
        response = self.client.get("/fulltext/1")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("attachment", response.headers.get("Content-Disposition", ""))
        self.assertNotIn("Content-Security-Policy", response.headers)
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        response.close()

    def test_raw_download_of_a_restricted_type_is_still_forbidden(self):
        self._db(self._row(restricted=1))
        self.assertEqual(self.client.get("/fulltext/1").status_code, 403)


if __name__ == "__main__":
    unittest.main()
