"""Consolidated versions of EU acts (src/tools/eu_consolidations.py,
refresh_eu_consolidations.py, src/sites/eurlex.consolidated_versions; doc/CELLAR_FULLTEXT.md,
odstavec 7): CLP shows its consolidated version of 01.07.2026 and switches to the one
of 01.01.2027 on that day; the original text stays a superseded version. No network;
the database part runs against fakes, the live/test database is not touched."""
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "tools"))
sys.path.insert(0, str(REPO_ROOT / "src"))
import eu_consolidations as ec  # noqa: E402
import fetch_fulltext as ff  # noqa: E402
import refresh_eu_consolidations as rc  # noqa: E402
from sites import eurlex  # noqa: E402

ACT = {"celex": "32008R1272", "identifier": "(ES) 1272/2008", "name": "CLP", "language": "CS",
       "original": {"label": "původní znění (Úř. věst. L 353, 31.12.2008)", "effective_date": "2009-01-20"}}
CONFIG = [ACT]
CACHE = {"32008R1272": {"identifier": "(ES) 1272/2008", "language": "ces", "checked_at": "2026-11-20",
                        "consolidations": [{"celex": "02008R1272-20090120", "date": "2009-01-20"},
                                           {"celex": "02008R1272-20260501", "date": "2026-05-01"},
                                           {"celex": "02008R1272-20260701", "date": "2026-07-01"},
                                           {"celex": "02008R1272-20270101", "date": "2027-01-01"}]}}
ORIGINAL_PDF = "data/fulltext/ES_1272_2008__1fe6eaaa.pdf"
CONSOLIDATED = "data/fulltext/ES_1272_2008__2d5ccccc.html"
MANIFEST = {
    "V02_Bibliografie|(ES) 1272/2008|odkaz_hlavni": {"status": "fetched", "local_path": ORIGINAL_PDF},
    "V02_Bibliografie|(ES) 1272/2008|konsolidace_20260701": {"status": "fetched", "local_path": CONSOLIDATED},
}


def db_doc(versions, file_path=ORIGINAL_PDF):
    return {"(ES) 1272/2008": {"id": 1220, "file_path": file_path, "versions": versions}}


def original_row():
    return {"id": 1220, "version": 1, "edition_label": None, "effective_date": None, "url": None,
            "file_path": None, "is_current": True, "lifecycle_state": "active"}


def state_after(actions, versions, file_path=ORIGINAL_PDF):
    """The versions and the document's file after `actions` (what execute() writes)."""
    versions = {v["version"]: dict(v) for v in versions}
    for a in actions:
        if a["action"] == "add":
            versions[a["version"]] = {k: a[k] for k in ec._COMPARED} | {"version": a["version"]}
        elif a["action"] == "update":
            for column, (_old, new) in a["changes"].items():
                versions[a["version"]][column] = new
        elif a["action"] == "file":
            file_path = a["new"]
    return [versions[n] for n in sorted(versions)], file_path


class HelpersTestCase(unittest.TestCase):
    def test_labels_and_addresses(self):
        self.assertEqual(ec.edition_label("2026-07-01"), "konsolidované znění ke dni 01.07.2026")
        self.assertEqual(ec.field_of({"date": "2026-07-01"}), "konsolidace_20260701")
        self.assertEqual(ec.eurlex_page("02008R1272-20260701"),
                         "https://eur-lex.europa.eu/legal-content/CS/TXT/?uri=CELEX:02008R1272-20260701")
        self.assertEqual(ec.text_address("02008R1272-20260701"),
                         "https://eur-lex.europa.eu/legal-content/CS/TXT/HTML/?uri=CELEX:02008R1272-20260701")

    def test_the_version_in_effect_and_the_prepared_one(self):
        consolidations = ec.consolidations_of(ACT, CACHE)
        self.assertNotIn("02008R1272-20090120", [c["celex"] for c in consolidations])  # = the original text
        self.assertEqual(ec.in_effect(consolidations, "2026-11-20")["celex"], "02008R1272-20260701")
        self.assertEqual(ec.in_effect(consolidations, "2026-12-31")["celex"], "02008R1272-20260701")
        self.assertEqual(ec.in_effect(consolidations, "2027-01-01")["celex"], "02008R1272-20270101")
        self.assertIsNone(ec.in_effect(consolidations, "2026-01-01"))

    def test_fetch_targets_follow_the_day(self):
        self.assertEqual(ec.fetch_targets(CONFIG, CACHE, "2026-11-20"),
                         {"(ES) 1272/2008": ("konsolidace_20260701", ec.text_address("02008R1272-20260701"))})
        self.assertEqual(ec.fetch_targets(CONFIG, CACHE, "2027-01-01")["(ES) 1272/2008"][0], "konsolidace_20270101")

    def test_the_document_shows_the_newest_text_in_effect(self):
        self.assertEqual(ec.displayed_file("(ES) 1272/2008", MANIFEST, "2026-11-20", CONFIG, CACHE), CONSOLIDATED)
        # 01.01.2027 before the new text is downloaded: still the text of 01.07.2026
        self.assertEqual(ec.displayed_file("(ES) 1272/2008", MANIFEST, "2027-01-01", CONFIG, CACHE), CONSOLIDATED)
        self.assertIsNone(ec.displayed_file("(ES) 1907/2006", MANIFEST, "2026-11-20", CONFIG, CACHE))
        self.assertEqual(ec.original_file(MANIFEST, "(ES) 1272/2008"), ORIGINAL_PDF)

    def test_save_cache_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "cache.json"
            ec.save_cache(CACHE, path)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), CACHE)

    def test_the_committed_list_names_clp_and_reach_only(self):
        acts = ec.load_config()
        self.assertEqual(sorted(a["celex"] for a in acts), ["32006R1907", "32008R1272"])
        for act in acts:
            self.assertEqual(act["language"], "CS")
            self.assertTrue(act["original"]["label"].startswith("původní znění"))


