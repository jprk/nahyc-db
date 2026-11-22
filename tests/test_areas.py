"""Areas of the catalogue (data/areas.json, src/tools/areas.py, assign_areas.py,
doc/OBLASTI.md): the data file is consistent, the rules give the expected areas,
every document gets at least one, and the writing is idempotent."""
import json
import pathlib
import re
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "tools"))
import areas  # noqa: E402

CONFIG = json.loads((REPO_ROOT / "data" / "areas.json").read_text(encoding="utf-8"))


class AreasFileTestCase(unittest.TestCase):
    def test_a_few_dozen_czech_areas_tied_to_the_scope(self):
        codes = [a["code"] for a in CONFIG["areas"]]
        self.assertTrue(20 <= len(codes) <= 40, len(codes))
        self.assertEqual(len(codes), len(set(codes)))
        self.assertEqual(len({a["name"] for a in CONFIG["areas"]}), len(codes))
        self.assertIn(CONFIG["fallback"], codes)
        circles = {a["okruh"] for a in CONFIG["areas"] if a["okruh"] is not None}
        self.assertEqual(circles, set(range(1, 11)), "every subject circle of doc/DATABASE_SCOPE.md has an area")
        for area in CONFIG["areas"]:
            self.assertRegex(area["name"], r"^[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ]", area["code"])
            self.assertNotRegex(area["name"], r"[äöüß]|[ľĺŕô]", "a German or Slovak word in a name")

    def test_every_reference_is_a_known_area_and_every_pattern_compiles(self):
        codes = {a["code"] for a in CONFIG["areas"]}
        used = [c for v in CONFIG["keywords"].values() for c in v]
        used += [c for r in CONFIG["committee_rules"] for c in r["areas"]]
        used += [r["area"] for r in CONFIG["title_rules"]]
        used += [c for v in CONFIG.get("type_rules", {}).values() for c in v]
        self.assertLessEqual(set(used), codes)
        for pattern in [r["pattern"] for r in CONFIG["committee_rules"] + CONFIG["title_rules"]] + CONFIG["ignore"]:
            re.compile(pattern)

    def test_scope_circle_names_are_mapped(self):
        """app/candidates_admin.py adds the circle of an accepted candidate as a keyword."""
        sys.path.insert(0, str(REPO_ROOT / "src" / "tools"))
        import candidates as cd
        rules = areas.load()
        for name in cd.SCOPE_AREAS.values():
            self.assertTrue(rules.keyword_areas(name)[0], name)


class RulesTestCase(unittest.TestCase):
    def setUp(self):
        self.rules = areas.load()

    def assign(self, title, keywords=(), identifier=None, type_=None):
        return self.rules.assign({"identifier": identifier, "title": title, "keywords": list(keywords), "type": type_})

    def test_keywords_committees_and_ignored_values(self):
        self.assertEqual(self.rules.keyword_areas("Explosionsschutz"), (["vybuch"], True))
        self.assertEqual(self.rules.keyword_areas("Norm (ISO/TC 58/SC 3/WG 27)"), (["tlakove-nadoby"], True))
        self.assertEqual(self.rules.keyword_areas("Norm (ISO/TC 220 Cryogenic vessels)"), (["kryogenika"], True))
        self.assertEqual(self.rules.keyword_areas("STN (prijatá v sústave)"), ([], True))
        self.assertEqual(self.rules.keyword_areas("DIN - Deutsches Institut für Normung e.V."), ([], True))
        self.assertEqual(self.rules.keyword_areas("Něco zcela nového"), ([], False))
        self.assertEqual(self.rules.unknown_keywords(["Explosionsschutz", "Něco zcela nového"]), ["Něco zcela nového"])

    def test_title_rules_in_czech_slovak_english_german(self):
        self.assertIn("plnici-stanice", self.assign("STN ISO 19880-1 — Plynný vodík. Plniace stanice"))
        self.assertIn("vybuch", self.assign("ČSN EN 60079-10-1 Výbušné atmosféry"))
        self.assertIn("palivove-clanky", self.assign("Fuel cell technologies — Part 3"))
        self.assertIn("tlakove-nadoby", self.assign("Gasflaschen — Druckbehälter"))
        self.assertIn("chemicke-latky", self.assign("Nařízení (ES) č. 1272/2008 o klasifikaci (CLP)"))
        self.assertIn("rfnbo", self.assign("paliva z obnovitelných zdrojů nebiologického původu"))

    def test_keyword_first_then_type_then_title(self):
        found = self.assign("Vodíková strategie a plnicí stanice", keywords=["Explosionsschutz"], type_="Strategie")
        self.assertEqual(found["vybuch"], "keyword")
        self.assertEqual(found["strategie"], "type")
        self.assertEqual(found["plnici-stanice"], "title")
        self.assertEqual(list(found), [c for c in self.rules.codes if c in found], "in the order of the data file")

    def test_every_document_gets_an_area(self):
        self.assertEqual(self.assign("Zákon o spotřebních daních", keywords=["EU"]), {"obecne": "fallback"})
        self.assertEqual(self.assign(""), {"obecne": "fallback"})


class FakeCursor:
    def __init__(self, results=()):
        self.results = list(results)
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchall(self):
        return self.results.pop(0) if self.results else []

    def fetchone(self):
        rows = self.fetchall()
        return rows[0] if rows else None


class PlanTestCase(unittest.TestCase):
    def test_plan_only_changed_documents(self):
        rules = areas.load()
        docs = [{"id": 1, "identifier": None, "title": "Výbušné atmosféry", "keywords": []},
                {"id": 2, "identifier": None, "title": "Výbušné atmosféry", "keywords": []}]
        stored = {1: {"vybuch": "title"}}
        self.assertEqual(areas.plan(rules, docs, stored), {2: {"vybuch": "title"}})

    def test_execute_writes_areas_and_links(self):
        rules = areas.load()
        ids = [(a["code"], i) for i, a in enumerate(rules.areas, start=1)]
        cursor = FakeCursor([ids])
        areas.execute(cursor, rules, {5: {"vybuch": "title"}}, create=False)
        statements = [s for s, _ in cursor.executed]
        self.assertFalse([s for s in statements if s.startswith("CREATE")])
        self.assertEqual(sum(1 for s in statements if s.startswith("INSERT INTO Area ")), len(rules.areas))
        self.assertIn(("DELETE FROM DocumentArea WHERE document_id = %s", (5,)), cursor.executed)
        inserted = [p for s, p in cursor.executed if s.startswith("INSERT INTO DocumentArea")]
        self.assertEqual(inserted, [(5, dict(ids)["vybuch"], "title")])


if __name__ == "__main__":
    unittest.main()
