import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from agentic.verification import normalize_text, verify_evidence


class NormalizeTextTestCase(unittest.TestCase):
    def test_collapses_whitespace(self):
        self.assertEqual(normalize_text("Hello   world\n\nfoo"), "hello world foo")

    def test_lowercases(self):
        self.assertEqual(normalize_text("HYDROGEN"), "hydrogen")

    def test_preserves_punctuation(self):
        self.assertEqual(normalize_text("Nařízení (EU) 2023/1804."), "nařízení (eu) 2023/1804.")


class VerifyEvidenceTestCase(unittest.TestCase):
    def setUp(self):
        self.source = "This Regulation (EU) 2023/1804 establishes hydrogen refuelling infrastructure requirements."

    def test_verbatim_quote_passes(self):
        extracted = {"verification_evidence": ["Regulation (EU) 2023/1804 establishes hydrogen refuelling"]}
        verified, failed = verify_evidence(extracted, self.source)
        self.assertTrue(verified)
        self.assertEqual(failed, [])

    def test_quote_with_wrapped_whitespace_still_passes(self):
        extracted = {"verification_evidence": ["Regulation (EU) 2023/1804\nestablishes   hydrogen refuelling"]}
        verified, failed = verify_evidence(extracted, self.source)
        self.assertTrue(verified)

    def test_fabricated_quote_fails(self):
        extracted = {"verification_evidence": ["this text does not appear anywhere in the source"]}
        verified, failed = verify_evidence(extracted, self.source)
        self.assertFalse(verified)
        self.assertEqual(len(failed), 1)

    def test_missing_evidence_field_fails_closed(self):
        verified, failed = verify_evidence({"znacka": "X"}, self.source)
        self.assertFalse(verified)
        self.assertIn("<missing verification_evidence>", failed)

    def test_empty_evidence_list_fails_closed(self):
        verified, failed = verify_evidence({"verification_evidence": []}, self.source)
        self.assertFalse(verified)

    def test_none_extracted_fails_closed(self):
        verified, failed = verify_evidence(None, self.source)
        self.assertFalse(verified)

    def test_one_bad_quote_among_good_ones_fails(self):
        extracted = {"verification_evidence": [
            "Regulation (EU) 2023/1804 establishes hydrogen refuelling",
            "an invented quote not in the source",
        ]}
        verified, failed = verify_evidence(extracted, self.source)
        self.assertFalse(verified)
        self.assertEqual(failed, ["an invented quote not in the source"])


if __name__ == "__main__":
    unittest.main()
