import os
import sys
import unittest

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "tools"))

from puvodce import (ABBREVIATION_MAP, EU_ACT_TYPES, gestor_list,
                     is_clean_institution_name, resolve_gestor, resolve_puvodce)

# The AI-enrichment blob shape: a Directorate-General list plus free-text
# commentary crammed into one `gestor` entry, never a real institution.
DG_BLOB = ("Primární DG \nDG ENER (Directorate-General for Energy)\n\n"
           "Další spolupracující DG: \nDG CLIMA (Climate Action)\nDG ENV (Environment)")


class GestorListTestCase(unittest.TestCase):
    def test_list_is_stripped_of_blanks(self):
        self.assertEqual(gestor_list({"gestor": ["  MPO  ", "", "  ", "MŽP"]}),
                         ["MPO", "MŽP"])

    def test_bare_string_is_accepted(self):
        self.assertEqual(gestor_list({"gestor": "MPO"}), ["MPO"])

    def test_missing_field(self):
        self.assertEqual(gestor_list({}), [])


class IsCleanInstitutionNameTestCase(unittest.TestCase):
    def test_a_real_name_is_clean(self):
        self.assertTrue(is_clean_institution_name("Ministerstvo průmyslu a obchodu"))

    def test_multi_line_blob_is_not(self):
        self.assertFalse(is_clean_institution_name(DG_BLOB))

    def test_overlong_value_is_not(self):
        self.assertFalse(is_clean_institution_name("x" * 200))

    def test_blank_is_not(self):
        self.assertFalse(is_clean_institution_name(""))
        self.assertFalse(is_clean_institution_name(None))


class ResolvePuvodceTestCase(unittest.TestCase):
    def test_first_clean_entry_wins(self):
        item = {"gestor": ["Ministerstvo životního prostředí", "Ministerstvo průmyslu a obchodu"]}
        self.assertEqual(resolve_puvodce(item), "Ministerstvo životního prostředí")

    def test_blob_entries_are_skipped_not_returned(self):
        item = {"gestor": [DG_BLOB, "Evropská komise"]}
        self.assertEqual(resolve_puvodce(item), "Evropská komise")

    def test_bare_abbreviation_is_expanded(self):
        # So "MPO" and "Ministerstvo průmyslu a obchodu" don't become two
        # different DocumentSource rows for the same institution.
        self.assertEqual(resolve_puvodce({"gestor": ["MPO"]}),
                         "Ministerstvo průmyslu a obchodu")

    def test_mz_expands_to_health_not_agriculture(self):
        # Verified from the record that uses it ("Zákon o ochraně
        # veřejného zdraví"), not guessed from the abbreviation — the
        # Agriculture ministry is a separate, already-present entry.
        self.assertEqual(ABBREVIATION_MAP["MZ"], "Ministerstvo zdravotnictví")

    def test_no_usable_entry_returns_none(self):
        self.assertIsNone(resolve_puvodce({"gestor": []}))
        self.assertIsNone(resolve_puvodce({"gestor": [DG_BLOB]}))


class ResolveGestorTestCase(unittest.TestCase):
    """doc/PLAN.md §16: one institution, chosen by document kind."""

    CACHE = {"https://eur-lex.europa.eu/eli/reg/2023/2405/oj":
             "Generální ředitelství pro mobilitu a dopravu"}

    def test_national_act_uses_the_primary_ministry(self):
        item = {"gestor": ["Ministerstvo dopravy", "Ministerstvo životního prostředí"]}
        gestor, unresolved = resolve_gestor(item, "Zákon", "http://x", {}, identifier="56/2001 Sb.")
        self.assertEqual(gestor, "Ministerstvo dopravy")
        self.assertFalse(unresolved)

    def test_eu_act_uses_the_cached_eu_body_not_the_ministry(self):
        # The record's own gestor list names Czech ministries; for an EU
        # act those are the wrong kind of institution entirely.
        item = {"gestor": ["Ministerstvo dopravy"]}
        url = "https://eur-lex.europa.eu/eli/reg/2023/2405/oj"
        gestor, unresolved = resolve_gestor(item, "Nařízení EU", url, self.CACHE)
        self.assertEqual(gestor, "Generální ředitelství pro mobilitu a dopravu")
        self.assertFalse(unresolved)

    def test_eu_act_with_no_cache_entry_is_flagged_not_downgraded(self):
        item = {"gestor": ["Ministerstvo dopravy"]}
        gestor, unresolved = resolve_gestor(item, "Směrnice EU", "https://unknown", self.CACHE)
        self.assertIsNone(gestor)
        self.assertTrue(unresolved)

    def test_norma_uses_its_own_designation(self):
        item = {"gestor": ["Ministerstvo průmyslu a obchodu"]}
        gestor, unresolved = resolve_gestor(item, "Norma", None, {}, identifier="ČSN EN 17124")
        self.assertIn("ČAS", gestor)
        self.assertFalse(unresolved)

    def test_norma_with_an_unrecognized_designation_gets_no_gestor(self):
        gestor, unresolved = resolve_gestor({"gestor": []}, "Norma", None, {}, identifier="MB 12")
        self.assertIsNone(gestor)
        self.assertFalse(unresolved)

    def test_every_eu_act_type_takes_the_eu_branch(self):
        for doc_type in EU_ACT_TYPES:
            _, unresolved = resolve_gestor({"gestor": ["MPO"]}, doc_type, "https://unknown", {})
            self.assertTrue(unresolved, doc_type)


if __name__ == "__main__":
    unittest.main()
