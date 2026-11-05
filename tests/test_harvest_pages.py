"""The adapters and lookups of stage E5 (src/tools/harvest_pages.py,
harvest_lookups.py) on recorded pages — no network access."""
import pathlib
import sys
import types
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))
import harvest_lookups as hl
import harvest_pages as hp
import harvest_sources as hs
import source_registry as sr

CONTEXT = {"today": "2026-11-05", "known": set(), "documents": []}


class Response:
    def __init__(self, text="", payload=None, url="https://site.test/page", content=None):
        self.text, self.payload, self.url = text, payload, url
        self.content = content if content is not None else text.encode("utf-8")

    def json(self):
        return self.payload

    def raise_for_status(self):
        pass


class Session:
    def __init__(self, route):
        self.route, self.headers = route, {}

    def get(self, url, params=None, timeout=None):
        return self.route(url, params or {})

    def post(self, url, data=None, timeout=None):
        return self.route(url, data or {})


TICR = """<nav>Aktuality</nav><div>Aktuality: &nbsp; 1.3.2024 - Technická inspekce ČR přijme právníka. &nbsp; &nbsp;
1.11.2026 Nové testové otázky pro obor plynových VTZ, platné od 1.1.2027 jsou k dispozici. &nbsp; &nbsp;
16.3.2026 - Vyjádření k zásahu ze dne 13.2.2026 na pracovišti. &nbsp; &nbsp;
2.2.2026 Metodika pro tlaková zařízení na vodík je k dispozici.</div>"""


class TicrTestCase(unittest.TestCase):
    def test_blocks_start_with_their_date_only(self):
        news = hp.parse_ticr(TICR)
        self.assertEqual([d for d, _ in news], ["2024-03-01", "2026-11-01", "2026-03-16", "2026-02-02"])
        self.assertTrue(news[2][1].startswith("Vyjádření k zásahu ze dne 13.2.2026"))

    def test_findings_with_broader_terms(self):
        entry = {"id": "ticr", "access": {"endpoint": "https://www.ticr.eu/inpage/aktuality-ticr/"}}
        findings = hp.ticr_news(entry, Session(lambda url, p: Response(TICR)), None, CONTEXT)
        self.assertEqual([(f.tier, f.date) for f in findings], [(1, "2026-02-02")])


class CmiAndHzsTestCase(unittest.TestCase):
    def test_measures_on_dispensers_and_hydrogen(self):
        page = """<a href="/files/OOP/0111-OOP-C004-16.pdf">Přístroje na měření tlaku krve</a>
        <a href="/files/OOP/0111-OOP-C045-14.pdf">Výdejní stojany na stlačený zemní plyn</a>
        <a href="/files/OOP/0111-OOP-C110-27.pdf">Výdejní stojany na vodík</a>"""
        entry = {"id": "cmi-oop", "access": {"endpoint": "https://cmi.gov.cz/node/212"}}
        findings = hp.cmi_oop(entry, Session(lambda url, p: Response(page, url="https://cmi.gov.cz/node/212")), None, CONTEXT)
        self.assertEqual([(f.native_id, f.tier) for f in findings], [("0111-OOP-C045-14", 2), ("0111-OOP-C110-27", 1)])
        self.assertEqual(findings[1].url, "https://cmi.gov.cz/files/OOP/0111-OOP-C110-27.pdf")

    def test_hzs_news_with_hydrogen_only(self):
        page = """<a href="/ustecky-kraj/cviceni-u-vodikove-plnici-stanice">Cvičení u vodíkové plnicí stanice</a>
        <a href="/pardubicky-kraj/medaile">Medaile za věrnost</a>"""
        entry = {"id": "hzs-cr", "access": {"endpoint": "https://hzscr.gov.cz/zpravodajstvi"}}
        findings = hp.hzs_news(entry, Session(lambda url, p: Response(page, url="https://hzscr.gov.cz/zpravodajstvi")),
                               None, CONTEXT)
        self.assertEqual([f.url for f in findings], ["https://hzscr.gov.cz/ustecky-kraj/cviceni-u-vodikove-plnici-stanice"])


MD = """<h1>Nákladní doprava</h1><ul><li><a href="/a">Mnohostranné dohody dle 1.5.1 ADR</a> <span>18. 08. 2026</span></li>
<li><a href="/b">Příslušné orgány ADR</a> <span>24. 03. 2026</span></li><li><a href="/c">Dohoda ADR 2025</a> 27. 06. 2025</li></ul>"""


class MdAdrTestCase(unittest.TestCase):
    def test_baseline_then_changed_pages(self):
        self.assertEqual(hp.parse_dated_pages(MD), [("Mnohostranné dohody dle 1.5.1 ADR", "2026-08-18"),
                                                    ("Příslušné orgány ADR", "2026-03-24"),
                                                    ("Dohoda ADR 2025", "2025-06-27")])
        entry = {"id": "md-adr", "url": "https://md.gov.cz/adr"}
        session = Session(lambda url, p: Response(MD, url=url))
        self.assertEqual(hp.md_adr_pages(entry, session, None, CONTEXT), [])
        changed = hp.md_adr_pages(entry, session, "2026-06-01T00:00:00+00:00", CONTEXT)
        self.assertEqual(len(changed), 1)
        self.assertIn("Mnohostranné dohody", changed[0].title)


