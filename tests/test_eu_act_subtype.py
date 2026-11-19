"""src/tools/eu_act_subtype.py and backfill_eu_act_subtype.plan()
(doc/MPO_PRIPOMINKY.md, krok 2). Titles are the real ones from the database."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "tools"))

import backfill_eu_act_subtype  # noqa: E402
from eu_act_subtype import DELEGATED, IMPLEMENTING, classify  # noqa: E402

EURLEX = "https://eur-lex.europa.eu/legal-content/CS/TXT/?uri=CELEX:32023R1185"


class ClassifyTestCase(unittest.TestCase):
    def test_eli_decides_first(self):
        self.assertEqual(classify("Cokoli", "https://eur-lex.europa.eu/eli/reg_del/2023/1184/oj", "EU"), DELEGATED)
        self.assertEqual(classify("Cokoli", "https://eur-lex.europa.eu/eli/dec_impl/2013/732/oj", "EU"), IMPLEMENTING)
        self.assertIsNone(classify("Cokoli", "https://eur-lex.europa.eu/eli/reg/2006/865/oj", "EU"))

    def test_czech_titles(self):
        self.assertEqual(classify("Nařízení Komise v\xa0přenesené pravomoci (EU) 2025/656 ze dne 2.\xa0dubna 2025",
                                  EURLEX, "EU"), DELEGATED)
        self.assertEqual(classify("Nařízení Komise v Přenesené Pravomoci (EU) 2019/1745", EURLEX, "EU"), DELEGATED)
        self.assertEqual(classify("Delegované nařízení Komise (EU) 2023/1184 ze dne 10. února 2023", EURLEX, "EU"),
                         DELEGATED)
        self.assertEqual(classify("Prováděcí rozhodnutí Komise (EU) 2025/1486", EURLEX, "EU"), IMPLEMENTING)

    def test_slovak_and_english_titles(self):
        self.assertEqual(classify("Vykonávacie rozhodnutie komisie 2022/2427", None, "EU"), IMPLEMENTING)
        self.assertEqual(classify("(EU) 2018/545 - COMMISSION IMPLEMENTING REGULATION (EU) of 4 April 2018",
                                  EURLEX, "EU"), IMPLEMENTING)
        self.assertEqual(classify("Commission Delegated Regulation (EU) 2023/1185", EURLEX, "EU"), DELEGATED)

    def test_the_act_s_own_designation_wins_over_an_amended_act(self):
        title = ("(EU) 2019/776 - COMMISSION IMPLEMENTING REGULATION of 16 May 2019 amending Commission "
                 "Regulations (EU) No 321/2013 … and Commission Delegated Decision (EU) 2017/1474")
        self.assertEqual(classify(title, EURLEX, "EU"), IMPLEMENTING)

    def test_pre_lisbon_implementing_rules_are_not_an_implementing_act(self):
        title = "Nařízení Komise (ES) č. 865/2006 ze dne 4. května 2006 o prováděcích pravidlech k nařízení Rady"
        self.assertIsNone(classify(title, EURLEX, "EU"))

    def test_only_eu_acts(self):
        title = "Recommendations of HYTEP on the Delegated Act specifying a methodology"
        self.assertIsNone(classify(title, "https://www.hytep.cz/x.pdf", "CZ"))
        self.assertIsNone(classify("Delegované nařízení Komise (EU) 2023/1184", "https://example.org", "CZ"))
        # an EUR-Lex URL is enough when the jurisdiction is missing
        self.assertEqual(classify("Delegované nařízení Komise (EU) 2023/1184", EURLEX, None), DELEGATED)

    def test_ordinary_regulation(self):
        self.assertIsNone(classify("Nařízení Evropského parlamentu a Rady (EU) 2023/1804", EURLEX, "EU"))


class BackfillPlanTestCase(unittest.TestCase):
    def test_only_changes_are_planned(self):
        rows = [
            (1, "(EU) 2023/1184", "Delegované nařízení Komise (EU) 2023/1184", EURLEX, "EU", None),
            (2, "(EU) 2023/1185", "Nařízení Komise v přenesené pravomoci (EU) 2023/1185", EURLEX, "EU", "delegated"),
            (3, "(EU) 2023/1804", "Nařízení Evropského parlamentu a Rady (EU) 2023/1804", EURLEX, "EU", None),
            (4, "(EU) 2023/1804", "Nařízení Evropského parlamentu a Rady (EU) 2023/1804", EURLEX, "EU", "implementing"),
        ]
        self.assertEqual(backfill_eu_act_subtype.plan(rows),
                         [(1, "(EU) 2023/1184", None, "delegated"), (4, "(EU) 2023/1804", "implementing", None)])


if __name__ == "__main__":
    unittest.main()
