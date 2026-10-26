import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))
import language_variants as lv


def row(jazyk, znacka="2014/68/EU", zdroj="Haltuf_Dokumenty", **extra):
    base = {"zdroj_dat": zdroj, "znacka": znacka, "jazyk": jazyk, "nazev_cz": f"title {jazyk}",
            "odkaz_hlavni": f"https://x/{jazyk}", "odkaz_eu": f"https://x/{jazyk}", "gestor": [jazyk],
            "anotace_poznamka": f"note {jazyk}"}
    base.update(extra)
    return base


class VariantPairsTestCase(unittest.TestCase):
    def test_a_designation_with_both_languages_is_a_pair_and_the_first_row_of_each_wins(self):
        raw = [row("CZ"), row("EN"), row("CZ", nazev_cz="later"), row("EN", nazev_cz="later")]
        pairs = lv.variant_pairs(raw)
        self.assertEqual(list(pairs), [("Haltuf_Dokumenty", "2014/68/EU")])
        self.assertEqual(pairs[("Haltuf_Dokumenty", "2014/68/EU")]["CS"]["nazev_cz"], "title CZ")
        self.assertEqual(pairs[("Haltuf_Dokumenty", "2014/68/EU")]["EN"]["nazev_cz"], "title EN")

    def test_the_language_of_the_eurlex_address_beats_a_wrong_jazyk_column(self):
        czech = row("angličtina", odkaz_hlavni="https://eur-lex.europa.eu/legal-content/CS/TXT/PDF/?uri=CELEX:1")
        english = row("angličtina", odkaz_hlavni="https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:1")
        pairs = lv.variant_pairs([czech, english])
        self.assertEqual(list(pairs), [("Haltuf_Dokumenty", "2014/68/EU")])
        czech_variant, english_variant = lv.split_record(row("angličtina"), pairs)
        self.assertEqual((czech_variant["jazyk"], english_variant["jazyk"]), ("CZ", "EN"))

    def test_one_language_only_or_another_source_is_not_a_pair(self):
        self.assertEqual(lv.variant_pairs([row("CZ"), row("CZ")]), {})
        self.assertEqual(lv.variant_pairs([row("CZ"), row("EN", zdroj="Sinay_Zakony")]), {})
        self.assertEqual(lv.variant_pairs([row("CZ", znacka=""), row("EN", znacka="")]), {})

    def test_the_english_row_of_a_pair_is_filed_under_the_suffixed_designation(self):
        raw = [row("CZ"), row("EN"), row("EN", znacka="other")]
        pairs = lv.variant_pairs(raw)
        self.assertEqual([lv.variant_designation(r, pairs) for r in raw], ["2014/68/EU", "2014/68/EU [EN]", "other"])


class SplitRecordTestCase(unittest.TestCase):
    def setUp(self):
        self.pairs = lv.variant_pairs([row("CZ"), row("EN")])
        self.merged = row("EN", zdroj="Sinay_Zakony, Haltuf_Dokumenty", platnost="1.1.2020", nazev_eu="eu title",
                          nazev_autoritativni="Czech authoritative", popis_autoritativni="Czech description",
                          zdroj_autoritativni_url="https://x/auth")

    def test_the_czech_variant_keeps_the_designation_and_every_source(self):
        czech, english = lv.split_record(self.merged, self.pairs)
        self.assertEqual((czech["znacka"], czech["zdroj_dat"]), ("2014/68/EU", "Sinay_Zakony, Haltuf_Dokumenty"))
        self.assertEqual((czech["nazev_cz"], czech["odkaz_hlavni"], czech["jazyk"]), ("title CZ", "https://x/CZ", "CZ"))
        self.assertEqual(czech["nazev_autoritativni"], "Czech authoritative")

    def test_the_english_variant_has_the_suffix_its_own_row_and_no_czech_overlay(self):
        _, english = lv.split_record(self.merged, self.pairs)
        self.assertEqual((english["znacka"], english["zdroj_dat"]), ("2014/68/EU [EN]", "Haltuf_Dokumenty"))
        self.assertEqual((english["nazev_cz"], english["odkaz_hlavni"], english["jazyk"]), ("title EN", "https://x/EN", "EN"))
        for field in lv.CZECH_ONLY_FIELDS:
            self.assertNotIn(field, english)
        self.assertEqual(english["nazev_eu"], "")
        self.assertEqual(english["platnost"], "1.1.2020")  # shared metadata stays

    def test_a_record_outside_the_pairs_is_not_split(self):
        self.assertIsNone(lv.split_record(row("EN", znacka="other"), self.pairs))

    def test_the_input_record_is_not_changed(self):
        before = dict(self.merged)
        lv.split_record(self.merged, self.pairs)
        self.assertEqual(self.merged, before)


class ExpandTestCase(unittest.TestCase):
    def setUp(self):
        self.pairs = lv.variant_pairs([row("CZ"), row("EN")])
        self.corpus = [row("EN", znacka="first"), row("EN"), row("CZ", znacka="last")]

    def test_the_pair_is_replaced_by_its_two_variants_in_place(self):
        expanded = lv.expand_variants(self.corpus, self.pairs)
        self.assertEqual([r["znacka"] for r in expanded], ["first", "2014/68/EU", "2014/68/EU [EN]", "last"])

    def test_expanding_twice_changes_nothing(self):
        once = lv.expand_variants(self.corpus, self.pairs)
        self.assertEqual(lv.expand_variants(once, self.pairs), once)

    def test_the_relations_link_the_english_variant_to_the_czech_original(self):
        relations = lv.translation_relations(lv.expand_variants(self.corpus, self.pairs))
        self.assertEqual([(r["from_identifier"], r["to_identifier"], r["relation_type"]) for r in relations],
                         [("2014/68/EU [EN]", "2014/68/EU", "TRANSLATION_OF")])

    def test_no_relation_without_the_original(self):
        self.assertEqual(lv.translation_relations([row("EN", znacka="x [EN]")]), [])

class GestorCacheTestCase(unittest.TestCase):
    def test_the_english_address_gets_the_gestor_of_the_czech_original(self):
        pairs = lv.variant_pairs([row("CZ"), row("EN")])
        records = lv.expand_variants([row("EN")], pairs)
        cache = {"https://x/CZ": "DG GROW"}
        self.assertEqual(lv.gestor_cache_additions(records, cache), {"https://x/EN": "DG GROW"})

    def test_the_czech_address_gets_the_gestor_of_the_english_one_too(self):
        pairs = lv.variant_pairs([row("CZ"), row("EN")])
        records = lv.expand_variants([row("EN")], pairs)
        self.assertEqual(lv.gestor_cache_additions(records, {"https://x/EN": "DG GROW"}), {"https://x/CZ": "DG GROW"})

    def test_nothing_is_added_when_present_or_unknown(self):
        pairs = lv.variant_pairs([row("CZ"), row("EN")])
        records = lv.expand_variants([row("EN")], pairs)
        self.assertEqual(lv.gestor_cache_additions(records, {"https://x/CZ": "a", "https://x/EN": "b"}), {})
        self.assertEqual(lv.gestor_cache_additions(records, {}), {})


if __name__ == "__main__":
    unittest.main()
