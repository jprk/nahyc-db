import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))

from parse_v02_processes import (
    parse_node_heading, looks_like_list_intro_or_wrapup, extract_list_items,
    split_branch_heading, is_krok_heading, is_cross_cutting_heading,
    split_problem_text, parse_subject_cell, parse_bibliography_line,
    extract_citations, extract_bracket_refs, parse_edge_target,
    map_installation_type,
)


class ParseNodeHeadingTestCase(unittest.TestCase):
    def test_matches_real_heading(self):
        self.assertEqual(parse_node_heading("Uzel U1 — Územní kompatibilita záměru"), "U1")
        self.assertEqual(parse_node_heading("Uzel U7 — Certifikace produktu"), "U7")

    def test_non_node_heading_returns_none(self):
        self.assertIsNone(parse_node_heading("Vazba na databázi předpisů a procesů (V01)"))


class ListIntroWrapupTestCase(unittest.TestCase):
    def test_colon_ending_is_intro(self):
        self.assertTrue(looks_like_list_intro_or_wrapup("Základní vstupy zahrnují:"))

    def test_normal_sentence_is_not(self):
        self.assertFalse(looks_like_list_intro_or_wrapup(
            "záměr investora s identifikací lokality,"))


class ExtractListItemsTestCase(unittest.TestCase):
    def test_prefers_list_paragraph_style_when_present(self):
        paras = [
            ("Normal", "Základní vstupy zahrnují:"),
            ("List Paragraph", "první vstup,"),
            ("List Paragraph", "druhý vstup."),
            ("Normal", "Poznámka na závěr, není položka seznamu."),
        ]
        self.assertEqual(extract_list_items(paras), ["první vstup,", "druhý vstup."])

    def test_falls_back_to_normal_minus_colon_intro(self):
        # U4-U7's actual style: no List Paragraph at all, just plain
        # 'Normal' paragraphs after a colon-terminated intro sentence.
        paras = [
            ("Normal", "Základní vstupy zahrnují:"),
            ("Normal", "rozhodnutí o obchodním modelu,"),
            ("Normal", "technické parametry instalace,"),
        ]
        self.assertEqual(extract_list_items(paras),
                          ["rozhodnutí o obchodním modelu,", "technické parametry instalace,"])

    def test_empty_section_gives_empty_list(self):
        self.assertEqual(extract_list_items([]), [])


class SplitBranchHeadingTestCase(unittest.TestCase):
    def test_lettered_branch_with_prefix_word(self):
        self.assertEqual(split_branch_heading("Větev A — Vlastní spotřeba"),
                          ("A", "Vlastní spotřeba"))

    def test_bare_letter_from_table_cell(self):
        self.assertEqual(split_branch_heading("A — Bez posouzení"),
                          ("A", "Bez posouzení"))

    def test_cross_cutting_heading(self):
        self.assertEqual(split_branch_heading("Průřezově — ATEX klasifikace"),
                          ("Průřezově", "ATEX klasifikace"))

    def test_no_dash_falls_back_to_whole_text(self):
        self.assertEqual(split_branch_heading("Bez oddělovače"),
                          ("Bez oddělovače", "Bez oddělovače"))

    def test_hyphen_variant_also_matches(self):
        self.assertEqual(split_branch_heading("B - Požární ochrana"),
                          ("B", "Požární ochrana"))


class KrokAndCrossCuttingDetectionTestCase(unittest.TestCase):
    def test_krok_heading(self):
        self.assertTrue(is_krok_heading("Krok 2 — Větvení procesu"))
        self.assertFalse(is_krok_heading("Větev A — Vlastní spotřeba"))

    def test_cross_cutting_heading_detection(self):
        self.assertTrue(is_cross_cutting_heading("Průřezově — ATEX klasifikace"))
        self.assertFalse(is_cross_cutting_heading("Větev A — Vlastní spotřeba"))


class SplitProblemTextTestCase(unittest.TestCase):
    def test_splits_title_from_elaboration(self):
        title, full = split_problem_text(
            "Nejednoznačná funkční klasifikace — vodíkové instalace nejsou...")
        self.assertEqual(title, "Nejednoznačná funkční klasifikace")
        self.assertTrue(full.startswith("Nejednoznačná"))

    def test_no_dash_gives_none_title(self):
        title, full = split_problem_text("Prostý text bez pomlčky.")
        self.assertIsNone(title)
        self.assertEqual(full, "Prostý text bez pomlčky.")


