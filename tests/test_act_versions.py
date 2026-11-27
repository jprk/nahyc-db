"""Edition and effect of the versions of Czech and EU acts (issue #38;
src/tools/act_versions.py, refresh_act_versions.py): the baseline version describes
the stored text and keeps an editor's values, versions the source adds after the
document came into the database are added, the one in effect current; texts follow.
No network; the database part runs against fakes."""
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "tools"))
sys.path.insert(0, str(REPO_ROOT / "src"))
import act_versions as av  # noqa: E402
import refresh_act_versions as rav  # noqa: E402

CZ = {"family": "CZ", "key": "CZ:458/2000", "number": 458, "year": 2000}
EU = {"family": "EU", "key": "EU:2018/2001", "celex": "32018L2001", "language": "CS"}
STORED = "data/fulltext/458_2000_Sb.__5896fdec.html"
NEWER = "data/fulltext/458_2000_Sb.__aaaaaaaa.html"
MANIFEST = {
    "Sinay_Zakony|458/2000 Sb.|odkaz_hlavni": {"status": "fetched", "local_path": STORED,
                                                "fetched_at": "2026-09-09T17:34:18"},
}
CZ_FOUND = {"first_effective": "2001-01-01",
            "versions": [{"id": d, "date": d} for d in ("2001-01-01", "2026-08-01", "2026-11-01", "2027-01-01")]}


def cz_cache():
    cache = {}
    av.record_check(cache, "458/2000 Sb.", CZ, CZ_FOUND, "2026-09-09", "2026-09-09")
    return cache


def cz_doc(versions=None, file_path=STORED, effective=""):
    if versions is None:
        versions = [{"id": 72, "version": 1, "edition_label": None, "effective_date": None, "url": None,
                     "file_path": None, "is_current": True, "lifecycle_state": "active"}]
    return {"458/2000 Sb.": {"id": 72, "file_path": file_path, "effective_date": effective, "act": CZ,
                             "versions": versions}}


def applied(documents, actions):
    """The documents after `actions` (what execute() would write)."""
    docs = {k: {**d, "versions": [dict(v) for v in d["versions"]]} for k, d in documents.items()}
    by_id = {d["id"]: d for d in docs.values()}
    next_id = 1000
    for a in actions:
        doc = by_id[a["document_id"]]
        if a["action"] == "add":
            next_id += 1
            doc["versions"].append({"id": next_id, **{k: a[k] for k in ("version", *av._COMPARED)}})
        elif a["action"] == "update":
            version = next(v for v in doc["versions"] if v["id"] == a["version_id"])
            version.update({k: new for k, (_old, new) in a["changes"].items()})
        elif a["action"] == "file":
            doc["file_path"] = a["new"]
        elif a["action"] == "effective":
            doc["effective_date"] = a["new"]
    return docs


class ActOfTestCase(unittest.TestCase):
    def test_czech_act(self):
        self.assertEqual(av.act_of("458/2000 Sb.", "Energetický zákon", "CS", {})["key"], "CZ:458/2000")

    def test_eu_act_needs_its_celex(self):
        validity = {"EU:2018/2001": {"celex": "32018L2001"}}
        act = av.act_of("(EU) 2018/2001 [EN]", "Directive", "EN", validity)
        self.assertEqual((act["celex"], act["language"]), ("32018L2001", "EN"))
        self.assertIsNone(av.act_of("(EU) 2018/2001", "Směrnice", "CS", {}))

    def test_excluded_and_slovak_acts(self):
        self.assertIsNone(av.act_of("(ES) 1272/2008", "CLP", "CS", {"EU:2008/1272": {"celex": "32008R1272"}},
                                    excluded={"(ES) 1272/2008"}))
        self.assertIsNone(av.act_of("24/2006 Z. z.", "Zákon", "SK", {}))


