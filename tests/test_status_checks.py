"""The last check of a document's state (src/tools/status_checks.py) and its use
on a rebuild (init_db.last_state_check, current_version_state) and in the live
database (backfill_document_states.plan_states keeps an editor's state)."""
import datetime
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))
import backfill_document_states as bf  # noqa: E402
import init_db  # noqa: E402
import status_checks as sc  # noqa: E402

CACHE = {
    "CZ:183/2006": {"status": "zrušený", "source": "e-sbirka", "checked_at": "2026-10-27"},
    "EU:2024/1788": {"status": "účinný", "source": "cellar", "checked_at": "2026-10-27"},
    "NORM:EN 17124": {"status": "platná", "source": "csnonline", "checked_at": "2026-11-05"},
    "NORM:ISO 19880-1": {"status": "nezjištěno", "source": "normoff", "checked_at": "2026-11-05"},
    "NORM:EN 1594": {"source": "ec-harmonised-standards", "harmonised": [], "checked_at": "2026-11-05"},
    "NORM:TPG 609 02": {"status": "platná", "source": "vestnik-unmz", "checked_at": "2026-11-06"},
}


class LastCheckTestCase(unittest.TestCase):
    def test_acts_and_standards_by_their_keys(self):
        self.assertEqual(sc.last_check("183/2006 Sb.", "Stavební zákon", CACHE), ("2026-10-27", "e-Sbírka"))
        self.assertEqual(sc.last_check("(EU) 2024/1788", "", CACHE), ("2026-10-27", "EUR-Lex (Cellar)"))
        self.assertEqual(sc.last_check("ČSN EN 17124", "", CACHE), ("2026-11-05", "ČSN online"))
        self.assertEqual(sc.last_check("TPG 609 02", "", CACHE), ("2026-11-06", "Věstník ÚNMZ"))

    def test_an_inconclusive_entry_is_not_a_check(self):
        self.assertIsNone(sc.last_check("ISO 19880-1", "", CACHE))
        self.assertIsNone(sc.last_check("EN 1594", "", CACHE))
        self.assertIsNone(sc.last_check(None, "Vodíková strategie", CACHE))

    def test_a_date_never_moves_back(self):
        self.assertTrue(sc.newer(("2026-10-27", "x"), None))
        self.assertTrue(sc.newer(("2026-10-27", "x"), datetime.date(2026, 10, 1)))
        self.assertFalse(sc.newer(("2026-10-27", "x"), datetime.date(2026, 11, 19)))
        self.assertFalse(sc.newer(None, None))

    def test_plan_lists_only_newer_dates(self):
        rows = [(1, "183/2006 Sb.", "", None), (2, "(EU) 2024/1788", "", datetime.date(2026, 11, 19)),
                (3, None, "Strategie", None)]
        self.assertEqual(sc.plan_checks(rows, CACHE), [(1, "2026-10-27", "e-Sbírka")])

    def test_ensure_columns_adds_only_the_missing_ones(self):
        class Cursor:
            def __init__(self):
                self.sql, self.last = [], None

            def execute(self, sql, params=None):
                self.sql.append(sql)
                self.last = params

            def fetchone(self):
                return (1,) if self.last == ("status_checked_at",) else (0,)
        cursor = Cursor()
        self.assertTrue(sc.ensure_columns(cursor))
        self.assertEqual([s for s in cursor.sql if s.startswith("ALTER")],
                         ["ALTER TABLE Document ADD COLUMN status_checked_by VARCHAR(100) NULL"])


class RebuildTestCase(unittest.TestCase):
    def test_the_editors_confirmation_wins_when_newer(self):
        item = {"stav_overen": "2026-11-19", "stav_overil": "editor Jana Nováková"}
        self.assertEqual(init_db.last_state_check(item, "183/2006 Sb.", "", CACHE),
                         ("2026-11-19", "editor Jana Nováková"))
        self.assertEqual(init_db.last_state_check({"stav_overen": "2026-01-01"}, "183/2006 Sb.", "", CACHE),
                         ("2026-10-27", "e-Sbírka"))
        self.assertIsNone(init_db.last_state_check({}, None, "Strategie", CACHE))

    def test_the_editors_state_replaces_the_one_from_the_text(self):
        state = init_db.current_version_state
        self.assertEqual(state({"stav_dokumentu": "promulgated"}, "draft", "1/2099 Sb.", "", {}), "promulgated")
        self.assertEqual(state({"stav_dokumentu": "superseded"}, "draft", "183/2006 Sb.", "", CACHE), "superseded")
        self.assertEqual(state({"stav_dokumentu": "active"}, "draft", "183/2006 Sb.", "", CACHE), "repealed")
        self.assertEqual(state({}, "draft", "183/2006 Sb.", "", CACHE), "draft")
        self.assertEqual(state({"stav_dokumentu": "nonsense"}, "active", "1/2099 Sb.", "", {}), "active")


class EditorStateKeptTestCase(unittest.TestCase):
    def test_promulgated_stays_without_a_check_and_goes_active_on_its_word(self):
        validity = {"CZ:283/2021": {"status": "účinný"}}
        rows = [(1, "1/2099 Sb.", "", 11, "promulgated"), (2, "283/2021 Sb.", "", 12, "promulgated"),
                (3, "2/2099 Sb.", "", 13, "superseded")]
        self.assertEqual(bf.plan_states(rows, validity), [(12, 2, "283/2021 Sb.", "promulgated", "active")])


if __name__ == "__main__":
    unittest.main()
