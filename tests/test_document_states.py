import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))
import backfill_document_states as bf
import document_states as ds

CACHE = {"CZ:183/2006": {"status": "zrušený", "source": "e-sbirka", "repealed_by": ["CZ:283/2021"], "repealed_on": "2024-01-01"},
         "CZ:283/2021": {"status": "účinný", "repealed_by": []},
         "EU:2009/73": {"status": "zrušený", "source": "cellar", "end": "2024-08-03", "repealed_by": ["EU:2024/1788"]},
         "EU:2024/1788": {"status": "účinný", "repealed_by": []},
         "CZ:1/2027": {"status": "dosud neúčinný", "repealed_by": []},
         "EU:2012/630": {"status": "zrušený", "source": "cellar", "repealed_by": []}}


class StateTestCase(unittest.TestCase):
    def test_the_validity_check_gives_repealed_and_promulgated(self):
        self.assertEqual(ds.state_of("183/2006 Sb.", "Stavební zákon", CACHE), "repealed")
        self.assertEqual(ds.state_of("1/2027 Sb.", "Zákon", CACHE), "promulgated")
        self.assertIsNone(ds.state_of("283/2021 Sb.", "Stavební zákon", CACHE))
        self.assertIsNone(ds.state_of(None, "Vodíková strategie", CACHE))

    def test_a_draft_stays_a_draft_and_the_rest_follows_the_check(self):
        self.assertEqual(ds.current_state("draft", "183/2006 Sb.", "", CACHE), "draft")
        self.assertEqual(ds.current_state("active", "183/2006 Sb.", "", CACHE), "repealed")
        self.assertEqual(ds.current_state("active", "283/2021 Sb.", "", CACHE), "active")

    def test_every_state_has_a_czech_label(self):
        self.assertEqual(set(ds.LABELS), set(ds.STATES))


class RepealRelationsTestCase(unittest.TestCase):
    DOCUMENTS = [("183/2006 Sb.", "Stavební zákon"), ("283/2021 Sb.", "Stavební zákon"),
                 ("2009/73/ES", "Směrnice"), ("(EU) 2024/1788", "Směrnice"), ("(EU) 2024/1788 [EN]", "Directive"),
                 ("(EU) 2012/630", "Nařízení"), (None, "Strategie")]

    def test_the_repealing_act_repeals_the_document_once_not_per_language_variant(self):
        relations = ds.repeal_relations(self.DOCUMENTS, CACHE)
        self.assertEqual([(r["from_identifier"], r["to_identifier"], r["relation_type"]) for r in relations],
                         [("(EU) 2024/1788", "2009/73/ES", "REPEALS"), ("283/2021 Sb.", "183/2006 Sb.", "REPEALS")])
        self.assertIn("2024-01-01", relations[1]["note"])

    def test_no_relation_without_the_successor_in_the_database(self):
        self.assertEqual(ds.repeal_relations([("183/2006 Sb.", "Stavební zákon"), ("(EU) 2012/630", "")], CACHE), [])


class PlanStatesTestCase(unittest.TestCase):
    def test_only_changes_are_planned_and_a_document_no_longer_repealed_goes_back_to_active(self):
        rows = [(1, "183/2006 Sb.", "", 11, "active"), (2, "283/2021 Sb.", "", 12, "active"),
                (3, "283/2021 Sb.", "", 13, "repealed"), (4, "183/2006 Sb.", "", 14, "draft"),
                (5, "183/2006 Sb.", "", 15, "superseded")]
        self.assertEqual(bf.plan_states(rows, CACHE), [(11, 1, "183/2006 Sb.", "active", "repealed"),
                                                       (13, 3, "283/2021 Sb.", "repealed", "active")])


class EnsureStatesTestCase(unittest.TestCase):
    def test_the_enum_gets_the_new_states(self):
        class Cursor:
            def __init__(self):
                self.sql = []

            def execute(self, sql, params=None):
                self.sql.append(" ".join(sql.split()))

            def fetchone(self):
                return ("enum('active','superseded','draft')",)
        cursor = Cursor()
        self.assertTrue(bf.ensure_states(cursor))
        self.assertIn("ENUM('active','superseded','draft','promulgated','repealed')", cursor.sql[-1])


if __name__ == "__main__":
    unittest.main()