class RecordCheckTestCase(unittest.TestCase):
    def test_first_check_stores_since_and_known(self):
        entry = cz_cache()["458/2000 Sb."]
        self.assertEqual(entry["since"], "2026-09-09")
        self.assertEqual(entry["known"], ["2001-01-01", "2026-08-01"])
        self.assertEqual(av.baseline_date(entry), "2026-08-01")
        self.assertEqual([v["date"] for v in av.later_versions(entry)], ["2026-11-01", "2027-01-01"])

    def test_later_check_keeps_since_and_reports_new(self):
        cache = cz_cache()
        found = {**CZ_FOUND, "versions": CZ_FOUND["versions"] + [{"id": "2027-06-01", "date": "2027-06-01"}]}
        new = av.record_check(cache, "458/2000 Sb.", CZ, found, "2026-12-01", "2026-12-01")
        self.assertEqual(new, ["2027-06-01"])
        self.assertEqual(cache["458/2000 Sb."]["since"], "2026-09-09")
        self.assertEqual(cache["458/2000 Sb."]["known"], ["2001-01-01", "2026-08-01"])

    def test_since_is_the_download_of_the_stored_text(self):
        self.assertEqual(av.since_of(STORED, MANIFEST, "2026-11-27"), "2026-09-09")
        self.assertEqual(av.since_of(None, MANIFEST, "2026-11-27"), "2026-11-27")


