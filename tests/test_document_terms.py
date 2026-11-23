"""Keywords of the documents (doc/KLICOVA_SLOVA.md): document_terms.py, fetch_eurovoc.py,
fetch_ics.py, extract_keywords.py and the search over them in the catalogue. No network,
no model, no database."""
import json
import os
import pathlib
import sys
import tempfile
import unittest
from types import SimpleNamespace

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "tools"))
sys.path.append(str(ROOT))

import document_terms as dterms  # noqa: E402
import extract_keywords as ek  # noqa: E402
import fetch_eurovoc as fe  # noqa: E402
import fetch_ics as fi  # noqa: E402
import fulltext_keys  # noqa: E402


class DocKeyTestCase(unittest.TestCase):
    def test_identifier_wins(self):
        self.assertEqual(dterms.doc_key(" ČSN EN 17124 ", "https://x"), "ČSN EN 17124")

    def test_address_when_no_identifier(self):
        url = "https://example.org/strategie.pdf"
        self.assertEqual(dterms.doc_key(None, url + "\nhttps://other"), fulltext_keys.url_designation(url))

    def test_nothing(self):
        self.assertIsNone(dterms.doc_key("", None))

    def test_documents_sharing_an_address_are_told_apart_by_title(self):
        rows = [(1, None, "https://www.bveg.de/", "Strategie", "BVEG Leitfaden A"),
                (2, None, "https://www.bveg.de/", "Strategie", "BVEG Leitfaden B"),
                (3, None, "https://example.org/x.pdf", "Strategie", "Jiná"),
                (4, "ČSN EN 1", "https://www.bveg.de/", "Norma", "Norma")]
        keys = dterms.document_keys(rows)
        self.assertEqual(keys[1], fulltext_keys.title_designation("BVEG Leitfaden A"))
        self.assertNotEqual(keys[1], keys[2])
        self.assertEqual(keys[3], fulltext_keys.url_designation("https://example.org/x.pdf"))
        self.assertEqual(keys[4], "ČSN EN 1")


class PlanTestCase(unittest.TestCase):
    CACHES = {
        "eurovoc": {"(EU) 2021/535": {"celex": "32021R0535", "terms": [
            {"code": "1252", "cs": "homologace", "en": "approval"},
            {"code": "4654", "cs": None, "en": "motor vehicle"}]}},
        "ics": {"ČSN EN 12279": {"found": True, "ics": [{"code": "23.060.40", "name": "Regulátory tlaku"}],
                                 "descriptors": ["regulace tlaku", "zemní plyn"]},
                "ISO 99999": {"found": False}},
        "model": {"ČSN EN 12279": {"result": {"keywords": ["regulátor tlaku", "Regulátor  tlaku", "plynovod"]}}},
    }

    def test_terms_from_caches(self):
        terms = dterms.terms_from_caches(self.CACHES)
        self.assertEqual(terms["eurovoc"]["(EU) 2021/535"][1], {"code": "4654", "term": "motor vehicle",
                                                                "term_en": "motor vehicle"})
        self.assertEqual(terms["ics"]["ČSN EN 12279"][0]["term"], "23.060.40 Regulátory tlaku")
        self.assertEqual([t["term"] for t in terms["cas"]["ČSN EN 12279"]], ["regulace tlaku", "zemní plyn"])
        self.assertEqual(terms["ics"]["ISO 99999"], [])

    def test_plan_maps_keys_to_ids_and_drops_duplicates(self):
        rows = dterms.plan([(7, "ČSN EN 12279", None, "Norma", "t"), (8, "(EU) 2021/535", None, "Nařízení EU", "t"),
                            (9, None, None, "Studie", "")],
                           dterms.terms_from_caches(self.CACHES))
        model = [r for r in rows if r[1] == "model"]
        self.assertEqual([(r[0], r[4]) for r in model], [(7, "regulátor tlaku"), (7, "plynovod")])
        self.assertEqual({r[0] for r in rows}, {7, 8})
        self.assertIn((8, "eurovoc", 0, "1252", "homologace", "approval"), rows)

    def test_write_replaces_only_the_given_origins(self):
        executed = []
        cursor = SimpleNamespace(execute=lambda sql, params=None: executed.append((sql.strip()[:30], params)),
                                 executemany=lambda sql, rows: executed.append(("INSERT", len(rows))))
        dterms.write(cursor, [(1, "ics", 0, "1", "x", None)], ["ics"])
        self.assertTrue(executed[0][0].startswith("CREATE TABLE IF NOT EXISTS"))
        self.assertEqual(executed[1], ("DELETE FROM DocumentTerm WHERE", ("ics",)))
        self.assertEqual(executed[2], ("INSERT", 1))


