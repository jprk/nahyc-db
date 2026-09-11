import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))

from load_document_relations import resolve_relations


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


if __name__ == "__main__":
    unittest.main()
