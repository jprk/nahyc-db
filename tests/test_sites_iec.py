import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from sites.iec import lookup, normalize_designation

_INDEX = {
    "IEC 62351-14": {"title": "Power systems management - Part 14: Security event logging",
                     "description": "Defines requirements for security event logging."},
    "IEC 60092-506": {"title": "Electrical installations in ships - Part 506",
                     "description": "Specifies requirements for electrical installations."},
}


class NormalizeDesignationTestCase(unittest.TestCase):
    def test_bare_designation_is_unchanged(self):
        self.assertEqual(normalize_designation("IEC 62351-14"), "IEC 62351-14")

    def test_strips_sinay_edition_suffix(self):
        self.assertEqual(normalize_designation("IEC/TR 62351-13/ - 2016.08"), "IEC TR 62351-13")
        self.assertEqual(normalize_designation("IEC 60092-506/ - 2003.06"), "IEC 60092-506")

    def test_strips_pren_prefix(self):
        # "prEN IEC ..." is the corpus's own marker for a draft European
        # adoption — not part of the IEC document's own identity.
        self.assertEqual(normalize_designation("prEN IEC 63341-2"), "IEC 63341-2")

    def test_slash_type_marker_becomes_space_separated(self):
        # The corpus writes "IEC/TR"/"IEC/TS"/"IEC/PAS"; IEC's own
        # catalog (and the harvested index) writes "IEC TR"/"IEC TS"/
        # "IEC PAS" — confirmed live for "IEC TR 62351-13:2016".
        self.assertEqual(normalize_designation("IEC/TR 62351-13/ - 2016.08"), "IEC TR 62351-13")
        self.assertEqual(normalize_designation("IEC/TS 63208/ - 2020.03"), "IEC TS 63208")

    def test_blank_returns_none(self):
        self.assertIsNone(normalize_designation(""))
        self.assertIsNone(normalize_designation(None))


class LookupTestCase(unittest.TestCase):
    def test_finds_an_exact_match(self):
        result = lookup("IEC 62351-14", _INDEX)
        self.assertEqual(result["title"], "Power systems management - Part 14: Security event logging")
        self.assertIn("security event logging", result["description"])

    def test_finds_a_match_after_normalization(self):
        result = lookup("IEC 60092-506/ - 2003.06", _INDEX)
        self.assertIsNotNone(result)
        self.assertIn("electrical installations", result["description"])

    def test_not_in_index_returns_none(self):
        # Never guesses at a draft/not-yet-published document.
        self.assertIsNone(lookup("prEN IEC 63341-2", _INDEX))

    def test_blank_designation_returns_none(self):
        self.assertIsNone(lookup("", _INDEX))


if __name__ == "__main__":
    unittest.main()