class EuroVocTestCase(unittest.TestCase):
    def row(self, celex, code, label, lang):
        return {"celex": {"value": celex}, "c": {"value": f"http://eurovoc.europa.eu/{code}"},
                "l": {"value": label, "xml:lang": lang}}

    def test_eu_acts(self):
        documents = [
            (1, "(EU) 2023/1804", None, "Nařízení EU", "Nařízení Evropského parlamentu a Rady (EU) 2023/1804 ze dne …", "CS", None, None),
            (2, "[2019/795]", None, "Nařízení EU", "Předpis EHK OSN č. 134", "CS", None, None),
            (3, "ČSN EN 1", None, "Norma", "Norma", "CS", None, None),
        ]
        acts = fe.eu_acts(documents)
        self.assertEqual(acts["(EU) 2023/1804"], ["32023R1804"])
        self.assertEqual(acts["[2019/795]"], ["42019X0795"])
        self.assertNotIn("ČSN EN 1", acts)

    def test_acts_with_a_wrong_title_get_no_descriptors(self):
        documents = [(1, "(EU) 2021/535", None, "Nařízení EU", "Nařízení Komise (EU) 2021/535 …", "CS", None, None)]
        self.assertEqual(fe.eu_acts(documents), {})

    def test_entries_take_one_celex_and_both_languages(self):
        found = fe.parse_bindings([self.row("32021R0535", "1252", "homologace", "cs"),
                                   self.row("32021R0535", "1252", "approval", "en"),
                                   self.row("32021L0535", "9", "x", "cs")])
        out = fe.entries({"A": ["32021R0535"], "B": ["32021R0535", "32021L0535"], "C": ["39999R0001"]},
                         found, "2026-11-23")
        self.assertEqual(out["A"]["terms"], [{"code": "1252", "cs": "homologace", "en": "approval"}])
        self.assertNotIn("B", out)  # two acts: not guessed
        self.assertNotIn("C", out)


class IcsTestCase(unittest.TestCase):
    def test_international_part(self):
        cases = {
            "STN EN ISO 6145-11/ - 2009.02": "EN ISO 6145-11",
            "DIN EN IEC 60079-14*VDE 0165-1": "EN IEC 60079-14",
            "ISO 11623:2015": "ISO 11623",
            "ČSN EN 13445-1 (690250)": "EN 13445-1",
            "STN EN 13365/A1 – 2003.08": "EN 13365",
            "STN EN 13136+A1/ - 2019.05": "EN 13136",
            "CEN/TS 15502-3-1": "CEN/TS 15502-3-1",
            "DIN 50916-2": None,
            "G 213 (A)": None,
            "EIGA Doc 211/17/E": None,
            None: None,
        }
        for identifier, expected in cases.items():
            with self.subTest(identifier=identifier):
                self.assertEqual(fi.international_part(identifier), expected)

    def test_pick_prefers_the_valid_edition_and_skips_amendments(self):
        results = [
            {"designation": "ČSN ISO 19880-1", "title": "Plynný vodík", "issued": "9.2020", "is_valid": False,
             "catalog_number": "1"},
            {"designation": "ČSN ISO 19880-1", "title": "Plynný vodík", "issued": "8.2025", "is_valid": True,
             "catalog_number": "2"},
            {"designation": "ČSN ISO 19880-1", "title": "Změna ke stažení", "issued": "1.2026", "is_valid": True,
             "catalog_number": "3"},
            {"designation": "ČSN ISO 19880-10", "title": "Jiná", "issued": "1.2026", "is_valid": True,
             "catalog_number": "4"},
        ]
        self.assertEqual(fi.pick(results, "ISO 19880-1")["catalog_number"], "2")

    def test_pick_takes_the_cen_adoption_of_an_iso_standard(self):
        results = [{"designation": "ČSN EN ISO 17268", "title": "Plynný vodík", "issued": "1.2021",
                    "is_valid": True, "catalog_number": "5"}]
        self.assertEqual(fi.pick(results, "ISO 17268")["catalog_number"], "5")
        self.assertIsNone(fi.pick(results, "EN 17268"))

    def test_parse_ics(self):
        text = "43.060.40 - Palivové systémy spalovacích motorů71.100.20 - Technické plyny"
        self.assertEqual(fi.parse_ics(text), [{"code": "43.060.40", "name": "Palivové systémy spalovacích motorů"},
                                              {"code": "71.100.20", "name": "Technické plyny"}])
        self.assertEqual(fi.parse_ics(""), [])

    def test_descriptor_codes_are_not_keywords(self):
        self.assertEqual(fi._split_terms("BL/BY, KNX.C; regulace tlaku, zemní plyn"), ["regulace tlaku", "zemní plyn"])
        terms = dterms.terms_from_caches({"ics": {"X": {"ics": [], "descriptors": ["KIP", "tlak"]}}})
        self.assertEqual([t["term"] for t in terms["cas"]["X"]], ["tlak"])


