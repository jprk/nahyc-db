"""Record checks (doc/KONTROLA_ZAZNAMU.md): check_records.py and check_records_model.py.
No network, no model, no database."""
import json
import pathlib
import sys
import unittest
from types import SimpleNamespace

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "tools"))

import check_records as cr  # noqa: E402
import check_records_model as crm  # noqa: E402


def doc(id_, identifier, title, type_="Nařízení EU", language="CS", **extra):
    return {"id": id_, "identifier": identifier, "slug": None, "title": title, "language": language, "type": type_,
            "nazev_autoritativni": None, "zdroj_autoritativni_url": None, "url": None, **extra}


OURS_955 = "Nařízení Evropského parlamentu a Rady (EU) 2023/955 ze dne 10. května 2023 o vnitřním trhu s obnovitelnými plyny a zemním plynem a o vodíku"
OFFICIAL_955 = ("Nařízení Evropského parlamentu a Rady (EU) 2023/955 ze dne 10. května 2023, kterým se zřizuje Sociální "
                "klimatický fond a mění nařízení (EU) 2021/1060")


class TextTestCase(unittest.TestCase):
    def test_similarity_ignores_boilerplate(self):
        self.assertLess(cr.similarity(OURS_955, OFFICIAL_955), cr.SIMILAR)
        same = cr.similarity("Směrnice Evropského parlamentu a Rady 2014/68/EU o tlakových zařízeních",
                             "Směrnice Evropského parlamentu a Rady 2014/68/EU ze dne 15. května 2014 o harmonizaci "
                             "právních předpisů týkajících se dodávání tlakových zařízení na trh")
        self.assertGreaterEqual(same, cr.SIMILAR)

    def test_title_date_and_kind(self):
        self.assertEqual(cr.title_date(OURS_955), "2023-05-10")
        self.assertEqual(cr.title_kind("Prováděcí nařízení Komise (EU) 2021/535"), "R")
        self.assertEqual(cr.title_kind("(EU) 2023/2413 - SMĚRNICE EVROPSKÉHO PARLAMENTU"), "L")

    def test_identifier_numbers(self):
        self.assertEqual(cr.identifier_numbers("(ES) 1907/2006"), ["1907/2006", "2006/1907"])
        self.assertEqual(cr.identifier_numbers("458/2000 Sb."), ["458/2000"])
        self.assertEqual(cr.identifier_numbers("AS 2022-1983"), ["2022"])
        self.assertEqual(cr.identifier_numbers("ISO 9809-1:2019"), ["9809-1"])


class EuTestCase(unittest.TestCase):
    CELLAR = {"32023R0955": {"exists": True, "date": "2023-05-10", "titles": {"CES": OFFICIAL_955}},
              "32023L0955": {"exists": False, "titles": {}}, "32023D0955": {"exists": False, "titles": {}}}

    def test_wrong_title_is_an_error(self):
        found = cr.check_eu(doc(86, "(EU) 2023/955", OURS_955), ["32023R0955", "32023L0955", "32023D0955"], self.CELLAR)
        self.assertEqual([f["check"] for f in found], ["eu_title"])
        self.assertEqual(found[0]["severity"], "error")

    def test_missing_number_type_and_date(self):
        self.assertEqual(cr.check_eu(doc(1, "x", "y"), ["32023D0955"], self.CELLAR)[0]["check"], "eu_not_found")
        wrong = cr.check_eu(doc(2, "(EU) 2023/955", OFFICIAL_955.replace("10. května", "11. května"), type_="Směrnice EU"),
                            ["32023R0955"], self.CELLAR)
        self.assertEqual(sorted(f["check"] for f in wrong), ["eu_date", "eu_type"])


