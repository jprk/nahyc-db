import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))

from link_document_versions import (
    version_group_key, amendment_level, version_sort_key,
    _has_en_iec_renumbering, build_version_groups,
    merge_version_group, link_document_versions,
)


def _rec(znacka, nazev_cz="Titul", jurisdikce="SK", platnost="", klicova_slova=None,
         zdroj_dat="Sinay_Normy", **extra):
    r = {"znacka": znacka, "nazev_cz": nazev_cz, "jurisdikce": jurisdikce,
         "platnost": platnost, "klicova_slova": klicova_slova or [], "zdroj_dat": zdroj_dat}
    r.update(extra)
    return r


class VersionGroupKeyTestCase(unittest.TestCase):
    def test_plain_suffix_marker_before_slash(self):
        self.assertEqual(
            version_group_key("STN EN 13445-2+A1/ - 2024.02"),
            version_group_key("STN EN 13445-2/ – 2021.08"))

    def test_marker_embedded_before_the_slash_still_groups(self):
        # "/A1" sits BEFORE the "/" that would otherwise start the date
        # suffix -- real corpus shape, must still resolve to the same key.
        self.assertEqual(
            version_group_key("STN EN 13322-2/A1 – 2003.12"),
            version_group_key("STN EN 13322-2/ - 2003.12"))

    def test_ac_corrigendum_marker_still_groups(self):
        self.assertEqual(
            version_group_key("STN EN 14638-3/AC – 2010.12"),
            version_group_key("STN EN 14638-3/ - 2010.12"))

    def test_marker_between_two_slashes_still_groups(self):
        self.assertEqual(
            version_group_key("STN EN 60079-5/A1/ - 2025.03"),
            version_group_key("STN EN 60079-5/ – 2015.09"))

    def test_unrelated_designations_do_not_collide(self):
        self.assertNotEqual(version_group_key("STN EN 1106+A1/ - 2024.06"),
                             version_group_key("STN EN 12583+A1/ - 2025.02"))

    def test_en_iec_renumbering_not_folded_by_default(self):
        # Without the flag, "EN 60079-11" and "EN IEC 60079-11" are
        # different cores -- the fold is opt-in.
        self.assertNotEqual(version_group_key("STN EN 60079-11/ - 2012.11"),
                             version_group_key("STN EN IEC 60079-11/ - 2025.03"))

    def test_en_iec_renumbering_folded_when_requested(self):
        self.assertEqual(
            version_group_key("STN EN 60079-11/ - 2012.11", fold_en_iec_renumbering=True),
            version_group_key("STN EN IEC 60079-11/ - 2025.03", fold_en_iec_renumbering=True))

    def test_en_iec_fold_does_not_collide_different_part_numbers(self):
        self.assertNotEqual(
            version_group_key("STN EN 60079-11/ - 2012.11", fold_en_iec_renumbering=True),
            version_group_key("STN EN IEC 60079-17/ - 2024.04", fold_en_iec_renumbering=True))


class AmendmentLevelTestCase(unittest.TestCase):
    def test_unmarked_base_is_zero(self):
        self.assertEqual(amendment_level("STN EN 13445-2/ – 2021.08"), 0)

    def test_numbered_amendment(self):
        self.assertEqual(amendment_level("STN EN 13445-2+A1/ - 2024.02"), 1)
        self.assertEqual(amendment_level("STN EN 1-1+A2"), 2)

    def test_corrigendum_with_no_number_is_one(self):
        self.assertEqual(amendment_level("STN EN 14638-3/AC – 2010.12"), 1)


class HasEnIecRenumberingTestCase(unittest.TestCase):
    def test_detects_en_iec(self):
        self.assertTrue(_has_en_iec_renumbering("STN EN IEC 60079-11/ - 2025.03"))

    def test_plain_en_is_false(self):
        self.assertFalse(_has_en_iec_renumbering("STN EN 60079-11/ - 2012.11"))


class VersionSortKeyTestCase(unittest.TestCase):
    def test_en_iec_renumbered_sorts_after_plain_en(self):
        self.assertLess(version_sort_key("STN EN 60079-11/ - 2012.11"),
                         version_sort_key("STN EN IEC 60079-11/ - 2025.03"))

    def test_amendment_still_outranks_en_iec_renumbering(self):
        # An amendment marker is a stronger "later" signal than the bare
        # EN-IEC renumbering flag (unlikely combination, but the ordering
        # must still be well-defined).
        self.assertLess(version_sort_key("STN EN IEC 60079-11/ - 2025.03"),
                         version_sort_key("STN EN IEC 60079-11+A1/ - 2026.01"))


