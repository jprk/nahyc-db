import pathlib
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from sites.normoff import (designation_variants, extract, fetch_by_designation,
                            resolve)

# Trimmed real fixtures, matching what the registry actually returned
# 2026-09-16 for STN EN 17127 (three editions, the 2024 one still in
# force) and for /norma/139845/.
_EXPORT_CSV = (
    '﻿"Katalógové číslo";Označenie;"Názov normy";"Triediaci znak";'
    '"Dátum vydania";"Dátum zrušenia";Jazyk;URL\r\n'
    '138918;"STN EN 17127";"Vonkajšie vodíkové čerpacie stanice";"69 7210";'
    '2024-08-01;;en;https://normy.normoff.gov.sk/norma/138918/\r\n'
    '128280;"STN EN 17127";"Vonkajšie vodíkové čerpacie stanice";"69 7210";'
    '2019-04-01;2021-05-01;en;https://normy.normoff.gov.sk/norma/128280/\r\n'
    '132323;"STN EN 17127";"Vonkajšie vodíkové čerpacie stanice";"69 7210";'
    '2021-05-01;2024-08-01;en;https://normy.normoff.gov.sk/norma/132323/\r\n'
)

# A near miss the registry happily returns for a partial designation —
# must never be accepted as a match.
_EXPORT_CSV_NEAR_MISS = (
    '﻿"Katalógové číslo";Označenie;"Názov normy";"Triediaci znak";'
    '"Dátum vydania";"Dátum zrušenia";Jazyk;URL\r\n'
    '999999;"STN EN 171270";"Úplne iná norma";"69 7210";'
    '2024-08-01;;en;https://normy.normoff.gov.sk/norma/999999/\r\n'
)

_SCOPE_TEXT = (
    "This document defines the minimum requirements to ensure the "
    "interoperability of public hydrogen refuelling points including "
    "refuelling protocols that dispense gaseous hydrogen to road vehicles."
)

_DETAIL_HTML = f"""
<table class="govuk-table"><tbody>
  <tr><td class="govuk-table__cell title">Označenie:</td>
      <td class="govuk-table__cell">STN EN 17127</td></tr>
  <tr><td class="govuk-table__cell title">Slovenský názov:</td>
      <td class="govuk-table__cell">Vonkajšie vodíkové čerpacie stanice</td></tr>
  <tr><td class="govuk-table__cell title">Anglický názov:</td>
      <td class="govuk-table__cell">Outdoor hydrogen refuelling points</td></tr>
  <tr><td class="govuk-table__cell title">Predmet normy:</td>
      <td class="govuk-table__cell">{_SCOPE_TEXT}</td></tr>
</tbody></table>
<a href="#top">Hore</a>
"""

# The registry leaves the scope cell empty for part of its catalogue.
_DETAIL_HTML_NO_SCOPE = """
<table class="govuk-table"><tbody>
  <tr><td class="govuk-table__cell title">Slovenský názov:</td>
      <td class="govuk-table__cell">Navrhovanie a výroba nádrží</td></tr>
  <tr><td class="govuk-table__cell title">Predmet normy:</td>
      <td class="govuk-table__cell">
      </td></tr>
</tbody></table>
<a href="#top">Hore</a>
"""


def _session(payloads):
    """A requests.Session double returning `payloads` in order — each is
    either text (CSV) or HTML. No network."""
    session = MagicMock()
    session.headers = {}
    responses = []
    for payload in payloads:
        response = MagicMock()
        response.raise_for_status = MagicMock()
        response.content = payload.encode("utf-8")
        response.text = payload
        responses.append(response)
    session.get.side_effect = responses
    return session


