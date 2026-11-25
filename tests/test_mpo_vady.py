"""The defects of the web found on 21. 11. 2026 (doc/MPO_OVERENI_WEBU.md, Z3–Z5;
Z1 is in test_app_export.py, Z2 in tests/e2e/test_mpo_vady.py): stage stamps of
standards in the effective date, description and keywords (init_db.py,
fix_norm_stage_fields.py), nicknames appended to titles of EU directives
(data/manual_corrections.json) and the date of the last check after a refresh of
consolidated versions (status_checks.py, refresh_eu_consolidations.py)."""
import copy
import json
import pathlib
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "tools"))
import build_unified_db  # noqa: E402
import fix_norm_stage_fields as fix  # noqa: E402
import init_db  # noqa: E402
import refresh_eu_consolidations as refresh  # noqa: E402
import status_checks as sc  # noqa: E402


class FakeCursor:
    """Returns the queued result sets in order; records executed statements."""

    def __init__(self, results):
        self.results = list(results)
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchall(self):
        return self.results.pop(0) if self.results else []


class StageStampTestCase(unittest.TestCase):
    def test_published_with_date_becomes_month(self):
        self.assertEqual(init_db.normalize_effective_date("Veröffentlicht-Publikovaný / 2021-12"), "od 12/2021")

    def test_drafts_and_work_items_have_no_effective_date(self):
        for stamp in ("Arbeitsdokument (Work Item)-Pracovný dokument (pracovná položka)",
                      "Arbeitsdokument (Work Item)-Pracovný dokument (pracovná položka) / 2023-03",
                      "vorläufiges Arbeitsdokument (PWI)-predbežný pracovný dokument (PWI) / 2019-05",
                      "Entwurf-Návrh", "Entwurf-Návrh / 2023-03", "Veröffentlicht-Publikovaný"):
            self.assertEqual(init_db.normalize_effective_date(stamp), "", stamp)

    def test_other_text_is_kept(self):
        for text in ("od 02/2025", "1.1.2015", "Platnost od 20.11.2023", "Od 26.5.2016", ""):
            self.assertEqual(init_db.normalize_effective_date(text), text)

    def test_lifecycle_state_still_read_from_the_raw_stamp(self):
        self.assertEqual(init_db.classify_lifecycle_state("Entwurf-Návrh / 2023-03", True), "draft")

    def test_placeholder_description(self):
        for text in ("noch nocht vorhanden", "noch nicht vorhanden", "-"):
            self.assertEqual(init_db.resolve_description({"anotace_poznamka": text}), "", text)
        self.assertEqual(init_db.resolve_description({"anotace_poznamka": "Diese Norm legt fest."}),
                         "Diese Norm legt fest.")
        self.assertIn("chybí popis/anotace dokumentu",
                      init_db.detect_data_quality_issues({"znacka": "ISO 19885-2", "nazev_cz": "Gaseous hydrogen",
                                                          "anotace_poznamka": "noch nocht vorhanden"}))

    def test_status_keyword(self):
        self.assertTrue(init_db.is_status_keyword("Stav k 02/2025: v príprave"))
        self.assertTrue(init_db.is_status_keyword("Stav k 02/2025: Prebieha prijatie do sústavy STN"))
        self.assertFalse(init_db.is_status_keyword("STN (prijatá v sústave)"))
        self.assertFalse(init_db.is_status_keyword("Wasserstoff"))

    def test_versions_store_the_normalized_date(self):
        versions = init_db.resolve_document_versions({"versions": [
            {"effective_date": "Veröffentlicht-Publikovaný / 2018-01", "is_current": False},
            {"effective_date": "Entwurf-Návrh / 2023-03", "is_current": True}]})
        self.assertEqual([v["effective_date"] for v in versions], ["od 01/2018", None])
        self.assertEqual([v["lifecycle_state"] for v in versions], ["superseded", "draft"])


class FixNormStageFieldsTestCase(unittest.TestCase):
    def test_plan_and_execute(self):
        cursor = FakeCursor([
            [(575, "Arbeitsdokument (Work Item)-Pracovný dokument (pracovná položka)", "noch nocht vorhanden", 0, None),
             (900, "Veröffentlicht-Publikovaný / 2021-12", "Real description", 1, "jazyk"),
             (901, "od 02/2025", "", 0, None),
             (902, None, "-", 1, "chybí popis/anotace dokumentu")],
            [(1, "od 02/2025"), (2, "Entwurf-Návrh / 2023-03")],
            [(7, "Stav k 02/2025: v príprave", 34), (8, "Wasserstoff", 3)],
        ])
        changes = fix.plan(cursor)
        self.assertEqual(changes["documents"], [
            (575, "effective_date", "Arbeitsdokument (Work Item)-Pracovný dokument (pracovná položka)", ""),
            (575, "description", "noch nocht vorhanden", ""),
            (900, "effective_date", "Veröffentlicht-Publikovaný / 2021-12", "od 12/2021"),
            (902, "description", "-", "")])
        self.assertEqual(changes["reviews"], [(575, 1, "chybí popis/anotace dokumentu"),
                                              (902, 1, "chybí popis/anotace dokumentu")])
        self.assertEqual(changes["versions"], [(2, "Entwurf-Návrh / 2023-03", None)])
        self.assertEqual(changes["keywords"], [(7, "Stav k 02/2025: v príprave", 34)])
        cursor.executed.clear()
        fix.execute(cursor, changes)
        statements = [sql for sql, _ in cursor.executed]
        self.assertIn("DELETE FROM Keyword WHERE id = %s", statements)
        self.assertEqual(sum(1 for s in statements if s.startswith("UPDATE Document SET")), 6)

    def test_nothing_to_do_on_clean_data(self):
        cursor = FakeCursor([[(1, "od 02/2025", "Popis", 0, None)], [], [(8, "Wasserstoff", 3)]])
        changes = fix.plan(cursor)
        self.assertEqual(sum(len(v) for v in changes.values()), 0)


