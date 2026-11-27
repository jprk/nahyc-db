"""Descriptions of the legal acts from their own text (issue #37, doc/ANOTACE_PREDPISU.md):
act_provisions.py, annotate_acts.py, build_unified_db.apply_act_description() and
init_db.resolve_description(). No network, no model, no database."""
import json
import pathlib
import sys
import unittest
from types import SimpleNamespace

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "tools"))

import act_provisions as ap  # noqa: E402
import annotate_acts as aa  # noqa: E402
import build_unified_db as bud  # noqa: E402
import init_db  # noqa: E402

CZ_LAW = """ZÁKON
ze dne 20. února 2001
o posuzování vlivů na životní prostředí
§ 1
Předmět úpravy
(1) Zákon v souladu s právem Evropské unie1) upravuje posuzování vlivů na životní prostředí
a veřejné zdraví.
(2) Posuzování vlivů podléhají záměry a koncepce.
§ 2
Ochrana životního prostředí
Každý je povinen chránit životní prostředí.
"""


class OpeningProvisionTestCase(unittest.TestCase):
    def test_czech_subject_provision_word_for_word(self):
        p = ap.opening_provision(CZ_LAW, "CS")
        self.assertTrue(p["usable"])
        self.assertEqual(ap.label_of(p), "§ 1 Předmět úpravy")
        self.assertEqual(p["text"], "(1) Zákon v souladu s právem Evropské unie upravuje posuzování vlivů na životní "
                                    "prostředí a veřejné zdraví.\n(2) Posuzování vlivů podléhají záměry a koncepce.")

    def test_transposition_clause_with_a_subject_is_kept(self):
        text = "§ 1\nPředmět úpravy\nTento zákon zapracovává příslušné předpisy Evropské unie1) a upravuje podmínky podnikání.\n§ 2\n"
        self.assertTrue(ap.opening_provision(text)["usable"])
        only = "§ 1\nPředmět úpravy\nTento zákon zapracovává příslušné předpisy Evropské unie1).\n§ 2\n"
        self.assertEqual(ap.opening_provision(only)["reason"], "ustanovení jen vyjmenovává transponované předpisy EU")

    def test_eu_act_amending_and_definitions(self):
        eu = "Článek 1\nPředmět\nTato směrnice stanoví společný rámec pro podporu energie z obnovitelných zdrojů.\nČlánek 2\n"
        p = ap.opening_provision(eu)
        self.assertTrue(p["usable"])
        self.assertEqual(ap.label_of(p), "čl. 1 Předmět")
        amending = "Článek 1\nSměrnice 98/70/ES se mění takto:\n1) Článek 2 se nahrazuje tímto:\nČlánek 2\n"
        self.assertEqual(ap.opening_provision(amending)["reason"], "novela: ustanovení jen mění jiný předpis")
        annexes = "Článek 1\nPřílohy V a VI směrnice 2008/57/ES se nahrazují zněním příloh I a II této směrnice.\nČlánek 2\n"
        self.assertFalse(ap.opening_provision(annexes)["usable"])
        definitions = "§ 1\nZákladní pojmy\nPro účely této vyhlášky se rozumí\na) požární bezpečností …\n§ 2\n"
        self.assertEqual(ap.opening_provision(definitions)["reason"], "první ustanovení vymezuje pojmy")

    def test_purpose_and_sentence_start(self):
        purpose = "Článek 1\nÚčelem této směrnice je stanovit rámec pro ochranu vod.\nČlánek 2\n"
        self.assertTrue(ap.opening_provision(purpose)["usable"])
        sentence = "§ 1\nTento zákon\na) upravuje právní vztahy při výkonu závislé práce,\nb) upravuje rovněž …\n§ 2\n"
        p = ap.opening_provision(sentence)
        self.assertEqual(p["heading"], "")
        self.assertTrue(p["text"].startswith("Tento zákon\na) upravuje"))
        slovak = "§ 1\nPredmet úpravy\nTento zákon upravuje územné plánovanie, štátu,1) a orgány.\n§ 2\n"
        self.assertEqual(ap.opening_provision(slovak, "SK")["text"], "Tento zákon upravuje územné plánovanie, štátu, a orgány.")
        self.assertIsNone(ap.opening_provision("Bez paragrafů.", "CS"))

    def test_shorten(self):
        text = ("Věta jedna je dlouhá. " * 100).strip()
        short = ap.shorten(text, 200)
        self.assertTrue(short.endswith(" …"))
        self.assertLessEqual(len(short), 202)


