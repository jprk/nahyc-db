import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))

from harvest_iec_publications import (clean_description, is_amendment_or_corrigendum,
                                       reference_base)


class ReferenceBaseTestCase(unittest.TestCase):
    def test_strips_edition_year(self):
        self.assertEqual(reference_base("IEC 60050-102:2007"), "IEC 60050-102")

    def test_strips_amendment_chain_too(self):
        self.assertEqual(reference_base("IEC 60050-102:2007/AMD1:2017"), "IEC 60050-102")

    def test_already_bare_is_unchanged(self):
        self.assertEqual(reference_base("IEC 60050-102"), "IEC 60050-102")

    def test_blank(self):
        self.assertEqual(reference_base(""), "")
        self.assertEqual(reference_base(None), "")


class IsAmendmentOrCorrigendumTestCase(unittest.TestCase):
    def test_amendment_reference(self):
        self.assertTrue(is_amendment_or_corrigendum("IEC 60050-102:2007/AMD1:2017"))

    def test_corrigendum_reference(self):
        self.assertTrue(is_amendment_or_corrigendum("IEC 60034-1:2022/COR1:2023"))

    def test_base_reference_is_not(self):
        self.assertFalse(is_amendment_or_corrigendum("IEC 60050-102:2007"))

    def test_blank(self):
        self.assertFalse(is_amendment_or_corrigendum(""))
        self.assertFalse(is_amendment_or_corrigendum(None))


class CleanDescriptionTestCase(unittest.TestCase):
    def test_strips_br_tags(self):
        text = clean_description("First sentence.<br />Second sentence.")
        self.assertEqual(text, "First sentence. Second sentence.")

    def test_strips_full_html_markup_and_comments(self):
        # Regression guard: an early version only stripped <br/>, leaving
        # <!-- NEW! --><a href="...">...</a> announcement blurbs (a real
        # pattern in the live export) in the description verbatim.
        text = clean_description(
            '<!-- NEW! -->IEC 60034-1:2026 is available as '
            '<a href="https://webstore.iec.ch/publication/112762">IEC 60034-1:2026 RLV</a> '
            'which contains the standard.')
        self.assertNotIn("<", text)
        self.assertNotIn("-->", text)
        self.assertIn("IEC 60034-1:2026 RLV", text)

    def test_strips_excel_carriage_return_artifact(self):
        text = clean_description("First part._x000D_\nSecond part.")
        self.assertNotIn("_x000D_", text)

    def test_blank_or_none_returns_none(self):
        self.assertIsNone(clean_description(""))
        self.assertIsNone(clean_description(None))

    def test_whitespace_only_after_cleaning_returns_none(self):
        self.assertIsNone(clean_description("<br />"))


if __name__ == "__main__":
    unittest.main()
