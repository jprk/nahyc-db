"""Editions of standards issued with a later date of effect (src/tools/norm_editions.py,
check_csn_validity.editions(); doc/MPO_PRIPOMINKY.md, odstavec 5): ČSN EN 13445
of 12/2026 takes effect on 1. 1. 2027 and the database switches to it that day.
No network, no database."""
import json
import pathlib
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "tools"))
import check_csn_validity as csn  # noqa: E402
import norm_editions as ne  # noqa: E402

NEW = {"designation": "ČSN EN 13445-2", "title": "Netopené tlakové nádoby - Část 2: Materiály", "issued": "12.2026",
       "effective_from": "2027-01-01", "catalog_number": "524693",
       "url": "https://csnonline.agentura-cas.cz/Detailnormy.aspx?k=524693"}
CACHE = {"NORM:ČSN EN 13445-2+A1": {"status": "platná", "source": "csnonline", "designation": "ČSN EN 13445-2+A1",
                                    "upcoming": NEW}}


def version(id_, number, label, effective, current, state):
    return {"id": id_, "version": number, "edition_label": label, "effective_date": effective,
            "is_current": current, "lifecycle_state": state}


class EditionsTestCase(unittest.TestCase):
    def test_family_joins_a_consolidated_amendment_and_the_edition_mark(self):
        self.assertEqual(csn.family("ČSN EN 13445-2+A1"), csn.family("ČSN EN 13445-2"))
        self.assertEqual(csn.family("ČSN EN 60079-1 ed. 3"), csn.family("ČSN EN 60079-1"))
        self.assertNotEqual(csn.family("ČSN EN 13445-2"), csn.family("ČSN EN 13445-21"))

    def test_iso_date(self):
        self.assertEqual(csn.iso_date("01.01.2027"), "2027-01-01")
        self.assertEqual(csn.iso_date("1.12.2021"), "2021-12-01")
        self.assertIsNone(csn.iso_date(""))

    def test_a_withdrawal_announced_for_later_leaves_the_edition_in_force(self):
        self.assertTrue(csn.in_force_on({"withdrawn": "1.1.2027"}, "2026-12-15"))
        self.assertFalse(csn.in_force_on({"withdrawn": "1.1.2027"}, "2027-01-01"))
        self.assertTrue(csn.in_force_on({"withdrawn": ""}, "2027-01-01"))

    def test_the_edition_in_force_and_the_upcoming_one(self):
        old = {"designation": "ČSN EN 13445-2+A1", "issued": "1.2024", "effective_from": "2024-02-01"}
        found = csn.pick_editions([old, NEW], "2026-11-20")
        self.assertIs(found["current"], old)
        self.assertIs(found["upcoming"], NEW)
        found = csn.pick_editions([old, NEW], "2027-01-01")
        self.assertIs(found["current"], NEW)
        self.assertIsNone(found["upcoming"])

    def test_a_new_standard_not_yet_in_effect_is_its_own_current_edition(self):
        new = {"designation": "ČSN EN IEC 60079-29-0", "issued": "11.2026", "effective_from": "2026-12-01"}
        self.assertEqual(csn.pick_editions([new], "2026-11-20"), {"current": new, "upcoming": None})


