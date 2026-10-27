import csv
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))
import check_validity as cv

TODAY = "2026-10-27"


def setUpModule():  # the polite pauses between queries are not part of what is tested
    global _no_sleep
    _no_sleep = mock.patch.object(cv.time, "sleep")
    _no_sleep.start()


def tearDownModule():
    _no_sleep.stop()


class FakeSession:
    """Answers Cellar/e-Sbírka queries with prepared rows, zakonyprolidi.cz with a page."""
    def __init__(self, rows=None, page=""):
        self.rows, self.page, self.queries, self.headers = rows or [], page, [], {}

    def get(self, url, params=None, timeout=None):
        self.queries.append((url, params))
        session = self

        class Response:
            ok = True
            text = session.page

            def raise_for_status(self):
                pass

            def json(self):
                return {"results": {"bindings": session.rows}}
        return Response()


def literal(value):
    return {"value": value}


class CelexTestCase(unittest.TestCase):
    def test_a_known_kind_gives_one_celex_and_an_unknown_one_all_three(self):
        self.assertEqual(cv.celex_candidates("EU:1994/9", "directive"), ["31994L0009"])
        self.assertEqual(cv.celex_candidates("EU:2019/943"), ["32019R0943", "32019L0943", "32019D0943"])
        self.assertEqual(cv.key_of_celex("32014L0034"), "EU:2014/34")
        self.assertIsNone(cv.key_of_celex("52020DC0301"))

    def test_the_kind_of_a_database_act_comes_from_its_title(self):
        self.assertEqual(cv.kind_from_title("Směrnice Evropského parlamentu a Rady 2014/34/EU"), "directive")
        self.assertEqual(cv.kind_from_title("Prováděcí nařízení Komise (EU) 2019/250"), "regulation")
        self.assertIsNone(cv.kind_from_title("Vodíková strategie"))


class EuStatusTestCase(unittest.TestCase):
    def test_an_act_no_longer_in_force_with_the_act_that_repealed_it(self):
        session = FakeSession([{"celex": literal("31994L0009"), "inforce": literal("0"), "end": literal("2016-04-20"),
                                "repealer": literal("32014L0034")}])
        result = cv.eu_status(session, [("EU:1994/9", "directive")], TODAY)
        self.assertEqual(result["EU:1994/9"]["status"], cv.ENDED)
        self.assertEqual(result["EU:1994/9"]["repealed_by"], ["EU:2014/34"])

    def test_an_act_in_force(self):
        session = FakeSession([{"celex": literal("32019R0943"), "inforce": literal("1"), "end": literal("9999-12-31")}])
        self.assertEqual(cv.eu_status(session, [("EU:2019/943", None)], TODAY)["EU:2019/943"]["status"], cv.IN_FORCE)

    def test_several_acts_of_one_number_are_not_guessed_between(self):
        session = FakeSession([{"celex": literal("32014R0034"), "inforce": literal("1")},
                               {"celex": literal("32014L0034"), "inforce": literal("1")}])
        entry = cv.eu_status(session, [("EU:2014/34", None)], TODAY)["EU:2014/34"]
        self.assertEqual(entry["status"], cv.UNKNOWN)
        self.assertIn("several acts", entry["note"])


class CzStatusTestCase(unittest.TestCase):
    ACT = "https://opendata.eselpoint.gov.cz/esel-esb/eli/cz/sb/2001/185"

    def test_an_ended_act_gets_its_repealing_act_from_zakonyprolidi(self):
        session = FakeSession([{"act": literal(self.ACT), "to": literal("2020-12-31"), "from": literal("2001-06-14")}],
                              page='<td class="td0">Zrušeno k 01.01.2021 ( <a>541/2020 Sb.</a> )</td>')
        entry = cv.cz_status(session, ["CZ:185/2001"], TODAY)["CZ:185/2001"]
        self.assertEqual((entry["status"], entry["repealed_by"], entry["repealed_on"]),
                         (cv.ENDED, ["CZ:541/2020"], "2021-01-01"))

    def test_an_act_without_end_is_in_force_and_one_starting_later_is_not_yet(self):
        session = FakeSession([{"act": literal(self.ACT), "from": literal("2001-06-14")}])
        self.assertEqual(cv.cz_status(session, ["CZ:185/2001"], TODAY)["CZ:185/2001"]["status"], cv.IN_FORCE)
        session = FakeSession([{"act": literal(self.ACT), "from": literal("2027-01-01")}])
        self.assertEqual(cv.cz_status(session, ["CZ:185/2001"], TODAY)["CZ:185/2001"]["status"], cv.NOT_YET)

    def test_an_act_missing_from_the_open_data_is_unknown(self):
        self.assertEqual(cv.cz_status(FakeSession([]), ["CZ:1/1900"], TODAY)["CZ:1/1900"]["status"], cv.UNKNOWN)


class CacheAndSheetTestCase(unittest.TestCase):
    def test_entries_older_than_the_limit_are_checked_again(self):
        self.assertTrue(cv.stale({}, 30, TODAY))
        self.assertFalse(cv.stale({"checked_at": "2026-10-20"}, 30, TODAY))
        self.assertTrue(cv.stale({"checked_at": "2026-09-01"}, 30, TODAY))

    def test_the_candidates_sheet_gets_the_status_columns_before_the_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "c.csv"
            with open(path, "w", encoding="utf-8", newline="") as f:
                csv.writer(f).writerows([["family", "designation", "kind", "cited_by", "amendment_share", "context",
                                          "citing_ids", "rozhodnuti"],
                                         ["EU", "1994/9", "directive", "18", "0.0", "ATEX", "1 2", "mimo"]])
            cache = {"EU:1994/9": {"status": cv.ENDED, "end": "2016-04-20", "repealed_by": ["EU:2014/34"]}}
            self.assertEqual(cv.update_candidates(cache, path), 1)
            rows = list(csv.DictReader(path.open(encoding="utf-8")))
        self.assertEqual(list(rows[0])[-4:], ["platnost", "konec", "zruseno_predpisem", "rozhodnuti"])
        self.assertEqual((rows[0]["platnost"], rows[0]["zruseno_predpisem"], rows[0]["rozhodnuti"]),
                         (cv.ENDED, "EU:2014/34", "mimo"))


if __name__ == "__main__":
    unittest.main()
