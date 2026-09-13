import pathlib
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))

from check_csn_validity import (
    strip_catalog_suffix, split_edition, find_best_match, fetch_detail,
)


class StripCatalogSuffixTestCase(unittest.TestCase):
    def test_strips_trailing_parenthetical_number(self):
        self.assertEqual(strip_catalog_suffix("ČSN EN IEC 62282-2-100 (336000)"), "ČSN EN IEC 62282-2-100")

    def test_no_suffix_is_unchanged(self):
        self.assertEqual(strip_catalog_suffix("ČSN EN 17127"), "ČSN EN 17127")

    def test_blank_is_blank(self):
        self.assertEqual(strip_catalog_suffix(""), "")
        self.assertEqual(strip_catalog_suffix(None), "")


class SplitEditionTestCase(unittest.TestCase):
    def test_uppercase_no_space_form(self):
        self.assertEqual(split_edition("ČSN EN IEC 31010 ED.2"), ("ČSN EN IEC 31010", "2"))

    def test_lowercase_spaced_form(self):
        self.assertEqual(split_edition("ČSN EN IEC 31010 ed. 2"), ("ČSN EN IEC 31010", "2"))

    def test_no_edition_marker(self):
        self.assertEqual(split_edition("ČSN EN IEC 60079-0"), ("ČSN EN IEC 60079-0", None))


class FindBestMatchTestCase(unittest.TestCase):
    """doc/PLAN.md §9 — each case here is a real designation found broken
    against the live agentura-cas.cz search during that pass's research."""

    def test_parenthetical_catalog_suffix_matches_plain_designation(self):
        results = [{"designation": "ČSN EN IEC 62282-2-100", "title": "T", "is_valid": True, "issued": "12.2020"}]
        best = find_best_match(results, "ČSN EN IEC 62282-2-100 (336000)")
        self.assertEqual(best["title"], "T")

    def test_edition_marker_spacing_mismatch_matches(self):
        results = [{"designation": "ČSN EN IEC 31010 ed. 2", "title": "T", "is_valid": True, "issued": "8.2020"}]
        best = find_best_match(results, "ČSN EN IEC 31010 ED.2")
        self.assertEqual(best["title"], "T")

    def test_missing_edition_marker_on_query_side_matches_base(self):
        results = [{"designation": "ČSN EN IEC 60079-0 ed. 5", "title": "T", "is_valid": True, "issued": "12.2018"}]
        best = find_best_match(results, "ČSN EN IEC 60079-0")
        self.assertEqual(best["title"], "T")

    def test_prefers_valid_edition_over_withdrawn(self):
        results = [
            {"designation": "ČSN EN ISO 17268", "title": "Old", "is_valid": False, "issued": "5.2017"},
            {"designation": "ČSN EN ISO 17268", "title": "New", "is_valid": True, "issued": "7.2022"},
        ]
        best = find_best_match(results, "ČSN EN ISO 17268")
        self.assertEqual(best["title"], "New")

    def test_no_valid_edition_prefers_most_recent_real_edition(self):
        # Real case: neither historical edition of ČSN EN ISO 17268 is
        # valid any more (superseded/split into ISO 17268-1) — the most
        # recent REAL edition title wins over the stale, older one.
        results = [
            {"designation": "ČSN EN ISO 17268", "title": "Old (2017)", "is_valid": False, "issued": "5.2017"},
            {"designation": "ČSN EN ISO 17268", "title": "Mid (2020)", "is_valid": False, "issued": "9.2020"},
            {"designation": "ČSN EN ISO 17268", "title": "New (2022)", "is_valid": False, "issued": "7.2022"},
        ]
        best = find_best_match(results, "ČSN EN ISO 17268")
        self.assertEqual(best["title"], "New (2022)")

    def test_amendment_errata_rows_never_picked_as_most_recent(self):
        results = [
            {"designation": "ČSN EN 60079-0", "title": "Real title", "is_valid": False, "issued": "1.2015"},
            {"designation": "ČSN EN 60079-0", "title": "Změna ke stažení: A11", "is_valid": False, "issued": "6.2022"},
        ]
        best = find_best_match(results, "ČSN EN 60079-0")
        self.assertEqual(best["title"], "Real title")

    def test_genuinely_different_designation_is_none(self):
        results = [{"designation": "ČSN EN ISO 14687", "title": "T", "is_valid": True, "issued": "1.2020"}]
        self.assertIsNone(find_best_match(results, "ČSN ISO 19880-1"))

    def test_empty_results_is_none(self):
        self.assertIsNone(find_best_match([], "ČSN EN 17127"))


class FetchDetailTestCase(unittest.TestCase):
    def test_parses_labeled_fields_and_incorporates_table(self):
        html = """
        <html><body>
        <span id="oznaceni">ČSN ISO 19880-1   </span>
        <span id="nazev">Plynný vodík - Čerpací stanice</span>
        <span id="nazeven">Gaseous hydrogen - Fuelling stations</span>
        <table id="GridView2">
          <tr><th>Shoda</th><th>Označení</th><th>Rok vydání</th></tr>
          <tr><td>idt</td><td>ISO 19880-1</td><td>2020</td></tr>
        </table>
        </body></html>
        """
        session = MagicMock()
        resp = MagicMock()
        resp.text = html
        resp.raise_for_status = MagicMock()
        session.get.return_value = resp
        detail = fetch_detail(510864, session)
        self.assertEqual(detail["designation"], "ČSN ISO 19880-1")
        self.assertEqual(detail["title"], "Plynný vodík - Čerpací stanice")
        self.assertEqual(detail["title_en"], "Gaseous hydrogen - Fuelling stations")
        self.assertEqual(detail["incorporates"], [{"designation": "ISO 19880-1", "year": "2020"}])
        self.assertIn("k=510864", detail["url"])

    def test_missing_required_fields_is_none(self):
        session = MagicMock()
        resp = MagicMock()
        resp.text = "<html><body></body></html>"
        resp.raise_for_status = MagicMock()
        session.get.return_value = resp
        self.assertIsNone(fetch_detail(1, session))

    def test_request_exception_is_none(self):
        import requests
        session = MagicMock()
        session.get.side_effect = requests.RequestException("boom")
        self.assertIsNone(fetch_detail(1, session))


if __name__ == "__main__":
    unittest.main()