class BuildVersionGroupsTestCase(unittest.TestCase):
    def test_finds_a_base_and_amendment_pair(self):
        records = [
            _rec("STN EN 13445-2/ – 2021.08"),
            _rec("STN EN 13445-2+A1/ - 2024.02"),
            _rec("STN EN 9999", jurisdikce="DE"),  # unrelated, must not be swept in
        ]
        groups = build_version_groups(records)
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]), 2)

    def test_conflicting_jurisdikce_never_groups(self):
        records = [
            _rec("STN EN 1+A1", jurisdikce="SK"),
            _rec("STN EN 1", jurisdikce="DE"),
        ]
        self.assertEqual(build_version_groups(records), [])

    def test_same_core_but_no_amendment_marker_anywhere_is_not_a_group(self):
        # Same designation-core coincidence with NO amendment marker on
        # either side is not this script's job (would be a plain
        # duplicate, deduplicate_db.py's job, not a version pair).
        records = [_rec("STN EN 1"), _rec("STN EN 1")]
        self.assertEqual(build_version_groups(records), [])

    def test_records_without_znacka_are_ignored(self):
        records = [_rec(""), _rec("STN EN 1+A1"), _rec("STN EN 1")]
        groups = build_version_groups(records)
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]), 2)

    def test_finds_a_real_en_iec_renumbering_pair(self):
        # Step 1 follow-up #18: STN EN 60079-11 (2012) -> STN EN IEC
        # 60079-11 (2025), no amendment marker at all -- must still group,
        # on the strength of the genuine EN/EN-IEC split.
        records = [
            _rec("STN EN 60079-11/ - 2012.11"),
            _rec("STN EN IEC 60079-11/ - 2025.03"),
            _rec("STN EN 9999", jurisdikce="DE"),
        ]
        groups = build_version_groups(records)
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]), 2)

    def test_two_en_iec_records_alone_are_not_grouped(self):
        # Both members already renumbered ("EN IEC ...") -- no EN/EN-IEC
        # split and no amendment marker, so no structural evidence this
        # is a real version pair (would just be a plain duplicate,
        # deduplicate_db.py's job).
        records = [_rec("STN EN IEC 1"), _rec("STN EN IEC 1")]
        self.assertEqual(build_version_groups(records), [])


class MergeVersionGroupTestCase(unittest.TestCase):
    def test_current_version_fields_win_and_versions_list_is_ordered(self):
        base = _rec("STN EN 13445-2/ – 2021.08", nazev_cz="Nevyhrievané tlakové nádoby",
                     platnost="Veröffentlicht-Publikovaný / 2021-08", klicova_slova=["A"])
        amendment = _rec("STN EN 13445-2+A1/ - 2024.02", nazev_cz="Nevyhrievané tlakové nádoby",
                          platnost="od 02/2024", klicova_slova=["B"])
        merged = merge_version_group([amendment, base])  # order-independent input
        self.assertEqual(merged["znacka"], "STN EN 13445-2+A1/ - 2024.02")
        self.assertEqual(merged["klicova_slova"], ["A", "B"])
        versions = merged["versions"]
        self.assertEqual(len(versions), 2)
        self.assertEqual(versions[0]["znacka"], "STN EN 13445-2/ – 2021.08")
        self.assertFalse(versions[0]["is_current"])
        self.assertEqual(versions[1]["znacka"], "STN EN 13445-2+A1/ - 2024.02")
        self.assertTrue(versions[1]["is_current"])

    def test_sources_are_combined(self):
        base = _rec("STN EN 1/ - 2021.08", zdroj_dat="Sinay_Normy")
        amendment = _rec("STN EN 1+A1/ - 2024.02", zdroj_dat="Prokop_Normy")
        merged = merge_version_group([base, amendment])
        self.assertEqual(merged["zdroj_dat"], "Prokop_Normy, Sinay_Normy")

    def test_en_iec_renumbered_edition_wins_as_current(self):
        base = _rec("STN EN 60079-11/ - 2012.11", nazev_cz="Výbušné atmosféry")
        renumbered = _rec("STN EN IEC 60079-11/ - 2025.03", nazev_cz="Výbušné atmosféry")
        merged = merge_version_group([base, renumbered])
        self.assertEqual(merged["znacka"], "STN EN IEC 60079-11/ - 2025.03")
        versions = merged["versions"]
        self.assertEqual(versions[0]["znacka"], "STN EN 60079-11/ - 2012.11")
        self.assertFalse(versions[0]["is_current"])
        self.assertTrue(versions[1]["is_current"])


class LinkDocumentVersionsTestCase(unittest.TestCase):
    def test_untouched_records_pass_through(self):
        untouched = _rec("STN EN 9999", jurisdikce="DE")
        result = link_document_versions([untouched])
        self.assertEqual(result, [untouched])

    def test_end_to_end_reduces_a_pair_to_one_record(self):
        records = [
            _rec("STN EN 1/ - 2021.08"),
            _rec("STN EN 1+A1/ - 2024.02"),
            _rec("STN EN 9999", jurisdikce="DE"),
        ]
        result = link_document_versions(records)
        self.assertEqual(len(result), 2)
        versioned = [r for r in result if "versions" in r]
        self.assertEqual(len(versioned), 1)
        self.assertEqual(len(versioned[0]["versions"]), 2)


if __name__ == "__main__":
    unittest.main()
