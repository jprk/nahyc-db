import json
import pathlib
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))

import fetch_fulltext as ff


class SanitizeZnackaTestCase(unittest.TestCase):
    def test_replaces_unsafe_characters(self):
        self.assertEqual(ff.sanitize_znacka("(EU) 2024/1788"), "EU_2024_1788")

    def test_strips_leading_trailing_underscores(self):
        self.assertEqual(ff.sanitize_znacka("  183/2006 Sb.  "), "183_2006_Sb.")

    def test_empty_falls_back_to_placeholder(self):
        self.assertEqual(ff.sanitize_znacka("***"), "unnamed")


class IsFetchableSourceTestCase(unittest.TestCase):
    """doc/PLAN.md §15, 2026-09-15: source-agnostic -- keyed on the
    record's own typ_dokumentu, not which spreadsheet it came from."""

    def test_norma_excluded(self):
        self.assertFalse(ff.is_fetchable_source("Norma"))

    def test_law_types_included(self):
        for typ in ("Zákon", "Vyhláška", "Nařízení vlády", "Nařízení EU",
                    "Směrnice EU"):
            self.assertTrue(ff.is_fetchable_source(typ), typ)

    def test_blank_typ_is_still_true(self):
        self.assertTrue(ff.is_fetchable_source(""))


class IsNormDesignationTestCase(unittest.TestCase):
    """doc/REQUIREMENTS.md R4.1, 2026-09-11: a second, source-independent
    guard -- a law source (e.g. Haltuf_Dokumenty) can still carry a stray
    norm citation of its own (real corpus cases: "ISO 14687", "ČSN EN
    17127", "DIN EN ISO 22734")."""

    def test_norm_designations_detected_regardless_of_source(self):
        for zn in ("ISO 14687", "ČSN EN 17127", "ČSN EN ISO 17268",
                   "DIN EN ISO 22734", "STN ISO 1", "EN 50129"):
            self.assertTrue(ff.is_norm_designation(zn), zn)

    def test_law_designations_are_not_norms(self):
        for zn in ("183/2006 Sb.", "(EU) 2016/797", "458/2000 Sb."):
            self.assertFalse(ff.is_norm_designation(zn), zn)

    def test_blank_is_not_a_norm(self):
        self.assertFalse(ff.is_norm_designation(""))
        self.assertFalse(ff.is_norm_designation(None))


class IterFetchTargetsTestCase(unittest.TestCase):
    def test_skips_norma_typ_even_with_url(self):
        raw = [{"zdroj_dat": "Prokop_Normy", "typ_dokumentu": "Norma", "znacka": "ISO 14687",
                "odkaz_hlavni": "https://iso.org/standards.html"}]
        self.assertEqual(list(ff.iter_fetch_targets(raw)), [])

    def test_skips_norm_shaped_znacka_even_when_typ_is_not_norma(self):
        # Real corpus case: a law-typed record also carried a stray
        # "ČSN EN 17127" entry, fetched before this fix.
        raw = [{"zdroj_dat": "Haltuf_Dokumenty", "typ_dokumentu": "Zákon", "znacka": "ČSN EN 17127",
                "odkaz_hlavni": "https://www.technicke-normy-csn.cz/x.html"}]
        self.assertEqual(list(ff.iter_fetch_targets(raw)), [])

    def test_skips_records_without_znacka(self):
        raw = [{"zdroj_dat": "Haltuf_Dokumenty", "znacka": "",
                "odkaz_hlavni": "https://eur-lex.europa.eu/x"}]
        self.assertEqual(list(ff.iter_fetch_targets(raw)), [])

    def test_yields_one_entry_per_populated_url_field(self):
        raw = [{"zdroj_dat": "Sinay_Zakony", "znacka": "183/2006 Sb.",
                "odkaz_hlavni": "https://www.zakonyprolidi.cz/cs/2006-183",
                "odkaz_eu": "", "odkaz_sk": "https://www.slov-lex.sk/x"}]
        targets = list(ff.iter_fetch_targets(raw))
        self.assertEqual(len(targets), 2)
        fields = {t[1] for t in targets}
        self.assertEqual(fields, {"odkaz_hlavni", "odkaz_sk"})

    def test_takes_only_the_first_url_when_two_are_newline_joined(self):
        # A real case found in Haltuf's raw data: an Excel line-break
        # leaves two URLs in one cell (the real EUR-Lex PDF link, then an
        # unrelated informational page) -- sending the whole blob 404s.
        raw = [{"zdroj_dat": "Haltuf_Dokumenty", "znacka": "(EU) 2016/797",
                "odkaz_hlavni": "https://eur-lex.europa.eu/x?uri=CELEX:1\n\n"
                                 "https://transport.ec.europa.eu/unrelated-page"}]
        targets = list(ff.iter_fetch_targets(raw))
        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0][2], "https://eur-lex.europa.eu/x?uri=CELEX:1")


