import pathlib
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from agentic.parser import extract_text_from_html_bytes, parse_source


class ExtractTextFromHtmlBytesTestCase(unittest.TestCase):
    def test_strips_tags(self):
        html = b"<html><body><h1>Title</h1><p>Some hydrogen text.</p></body></html>"
        text = extract_text_from_html_bytes(html)
        self.assertIn("Title", text)
        self.assertIn("Some hydrogen text.", text)
        self.assertNotIn("<p>", text)


class ParseSourceTestCase(unittest.TestCase):
    def test_uses_local_manifest_copy_when_available(self):
        with patch("agentic.parser._load_manifest") as mock_manifest, \
             patch("agentic.parser._local_path_for_url") as mock_local_path:
            mock_manifest.return_value = {}
            fake_path = MagicMock()
            fake_path.read_bytes.return_value = b"<html><body>Local hydrogen text</body></html>"
            fake_path.suffix = ".html"
            mock_local_path.return_value = fake_path
            text, error = parse_source("https://example.org/act")
        self.assertIsNone(error)
        self.assertIn("Local hydrogen text", text)

    def test_fetch_failure_returns_error_not_exception(self):
        import requests

        with patch("agentic.parser._load_manifest", return_value={}), \
             patch("agentic.parser._local_path_for_url", return_value=None):
            session = MagicMock()
            session.get.side_effect = requests.RequestException("boom")
            text, error = parse_source("https://example.org/act", session=session)
        self.assertIsNone(text)
        self.assertIn("fetch failed", error)

    def test_empty_parsed_text_is_an_error(self):
        with patch("agentic.parser._load_manifest", return_value={}), \
             patch("agentic.parser._local_path_for_url") as mock_local_path:
            fake_path = MagicMock()
            fake_path.read_bytes.return_value = b"<html><body>   </body></html>"
            fake_path.suffix = ".html"
            mock_local_path.return_value = fake_path
            text, error = parse_source("https://example.org/act")
        self.assertIsNone(text)
        self.assertEqual(error, "parsed empty text")


if __name__ == "__main__":
    unittest.main()