class IsoTestCase(unittest.TestCase):
    def index(self, stage=6060):
        record = {"id": 9, "reference": "ISO 18760:2026", "currentStage": stage, "publicationDate": "2026-01-01",
                  "icsCode": [], "title": {"en": "Ship and marine technology — High-manganese austenitic steel"}}
        return {"ISO 18760": [record], ("", "18760"): [record]}

    def test_published_draft_and_withdrawn(self):
        draft = cr.check_iso(doc(1, "ISO/DIS 18760", "ISO/DIS 18760 — x", "Norma", "EN"), "ISO/DIS 18760", self.index())
        self.assertIn("iso_draft_published", [f["check"] for f in draft])
        self.assertEqual(draft[0]["id"], 1)  # the id of the document, not of the ISO record
        old = cr.check_iso(doc(2, "ISO 18760", "ISO 18760 — Ship and marine technology — High-manganese austenitic steel",
                               "Norma", "EN"), "ISO 18760", self.index(9599))
        self.assertEqual([f["check"] for f in old], ["iso_withdrawn"])

    def test_title_of_another_standard(self):
        found = cr.check_iso(doc(3, "ISO 18760", "ISO 18760 — Hydrogen fuelling stations dispensers", "Norma", "EN"),
                             "ISO 18760", self.index())
        self.assertEqual([(f["check"], f["severity"]) for f in found], [("iso_title", "error")])


class InternalTestCase(unittest.TestCase):
    def test_fragments(self):
        checks = lambda d: [f["check"] for f in cr.check_internal(d)]  # noqa: E731
        self.assertIn("bad_identifier", checks(doc(1, "A1/ - 2024.03", "A1 — plynovým obsahom", "Norma")))
        self.assertIn("bad_identifier", checks(doc(2, "Part 1", "Part 1 — Metallurgical Factors", "Norma")))
        self.assertEqual(checks(doc(3, "NFPA 2", "NFPA 2 — Hydrogen Technologies Code", "Norma")), [])
        self.assertIn("title_fragment", checks(doc(4, "ANSI/CSA CHMC 2-2019", "ANSI/CSA CHMC 2 — est Methods", "Norma")))
        self.assertIn("title_fragment", checks(doc(5, "ASME Section VIII", "Poznámka: ASME Section VIII …", "Norma")))
        self.assertIn("number_not_in_title", checks(doc(6, "ČSN EN 1234", "ČSN EN 4321 — Tlakové nádoby", "Norma")))
        self.assertEqual(checks(doc(7, "200/2022 Z. z.", "Zákon o územnom plánovaní", "Zákon")), [])

    def test_duplicates_skip_linked_documents_and_parts(self):
        a = doc(1, "AGBF Leitfaden", "AGBF Leitfaden Wasserstoff und dessen Gefahren Feuerwehr", "Metodika", "DE")
        b = doc(2, "AGBF Leitfaden – Wasserstoff", a["title"], "Metodika", "DE")
        c = doc(3, "ISO 11114-1", "ISO 11114-1 — Gas cylinders compatibility cylinder valve materials gas contents",
                "Norma", "EN")
        d = doc(4, "ISO 11114-2", c["title"].replace("11114-1", "11114-2"), "Norma", "EN")
        self.assertEqual([(f["id"], f["other_id"]) for f in cr.check_duplicates([a, b, c, d], set())], [(1, 2)])
        self.assertEqual(cr.check_duplicates([a, b], {frozenset((1, 2))}), [])


class ModelLayerTestCase(unittest.TestCase):
    def test_findings_of(self):
        d = doc(91, "(EU) 2021/535", "ochratoxin A")
        found = crm.findings_of(d, {"title_ok": "no", "description_ok": "no", "relevance": "none",
                                    "problems": ["Název se týká potravin."]})
        self.assertEqual([(f["check"], f["severity"]) for f in found],
                         [("model_title", "error"), ("model_description", "error"), ("model_relevance", "warning")])
        self.assertEqual(crm.findings_of(d, {"title_ok": "unknown", "description_ok": "none", "relevance": "low",
                                             "problems": []}), [])

    def test_check_with_a_fake_client(self):
        answer = {"title_ok": "yes", "description_ok": "yes", "relevance": "high", "problems": []}
        completion = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(answer)))],
                                     usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5))
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **a: completion)))
        result, usage = crm.Checker(client=client, model="gpt-5.5").check({"název": "x"})
        self.assertEqual(result, answer)
        item = crm.payload(doc(1, "ISO 1", "t", "Norma", description="d"), {"název v ISO": "t"})
        self.assertNotEqual(crm.input_hash(item, "gpt-5.5"), crm.input_hash(dict(item, popis="e"), "gpt-5.5"))


if __name__ == "__main__":
    unittest.main()
