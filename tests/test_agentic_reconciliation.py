import pathlib
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from agentic.reconciliation import reconcile, title_overlap_score


class TitleOverlapScoreTestCase(unittest.TestCase):
    def test_identical_titles_score_one(self):
        self.assertEqual(title_overlap_score("hydrogen refuelling regulation", "hydrogen refuelling regulation"), 1.0)

    def test_disjoint_titles_score_zero(self):
        self.assertEqual(title_overlap_score("hydrogen refuelling regulation", "unrelated waste directive"), 0.0)

    def test_partial_overlap_between_bounds(self):
        score = title_overlap_score("hydrogen refuelling infrastructure regulation",
                                     "hydrogen refuelling infrastructure directive")
        self.assertGreater(score, 0.0)
        self.assertLess(score, 1.0)

    def test_empty_title_scores_zero(self):
        self.assertEqual(title_overlap_score("", "hydrogen regulation"), 0.0)
        self.assertEqual(title_overlap_score("hydrogen regulation", None), 0.0)


def _cursor_with_fetchall(rows):
    cursor = MagicMock()
    cursor.fetchall.return_value = rows
    return cursor


class ReconcileTestCase(unittest.TestCase):
    def test_exact_identifier_match_is_existing(self):
        cursor = _cursor_with_fetchall([("(EU) 2023/1804",)])
        result = reconcile("(EU) 2023/1804", "Some title", cursor)
        self.assertEqual(result, {"action": "existing", "matched_znacka": "(EU) 2023/1804"})

    def test_no_identifier_and_no_similar_title_is_new(self):
        cursor = MagicMock()
        cursor.fetchall.side_effect = [[], []]
        result = reconcile("(EU) 9999/9999", "Totally novel act title", cursor)
        self.assertEqual(result["action"], "new")
        self.assertIsNone(result["matched_znacka"])

    def test_similar_title_without_identifier_match_is_ambiguous(self):
        # identifier=None -> the identifier-lookup branch never executes,
        # so only the title query runs a single fetchall().
        cursor = _cursor_with_fetchall(
            [("(EU) 2020/1", "hydrogen refuelling infrastructure regulation for member states")])
        result = reconcile(None, "hydrogen refuelling infrastructure regulation for member states here",
                            cursor)
        self.assertEqual(result["action"], "ambiguous")
        self.assertEqual(result["matched_znacka"], "(EU) 2020/1")

    def test_never_returns_a_merge_action(self):
        cursor = _cursor_with_fetchall([("(EU) 2023/1804",)])
        result = reconcile("(EU) 2023/1804", "x", cursor)
        self.assertIn(result["action"], ("existing", "ambiguous", "new"))


if __name__ == "__main__":
    unittest.main()