class DescribesTestCase(unittest.TestCase):
    def test_located_quotes(self):
        self.assertIsNone(ap.describes("Tato směrnice zavádí další požadavky s cílem zajistit nezávislost provozovatele "
                                       "infrastruktury a otevřít trh.", "bod odůvodnění 7"))
        self.assertEqual(ap.describes("Směrnice 98/70/ES stanoví environmentální specifikace pro tržní paliva a jejich "
                                      "sledování v členských státech.", "bod odůvodnění 1"),
                         "bod odůvodnění nemluví o tomto předpisu")
        self.assertEqual(ap.describes("Ministerstvo dopravy stanoví podle § 137 odst. 2 zákona č. 361/2000 Sb. "
                                      "k provedení § 124 odst. 1 tohoto zákona:", "úvod"),
                         "citace končí dvojtečkou (výčet nebo úvodní věta)")
        self.assertEqual(ap.describes("Krátké."), "citace je příliš krátká")


class RestatesTitleTestCase(unittest.TestCase):
    def test_restatements_and_real_descriptions(self):
        self.assertTrue(ap.restates_title("Zákon č. 201/2012 Sb. - Zákon o ochraně ovzduší", "201/2012 Sb. Zákon o ochraně ovzduší"))
        self.assertTrue(ap.restates_title("Zákon č. 100/2001 Sb. - Zákon o posuzování vlivů na životní prostředí a o změně "
                                          "některých souvisejících zákonů", "100/2001 Sb."))
        self.assertFalse(ap.restates_title("Transpozice provedena – nařízení vlády č. 406/2004 Sb.", "1999/92/ES"))
        self.assertFalse(ap.restates_title("", "x"))


class DescriptionOfTestCase(unittest.TestCase):
    def test_provision_located_summary(self):
        self.assertEqual(ap.description_of({"provision": {"label": "§ 1 Předmět úpravy", "text": "T", "method": "pattern"}}),
                         ("T", "§ 1 Předmět úpravy, doslova z textu předpisu", None))
        located = {"located": {"found": True, "label": "1", "text": "This Regulation applies to …"}}
        self.assertEqual(ap.description_of(located)[1], "bod 1, doslova z textu předpisu, ustanovení vyhledal jazykový model")
        self.assertEqual(ap.description_of({"located": {"found": False}, "summary": {"summary": "S", "verdict": "ok"}}),
                         (None, None, "S"))
        self.assertEqual(ap.description_of({"summary": {"verdict": "reject"}}), (None, None, None))


def doc(id_, identifier, description, title="Zákon o ovzduší"):
    return {"id": id_, "identifier": identifier, "url": None, "type": "Zákon", "title": title, "language": "CS",
            "description": description, "nazev_autoritativni": None}


class PlanTestCase(unittest.TestCase):
    CACHE = {"A": {"provision": {"label": "§ 1", "text": "Tento zákon upravuje ovzduší.", "method": "pattern"}},
             "B": {"summary": {"summary": "Zákon mění zákon o ovzduší.", "verdict": "ok"}},
             "C": {"summary": {"verdict": "reject"}},
             "D": {"provision": {"label": "§ 1", "text": "x", "method": "pattern"}}}

    def test_plan(self):
        documents = [doc(1, "A", "Zákon č. 1/2000 Sb. - Zákon o ovzduší"), doc(2, "B", "Zákon č. 2/2000 Sb. - Zákon o ovzduší"),
                     doc(3, "C", "Transpozice provedena nařízením vlády č. 1/2001 Sb."), doc(4, "D", "Editor napsal popis.")]
        changes = {d["identifier"]: c for d, c in aa.plan(documents, self.CACHE, protected={"D"})}
        self.assertEqual(changes["A"]["popis_zdroj"], "§ 1, doslova z textu předpisu")
        self.assertEqual((changes["B"]["description"], changes["B"]["popis_priblizny"], changes["B"]["manual"]),
                         (None, "Zákon mění zákon o ovzduší.", True))
        self.assertNotIn("C", changes)  # a note of the survey stays when nothing better is found
        self.assertNotIn("D", changes)  # an editor's description is never touched

    def test_review_reason(self):
        self.assertEqual(aa.review_reason("chybí popis/anotace dokumentu; jazyk odhadnut", False), "jazyk odhadnut")
        self.assertEqual(aa.review_reason("chybí popis/anotace dokumentu", True),
                         "chybí popis/anotace dokumentu; popis je třeba doplnit ručně")
        self.assertIsNone(aa.review_reason(None, False))

    def test_editor_keys_ignore_a_removed_description(self):
        corrections = {"A": {"changes": {"anotace_poznamka": "Popis editora."}}, "B": {"changes": {"anotace_poznamka": ""}},
                       "C": {"changes": {"nazev_cz": "x"}}}
        self.assertEqual(aa.editor_keys(corrections), {"A"})


