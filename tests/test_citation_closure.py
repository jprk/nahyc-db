import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))
import citation_closure as cc


def keys(text):
    return [c.key for c in cc.citations(text)]


class CitationsTestCase(unittest.TestCase):
    def test_czech_and_slovak_acts_and_treaties(self):
        self.assertEqual(keys("podle zákona č. 458/2000 Sb., energetický zákon, a vyhlášky 12/2020 Sb."),
                         ["CZ:458/2000", "CZ:12/2020"])
        self.assertEqual(keys("vyhlášená pod č. 102/2011 Sb. m. s., Řád RID"), ["CZ-MS:102/2011"])
        self.assertEqual(keys("zákon č. 124/2006 Z. z. o bezpečnosti"), ["SK:124/2006"])

    def test_eu_acts_in_every_numbering_style_become_year_and_number(self):
        self.assertEqual(keys("nařízení (EU) 2019/943"), ["EU:2019/943"])
        self.assertEqual(keys("nařízení (ES) č. 1907/2006"), ["EU:2006/1907"])
        self.assertEqual(keys("nariadenie (ES) 1882/2003"), ["EU:2003/1882"])
        self.assertEqual(keys("Regulation (EC) No 715/2009"), ["EU:2009/715"])
        self.assertEqual(keys("směrnice 2012/18/EU a směrnice 98/34/ES"), ["EU:2012/18", "EU:1998/34"])
        self.assertEqual(keys("nařízení (EHS) č. 1408/71"), ["EU:1971/1408"])

    def test_the_kind_of_an_eu_act_is_read_from_the_words_before_it(self):
        found = cc.citations("v souladu se směrnicí Evropského parlamentu a Rady 2003/87/ES a s nařízením (EU) 2018/1999")
        self.assertEqual([(c.key, c.kind) for c in found], [("EU:2003/87", "directive"), ("EU:2018/1999", "regulation")])

    def test_standards_lose_the_national_prefix(self):
        self.assertEqual(keys("ČSN EN ISO 19880-1 a IEC 60079-10-1 a ČSN EN 17124"),
                         ["NORM:EN ISO 19880-1", "NORM:IEC 60079-10-1", "NORM:EN 17124"])


class OwnKeysTestCase(unittest.TestCase):
    def test_identifiers_in_the_database(self):
        self.assertEqual(cc.own_keys("(EU) 2022/869", None), {"EU:2022/869"})
        self.assertEqual(cc.own_keys("2014/68/EU [EN]", None), {"EU:2014/68"})
        self.assertEqual(cc.own_keys("(ES) 1907/2006", None), {"EU:2006/1907"})
        self.assertEqual(cc.own_keys("Nařízení vlády 133/2005", None), {"CZ:133/2005"})
        self.assertEqual(cc.own_keys("ČSN EN 17124", None), {"NORM:EN 17124"})

    def test_without_an_identifier_the_first_citation_of_the_title(self):
        self.assertEqual(cc.own_keys(None, "Směrnice Evropského parlamentu a Rady 2010/75/EU ze dne 24. listopadu 2010, "
                                          "kterou se mění směrnice 96/61/ES"), {"EU:2010/75"})
        self.assertEqual(cc.own_keys(None, "Vodíková strategie"), set())


class ClosureTestCase(unittest.TestCase):
    DOCUMENTS = [(1, "458/2000 Sb.", "Energetický zákon"), (2, "(EU) 2019/943", "Nařízení"),
                 (3, "(EU) 2019/943 [EN]", "Regulation"), (4, None, "Strategie")]

    def test_a_document_and_its_language_variant_are_one_citing_document(self):
        texts = {2: "podle zákona č. 500/2004 Sb., správní řád", 3: "see Act No 500/2004 Sb.",
                 4: "zákon č. 500/2004 Sb. a nařízení (EU) 2019/943"}
        rows = {r["key"]: r for r in cc.closure(self.DOCUMENTS, texts)}
        self.assertEqual(rows["CZ:500/2004"]["cited_by"], 2)
        self.assertEqual(rows["CZ:500/2004"]["citing_ids"], [2, 3, 4])
        self.assertFalse(rows["CZ:500/2004"]["in_database"])
        self.assertTrue(rows["EU:2019/943"]["in_database"])
        self.assertEqual(rows["EU:2019/943"]["database_ids"], [2, 3])

    def test_a_document_citing_itself_does_not_count(self):
        rows = cc.closure(self.DOCUMENTS, {1: "Zákon č. 458/2000 Sb. upravuje"})
        self.assertEqual(rows, [])

    def test_a_list_of_amending_acts_is_marked_as_such(self):
        text = "Zákon č. 458/2000 Sb., ve znění zákona č. 262/2002 Sb., zákona č. 151/2002 Sb., zákona č. 278/2003 Sb.; " \
               "podle zákona č. 500/2004 Sb., správní řád"
        rows = {r["key"]: r for r in cc.closure(self.DOCUMENTS, {4: text})}
        self.assertEqual([rows[k]["amendment_share"] for k in ("CZ:262/2002", "CZ:151/2002", "CZ:278/2003")], [1.0] * 3)
        self.assertEqual(rows["CZ:500/2004"]["amendment_share"], 0.0)
        self.assertEqual(rows["CZ:458/2000"]["amendment_share"], 0.0)

    def test_the_summary_counts_the_share_per_threshold(self):
        rows = [{"family": "CZ", "cited_by": 3, "in_database": True}, {"family": "CZ", "cited_by": 1, "in_database": False},
                {"family": "EU", "cited_by": 2, "in_database": False}]
        result = cc.summary(rows, thresholds=(1, 2))
        self.assertEqual(result["CZ"][1], {"cited": 2, "in_database": 1, "share": 0.5})
        self.assertEqual(result["CZ"][2], {"cited": 1, "in_database": 1, "share": 1.0})
        self.assertEqual(result["all"][2], {"cited": 2, "in_database": 1, "share": 0.5})


class CandidatesTestCase(unittest.TestCase):
    def test_only_missing_documents_cited_often_enough_and_not_as_amendments_go_to_the_sheet(self):
        import csv
        import tempfile
        row = {"family": "CZ", "designation": "500/2004 Sb.", "kind": None, "cited_by": 3, "amendment_share": 0.0,
               "context": "správní řád", "citing_ids": [4, 7], "in_database": False}
        rows = [row, {**row, "designation": "1/2000 Sb.", "cited_by": 1}, {**row, "designation": "2/2000 Sb.", "amendment_share": 0.9},
                {**row, "designation": "3/2000 Sb.", "in_database": True}]
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "c.csv"
            self.assertEqual(cc.write_candidates(rows, path), 1)
            lines = list(csv.reader(path.open(encoding="utf-8")))
        self.assertEqual(lines[1], ["CZ", "500/2004 Sb.", "", "3", "0.0", "správní řád", "4 7", ""])


if __name__ == "__main__":
    unittest.main()
