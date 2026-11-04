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
HIT = "https://opendata.eselpoint.gov.cz/esel-esb/právní-akt-fragment/"
TITLES = {
    "CZ:294/2015": "Vyhláška, kterou se provádějí pravidla provozu na pozemních komunikacích",
    "CZ:311/2006": "Zákon o pohonných hmotách",  # known, not asked
    "CZ:42/2025": "Zákon, kterým se mění zákon č. 201/2012 Sb., o ochraně ovzduší",
    "CZ:10/2022": "Vyhláška, kterou se mění vyhláška č. 361/2007 Sb., o ochraně zdraví při práci",
    "CZ:361/2007": "Nařízení vlády, kterým se stanoví podmínky ochrany zdraví při práci",
    "CZ:316/2023": "Vyhláška o Programu statistických zjišťování na rok 2024",
    "CZ:101/1931": "Vyhláška o počátku platnosti nové přílohy I k Mezinárodní úmluvě o přepravě zboží po železnicích",
    "CZ:52/1929": "Obchodní úmluva mezi republikou Československou a Francií",
    "CZ:586/1992": "Zákon o daních z příjmů",
}
FOUND = {  # act: (version date, paths of the hits under /dokument/)
    "CZ:294/2015": ("2025-07-01", ["prilohy/frag_1", "cast_1/frag_2"]),
    "CZ:311/2006": ("2026-01-01", ["frag_3"]),
    "CZ:42/2025": ("2025-03-01", ["novela/cast_1/bod_5/frag_4"]),
    "CZ:10/2022": ("2022-02-01", ["novela/bod_1/frag_5"]),
    "CZ:361/2007": ("2025-01-01", ["prilohy/frag_6"]),
    "CZ:316/2023": ("2024-01-01", ["prilohy/frag_7"]),
    "CZ:101/1931": ("0000-00-00", ["prilohy/frag_8"]),
    "CZ:52/1929": ("0000-00-00", ["prilohy/frag_9"]),
    "CZ:586/1992": ("2026-01-01", ["cast_2/frag_10"]),
}


def eli(key):
    number, year = key.split(":")[1].split("/")
    return f"{ELI}{year}/{number}"


class EsbirkaTestCase(unittest.TestCase):
    """Acts the database lacks whose last version in effect contains the word, with
    the noise reduced as doc/DATA_SOURCES.md odstavec 8.8 proposes."""

    def route(self, url, params):
        query = params["query"]
        if "bif:contains" in query and "obsahuje-fragment" in query:
            return bindings(*({"owner": f"{eli(k)}/{date}/dokument/{p}", "hit": f"{HIT}{k}{p}"}
                              for k, (date, paths) in FOUND.items() for p in paths))
        if "má-poslední-znění" in query:
            self.asked_last = query
            return bindings(*({"act": eli(k), "last": f"{eli(k)}/{date}"} for k, (date, _) in FOUND.items()
                              if f"<{eli(k)}>" in query))
        if "isLiteral" in query:
            return bindings(*({"s": f"{HIT}{k}{p}", "o": "výskyt slova vodík"}
                              for k, (_, paths) in FOUND.items() for p in paths if f"{HIT}{k}{p}" in query))
        if url.startswith("https://www.zakonyprolidi.cz/cs/"):
            raise AssertionError("titles come from the patched cz_title")
        raise AssertionError(query)

    def run_adapter(self, repealed=()):
        context = {"today": "2026-11-04", "known": {"CZ:311/2006", "CZ:201/2012"},
                   "documents": [(7, "201/2012 Sb.", "Zákon o ochraně ovzduší", None)],
                   "candidate_titles": {"CZ:586/1992": "Zákon o daních z příjmů", "CZ:294/2015": "294/2015 Sb."}}
        fetched = []

        def cz_title(session, key):
            fetched.append(key)
            return TITLES[key]

        def repealing_act(session, key):
            return (["CZ:1/1960"], "1960-01-01") if key in repealed else ([], None)
        with mock.patch.object(ha, "time", NO_SLEEP), mock.patch("candidates.cz_title", cz_title), \
                mock.patch("check_validity.repealing_act", repealing_act):
            findings = ha.esbirka_new(ENTRY, Session(self.route), None, context)
        return {f.key: f for f in findings}, fetched

    def test_the_noise_is_sorted_out(self):
        found, fetched = self.run_adapter(repealed={"CZ:52/1929"})
        self.assertNotIn("CZ:311/2006", found)  # the database has it
        self.assertNotIn("CZ:586/1992", fetched)  # its title came from the queue
        self.assertIn("CZ:294/2015", fetched)  # a placeholder title is looked up
        tier = {k: (f.signal, f.tier) for k, f in found.items()}
        self.assertEqual(tier["CZ:294/2015"], ("new_document", 1))
        self.assertEqual(tier["CZ:361/2007"], ("new_document", 1))
        self.assertEqual(tier["CZ:586/1992"], ("new_document", 2))
        self.assertEqual(tier["CZ:101/1931"], ("new_document", 2))
        self.assertIn("před rokem 1990", found["CZ:101/1931"].extra["note"])
        self.assertEqual(found["CZ:294/2015"].occurrences, 2)
        # an amendment of a document of the database, with the documents it amends
        self.assertEqual(tier["CZ:42/2025"], ("amendment", 1))
        self.assertEqual(found["CZ:42/2025"].extra, {"amends": ["CZ:201/2012"], "amends_ids": [7]})
        # an amendment of another act found goes with that act
        self.assertNotIn("CZ:10/2022", found)
        self.assertEqual(found["CZ:361/2007"].extra["amended_by"][0]["key"], "CZ:10/2022")
        # excluded, with the reason
        self.assertEqual(found["CZ:316/2023"].signal, "excluded")
        self.assertIn("statistických zjišťování", found["CZ:316/2023"].extra["reason"])
        self.assertEqual(found["CZ:52/1929"].signal, "excluded")
        self.assertIn("zrušen k 1960-01-01", found["CZ:52/1929"].extra["reason"])
        self.assertNotIn("2006/311", self.asked_last)

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


