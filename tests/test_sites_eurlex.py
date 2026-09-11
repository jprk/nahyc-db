import pathlib
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from sites.eurlex import celex_from_url, extract


def _fake_session(bindings):
    """A requests.Session double whose .get() returns a canned SPARQL
    results.bindings payload — no real network call."""
    session = MagicMock()
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = {"results": {"bindings": bindings}}
    session.get.return_value = response
    return session


def _binding(lang, title):
    return {"lang": {"value": lang}, "title": {"value": title}}


class CelexFromUrlTestCase(unittest.TestCase):
    def test_extracts_celex_from_colon_style_url(self):
        self.assertEqual(
            celex_from_url("https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32014R1300"),
            "32014R1300")

    def test_extracts_celex_from_url_encoded_colon(self):
        self.assertEqual(
            celex_from_url("https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A52020DC0301"),
            "52020DC0301")

    def test_eli_style_url_returns_none(self):
        # Real corpus shape -- deliberately NOT resolved (see module
        # docstring): no verified, non-guessing path from ELI to CELEX.
        self.assertIsNone(celex_from_url("https://eur-lex.europa.eu/eli/dir/2019/692/oj"))

    def test_oj_reference_style_url_returns_none(self):
        self.assertIsNone(celex_from_url("https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=OJ:L_202401788"))

    def test_blank_url_returns_none(self):
        self.assertIsNone(celex_from_url(""))
        self.assertIsNone(celex_from_url(None))


class ExtractTestCase(unittest.TestCase):
    def test_prefers_czech_title_over_english(self):
        session = _fake_session([
            _binding("ENG", "English title"),
            _binding("CES", "Český název"),
        ])
        result = extract("https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32014R0559",
                          session=session)
        self.assertEqual(result, {"title": "Český název", "description": None})

    def test_falls_back_to_english_when_no_czech(self):
        session = _fake_session([_binding("ENG", "English only title")])
        result = extract("https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32014R0559",
                          session=session)
        self.assertEqual(result, {"title": "English only title", "description": None})

    def test_no_celex_in_url_is_none_without_querying(self):
        session = _fake_session([_binding("ENG", "Should never be returned")])
        result = extract("https://eur-lex.europa.eu/eli/dir/2019/692/oj", session=session)
        self.assertIsNone(result)
        session.get.assert_not_called()

    def test_empty_bindings_is_none(self):
        session = _fake_session([])
        result = extract("https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:99999X9999",
                          session=session)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
