import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))

import screen_esbirka as sb


class BuildQueryTestCase(unittest.TestCase):
    def test_search_query_interpolates_keyword_and_limit(self):
        query = sb.build_search_query("vodí*", limit=50)
        self.assertIn("'vodí*'", query)
        self.assertIn("LIMIT 50", query)

    def test_snippet_query_interpolates_uri(self):
        query = sb.build_snippet_query("https://opendata.eselpoint.gov.cz/esel-esb/x/1")
        self.assertIn("<https://opendata.eselpoint.gov.cz/esel-esb/x/1>", query)


class ExtractKeywordSnippetTestCase(unittest.TestCase):
    def test_prefers_literal_containing_the_stem(self):
        bindings = [
            {"p": {"value": "p1"}, "o": {"type": "uri", "value": "https://example.com/type"}},
            {"p": {"value": "p2"}, "o": {"type": "typed-literal",
                                          "value": "predpis o vodíku a jeho využití"}},
        ]
        self.assertIn("vodíku", sb.extract_keyword_snippet(bindings, "vodí*"))

    def test_falls_back_to_first_literal_if_no_exact_match(self):
        bindings = [{"p": {"value": "p1"}, "o": {"type": "literal", "value": "nesouvisí"}}]
        self.assertEqual(sb.extract_keyword_snippet(bindings, "vodí*"), "nesouvisí")

    def test_empty_bindings_gives_empty_string(self):
        self.assertEqual(sb.extract_keyword_snippet([], "vodí*"), "")

    def test_uri_only_bindings_give_empty_string(self):
        bindings = [{"p": {"value": "p1"}, "o": {"type": "uri", "value": "https://example.com/x"}}]
        self.assertEqual(sb.extract_keyword_snippet(bindings, "vodí*"), "")


class FindNewUrisTestCase(unittest.TestCase):
    def test_filters_out_already_reported(self):
        matched = ["https://x/1", "https://x/2", "https://x/3"]
        already = {"https://x/1", "https://x/3"}
        self.assertEqual(sb.find_new_uris(matched, already), ["https://x/2"])

    def test_no_overlap_returns_all(self):
        matched = ["https://x/1"]
        self.assertEqual(sb.find_new_uris(matched, set()), matched)


if __name__ == "__main__":
    unittest.main()
