import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))

from run_agentic_pipeline import build_discovered_record


class BuildDiscoveredRecordTestCase(unittest.TestCase):
    def test_eurlex_record_shape_matches_existing_discovered_files(self):
        candidate = {"celex": "32014R0559", "matched_keyword": "hydrogen",
                     "title": "Fallback title", "url": "https://eur-lex.europa.eu/x"}
        extracted = {"znacka": "(EU) 2014/559", "nazev": "Council Regulation (EU) No 559/2014",
                     "typ_dokumentu": "Nařízení EU", "gestor": "Evropská komise",
                     "verification_evidence": ["quote"]}
        record = build_discovered_record("EUR-Lex", candidate, extracted)
        self.assertEqual(record["zdroj_dat"], "Agentic_Discovery")
        self.assertEqual(record["znacka"], "(EU) 2014/559")
        self.assertEqual(record["nazev_cz"], "Council Regulation (EU) No 559/2014")
        self.assertEqual(record["nazev_eu"], record["nazev_cz"])
        self.assertEqual(record["odkaz_eu"], candidate["url"])
        self.assertEqual(record["nazev_sk"], "")
        self.assertEqual(record["gestor"], ["Evropská komise"])
        self.assertEqual(record["jurisdikce"], "EU")
        self.assertEqual(record["klicova_slova"], ["hydrogen"])

    def test_falls_back_to_candidate_title_when_extraction_missing_nazev(self):
        candidate = {"title": "Candidate title", "url": "https://example.org/x"}
        record = build_discovered_record("e-Sbirka", candidate, {})
        self.assertEqual(record["nazev_cz"], "Candidate title")
        self.assertEqual(record["jurisdikce"], "CZ")
        self.assertEqual(record["gestor"], [])

    def test_slovlex_jurisdiction_is_sk(self):
        record = build_discovered_record("Slov-Lex", {"title": "t", "url": "u"}, {"nazev": "n"})
        self.assertEqual(record["jurisdikce"], "SK")
        self.assertEqual(record["nazev_sk"], "n")
        self.assertEqual(record["nazev_eu"], "")


if __name__ == "__main__":
    unittest.main()
