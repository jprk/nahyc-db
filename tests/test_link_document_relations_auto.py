import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))

from link_document_relations_auto import (
    international_core, jurisdikce_tier, find_localization_pairs,
    digit_core, find_eu_transposition_pairs, is_eu_act_znacka,
    _normalized_digit_pair,
)


def _rec(znacka, nazev_cz="Titul", jurisdikce="", nazev_eu="", odkaz_eu="", **extra):
    r = {"znacka": znacka, "nazev_cz": nazev_cz, "jurisdikce": jurisdikce,
         "nazev_eu": nazev_eu, "odkaz_eu": odkaz_eu}
    r.update(extra)
    return r


class InternationalCoreTestCase(unittest.TestCase):
    def test_strips_national_prefix(self):
        self.assertEqual(international_core("STN ISO 19880-1/ - 2024.05"),
                          international_core("ISO 19880-1"))

    def test_strips_national_prefix_and_en_layer_before_iso(self):
        self.assertEqual(international_core("STN EN ISO 11114-4/ - 2017.10"),
                          international_core("ISO 11114-4"))
        self.assertEqual(international_core("DIN EN ISO 24078"),
                          international_core("EN ISO 24078"))
        self.assertEqual(international_core("DIN EN ISO 24078"),
                          international_core("ISO 24078"))

    def test_bare_en_with_nothing_further_is_not_stripped(self):
        # "EN 1717" is itself the origin (a CEN-native standard) -- must
        # NOT be reduced further just because it starts with "EN ".
        self.assertEqual(international_core("DIN EN 1717"), international_core("EN 1717"))
        self.assertNotEqual(international_core("EN 1717"), "1717")

    def test_unrelated_designations_do_not_collide(self):
        self.assertNotEqual(international_core("STN ISO 11114-1"), international_core("STN ISO 11114-2"))


class JurisdikceTierTestCase(unittest.TestCase):
    def test_known_tiers(self):
        self.assertEqual(jurisdikce_tier("mezinárodní"), "mezinárodní")
        self.assertEqual(jurisdikce_tier("EU"), "EU")
        self.assertEqual(jurisdikce_tier("SK"), "národní")
        self.assertEqual(jurisdikce_tier("DE"), "národní")
        self.assertEqual(jurisdikce_tier("PL"), "národní")  # any future country code

    def test_unknown_is_none_not_guessed(self):
        self.assertIsNone(jurisdikce_tier("neurčeno"))
        self.assertIsNone(jurisdikce_tier(""))
        self.assertIsNone(jurisdikce_tier(None))


class FindLocalizationPairsTestCase(unittest.TestCase):
    def test_national_child_adopts_international_parent(self):
        records = [
            _rec("ISO 11114-4", jurisdikce="mezinárodní"),
            _rec("STN EN ISO 11114-4/ - 2017.10", jurisdikce="SK"),
        ]
        pairs = find_localization_pairs(records)
        self.assertEqual(len(pairs), 1)
        child, parent = pairs[0]
        self.assertEqual(child["znacka"], "STN EN ISO 11114-4/ - 2017.10")
        self.assertEqual(parent["znacka"], "ISO 11114-4")

    def test_multiple_international_editions_each_get_an_edge(self):
        records = [
            _rec("ISO 14687/ - 2019.11", jurisdikce="mezinárodní"),
            _rec("ISO 14687/ - 2025.02", jurisdikce="mezinárodní"),
            _rec("ČSN ISO 14687", jurisdikce="CZ"),
        ]
        pairs = find_localization_pairs(records)
        self.assertEqual(len(pairs), 2)
        self.assertTrue(all(p[0]["znacka"] == "ČSN ISO 14687" for p in pairs))

    def test_two_international_records_alone_do_not_link(self):
        records = [_rec("ISO 1", jurisdikce="mezinárodní"), _rec("EN ISO 1", jurisdikce="EU")]
        self.assertEqual(find_localization_pairs(records), [])

    def test_two_national_records_alone_do_not_link(self):
        records = [_rec("STN ISO 1", jurisdikce="SK"), _rec("DIN ISO 1", jurisdikce="DE")]
        self.assertEqual(find_localization_pairs(records), [])

    def test_unknown_jurisdikce_is_neither_parent_nor_child(self):
        records = [_rec("ISO 1", jurisdikce="neurčeno"), _rec("STN ISO 1", jurisdikce="SK")]
        self.assertEqual(find_localization_pairs(records), [])

    def test_never_links_a_record_to_itself_via_a_shared_znacka(self):
        # doc/PLAN.md §15 follow-up: a record can't ADOPT itself. Real
        # corpus case: a national-jurisdikce record's own znacka was
        # mis-extracted as the SAME designation as a genuinely separate
        # EU-tier record (extract_znacka_from_title() picked up a cited
        # directive's number, not the record's own) -- would otherwise
        # form a same-identifier self-loop that also violates
        # document_relation's unique constraint downstream.
        records = [
            _rec("2010/75/EU", jurisdikce="EU"),
            _rec("2010/75/EU", jurisdikce="SK"),
        ]
        self.assertEqual(find_localization_pairs(records), [])


