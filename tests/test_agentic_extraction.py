import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from agentic.extraction import extract_with_retry_feedback


class ExtractWithRetryFeedbackTestCase(unittest.TestCase):
    def test_no_failed_quotes_calls_extractor_with_plain_text(self):
        calls = []

        def fake_extractor(text):
            calls.append(text)
            return {"znacka": "X", "verification_evidence": []}

        extract_with_retry_feedback("source text", None, llm_extractor=fake_extractor)
        self.assertEqual(calls, ["source text"])

    def test_failed_quotes_are_appended_to_feedback(self):
        calls = []

        def fake_extractor(text):
            calls.append(text)
            return {"znacka": "X", "verification_evidence": []}

        extract_with_retry_feedback("source text", ["a bad quote"], llm_extractor=fake_extractor)
        self.assertEqual(len(calls), 1)
        self.assertIn("source text", calls[0])
        self.assertIn("a bad quote", calls[0])

    def test_returns_none_when_extractor_returns_none(self):
        result = extract_with_retry_feedback("source text", None, llm_extractor=lambda text: None)
        self.assertIsNone(result)

    def test_client_unconfigured_returns_none_not_a_guess(self):
        # Mirrors add_eurlex_hydrogen_acts.py's own convention: a caller
        # of extract_with_llm() directly (client is None) must get None,
        # never a fabricated/default record.
        import agentic.extraction as extraction_module
        original_client = extraction_module.client
        extraction_module.client = None
        try:
            self.assertIsNone(extraction_module.extract_with_llm("some text"))
        finally:
            extraction_module.client = original_client


if __name__ == "__main__":
    unittest.main()
