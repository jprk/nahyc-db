import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))

from run_agentic_pipeline import build_discovered_record, partition_candidates


class PartitionCandidatesTestCase(unittest.TestCase):
    """The screening file holds three structurally different payloads
    under three keys (doc/AUTOMATION.md odstavec 4.1). These tests pin
    the rule that only declared-processable sources reach the graph —
    before SOURCE_HANDLING existed, e-Sbírka entries were skipped only
    by accident, because they carry `uri` rather than `url`."""

    def test_eurlex_entries_are_processable(self):
        data = {"EUR-Lex": [{"celex": "32014R0559", "url": "https://eur-lex.europa.eu/x",
                              "title": "t"}]}
        processable, skipped, anomalies = partition_candidates(data)
        self.assertEqual(len(processable), 1)
        source, candidate, url = processable[0]
        self.assertEqual(source, "EUR-Lex")
        self.assertEqual(url, "https://eur-lex.europa.eu/x")
        self.assertEqual(skipped, {})
        self.assertEqual(anomalies, [])

    def test_esbirka_fragments_are_skipped_by_declaration_not_by_missing_url(self):
        # The regression this guards: give an e-Sbírka entry a `url` and
        # it must STILL be skipped — the reason it is not a candidate is
        # that it is an unresolved fragment, not that it lacks a field.
        data = {"e-Sbirka": [
            {"uri": "https://opendata.eselpoint.gov.cz/x", "snippet": "…vodík…"},
            {"uri": "https://opendata.eselpoint.gov.cz/y", "url": "https://example.org/y"},
        ]}
        processable, skipped, anomalies = partition_candidates(data)
        self.assertEqual(processable, [])
        self.assertEqual(skipped, {"e-Sbirka": 2})
        self.assertEqual(anomalies, [])

    def test_slovlex_link_rot_entries_are_skipped(self):
        data = {"Slov-Lex": [{"url": "https://slov-lex.sk/broken", "status": 404}]}
        processable, skipped, _ = partition_candidates(data)
        self.assertEqual(processable, [])
        self.assertEqual(skipped, {"Slov-Lex": 1})

    def test_undeclared_source_is_skipped_and_named(self):
        data = {"Some-New-Screener": [{"url": "https://example.org/a"}]}
        processable, skipped, _ = partition_candidates(data)
        self.assertEqual(processable, [])
        self.assertEqual(len(skipped), 1)
        key = next(iter(skipped))
        self.assertIn("Some-New-Screener", key)
        self.assertIn("unknown", key)

    def test_processable_entry_without_its_url_field_is_an_anomaly(self):
        data = {"EUR-Lex": [{"celex": "32014R0559", "title": "no url here"}]}
        processable, skipped, anomalies = partition_candidates(data)
        self.assertEqual(processable, [])
        self.assertEqual(len(anomalies), 1)
        self.assertEqual(anomalies[0]["source"], "EUR-Lex")
        self.assertEqual(anomalies[0]["missing_field"], "url")

    def test_counts_cover_the_whole_file(self):
        data = {
            "EUR-Lex": [{"url": f"https://eur-lex.europa.eu/{i}"} for i in range(3)],
            "e-Sbirka": [{"uri": f"https://opendata.eselpoint.gov.cz/{i}"} for i in range(5)],
            "Slov-Lex": [],
        }
        processable, skipped, _ = partition_candidates(data)
        self.assertEqual(len(processable), 3)
        self.assertEqual(skipped["e-Sbirka"], 5)
        self.assertEqual(skipped["Slov-Lex"], 0)


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
