import pathlib
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from sites.eiga import (build_search_url, extract, fetch_by_designation,
                        normalize_designation, resolve)

# Trimmed real fixtures, matching what eiga.eu's Search & Filter listing
# actually returned 2026-09-17 for `?_sf_s=246` (one clean exact match)
# and `?_sf_s=100` (ten unrelated fuzzy hits — the site's own search
# falls back to full-text matching when the query digits don't identify
# a current document, confirmed live; "100" happens to also BE a real
# code, buried among the noise, which is exactly the case the exact-match
# filter has to get right).
_SINGLE_MATCH_HTML = """
<div class="mc-posts-list publication-list search-filter-list">
  <div class="list-item ct_documents">
    <div class="list-item-wrapper"><div class="list-content-wrapper">
      <span class="tag">Document</span><span class="tag"></span>
      <h4 class="list-title">DOC  246 / 23 - Guideline for Small Scale Hydrogen Production</h4>
      <div class="links">
        <a class="list-download read-more" download="" href="/uploads/documents/DOC246.pdf?v=1"
           rel="noopener noreferrer" target="_blank">Download</a>
        <a onclick="ctcollapse('1')"><b>READ MORE</b></a>
        <div id="content1" style="display:none; ">
          This publication provides safety and operating guidelines to address the hazards
          associated with the operation of small scale hydrogen production plants.
        </div>
      </div>
    </div></div>
  </div>
</div>
"""

_NOISY_MULTI_MATCH_HTML = """
<div class="mc-posts-list publication-list search-filter-list">
  <div class="list-item ct_documents"><div class="list-item-wrapper"><div class="list-content-wrapper">
    <h4 class="list-title">DOC  210 / 23 - Hydrogen Pressure Swing Adsorber Requirements</h4>
    <div class="links">
      <a class="list-download read-more" href="/uploads/documents/DOC210.pdf?v=1">Download</a>
      <div id="content2" style="display:none; ">Requirements for PSA mechanical integrity.</div>
    </div>
  </div></div></div>
  <div class="list-item ct_documents"><div class="list-item-wrapper"><div class="list-content-wrapper">
    <h4 class="list-title">DOC  100 / 20 - Hydrogen Cylinders and Transport Vessels</h4>
    <div class="links">
      <a class="list-download read-more" href="/uploads/documents/DOC100.pdf?v=1">Download</a>
      <div id="content3" style="display:none; ">Recommendations for cylinders and vessels.</div>
    </div>
  </div></div></div>
</div>
"""

_NO_DESCRIPTION_HTML = """
<div class="mc-posts-list publication-list search-filter-list">
  <div class="list-item ct_documents"><div class="list-item-wrapper"><div class="list-content-wrapper">
    <h4 class="list-title">TB  42 / 19 - Some Technical Bulletin</h4>
    <div class="links">
      <a class="list-download read-more" href="/uploads/documents/TB042.pdf?v=1">Download</a>
    </div>
  </div></div></div>
</div>
"""

_NO_RESULTS_HTML = '<div class="mc-posts-list publication-list search-filter-list"></div>'


def _session(payloads):
    """A requests.Session double returning `payloads` in order — each is
    an HTML string. No network."""
    session = MagicMock()
    session.headers = {}
    responses = []
    for payload in payloads:
        response = MagicMock()
        response.raise_for_status = MagicMock()
        response.text = payload
        response.content = payload.encode("utf-8")
        responses.append(response)
    session.get.side_effect = responses
    return session


class NormalizeDesignationTestCase(unittest.TestCase):
    def test_strips_eiga_and_igc_prefixes(self):
        self.assertEqual(normalize_designation("EIGA DOC 246"), "246")
        self.assertEqual(normalize_designation("EIGA IGC Doc 100/20"), "100")

    def test_keeps_the_document_type_word_but_skips_past_it(self):
        # "TB"/"PP"/"DOC" etc. are the document TYPE, not a prefix to
        # strip — the first digit run after them is still found.
        self.assertEqual(normalize_designation("EIGA TB 42"), "42")

    def test_strips_a_trailing_parenthetical_year(self):
        self.assertEqual(normalize_designation("EIGA IGC Doc 121/14 (2014)"), "121")

    def test_no_digits_at_all_returns_none(self):
        self.assertIsNone(normalize_designation("EIGA"))
        self.assertIsNone(normalize_designation(""))
        self.assertIsNone(normalize_designation(None))


class ResolveTestCase(unittest.TestCase):
    """Pure — makes no request; only normalizes and length-gates."""

    def test_builds_the_search_url(self):
        entry = resolve("EIGA DOC 246")
        self.assertEqual(entry, {"code": "246", "url": build_search_url("246")})
        self.assertIn("_sf_s=246", entry["url"])

    def test_short_code_is_rejected_before_any_request(self):
        # The site's own search returns noise, not nothing, below three
        # digits (its own documented minimum) — rejected here rather
        # than relying purely on extract()'s exact-match check.
        self.assertIsNone(resolve("EIGA Doc 12"))

    def test_no_digits_returns_none(self):
        self.assertIsNone(resolve("EIGA"))


class ExtractTestCase(unittest.TestCase):
    def test_single_clean_result_is_trusted(self):
        result = extract(build_search_url("246"), session=_session([_SINGLE_MATCH_HTML]))
        self.assertEqual(result["title"], "DOC 246 / 23 - Guideline for Small Scale Hydrogen Production")
        self.assertIn("small scale hydrogen production", result["description"])

    def test_noisy_multi_result_page_picks_the_exact_code_only(self):
        # Regression guard: "first result" would have returned DOC 210,
        # not the DOC 100 the query digits actually identify.
        result = extract(build_search_url("100"), session=_session([_NOISY_MULTI_MATCH_HTML]))
        self.assertEqual(result["title"], "DOC 100 / 20 - Hydrogen Cylinders and Transport Vessels")
        self.assertIn("cylinders and vessels", result["description"])

    def test_multi_result_page_with_no_exact_code_match_yields_none(self):
        # Neither DOC 210 nor DOC 100 is "999" — must not fall back to
        # either one just because the page returned something.
        result = extract(build_search_url("999"), session=_session([_NOISY_MULTI_MATCH_HTML]))
        self.assertIsNone(result)

    def test_no_results_at_all_yields_none(self):
        result = extract(build_search_url("246"), session=_session([_NO_RESULTS_HTML]))
        self.assertIsNone(result)

    def test_missing_read_more_falls_back_to_pdf_lead(self):
        session = _session([_NO_DESCRIPTION_HTML])
        session.get.side_effect = list(session.get.side_effect) + [MagicMock(
            raise_for_status=MagicMock(), content=b"not a real pdf, extraction will fail")]
        result = extract(build_search_url("42"), session=session)
        self.assertEqual(result["title"], "TB 42 / 19 - Some Technical Bulletin")
        # A malformed PDF is a legitimate "couldn't extract" case, not an error.
        self.assertIsNone(result["description"])


class FetchByDesignationTestCase(unittest.TestCase):
    def test_resolve_then_extract(self):
        result = fetch_by_designation("EIGA DOC 246", session=_session([_SINGLE_MATCH_HTML]))
        self.assertEqual(result["title"], "DOC 246 / 23 - Guideline for Small Scale Hydrogen Production")
        self.assertTrue(result["url"].endswith("_sf_s=246"))

    def test_short_designation_never_reaches_the_network(self):
        session = _session([])
        self.assertIsNone(fetch_by_designation("EIGA Doc 12", session=session))
        self.assertEqual(session.get.call_count, 0)


if __name__ == "__main__":
    unittest.main()