class FirstUrlTestCase(unittest.TestCase):
    def test_single_url_passes_through(self):
        self.assertEqual(ff.first_url("https://example.com/x"), "https://example.com/x")

    def test_two_newline_joined_urls_keeps_first(self):
        self.assertEqual(ff.first_url("https://a.com/x\n\nhttps://b.com/y"), "https://a.com/x")

    def test_blank_or_none_gives_empty_string(self):
        self.assertEqual(ff.first_url(""), "")
        self.assertEqual(ff.first_url(None), "")


class ExtensionFromUrlTestCase(unittest.TestCase):
    def test_pdf_from_url_suffix(self):
        self.assertEqual(ff.extension_from_url("https://eur-lex.europa.eu/x/PDF/?uri=y"), "bin")

    def test_pdf_from_explicit_extension(self):
        self.assertEqual(ff.extension_from_url("https://example.com/doc.pdf"), "pdf")

    def test_html_from_content_type_when_url_has_no_extension(self):
        self.assertEqual(ff.extension_from_url("https://www.zakonyprolidi.cz/cs/2006-183",
                                                "text/html; charset=utf-8"), "html")

    def test_falls_back_to_bin(self):
        self.assertEqual(ff.extension_from_url("https://example.com/x", None), "bin")


class ManifestKeyTestCase(unittest.TestCase):
    def test_key_is_stable_and_distinguishes_url_field(self):
        k1 = ff.manifest_key("Sinay_Zakony", "183/2006 Sb.", "odkaz_hlavni")
        k2 = ff.manifest_key("Sinay_Zakony", "183/2006 Sb.", "odkaz_sk")
        self.assertNotEqual(k1, k2)


class AlreadyFetchedTestCase(unittest.TestCase):
    def test_false_when_no_manifest_entry(self):
        self.assertFalse(ff.already_fetched({}, "missing"))

    def test_false_when_status_is_not_fetched(self):
        manifest = {"k": {"status": "failed", "local_path": "data/fulltext/x.pdf"}}
        self.assertFalse(ff.already_fetched(manifest, "k"))

    def test_false_when_local_file_is_missing_on_disk(self):
        manifest = {"k": {"status": "fetched", "local_path": "data/fulltext/does-not-exist.pdf"}}
        self.assertFalse(ff.already_fetched(manifest, "k"))

    def test_true_when_fetched_and_file_present(self):
        real_file = pathlib.Path(__file__).resolve()  # any file that actually exists
        manifest = {"k": {"status": "fetched", "local_path": str(real_file.relative_to(ff.REPO_ROOT))}}
        self.assertTrue(ff.already_fetched(manifest, "k"))


class FetchOneTestCase(unittest.TestCase):
    def test_records_failure_on_request_exception(self):
        import requests
        session = MagicMock()
        session.get.side_effect = requests.RequestException("timeout")
        record = {"zdroj_dat": "Haltuf_Dokumenty", "znacka": "(EU) 2024/1788"}
        entry = ff.fetch_one(session, record, "odkaz_hlavni", "https://eur-lex.europa.eu/x")
        self.assertEqual(entry["status"], "failed")

    def _session(self, content, content_type="application/pdf"):
        session = MagicMock()
        resp = MagicMock()
        resp.content = content
        resp.status_code = 200
        resp.headers = {"Content-Type": content_type}
        resp.raise_for_status.return_value = None
        session.get.return_value = resp
        return session

    def test_writes_one_flat_file_named_by_designation_and_content(self):
        import hashlib
        import tempfile
        from unittest import mock
        content = b"%PDF-1.4 fake content"
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            with mock.patch.object(ff, "REPO_ROOT", root), \
                    mock.patch.object(ff, "FULLTEXT_DIR", root / "data" / "fulltext"):
                entry = ff.fetch_one(self._session(content), {"zdroj_dat": "Anything", "znacka": "TEST/2026"},
                                     "odkaz_hlavni", "https://example.com/doc")
            sha = hashlib.sha256(content).hexdigest()
            self.assertEqual(entry["status"], "fetched")
            self.assertEqual(entry["sha256"], sha)
            # straight into data/fulltext/, no per-source folder
            self.assertEqual(entry["local_path"], f"data/fulltext/TEST_2026__{sha[:8]}.pdf")
            self.assertEqual((root / entry["local_path"]).read_bytes(), content)

    def test_the_same_content_from_two_url_fields_is_one_file(self):
        import tempfile
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            with mock.patch.object(ff, "REPO_ROOT", root), \
                    mock.patch.object(ff, "FULLTEXT_DIR", root / "data" / "fulltext"):
                record = {"zdroj_dat": "Sinay_Zakony", "znacka": "(EU) 2022/869"}
                first = ff.fetch_one(self._session(b"<html>x</html>", "text/html"), record, "odkaz_hlavni", "https://a/x")
                second = ff.fetch_one(self._session(b"<html>x</html>", "text/html"), record, "odkaz_eu", "https://b/x")
            self.assertEqual(first["local_path"], second["local_path"])
            self.assertEqual(len(list((root / "data" / "fulltext").iterdir())), 1)

    def test_different_content_under_the_same_designation_gets_a_different_name(self):
        import tempfile
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            with mock.patch.object(ff, "REPO_ROOT", root), \
                    mock.patch.object(ff, "FULLTEXT_DIR", root / "data" / "fulltext"):
                record = {"zdroj_dat": "Haltuf_Dokumenty", "znacka": "201/2012 Sb."}
                a = ff.fetch_one(self._session(b"<html>cz law</html>", "text/html"), record, "odkaz_hlavni", "https://a/x")
                b = ff.fetch_one(self._session(b"<html>eur-lex</html>", "text/html"), record, "odkaz_hlavni", "https://b/x")
            self.assertNotEqual(a["local_path"], b["local_path"])
            self.assertEqual(len(list((root / "data" / "fulltext").iterdir())), 2)

    def test_source_spreadsheet_is_not_part_of_the_path(self):
        import tempfile
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            with mock.patch.object(ff, "REPO_ROOT", root), \
                    mock.patch.object(ff, "FULLTEXT_DIR", root / "data" / "fulltext"):
                entry = ff.fetch_one(self._session(b"%PDF-1.4 x"), {"zdroj_dat": "Haltuf_Dokumenty", "znacka": "A 1"},
                                     "odkaz_hlavni", "https://example.com/doc")
            self.assertNotIn("Haltuf", entry["local_path"])


