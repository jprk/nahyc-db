"""The adapters of stage E1 (src/tools/harvest_adapters.py) against recorded
answers of their sources — no network access."""
import json
import pathlib
import sys
import tempfile
import types
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))
import harvest
import harvest_adapters as ha
import harvest_sources as hs
import source_registry as sr

ENTRY = {"id": "test-source"}
NO_SLEEP = types.SimpleNamespace(sleep=lambda seconds: None)


class Response:
    def __init__(self, payload=None, text="", status=200):
        self.payload, self.text, self.status_code, self.ok = payload, text, status, status < 400

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


class Session:
    """Answers GETs with `route(url, params)`."""

    def __init__(self, route):
        self.route, self.headers, self.calls = route, {}, []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params))
        return self.route(url, params or {})


def bindings(*rows):
    return Response({"results": {"bindings": [{k: {"value": v, "type": "literal"} for k, v in row.items()}
                                              for row in rows]}})


class EurlexTestCase(unittest.TestCase):
    def test_binding_on_topic_acts_with_their_keys(self):
        def route(url, params):
            if "'hydrogen'" in params["query"]:
                return bindings({"celex": "32024R1789", "title": "Regulation on hydrogen markets"},
                                {"celex": "32024R1789", "title": "duplicate"},
                                {"celex": "32013R0123", "title": "approving hydrogen peroxide as a biocide"},
                                {"celex": "52022DC0230", "title": "Communication: hydrogen strategy"})
            return bindings({"celex": "32023R1184", "title": "Delegated regulation on RFNBO methodology"})
        with mock.patch.object(ha, "time", NO_SLEEP), mock.patch("screen_eurlex.time", NO_SLEEP):
            findings = ha.eurlex_new(ENTRY, Session(route), None, {})
        self.assertEqual([(f.key, f.designation, f.document_type) for f in findings],
                         [("EU:2024/1789", "(EU) 2024/1789", "Nařízení EU"),
                          ("EU:2023/1184", "(EU) 2023/1184", "Nařízení EU")])
        self.assertTrue(findings[0].url.endswith("CELEX:32024R1789"))
        self.assertTrue(all(f.signal == "new_document" and f.jurisdikce == "EU" for f in findings))

    def test_a_truncated_answer_is_an_error(self):
        many = [{"celex": f"32020R{n:04d}", "title": "hydrogen"} for n in range(1000)]
        with mock.patch.object(ha, "time", NO_SLEEP), self.assertRaises(RuntimeError):
            ha.eurlex_new(ENTRY, Session(lambda url, params: bindings(*many)), None, {})


ELI = "https://opendata.eselpoint.gov.cz/esel-esb/eli/cz/sb/"
FRAGMENT = "https://opendata.eselpoint.gov.cz/esel-esb/právní-akt-fragment/1"
FILE = "https://opendata.eselpoint.gov.cz/esel-esb/právní-akt-binární-soubor/2"
OLD_FRAGMENT = "https://opendata.eselpoint.gov.cz/esel-esb/právní-akt-fragment/3"
ENDED_FRAGMENT = "https://opendata.eselpoint.gov.cz/esel-esb/právní-akt-fragment/4"
KNOWN_FRAGMENT = "https://opendata.eselpoint.gov.cz/esel-esb/právní-akt-fragment/5"
METADATA = "https://opendata.eselpoint.gov.cz/esel-esb/právní-akt-metadata/6"


