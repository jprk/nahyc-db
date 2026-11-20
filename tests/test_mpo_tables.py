"""Unit tests of src/tools/mpo_tables.py (no database): reading the rows of the MPO
and CDV tables, the keys of their numbers, matching standards, and the consistency
of the committed files data/20260430_MPO/*.json (every row of both tables has a
status, a row with a reason states it, every planned candidate has its metadata).
The golden test against the database is tests/test_mpo_golden.py."""
import json
import pathlib
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "tools"))
import mpo_tables as mt  # noqa: E402


def row(table, number, **cells):
    return {"id": f"{table}-{number:02d}", "table": table, "row": number, "cislo": cells.get("cislo"),
            "nazev": cells.get("nazev"), "yellow": False, "keys": []}


class KeysTestCase(unittest.TestCase):
    def test_czech_acts_with_and_without_sb(self):
        self.assertEqual(mt.row_keys(row("MPO", 3, cislo="349/2015 Sb.")), ["CZ:349/2015"])
        self.assertEqual(mt.row_keys(row("MPO", 33, cislo="249/2025")), ["CZ:249/2025"])

    def test_eu_acts_with_the_year_first_or_the_number_first(self):
        self.assertEqual(mt.row_keys(row("CDV", 8, cislo="2019/776/EU")), ["EU:2019/776"])
        self.assertEqual(mt.row_keys(row("CDV", 13, cislo="1302/2014/EU")), ["EU:2014/1302"])
        self.assertEqual(mt.row_keys(row("CDV", 19, cislo="79/2009/EU")), ["EU:2009/79"])
        self.assertEqual(mt.row_keys(row("CDV", 31, cislo="DA 2023/1184/EU")), ["EU:2023/1184"])
        self.assertEqual(mt.row_keys(row("CDV", 25, cislo="1999/92/ES (ATEX 137)")), ["EU:1999/92"])

    def test_standards_and_committees(self):
        self.assertEqual(mt.row_keys(row("MPO", 48, cislo="ČSN EN 60079 (řada)")), ["NORM:EN 60079"])
        self.assertEqual(mt.row_keys(row("CDV", 34, cislo=mt.clean("ISO 19880‑3:2018"))), ["NORM:ISO 19880-3"])
        self.assertEqual(mt.row_keys(row("CDV", 35, cislo="ISO/TC 22")), [])
        self.assertEqual(mt.row_keys(row("CDV", 38, cislo="IEC/TC 105")), [])


class MatchingTestCase(unittest.TestCase):
    DOCUMENTS = [
        {"id": 3, "identifier": "ČSN EN ISO 19880-1", "title": "Plynný vodík", "type": "Norma"},
        {"id": 34, "identifier": "ISO 19880-1", "title": "Gaseous hydrogen", "type": "Norma"},
        {"id": 29, "identifier": "ČSN EN IEC 60079-0", "title": "Výbušné atmosféry", "type": "Norma"},
        {"id": 321, "identifier": "STN EN 60079-1/ - 2016.10", "title": "Výbušné atmosféry", "type": "Norma"},
        {"id": 568, "identifier": "ISO 19880-3/ - 2018.06", "title": "Valves", "type": "Norma"},
        {"id": 72, "identifier": "458/2000 Sb.", "title": "Energetický zákon", "type": "Zákon"},
        {"id": 120, "identifier": None, "title": "RID - Přípojek C – Řád", "type": "Nezařazeno"},
    ]

    def setUp(self):
        self.snapshot = mt.Snapshot(self.DOCUMENTS, [{"id": 9, "candidate_key": "CZ:108/2011", "source": "citation",
                                                      "status": "new", "document_id": None}])

    def classify(self, r, decision=None):
        r["keys"] = mt.row_keys(r)
        return mt.classify(r, decision or {}, self.snapshot)

    def test_a_czech_standard_matches_the_czech_adoption_only(self):
        record = self.classify(row("MPO", 47, cislo="ČSN ISO 19880-1"))
        self.assertEqual([d["id"] for d in record["documents"]], [3])
        self.assertEqual(record["status"], "database")

    def test_a_series_matches_its_parts_in_the_same_adoption(self):
        record = self.classify(row("MPO", 48, cislo="ČSN EN 60079 (řada)"))
        self.assertEqual([d["id"] for d in record["documents"]], [29])

    def test_an_international_standard_with_its_edition(self):
        self.assertEqual([d["id"] for d in self.classify(row("CDV", 34, cislo="ISO 19880-3:2018"))["documents"]], [568])

    def test_an_act_in_the_queue_and_a_missing_act(self):
        queued = self.classify(row("MPO", 9, cislo="108/2011 Sb."))
        self.assertEqual((queued["status"], queued["candidates"][0]["existing_id"]), ("queue", 9))
        missing = self.classify(row("MPO", 3, cislo="349/2015 Sb."))
        self.assertEqual((missing["status"], missing["candidates"][0]["existing_id"]), ("queue", None))

    def test_decisions_name_documents_and_reasons(self):
        rid = self.classify(row("CDV", 4), {"title_prefixes": ["RID - Přípojek C"]})
        self.assertEqual([d["id"] for d in rid["documents"]], [120])
        committee = self.classify(row("CDV", 35, cislo="ISO/TC 22"), {"reason": "technická komise"})
        self.assertEqual(committee["status"], "reason")
        self.assertIsNone(self.classify(row("CDV", 36, cislo="ISO/TC 193"))["status"])