class FlatNameTestCase(unittest.TestCase):
    def test_designation_and_eight_hash_digits(self):
        self.assertEqual(ff.flat_name("(EU) 2022/869", "a" * 64, "html"), "EU_2022_869__aaaaaaaa.html")

    def test_unsafe_designation_is_sanitized(self):
        self.assertEqual(ff.flat_name("183/2006 Sb.", "0123456789abcdef" * 4, "pdf"), "183_2006_Sb.__01234567.pdf")


SEARCH_PAGE = b"<html><head><title>Search results - EUR-Lex</title></head><body>0 results</body></html>"
ACT_PAGE = b"<html><head><title>Regulation - 2018/858 - EN - EUR-Lex</title></head><body><div id='text'>act</div></body></html>"


class IsDocumentPageTestCase(unittest.TestCase):
    def test_eur_lex_search_results_page_is_not_a_document(self):
        ok, reason = ff.is_document_page("https://eur-lex.europa.eu/eli/dir/2018/858/oj", SEARCH_PAGE, "text/html")
        self.assertFalse(ok)
        self.assertIn("search-results", reason)

    def test_an_eur_lex_page_whose_content_did_not_render_is_not_a_document(self):
        chrome_only = b"<html><head><title>Regulation - 1272/2008 - EN - EUR-Lex</title></head><body><div class='ecl-site-footer'>x</div></body></html>"
        ok, reason = ff.is_document_page("https://eur-lex.europa.eu/eli/reg/2008/1272/oj", chrome_only, "text/html")
        self.assertFalse(ok)
        self.assertIn("did not render", reason)

    def test_each_eur_lex_dialect_passes_the_render_check(self):
        url = "https://eur-lex.europa.eu/eli/reg/x/oj"
        for marker in ("<div id='text'>", "<div class='eli-container'>", "<p class='oj-doc-ti'>", "<div id='TexteOnly'>"):
            page = f"<html><head><title>Regulation - EUR-Lex</title></head><body>{marker}x</body></html>".encode()
            self.assertTrue(ff.is_document_page(url, page, "text/html")[0], marker)

    def test_real_eur_lex_act_is_a_document(self):
        self.assertEqual(ff.is_document_page("https://eur-lex.europa.eu/eli/reg/2018/858/oj", ACT_PAGE, "text/html"), (True, ""))

    def test_empty_body_is_not_a_document(self):
        self.assertFalse(ff.is_document_page("https://example.test/x", b"", "text/html")[0])

    def test_a_pdf_must_start_like_a_pdf(self):
        self.assertTrue(ff.is_document_page("https://example.test/x.pdf", b"%PDF-1.7 ...", "application/pdf")[0])
        self.assertFalse(ff.is_document_page("https://example.test/x.pdf", b"<html>captcha</html>", "application/pdf")[0])

    def test_a_page_called_search_results_elsewhere_is_left_alone(self):
        self.assertTrue(ff.is_document_page("https://www.zakonyprolidi.cz/x", SEARCH_PAGE, "text/html")[0])


