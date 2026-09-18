import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))

from load_process_layer import (
    normalize_citation_core, document_identifier_digit_core,
    build_document_lookup, match_citations, eu_core_designation, strip_national_prefix,
)


class NormalizeCitationCoreTestCase(unittest.TestCase):
    def test_bare_digit_slash_is_digits_kind(self):
        self.assertEqual(normalize_citation_core("283/2021"), ("digits", "283/2021"))

    def test_norm_code_is_text_kind(self):
        self.assertEqual(normalize_citation_core("ČSN EN 17124"), ("text", "ČSN EN 17124"))

    def test_whitespace_collapsed_for_text_kind(self):
        self.assertEqual(normalize_citation_core("ČSN  EN   17124"), ("text", "ČSN EN 17124"))


class DocumentIdentifierDigitCoreTestCase(unittest.TestCase):
    def test_czech_law(self):
        self.assertEqual(document_identifier_digit_core("283/2021 Sb."), "283/2021")

    def test_eu_regulation(self):
        self.assertEqual(document_identifier_digit_core("(EU) 2023/1804"), "2023/1804")

    def test_norm_code_has_no_digit_slash_pair(self):
        self.assertIsNone(document_identifier_digit_core("ČSN EN 17124"))


class StripNationalPrefixTestCase(unittest.TestCase):
    def test_strips_csn(self):
        self.assertEqual(strip_national_prefix("ČSN EN 17124"), "EN 17124")

    def test_strips_stn_case_insensitively(self):
        self.assertEqual(strip_national_prefix("stn EN ISO 17268"), "EN ISO 17268")

    def test_no_prefix_is_unchanged(self):
        self.assertEqual(strip_national_prefix("EN 17124"), "EN 17124")

    def test_empty_is_unchanged(self):
        self.assertEqual(strip_national_prefix(""), "")
        self.assertEqual(strip_national_prefix(None), "")


class EuCoreDesignationTestCase(unittest.TestCase):
    def test_csn_identifier(self):
        self.assertEqual(eu_core_designation("ČSN EN 17124"), "EN 17124")

    def test_stn_identifier_with_edition_suffix(self):
        self.assertEqual(eu_core_designation("STN EN 17124/ - 2022.06"), "EN 17124")

    def test_bare_identifier_maps_to_itself(self):
        self.assertEqual(eu_core_designation("EN 17124"), "EN 17124")

    def test_law_citation_is_unaffected(self):
        # Not a norm code at all -- no national-agency prefix to strip,
        # designation_core() only touches a trailing edition/date suffix.
        self.assertEqual(eu_core_designation("283/2021 Sb."), "283/2021 Sb.")


class BuildDocumentLookupTestCase(unittest.TestCase):
    def test_builds_all_three_lookup_tables(self):
        by_digits, by_text, by_eu_core = build_document_lookup(
            ["283/2021 Sb.", "(EU) 2023/1804", "ČSN EN 17124"])
        self.assertEqual(by_digits["283/2021"], "283/2021 Sb.")
        self.assertEqual(by_digits["2023/1804"], "(EU) 2023/1804")
        self.assertEqual(by_text["ČSN EN 17124"], "ČSN EN 17124")
        self.assertNotIn("ČSN EN 17124", by_digits)

    def test_stn_and_csn_do_not_collide_in_by_text(self):
        # Slovak STN and Czech ČSN adoptions of the same EN number are
        # legally distinct (see doc/PLAN.md Step 1 follow-up #9) -- the
        # exact text-core lookup must never conflate them.
        by_digits, by_text, by_eu_core = build_document_lookup(
            ["ČSN EN 17124", "STN EN 17124/ - 2022.06"])
        self.assertEqual(by_text["ČSN EN 17124"], "ČSN EN 17124")
        self.assertNotIn("STN EN 17124", by_text)

    def test_stn_and_csn_both_gathered_under_the_same_eu_core(self):
        # doc/PLAN.md §35, 2026-09-18, user-directed: this is the
        # deliberate fan-out counterpart to the previous test -- distinct
        # in by_text, but grouped together under by_eu_core so a bare
        # citation can link to every jurisdiction's adoption.
        by_digits, by_text, by_eu_core = build_document_lookup(
            ["ČSN EN 17124", "STN EN 17124/ - 2022.06"])
        self.assertCountEqual(by_eu_core["EN 17124"],
                              ["ČSN EN 17124", "STN EN 17124/ - 2022.06"])


class MatchCitationsTestCase(unittest.TestCase):
    def setUp(self):
        self.by_digits, self.by_text, self.by_eu_core = build_document_lookup(
            ["283/2021 Sb.", "(EU) 2023/1804", "ČSN EN 17124", "STN EN 17124/ - 2022.06",
             "ČSN EN ISO 17268"])

    def test_matches_law_by_digit_core(self):
        self.assertEqual(match_citations("283/2021", self.by_digits, self.by_text, self.by_eu_core),
                         ["283/2021 Sb."])

    def test_matches_eu_regulation_by_digit_core(self):
        self.assertEqual(
            match_citations("2023/1804", self.by_digits, self.by_text, self.by_eu_core),
            ["(EU) 2023/1804"])

    def test_national_prefixed_citation_matches_only_that_one_identifier(self):
        # A citation that already names a specific national adoption is
        # jurisdiction-specific by itself -- never fanned out to a
        # sibling jurisdiction it didn't ask for.
        self.assertEqual(
            match_citations("ČSN EN 17124", self.by_digits, self.by_text, self.by_eu_core),
            ["ČSN EN 17124"])

    def test_bare_eu_designation_fans_out_to_every_jurisdiction(self):
        result = match_citations("EN 17124", self.by_digits, self.by_text, self.by_eu_core)
        self.assertCountEqual(result, ["ČSN EN 17124", "STN EN 17124/ - 2022.06"])

    def test_bare_eu_designation_with_only_one_adoption(self):
        self.assertEqual(
            match_citations("EN ISO 17268", self.by_digits, self.by_text, self.by_eu_core),
            ["ČSN EN ISO 17268"])

    def test_unmatched_citation_gives_empty_list(self):
        self.assertEqual(
            match_citations("999/2099", self.by_digits, self.by_text, self.by_eu_core), [])
        self.assertEqual(
            match_citations("EN 99999", self.by_digits, self.by_text, self.by_eu_core), [])


if __name__ == "__main__":
    unittest.main()
