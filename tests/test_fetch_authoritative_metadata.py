import pathlib
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from fetch_authoritative_metadata import (
    is_law_record, is_csn_norm_record, csn_core, record_url,
    dispatch_site_module, fetch_csn_metadata,
)
from sites import eurlex, zakonyprolidi, slovlex


class IsLawRecordTestCase(unittest.TestCase):
    def test_single_law_source(self):
        self.assertTrue(is_law_record({"zdroj_dat": "Haltuf_Dokumenty"}))
        self.assertTrue(is_law_record({"zdroj_dat": "Sinay_Zakony"}))
        self.assertTrue(is_law_record({"zdroj_dat": "EU_Transposition_Targets"}))
        self.assertTrue(is_law_record({"zdroj_dat": "V02_Bibliografie"}))

    def test_merged_source_with_at_least_one_law_component(self):
        self.assertTrue(is_law_record({"zdroj_dat": "Sinay_Zakony, Haltuf_Dokumenty"}))
        self.assertTrue(is_law_record({"zdroj_dat": "Prokop_Normy, Haltuf_Dokumenty"}))

    def test_norm_only_source_is_false(self):
        self.assertFalse(is_law_record({"zdroj_dat": "Prokop_Normy"}))
        self.assertFalse(is_law_record({"zdroj_dat": "Sinay_Normy"}))


class IsCsnNormRecordTestCase(unittest.TestCase):
    def test_prokop_normy_with_csn_znacka(self):
        self.assertTrue(is_csn_norm_record({"zdroj_dat": "Prokop_Normy", "znacka": "ČSN ISO 14687"}))
        self.assertTrue(is_csn_norm_record({"zdroj_dat": "Prokop_Normy", "znacka": "CSN EN 17127"}))

    def test_prokop_normy_without_csn_prefix_is_false(self):
        self.assertFalse(is_csn_norm_record({"zdroj_dat": "Prokop_Normy", "znacka": "ISO 14687"}))

    def test_non_prokop_source_is_false_even_with_csn_znacka(self):
        self.assertFalse(is_csn_norm_record({"zdroj_dat": "Sinay_Normy", "znacka": "ČSN ISO 14687"}))


class CsnCoreTestCase(unittest.TestCase):
    def test_strips_csn_prefix(self):
        self.assertEqual(csn_core("ČSN ISO 14687"), "ISO 14687")
        self.assertEqual(csn_core("CSN EN 17127"), "EN 17127")

    def test_blank_is_blank(self):
        self.assertEqual(csn_core(""), "")
        self.assertEqual(csn_core(None), "")


class RecordUrlTestCase(unittest.TestCase):
    def test_prefers_odkaz_hlavni(self):
        item = {"odkaz_hlavni": "https://a", "odkaz_eu": "https://b", "odkaz_sk": "https://c"}
        self.assertEqual(record_url(item), "https://a")

    def test_falls_back_in_order(self):
        self.assertEqual(record_url({"odkaz_eu": "https://b", "odkaz_sk": "https://c"}), "https://b")
        self.assertEqual(record_url({"odkaz_sk": "https://c"}), "https://c")

    def test_no_url_is_empty_string(self):
        self.assertEqual(record_url({}), "")


class DispatchSiteModuleTestCase(unittest.TestCase):
    def test_dispatches_each_known_domain(self):
        self.assertIs(dispatch_site_module("https://eur-lex.europa.eu/eli/dir/2019/692/oj"), eurlex)
        self.assertIs(dispatch_site_module("https://www.zakonyprolidi.cz/cs/2006-183"), zakonyprolidi)
        self.assertIs(dispatch_site_module("https://www.slov-lex.sk/pravne-predpisy/SK/ZZ/2000/124/"), slovlex)

    def test_unknown_domain_is_none(self):
        self.assertIsNone(dispatch_site_module("https://www.dvgw.de/"))


class FetchCsnMetadataTestCase(unittest.TestCase):
    def test_exact_designation_match_returns_its_title(self):
        session = MagicMock()
        results = [
            {"designation": "ČSN ISO 14687", "title": "Real title", "is_valid": True},
            {"designation": "ČSN EN ISO 14687", "title": "Different edition", "is_valid": False},
        ]
        import fetch_authoritative_metadata as mod
        mod.csn_search = lambda s, q: results
        result = fetch_csn_metadata("ČSN ISO 14687", session)
        self.assertEqual(result, {"title": "Real title", "description": None})

    def test_no_exact_match_is_none(self):
        import fetch_authoritative_metadata as mod
        mod.csn_search = lambda s, q: [{"designation": "ČSN EN ISO 14687", "title": "x", "is_valid": True}]
        session = MagicMock()
        result = fetch_csn_metadata("ČSN ISO 14687", session)
        self.assertIsNone(result)

    def test_blank_znacka_is_none(self):
        session = MagicMock()
        self.assertIsNone(fetch_csn_metadata("", session))


if __name__ == "__main__":
    unittest.main()
