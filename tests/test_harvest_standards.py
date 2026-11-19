"""The adapters of stage E3 (src/tools/harvest_standards.py) on recorded text — no
network, no real PDF."""
import io
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
import harvest_sources as hs
import harvest_standards as st
import source_registry as sr

NO_SLEEP = types.SimpleNamespace(sleep=lambda seconds: None)

VESTNIK = """OZNÁMENÍ č. 76/26
o vydání ČSN, jejich změn, oprav a zrušení
VYDANÉ ČSN
1. ČSN EN 17124 (69 7281) Vodíkové palivo - Specifikace produktu a zajištění kvality pro čerpací stanice
kat. č. 524365 s výdejem kapalného nebo plynného vodíku; EN 17124:2026; Vydání: Říjen 2026
K datu její účinnosti se zrušuje
ČSN EN 17124 (69 7281) Vodíkové palivo - Specifikace; Vyhlášena: Březen 2023
2. ČSN EN ISO 19870-1 (38 6477) Vodíkové technologie - Metodika pro určování emisí skleníkových plynů
kat. č. 524381 spojených s dodavatelským řetězcem vodíku; Vydání: Říjen 2026
3. ČSN EN 1555-1 ed. 2 (64 3041) Plastové potrubní systémy pro rozvod plynných paliv - Část 1: Všeobecně
kat. č. 524700; Vydání: Říjen 2026
K datu její účinnosti se zrušuje
ČSN EN 1555-1 ed. 1 (64 3041) Plastové potrubní systémy; Vyhlášena: Květen 2011
4. ČSN EN ISO 18490 (01 5004) Nedestruktivní zkoušení - Ověřování zrakové ostrosti; Vydání: Říjen 2026
5. ČSN EN 17931 (05 2101) Zařízení pro plynové svařování - Ruční plynová zařízení; Vydání: Říjen 2026
14
Věstník č. 10/2026
6. ČSN EN 12345 (69 0001) Nová norma, jež nahrazuje normu databáze; Vydání: Říjen 2026
K datu její účinnosti se zrušuje
ČSN 07 8304 (07 8304) Kovové tlakové nádoby; Vyhlášena: Leden 1990
ZRUŠENÉ ČSN
7. ČSN EN 1717 (75 5030) Ochrana proti znečištění pitné vody; Vydání: Září 2001; Zrušena k 2026-11-01
8. ČSN ISO 317 (44 1575) Manganové rudy; Vydání: Prosinec 1992; Zrušena k 2026-11-01
OZNÁMENÍ č. 79/26
NÁVRHY EVROPSKÝCH NOREM PŘEDLOŽENÉ K VEŘEJNÉMU PROJEDNÁNÍ
CEN
Označení Název v angličtině Původce Lhůty
prEN ISO 16708 Oil and gas industries including lower carbon energy - CEN/TC 12 2026-11-17
Pipeline transportation systems (ISO/DIS 16708:2026)
prEN 17124 Hydrogen fuel - Product specification - CEN/TC 268 2026-12-01
EN IEC 60079-11:2024/prA1:2026 Amendment 1 - Explosive atmospheres - Part 11: CLC/TC 31 2026-11-20
prEN IEC 60034-33:2026 Rotating electrical machines - Synchronous hydrogenerators CLC/TC 2 2026-11-20
prEN IEC 62282-2-400 Fuel cell technologies - Part 2-400: Fuel cell modules CLC/SR 105 2026-10-23
OZNÁMENÍ č. 80/26
"""

CONTEXT = {"today": "2026-11-04", "known": {"NORM:EN 17124", "NORM:EN 1555-1", "NORM:EN 1717", "NORM:ČSN 07 8304"},
           "documents": [(1, "ČSN EN 17124", "Vodíkové palivo", None), (2, "ČSN 07 8304", "Tlakové nádoby", None)]}