class ModelStepsTestCase(unittest.TestCase):
    def models(self, answers):
        calls = []

        def create(**arguments):
            calls.append(arguments)
            answer = answers.pop(0)
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(answer)))],
                                   usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5))
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        return aa.Models(client=client, model="gpt-5.5"), calls

    def test_locate_keeps_only_a_verbatim_describing_quote(self):
        text = "Čl. I\nZákon č. 1/2000 Sb. se mění takto:\n(17) Tato směrnice mění směrnici 2008/57/ES tak, aby se zlepšila interoperabilita železničního systému Unie.\n"
        quote = "Tato směrnice mění směrnici 2008/57/ES tak, aby se zlepšila interoperabilita železničního systému Unie."
        models, _ = self.models([{"found": True, "quote": quote, "label": "bod odůvodnění 17"}])
        self.assertEqual(aa.locate(models, doc(1, "A", ""), text)["found"], True)
        invented = "Tento zákon upravuje vše, co se týká železnice, a to velmi podrobně a důkladně v celém rozsahu."
        models, _ = self.models([{"found": True, "quote": invented, "label": "§ 1"}])
        self.assertEqual(aa.locate(models, doc(1, "A", ""), text)["rejected"], "citace se v textu nevyskytuje doslova")

    def test_summary_is_kept_only_when_the_checker_accepts_it(self):
        models, calls = self.models([{"summary": "Zakon upravuje dráhy."},
                                     {"verdict": "ok", "corrected": "Zákon upravuje dráhy.", "problems": []}])
        result = aa.summarize(models, doc(1, "A", ""), "text")
        self.assertEqual(result["summary"], "Zákon upravuje dráhy.")
        self.assertEqual([c["model"] for c in calls], [aa.SUMMARY_MODEL, aa.CHECK_MODEL])
        self.assertNotEqual(aa.SUMMARY_MODEL, aa.CHECK_MODEL)
        models, _ = self.models([{"summary": "Zákon zakazuje vlaky."},
                                 {"verdict": "reject", "corrected": "", "problems": ["Tvrzení z textu neplyne."]}])
        self.assertNotIn("summary", aa.summarize(models, doc(1, "A", ""), "text"))


class RebuildTestCase(unittest.TestCase):
    def test_apply_act_description(self):
        descriptions = {"(EU) 2018/2001": {"provision": {"label": "čl. 1 Předmět", "text": "Tato směrnice stanoví …",
                                                         "method": "pattern"}},
                        "(EU) 2018/2001 [EN]": {"provision": {"label": "Art. 1 Subject matter",
                                                              "text": "This Directive establishes …", "method": "pattern"}},
                        "1/2000 Sb.": {"summary": {"summary": "Zákon mění …", "verdict": "ok"}}}
        czech = {"znacka": "(EU) 2018/2001", "typ_dokumentu": "Směrnice EU", "jazyk": "čeština", "nazev_cz": "Směrnice"}
        english = {"znacka": "(EU) 2018/2001", "typ_dokumentu": "Směrnice EU", "jazyk": "angličtina", "nazev_cz": "Directive"}
        law = {"znacka": "1/2000 Sb.", "typ_dokumentu": "Zákon", "anotace_poznamka": "Zákon č. 1/2000 Sb. - Zákon o x",
               "nazev_cz": "Zákon o x"}
        norm = {"znacka": "ČSN 1", "typ_dokumentu": "Norma"}
        self.assertTrue(bud.apply_act_description(czech, descriptions))
        self.assertEqual(czech["popis_zdroj"], "čl. 1 Předmět, doslova z textu předpisu")
        if bud.row_language(english) == "EN":
            bud.apply_act_description(english, descriptions)
            self.assertEqual(english["popis_autoritativni"], "This Directive establishes …")
        self.assertTrue(bud.apply_act_description(law, descriptions))
        self.assertEqual(law["popis_priblizny"], "Zákon mění …")
        self.assertEqual(init_db.resolve_description(law), "")  # the annotation only restated the title
        self.assertIn("popis je třeba doplnit ručně", init_db.detect_data_quality_issues(law))
        self.assertFalse(bud.apply_act_description(norm, descriptions))
        protected = {"znacka": "(EU) 2018/2001", "typ_dokumentu": "Směrnice EU", "jazyk": "čeština"}
        self.assertFalse(bud.apply_act_description(protected, descriptions, protected={"(EU) 2018/2001"}))


if __name__ == "__main__":
    unittest.main()