class EsbirkaTestCase(unittest.TestCase):
    """Acts are found by the hits in their text and kept when the database lacks
    them, their last version contains the word and it is still in effect."""

    def route(self, url, params):
        query = params["query"]
        if "bif:contains" in query and "obsahuje-fragment" in query:
            return bindings({"owner": ELI + "2015/294/2025-07-01/dokument/prilohy/frag_1", "hit": FRAGMENT},
                            {"owner": ELI + "2015/294/2025-07-01/dokument/frag_2", "hit": FILE},
                            {"owner": ELI + "2006/311/2020-01-01/dokument/frag_3", "hit": OLD_FRAGMENT},
                            {"owner": ELI + "1999/1/2005-01-01/dokument/frag_4", "hit": ENDED_FRAGMENT},
                            {"owner": ELI + "2000/458/2028-01-01/dokument/frag_5", "hit": KNOWN_FRAGMENT})
        if "má-poslední-znění" in query:
            self.asked_last = query
            return bindings({"act": ELI + "2015/294", "last": ELI + "2015/294/2025-07-01"},
                            {"act": ELI + "2006/311", "last": ELI + "2006/311/2024-01-01"},
                            {"act": ELI + "1999/1", "last": ELI + "1999/1/2005-01-01", "to": "2010-12-31"})
        if "citace-názvu" in query:
            return bindings({"s": METADATA, "title": "vyhláška o plnicích stanicích vodíku"},
                            {"s": METADATA + "x", "title": "zrušená vyhláška o vodíku", "repealed": "2001-01-01"})
        if "isLiteral" in query:
            return bindings({"s": FRAGMENT, "o": "Tabulka"}, {"s": FRAGMENT, "o": "<td>409 - Čerpací stanice vodíku</td>"})
        raise AssertionError(query)

    def test_acts_in_effect_whose_last_version_has_the_word(self):
        context = {"today": "2026-11-04", "known": {"CZ:458/2000"}}
        with mock.patch.object(ha, "time", NO_SLEEP):
            findings = ha.esbirka_new(ENTRY, Session(self.route), None, context)
        keyed = [(f.key, f.designation, f.url) for f in findings if f.key]
        self.assertEqual(keyed, [("CZ:294/2015", "294/2015 Sb.", "https://www.zakonyprolidi.cz/cs/2015-294")])
        self.assertIn("409 - Čerpací stanice vodíku", findings[0].excerpt)
        self.assertIn("2 míst v textu", findings[0].excerpt)
        self.assertNotIn("2000/458", self.asked_last)
        titled = [f for f in findings if not f.key]
        self.assertEqual([(f.title, f.url) for f in titled], [("vyhláška o plnicích stanicích vodíku", METADATA)])
        self.assertTrue(titled[0].as_evidence("x")["needs_key"])

    def test_act_keys_and_versions(self):
        node = ELI + "1925/262/0000-00-00/dokument/prilohy/priloha_0:2/frag_27667"
        self.assertEqual(ha.act_key(node), "CZ:262/1925")
        self.assertEqual(ha.version_of(node), ELI + "1925/262/0000-00-00")
        self.assertIsNone(ha.act_key("https://x/právní-akt-metadata/4"))

    def test_a_truncated_or_empty_answer_is_an_error(self):
        with mock.patch.object(ha, "time", NO_SLEEP), mock.patch.object(ha, "ESBIRKA_LIMIT", 2), \
                self.assertRaises(RuntimeError):
            ha.esbirka_new(ENTRY, Session(self.route), None, {"today": "2026-11-04", "known": set()})
        with mock.patch.object(ha, "time", NO_SLEEP), self.assertRaises(RuntimeError):
            ha.esbirka_new(ENTRY, Session(lambda url, params: bindings()), None, {"today": "x", "known": set()})


class ValidityTestCase(unittest.TestCase):
    def test_only_stale_acts_of_the_database_are_checked_and_states_go_to_the_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = pathlib.Path(tmp) / "validity.json"
            norms = pathlib.Path(tmp) / "norms.json"
            cache.write_text(json.dumps({"EU:2019/943": {"status": "účinný", "checked_at": "2026-10-20"},
                                         "EU:2003/87": {"status": "účinný", "checked_at": "2026-01-01"}}))
            context = {"today": "2026-11-04", "documents": [
                (1, "(EU) 2019/943", "Nařízení (EU) 2019/943", None), (2, "2003/87/ES", "Směrnice 2003/87/ES", None),
                (3, "(EU) 2024/1789", "Nařízení (EU) 2024/1789", None), (4, "458/2000 Sb.", "Zákon", None)]}
            asked = []

            def eu_status(session, keys_with_kinds, today):
                asked.extend(k for k, _ in keys_with_kinds)
                return {"EU:2003/87": {"status": "zrušený", "source": "cellar", "repealed_by": []},
                        "EU:2024/1789": {"status": "účinný", "source": "cellar", "repealed_by": []}}
            with mock.patch.object(harvest, "VALIDITY_CACHE_PATH", cache), \
                    mock.patch("check_validity.eu_status", eu_status):
                findings = ha.validity_eu(ENTRY, None, None, context)
            self.assertEqual(sorted(asked), ["EU:2003/87", "EU:2024/1789"])
            self.assertEqual([(f.signal, f.key, f.state["status"]) for f in findings],
                             [("state_change", "EU:2003/87", "zrušený"), ("state_change", "EU:2024/1789", "účinný")])
            outcome = harvest.apply_state_changes(findings, "2026-11-04", cache, norms)
            self.assertEqual(dict(outcome), {"state_changed": 2})
            written = json.loads(cache.read_text())
            self.assertEqual(written["EU:2003/87"], {"status": "zrušený", "source": "cellar", "repealed_by": [],
                                                     "checked_at": "2026-11-04"})
            self.assertIn("EU:2019/943", written)
            self.assertFalse(norms.exists())