class KeysAndTermsTestCase(unittest.TestCase):
    def test_designations_and_keys(self):
        self.assertEqual(st.designation("ČSN EN 60204-1 ed. 3 Bezpečnost strojních zařízení"), "ČSN EN 60204-1 ed. 3")
        self.assertEqual(st.designation("FprEN IEC 60086-1:2025/prAA:2026 Primary batteries", "FprEN"),
                         "FprEN IEC 60086-1:2025/prAA:2026")
        self.assertEqual(st.base("prEN IEC 60079-101:2026"), "prEN IEC 60079-101")
        self.assertEqual(harvest.norm_key("ČSN EN 17124"), "NORM:EN 17124")
        self.assertEqual(harvest.norm_key("ČSN  07 8304"), "NORM:ČSN 07 8304")
        self.assertEqual(harvest.norm_key("TPG 304 03"), "NORM:TPG 304 03")
        self.assertIsNone(harvest.norm_key("Vyhláška o něčem"))
        self.assertIn("NORM:SAE J2601", harvest.known_keys([(1, "SAE J2601", "Fueling protocols", None)]))

    def test_hydrogenerators_are_not_hydrogen(self):
        self.assertFalse(harvest.matches("Synchronous hydrogenerators including motor-generators"))
        self.assertTrue(harvest.matches("Hydrogen generators for fuel cells"))

    def test_sae_designations(self):
        self.assertEqual(st.sae_designation("10.4271/j2601_202005"), "SAE J2601")
        self.assertEqual(st.sae_designation("10.4271/ams2401k"), "SAE AMS2401")
        self.assertEqual(st.sae_designation("10.4271/j2601/5_202312"), "SAE J2601/5")


class VestnikTestCase(unittest.TestCase):
    def test_entries(self):
        entries = st.parse_entries(VESTNIK)
        self.assertEqual([e["designation"] for e in entries][:3], ["ČSN EN 17124", "ČSN EN ISO 19870-1", "ČSN EN 1555-1 ed. 2"])
        first = entries[0]
        self.assertEqual((first["klass"], first["catalog"], first["issued"]), ("69 7281", "524365", "Říjen 2026"))
        self.assertTrue(first["title"].startswith("Vodíkové palivo - Specifikace produktu"))
        self.assertEqual(entries[2]["replaced"], ["ČSN EN 1555-1 ed. 1"])
        withdrawn = [e for e in entries if e["section"] == "ZRUŠENÉ ČSN"]
        self.assertEqual([(e["designation"], e["withdrawn"]) for e in withdrawn],
                         [("ČSN EN 1717", "2026-11-01"), ("ČSN ISO 317", "2026-11-01")])

    def test_enquiry(self):
        drafts = st.parse_enquiry(VESTNIK)
        self.assertEqual([d["designation"] for d in drafts],
                         ["prEN ISO 16708", "prEN 17124", "EN IEC 60079-11:2024/prA1:2026", "prEN IEC 60034-33:2026",
                          "prEN IEC 62282-2-400"])
        self.assertEqual(drafts[2]["title"], "Amendment 1 - Explosive atmospheres - Part 11:")
        self.assertEqual((drafts[4]["title"], drafts[4]["committee"]),
                         ("Fuel cell technologies - Part 2-400: Fuel cell modules", "CLC/SR 105"))
        self.assertEqual(drafts[0]["title"], "Oil and gas industries including lower carbon energy - "
                                             "Pipeline transportation systems")
        self.assertEqual((drafts[1]["committee"], drafts[1]["deadline"]), ("CEN/TC 268", "2026-12-01"))

    def test_findings(self):
        findings = st.vestnik_findings({"id": "vestnik-unmz"}, VESTNIK, None, "10/26", CONTEXT)
        by = {(f.signal, f.key): f for f in findings}
        # editions and withdrawals of standards of the database go to the standards cache
        self.assertEqual(by[("state_change", "NORM:EN 17124")].state["status"], "platná")
        self.assertEqual(by[("state_change", "NORM:EN 1555-1")].state["edition"], "Říjen 2026")
        self.assertEqual(by[("state_change", "NORM:EN 1717")].state["status"], "zrušená")
        self.assertEqual(by[("state_change", "NORM:ČSN 07 8304")].state,
                         {"source": "vestnik-unmz", "issue": "10/26", "catalog_number": None, "status": "nahrazená",
                          "replaced_by": "ČSN EN 12345"})
        # new standards by tier; plain NDT is no finding
        self.assertEqual(by[("new_document", "NORM:EN ISO 19870-1")].tier, 1)
        self.assertEqual(by[("new_document", "NORM:EN 17931")].tier, 2)
        self.assertEqual(by[("new_document", "NORM:EN 12345")].tier, 1)  # it replaces a standard of the database
        self.assertNotIn(("new_document", "NORM:EN ISO 18490"), by)
        self.assertNotIn(("state_change", "NORM:ISO 317"), by)
        # drafts: a revision of a standard of the database, an explosion one; hydrogenerators are none
        revision = by[("draft", "DRAFT-NORM:prEN 17124")]
        self.assertEqual((revision.tier, revision.extra["amends_ids"]), (1, [1]))
        self.assertEqual(by[("draft", "DRAFT-NORM:EN IEC 60079-11/prA1")].tier, 2)
        self.assertNotIn(("draft", "DRAFT-NORM:prEN IEC 60034-33"), by)