class DigitCoreTestCase(unittest.TestCase):
    def test_law_style(self):
        self.assertEqual(digit_core("283/2021 Sb."), "283/2021")

    def test_eu_style(self):
        self.assertEqual(digit_core("(EU) 2023/1804"), "2023/1804")

    def test_no_digits_is_none(self):
        self.assertIsNone(digit_core("ČSN ISO 14687"))


class NormalizedDigitPairTestCase(unittest.TestCase):
    def test_plain_pair_returns_both_orderings(self):
        self.assertEqual(_normalized_digit_pair("2023/1804"), {"2023/1804", "1804/2023"})

    def test_two_digit_year_second_position_is_expanded(self):
        # doc/PLAN.md §39: Decision 2119/98/EC, "č. NNNN/YY" style —
        # found live blocking a freshly-imported target from linking.
        got = _normalized_digit_pair("2119/98")
        self.assertIn("1998/2119", got)
        self.assertIn("2119/1998", got)
        self.assertIn("2119/98", got)  # original orderings still offered

    def test_two_digit_year_first_position_is_expanded(self):
        got = _normalized_digit_pair("85/337")
        self.assertIn("1985/337", got)
        self.assertIn("337/1985", got)

    def test_two_already_four_digit_numbers_are_never_expanded(self):
        got = _normalized_digit_pair("2001/2011")
        self.assertEqual(got, {"2001/2011", "2011/2001"})

    def test_non_digit_pair_text_returns_itself_unchanged(self):
        self.assertEqual(_normalized_digit_pair("ISO 14687"), {"ISO 14687"})


class IsEuActZnackaTestCase(unittest.TestCase):
    def test_eu_styled_designations(self):
        self.assertTrue(is_eu_act_znacka("(EU) 2023/1184"))
        self.assertTrue(is_eu_act_znacka("(ES) 2019/942"))
        self.assertTrue(is_eu_act_znacka("2019/692/EU"))

    def test_national_and_standard_designations_are_not_eu_acts(self):
        self.assertFalse(is_eu_act_znacka("458/2000 Sb."))
        self.assertFalse(is_eu_act_znacka("ČSN ISO 14687"))
        self.assertFalse(is_eu_act_znacka(""))
        self.assertFalse(is_eu_act_znacka(None))


