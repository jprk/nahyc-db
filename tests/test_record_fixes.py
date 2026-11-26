"""Corrections of the record check (doc/KONTROLA_ZAZNAMU.md, odstavec 7): the source-qualified
correction key, the ISO step of plan_record_fixes.py and review_findings.py. No network, no
model, no database."""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "tools"))

import build_unified_db as bud  # noqa: E402
import plan_record_fixes as prf  # noqa: E402
import review_findings as rf  # noqa: E402


class SourceQualifiedKeyTestCase(unittest.TestCase):
    def test_names_the_record_of_one_source(self):
        corrections = {"ASTM F1624-12 @Sinay_Normy": {"merged_into": "ASTM F1624-12"}}
        sinay = {"znacka": "ASTM F1624-12", "zdroj_dat": "Sinay_Normy", "nazev_cz": "x"}
        prokop = {"znacka": "ASTM F1624-12", "zdroj_dat": "Prokop_Normy", "nazev_cz": "x"}
        self.assertFalse(bud.apply_manual_corrections(dict(sinay), corrections))
        self.assertTrue(bud.apply_manual_corrections(dict(prokop), corrections))
        self.assertEqual(bud.correction_entry(prokop, {"ASTM F1624-12": {"changes": {}}})[0], "ASTM F1624-12")


def doc(id_, identifier, slug=None):
    return {"id": id_, "identifier": identifier, "title": "t", "slug": slug or f"s{id_}", "type": "Norma",
            "language": "EN", "source": "Sinay_Normy", "description": None}


class IsoPlanTestCase(unittest.TestCase):
    def index(self):
        published = {"id": 1, "reference": "ISO 19880-7:2025", "currentStage": 6060, "publicationDate": "2025-08-06",
                     "title": {"en": "Gaseous hydrogen — Fuelling stations — Part 7: Rubber O-rings"},
                     "scope": {"en": "<p>This document specifies O-rings.</p>"}}
        abandoned = {"id": 2, "reference": "ISO/CD 17268-3", "currentStage": 3098, "title": {"en": "x"}}
        return {"ISO 19880-7": [published], ("", "19880-7"): [published],
                "ISO/CD 17268-3": [abandoned], ("", "17268-3"): [abandoned]}

    def test_drafts_merge_into_the_published_standard(self):
        documents = [doc(594, "ISO/DIS 19880-7", "iso-dis-19880-7"), doc(1204, "ISO/WD 19880-7"),
                     doc(1178, "ISO/AWI 17268-3")]
        survivors, merges, _ = prf.iso_plan(documents, self.index(), [])
        self.assertEqual(len(survivors), 1)
        key, entry = survivors[0]
        self.assertEqual(key, "ISO/DIS 19880-7")
        self.assertEqual(entry["changes"]["znacka"], "ISO 19880-7")
        self.assertEqual(entry["changes"]["slug"], "iso-dis-19880-7")  # the permanent address stays
        self.assertEqual(entry["changes"]["anotace_poznamka"], "This document specifies O-rings.")
        self.assertEqual(merges, [("ISO/WD 19880-7", merges[0][1])])
        self.assertEqual(merges[0][1]["merged_into"], "ISO 19880-7")

    def test_an_edition_date_goes_from_the_identifier(self):
        survivors, _, _ = prf.iso_plan([doc(1, "ISO 19880-7/ - 2025.08")], self.index(),
                                       [{"id": 1, "check": "iso_title"}] and [{"id": 1, "check": "duplicate_title"}])
        self.assertEqual(survivors[0][1]["changes"]["znacka"], "ISO 19880-7")


class ReviewFindingsTestCase(unittest.TestCase):
    FINDINGS = [{"id": 1, "identifier": "A", "check": "iso_withdrawn", "detail": "zrušena"},
                {"id": 1, "identifier": "A", "check": "model_relevance", "detail": "nesouvisí"},
                {"id": 2, "identifier": "STN EN IEC 62282-8-301/ - 2023.11", "check": "model_description",
                 "detail": "x"}]

    def test_one_reason_per_document_without_verified_findings(self):
        reasons = rf.reasons(self.FINDINGS)
        self.assertEqual(list(reasons), [1])
        self.assertEqual(reasons[1][1], "Kontrola záznamů: ISO poslední vydání zrušila, model: nesouvisí s vodíkem")

    def test_plan_is_idempotent(self):
        class Cursor:
            def __init__(self, current, items):
                self.current, self.items, self.rows = current, items, []

            def execute(self, sql, params=None):
                self.rows = list(self.current.items()) if sql.startswith("SELECT id") else [(i,) for i in self.items]

            def fetchall(self):
                return self.rows
        fresh = rf.plan(Cursor({1: "chybí popis", 3: None}, []), self.FINDINGS)
        self.assertEqual(fresh[0][2], "chybí popis; Kontrola záznamů: ISO poslední vydání zrušila, "
                                      "model: nesouvisí s vodíkem")
        self.assertTrue(fresh[0][3])
        again = rf.plan(Cursor({1: fresh[0][2]}, [1]), self.FINDINGS)
        self.assertEqual(again, [(1, again[0][1], None, False)])


class ExcludedCandidatesTestCase(unittest.TestCase):
    def test_the_closure_does_not_propose_an_excluded_act_again(self):
        import candidates
        excluded = candidates.excluded_keys({"2000/43/ES": {"exclude": True}, "ISO 1": {"changes": {}}})
        self.assertEqual(excluded, {"EU:2000/43"})
        row = {"family": "EU", "in_database": False, "cited_by": 3, "amendment_share": 0, "key": "EU:2000/43",
               "kind": "directive", "citing_ids": [], "context": ""}
        self.assertEqual(candidates.from_closure([row], {}, excluded=excluded), [])
        self.assertEqual(len(candidates.from_closure([row], {}, excluded=set())), 1)


if __name__ == "__main__":
    unittest.main()
