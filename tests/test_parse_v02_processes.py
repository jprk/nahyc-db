import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))

from parse_v02_processes import (
    parse_node_heading, looks_like_list_intro_or_wrapup, extract_list_items,
    split_branch_heading, is_krok_heading, is_cross_cutting_heading,
    split_problem_text, parse_subject_cell, parse_bibliography_line,
    extract_citations,
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


if __name__ == "__main__":
    unittest.main()