class PlanTestCase(unittest.TestCase):
    def test_first_run(self):
        actions = av.plan(cz_doc(), cz_cache(), MANIFEST, "2026-11-27")
        base = next(a for a in actions if a["action"] == "update")
        self.assertEqual(base["changes"]["edition_label"], (None, "znění účinné od 01.08.2026"))
        self.assertEqual(base["changes"]["url"], (None, "https://e-sbirka.gov.cz/sb/2000/458/2026-08-01"))
        self.assertEqual(base["changes"]["file_path"], (None, STORED))
        self.assertEqual(base["changes"]["lifecycle_state"], ("active", "superseded"))
        added = [a for a in actions if a["action"] == "add"]
        self.assertEqual([(a["version"], a["lifecycle_state"], a["is_current"]) for a in added],
                         [(2, "active", True), (3, "promulgated", False)])
        effective = next(a for a in actions if a["action"] == "effective")
        self.assertEqual(effective["new"], "01.01.2001 (účinnost)")
        self.assertFalse([a for a in actions if a["action"] == "file"])  # no newer text yet

    def test_second_run_changes_nothing(self):
        documents = cz_doc()
        once = applied(documents, av.plan(documents, cz_cache(), MANIFEST, "2026-11-27"))
        self.assertEqual(av.plan(once, cz_cache(), MANIFEST, "2026-11-27"), [])

    def test_downloaded_text_is_shown(self):
        manifest = {**MANIFEST, "Sinay_Zakony|458/2000 Sb.|zneni_20261101": {"status": "fetched", "local_path": NEWER}}
        documents = applied(cz_doc(), av.plan(cz_doc(), cz_cache(), MANIFEST, "2026-11-27"))
        actions = av.plan(documents, cz_cache(), manifest, "2026-11-27")
        self.assertIn({"action": "file", "document_id": 72, "identifier": "458/2000 Sb.", "old": STORED, "new": NEWER},
                      actions)
        after = applied(documents, actions)["458/2000 Sb."]
        self.assertEqual({v["version"]: v["file_path"] for v in after["versions"]}, {1: STORED, 2: NEWER, 3: None})

    def test_prepared_version_takes_effect_on_its_day(self):
        documents = applied(cz_doc(), av.plan(cz_doc(), cz_cache(), MANIFEST, "2026-11-27"))
        actions = av.plan(documents, cz_cache(), MANIFEST, "2027-01-01")
        states = {a["version"]: a["changes"].get("lifecycle_state") for a in actions if a["action"] == "update"}
        self.assertEqual(states, {2: ("active", "superseded"), 3: ("promulgated", "active")})

    def test_editor_values_are_kept(self):
        versions = [{"id": 72, "version": 1, "edition_label": "úplné znění 2026", "effective_date": "01.08.2026",
                     "url": None, "file_path": STORED, "is_current": True, "lifecycle_state": "active"}]
        actions = av.plan(cz_doc(versions, effective="01.01.2001"), cz_cache(), MANIFEST, "2026-09-10")
        self.assertEqual([sorted(a["changes"]) for a in actions if a["action"] == "update"], [["url"]])
        self.assertFalse([a for a in actions if a["action"] == "effective"])

    def test_repealed_act_gets_only_its_baseline(self):
        versions = [{"id": 72, "version": 1, "edition_label": None, "effective_date": None, "url": None,
                     "file_path": None, "is_current": True, "lifecycle_state": "repealed"}]
        actions = av.plan(cz_doc(versions), cz_cache(), MANIFEST, "2026-11-27")
        self.assertEqual({a["action"] for a in actions}, {"update", "effective"})
        update = next(a for a in actions if a["action"] == "update")
        self.assertNotIn("lifecycle_state", update["changes"])

    def test_eu_act_baseline_is_the_original(self):
        cache = {}
        found = {"first_effective": "2018-12-24",
                 "versions": [{"id": "02018L2001-20231120", "date": "2023-11-20"},
                              {"id": "02018L2001-20270101", "date": "2027-01-01"}]}
        av.record_check(cache, "(EU) 2018/2001", EU, found, "2026-11-20", "2026-11-20")
        documents = {"(EU) 2018/2001": {"id": 106, "file_path": "data/fulltext/EU_2018_2001__7177d159.pdf",
                                        "effective_date": "Platnost od 12 října 2023", "act": EU,
                                        "versions": cz_doc()["458/2000 Sb."]["versions"]}}
        actions = av.plan(documents, cache, {}, "2026-11-27")
        base = actions[0]["changes"]
        self.assertEqual(base["edition_label"], (None, "původní znění"))
        self.assertEqual(base["effective_date"], (None, "2018-12-24"))
        self.assertEqual(base["url"][1], "https://eur-lex.europa.eu/legal-content/CS/TXT/?uri=CELEX:32018L2001")
        self.assertNotIn("lifecycle_state", base)  # stays current until 01.01.2027
        added = next(a for a in actions if a["action"] == "add")
        self.assertEqual((added["edition_label"], added["lifecycle_state"]),
                         ("konsolidované znění ke dni 01.01.2027", "promulgated"))
        self.assertFalse([a for a in actions if a["action"] == "effective"])  # not empty: kept

    def test_rebuild_keeps_the_stored_text_on_the_baseline(self):
        manifest = {**MANIFEST, "Sinay_Zakony|458/2000 Sb.|zneni_20261101": {"status": "fetched", "local_path": NEWER}}
        actions = av.plan(cz_doc(file_path=NEWER), cz_cache(), manifest, "2026-11-27")
        base = next(a for a in actions if a["action"] == "update" and a["version"] == 1)
        self.assertEqual(base["changes"]["file_path"], (None, STORED))
        self.assertEqual(av.displayed_file("458/2000 Sb.", manifest, "2026-11-27", cz_cache()), NEWER)


class TargetsTestCase(unittest.TestCase):
    def test_version_in_effect_is_downloaded_from_zakonyprolidi(self):
        self.assertEqual(av.fetch_targets(cz_cache(), "2026-11-27"),
                         {"458/2000 Sb.": ("zneni_20261101", "https://www.zakonyprolidi.cz/cs/2000-458")})
        self.assertEqual(av.fetch_targets(cz_cache(), "2026-10-01"), {})

    def test_cache_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "cache.json"
            av.save_cache(cz_cache(), path)
            self.assertEqual(av.load_cache(path), cz_cache())