class ParseSubjectCellTestCase(unittest.TestCase):
    def test_extracts_abbreviation_in_parens(self):
        name, abbr = parse_subject_cell("HZS (Hasičský záchranný sbor)")
        self.assertEqual(abbr, "HZS")
        self.assertEqual(name, "HZS (Hasičský záchranný sbor)")

    def test_no_abbreviation(self):
        name, abbr = parse_subject_cell("Investor")
        self.assertEqual(name, "Investor")
        self.assertIsNone(abbr)


class ParseBibliographyLineTestCase(unittest.TestCase):
    def test_real_entry(self):
        ref_id, text = parse_bibliography_line(
            "[24] Zákon č. 283/2021 Sb., o územním plánování a stavebním řádu.")
        self.assertEqual(ref_id, 24)
        self.assertTrue(text.startswith("Zákon č."))

    def test_category_header_line_returns_none(self):
        self.assertIsNone(parse_bibliography_line("České zákony"))


class ExtractCitationsTestCase(unittest.TestCase):
    def test_czech_law_citation(self):
        self.assertIn("283/2021", extract_citations(
            "stavební právo (zákon č. 283/2021 Sb., o územním plánování a stavebním řádu)"))

    def test_government_decree_citation(self):
        self.assertIn("192/2022", extract_citations(
            "nařízení vlády č. 192/2022 Sb., o vyhrazených tlakových zařízeních"))

    def test_eu_regulation_bracketed(self):
        self.assertIn("2023/1804", extract_citations(
            "nařízení Evropského parlamentu a Rady (EU) 2023/1804 ze dne..."))

    def test_eu_regulation_unbracketed(self):
        self.assertIn("1907/2006", extract_citations(
            "nařízení EU č. 1907/2006 (REACH) a č. 1272/2008 (CLP)"))

    def test_no_citation_gives_empty_list(self):
        self.assertEqual(extract_citations("Obyčejná věta bez odkazu na předpis."), [])

    def test_second_act_in_coordinated_eu_phrase(self):
        # doc/PLAN.md Step 1 (2026-09-17): U4 cites "nařízení EU
        # č. 1907/2006 (REACH) a č. 1272/2008 (CLP)" — the second act has
        # no "EU"/"ES" prefix of its own, only the trailing "(CLP)".
        found = extract_citations("nařízení EU č. 1907/2006 (REACH) a č. 1272/2008 (CLP)")
        self.assertIn("1907/2006", found)
        self.assertIn("1272/2008", found)

    def test_bare_en_standard_citation(self):
        found = extract_citations("EN 17124:2022 — jakost vodíku jako paliva")
        self.assertIn("EN 17124", found)

    def test_bare_en_pattern_does_not_swallow_csn_prefix(self):
        # "ČSN EN 1514-1" must still be captured whole by the ČSN
        # pattern, and must NOT also yield a spurious bare "EN 1514".
        found = extract_citations("viz ČSN EN 1514-1, technické provedení přírub")
        self.assertIn("ČSN EN 1514-1", found)
        self.assertNotIn("EN 1514", found)

    def test_bare_en_pattern_does_not_swallow_stn_prefix(self):
        found = extract_citations("viz STN EN 17124, špecifikácia výrobku")
        self.assertNotIn("EN 17124", found)


class ExtractBracketRefsTestCase(unittest.TestCase):
    def test_finds_every_ref_in_prose(self):
        text = ("Klíčovým podkladem jsou instrukce HYTEP [6], aktualizace oprávnění [7] "
                 "a případová studie [8].")
        self.assertEqual(extract_bracket_refs(text), [6, 7, 8])

    def test_no_refs_gives_empty_list(self):
        self.assertEqual(extract_bracket_refs("Žádný odkaz na literaturu zde není."), [])


class ParseEdgeTargetTestCase(unittest.TestCase):
    def test_extracts_node_code_from_arrow_cell(self):
        self.assertEqual(parse_edge_target("→ U2 (Environmentální režim)"), "U2")

    def test_no_node_code_returns_none(self):
        self.assertIsNone(parse_edge_target("Vazba"))


class MapInstallationTypeTestCase(unittest.TestCase):
    def test_electrolysis(self):
        self.assertEqual(map_installation_type("Elektrolýza"), "ELEKTROLYZA")

    def test_storage_and_transport(self):
        self.assertEqual(map_installation_type("Skladování a přeprava"), "SKLADOVANI")

    def test_refuelling_station(self):
        self.assertEqual(map_installation_type("VČS (čerpací stanice)"), "VCS")

    def test_vehicles(self):
        self.assertEqual(map_installation_type("Vodíková vozidla"), "VOZIDLA")

    def test_unknown_text_returns_none(self):
        self.assertIsNone(map_installation_type("Něco úplně jiného"))


if __name__ == "__main__":
    unittest.main()