class FakePage:
    def __init__(self, left_text, header=False):
        self.left_text, self.header, self.height = left_text, header, 800

    def extract_text(self):
        return ("o zahájení zpracování návrhů českých technických norem\nTermíny\n" if self.header else "") + self.left_text

    def extract_words(self):
        return [{"text": "Termíny", "x0": 373}] if self.header else []

    def crop(self, box):
        assert box[2] == 372
        return types.SimpleNamespace(extract_text=lambda: self.left_text)


class TasksTestCase(unittest.TestCase):
    def test_tasks_continue_over_pages_without_the_header(self):
        pdf = types.SimpleNamespace(pages=[
            FakePage("ÚNMZ č. 78/26 o zahájení zpracování návrhů 35"),  # the table of contents
            FakePage("Číslo Název\n33/0033/26 Technologie palivových článků - Část 3-400:\nStabilní napájecí systémy\n"
                     "TNK: 115\nPřejímané mezinárodní dokumenty: EN IEC 62282-3-400:2026 +\nIEC 62282-3-400:2026", header=True),
            FakePage("01/0087/26 Prohlášení o vlivech na životní prostředí\nPřejímané mezinárodní dokumenty: EN ISO 14025:2026\n"
                     "OZNÁMENÍ č. 79/26\n02/0001/26 not a task of this notice"),
        ])
        pdf.pages[0].extract_text = lambda: "o zahájení zpracování návrhů českých technických norem 35"
        tasks = st.parse_tasks(pdf)
        self.assertEqual([t["task"] for t in tasks], ["33/0033/26", "01/0087/26"])
        self.assertEqual(tasks[0]["title"], "Technologie palivových článků - Část 3-400: Stabilní napájecí systémy")
        self.assertEqual(tasks[0]["adopts"], ["EN IEC 62282-3-400:2026", "IEC 62282-3-400:2026"])