class SourcesTestCase(unittest.TestCase):
    def test_czech_versions_from_esbirka(self):
        node = "https://opendata.eselpoint.gov.cz/esel-esb/eli/cz/sb/2000/458"
        rows = [{"act": {"value": node}, "from": {"value": d}} for d in ("2001-01-01", "0000-00-00", "2026-08-01",
                                                                          "2001-01-01")]
        with mock.patch.object(rav.time, "sleep"):
            found = rav.czech_versions(None, [("CZ:458/2000", 458, 2000)], sparql=lambda *a, **k: rows)
        self.assertEqual(found["CZ:458/2000"]["first_effective"], "2001-01-01")
        self.assertEqual([v["id"] for v in found["CZ:458/2000"]["versions"]], ["2001-01-01", "2026-08-01"])

    def test_failed_query_leaves_the_act_out(self):
        def fail(*_a, **_k):
            raise rav.requests.ConnectionError("down")
        with mock.patch.object(rav.time, "sleep"):
            self.assertEqual(rav.czech_versions(None, [("CZ:458/2000", 458, 2000)], sparql=fail), {})
            self.assertEqual(rav.eu_entry_into_force(None, ["32018L2001"], sparql=fail), {})

    def test_eu_act_without_answer_is_left_out(self):
        documents = {"(EU) 2018/2001": {"act": EU}}
        with mock.patch.object(rav, "eu_entry_into_force", return_value={"32018L2001": "2018-12-24"}), \
                mock.patch.object(rav, "czech_versions", return_value={}), mock.patch.object(rav.time, "sleep"):
            self.assertEqual(rav.query_sources(documents, None, consolidated=lambda *a, **k: None), {})
            found = rav.query_sources(documents, None, consolidated=lambda *a, **k: [
                {"celex": "02018L2001-20231120", "date": "2023-11-20"}])
        self.assertEqual(found["(EU) 2018/2001"]["versions"], [{"id": "02018L2001-20231120", "date": "2023-11-20"}])


class VerifiedFetchTestCase(unittest.TestCase):
    PAGE = "<div class='Frags'><span>znění 01.11.2026 - 31.12.2026</span> (verze 52)</div>"

    def fetch_page(self, page):
        tmp = tempfile.mkdtemp()
        (pathlib.Path(tmp) / "458_2000_Sb.__x.html").write_text(page, encoding="utf-8")

        def fetch(*_a, **_k):
            return {"status": "fetched", "local_path": "data/fulltext/458_2000_Sb.__x.html", "http_status": 200}
        return lambda field: rav.verified_fetch(None, {}, field, "https://www.zakonyprolidi.cz/cs/2000-458", tmp,
                                                fetch=fetch)

    def test_page_of_the_version_is_kept(self):
        self.assertEqual(rav.stated_version(self.PAGE), "2026-11-01")
        self.assertEqual(self.fetch_page(self.PAGE)("zneni_20261101")["status"], "fetched")

    def test_page_of_another_version_is_a_failure(self):
        entry = self.fetch_page(self.PAGE)("zneni_20270101")
        self.assertEqual(entry["status"], "failed")
        self.assertIn("2026-11-01", entry["error"])
        self.assertEqual(self.fetch_page("<p>bez data</p>")("zneni_20261101")["status"], "failed")

    def test_eu_texts_are_not_checked(self):
        self.assertEqual(self.fetch_page("<p>x</p>")("konsolidace_20270101")["status"], "fetched")


class DisplayTestCase(unittest.TestCase):
    def test_link_label_and_date(self):
        import os
        os.environ.setdefault("SECRET_KEY", "unit-test")
        sys.path.insert(0, str(REPO_ROOT))
        import app.app as webapp
        self.assertEqual(webapp.version_link_label("https://e-sbirka.gov.cz/sb/2001/100/2025-08-01"), "e-Sbírka")
        self.assertEqual(webapp.version_link_label("https://eur-lex.europa.eu/legal-content/CS/TXT/"), "EUR-Lex")
        self.assertEqual(webapp.czech_iso_date("2025-08-01"), "01.08.2025")
        self.assertEqual(webapp.czech_iso_date("Platnost od 12 října 2023"), "Platnost od 12 října 2023")


if __name__ == "__main__":
    unittest.main()
