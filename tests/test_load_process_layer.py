import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))

from load_process_layer import (
    normalize_citation_core, document_identifier_digit_core,
    build_document_lookup, match_citation,
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


class BuildDocumentLookupTestCase(unittest.TestCase):
    def test_builds_both_lookup_tables(self):
        by_digits, by_text = build_document_lookup(
            ["283/2021 Sb.", "(EU) 2023/1804", "ČSN EN 17124"])
        self.assertEqual(by_digits["283/2021"], "283/2021 Sb.")
        self.assertEqual(by_digits["2023/1804"], "(EU) 2023/1804")
        self.assertEqual(by_text["ČSN EN 17124"], "ČSN EN 17124")
        self.assertNotIn("ČSN EN 17124", by_digits)

    def test_stn_and_csn_do_not_collide(self):
        # Slovak STN and Czech ČSN adoptions of the same EN number are
        # legally distinct (see doc/PLAN.md Step 1 follow-up #9) -- the
        # text-core lookup must never conflate them.
        by_digits, by_text = build_document_lookup(
            ["ČSN EN 17124", "STN EN 17124/ - 2022.06"])
        self.assertEqual(by_text["ČSN EN 17124"], "ČSN EN 17124")
        self.assertNotIn("STN EN 17124", by_text)


class MatchCitationTestCase(unittest.TestCase):
    def setUp(self):
        self.by_digits, self.by_text = build_document_lookup(
            ["283/2021 Sb.", "(EU) 2023/1804", "ČSN EN 17124"])

    def test_matches_law_by_digit_core(self):
        self.assertEqual(match_citation("283/2021", self.by_digits, self.by_text), "283/2021 Sb.")

    def test_matches_eu_regulation_by_digit_core(self):
        self.assertEqual(match_citation("2023/1804", self.by_digits, self.by_text), "(EU) 2023/1804")

    def test_matches_norm_by_exact_text(self):
        self.assertEqual(match_citation("ČSN EN 17124", self.by_digits, self.by_text), "ČSN EN 17124")

    def test_unmatched_citation_gives_none(self):
        self.assertIsNone(match_citation("999/2099", self.by_digits, self.by_text))


if __name__ == "__main__":
    unittest.main()
