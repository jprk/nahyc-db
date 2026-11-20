"""The adapters of stage E2 (src/tools/harvest_drafts.py) against recorded answers —
small archives in the shape of the Chamber's open data, a feed, EP API answers; no
network access."""
import io
import json
import pathlib
import sys
import types
import unittest
import zipfile
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))
import harvest_drafts as hd
import harvest_sources as hs
import source_registry as sr

NO_SLEEP = types.SimpleNamespace(sleep=lambda seconds: None)
KNOWN = {"CZ:458/2000", "CZ:311/2006"}
CONTEXT = {"today": "2026-11-04", "known": KNOWN,
           "documents": [(5, "458/2000 Sb.", "Energetický zákon", None), (6, "311/2006 Sb.", "Zákon o pohonných hmotách", None)]}


def tisk(id_tisk, kind, stav, ct, term, title, date="01.11.2025"):
    row = [id_tisk, kind, stav, ct, "0", "", "", term, "", "vláda", title[:40], date, "", "", "", title]
    return "|".join(row + [""] * 9)


def archive(tables):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as z:
        for name, lines in tables.items():
            z.writestr(name, ("\n".join(lines) + "\n").encode("cp1250"))
    return buffer.getvalue()


TISKY = archive({
    "tisky.unl": [
        tisk("100", "1", "61", "10", "174", "Vládní návrh zákona, kterým se mění zákon č. 458/2000 Sb., energetický zákon"),
        tisk("101", "2", "61", "11", "174", "Návrh poslanců na vydání zákona o podpoře vodíkových plnicích stanic"),
        tisk("102", "1", "61", "12", "174", "Vládní návrh zákona o pozemních komunikacích"),
        tisk("103", "1", "61", "13", "174", "Vládní návrh zákona o veterinární péči"),
        tisk("104", "1", "66", "14", "174", "Vládní návrh zákona, kterým se mění zákon č. 311/2006 Sb."),  # concluded
        tisk("105", "1", "61", "15", "173", "Vládní návrh zákona o vodíku", date="01.01.2023"),  # earlier term
        tisk("106", "5", "61", "16", "174", "Zpráva o vodíku"),  # not a bill
    ],
    "stavy.unl": ["61|1|1||||", "66|6|1||||"],
    "typ_stavu.unl": ["1|1. čtení|", "6|KONEC|"],
    "tisk_eklep.unl": ["KORNTEST1|1|2025|1|100|0|"],
})
SBIRKA = archive({"sbirka.unl": ["900|458|2000|1||01.01.2000|1|0|", "901|13|1997|1||01.01.1997|1|0|"],
                  "sb_pre.unl": ["102|0|901|31|1|0|", "100|0|900|31|1|0|"]})
POSLANCI = archive({"organy.unl": ["174||11|PSP10|Poslanecká sněmovna|Chamber|04.10.2025||", "173||11|PSP9|PS|C|||"]})
SENAT = archive({"se_tisk.unl": ["500|1|5|7|15|Energetický zákon|Návrh zákona, kterým se mění zákon č. 458/2000 Sb.",
                                 "501|3|5|8|15|Vodík|Senátní návrh zákona o vodíkových technologiích",
                                 "502|1|5|9|14|Starý|Návrh zákona o vodíku"],
                 "psp2senat.unl": ["100|500|20|"]})


class Response:
    def __init__(self, content=b"", payload=None):
        self.content, self.payload, self.status_code = content, payload, 200

    def json(self):
        return self.payload

    def raise_for_status(self):
        pass


class Session:
    def __init__(self, route):
        self.route, self.headers = route, {}

    def get(self, url, params=None, timeout=None, headers=None):
        return self.route(url)


def chamber(url):
    return Response({"tisky": TISKY, "sbirka": SBIRKA, "poslanci": POSLANCI, "se_tisk": SENAT}[url.split("/")[-1][:-4]])


class TierTestCase(unittest.TestCase):
    def test_tiers(self):
        self.assertEqual(hd.draft_tier("Návrh zákona o něčem", ["CZ:458/2000"], KNOWN), 1)
        self.assertEqual(hd.draft_tier("Návrh zákona o vodíkových technologiích", [], KNOWN), 1)
        self.assertEqual(hd.draft_tier("Návrh zákona o pozemních komunikacích", [], KNOWN), 2)
        self.assertIsNone(hd.draft_tier("Návrh zákona o veterinární péči", [], KNOWN))
        self.assertEqual(hd.amended_in_title("Vyhláška, kterou se mění vyhláška č. 343/2014 Sb., o registraci"),
                         ["CZ:343/2014"])


