import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))

from add_missing_iso_parents import (build_document_record, find_matching_iso_result,
                                     find_missing_international_cores, iso_search_target)


class IsoSearchTargetTestCase(unittest.TestCase):
    def test_bare_iso(self):
        self.assertEqual(iso_search_target("iso 17268"), ("ISO", "17268"))

    def test_multi_part_number(self):
        self.assertEqual(iso_search_target("iso 15156-1"), ("ISO", "15156-1"))

    def test_iso_iec_joint_standard(self):
        self.assertEqual(iso_search_target("iso/iec 80079-20-1"), ("ISO/IEC", "80079-20-1"))

    def test_iso_ts_with_provisional_marker(self):
        self.assertEqual(iso_search_target("p iso/ts 19870"), ("ISO/TS", "19870"))

    def test_amendment_marker_does_not_parse(self):
        # doc/PLAN.md §37: an amendment/corrigendum suffix breaks the
        # expected shape on purpose -- these are markers of an existing
        # base standard, not a missing one, and must never be treated as
        # a new searchable target.
        self.assertIsNone(iso_search_target("iso 11114-1/a1"))
        self.assertIsNone(iso_search_target("iso 11114-1/zmena"))

    def test_non_iso_core_does_not_parse(self):
        self.assertIsNone(iso_search_target("csa/ansi hgv 2"))
        self.assertIsNone(iso_search_target(""))


class FindMatchingIsoResultTestCase(unittest.TestCase):
    def test_exact_match(self):
        results = [("https://www.iso.org/standard/68442.html", "ISO 17268:2020")]
        self.assertEqual(find_matching_iso_result(results, "ISO", "17268"),
                         ("https://www.iso.org/standard/68442.html", "ISO 17268:2020"))

    def test_prefers_highest_year_among_multiple_editions(self):
        results = [
            ("https://x/old.html", "ISO 31000:2009"),
            ("https://x/new.html", "ISO 31000:2018"),
        ]
        self.assertEqual(find_matching_iso_result(results, "ISO", "31000"),
                         ("https://x/new.html", "ISO 31000:2018"))

    def test_rejects_a_different_part(self):
        # doc/PLAN.md §37: target is bare "17268", not "17268-1"/"17268-2".
        results = [("https://x/1.html", "ISO 17268-1:2025"),
                   ("https://x/2.html", "ISO/DIS 17268-2")]
        self.assertIsNone(find_matching_iso_result(results, "ISO", "17268"))

    def test_rejects_a_draft(self):
        results = [("https://x/dis.html", "ISO/DIS 15156-1")]
        self.assertIsNone(find_matching_iso_result(results, "ISO", "15156-1"))

    def test_rejects_a_corrigendum(self):
        results = [("https://x/cor.html", "ISO/IEC 80079-20-1:2017/Cor 1:2018")]
        self.assertIsNone(find_matching_iso_result(results, "ISO/IEC", "80079-20-1"))

    def test_no_results_gives_none(self):
        self.assertIsNone(find_matching_iso_result([], "ISO", "17268"))

    def test_unrelated_number_never_matches(self):
        results = [("https://x/1.html", "ISO/IEC 27554:2024")]
        self.assertIsNone(find_matching_iso_result(results, "ISO", "31000"))


class BuildDocumentRecordTestCase(unittest.TestCase):
    def test_full_record_shape(self):
        record = build_document_record("ISO", "17268", "ISO 17268:2020 Gaseous hydrogen — Test",
                                       "https://www.iso.org/standard/68442.html")
        self.assertEqual(record["znacka"], "ISO 17268")
        self.assertEqual(record["typ_dokumentu"], "Norma")
        self.assertEqual(record["nazev_cz"], "ISO 17268:2020 Gaseous hydrogen — Test")
        self.assertEqual(record["odkaz_hlavni"], "https://www.iso.org/standard/68442.html")
        self.assertEqual(record["jurisdikce"], "mezinárodní")
        self.assertEqual(record["gestor"], [])
        self.assertEqual(record["jazyk"], "")

    def test_iso_iec_prefix_preserved_in_znacka(self):
        record = build_document_record("ISO/IEC", "80079-20-1", "title", "https://x")
        self.assertEqual(record["znacka"], "ISO/IEC 80079-20-1")


class FindMissingInternationalCoresTestCase(unittest.TestCase):
    def _record(self, znacka, jurisdikce, typ_dokumentu="Norma"):
        return {"znacka": znacka, "jurisdikce": jurisdikce, "typ_dokumentu": typ_dokumentu,
               "nazev_cz": znacka}

    def test_national_only_group_is_missing(self):
        records = [self._record("ČSN EN ISO 17268", "CZ"),
                   self._record("STN EN ISO 17268/ - 2020.08", "SK")]
        missing = find_missing_international_cores(records)
        self.assertIn("iso 17268", missing)

    def test_group_with_international_parent_is_not_missing(self):
        records = [self._record("ČSN EN ISO 19880-1", "CZ"),
                   self._record("ISO 19880-1", "mezinárodní")]
        missing = find_missing_international_cores(records)
        self.assertNotIn("iso 19880-1", missing)

    def test_non_norma_records_are_ignored(self):
        records = [self._record("ISO 17268", "CZ", typ_dokumentu="Zákon")]
        missing = find_missing_international_cores(records)
        self.assertEqual(missing, {})

    def test_amendment_marker_group_is_still_reported_as_missing_but_unparseable_downstream(self):
        # find_missing_international_cores() itself doesn't know about
        # amendment markers -- that filtering happens in
        # iso_search_target() downstream. Just confirm this doesn't crash
        # and produces the (later-rejected) core.
        records = [self._record("STN EN ISO 11114-1/Zmena", "SK")]
        missing = find_missing_international_cores(records)
        self.assertIn("iso 11114-1/zmena", missing)


if __name__ == "__main__":
    unittest.main()
