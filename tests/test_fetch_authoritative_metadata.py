import pathlib
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from fetch_authoritative_metadata import (
    is_law_record, is_csn_norm_record, csn_core, record_url,
    dispatch_site_module, fetch_csn_metadata, is_bare_international_znacka,
    bare_jurisdikce_tier,
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
    """doc/PLAN.md §9: widened from Prokop_Normy-only, ČSN-prefix-only to
    also cover Haltuf_Dokumenty/Sinay_Normy and bare EN/ISO/IEC
    designations (the international original, not yet/never separately
    ČSN-numbered in the corpus's own znacka)."""

    def test_prokop_normy_with_csn_znacka(self):
        self.assertTrue(is_csn_norm_record({"zdroj_dat": "Prokop_Normy", "znacka": "ČSN ISO 14687"}))
        self.assertTrue(is_csn_norm_record({"zdroj_dat": "Prokop_Normy", "znacka": "CSN EN 17127"}))

    def test_eligible_source_with_bare_international_designation_is_true(self):
        self.assertTrue(is_csn_norm_record({"zdroj_dat": "Prokop_Normy", "znacka": "ISO 14687"}))
        self.assertTrue(is_csn_norm_record({"zdroj_dat": "Haltuf_Dokumenty", "znacka": "EN 17339"}))
        self.assertTrue(is_csn_norm_record({"zdroj_dat": "Sinay_Normy", "znacka": "IEC 60079-0"}))

    def test_other_national_prefix_is_false(self):
        # An STN/DIN/etc. designation is a different country's own
        # national adoption, not a bare international original.
        self.assertFalse(is_csn_norm_record({"zdroj_dat": "Sinay_Normy", "znacka": "STN EN 17127"}))

    def test_non_eligible_source_is_false_even_with_csn_znacka(self):
        self.assertFalse(is_csn_norm_record({"zdroj_dat": "Sinay_Zakony", "znacka": "ČSN ISO 14687"}))


class IsBareInternationalZnackaTestCase(unittest.TestCase):
    def test_bare_en_iso_iec_is_true(self):
        self.assertTrue(is_bare_international_znacka("EN 17127"))
        self.assertTrue(is_bare_international_znacka("ISO 14687"))
        self.assertTrue(is_bare_international_znacka("IEC 60079-0"))
        self.assertTrue(is_bare_international_znacka("EN ISO 19880-1"))

    def test_csn_prefixed_is_false(self):
        self.assertFalse(is_bare_international_znacka("ČSN EN 17127"))
        self.assertFalse(is_bare_international_znacka("CSN ISO 14687"))

    def test_other_national_prefix_is_false(self):
        self.assertFalse(is_bare_international_znacka("STN EN 17127"))
        self.assertFalse(is_bare_international_znacka(""))


class BareJurisdikceTierTestCase(unittest.TestCase):
    def test_bare_iso_iec_is_mezinarodni(self):
        self.assertEqual(bare_jurisdikce_tier("ISO 14687"), "mezinárodní")
        self.assertEqual(bare_jurisdikce_tier("IEC 60079-0"), "mezinárodní")

    def test_bare_en_is_eu(self):
        self.assertEqual(bare_jurisdikce_tier("EN 17127"), "EU")
        self.assertEqual(bare_jurisdikce_tier("EN ISO 19880-1"), "EU")


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
    def setUp(self):
        import fetch_authoritative_metadata as mod
        self.mod = mod
        self._orig_search = mod.csn_search
        self._orig_detail = mod.csn_fetch_detail
        self.addCleanup(setattr, mod, "csn_search", self._orig_search)
        self.addCleanup(setattr, mod, "csn_fetch_detail", self._orig_detail)
        mod.csn_fetch_detail = lambda catalog_number, session: None

    def test_exact_designation_match_returns_its_title(self):
        session = MagicMock()
        results = [
            {"designation": "ČSN ISO 14687", "title": "Real title", "is_valid": True, "catalog_number": ""},
            {"designation": "ČSN EN ISO 14687", "title": "Different edition", "is_valid": False, "catalog_number": ""},
        ]
        self.mod.csn_search = lambda s, q: results
        result = fetch_csn_metadata("ČSN ISO 14687", session)
        self.assertEqual(result["title"], "Real title")
        self.assertIsNone(result["description"])
        self.assertEqual(result["csn_designation"], "ČSN ISO 14687")

    def test_no_exact_match_is_none(self):
        self.mod.csn_search = lambda s, q: [{"designation": "ČSN EN ISO 14687", "title": "x", "is_valid": True, "catalog_number": ""}]
        session = MagicMock()
        result = fetch_csn_metadata("ČSN ISO 14687", session)
        self.assertIsNone(result)

    def test_blank_znacka_is_none(self):
        session = MagicMock()
        self.assertIsNone(fetch_csn_metadata("", session))

    def test_bare_designation_returns_english_title_from_detail_page(self):
        # doc/PLAN.md §9: a bare "EN 17127" resolves against "ČSN EN
        # 17127" and picks up the English title from the detail page.
        self.mod.csn_search = lambda s, q: [
            {"designation": "ČSN EN 17127", "title": "Český název", "is_valid": True, "catalog_number": "123"},
        ]
        self.mod.csn_fetch_detail = lambda catalog_number, session: {
            "designation": "ČSN EN 17127", "title": "Český název",
            "title_en": "English title", "incorporates": [], "url": "https://example/123",
        }
        result = fetch_csn_metadata("EN 17127", MagicMock())
        self.assertEqual(result["title_en"], "English title")
        self.assertEqual(result["csn_designation"], "ČSN EN 17127")
        self.assertEqual(result["zdroj_autoritativni_url"], "https://example/123")

    def test_spurious_en_fallback_retries_without_en(self):
        # doc/PLAN.md §9: "ČSN EN ISO 19880-1" is a corpus-side mistake —
        # the real designation is "ČSN ISO 19880-1", found only on retry.
        calls = []

        def fake_search(session, query):
            calls.append(query)
            if query == "EN ISO 19880-1":
                return []
            return [{"designation": "ČSN ISO 19880-1", "title": "Plynný vodík", "is_valid": True, "catalog_number": ""}]

        self.mod.csn_search = fake_search
        result = fetch_csn_metadata("EN ISO 19880-1", MagicMock())
        self.assertIsNotNone(result)
        self.assertEqual(result["csn_designation"], "ČSN ISO 19880-1")
        self.assertEqual(calls, ["EN ISO 19880-1", "ISO 19880-1"])

    def test_spurious_en_fallback_also_applies_to_already_csn_prefixed_znacka(self):
        # doc/PLAN.md §9 follow-up: the same corpus mistake also shows up
        # already ČSN-prefixed ("ČSN EN ISO 19880-1", not just bare) —
        # found live after a dedup merge dropped a resolved title because
        # only the OTHER (correctly-spelled) sibling row had resolved.
        calls = []

        def fake_search(session, query):
            calls.append(query)
            if query == "EN ISO 19880-1":
                return []
            return [{"designation": "ČSN ISO 19880-1", "title": "Plynný vodík", "is_valid": True, "catalog_number": ""}]

        self.mod.csn_search = fake_search
        result = fetch_csn_metadata("ČSN EN ISO 19880-1", MagicMock())
        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "Plynný vodík")
        self.assertEqual(result["csn_designation"], "ČSN ISO 19880-1")
        self.assertIsNone(result["title_en"])  # not a bare znacka — stays Czech-only

    def test_non_en_iso_iec_bare_designation_gets_no_fallback(self):
        self.mod.csn_search = lambda s, q: []
        result = fetch_csn_metadata("ISO 14687", MagicMock())
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