class ChamberTestCase(unittest.TestCase):
    def test_open_bills_of_the_current_term_with_what_they_amend(self):
        found = {f.key: f for f in hd.psp_bills({"id": "psp"}, Session(chamber), None, CONTEXT)}
        self.assertEqual(sorted(found), ["DRAFT-CZ:eklep:KORNTEST1", "DRAFT-CZ:psp:101", "DRAFT-CZ:psp:102"])
        energy = found["DRAFT-CZ:eklep:KORNTEST1"]
        self.assertEqual((energy.signal, energy.tier, energy.extra["amends_ids"]), ("draft", 1, [5]))
        self.assertEqual(energy.url, "https://www.psp.cz/sqw/historie.sqw?o=10&t=10")
        self.assertIn("stav: 1. čtení", energy.excerpt)
        self.assertIn("mění 458/2000 Sb.", energy.excerpt)
        self.assertEqual(found["DRAFT-CZ:psp:101"].tier, 1)  # hydrogen in the title
        self.assertEqual(found["DRAFT-CZ:psp:102"].tier, 2)  # subject area; amends 13/1997, not in the database
        self.assertEqual(found["DRAFT-CZ:psp:102"].extra, {"amends": ["CZ:13/1997"]})

    def test_a_senate_print_joins_its_chamber_print(self):
        found = {f.key: f for f in hd.senate_bills({"id": "senat"}, Session(chamber), None, CONTEXT)}
        self.assertEqual(sorted(found), ["DRAFT-CZ:eklep:KORNTEST1", "DRAFT-CZ:senat:501"])
        self.assertIn("sněmovní tisk 10", found["DRAFT-CZ:eklep:KORNTEST1"].excerpt)
        self.assertIsNone(found["DRAFT-CZ:senat:501"].url)


FEED = """<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>
<item><title>Vyhláška, kterou se mění vyhláška č. 343/2014 Sb., o registraci vozidel</title>
<link>https://www.odok.cz/portal/veklep/material/KORNA</link><description>Předkladatel: MD</description>
<pubDate>Tue, 27 Oct 2026 15:41:58 +0000</pubDate><guid>KORNA</guid></item>
<item><title>Nařízení vlády o platových poměrech</title><link>x</link><guid>KORNB</guid></item>
<item><title>Návrh zákona, kterým se mění zákon č. 458/2000 Sb.</title><link>y</link><guid>KORNTEST1</guid></item>
</channel></rss>""".encode("utf-8")


class VeklepTestCase(unittest.TestCase):
    def test_relevant_items_with_the_key_shared_with_the_chamber(self):
        entry = {"id": "veklep", "access": {"endpoint": "https://feed.test/"}}
        found = {f.key: f for f in hd.veklep_rss(entry, Session(lambda url: Response(FEED)), None, CONTEXT)}
        self.assertEqual(sorted(found), ["DRAFT-CZ:eklep:KORNA", "DRAFT-CZ:eklep:KORNTEST1"])
        self.assertEqual((found["DRAFT-CZ:eklep:KORNA"].tier, found["DRAFT-CZ:eklep:KORNA"].date), (2, "2026-10-27"))
        self.assertEqual(found["DRAFT-CZ:eklep:KORNTEST1"].extra["amends_ids"], [5])


OEIL = """<?xml version="1.0"?><rss version="2.0"><channel>
<item><title>2025/0400(COD)</title><link>l1</link><description>Hydrogen markets</description></item>
<item><title>2021/0424(COD)</title><link>l2</link><description>Gas and hydrogen markets regulation</description></item>
<item><title>2023/2568(DEA)</title><link>l3</link><description>RFNBO methodology</description></item>
<item><title>2023/2123(INI)</title><link>l4</link><description>European Hydrogen Bank</description></item>
</channel></rss>""".encode("utf-8")
EP = {
    "2025-0400": {"process_title": {"cs": "Změna směrnic o vodíku"}, "consists_of": [{"activity_date": "2026-09-01"}]},
    "2021-0424": {"process_title": {"en": "Gas"}, "consists_of": [
        {"activity_date": "2024-07-15", "had_activity_type": "def/ep-activities/PUBLICATION_OFFICIAL_JOURNAL"}]},
    "2023-2568": {"process_title": {"en": "RFNBO"}, "consists_of": [{"activity_date": "2023-03-01"}]},
}


class OeilTestCase(unittest.TestCase):
    def test_open_legislative_procedures_only(self):
        asked = []

        def route(url):
            if url.startswith("https://oeil"):
                return Response(OEIL)
            asked.append(url)
            return Response(payload={"data": [EP[url.split("/")[-1].split("?")[0]]]})
        entry = {"id": "oeil", "access": {"endpoint": "https://oeil.test/rss"}}
        with mock.patch.object(hd, "time", NO_SLEEP):
            findings = hd.oeil_procedures(entry, Session(route), None, CONTEXT)
        self.assertEqual([(f.key, f.title, f.jurisdikce) for f in findings],
                         [("DRAFT-EU:2025/0400(COD)", "Změna směrnic o vodíku", "EU")])
        self.assertEqual(len(asked), 3)  # the INI report is not asked about
        self.assertTrue(hd.procedure_over("DEA", False, "2023-03-01", "2026-11-04"))
        self.assertFalse(hd.procedure_over("DEA", False, "2026-09-01", "2026-11-04"))
        self.assertFalse(hd.procedure_over("COD", False, "2020-01-01", "2026-11-04"))


class PlanTestCase(unittest.TestCase):
    def test_stage_e2_runs_four_sources_and_defers_slovlex(self):
        entries, _ = sr.load()
        planned = {e["id"]: (specs, reason) for e, specs, reason in hs.plan(sr.select(entries, stage="E2"),
                                                                            hs.ADAPTERS)}
        self.assertEqual(sorted(i for i, (specs, _) in planned.items() if specs),
                         ["ep-oeil", "psp-snemovni-tisky", "senat-tisky", "veklep-odok"])
        self.assertTrue(planned["slovlex-legislativny-proces"][1].startswith("deferred"))


if __name__ == "__main__":
    unittest.main()