class PlanTestCase(unittest.TestCase):
    def test_first_run_makes_the_consolidation_of_july_2026_current(self):
        actions = ec.plan(db_doc([original_row()]), CONFIG, CACHE, MANIFEST, "2026-11-20")
        versions, shown = state_after(actions, [original_row()])
        self.assertEqual([(v["version"], v["edition_label"], v["lifecycle_state"], v["is_current"]) for v in versions], [
            (1, "původní znění (Úř. věst. L 353, 31.12.2008)", "superseded", False),
            (2, "konsolidované znění ke dni 01.05.2026", "superseded", False),
            (3, "konsolidované znění ke dni 01.07.2026", "active", True),
            (4, "konsolidované znění ke dni 01.01.2027", "promulgated", False)])
        self.assertEqual(versions[0]["file_path"], ORIGINAL_PDF)  # the original text is kept
        self.assertEqual(versions[0]["url"], "https://eur-lex.europa.eu/legal-content/CS/TXT/?uri=CELEX:32008R1272")
        self.assertEqual(versions[2]["file_path"], CONSOLIDATED)
        self.assertIsNone(versions[3]["file_path"])
        self.assertEqual(shown, CONSOLIDATED)

    def test_a_second_run_changes_nothing(self):
        actions = ec.plan(db_doc([original_row()]), CONFIG, CACHE, MANIFEST, "2026-11-20")
        versions, shown = state_after(actions, [original_row()])
        rows = [dict(v, id=100 + v["version"]) for v in versions]
        self.assertEqual(ec.plan(db_doc(rows, shown), CONFIG, CACHE, MANIFEST, "2026-11-20"), [])

    def test_on_1_january_2027_the_prepared_version_becomes_current(self):
        versions, shown = state_after(ec.plan(db_doc([original_row()]), CONFIG, CACHE, MANIFEST, "2026-11-20"),
                                      [original_row()])
        rows = [dict(v, id=100 + v["version"]) for v in versions]
        actions = ec.plan(db_doc(rows, shown), CONFIG, CACHE, MANIFEST, "2027-01-01")
        self.assertEqual(sorted((a["version"], sorted(a["changes"])) for a in actions if a["action"] == "update"),
                         [(3, ["is_current", "lifecycle_state"]), (4, ["is_current", "lifecycle_state"])])
        self.assertFalse([a for a in actions if a["action"] == "file"])  # the new text is not downloaded yet
        after, _ = state_after(actions, rows, shown)
        self.assertEqual([(v["version"], v["lifecycle_state"], v["is_current"]) for v in after][2:],
                         [(3, "superseded", False), (4, "active", True)])
        # downloaded: the document shows it
        manifest = dict(MANIFEST, **{"V02_Bibliografie|(ES) 1272/2008|konsolidace_20270101":
                                     {"status": "fetched", "local_path": "data/fulltext/ES_1272_2008__aaaaaaaa.html"}})
        actions = ec.plan(db_doc(after, shown), CONFIG, CACHE, manifest, "2027-01-01")
        self.assertIn({"action": "file", "document_id": 1220, "identifier": "(ES) 1272/2008", "old": CONSOLIDATED,
                       "new": "data/fulltext/ES_1272_2008__aaaaaaaa.html"}, actions)
        # the superseded version keeps its stored text
        self.assertEqual(state_after(actions, after, shown)[0][2]["file_path"], CONSOLIDATED)

    def test_a_new_consolidation_found_later_is_appended(self):
        versions, shown = state_after(ec.plan(db_doc([original_row()]), CONFIG, CACHE, MANIFEST, "2026-11-20"),
                                      [original_row()])
        rows = [dict(v, id=100 + v["version"]) for v in versions]
        cache = json.loads(json.dumps(CACHE))
        cache["32008R1272"]["consolidations"].append({"celex": "02008R1272-20270601", "date": "2027-06-01"})
        actions = ec.plan(db_doc(rows, shown), CONFIG, cache, MANIFEST, "2026-11-20")
        self.assertEqual([(a["action"], a["version"], a["lifecycle_state"]) for a in actions],
                         [("add", 5, "promulgated")])

    def test_a_repealed_act_is_left_alone(self):
        row = dict(original_row(), lifecycle_state="repealed")
        actions = ec.plan(db_doc([row]), CONFIG, CACHE, MANIFEST, "2026-11-20")
        self.assertEqual([a["action"] for a in actions], ["skip"])

    def test_an_act_without_a_cache_entry_or_document_is_skipped(self):
        self.assertEqual(ec.plan(db_doc([original_row()]), CONFIG, {}, MANIFEST, "2026-11-20"), [])
        self.assertEqual(ec.plan({}, CONFIG, CACHE, MANIFEST, "2026-11-20"), [])


