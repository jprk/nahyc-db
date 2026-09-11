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
    def test_norms_sources_excluded(self):
        self.assertFalse(ff.is_fetchable_source("Prokop_Normy"))
        self.assertFalse(ff.is_fetchable_source("Sinay_Normy"))

    def test_law_sources_included(self):
        self.assertTrue(ff.is_fetchable_source("Haltuf_Dokumenty"))
        self.assertTrue(ff.is_fetchable_source("Sinay_Zakony"))


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
    def test_skips_norm_sources_even_with_url(self):
        raw = [{"zdroj_dat": "Prokop_Normy", "znacka": "ISO 14687",
                "odkaz_hlavni": "https://iso.org/standards.html"}]
        self.assertEqual(list(ff.iter_fetch_targets(raw)), [])

    def test_skips_norm_shaped_znacka_even_from_a_law_source(self):
        # Real corpus case: Haltuf_Dokumenty (a law source) also carried a
        # stray "ČSN EN 17127" entry, fetched before this fix.
        raw = [{"zdroj_dat": "Haltuf_Dokumenty", "znacka": "ČSN EN 17127",
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

    def test_writes_file_and_records_success(self):
        session = MagicMock()
        resp = MagicMock()
        resp.content = b"%PDF-1.4 fake content"
        resp.status_code = 200
        resp.headers = {"Content-Type": "application/pdf"}
        resp.raise_for_status.return_value = None
        session.get.return_value = resp

        record = {"zdroj_dat": "__test_source__", "znacka": "TEST/2026"}
        try:
            entry = ff.fetch_one(session, record, "odkaz_hlavni", "https://example.com/doc")
            self.assertEqual(entry["status"], "fetched")
            self.assertTrue((ff.REPO_ROOT / entry["local_path"]).exists())
            self.assertEqual((ff.REPO_ROOT / entry["local_path"]).read_bytes(), resp.content)
        finally:
            out_dir = ff.REPO_ROOT / "data" / "fulltext" / "__test_source__"
            for f in out_dir.glob("*"):
                f.unlink()
            if out_dir.exists():
                out_dir.rmdir()


if __name__ == "__main__":
    unittest.main()