class DesignationVariantsTestCase(unittest.TestCase):
    def test_literal_spelling_comes_first(self):
        self.assertEqual(designation_variants("STN EN 17127")[0], "STN EN 17127")

    def test_amendment_spacing_is_normalized(self):
        # This corpus writes "STN EN 16898 + A1"; the registry writes it closed up.
        self.assertIn("STN EN 16898+A1", designation_variants("STN EN 16898 + A1"))

    def test_no_base_standard_fallback_for_an_amendment(self):
        # The base standard is a DIFFERENT document — its scope would
        # describe the wrong thing, so it must never be offered.
        variants = designation_variants("STN EN ISO 11114-1/Zmena")
        self.assertEqual(variants, ["STN EN ISO 11114-1/Zmena"])

    def test_blank(self):
        self.assertEqual(designation_variants(""), [])
        self.assertEqual(designation_variants(None), [])


class ResolveTestCase(unittest.TestCase):
    def test_prefers_the_edition_still_in_force(self):
        # 138918 has no withdrawal date; the other two do.
        entry = resolve("STN EN 17127", session=_session([_EXPORT_CSV]))
        self.assertEqual(entry["Katalógové číslo"], "138918")

    def test_falls_back_to_the_newest_withdrawn_edition(self):
        csv_all_withdrawn = _EXPORT_CSV.replace(
            "2024-08-01;;en", "2024-08-01;2025-01-01;en")
        entry = resolve("STN EN 17127", session=_session([csv_all_withdrawn]))
        self.assertEqual(entry["Katalógové číslo"], "138918")  # newest issue date

    def test_near_miss_is_never_accepted(self):
        self.assertIsNone(resolve("STN EN 17127", session=_session([_EXPORT_CSV_NEAR_MISS])))

    def test_no_rows_at_all(self):
        header = _EXPORT_CSV.split("\r\n")[0] + "\r\n"
        self.assertIsNone(resolve("STN EN 17127", session=_session([header])))


class ExtractTestCase(unittest.TestCase):
    def test_reads_the_scope_from_the_labelled_cell(self):
        result = extract("https://normy.normoff.gov.sk/norma/138918/",
                          session=_session([_DETAIL_HTML]))
        self.assertEqual(result["title"], "Vonkajšie vodíkové čerpacie stanice")
        self.assertEqual(result["description"], _SCOPE_TEXT)

    def test_empty_scope_cell_yields_none_not_page_chrome(self):
        # Regression guard: an early version read the next line of
        # flattened text and picked up the page's "Hore" (back-to-top)
        # link for records that have no scope.
        result = extract("https://normy.normoff.gov.sk/norma/102657/",
                          session=_session([_DETAIL_HTML_NO_SCOPE]))
        self.assertIsNotNone(result)
        self.assertIsNone(result["description"])
        self.assertNotIn("Hore", result["title"])

    def test_page_without_a_title_yields_none(self):
        result = extract("https://normy.normoff.gov.sk/norma/1/",
                          session=_session(["<html><body>nic</body></html>"]))
        self.assertIsNone(result)


class FetchByDesignationTestCase(unittest.TestCase):
    def test_resolve_then_extract(self):
        result = fetch_by_designation(
            "STN EN 17127", session=_session([_EXPORT_CSV, _DETAIL_HTML]))
        self.assertEqual(result["catalogue_number"], "138918")
        self.assertEqual(result["description"], _SCOPE_TEXT)
        self.assertFalse(result["withdrawn"])
        self.assertTrue(result["url"].endswith("/norma/138918/"))

    def test_marks_a_withdrawn_edition(self):
        csv_all_withdrawn = _EXPORT_CSV.replace(
            "2024-08-01;;en", "2024-08-01;2025-01-01;en")
        result = fetch_by_designation(
            "STN EN 17127", session=_session([csv_all_withdrawn, _DETAIL_HTML]))
        self.assertTrue(result["withdrawn"])

    def test_unresolved_designation_never_reaches_the_detail_page(self):
        session = _session([_EXPORT_CSV_NEAR_MISS])
        self.assertIsNone(fetch_by_designation("STN EN 17127", session=session))
        self.assertEqual(session.get.call_count, 1)


if __name__ == "__main__":
    unittest.main()