class PlanTestCase(unittest.TestCase):
    def test_the_new_edition_is_added_as_promulgated(self):
        docs = [(7, "ČSN EN 13445-2+A1", [version(70, 1, None, None, True, "active")])]
        actions = ne.plan(docs, CACHE, "2026-11-20")
        self.assertEqual(actions, [{"action": "add", "document_id": 7, "version": 2,
                                    "edition_label": "ČSN EN 13445-2 (vydání 12.2026)", "effective_date": "2027-01-01"}])

    def test_nothing_before_the_date_of_effect_once_added(self):
        docs = [(7, "ČSN EN 13445-2+A1", [version(70, 1, None, None, True, "active"),
                                          version(71, 2, "ČSN EN 13445-2 (vydání 12.2026)", "2027-01-01", False,
                                                  "promulgated")])]
        self.assertEqual(ne.plan(docs, CACHE, "2026-12-31"), [])

    def test_the_switch_on_the_date_of_effect(self):
        docs = [(7, "ČSN EN 13445-2+A1", [version(70, 1, None, None, True, "active"),
                                          version(71, 2, "ČSN EN 13445-2 (vydání 12.2026)", "2027-01-01", False,
                                                  "promulgated")])]
        actions = ne.plan(docs, CACHE, "2027-01-01")
        self.assertEqual([(a["action"], a["to_version_id"], a["from_version_id"]) for a in actions],
                         [("switch", 71, 70)])
        switched = [(7, "ČSN EN 13445-2+A1", [version(70, 1, None, None, False, "superseded"),
                                              version(71, 2, "ČSN EN 13445-2 (vydání 12.2026)", "2027-01-01", True,
                                                      "active")])]
        self.assertEqual(ne.plan(switched, CACHE, "2027-01-02"), [], "nothing more once switched")

    def test_added_and_switched_in_one_run_when_the_date_has_passed(self):
        docs = [(7, "ČSN EN 13445-2+A1", [version(70, 1, None, None, True, "active")])]
        actions = ne.plan(docs, CACHE, "2027-01-05")
        self.assertEqual([a["action"] for a in actions], ["add", "switch"])
        self.assertIsNone(actions[1]["to_version_id"])
        self.assertEqual(actions[1]["to_version"], 2)

    def test_an_edition_no_longer_listed_is_dropped(self):
        docs = [(7, "ČSN EN 13445-2+A1", [version(70, 1, None, None, True, "active"),
                                          version(71, 2, "ČSN EN 13445-2 (vydání 12.2026)", "2027-01-01", False,
                                                  "promulgated")])]
        cache = {"NORM:ČSN EN 13445-2+A1": {"status": "platná", "upcoming": None}}
        self.assertEqual([a["action"] for a in ne.plan(docs, cache, "2026-12-01")], ["drop"])
        self.assertEqual(ne.plan(docs, {}, "2026-12-01"), [], "no word of the check, nothing dropped")

    def test_a_new_standard_takes_effect(self):
        docs = [(9, "ČSN EN IEC 60079-29-0", [version(90, 1, "ČSN EN IEC 60079-29-0 (vydání 11.2026)", "2026-12-01",
                                                      True, "promulgated")])]
        self.assertEqual(ne.plan(docs, {}, "2026-11-30"), [])
        actions = ne.plan(docs, {}, "2026-12-01")
        self.assertEqual([(a["action"], a["to_version_id"], a["from_version_id"]) for a in actions],
                         [("switch", 90, None)])

    def test_free_text_dates_never_trigger(self):
        docs = [(5, "ČSN EN 1", [version(50, 1, "x", "2015", False, "superseded"),
                                 version(51, 2, "y", "platná od 1. 1. 2020", True, "active")])]
        self.assertEqual(ne.plan(docs, {}, "2027-01-01"), [])

    def test_candidate_versions(self):
        evidence = {"edition": "ČSN EN 13445-1", "issued": "11.2021", "effective_from": "2021-12-01",
                    "upcoming_edition": {"edition": "ČSN EN 13445-1", "issued": "12.2026", "effective_from": "2027-01-01"}}
        self.assertEqual(ne.candidate_versions(evidence, "2026-11-20"),
                         [(1, "ČSN EN 13445-1 (vydání 11.2021)", "2021-12-01", 1, "active"),
                          (2, "ČSN EN 13445-1 (vydání 12.2026)", "2027-01-01", 0, "promulgated")])
        self.assertIsNone(ne.candidate_versions({"edition": "ČSN EN 1"}, "2026-11-20"))


class CommittedDataTestCase(unittest.TestCase):
    """The candidates of ČSN EN 13445 carry the edition in force, the 12/2026 edition is upcoming."""

    def test_13445_candidates(self):
        data = json.loads((REPO_ROOT / "data" / "20260430_MPO" / "mpo_candidates.json").read_text(encoding="utf-8"))
        parts = [c for c in data["candidates"] if c["designation"].startswith("ČSN EN 13445-")]
        self.assertEqual(len(parts), 8)
        for c in parts:
            evidence = c["evidence"]
            self.assertLessEqual(evidence["effective_from"], "2026-11-20", c["designation"])
            self.assertEqual(evidence["upcoming_edition"]["issued"], "12.2026", c["designation"])
            self.assertEqual(evidence["upcoming_edition"]["effective_from"], "2027-01-01", c["designation"])
            self.assertEqual(c["validity_status"], "platná")
        self.assertEqual(sorted(c["designation"] for c in parts if c["designation"].endswith("+A1")),
                         ["ČSN EN 13445-2+A1", "ČSN EN 13445-3+A1", "ČSN EN 13445-4+A1"])


if __name__ == "__main__":
    unittest.main()
