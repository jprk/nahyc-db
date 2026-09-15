import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))

import load_document_relations as ldr
from load_document_relations import resolve_relations, dedupe_resolved_relations


class ResolveRelationsTestCase(unittest.TestCase):
    def setUp(self):
        self.identifier_map = {"426/2021 Sb.": 101, "266/1994 Sb.": 42}

    def test_resolves_both_identifiers(self):
        relations = [{"from_identifier": "426/2021 Sb.", "to_identifier": "266/1994 Sb.",
                      "relation_type": "AMENDS", "note": "..."}]
        resolved, unresolved = resolve_relations(relations, self.identifier_map)
        self.assertEqual(unresolved, [])
        self.assertEqual(resolved[0]["from_document_id"], 101)
        self.assertEqual(resolved[0]["to_document_id"], 42)

    def test_unknown_from_identifier_goes_to_review_queue(self):
        relations = [{"from_identifier": "999/9999 Sb.", "to_identifier": "266/1994 Sb.",
                      "relation_type": "AMENDS"}]
        resolved, unresolved = resolve_relations(relations, self.identifier_map)
        self.assertEqual(resolved, [])
        self.assertIn("from_identifier '999/9999 Sb.' not found", unresolved[0]["_problems"])

    def test_unknown_to_identifier_goes_to_review_queue(self):
        relations = [{"from_identifier": "426/2021 Sb.", "to_identifier": "0/0000 Sb.",
                      "relation_type": "AMENDS"}]
        resolved, unresolved = resolve_relations(relations, self.identifier_map)
        self.assertEqual(resolved, [])
        self.assertEqual(len(unresolved), 1)

    def test_unrecognized_relation_type_goes_to_review_queue_not_a_guess(self):
        relations = [{"from_identifier": "426/2021 Sb.", "to_identifier": "266/1994 Sb.",
                      "relation_type": "SUPERSEDES"}]
        resolved, unresolved = resolve_relations(relations, self.identifier_map)
        self.assertEqual(resolved, [])
        self.assertIn("unrecognized relation_type 'SUPERSEDES'", unresolved[0]["_problems"])

    def test_national_equivalent_is_a_valid_relation_type(self):
        # doc/PLAN.md §15: the new CZ<->SK relation type.
        relations = [{"from_identifier": "426/2021 Sb.", "to_identifier": "266/1994 Sb.",
                      "relation_type": "NATIONAL_EQUIVALENT"}]
        resolved, unresolved = resolve_relations(relations, self.identifier_map)
        self.assertEqual(unresolved, [])
        self.assertEqual(resolved[0]["relation_type"], "NATIONAL_EQUIVALENT")


class DedupeResolvedRelationsTestCase(unittest.TestCase):
    """doc/PLAN.md §15 follow-up: document_relations_split.json is written
    per raw Sinay_Zakony spreadsheet row, before deduplicate_db.py merges
    duplicate rows -- the same CZ+SK pair can legitimately appear twice,
    resolving to an identical (from, to, relation_type) triple that would
    otherwise violate document_relation's unique constraint on insert."""

    def test_exact_duplicate_triple_is_dropped(self):
        resolved = [
            {"from_document_id": 71, "to_document_id": 72, "relation_type": "NATIONAL_EQUIVALENT"},
            {"from_document_id": 71, "to_document_id": 72, "relation_type": "NATIONAL_EQUIVALENT"},
        ]
        self.assertEqual(len(dedupe_resolved_relations(resolved)), 1)

    def test_different_relation_type_for_same_pair_is_kept(self):
        resolved = [
            {"from_document_id": 1, "to_document_id": 2, "relation_type": "AMENDS"},
            {"from_document_id": 1, "to_document_id": 2, "relation_type": "IMPLEMENTS"},
        ]
        self.assertEqual(len(dedupe_resolved_relations(resolved)), 2)

    def test_no_duplicates_is_unchanged(self):
        resolved = [
            {"from_document_id": 1, "to_document_id": 2, "relation_type": "AMENDS"},
            {"from_document_id": 3, "to_document_id": 4, "relation_type": "ADOPTS"},
        ]
        self.assertEqual(dedupe_resolved_relations(resolved), resolved)


class LoadRelationSourcesTestCase(unittest.TestCase):
    """doc/PLAN.md §15: a third source file (build-time NATIONAL_EQUIVALENT
    pairs) is merged in alongside the existing two — missing files are
    silently skipped, not an error, same as before."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        base = pathlib.Path(self.tmpdir.name)
        self.hand = base / "document_relations.json"
        self.auto = base / "document_relations_auto.json"
        self.split = base / "document_relations_split.json"

        self._orig = (ldr.RELATIONS_PATH, ldr.AUTO_RELATIONS_PATH, ldr.SPLIT_RELATIONS_PATH)
        ldr.RELATIONS_PATH, ldr.AUTO_RELATIONS_PATH, ldr.SPLIT_RELATIONS_PATH = (
            self.hand, self.auto, self.split)
        self.addCleanup(self._restore_paths)

    def _restore_paths(self):
        ldr.RELATIONS_PATH, ldr.AUTO_RELATIONS_PATH, ldr.SPLIT_RELATIONS_PATH = self._orig

    def test_merges_all_three_when_present(self):
        self.hand.write_text(json.dumps([{"relation_type": "AMENDS"}]), encoding="utf-8")
        self.auto.write_text(json.dumps([{"relation_type": "ADOPTS"}]), encoding="utf-8")
        self.split.write_text(json.dumps([{"relation_type": "NATIONAL_EQUIVALENT"}]), encoding="utf-8")
        relations = ldr.load_relation_sources()
        self.assertEqual(
            sorted(r["relation_type"] for r in relations),
            ["ADOPTS", "AMENDS", "NATIONAL_EQUIVALENT"])

    def test_missing_split_file_is_silently_skipped(self):
        self.hand.write_text(json.dumps([{"relation_type": "AMENDS"}]), encoding="utf-8")
        self.auto.write_text(json.dumps([]), encoding="utf-8")
        # self.split intentionally never written
        relations = ldr.load_relation_sources()
        self.assertEqual(relations, [{"relation_type": "AMENDS"}])


if __name__ == "__main__":
    unittest.main()