class StandardsTestCase(unittest.TestCase):
    def test_csn_states_of_the_standards_of_the_database(self):
        results = {"EN 17124": [{"designation": "ČSN EN 17124", "title": "Vodík jako palivo", "issued": "7.2022",
                                 "withdrawn": "", "is_valid": True, "catalog_number": "515125"}],
                   "EN 1": [{"designation": "ČSN EN 1", "title": "Stará", "issued": "1.2000",
                             "withdrawn": "5.2020", "is_valid": False, "catalog_number": "1"}]}
        context = {"today": "2026-11-04", "documents": [(1, "ČSN EN 17124", "x", None), (2, "ČSN EN 1", "y", None),
                                                        (3, "ČSN EN 2", "z", None), (4, "STN EN 3", "w", None)]}
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(harvest, "NORM_CACHE_PATH", pathlib.Path(tmp) / "n.json"), \
                mock.patch.object(ha, "time", NO_SLEEP), \
                mock.patch("check_csn_validity.search", lambda session, query: results.get(query, [])):
            findings = ha.csn_state(ENTRY, None, None, context)
        self.assertEqual([(f.key, f.state["status"]) for f in findings],
                         [("NORM:ČSN EN 1", "zrušená"), ("NORM:ČSN EN 17124", "platná"), ("NORM:ČSN EN 2", "nezjištěno")])


class HytepTestCase(unittest.TestCase):
    PAGE = """<a href="https://www.hytep.cz/a.pdf">zobrazit</a>
              <a data-link-type="url" href="https://www.hytep.cz/a.pdf">Metodika plnicích stanic</a>
              <a data-link-type="url" href="https://www.hytep.cz/Vodikova-strategie-CR-2024.pdf">Strategie</a>"""

    def test_documents_of_the_lists_without_the_strategy_mirrors(self):
        with mock.patch.object(ha, "time", NO_SLEEP):
            findings = ha.hytep_new(ENTRY, Session(lambda url, params: Response(text=self.PAGE)), None, {})
        self.assertEqual({(f.title, f.url, f.document_type) for f in findings},
                         {("Metodika plnicích stanic", "https://www.hytep.cz/a.pdf", "Metodika")})
        self.assertIsNone(findings[0].key)
        known = harvest.known_keys([(1, None, "Metodika", "https://www.hytep.cz/a.pdf")])
        self.assertTrue(hs.is_known(findings[0], known))


class RunnerPlanTestCase(unittest.TestCase):
    def test_stage_e1_runs_five_sources_and_reports_the_deferred_ones(self):
        entries, _ = sr.load()
        planned = {e["id"]: (specs, reason) for e, specs, reason in hs.plan(sr.select(entries, stage="E1"),
                                                                            hs.ADAPTERS)}
        run = sorted(i for i, (specs, _) in planned.items() if specs)
        self.assertEqual(run, ["csn-online", "esbirka-lod", "eurlex-cellar", "hytep", "normoff-stn"])
        deferred = sorted(i for i, (_, reason) in planned.items() if reason and reason.startswith("deferred"))
        self.assertEqual(deferred, sorted(hs.DEFERRED))
        self.assertEqual(len(planned["eurlex-cellar"][0]), 2)

    def test_every_adapter_and_deferred_source_is_in_the_registry(self):
        entries, _ = sr.load()
        ids = {e["id"] for e in entries}
        self.assertLessEqual(set(hs.ADAPTERS) | set(hs.DEFERRED), ids)
        for specs in hs.ADAPTERS.values():
            for spec in specs:
                self.assertTrue(callable(hs.resolve(spec)), spec)

    def test_a_state_change_run_writes_the_cache_and_not_the_queue(self):
        finding = harvest.Finding("x", "state_change", "EU:2003/87", key="EU:2003/87", state={"status": "zrušený"})
        sys.modules["fake_state_adapters"] = types.SimpleNamespace(run=lambda e, s, since, c: [finding])
        entries, _ = sr.load()
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            records = hs.run(sr.select(entries, ["eurlex-cellar"]), {"eurlex-cellar": ("fake_state_adapters:run",)},
                             apply=True, connection=object(), log_path=tmp / "log.jsonl", out=lambda line: None,
                             context={"documents": [], "known": set(), "today": "2026-11-04"},
                             validity_path=tmp / "v.json", norm_path=tmp / "n.json")
            self.assertEqual(records[0]["outcome"], {"state_changed": 1})
            self.assertEqual(json.loads((tmp / "v.json").read_text())["EU:2003/87"]["status"], "zrušený")


if __name__ == "__main__":
    unittest.main()