class ClassifyActTestCase(unittest.TestCase):
    KNOWN = {"CZ:458/2000", "CZ:353/1999"}

    def classify(self, key, title, paths=("cast_1/frag",), candidates=()):
        return ha.classify_act(key, title, list(paths), self.KNOWN, set(candidates))

    def test_amendments(self):
        by_structure = self.classify("CZ:469/2023", "Zákon, kterým se mění zákon č. 458/2000 Sb., energetický zákon",
                                     ["novela/bod_1"])
        self.assertEqual((by_structure["action"], by_structure["target"]), ("amendment", ["CZ:458/2000"]))
        attach = self.classify("CZ:10/2022", "Vyhláška, kterou se mění vyhláška č. 361/2007 Sb.", ["novela/x"],
                               candidates={"CZ:361/2007"})
        self.assertEqual((attach["action"], attach["target"]), ("attach", "CZ:361/2007"))
        outside = self.classify("CZ:1/2020", "Vyhláška, kterou se mění vyhláška č. 9/2010 Sb.", ["novela/x"])
        self.assertEqual((outside["action"], outside["tier"]), ("candidate", 2))
        self.assertIn("9/2010", outside["reason"])
        mixed = self.classify("CZ:349/2023", "Zákon, kterým se mění některé zákony", ["novela/x"])
        self.assertEqual((mixed["action"], mixed["tier"], mixed["reason"]),
                         ("candidate", 2, "novela, měněný předpis nezjištěn"))
        # a title saying "o změně" is not an amendment when no hit lies in amending points
        own = self.classify("CZ:330/2025", "Zákon o správě informací o stavbě a o změně některých zákonů", ["cast_1/x"])
        self.assertEqual((own["action"], own["tier"]), ("candidate", 1))

    def test_full_texts_deny_patterns_and_tiers(self):
        full = self.classify("CZ:349/2004", "Úplné znění zákona č. 353/1999 Sb., o prevenci závažných havárií")
        self.assertEqual(full["action"], "exclude")
        self.assertIn("353/1999", full["reason"])
        self.assertEqual(self.classify("CZ:86/1998", "Dohoda o volném obchodu mezi ČR a Izraelem")["action"], "exclude")
        self.assertEqual(self.classify("CZ:8/2021", "Katalog odpadů")["tier"], 2)
        self.assertEqual(self.classify("CZ:226/2015", "Vyhláška o vymezení zóny havarijního plánování")["tier"], 1)
        self.assertEqual(self.classify("CZ:361/2007", "Nařízení vlády o ochraně zdraví při práci")["tier"], 1)
        self.assertIsNone(ha.denied("Vyhláška o požadavcích na pohonné hmoty"))


class ExcludedTestCase(unittest.TestCase):
    def test_excluded_findings_go_to_the_not_imported_file_and_keep_their_first_date(self):
        finding = harvest.Finding("esbirka-lod", "excluded", "Program statistických zjišťování", key="CZ:316/2023",
                                  extra={"reason": "vzor názvu: sazebník"})
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "not_imported.json"
            self.assertEqual(harvest.record_excluded([finding], "2026-11-04T10:00:00", path), 1)
            harvest.record_excluded([finding], "2026-11-11T10:00:00", path)
            entry = json.loads(path.read_text())["esbirka-lod"]["CZ:316/2023"]
        self.assertEqual((entry["first_seen"], entry["seen"], entry["reason"]),
                         ("2026-11-04T10:00:00", "2026-11-11T10:00:00", "vzor názvu: sazebník"))
        self.assertEqual(harvest.write_findings(None, [finding], set(), "x")["excluded"], 1)


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
