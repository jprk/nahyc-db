import pathlib
import sys
import tempfile
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from sites.slovlex import extract, _parse_html

# A trimmed real fixture, matching the structure verified live 2026-09-11
# against https://www.slov-lex.sk/pravne-predpisy/SK/ZZ/2000/124/.
_SAMPLE_HTML = """
<!doctype html><html><head>
<title>124/2000 Z. z. Vyhláška Ministerstva vnútra Slovenskej republiky | Slov-Lex</title>
<script type="application/ld+json">{"@context":"https://schema.org","@type":"Legislation","name":"Vyhláška Ministerstva vnútra Slovenskej republiky, ktorou sa ustanovujú zásady požiarnej bezpečnosti","legislationIdentifier":"124/2000 Z. z.","inLanguage":"sk"}</script>
</head><body><div id="app"></div></body></html>
"""

_NO_JSONLD_HTML = "<html><head><title>96/2004 Z. z. Nejaký zákon | Slov-Lex</title></head><body></body></html>"


class ParseHtmlTestCase(unittest.TestCase):
    def test_extracts_title_from_jsonld_legislation_block(self):
        result = _parse_html(_SAMPLE_HTML)
        self.assertEqual(result["title"],
                          "Vyhláška Ministerstva vnútra Slovenskej republiky, ktorou sa ustanovujú "
                          "zásady požiarnej bezpečnosti")
        self.assertIsNone(result["description"])

    def test_falls_back_to_title_tag_stripping_site_suffix(self):
        result = _parse_html(_NO_JSONLD_HTML)
        self.assertEqual(result["title"], "96/2004 Z. z. Nejaký zákon")

    def test_no_title_at_all_is_none(self):
        self.assertIsNone(_parse_html("<html><head></head><body></body></html>"))

    def test_malformed_jsonld_falls_back_to_title_tag(self):
        html = ('<html><head><title>96/2004 Z. z. X | Slov-Lex</title>'
                '<script type="application/ld+json">{not valid json</script></head></html>')
        result = _parse_html(html)
        self.assertEqual(result["title"], "96/2004 Z. z. X")


class ExtractTestCase(unittest.TestCase):
    def test_parses_a_cached_local_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
            f.write(_SAMPLE_HTML)
            path = f.name
        try:
            result = extract(None, cached_path=path)
            self.assertIn("požiarnej bezpečnosti", result["title"])
        finally:
            pathlib.Path(path).unlink()

    def test_missing_cached_file_falls_back_to_live_fetch(self):
        session = MagicMock()
        response = MagicMock()
        response.raise_for_status = MagicMock()
        response.text = _SAMPLE_HTML
        session.get.return_value = response
        result = extract("https://www.slov-lex.sk/pravne-predpisy/SK/ZZ/2000/124/",
                          cached_path="/nonexistent/path.html", session=session)
        self.assertIn("požiarnej bezpečnosti", result["title"])
        session.get.assert_called_once()
        self.assertTrue(session.get.call_args.kwargs.get("allow_redirects", False))

    def test_no_url_and_no_cached_path_is_none(self):
        self.assertIsNone(extract(None, cached_path=None))


if __name__ == "__main__":
    unittest.main()