class ExtractKeywordsTestCase(unittest.TestCase):
    def test_tidy(self):
        self.assertEqual(ek.tidy(["  vodíková  křehkost.", "Vodíková křehkost", "", "x" * 90, "ocel"]),
                         ["vodíková křehkost", "ocel"])
        self.assertEqual(len(ek.tidy([f"slovo {i}" for i in range(15)])), 10)

    def test_payload_and_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            texts = pathlib.Path(tmp)
            (texts / "17124__abcd1234.txt").write_text("Úvod  normy " * 10, encoding="utf-8")
            row = (1, "ČSN EN 17124", None, "Norma", "Vodíkové palivo", "CS", "Anotace.",
                   "data/fulltext/17124__abcd1234.pdf")
            item = ek.payload(row, texts)
        self.assertEqual(item["anotace"], "Anotace.")
        self.assertTrue(item["začátek textu"].startswith("Úvod normy"))
        self.assertNotEqual(ek.input_hash(item, "gpt-5.5"), ek.input_hash(item, "gpt-4.1"))

    def test_wanted_skips_eu_acts_with_eurovoc(self):
        rows = [(1, "(EU) 2021/535", None, "Nařízení EU", "", "", None, None),
                (2, "ČSN EN 17124", None, "Norma", "", "", None, None)]
        self.assertEqual([k for k, _ in ek.wanted(rows, {"(EU) 2021/535": {}})], ["ČSN EN 17124"])

    def test_keywords_with_a_fake_client(self):
        completion = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({"keywords": ["vodík", "vodík"]})))],
            usage=SimpleNamespace(prompt_tokens=100, completion_tokens=10))
        calls = []

        def create(**arguments):
            calls.append(arguments)
            return completion
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        result, usage = ek.Extractor(client=client, model="gpt-5.5").keywords({"název": "x"})
        self.assertEqual(result, {"keywords": ["vodík"]})
        self.assertNotIn("temperature", calls[0])  # a reasoning model takes its default
        ek.Extractor(client=client, model="gpt-4.1").keywords({"název": "x"})
        self.assertEqual(calls[1]["temperature"], 0)


class CatalogSearchTestCase(unittest.TestCase):
    def test_search_covers_the_keywords_only_when_the_table_exists(self):
        os.environ.setdefault("SECRET_KEY", "test")
        from app.app import build_filter_clause
        filters = {"q": "křehkost", "type_id": "", "source_id": "", "keyword_id": "", "include_sk": True}
        clause, _ = build_filter_clause(filters)
        self.assertNotIn("DocumentTerm", clause)
        clause, params = build_filter_clause(dict(filters, with_terms=True))
        self.assertIn("FROM DocumentTerm t", clause)
        self.assertEqual(clause.count("%s"), len(params))


if __name__ == "__main__":
    unittest.main()
