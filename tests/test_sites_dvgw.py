import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from sites.dvgw import lookup, normalize_designation

_INDEX = {
    "G 100": {"title": "Code of Practice G 100",
             "description": "Qualification requirements for experts."},
    "GW 302-1": {"title": "Code of Practice GW 302-1",
                "description": "Requirements for gas/water installations."},
}


class NormalizeDesignationTestCase(unittest.TestCase):
    def test_strips_arbeitsblatt_status_suffix(self):
        self.assertEqual(normalize_designation("G 260 (A)"), "G 260")

    def test_strips_merkblatt_status_suffix(self):
        self.assertEqual(normalize_designation("G 404 (M)"), "G 404")

    def test_no_suffix_is_unchanged(self):
        self.assertEqual(normalize_designation("G 685-1"), "G 685-1")

    def test_blank_returns_none(self):
        self.assertIsNone(normalize_designation(""))
        self.assertIsNone(normalize_designation(None))


class LookupTestCase(unittest.TestCase):
    def test_finds_a_match_after_normalization(self):
        result = lookup("G 100", _INDEX)
        self.assertIsNotNone(result)
        self.assertIn("Qualification requirements", result["description"])

    def test_finds_a_match_with_status_suffix(self):
        result = lookup("GW 302-1 (A)", _INDEX)
        self.assertIsNotNone(result)
        self.assertIn("gas/water", result["description"])

    def test_not_in_index_returns_none(self):
        # The expected, common case — most DVGW designations aren't in
        # this site's curated listings at all.
        self.assertIsNone(lookup("G 260 (A)", _INDEX))

    def test_blank_designation_returns_none(self):
        self.assertIsNone(lookup("", _INDEX))


if __name__ == "__main__":
    unittest.main()