class FetchOneGuardsTestCase(unittest.TestCase):
    def _session(self, content, status=200, content_type="text/html"):
        from unittest.mock import MagicMock
        resp = MagicMock()
        resp.content, resp.status_code = content, status
        resp.headers = {"Content-Type": content_type}
        resp.raise_for_status.return_value = None
        session = MagicMock()
        session.get.return_value = resp
        return session

    def _run(self, session, url, browser=None):
        import tempfile
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            with mock.patch.object(ff, "REPO_ROOT", root), mock.patch.object(ff, "FULLTEXT_DIR", root / "data" / "fulltext"), \
                    mock.patch.object(ff, "fetch_with_browser", return_value=browser) as fb:
                entry = ff.fetch_one(session, {"zdroj_dat": "S", "znacka": "56/2001 Sb."}, "odkaz_eu", url)
                written = list((root / "data" / "fulltext").glob("*")) if (root / "data" / "fulltext").exists() else []
            return entry, written, fb

    def test_a_search_results_page_is_recorded_as_failed_and_not_written(self):
        entry, written, _ = self._run(self._session(SEARCH_PAGE), "https://eur-lex.europa.eu/eli/dir/2018/858/oj")
        self.assertEqual(entry["status"], "failed")
        self.assertEqual(written, [])

    def test_a_firewall_challenge_is_retried_in_a_browser(self):
        entry, written, fb = self._run(self._session(b"", status=202), "https://eur-lex.europa.eu/eli/reg/2018/858/oj",
                                       browser=(200, ACT_PAGE, "text/html; charset=utf-8"))
        fb.assert_called_once()
        self.assertEqual(entry["status"], "fetched")
        self.assertEqual(entry["http_status"], 200)
        self.assertEqual(len(written), 1)

    def test_a_challenge_with_no_browser_is_a_failure_not_an_empty_file(self):
        entry, written, _ = self._run(self._session(b"", status=202), "https://eur-lex.europa.eu/eli/reg/2018/858/oj")
        self.assertEqual(entry["status"], "failed")
        self.assertEqual(written, [])

    def test_other_hosts_are_not_sent_to_a_browser(self):
        _, _, fb = self._run(self._session(b"", status=202), "https://example.test/x")
        fb.assert_not_called()


class OverridesTestCase(unittest.TestCase):
    RECORDS = [{"zdroj_dat": "Sinay_Zakony", "znacka": "56/2001 Sb.", "typ_dokumentu": "Zákon",
                "odkaz_hlavni": "https://a/x", "odkaz_eu": "https://eur-lex.europa.eu/eli/dir/2018/858/oj"}]

    def test_an_override_replaces_only_its_own_url(self):
        overrides = {"Sinay_Zakony|56/2001 Sb.|odkaz_eu": {"url": "https://eur-lex.europa.eu/eli/reg/2018/858/oj", "reason": "r"}}
        urls = {f: u for _, f, u in ff.iter_fetch_targets(self.RECORDS, overrides)}
        self.assertEqual(urls["odkaz_eu"], "https://eur-lex.europa.eu/eli/reg/2018/858/oj")
        self.assertEqual(urls["odkaz_hlavni"], "https://a/x")

    def test_without_overrides_nothing_changes(self):
        urls = {f: u for _, f, u in ff.iter_fetch_targets(self.RECORDS)}
        self.assertEqual(urls["odkaz_eu"], "https://eur-lex.europa.eu/eli/dir/2018/858/oj")

    def test_missing_overrides_file_is_an_empty_mapping(self):
        self.assertEqual(ff.load_url_overrides("/nonexistent/overrides.json"), {})

    def test_the_committed_overrides_are_well_formed(self):
        for key, value in ff.load_url_overrides().items():
            self.assertEqual(key.count("|") >= 2, True, key)
            self.assertTrue(value["url"].startswith("https://"))
            self.assertTrue(value["reason"])


