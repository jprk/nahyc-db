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


if __name__ == "__main__":
    unittest.main()
