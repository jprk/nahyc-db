import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))
import backfill_strategies as bs


class FakeCursor:
    """Answers SELECTs from `answers` in order; records every statement."""

    def __init__(self, answers):
        self.answers, self.executed = list(answers), []

    def execute(self, sql, params=None):
        self.executed.append((" ".join(sql.split()), params))
        return 2

    def fetchall(self):
        return self.answers.pop(0)


class RenameTypeTestCase(unittest.TestCase):
    def test_the_type_is_renamed_and_candidates_follow(self):
        cursor = FakeCursor([[("Strategický dokument", 9)]])
        self.assertIn("'Strategie'", bs.rename_type(cursor))
        sql = [s for s, _ in cursor.executed]
        self.assertIn("UPDATE DocumentType SET name = %s WHERE id = %s", sql)
        self.assertIn("UPDATE DocumentCandidate SET document_type = %s WHERE document_type = %s", sql)
        self.assertFalse([s for s in sql if s.startswith("DELETE")])

    def test_a_duplicate_new_type_is_merged_into_the_renamed_one(self):
        cursor = FakeCursor([[("Strategický dokument", 9), ("Strategie", 14)]])
        bs.rename_type(cursor)
        self.assertIn(("UPDATE Document SET type_id = %s WHERE type_id = %s", (9, 14)), cursor.executed)
        self.assertIn(("DELETE FROM DocumentType WHERE id = %s", (14,)), cursor.executed)

    def test_nothing_to_do_once_renamed(self):
        cursor = FakeCursor([[("Strategie", 9)]])
        self.assertIsNone(bs.rename_type(cursor))
        self.assertEqual(len(cursor.executed), 1)


class SelectionTestCase(unittest.TestCase):
    def test_the_new_records_are_the_strategies_and_the_eiga_publication(self):
        records = [{"zdroj_dat": "Strategy_Research", "znacka": ""}, {"zdroj_dat": "Sinay_Normy", "znacka": "EIGA IGC Doc 100/20"},
                   {"zdroj_dat": "HYTEP", "znacka": ""}]
        self.assertEqual(bs.new_records(records), records[:2])

    def test_a_record_without_designation_is_named_by_its_address(self):
        from fulltext_keys import url_designation
        self.assertEqual(bs.record_name({"znacka": "COM(2022) 230"}), "COM(2022) 230")
        self.assertEqual(bs.record_name({"znacka": "", "odkaz_hlavni": "https://x/a.pdf"}), url_designation("https://x/a.pdf"))

    def test_the_relations_of_this_step(self):
        relations = bs.wanted_relations([])
        self.assertTrue(relations)
        for relation in relations:
            slovak = relation["from_identifier"].endswith(" [SK]") and relation["relation_type"] == "TRANSLATION_OF"
            superseded = relation["to_identifier"] in bs.RELATION_NAMES and relation["relation_type"] == "REPEALS"
            self.assertTrue(slovak or superseded, relation)


class DraftStrategiesTestCase(unittest.TestCase):
    """doc/MPO_PRIPOMINKY.md, odstavec 5: the unapproved updates of two strategies are
    prepared documents joined to the strategy each is to replace."""

    def setUp(self):
        self.records = [r for r in bs.load(bs.REPO_ROOT / "data" / "strategy_documents.json")
                        if r.get("stav_dokumentu") == "draft"]

    def test_the_two_updates_are_drafts(self):
        titles = sorted(r["nazev_cz"] for r in self.records)
        self.assertEqual(len(titles), 2)
        self.assertTrue(titles[0].startswith("Aktualizace Státní energetické koncepce"))
        self.assertTrue(titles[1].startswith("Politika ochrany klimatu v České republice – aktualizace"))
        self.assertEqual(sorted(r["gestor"][0] for r in self.records),
                         ["Ministerstvo průmyslu a obchodu", "Ministerstvo životního prostředí"])

    def test_each_update_replaces_a_strategy_of_the_step(self):
        names = [bs.record_name(r) for r in self.records]
        relations = [r for r in bs.wanted_relations(names) if r["from_identifier"] in names]
        self.assertEqual(len(relations), 2)
        strategies = {bs.record_name(r) for r in bs.load(bs.REPO_ROOT / "data" / "strategy_documents.json")
                      if not r.get("stav_dokumentu")}
        for relation in relations:
            self.assertEqual(relation["relation_type"], "REPEALS")
            self.assertIn(relation["to_identifier"], strategies)

    def test_a_present_document_gets_its_state(self):
        record = self.records[0]
        name = bs.record_name(record)
        cursor = FakeCursor([[(71, "active")]])
        self.assertEqual(bs.record_states(cursor, [record], {name: 5}), [(name, 5, "active", "draft")])
        self.assertIn(("UPDATE DocumentVersion SET lifecycle_state = %s WHERE id = %s", ("draft", 71)), cursor.executed)
        cursor = FakeCursor([[(71, "draft")]])
        self.assertEqual(bs.record_states(cursor, [record], {name: 5}), [])

    def test_priority_c_strategies_are_documents(self):
        designations = {r["znacka"] for r in bs.load(bs.REPO_ROOT / "data" / "strategy_documents.json")}
        for designation in ("COM(2023) 634", "COM(2024) 63", "COM(2025) 79", "COM(2025) 95", "COM(2025) 1005"):
            self.assertIn(designation, designations)


if __name__ == "__main__":
    unittest.main()