class DirectiveNicknameTestCase(unittest.TestCase):
    """Z4: "Známá jako RED III Direktiva", "ATEX", "Pressure Equipment Directive (PED)"
    appended to the titles of directives in the Haltuf table."""

    NICKNAMES = ("Známá jako", "Direktiva", "\n\nATEX", "\n\nPressure Equipment Directive")

    def test_corrected_records_have_official_titles(self):
        records = json.loads((REPO_ROOT / "data" / "database_merged_deduplicated.json").read_text(encoding="utf-8"))
        corrections = build_unified_db.load_manual_corrections()
        wanted = {"(EU) 2023/2413", "(EU) 2023/2413 [EN]", "(EU) 2018/2001 [EN]", "2014/34/EU",
                  "2014/34/EU [EN]", "2014/68/EU [EN]"}
        seen = {}
        for record in records:
            record = copy.deepcopy(record)
            if not build_unified_db.apply_manual_corrections(record, corrections):
                continue
            title = init_db.resolve_title(record) or ""
            for nickname in self.NICKNAMES:
                self.assertNotIn(nickname, title, record.get("znacka"))
            if record.get("znacka") in wanted:
                seen[record["znacka"]] = title
        self.assertEqual(set(seen), wanted)
        self.assertTrue(seen["(EU) 2023/2413"].startswith(
            "Směrnice Evropského parlamentu a Rady (EU) 2023/2413 ze dne 18. října 2023, kterou se mění"))
        self.assertTrue(seen["(EU) 2023/2413 [EN]"].startswith("Directive (EU) 2023/2413"))


class ConsolidationCheckTestCase(unittest.TestCase):
    """Z5: a refresh of the consolidated versions is a check of the act in Cellar."""

    CONSOLIDATIONS = {"32008R1272": {"identifier": "(ES) 1272/2008", "checked_at": "2026-11-20",
                                     "consolidations": []}}

    def test_newer_consolidation_check_wins(self):
        cache = {"EU:2008/1272": {"status": "účinný", "source": "cellar", "checked_at": "2026-10-27"}}
        sc.merge_consolidation_checks(cache, self.CONSOLIDATIONS)
        self.assertEqual(cache["EU:2008/1272"]["status"], "účinný")
        self.assertEqual(sc.last_check("(ES) 1272/2008", "", cache), ("2026-11-20", "EUR-Lex (Cellar)"))

    def test_older_consolidation_check_does_not_move_back(self):
        cache = {"EU:2008/1272": {"status": "účinný", "source": "cellar", "checked_at": "2026-12-01"}}
        sc.merge_consolidation_checks(cache, self.CONSOLIDATIONS)
        self.assertEqual(sc.last_check("(ES) 1272/2008", "", cache)[0], "2026-12-01")

    def test_act_without_validity_entry(self):
        cache = sc.merge_consolidation_checks({}, self.CONSOLIDATIONS)
        self.assertEqual(sc.last_check("(ES) 1272/2008", "", cache), ("2026-11-20", "EUR-Lex (Cellar)"))

    def test_refresh_plans_the_date(self):
        cursor = FakeCursor([[(1219, "(ES) 1272/2008", "CLP", "2026-10-27")]])
        checks = refresh.plan_status_checks(cursor, [{"identifier": "(ES) 1272/2008", "celex": "32008R1272"}],
                                            self.CONSOLIDATIONS)
        self.assertEqual(checks, [(1219, "2026-11-20", "EUR-Lex (Cellar)")])
        self.assertIn("identifier IN (%s)", cursor.executed[0][0])

    def test_refresh_keeps_a_newer_date(self):
        cursor = FakeCursor([[(1219, "(ES) 1272/2008", "CLP", "2026-11-21")]])
        self.assertEqual(refresh.plan_status_checks(cursor, [{"identifier": "(ES) 1272/2008"}],
                                                    self.CONSOLIDATIONS), [])


if __name__ == "__main__":
    unittest.main()