class FakeCursor:
    """Records the statements; answers the column check and the document query."""

    def __init__(self, has_url=True, rows=()):
        self.has_url, self.rows, self.executed, self._result = has_url, list(rows), [], []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        if "information_schema.COLUMNS" in sql:
            self._result = [(1 if self.has_url else 0,)]
        elif sql.startswith("SELECT d.id"):
            self._result = self.rows
        elif sql.startswith("ALTER TABLE DocumentVersion ADD COLUMN url"):
            self.has_url = True
            self._result = []
        else:
            self._result = []

    def fetchall(self):
        return self._result


class DatabaseTestCase(unittest.TestCase):
    ROW = (1220, "(ES) 1272/2008", ORIGINAL_PDF, 5001, 1, None, None, None, None, 1, "active")

    def test_apply_adds_the_column_and_the_versions(self):
        cur = FakeCursor(has_url=False, rows=[self.ROW])
        actions = ec.apply(cur, "2026-11-20", config=CONFIG, cache=CACHE, manifest=MANIFEST)
        statements = [sql for sql, _ in cur.executed]
        self.assertTrue(any(s.startswith("ALTER TABLE DocumentVersion ADD COLUMN url") for s in statements))
        self.assertEqual(sum(s.startswith("INSERT INTO DocumentVersion") for s in statements), 3)
        self.assertIn(("UPDATE Document SET file_path = %s WHERE id = %s", (CONSOLIDATED, 1220)), cur.executed)
        self.assertEqual(len(actions), 5)  # original updated, three added, the shown text

    def test_a_dry_run_writes_nothing(self):
        cur = FakeCursor(has_url=False, rows=[self.ROW])
        ec.apply(cur, "2026-11-20", write=False, config=CONFIG, cache=CACHE, manifest=MANIFEST)
        self.assertFalse([s for s, _ in cur.executed if not s.startswith("SELECT")])


class CellarTestCase(unittest.TestCase):
    def response(self, bindings):
        resp = mock.Mock()
        resp.raise_for_status.return_value = None
        resp.json.return_value = {"results": {"bindings": bindings}}
        return resp

    def test_consolidated_versions_are_sorted_by_date_and_checked(self):
        session = mock.Mock(headers={})
        session.get.return_value = self.response([
            {"celex": {"value": "02008R1272-20270101"}, "date": {"value": "2027-01-01"}},
            {"celex": {"value": "02008R1272-20260701"}, "date": {"value": "2026-07-01"}},
            {"celex": {"value": "32008R1272"}, "date": {"value": "2008-12-16"}},  # not a consolidated version
        ])
        found = eurlex.consolidated_versions("32008R1272", "ces", session=session)
        self.assertEqual(found, [{"celex": "02008R1272-20260701", "date": "2026-07-01"},
                                 {"celex": "02008R1272-20270101", "date": "2027-01-01"}])
        query = session.get.call_args.kwargs["params"]["query"]
        self.assertIn('"32008R1272"^^xsd:string', query)
        self.assertIn("/language/CES>", query)

    def test_a_failed_query_is_none_not_an_empty_list(self):
        import requests
        session = mock.Mock(headers={})
        session.get.side_effect = requests.ConnectionError("down")
        self.assertIsNone(eurlex.consolidated_versions("32008R1272", session=session))

    def test_refresh_keeps_the_cache_when_cellar_fails(self):
        cache = json.loads(json.dumps(CACHE))
        messages, failed = ec.refresh(CONFIG, cache, "2026-11-21", query=lambda *a, **k: None)
        self.assertEqual(failed, ["32008R1272"])
        self.assertEqual(cache, CACHE)

    def test_refresh_reports_a_new_version(self):
        cache = json.loads(json.dumps(CACHE))
        found = CACHE["32008R1272"]["consolidations"] + [{"celex": "02008R1272-20270601", "date": "2027-06-01"}]
        messages, failed = ec.refresh(CONFIG, cache, "2026-11-21", query=lambda *a, **k: found)
        self.assertEqual(failed, [])
        self.assertIn("new since the last check: 02008R1272-20270601", messages[0])
        self.assertEqual(cache["32008R1272"]["checked_at"], "2026-11-21")


