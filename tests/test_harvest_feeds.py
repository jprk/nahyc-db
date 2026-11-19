"""The adapters of stage E4 (src/tools/harvest_feeds.py, harvest_standards.rss_items,
harvest_drafts.parse_rss) on recorded answers — no network access."""
import json
import pathlib
import sys
import types
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))
import harvest_drafts as hd
import harvest_feeds as hf
import harvest_sources as hs
import harvest_standards as st
import source_registry as sr

ACER = """<?xml version="1.0" encoding="utf-8"?><rss version="2.0"><channel>
<item><title><a href="/news/hydrogen-network-monitoring" hreflang="en">ACER report on hydrogen network development</a></title>
<link>https://www.acer.europa.eu/%3Ca%20href%3D%22/news/hydrogen-network-monitoring%22%20hreflang%3D%22en%22%3EACER%3C/a%3E</link>
<description>The monitoring report covers hydrogen networks.</description><pubDate>Wed, 11/04/2026 - 07:38</pubDate>
<guid>https://www.acer.europa.eu/%3Ca%20href%3D%22/news/hydrogen-network-monitoring%22%20hreflang%3D%22en%22%3EACER%3C/a%3E</guid></item>
<item><title>Electricity market integration</title><link>https://www.acer.europa.eu/news/x</link>
<description>Cross-zonal capacity.</description><pubDate>Tue, 03 Nov 2026 10:00:00 +0000</pubDate><guid>g2</guid></item>
<item><title>Dangerous goods by rail: final decisions for RID 2027</title><link>https://otif.org/en/?p=1</link>
<description>The RID Committee of Experts met.</description><guid>g3</guid></item>
</channel></rss>""".encode("utf-8")


class Response:
    def __init__(self, content=b"", payload=None, headers=None):
        self.content, self.payload, self.headers = content, payload, headers or {}

    def json(self):
        return self.payload

    def raise_for_status(self):
        pass


class Session:
    def __init__(self, response):
        self.response, self.asked = response, []

    def get(self, url, timeout=None):
        self.asked.append(url)
        return self.response


CONTEXT = {"today": "2026-11-05", "known": set(), "documents": []}


class ParseRssTestCase(unittest.TestCase):
    def test_acer_titles_links_and_dates(self):
        items = hd.parse_rss(ACER)
        self.assertEqual(items[0]["title"], "ACER report on hydrogen network development")
        self.assertEqual(items[0]["link"], "https://www.acer.europa.eu/news/hydrogen-network-monitoring")
        self.assertEqual((items[0]["date"], items[1]["date"]), ("2026-11-04", "2026-11-03"))
        self.assertEqual(items[1]["link"], "https://www.acer.europa.eu/news/x")
        self.assertEqual(items[0]["guid"], items[0]["link"])  # the candidate key must not carry the anchor
        self.assertEqual(items[1]["guid"], "g2")


class RssItemsTestCase(unittest.TestCase):
    def test_basic_terms_by_default_broader_on_demand_and_the_feed_first(self):
        entry = {"id": "acer", "jurisdiction": "EU", "access": {"endpoint": "https://page.test/", "feed": "https://feed.test/"}}
        session = Session(Response(ACER))
        basic = st.rss_items(entry, session, None, CONTEXT)
        self.assertEqual(session.asked, ["https://feed.test/"])
        self.assertEqual([(f.title, f.tier) for f in basic], [("ACER report on hydrogen network development", 1)])
        broad = hf.rss_items_broader(entry, Session(Response(ACER)), None, CONTEXT)
        self.assertEqual([(f.title, f.tier) for f in broad],
                         [("ACER report on hydrogen network development", 1),
                          ("Dangerous goods by rail: final decisions for RID 2027", 2)])


class EhspTestCase(unittest.TestCase):
    def test_documents_without_members_profiles(self):
        media = [{"id": 1, "date": "2026-09-11T12:00:00", "title": {"rendered": "Hydrogen_Safety._Regulations,_codes"},
                  "source_url": "https://ehsp.eu/a.pdf"},
                 {"id": 2, "date": "2026-10-26T09:00:00", "title": {"rendered": "EHSP-Factsheet"}, "source_url": "https://ehsp.eu/b.pdf"},
                 {"id": 3, "date": "2026-03-01T09:00:00", "title": {"rendered": "Jan Strybol Web"}, "source_url": "https://ehsp.eu/c.pdf"},
                 {"id": 4, "date": "2026-03-01T09:00:00", "title": {"rendered": "Call for expression of interest"},
                  "source_url": "https://ehsp.eu/d.pdf"}]
        entry = {"id": "ehsp", "access": {"endpoint": "https://ehsp.eu/wp-json/wp/v2/media?per_page=20"}}
        session = Session(Response(payload=media, headers={"X-WP-Total": "4"}))
        findings = hf.ehsp_documents(entry, session, None, CONTEXT)
        self.assertIn("per_page=100", session.asked[0])
        self.assertEqual([(f.title, f.tier, f.date) for f in findings],
                         [("Hydrogen Safety. Regulations, codes", 1, "2026-09-11"), ("EHSP-Factsheet", 2, "2026-10-26")])
        with self.assertRaises(RuntimeError):
            hf.ehsp_documents(entry, Session(Response(payload=media, headers={"X-WP-Total": "40"})), None, CONTEXT)


class RidPageTestCase(unittest.TestCase):
    PAGE = {"id": 991, "modified": "2026-10-13T08:00:00", "title": {"rendered": "RID &#8211; přeprava nebezpečných věcí"},
            "link": "https://du.gov.cz/rid/"}

    def test_the_first_run_is_a_baseline_and_a_later_change_a_finding(self):
        entry = {"id": "du-rid", "access": {"endpoint": "https://du.gov.cz/wp-json/wp/v2/pages/991"}}
        self.assertEqual(hf.du_rid_page(entry, Session(Response(payload=self.PAGE)), None, CONTEXT), [])
        self.assertEqual(hf.du_rid_page(entry, Session(Response(payload=self.PAGE)), "2026-10-20T00:00:00+00:00", CONTEXT), [])
        changed = hf.du_rid_page(entry, Session(Response(payload=self.PAGE)), "2026-10-01T00:00:00+00:00", CONTEXT)
        self.assertEqual(len(changed), 1)
        self.assertIn("RID – přeprava nebezpečných věcí", changed[0].title)
        self.assertEqual((changed[0].tier, changed[0].url), (2, "https://du.gov.cz/rid/"))


class PlanTestCase(unittest.TestCase):
    def test_stage_e4(self):
        entries, _ = sr.load()
        planned = {e["id"]: (specs, reason) for e, specs, reason in hs.plan(sr.select(entries, stage="E4"), hs.ADAPTERS)}
        self.assertEqual(sum(1 for specs, _ in planned.values() if specs), 12)
        self.assertIn("on demand", planned["mhsr-vodikova-strategia"][1])
        self.assertEqual(len(planned["du-rid"][0]), 2)
        for sid in ("acer", "mpo-cz", "eru-cz", "mmr-stavebni-pravo", "mzp-cz", "cizp"):
            self.assertEqual(next(e for e in entries if e["id"] == sid)["cadence"], "weekly", sid)


if __name__ == "__main__":
    unittest.main()
