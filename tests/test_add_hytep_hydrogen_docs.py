import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))

from add_hytep_hydrogen_docs import (build_document_record, classify_hytep_document_typ,
                                     classify_jurisdikce, extract_document_links,
                                     is_skipped_duplicate)

_FIXTURE_HTML = """
<div class="sppb-addon-content">
  <a href="https://www.hytep.cz/images/dokumenty-ke-stazeni/Vodikova-strategie-CR-2024.pdf"
     target="_blank" id="btn-x" class="sppb-btn sppb-btn-default">zobrazit [.pdf]</a>
  <a rel="" href="https://www.hytep.cz/images/dokumenty-ke-stazeni/Vodikova-strategie-CR-2024.pdf"
     target="_blank" data-link-type="url"
     data-link-value="https://www.hytep.cz/images/dokumenty-ke-stazeni/Vodikova-strategie-CR-2024.pdf">
     Aktualizace Vodíkové strategie České republiky (2024)</a>
  <a href="https://www.hytep.cz/images/dokumenty-ke-stazeni/Studie-Vyuziti.pdf"
     target="_blank" id="btn-y" class="sppb-btn sppb-btn-default">zobrazit [.pdf]</a>
  <a rel="" href="https://www.hytep.cz/images/dokumenty-ke-stazeni/Studie-Vyuziti.pdf"
     target="_blank" data-link-type="url"
     data-link-value="https://www.hytep.cz/images/dokumenty-ke-stazeni/Studie-Vyuziti.pdf">
     Studie – Využití vodíkového pohonu v dopravě v České republice (2017)</a>
</div>
"""


class ExtractDocumentLinksTestCase(unittest.TestCase):
    def test_extracts_only_the_data_link_type_anchor(self):
        links = extract_document_links(_FIXTURE_HTML, "https://www.hytep.cz/o-vodiku/klicove-dokumenty")
        self.assertEqual(len(links), 2)
        self.assertEqual(links[0]["title"], "Aktualizace Vodíkové strategie České republiky (2024)")
        self.assertTrue(links[0]["url"].endswith("Vodikova-strategie-CR-2024.pdf"))

    def test_generic_button_text_is_never_used_as_title(self):
        links = extract_document_links(_FIXTURE_HTML, "https://x")
        titles = [l["title"] for l in links]
        self.assertNotIn("zobrazit [.pdf]", titles)

    def test_duplicate_urls_are_not_repeated(self):
        html = _FIXTURE_HTML + _FIXTURE_HTML  # same content twice
        links = extract_document_links(html, "https://x")
        self.assertEqual(len(links), 2)

    def test_no_links_on_empty_page(self):
        self.assertEqual(extract_document_links("<html></html>", "https://x"), [])


class IsSkippedDuplicateTestCase(unittest.TestCase):
    def test_2021_strategy_mirror_is_skipped(self):
        self.assertTrue(is_skipped_duplicate(
            "https://www.hytep.cz/images/dokumenty-ke-stazeni/Vodikova-strategie_CZ_G_2021-26-07.pdf"))

    def test_2024_strategy_mirror_is_skipped(self):
        self.assertTrue(is_skipped_duplicate(
            "https://www.hytep.cz/images/dokumenty-ke-stazeni/Vodikova-strategie-CR-2024.pdf"))

    def test_unrelated_document_is_not_skipped(self):
        self.assertFalse(is_skipped_duplicate(
            "https://www.hytep.cz/images/dokumenty-ke-stazeni/Studie-Vyuziti.pdf"))


class ClassifyHytepDocumentTypTestCase(unittest.TestCase):
    def test_strategy_document(self):
        self.assertEqual(classify_hytep_document_typ("Vodíková strategie EU (2020)"), "Strategický dokument")

    def test_action_plan_with_inflected_form(self):
        self.assertEqual(
            classify_hytep_document_typ("Aktualizace Národního akčního plánu čisté mobility (2019)"),
            "Strategický dokument")

    def test_roadmap(self):
        self.assertEqual(
            classify_hytep_document_typ("Cestovní mapa rozvoje vodíkového hospodářství (2023)"),
            "Strategický dokument")

    def test_instruction_is_methodology(self):
        self.assertEqual(
            classify_hytep_document_typ(
                "Instrukce „Výroba vodíku elektrolýzou vody z hlediska živnostenských oprávnění“ (2024)"),
            "Metodika")

    def test_policy_paper_is_methodology(self):
        self.assertEqual(classify_hytep_document_typ("Policy Paper HYTEP: The Cost Challenge"), "Metodika")

    def test_catalogue_is_study(self):
        self.assertEqual(
            classify_hytep_document_typ("Katalog vodíkového výzkumu v ČR (EN, 2025)"), "Studie")

    def test_case_study_is_study(self):
        self.assertEqual(
            classify_hytep_document_typ("Případová studie výstavby elektrolyzéru v České republice (2023)"),
            "Studie")

    def test_strategy_wins_over_study_for_research_agenda(self):
        # "Strategická výzkumná agenda" matches both patterns — strategy
        # is checked first since it's the title's own primary descriptor.
        self.assertEqual(
            classify_hytep_document_typ("Strategická výzkumná agenda pro rozvoj vodíkového hospodářství (2023)"),
            "Strategický dokument")

    def test_genuinely_unclear_title_returns_empty_string(self):
        self.assertEqual(classify_hytep_document_typ("Dovoz obnovitelného vodíku do ČR (2024)"), "")


class ClassifyJurisdikceTestCase(unittest.TestCase):
    def test_eu_labelled_title_is_eu(self):
        self.assertEqual(classify_jurisdikce("Vodíková strategie EU (2020)"), "EU")

    def test_czech_title_is_cz(self):
        self.assertEqual(classify_jurisdikce("Cestovní mapa rozvoje vodíkového hospodářství (2023)"), "CZ")


class BuildDocumentRecordTestCase(unittest.TestCase):
    def test_full_record_shape(self):
        record = build_document_record(
            "Studie – Využití vodíkového pohonu v dopravě v České republice (2017)",
            "https://www.hytep.cz/images/dokumenty-ke-stazeni/Studie-Vyuziti.pdf")
        self.assertEqual(record["znacka"], "")
        self.assertEqual(record["typ_dokumentu"], "Studie")
        self.assertEqual(record["odkaz_hlavni"],
                         "https://www.hytep.cz/images/dokumenty-ke-stazeni/Studie-Vyuziti.pdf")
        self.assertEqual(record["jurisdikce"], "CZ")
        self.assertEqual(record["gestor"], [])
        self.assertEqual(record["jazyk"], "")
        self.assertIn("HYTEP", record["anotace_poznamka"])


if __name__ == "__main__":
    unittest.main()
