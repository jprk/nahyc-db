import json
import pathlib
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "tools"))
import backfill_provenance as bp

NOTE = "Nalezeno screeningem EUR-Lex Cellar (klíčové slovo 'hydrogen', doc/PLAN.md §28), ověřeno živě."


class PlanTestCase(unittest.TestCase):
    def test_a_provenance_note_moves_out_of_the_description(self):
        self.assertEqual(bp.plan([(1, "Nařízení", NOTE, None)], {}), [(1, None, NOTE)])

    def test_a_real_description_stays(self):
        self.assertEqual(bp.plan([(1, "Nařízení", "Nařízení stanoví pravidla.", None)], {}), [])

    def test_a_strategy_gets_the_description_and_provenance_of_its_record(self):
        strategies = {"Vodíková strategie": ("Popis.", "doc/PLAN.md §31")}
        rows = [(5, "Vodíková strategie", "Popis, doc/PLAN.md §31 — přidáno.", None)]
        self.assertEqual(bp.plan(rows, strategies), [(5, "Popis.", "doc/PLAN.md §31")])

    def test_a_strategy_already_done_is_left_alone(self):
        strategies = {"Vodíková strategie": ("Popis.", "doc/PLAN.md §31")}
        self.assertEqual(bp.plan([(5, "Vodíková strategie", "Popis.", "doc/PLAN.md §31")], strategies), [])


class ReviewFlagsTestCase(unittest.TestCase):
    def test_an_emptied_description_is_flagged(self):
        self.assertEqual(bp.review_flags(None, None), (True, bp.MISSING_DESCRIPTION))

    def test_other_reasons_stay(self):
        reason = "EU akt: autoritativní gestor (DG/instituce) se v EUR-Lex/Cellar nepodařilo dohledat"
        self.assertEqual(bp.review_flags(reason, ""), (True, f"{reason}; {bp.MISSING_DESCRIPTION}"))

    def test_a_description_clears_only_its_own_reason(self):
        self.assertEqual(bp.review_flags(bp.MISSING_DESCRIPTION, "Popis."), (False, None))


class CommittedDataTestCase(unittest.TestCase):
    """No committed record carries a provenance note as its public description."""

    def test_no_provenance_note_in_anotace_poznamka(self):
        for path in sorted((REPO_ROOT / "data").glob("discovered_*.json")) + [bp.STRATEGY_PATH]:
            for record in json.loads(path.read_text(encoding="utf-8")):
                if not isinstance(record, dict):
                    continue
                note = record.get("anotace_poznamka") or ""
                with self.subTest(path=path.name, title=record.get("nazev_cz")):
                    self.assertIsNone(bp.PROVENANCE_NOTE.match(note))
                    self.assertNotIn("doc/PLAN.md", note)


if __name__ == "__main__":
    unittest.main()