class AuditManifestTestCase(unittest.TestCase):
    def setUp(self):
        import tempfile
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = pathlib.Path(tmp.name)
        (self.root / "data" / "fulltext").mkdir(parents=True)
        (self.root / "data/fulltext/bad.html").write_bytes(SEARCH_PAGE)
        (self.root / "data/fulltext/good.html").write_bytes(ACT_PAGE)
        eur = "https://eur-lex.europa.eu/eli/reg/x/oj"
        self.manifest = {
            "S|A|odkaz_hlavni": {"status": "fetched", "url": eur, "local_path": "data/fulltext/bad.html"},
            "S|A|odkaz_eu": {"status": "fetched", "url": eur, "local_path": "data/fulltext/bad.html"},
            "S|B|odkaz_hlavni": {"status": "fetched", "url": eur, "local_path": "data/fulltext/good.html"},
        }

    def test_dry_run_reports_and_changes_nothing(self):
        bad = ff.audit_manifest(self.manifest, self.root)
        self.assertEqual([k for k, _, _ in bad], ["S|A|odkaz_eu", "S|A|odkaz_hlavni"])
        self.assertEqual(self.manifest["S|A|odkaz_hlavni"]["status"], "fetched")
        self.assertTrue((self.root / "data/fulltext/bad.html").exists())

    def test_apply_marks_failed_and_deletes_the_shared_file_once(self):
        ff.audit_manifest(self.manifest, self.root, apply=True)
        self.assertEqual(self.manifest["S|A|odkaz_hlavni"]["status"], "failed")
        self.assertEqual(self.manifest["S|A|odkaz_eu"]["status"], "failed")
        self.assertFalse((self.root / "data/fulltext/bad.html").exists())
        self.assertEqual(self.manifest["S|B|odkaz_hlavni"]["status"], "fetched")
        self.assertTrue((self.root / "data/fulltext/good.html").exists())

    def test_a_good_file_still_used_by_a_fetched_entry_is_never_deleted(self):
        self.manifest["S|C|odkaz_hlavni"] = {"status": "fetched", "url": "https://eur-lex.europa.eu/eli/reg/y/oj",
                                             "local_path": "data/fulltext/bad.html"}
        self.manifest["S|C|odkaz_hlavni"]["url"] = "https://www.zakonyprolidi.cz/cs/x"  # a different host: its check passes
        ff.audit_manifest(self.manifest, self.root, apply=True)
        self.assertTrue((self.root / "data/fulltext/bad.html").exists())


SLOVLEX_SHELL = b"<!doctype html><html lang='sk'><head><title>Slov-Lex</title></head><body><app-root></app-root></body></html>"
SLOVLEX_ACT = ("<html><head><title>124/2000 Z. z. Vyhláška</title></head><body><div class='predpis'>"
               "<div class='predpisOznacenie'>124</div></div></body></html>").encode("utf-8")
SLOVLEX_HISTORY = b"<html><head><title>Historia predpisu 96/2004 Z. z.</title></head><body>History</body></html>"
SLOVLEX_URL = "https://www.slov-lex.sk/pravne-predpisy/SK/ZZ/2000/124/"


class SlovLexTestCase(unittest.TestCase):
    def test_the_empty_shell_is_not_a_document(self):
        ok, reason = ff.is_document_page(SLOVLEX_URL, SLOVLEX_SHELL, "text/html", "124/2000 Z. z.")
        self.assertFalse(ok)
        self.assertIn("Slov-Lex", reason)

    def test_a_history_page_is_not_a_document(self):
        self.assertFalse(ff.is_document_page(SLOVLEX_URL, SLOVLEX_HISTORY, "text/html")[0])

    def test_the_rendered_act_is_a_document_and_must_carry_the_records_designation(self):
        self.assertTrue(ff.is_document_page(SLOVLEX_URL, SLOVLEX_ACT, "text/html", "124/2000 Z. z.")[0])
        ok, reason = ff.is_document_page(SLOVLEX_URL, SLOVLEX_ACT, "text/html", "125/2000 Z. z.")
        self.assertFalse(ok)
        self.assertIn("different act", reason)

    def test_designation_numbers(self):
        self.assertEqual(ff.designation_numbers("124/2000 Z. z."), {"124/2000"})
        self.assertEqual(ff.designation_numbers("(EU) 2019/2144"), {"2019/2144"})
        self.assertEqual(ff.designation_numbers("ADR 2025"), set())

    def test_slov_lex_always_needs_a_browser_eur_lex_only_for_a_challenge(self):
        self.assertTrue(ff.needs_browser(SLOVLEX_URL, 200, SLOVLEX_SHELL))
        self.assertTrue(ff.needs_browser("https://eur-lex.europa.eu/x", 202, b""))
        self.assertFalse(ff.needs_browser("https://eur-lex.europa.eu/x", 200, b"<html>act</html>"))
        self.assertFalse(ff.needs_browser("https://www.zakonyprolidi.cz/x", 200, b"<html></html>"))


