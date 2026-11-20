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
    def __init__(self, row, versions=()):
        self.row = row
        self.versions = list(versions)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, *args, **kwargs):
        pass

    def fetchone(self):
        return self.row

    def fetchall(self):  # the versions of the document (fetch_versions)
        return [dict(v) for v in self.versions]


class FakeDb:
    def __init__(self, row, versions=()):
        self.row = row
        self.versions = versions

    def cursor(self):
        return FakeCursor(self.row, self.versions)


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

    def _db(self, row, versions=()):
        patcher = mock.patch.object(appmod, "get_db", return_value=FakeDb(row, versions))
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

    def test_a_pdf_has_clean_text_only_when_it_was_extracted_under_its_name(self):
        self.assertIsNone(appmod.clean_text_path("data/fulltext/S/p.pdf"))
        (self.clean_dir / "S" / "p.html").write_text(CLEAN, encoding="utf-8")
        self.assertEqual(appmod.clean_text_path("data/fulltext/S/p.pdf"), self.clean_dir / "S" / "p.html")

    def test_other_file_types_and_paths_outside_the_download_dir_have_no_clean_text(self):
        (self.raw_dir / "S" / "x.xml").write_text("x", encoding="utf-8")
        (self.clean_dir / "S" / "x.html").write_text(CLEAN, encoding="utf-8")
        self.assertIsNone(appmod.clean_text_path("data/fulltext/S/x.xml"))
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

    # --- versions of an EU act shown in its consolidated version (eu_consolidations.py) ---
    @staticmethod
    def _versions(count=3):
        """The original text (p.pdf, superseded), consolidated versions, the last but
        one current with the text a.html, the last one prepared."""
        versions = [{"version": 1, "edition_label": "původní znění (Úř. věst. L 353, 31. 12. 2008)",
                     "effective_date": "2009-01-20", "is_current": 0, "lifecycle_state": "superseded",
                     "file_path": "data/fulltext/S/p.pdf",
                     "url": "https://eur-lex.europa.eu/legal-content/CS/TXT/?uri=CELEX:32008R1272"}]
        for n in range(2, count + 2):
            current, prepared = n == count, n == count + 1
            versions.append({"version": n, "edition_label": f"konsolidované znění ke dni {n}. 1. 2026",
                             "effective_date": f"2026-01-{n:02d}", "is_current": int(current),
                             "lifecycle_state": "promulgated" if prepared else ("active" if current else "superseded"),
                             "file_path": "data/fulltext/S/a.html" if current else None,
                             "url": f"https://eur-lex.europa.eu/legal-content/CS/TXT/?uri=CELEX:02008R1272-202601{n:02d}"})
        return versions

    def _versions_page(self, versions):
        (self.clean_dir / "S" / "p.html").write_text("<p>Původní znění</p>", encoding="utf-8")
        detail = {"document": {**self._row(), "description": None, "popis_priblizny": None,
                               "language": None, "effective_date": None, "jurisdikce": None,
                               "jurisdikce_uroven": None, "needs_review": 0, "review_reason": None,
                               "updated_at": None, "type_name": "Nařízení EU", "source_name": None, "id": 1},
                  "keywords": [], "versions": versions, "relations": [], "process_nodes": []}
        self._db(self._row())
        patcher = mock.patch.object(appmod, "fetch_document_detail", return_value=detail)
        patcher.start()
        self.addCleanup(patcher.stop)
        response = self.client.get("/dokument/nv-116-2016")
        self.assertEqual(response.status_code, 200)
        return response.data.decode("utf-8")

    def test_the_page_says_which_version_it_shows_and_links_every_version(self):
        body = self._versions_page(self._versions())
        self.assertIn("Zobrazený text: <strong>konsolidované znění ke dni 3. 1. 2026</strong>", body)
        self.assertIn("uri=CELEX:32008R1272", body)
        self.assertIn("uri=CELEX:02008R1272-20260104", body)  # the prepared one
        self.assertIn('href="/dokument/nv-116-2016/verze/1/text"', body)  # our text of the original
        self.assertNotIn("Starší znění", body)

    def test_a_long_history_is_folded_but_the_original_stays_in_view(self):
        body = self._versions_page(self._versions(count=10))
        self.assertIn("Starší znění (8)", body)
        head, _, folded = body.partition("Starší znění")
        self.assertIn("původní znění (Úř. věst. L 353, 31. 12. 2008)", head)
        self.assertIn("konsolidované znění ke dni 10. 1. 2026", head)
        self.assertIn("konsolidované znění ke dni 2. 1. 2026", folded)

    def test_versions_of_a_standard_have_no_links_column(self):
        body = self._versions_page([{"version": 1, "edition_label": "ČSN EN 1 (vydání 1.2020)", "effective_date": None,
                                     "is_current": 1, "lifecycle_state": "active", "file_path": None, "url": None}])
        self.assertNotIn("Odkazy", body)
        self.assertNotIn("Zobrazený text", body)

    def test_the_text_of_one_version(self):
        (self.clean_dir / "S" / "p.html").write_text("<p>Původní znění</p>", encoding="utf-8")
        self._db(self._row(), self._versions())
        response = self.client.get("/dokument/nv-116-2016/verze/1/text")
        self.assertEqual(response.status_code, 200)
        body = response.data.decode("utf-8")
        self.assertIn("<p>Původní znění</p>", body)
        self.assertIn("původní znění (Úř. věst. L 353, 31. 12. 2008)", body)
        self.assertIn("nahrazený", body)
        self.assertEqual(self.client.get("/dokument/nv-116-2016/verze/2/text").status_code, 404)  # no text
        self.assertEqual(self.client.get("/dokument/nv-116-2016/verze/99/text").status_code, 404)

    def test_the_text_of_a_version_of_a_restricted_type_is_forbidden(self):
        self._db(self._row(restricted=1), self._versions())
        self.assertEqual(self.client.get("/dokument/nv-116-2016/verze/1/text").status_code, 403)

    def test_the_main_text_page_names_the_consolidated_version(self):
        self._db(self._row(), self._versions())
        body = self.client.get("/dokument/nv-116-2016/text").data.decode("utf-8")
        self.assertIn("Znění: <strong>konsolidované znění ke dni 3. 1. 2026</strong>", body)

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
