import pathlib
import sys
import tempfile
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from sites.zakonyprolidi import extract, _parse_html

# A trimmed real fixture, matching the structure verified live 2026-09-11
# against https://www.zakonyprolidi.cz/cs/2006-183.
_SAMPLE_HTML = """
<!DOCTYPE html>
<html><head><title>
183/2006 Sb. Stavební zákon (starý)
</title>
<meta property="og:title" content="183/2006 Sb. Stavební zákon (starý)" />
<meta property="og:description" content="Zákon č. 183/2006 Sb. - Zákon o územním plánování a stavebním řádu (stavební zákon) - zrušeno k 01.01.2024(283/2021 Sb.)" />
<meta name="description" content="Zákon č. 183/2006 Sb. - Zákon o územním plánování a stavebním řádu (stavební zákon) - zrušeno k 01.01.2024(283/2021 Sb.)" />
</head><body></body></html>
"""

_NO_META_HTML = "<html><head><title>Jen titulek | Zákony pro lidi</title></head><body></body></html>"


class ParseHtmlTestCase(unittest.TestCase):
    def test_extracts_og_title_and_description(self):
        result = _parse_html(_SAMPLE_HTML)
        self.assertEqual(result["title"], "183/2006 Sb. Stavební zákon (starý)")
        self.assertIn("zrušeno k 01.01.2024", result["description"])

    def test_falls_back_to_title_tag_when_no_og_title(self):
        result = _parse_html(_NO_META_HTML)
        self.assertEqual(result["title"], "Jen titulek | Zákony pro lidi")
        self.assertIsNone(result["description"])

    def test_no_title_at_all_is_none(self):
        self.assertIsNone(_parse_html("<html><head></head><body></body></html>"))


class ExtractTestCase(unittest.TestCase):
    def test_parses_a_cached_local_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
            f.write(_SAMPLE_HTML)
            path = f.name
        try:
            result = extract(None, cached_path=path)
            self.assertEqual(result["title"], "183/2006 Sb. Stavební zákon (starý)")
        finally:
            pathlib.Path(path).unlink()

    def test_missing_cached_file_falls_back_to_live_fetch(self):
        session = MagicMock()
        response = MagicMock()
        response.raise_for_status = MagicMock()
        response.text = _SAMPLE_HTML
        session.get.return_value = response
        result = extract("https://www.zakonyprolidi.cz/cs/2006-183",
                          cached_path="/nonexistent/path.html", session=session)
        self.assertEqual(result["title"], "183/2006 Sb. Stavební zákon (starý)")
        session.get.assert_called_once()

    def test_no_url_and_no_cached_path_is_none(self):
        self.assertIsNone(extract(None, cached_path=None))


if __name__ == "__main__":
    unittest.main()