class SlovLexFetchOneTestCase(unittest.TestCase):
    def _run(self, browser):
        import tempfile
        from unittest import mock
        session = mock.MagicMock()
        resp = mock.MagicMock()
        resp.content, resp.status_code, resp.headers = SLOVLEX_SHELL, 200, {"Content-Type": "text/html"}
        resp.raise_for_status.return_value = None
        session.get.return_value = resp
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            with mock.patch.object(ff, "REPO_ROOT", root), mock.patch.object(ff, "FULLTEXT_DIR", root / "data" / "fulltext"), \
                    mock.patch.object(ff, "fetch_with_browser", return_value=browser):
                entry = ff.fetch_one(session, {"zdroj_dat": "S", "znacka": "124/2000 Z. z."}, "odkaz_sk", SLOVLEX_URL)
                written = list((root / "data" / "fulltext").glob("*")) if (root / "data" / "fulltext").exists() else []
        return entry, written

    def test_the_browser_rendered_act_is_stored(self):
        entry, written = self._run((200, SLOVLEX_ACT, "text/html; charset=utf-8"))
        self.assertEqual(entry["status"], "fetched")
        self.assertEqual(len(written), 1)

    def test_without_a_browser_the_shell_is_a_failure_and_not_written(self):
        entry, written = self._run(None)
        self.assertEqual(entry["status"], "failed")
        self.assertEqual(written, [])

    def test_a_browser_that_ends_on_a_history_page_is_a_failure(self):
        entry, written = self._run((200, SLOVLEX_HISTORY, "text/html; charset=utf-8"))
        self.assertEqual(entry["status"], "failed")
        self.assertEqual(written, [])


class PermanentFailureTestCase(unittest.TestCase):
    def test_a_wrong_act_is_permanent_other_failures_are_retried(self):
        self.assertTrue(ff.is_permanent_failure({"status": "failed", "error": "Slov-Lex page is a different act than 100/2001 Sb. ('24/2006')"}))
        self.assertFalse(ff.is_permanent_failure({"status": "failed", "error": "403 Client Error"}))
        self.assertFalse(ff.is_permanent_failure({"status": "failed", "error": "empty response"}))
        self.assertFalse(ff.is_permanent_failure({"status": "fetched"}))
        self.assertFalse(ff.is_permanent_failure({}))


class HtmlAlternativeTestCase(unittest.TestCase):
    PDF = "https://eur-lex.europa.eu/legal-content/CS/TXT/PDF/?uri=CELEX:02022R0869-20250205"

    def test_an_eur_lex_pdf_address_has_an_html_twin_in_the_same_language(self):
        self.assertEqual(ff.html_alternative(self.PDF),
                         "https://eur-lex.europa.eu/legal-content/CS/TXT/HTML/?uri=CELEX:02022R0869-20250205")
        self.assertEqual(ff.html_alternative("https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32014R1300"),
                         "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32014R1300")

    def test_the_qid_the_site_appends_is_dropped_and_the_oj_id_form_is_understood(self):
        self.assertEqual(ff.html_alternative("https://eur-lex.europa.eu/legal-content/CS/TXT/PDF/?uri=CELEX:32014R1304&qid=1751367790372"),
                         "https://eur-lex.europa.eu/legal-content/CS/TXT/HTML/?uri=CELEX:32014R1304")
        self.assertEqual(ff.html_alternative("https://eur-lex.europa.eu/legal-content/CS/TXT/PDF/?uri=CELEX:32018D0010(01)&qid=1"),
                         "https://eur-lex.europa.eu/legal-content/CS/TXT/HTML/?uri=CELEX:32018D0010(01)")
        self.assertEqual(ff.html_alternative("https://eur-lex.europa.eu/legal-content/CS/TXT/PDF/?uri=OJ:L_202401788"),
                         "https://eur-lex.europa.eu/legal-content/CS/TXT/HTML/?uri=OJ:L_202401788")

    def test_a_whole_official_journal_issue_has_no_single_act_twin(self):
        self.assertIsNone(ff.html_alternative("https://eur-lex.europa.eu/legal-content/CS/TXT/PDF/?uri=OJ:L:2014:096:FULL"))

    def test_other_addresses_have_none(self):
        for url in ("https://eur-lex.europa.eu/eli/reg/2022/869/oj", "https://example.test/x.pdf",
                    "https://eur-lex.europa.eu/legal-content/CS/TXT/HTML/?uri=CELEX:32014R1300", "", None):
            self.assertIsNone(ff.html_alternative(url), url)

    def test_a_pdf_target_is_followed_by_its_html_target_under_a_suffixed_field(self):
        records = [{"zdroj_dat": "Haltuf_Dokumenty", "znacka": "(EU) 2022/869", "typ_dokumentu": "Nařízení EU",
                    "odkaz_hlavni": self.PDF, "odkaz_eu": "https://eur-lex.europa.eu/eli/reg/2022/869/oj"}]
        targets = [(f, u) for _, f, u in ff.iter_fetch_targets(records)]
        self.assertEqual(targets, [("odkaz_hlavni", self.PDF),
                                   ("odkaz_hlavni_html", ff.html_alternative(self.PDF)),
                                   ("odkaz_eu", "https://eur-lex.europa.eu/eli/reg/2022/869/oj")])

    def test_an_override_can_name_the_twin_of_a_pdf_that_has_none(self):
        issue = "https://eur-lex.europa.eu/legal-content/CS/TXT/PDF/?uri=OJ:L:2014:096:FULL"
        records = [{"zdroj_dat": "H", "znacka": "2014/34/EU", "typ_dokumentu": "Směrnice EU", "odkaz_eu": issue}]
        twin = "https://eur-lex.europa.eu/legal-content/CS/TXT/HTML/?uri=CELEX:32014L0034"
        overrides = {"H|2014/34/EU|odkaz_eu_html": {"url": twin, "reason": "r"}}
        self.assertEqual([(f, u) for _, f, u in ff.iter_fetch_targets(records, overrides)],
                         [("odkaz_eu", issue), ("odkaz_eu_html", twin)])
        self.assertEqual([f for _, f, _ in ff.iter_fetch_targets(records)], ["odkaz_eu"])

    def test_the_html_twin_gets_its_own_manifest_key(self):
        self.assertEqual(ff.manifest_key("S", "X 1", "odkaz_hlavni" + ff.HTML_SUFFIX), "S|X 1|odkaz_hlavni_html")
        self.assertEqual(ff.designation_of("S|X 1|odkaz_hlavni_html"), "X 1")