class FindEuTranspositionPairsTestCase(unittest.TestCase):
    def test_real_reference_to_an_existing_record_links(self):
        records = [
            _rec("458/2000 Sb.", nazev_eu="Directive (EU) 2019/692 of the European Parliament..."),
            _rec("(EU) 2019/692", nazev_cz="Some EU directive"),
        ]
        pairs, missing = find_eu_transposition_pairs(records)
        self.assertEqual(len(pairs), 1)
        self.assertEqual(missing, [])
        national, eu_act = pairs[0]
        self.assertEqual(national["znacka"], "458/2000 Sb.")
        self.assertEqual(eu_act["znacka"], "(EU) 2019/692")

    def test_self_citation_is_not_a_link(self):
        # An EU-sourced record's own nazev_eu often just restates its own
        # designation -- must not link to itself.
        records = [_rec("(EU) 2023/1184", nazev_eu="Delegované nařízení Komise (EU) 2023/1184...")]
        pairs, missing = find_eu_transposition_pairs(records)
        self.assertEqual(pairs, [])
        self.assertEqual(missing, [])

    def test_missing_target_is_reported_not_dropped(self):
        records = [_rec("201/2012 Sb.", nazev_eu="Commission Implementing Decision (EU) 2013/732/EU...")]
        pairs, missing = find_eu_transposition_pairs(records)
        self.assertEqual(pairs, [])
        self.assertEqual(len(missing), 1)
        self.assertEqual(missing[0][0]["znacka"], "201/2012 Sb.")

    def test_blank_znacka_citer_is_ignored(self):
        # A record with no znacka at all can never resolve to a
        # from_document_id in load_document_relations.py, so it must not
        # produce a pair or a missing-target candidate either.
        records = [
            _rec("", nazev_cz="Vykonávacie rozhodnutie komisie 2022/2427...",
                 nazev_eu="Komise prováděcí rozhodnutí (EU) 2022/2427..."),
        ]
        pairs, missing = find_eu_transposition_pairs(records)
        self.assertEqual(pairs, [])
        self.assertEqual(missing, [])

    def test_no_eu_reference_at_all_is_ignored(self):
        records = [_rec("100/2001 Sb.", nazev_eu="")]
        pairs, missing = find_eu_transposition_pairs(records)
        self.assertEqual(pairs, [])
        self.assertEqual(missing, [])

    def test_eu_act_citing_its_own_parent_directive_is_not_a_link(self):
        # An EU delegated/implementing act citing its own parent directive
        # is a real relationship, but EU-to-EU, not R1.3's national-to-EU
        # transposition shape -- must be excluded even though jurisdikce is
        # empty for both records (as it is for real law records in this
        # corpus), by checking the CITING record's own designation shape.
        records = [
            _rec("(EU) 2023/1184", nazev_eu="Delegované nařízení Komise (EU) 2023/1184, "
                                             "kterým se doplňuje směrnice (EU) 2018/2001..."),
            _rec("(EU) 2018/2001", nazev_cz="Směrnice o podpoře energie z obnovitelných zdrojů"),
        ]
        pairs, missing = find_eu_transposition_pairs(records)
        self.assertEqual(pairs, [])
        self.assertEqual(missing, [])

    def test_national_law_with_empty_jurisdikce_still_links(self):
        # Real corpus shape: Sinay_Zakony/Haltuf_Dokumenty never populate
        # jurisdikce, even for genuine Czech national laws -- must not be
        # excluded just because jurisdikce is empty (see is_eu_act_znacka
        # docstring).
        records = [
            _rec("458/2000 Sb.", jurisdikce="",
                 nazev_eu="Directive (EU) 2019/692 of the European Parliament..."),
            _rec("(EU) 2019/692", jurisdikce="", nazev_cz="Some EU directive"),
        ]
        pairs, missing = find_eu_transposition_pairs(records)
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0][0]["znacka"], "458/2000 Sb.")

    def test_self_citation_first_does_not_hide_a_later_real_reference(self):
        # Real corpus shape: a national law's nazev_eu often cites several
        # EU acts in one string -- checking only the first match would
        # silently hide the genuinely different references that follow.
        # (This scenario is now scoped to a national citer, since a citer
        # whose OWN designation is EU-act-styled is excluded upfront by
        # is_eu_act_znacka() -- see test_eu_act_citing_its_own_parent_directive_is_not_a_link.)
        records = [
            _rec("100/2020 Sb.", nazev_eu="Zákon ... podle nařízení (EU) 2018/1999 a "
                                           "směrnice (EU) 2019/692..."),
            _rec("(EU) 2019/692", nazev_cz="Some EU directive"),
        ]
        pairs, missing = find_eu_transposition_pairs(records)
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0][0]["znacka"], "100/2020 Sb.")
        self.assertEqual(pairs[0][1]["znacka"], "(EU) 2019/692")
        # 2018/1999 is also cited and has no matching record -> reported too.
        self.assertTrue(any(ref == "2018/1999" for _, ref in missing))


if __name__ == "__main__":
    unittest.main()
