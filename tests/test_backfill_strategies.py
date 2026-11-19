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


if __name__ == "__main__":
    unittest.main()