class HarmonisedTestCase(unittest.TestCase):
    ROWS = [("Generated on 2 October 2026",), (),
            ("Legislation", "ESO", "Reference and title Provision", "Start of legal effect", "Publication OJ reference",
             "Publication Decision reference", "Publication OJ date", "End of legal effect"),
            ("2014/68/EU - PED", "CEN", "EN 17124:2021\nHydrogen fuel", "01.01.2022", "OJ L", "", "", ""),
            ("2014/68/EU - PED", "CEN", "EN 13445-5:2021\nUnfired pressure vessels", "01.01.2022", "OJ L", "", "", ""),
            ("2014/68/EU - PED", "CEN", "EN 99999:2020\nHydrogen dispensers", "01.01.2021", "OJ L", "", "", "")]

    def test_summary_list_and_findings(self):
        items = st.parse_summary_list(self.ROWS)
        self.assertEqual([(i["designation"], i["title"]) for i in items][:2],
                         [("EN 17124", "Hydrogen fuel"), ("EN 13445-5", "Unfired pressure vessels")])
        buffer = io.BytesIO()
        import openpyxl
        book = openpyxl.Workbook()
        for row in self.ROWS:
            book.active.append(list(row))
        book.save(buffer)

        def route(url, **kwargs):
            if url.endswith("_en"):
                html = '<a href="/document/download/x_en?filename=Summary.xlsx">xlsx</a>' if "pressure-equipment" in url else ""
                return types.SimpleNamespace(text=html, url=url, raise_for_status=lambda: None)
            self.assertTrue(url.startswith("https://single-market-economy.ec.europa.eu/document/download/"))
            return types.SimpleNamespace(content=buffer.getvalue(), raise_for_status=lambda: None)
        session = types.SimpleNamespace(get=lambda url, **kw: route(url, **kw))
        with mock.patch.object(st, "time", NO_SLEEP):
            findings = st.harmonised_standards({"id": "hs"}, session, None, CONTEXT)
        by = {f.key: f for f in findings}
        self.assertEqual(by["NORM:EN 17124"].state["harmonised"][0]["reference"], "EN 17124:2021")
        self.assertEqual((by["NORM:EN 99999"].signal, by["NORM:EN 99999"].tier), ("new_document", 1))
        self.assertNotIn("NORM:EN 13445-5", by)


TPG_HTML = """<table><tr><td>TPG 304 03</td></tr><tr><td>TPG 304 03 Plnicí stanice stlačeného vodíku pro mobilní zařízení</td></tr>
<tr><td>Schváleno dne</td><td>Platnost od</td></tr><tr><td>1. 6. 2022</td><td>1. 7. 2022</td></tr>
<tr><td>TPG 702 01</td></tr><tr><td>Plynovody a přípojky z polyetylenu (nahrazují TPG 702 01 schválená 2018)</td></tr>
<tr><td>Schváleno dne</td><td>Platnost od</td></tr><tr><td>2. 3. 2023</td><td>1. 4. 2023</td></tr></table>"""


class TpgTestCase(unittest.TestCase):
    def test_catalogue(self):
        items = st.parse_tpg(TPG_HTML)
        self.assertEqual([(i["designation"], i["title"], i["approved"], i["valid_from"]) for i in items],
                         [("TPG 304 03", "Plnicí stanice stlačeného vodíku pro mobilní zařízení", "1. 6. 2022", "1. 7. 2022"),
                          ("TPG 702 01", "Plynovody a přípojky z polyetylenu", "2. 3. 2023", "1. 4. 2023")])


class NormCacheTestCase(unittest.TestCase):
    def test_the_standards_cache_merges_what_several_sources_say(self):
        with tempfile.TemporaryDirectory() as tmp:
            norms = pathlib.Path(tmp) / "n.json"
            norms.write_text(json.dumps({"NORM:EN 17124": {"status": "platná", "source": "csnonline"}}))
            finding = harvest.Finding("hs", "state_change", "EN 17124", key="NORM:EN 17124",
                                      state={"source": "ec-harmonised-standards", "harmonised": [{"directive": "PED"}]})
            outcome = harvest.apply_state_changes([finding], "2026-11-04", pathlib.Path(tmp) / "v.json", norms)
            entry = json.loads(norms.read_text())["NORM:EN 17124"]
        self.assertEqual(entry["status"], "platná")
        self.assertEqual(entry["harmonised"], [{"directive": "PED"}])
        self.assertEqual(dict(outcome), {"state_unchanged": 1})


class PlanTestCase(unittest.TestCase):
    def test_stage_e3(self):
        entries, _ = sr.load()
        planned = {e["id"]: (specs, reason) for e, specs, reason in hs.plan(sr.select(entries, stage="E3"), hs.ADAPTERS)}
        self.assertEqual(sorted(i for i, (specs, _) in planned.items() if specs),
                         ["cps-tpg", "ec-harmonised-standards", "sae-standards", "unmz-news", "vestnik-unmz"])
        self.assertEqual(sorted(i for i, (_, r) in planned.items() if r and r.startswith("deferred")),
                         ["asme-codes", "astm-d03", "vestnik-unms-sr"])


if __name__ == "__main__":
    unittest.main()
