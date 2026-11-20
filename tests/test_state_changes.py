"""The parts of src/tools/state_changes.py that need no database: reading the
editor's form, the fields that really change, the key in
data/manual_corrections.json, merging corrections and the relation file."""
import json
import pathlib
import sys
import tempfile
import unittest

from werkzeug.datastructures import MultiDict

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))
import state_changes as sc  # noqa: E402


class ReadProposalTestCase(unittest.TestCase):
    def test_self_keeps_only_filled_fields(self):
        proposal, errors = sc.read_proposal(MultiDict({"mode": "self", "to_state": "promulgated",
                                                       "znacka": " 123/2027 Sb. ", "nazev_cz": "", "target": "x"}))
        self.assertEqual(errors, [])
        self.assertEqual(proposal["changes"], {"znacka": "123/2027 Sb."})
        self.assertEqual(proposal["target"], "")

    def test_act_needs_a_target_and_the_choices_are_checked(self):
        _proposal, errors = sc.read_proposal(MultiDict({"mode": "act", "to_state": "active"}))
        self.assertEqual(len(errors), 1)
        _proposal, errors = sc.read_proposal(MultiDict({"mode": "other", "to_state": "repealed"}))
        self.assertEqual(len(errors), 2)


class FieldsAndKeysTestCase(unittest.TestCase):
    def test_unchanged_fields_are_dropped(self):
        document = {"identifier": "prEN 17124", "title": "Vodík", "url": None, "effective_date": ""}
        self.assertEqual(sc.changed_fields(document, {"znacka": "EN 17124", "nazev_cz": "Vodík", "platnost": "2027"}),
                         {"znacka": "EN 17124", "platnost": "2027"})

    def test_correction_key(self):
        corrections = {"XY 1": {"changes": {"znacka": "XY 1:2020"}}}
        self.assertEqual(sc.correction_key("XY 1:2020", None, corrections), "XY 1")
        self.assertEqual(sc.correction_key("ZZ 2", None, corrections), "ZZ 2")
        self.assertTrue(sc.correction_key(None, "https://example.test/a extra", {}).startswith("url-"))
        self.assertEqual(sc.correction_key(None, "https://example.test/a extra", {}),
                         sc.correction_key(None, "https://example.test/a", {}))
        self.assertIsNone(sc.correction_key(None, None, {}))

    def test_merge_keeps_earlier_changes(self):
        corrections = {"A": {"changes": {"nazev_cz": "Opravený název"}, "confirmed_by": "x"}}
        sc.merge_correction(corrections, "A", {"stav_dokumentu": "active"}, "bob", "2026-11-19")
        self.assertEqual(corrections["A"]["changes"], {"nazev_cz": "Opravený název", "stav_dokumentu": "active"})
        self.assertEqual(corrections["A"]["confirmed_by"], "bob")


class FilesTestCase(unittest.TestCase):
    def test_corrections_and_relation_are_written_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            corrections = pathlib.Path(tmp) / "corrections.json"
            relations = pathlib.Path(tmp) / "relations.json"
            sc.save_corrections([("A", {"stav_dokumentu": "superseded"}), (None, {"x": 1})], "bob", "2026-11-19",
                                corrections)
            self.assertEqual(list(json.loads(corrections.read_text(encoding="utf-8"))), ["A"])
            for _ in range(2):
                sc.save_relation("ISO/AWI 1", "ISO 1", "pozn.", relations)
            self.assertEqual(json.loads(relations.read_text(encoding="utf-8")),
                             [{"from_identifier": "ISO/AWI 1", "to_identifier": "ISO 1", "relation_type": "ENACTED_AS",
                               "note": "pozn."}])


class EnsureSchemaTestCase(unittest.TestCase):
    def test_adds_the_relation_type_to_the_existing_ones(self):
        class Cursor:
            def __init__(self):
                self.sql, self.answers = [], [(1,), ("enum('AMENDS','TRANSLATION_OF')",)]

            def execute(self, sql, params=None):
                self.sql.append(" ".join(sql.split()))

            def fetchone(self):
                return self.answers.pop(0)
        cursor = Cursor()
        self.assertEqual(sc.ensure_schema(cursor), ["relation type ENACTED_AS"])
        self.assertIn("ENUM('AMENDS','TRANSLATION_OF','ENACTED_AS')", cursor.sql[-1])


if __name__ == "__main__":
    unittest.main()
