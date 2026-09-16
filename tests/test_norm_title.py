import os
import sys
import unittest

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "tools"))

from norm_title import designation_core, format_norm_title, is_real_designation


class DesignationCoreTestCase(unittest.TestCase):
    def test_strips_the_sinay_edition_artifact(self):
        self.assertEqual(designation_core("STN EN 61982-4/ - 2016.08"), "STN EN 61982-4")
        self.assertEqual(designation_core("IEC/TR 62351-13/ - 2016.08"), "IEC/TR 62351-13")

    def test_strips_an_en_dash_edition_artifact_too(self):
        # 17 records kept their edition date purely because the source
        # mixes ASCII "-" with en-dashes (bug found 2026-09-16).
        self.assertEqual(designation_core("STN EN 13365/A1 – 2003.08"), "STN EN 13365/A1")
        self.assertEqual(designation_core("STN 65 1312-2/ – 1990.09"), "STN 65 1312-2")

    def test_strips_a_bare_trailing_edition_year(self):
        # US/Australian designations legitimately carry one.
        self.assertEqual(designation_core("ASME B31.12-2019"), "ASME B31.12")
        self.assertEqual(designation_core("AS B12-1931"), "AS B12")

    def test_keeps_a_trailing_number_that_is_not_a_year(self):
        # Regression guard (2026-09-16): stripping any -NNNN turned
        # "ZP-5101" into "ZP" and collided two unrelated records.
        self.assertEqual(designation_core("ZP-5101"), "ZP-5101")
        self.assertEqual(designation_core("Sandia Report SAND2012-7321"),
                         "Sandia Report SAND2012-7321")

    def test_designation_without_a_suffix_is_untouched(self):
        self.assertEqual(designation_core("ČSN EN 17124"), "ČSN EN 17124")

    def test_blank_input(self):
        self.assertEqual(designation_core(None), "")
        self.assertEqual(designation_core(""), "")


class IsRealDesignationTestCase(unittest.TestCase):
    def test_designations_contain_a_digit(self):
        self.assertTrue(is_real_designation("ČSN EN 17124"))
        self.assertTrue(is_real_designation("G 260 (A)"))

    def test_title_copies_and_fragments_are_rejected(self):
        # Records with no number in the source get a copy of their own
        # title in `identifier`; that must not be treated as a number.
        self.assertFalse(is_real_designation("AGBF- Leitfaden – Wasserstoff"))
        self.assertFalse(is_real_designation("Publikation VDI Praxis"))

    def test_blank(self):
        self.assertFalse(is_real_designation(None))
        self.assertFalse(is_real_designation(""))


class FormatNormTitleTestCase(unittest.TestCase):
    def test_prefixes_the_designation(self):
        title, changed = format_norm_title("Vodíkové palivo", "ČSN EN 17124")
        self.assertTrue(changed)
        self.assertEqual(title, "ČSN EN 17124 — Vodíkové palivo")

    def test_edition_artifact_never_reaches_the_title(self):
        title, _ = format_norm_title("Akumulátorové batérie", "STN EN 61982-4/ - 2016.08")
        self.assertEqual(title, "STN EN 61982-4 — Akumulátorové batérie")

    def test_trailing_parenthesised_designation_is_moved_to_the_front(self):
        # The only embedded shape found in the corpus.
        title, _ = format_norm_title(
            "Power systems management (IEC/TR 62351-13:2016)", "IEC/TR 62351-13/ - 2016.08")
        self.assertEqual(title, "IEC/TR 62351-13 — Power systems management")

    def test_leading_designation_is_not_duplicated(self):
        title, _ = format_norm_title("ČSN EN 17124 — Vodíkové palivo", "ČSN EN 17124")
        self.assertEqual(title, "ČSN EN 17124 — Vodíkové palivo")

    def test_is_idempotent(self):
        once, _ = format_norm_title("Vodíkové palivo", "ČSN EN 17124")
        twice, _ = format_norm_title(once, "ČSN EN 17124")
        self.assertEqual(once, twice)

    def test_without_a_real_designation_the_title_is_untouched(self):
        original = "AGBF- Leitfaden – Wasserstoff und dessen Gefahren"
        title, changed = format_norm_title(original, "AGBF- Leitfaden – Wasserstoff")
        self.assertFalse(changed)
        self.assertEqual(title, original)

    def test_no_identifier_leaves_the_title_alone(self):
        title, changed = format_norm_title("Hydrogen Leak Detector", None)
        self.assertFalse(changed)
        self.assertEqual(title, "Hydrogen Leak Detector")

    def test_title_that_is_only_the_designation_does_not_become_empty(self):
        title, changed = format_norm_title("ČSN EN 17124", "ČSN EN 17124")
        self.assertTrue(changed)
        self.assertIn("ČSN EN 17124", title)
        self.assertTrue(title.strip())


if __name__ == "__main__":
    unittest.main()