class FetchTargetsTestCase(unittest.TestCase):
    RECORD = {"zdroj_dat": "V02_Bibliografie", "znacka": "(ES) 1272/2008", "typ_dokumentu": "Nařízení EU",
              "jazyk": "CZ", "odkaz_hlavni": "https://eur-lex.europa.eu/legal-content/CS/TXT/PDF/?uri=CELEX:32008R1272"}

    def test_the_version_in_effect_is_a_target_of_its_own_once(self):
        targets = ec.fetch_targets(CONFIG, CACHE, "2026-11-20")
        found = [(r["znacka"], f, u) for r, f, u in ff.iter_fetch_targets([self.RECORD, dict(self.RECORD)], {}, targets)]
        self.assertEqual([f for _, f, _ in found], ["odkaz_hlavni", "odkaz_hlavni_html", "konsolidace_20260701",
                                                    "odkaz_hlavni", "odkaz_hlavni_html"])
        self.assertEqual(found[2][2], ec.text_address("02008R1272-20260701"))

    def test_missing_texts(self):
        targets = [(self.RECORD, "konsolidace_20260701", ec.text_address("02008R1272-20260701")),
                   (self.RECORD, "odkaz_hlavni", self.RECORD["odkaz_hlavni"])]
        with tempfile.TemporaryDirectory() as tmp:
            missing = rc.missing_texts(targets, {}, repo_root=tmp)
            self.assertEqual([m[3] for m in missing], ["V02_Bibliografie|(ES) 1272/2008|konsolidace_20260701"])
            manifest = {"V02_Bibliografie|(ES) 1272/2008|konsolidace_20260701":
                        {"status": "fetched", "local_path": "data/fulltext/x.html", "url": targets[0][2]}}
            self.assertEqual(len(rc.missing_texts(targets, manifest, repo_root=tmp)), 1)  # no file
            (pathlib.Path(tmp) / "out").mkdir()
            (pathlib.Path(tmp) / "out" / "x.html").write_text("x")
            self.assertEqual(rc.missing_texts(targets, manifest, repo_root=tmp, out_dir=pathlib.Path(tmp) / "out"), [])

    def test_fetch_and_extract_records_the_download_and_extracts_it(self):
        key = "V02_Bibliografie|(ES) 1272/2008|konsolidace_20270101"
        missing = [(self.RECORD, "konsolidace_20270101", ec.text_address("02008R1272-20270101"), key)]
        entry = {"status": "fetched", "local_path": "data/fulltext/ES_1272_2008__aaaaaaaa.html", "celex": "02008R1272-20270101"}
        extract = mock.Mock(return_value=({"extracted: eurlex": 1}, []))
        saved = {}
        with mock.patch.object(ff, "load_manifest", return_value={}), \
                mock.patch.object(ff, "save_manifest", side_effect=saved.update):
            problems = rc.fetch_and_extract(missing, fetch=lambda *a: entry, extract=extract)
        self.assertEqual(problems, [])
        self.assertEqual(saved[key], entry)
        self.assertEqual(extract.call_args.kwargs["only"], [key])

    def test_a_failed_download_keeps_the_manifest(self):
        key = "V02_Bibliografie|(ES) 1272/2008|konsolidace_20270101"
        missing = [(self.RECORD, "konsolidace_20270101", "u", key)]
        extract = mock.Mock()
        with mock.patch.object(ff, "load_manifest", return_value={}), \
                mock.patch.object(ff, "save_manifest") as save:
            problems = rc.fetch_and_extract(missing, fetch=lambda *a: {"status": "failed", "error": "x"},
                                            extract=extract)
        self.assertEqual(len(problems), 1)
        save.assert_not_called()
        extract.assert_not_called()


if __name__ == "__main__":
    unittest.main()
