import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))

from harvest_dvgw_publications import extract_designation


class ExtractDesignationTestCase(unittest.TestCase):
    def test_code_of_practice(self):
        self.assertEqual(extract_designation("Code of Practice G 100"), "G 100")

    def test_guideline(self):
        self.assertEqual(extract_designation("Guideline GW 302-1"), "GW 302-1")

    def test_audit_basis(self):
        # A third document-type wording found live — the designation
        # extraction must not be hardcoded to just "Code of Practice"/
        # "Guideline".
        self.assertEqual(extract_designation("Audit Basis G 5634"), "G 5634")

    def test_dotted_designation(self):
        self.assertEqual(extract_designation("Project Paper ZP 3100.100"), "ZP 3100.100")

    def test_no_designation_returns_none(self):
        self.assertIsNone(extract_designation("Just a title with no code"))

    def test_blank(self):
        self.assertIsNone(extract_designation(""))
        self.assertIsNone(extract_designation(None))


if __name__ == "__main__":
    unittest.main()