class EurLexPdfRoutingTestCase(unittest.TestCase):
    def test_only_eur_lex_pdf_addresses_take_the_download_path(self):
        self.assertTrue(ff.is_eurlex_pdf("https://eur-lex.europa.eu/legal-content/CS/TXT/PDF/?uri=CELEX:32008R1272"))
        self.assertFalse(ff.is_eurlex_pdf("https://eur-lex.europa.eu/legal-content/CS/TXT/HTML/?uri=CELEX:32008R1272"))
        self.assertFalse(ff.is_eurlex_pdf("https://example.test/TXT/PDF/x"))

    def test_a_pdf_the_browser_downloaded_is_stored(self):
        import tempfile
        from unittest import mock
        session = mock.MagicMock()
        resp = mock.MagicMock()
        resp.content, resp.status_code, resp.headers = b"", 202, {"Content-Type": ""}
        resp.raise_for_status.return_value = None
        session.get.return_value = resp
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            with mock.patch.object(ff, "REPO_ROOT", root), mock.patch.object(ff, "FULLTEXT_DIR", root / "data" / "fulltext"), \
                    mock.patch.object(ff, "fetch_with_browser", return_value=(200, b"%PDF-1.4 body", "application/pdf")):
                entry = ff.fetch_one(session, {"zdroj_dat": "S", "znacka": "(ES) 1272/2008"}, "odkaz_hlavni",
                                     "https://eur-lex.europa.eu/legal-content/CS/TXT/PDF/?uri=CELEX:32008R1272")
            self.assertEqual(entry["status"], "fetched")
            self.assertTrue(entry["local_path"].endswith(".pdf"))


class LocalizedUrlTestCase(unittest.TestCase):
    ELI = "https://eur-lex.europa.eu/eli/reg/2022/869/oj"

    def test_an_english_eli_becomes_the_documents_language(self):
        self.assertEqual(ff.localized_url(self.ELI, "CS"), self.ELI + "/ces")
        self.assertEqual(ff.localized_url(self.ELI, "SK"), self.ELI + "/slk")
        self.assertEqual(ff.localized_url(self.ELI, "DE"), self.ELI + "/deu")

    def test_the_ignored_lang_parameter_is_replaced_not_kept(self):
        self.assertEqual(ff.localized_url(self.ELI + "?lang=CS", "CS"), self.ELI + "/ces")

    def test_english_unknown_or_other_languages_change_nothing(self):
        for language in ("EN", None, "FR", ""):
            self.assertEqual(ff.localized_url(self.ELI, language), self.ELI, language)

    def test_an_address_that_already_names_a_language_is_kept(self):
        self.assertEqual(ff.localized_url(self.ELI + "/slk", "CS"), self.ELI + "/slk")
        self.assertEqual(ff.localized_url(self.ELI + "/ces", "CS"), self.ELI + "/ces")

    def test_legal_content_addresses_swap_only_an_english_language_segment(self):
        en = "https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32014R1300&qid=1"
        self.assertEqual(ff.localized_url(en, "CS"), en.replace("/EN/", "/CS/"))
        cs = "https://eur-lex.europa.eu/legal-content/CS/TXT/?uri=CELEX:32000D0096"
        self.assertEqual(ff.localized_url(cs, "SK"), cs)

    def test_other_hosts_and_empty_addresses_are_untouched(self):
        self.assertEqual(ff.localized_url("https://www.zakonyprolidi.cz/cs/2006-183", "CS"), "https://www.zakonyprolidi.cz/cs/2006-183")
        self.assertEqual(ff.localized_url("", "CS"), "")
        self.assertIsNone(ff.localized_url(None, "CS"))