class CandidateDetailsTestCase(unittest.TestCase):
    """The details of mpo_decisions.json (`_candidates`) and the plan of the import."""

    def test_the_issuer_of_a_row_can_be_overridden(self):
        r = {**row("MPO", 42, cislo="191/2022 Sb."), "nositel": "MPO", "poznamka": None}
        plain = mt.apply_details({"candidate_key": "CZ:191/2022", "evidence": {}}, r, {})
        self.assertEqual(plain["puvodce"], "Ministerstvo průmyslu a obchodu")
        fixed = mt.apply_details({"candidate_key": "CZ:191/2022", "evidence": {}}, r,
                                 {"puvodce": "Ministerstvo práce a sociálních věcí"})
        self.assertEqual(fixed["puvodce"], "Ministerstvo práce a sociálních věcí")

    def test_an_amendment_carries_the_ids_of_the_amended_documents(self):
        snapshot = mt.Snapshot(MatchingTestCase.DOCUMENTS, [])
        candidate = mt.apply_details({"candidate_key": "CZ:19/2023", "evidence": {}},
                                     {**row("MPO", 2), "nositel": "MPO", "poznamka": None},
                                     {"signal": "amendment", "amends": ["CZ:458/2000", "CZ:406/2000"],
                                      "alias": "LEX OZE I"})
        self.assertEqual((candidate["signal"], candidate["evidence"]["alias"]), ("amendment", "LEX OZE I"))
        self.assertEqual(mt.amends_ids(candidate, snapshot), [72])  # 406/2000 Sb. is not a document

    def test_the_plan_of_the_import(self):
        c = {"candidate_key": "CZ:19/2023"}
        self.assertEqual(mt.planned_outcome(c, None), "inserted")
        self.assertEqual(mt.planned_outcome(c, {"source": "mpo", "status": "new"}), "refreshed")
        self.assertEqual(mt.planned_outcome(c, {"source": "mpo", "status": "deferred"}), "refreshed")
        self.assertEqual(mt.planned_outcome(c, {"source": "citation", "status": "new"}), "evidence")
        for status in ("proposed", "accepted", "rejected"):
            self.assertEqual(mt.planned_outcome(c, {"source": "mpo", "status": status}), "kept")

    def test_the_committed_details(self):
        details = mt.load_candidate_details()
        candidates = {c["candidate_key"]: c for c in mt.load_candidates()}
        self.assertEqual(candidates["CZ:191/2022"]["puvodce"], "Ministerstvo práce a sociálních věcí")
        for key, alias in (("CZ:19/2023", "LEX OZE I"), ("CZ:469/2023", "LEX OZE II"), ("CZ:87/2025", "LEX OZE III")):
            with self.subTest(key=key):
                self.assertEqual(details[key]["alias"], alias)
                self.assertEqual(candidates[key]["evidence"]["alias"], alias)
                self.assertEqual(candidates[key]["signal"], "amendment")
                self.assertTrue({"CZ:458/2000", "CZ:165/2012"} <= set(candidates[key]["evidence"]["amends"]))
        for key in details:
            self.assertIn(key, candidates, "details of a key that is no candidate")

    def test_the_parts_of_the_standard_series_are_valid_czech_adoptions(self):
        parts = [c for c in mt.load_candidates() if any(r["row"] in ("MPO-48", "MPO-49")
                                                        for r in c["evidence"]["mpo_rows"])]
        self.assertEqual(len(parts), 20)
        for c in parts:
            with self.subTest(designation=c["designation"]):
                self.assertTrue(c["designation"].startswith("ČSN EN "))
                # a part issued with a later date of effect is "dosud neúčinný" until then (norm_editions.py)
                expected = "dosud neúčinný" if c["evidence"]["effective_from"] > "2026-11-20" else "platná"
                self.assertEqual(c["validity_status"], expected)
                self.assertNotIn("&", c["title"])


class CommittedFilesTestCase(unittest.TestCase):
    """The committed conversion and coverage agree with each other and with the workbooks."""

    @classmethod
    def setUpClass(cls):
        cls.rows = mt.load_rows()
        cls.coverage = json.loads(mt.COVERAGE_PATH.read_text(encoding="utf-8"))["rows"]
        cls.candidates = {c["candidate_key"]: c for c in mt.load_candidates()}

    def test_both_tables_are_complete(self):
        tables = [r["table"] for r in self.rows]
        self.assertEqual((tables.count("MPO"), tables.count("CDV")), (50, 40))

    def test_the_conversion_matches_the_workbooks(self):
        try:
            import openpyxl  # noqa: F401
        except ImportError:
            self.skipTest("openpyxl not installed")
        fresh = []
        for table, name in mt.WORKBOOKS.items():
            fresh += mt.read_workbook(mt.RAW_DIR / name, table)
        self.assertEqual(fresh, self.rows)

    def test_every_row_has_a_status(self):
        self.assertEqual([c["id"] for c in self.coverage], [r["id"] for r in self.rows])
        for record in self.coverage:
            with self.subTest(row=record["id"]):
                self.assertIn(record["status"], mt.STATUSES)
                if record["status"] == "reason":
                    self.assertTrue(record["reason"])
                if record["status"] == "database":
                    self.assertTrue(record["documents"])

    def test_every_planned_candidate_has_its_metadata(self):
        for record in self.coverage:
            for entry in record["candidates"]:
                if entry["existing_id"] is None:
                    with self.subTest(key=entry["key"]):
                        candidate = self.candidates[entry["key"]]
                        self.assertTrue(candidate["title"] and candidate["url"] and candidate["designation"])
                        self.assertEqual(candidate["source"], mt.SOURCE)
                        self.assertIn(record["id"], [r["row"] for r in candidate["evidence"]["mpo_rows"]])


if __name__ == "__main__":
    unittest.main()