TRIS = """<table><tr><th>Country</th></tr>
<tr><td>Netherlands</td><td>2026/0576/NL</td><td>Title: Subsidy scheme for renewable hydrogen</td><td>27-10-2026</td>
<td>28-10-2026</td><td><a href="/en/notification/29781">x</a></td></tr>
<tr><td>Czechia</td><td>2026/0300/CZ</td><td>Decree on hydrogen refuelling stations</td><td>01-06-2026</td><td>02-09-2026</td>
<td><a href="/en/notification/27000">x</a></td></tr>
<tr><td>Germany</td><td>2024/0100/DE</td><td>Old hydrogen act</td><td>01-02-2024</td><td>02-05-2024</td></tr></table>"""


class TrisAndHysTestCase(unittest.TestCase):
    def test_tris_results(self):
        items = hp.parse_tris(TRIS)
        self.assertEqual([i["reference"] for i in items], ["2026/0576/NL", "2026/0300/CZ", "2024/0100/DE"])
        findings = hp.tris_notifications({"id": "tris"}, Session(lambda url, d: Response(TRIS)), None, CONTEXT)
        self.assertEqual([(f.key, f.tier) for f in findings], [("DRAFT-TRIS:2026/0576/NL", 2), ("DRAFT-TRIS:2026/0300/CZ", 1)])
        self.assertEqual(findings[1].url, "https://technical-regulation-information-system.ec.europa.eu/en/notification/27000")

    def test_hys_initiatives_not_yet_adopted(self):
        pages = [{"initiativeResultDtoPage": {"totalPages": 2, "content": [
            {"id": 19592.0, "initiativeStatus": "ACTIVE", "reference": "Ares(2026)1", "foreseenActType": "REG_DEL",
             "shortTitle": "Revision of the RFNBO criteria", "currentStatuses": [
                 {"frontEndStage": "INIT_PLANNED", "receivingFeedbackStatus": "DISABLED"}]},
            {"id": 12766.0, "initiativeStatus": "ACTIVE", "shortTitle": "Revision of EU rules on Gas",
             "currentStatuses": [{"frontEndStage": "ADOPTION_WORKFLOW"}]}]}},
            {"initiativeResultDtoPage": {"totalPages": 2, "content": [
                {"id": 1.0, "initiativeStatus": "CLOSED", "shortTitle": "Old", "currentStatuses": []}]}}]
        asked = []

        def route(url, params):
            asked.append(params["page"])
            return Response(payload=pages[params["page"]])
        with mock.patch.object(hp, "time", types.SimpleNamespace(sleep=lambda s: None)):
            findings = hp.hys_initiatives({"id": "hys"}, Session(route), None, CONTEXT)
        self.assertEqual(asked, [0, 1])
        self.assertEqual([(f.key, f.signal, f.tier) for f in findings], [("DRAFT-EU:hys:19592", "draft", 1)])
        self.assertIn("REG_DEL", findings[0].excerpt)


class LookupsTestCase(unittest.TestCase):
    def test_sbirka_and_gesetze(self):
        page = """<table><tr><th>Publikující</th></tr><tr><td>Obec Lhotky IČO: 00508977</td><td>1/2026</td>
        <td>Obecně závazná vyhláška</td><td>Požární řád obce</td><td>08.10.2026</td><td>23.10.2026</td><td>Platné</td>
        <td><a href="/detail/123">detail</a></td></tr></table>"""
        found = hl.sbirka_pp_usc(Session(lambda url, p: Response(page, url="https://sbirkapp.gov.cz/x")), "požár")
        self.assertEqual(found[0]["title"], "Obecně závazná vyhláška 1/2026: Požární řád obce")
        self.assertEqual(found[0]["url"], "https://sbirkapp.gov.cz/detail/123")
        toc = """<?xml version="1.0"?><items><item><title>Gesetz zur Beschleunigung von Wasserstoff</title>
        <link>http://www.gesetze-im-internet.de/wasserstoffbg/xml.zip</link></item>
        <item><title>Bundeswaldgesetz</title><link>http://x/bwaldg/xml.zip</link></item></items>"""
        found = hl.gesetze(Session(lambda url, p: Response(content=toc.encode("utf-8"))), "wasserstoff")
        self.assertEqual([(f["title"], f["url"]) for f in found],
                         [("Gesetz zur Beschleunigung von Wasserstoff", "http://www.gesetze-im-internet.de/wasserstoffbg/")])

    def test_the_lookup_command(self):
        out = []
        self.assertEqual(hs.lookup("no-such", "x", out=out.append), 2)
        session = Session(lambda url, p: Response(payload={"items": [{"substanceIndex": {
            "rmlId": "100.1", "rmlName": "Hydrogen", "rmlEc": "215-605-7", "rmlCas": "1333-74-0"}}]}))
        self.assertEqual(hs.lookup("echa-chem", "hydrogen", session=session, out=out.append), 0)
        self.assertIn("Hydrogen — EC 215-605-7, CAS 1333-74-0", out[1])


class PlanTestCase(unittest.TestCase):
    def test_stage_e5(self):
        entries, _ = sr.load()
        planned = {e["id"]: (specs, reason) for e, specs, reason in hs.plan(sr.select(entries, stage="E5"), hs.ADAPTERS)}
        self.assertEqual(sorted(i for i, (specs, _) in planned.items() if specs),
                         ["cmi-oop", "ec-have-your-say", "hzs-cr", "md-adr", "ticr"])
        self.assertTrue(planned["nfpa-2"][1].startswith("deferred"))
        self.assertNotIn("ec-tris", planned)  # prohibited since 2026-11-05
        self.assertEqual(sorted(hl.LOOKUPS), ["data-europa-search", "echa-chem", "gesetze-im-internet", "is-eia",
                                              "sbirka-pp-usc"])


if __name__ == "__main__":
    unittest.main()