class TargetLanguageTestCase(unittest.TestCase):
    def _targets(self, record, overrides=None, language="CS"):
        from unittest import mock
        with mock.patch.object(ff, "record_language", return_value=language):
            return [(f, u) for _, f, u in ff.iter_fetch_targets([record], overrides)]

    RECORD = {"zdroj_dat": "S", "znacka": "(EU) 2022/869", "typ_dokumentu": "Nařízení EU",
              "odkaz_hlavni": "https://eur-lex.europa.eu/eli/reg/2022/869/oj"}

    def test_the_target_is_fetched_in_the_records_language(self):
        self.assertEqual(self._targets(self.RECORD), [("odkaz_hlavni", self.RECORD["odkaz_hlavni"] + "/ces")])

    def test_an_explicit_override_wins_over_the_language_rule(self):
        pinned = {"S|(EU) 2022/869|odkaz_hlavni": {"url": self.RECORD["odkaz_hlavni"], "reason": "the document is English"}}
        self.assertEqual(self._targets(self.RECORD, pinned), [("odkaz_hlavni", self.RECORD["odkaz_hlavni"])])

    def test_an_unknown_language_leaves_the_address_alone(self):
        self.assertEqual(self._targets(self.RECORD, language=None), [("odkaz_hlavni", self.RECORD["odkaz_hlavni"])])


class StaleEntryTestCase(unittest.TestCase):
    def test_a_fetched_entry_with_another_address_is_stale(self):
        manifest = {"k": {"status": "fetched", "url": "https://a/oj"}}
        self.assertTrue(ff.is_stale(manifest, "k", "https://a/oj/ces"))
        self.assertFalse(ff.is_stale(manifest, "k", "https://a/oj"))

    def test_missing_and_failed_entries_are_not_stale_they_are_simply_not_fetched(self):
        self.assertFalse(ff.is_stale({}, "k", "https://a"))
        self.assertFalse(ff.is_stale({"k": {"status": "failed", "url": "https://old"}}, "k", "https://a"))


class SlovLexHistoryTestCase(unittest.TestCase):
    class FakePage:
        def __init__(self, hrefs):
            self.hrefs, self.selector = hrefs, None

        def eval_on_selector_all(self, selector, script):
            self.selector = selector
            return self.hrefs

    def test_the_newest_listed_version_is_taken_from_the_version_column_only(self):
        page = self.FakePage(["https://x/SK/ZZ/2011/271/vyhlasene_znenie.html", "https://x/SK/ZZ/2011/271/20230315.html"])
        self.assertEqual(ff._slovlex_latest_version_url(page), "https://x/SK/ZZ/2011/271/20230315.html")
        self.assertIn("td.title", page.selector)  # not the "Novela" links to amending acts

    def test_no_versions_listed_gives_none(self):
        self.assertIsNone(ff._slovlex_latest_version_url(self.FakePage([])))


class CommittedManifestTestCase(unittest.TestCase):
    def test_no_fetched_entry_has_another_address_than_the_one_the_record_asks_for(self):
        raw = json.loads(ff.RAW_DB_PATH.read_text(encoding="utf-8"))
        manifest = ff.load_manifest()
        seen, stale = set(), []
        for record, field, url in ff.iter_fetch_targets(raw, ff.load_url_overrides()):
            key = ff.manifest_key(record["zdroj_dat"], record["znacka"].strip(), field)
            if key not in seen and not seen.add(key) and ff.is_stale(manifest, key, url):
                stale.append(key)
        self.assertEqual(stale, [], "fetch_fulltext.py would fetch these again")

class LanguageVariantTargetsTestCase(unittest.TestCase):
    def rows(self):
        base = {"zdroj_dat": "Haltuf_Dokumenty", "znacka": "2014/68/EU", "typ_dokumentu": "Směrnice EU"}
        return [{**base, "jazyk": "CZ", "odkaz_hlavni": "https://eur-lex.europa.eu/legal-content/CS/TXT/HTML/?uri=CELEX:32014L0068"},
                {**base, "jazyk": "EN", "odkaz_hlavni": "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32014L0068"}]

    def test_the_english_row_of_an_act_with_a_czech_row_is_filed_under_its_own_designation(self):
        targets = [(r["znacka"], f, u) for r, f, u in ff.iter_fetch_targets(self.rows())]
        self.assertEqual([(z, f) for z, f, _ in targets], [("2014/68/EU", "odkaz_hlavni"), ("2014/68/EU [EN]", "odkaz_hlavni")])
        self.assertIn("/legal-content/CS/", targets[0][2])
        self.assertIn("/legal-content/EN/", targets[1][2])

    def test_a_lone_english_row_keeps_its_designation(self):
        targets = [r["znacka"] for r, _, _ in ff.iter_fetch_targets(self.rows()[1:])]
        self.assertEqual(targets, ["2014/68/EU"])


if __name__ == "__main__":
    unittest.main()
