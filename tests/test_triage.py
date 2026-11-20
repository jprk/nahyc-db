"""Unit tests of the automatic triage of the candidate queue (src/tools/triage.py,
triage_candidates.py): the rules of data/triage_rules.json, the subject areas and
metadata of a proposal, duplicates, what the model is sent (public data only), the
confidence and thresholds, the cache of the model's answers (the OpenAI client is a
fake, nothing goes to the network) and the refusal to write to the live database
before the rules are approved."""
import json
import math
import pathlib
import sys
import tempfile
import types
import unittest
from unittest import mock

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "tools"))
import triage  # noqa: E402
import triage_candidates  # noqa: E402

TYPES = ["Metodika", "Nařízení EU", "Nařízení vlády", "Nezařazeno", "Norma", "Rozhodnutí EU", "Směrnice EU",
         "Strategie", "Studie", "Vyhláška", "Zákon"]
INDEX = triage.document_index([
    (1, "(EU) 2019/942", "Nařízení o ACER", "CS"),
    (2, "(EU) 2019/942 [EN]", "Regulation on ACER", "EN"),
    (3, "ČSN EN 17124", "ČSN EN 17124 — Vodíkové palivo", "CS"),
    (4, "458/2000 Sb.", "Energetický zákon", "CS"),
    (5, "(EU) 2018/2001 [EN]", "Renewable Energy Directive", "EN"),
], areas={4: [9], 5: [1, 9]}, validity={"CZ:7/2099": {"status": "zrušený", "repealed_by": ["CZ:8/2099"]}})


def candidate(**fields):
    base = {"id": 1, "candidate_key": "CZ:1/2099", "source": "citation", "signal": None, "tier": 1,
            "designation": "1/2099 Sb.", "title": "Zákon o zkouškách", "document_type": "Zákon",
            "url": "https://example.test/1", "language": "CS", "jurisdikce": "CZ", "validity_status": "účinný",
            "puvodce": None, "scope_area": None, "scope_areas": None, "status": "new", "evidence": {},
            "cited_by": 3, "decision_note": "interní poznámka editora", "triage_json": None}
    base.update(fields)
    return base


class FakeCompletions:
    def __init__(self, answers, token_probability=1.0):
        self.answers = list(answers)
        self.calls = []
        self.logprob = math.log(token_probability)

    def create(self, **arguments):
        self.calls.append(arguments)
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        content = json.dumps(answer, ensure_ascii=False)
        # log probabilities of the tokens of the answer: the recommendation's first token gets `token_probability`
        tokens, logprobs = [], []
        head, value = content.split('"recommendation": "', 1)
        for piece in (head + '"recommendation": "', value[:3], value[3:]):
            tokens.append(types.SimpleNamespace(token=piece, logprob=self.logprob if piece == value[:3] else 0.0))
        return types.SimpleNamespace(
            choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=content),
                                           logprobs=types.SimpleNamespace(content=tokens))],
            usage=types.SimpleNamespace(prompt_tokens=4000, completion_tokens=200,
                                        prompt_tokens_details=types.SimpleNamespace(cached_tokens=1000)))


def fake_client(answers, token_probability=1.0):
    completions = FakeCompletions(answers, token_probability)
    return types.SimpleNamespace(chat=types.SimpleNamespace(completions=completions)), completions


def answer(recommendation="accept", category="v_rozsahu", confidence=0.97, areas=(7,), **fields):
    return {"reasoning": "Předpis upravuje bezpečnost tlakových zařízení.", "recommendation": recommendation,
            "category": category, "scope_areas": list(areas), "document_type": fields.get("document_type", "Zákon"),
            "puvodce": fields.get("puvodce"), "official_title": fields.get("official_title"),
            "confidence": confidence, "vztah_k_vodiku": fields.get("hydrogen", False),
            "vztah_k_vodiku_zduvodneni": "Zkušební zdůvodnění."}


class RulesTestCase(unittest.TestCase):
    config = triage.load_config()

    def rule(self, **fields):
        return triage.match_rule(candidate(**fields), self.config, INDEX)["id"]

    def test_the_rules_file_is_valid_and_approved(self):
        self.assertTrue(triage.is_approved(self.config))
        self.assertEqual(self.config["rules"][-1]["when"], {}, "the last rule must match everything")
        # the decisions of 20 Nov 2026 (doc/FRONTA_AUTOMAT.md, odstavec 3.3)
        self.assertEqual(self.config["model"]["auto_categories"], {
            "mimo_rozsah": {"action": "reject"}, "dane_dotace": {"action": "defer", "hydrogen": True},
            "zastaraly": {"action": "defer", "hydrogen": True}, "neni_dokument": {"action": "defer", "hydrogen": True},
            "fondy_zakazky": {"action": "defer"}, "obecne_vyrobky": {"action": "defer"}})
        self.assertTrue(set(self.config["model"]["auto_categories"]) <= set(triage.CATEGORIES))

    def test_rules_in_order(self):
        self.assertEqual(self.rule(candidate_key="EU:2019/942", designation="(EU) 2019/942"), "R1-duplicita")
        self.assertEqual(self.rule(validity_status="zrušený"), "R8-zruseny")
        self.assertEqual(self.rule(candidate_key="EU:2019/942", designation="(EU) 2019/942", language="SK",
                                   title="Nariadenie o ACER"), "R7-jazykova-verze")
        self.assertEqual(self.rule(source="acer", url="https://www.acer.europa.eu/news/x", candidate_key="acer:x",
                                   designation=None), "R3-novinka")
        self.assertEqual(self.rule(source="ehsp", title="20261021 EHSP Webinar. Safety Matters", designation=None,
                                   candidate_key="ehsp:1", url="https://ehsp.eu/x.pdf"), "R3-novinka")
        self.assertEqual(self.rule(source="cps-tpg", candidate_key="NORM:TPG 304 03", designation="TPG 304 03",
                                   title="TPG 304 03 Plnicí stanice stlačeného vodíku"), "R4-tpg")
        self.assertEqual(self.rule(source="mpo"), "R5-mpo")
        self.assertEqual(self.rule(source="vestnik-unmz", signal="draft", document_type="Norma",
                                   candidate_key="DRAFT-NORM:CZ:13/0015/26", designation=None,
                                   title="Průmyslové armatury pro vodíkové aplikace"), "R6-navrh-vodik")
        # a draft without a type, or without hydrogen in its title, goes to the model
        self.assertEqual(self.rule(signal="draft", document_type=None, title="Hydrogen strategy",
                                   candidate_key="DRAFT-EU:hys:1", designation=None), "R9-model")
        self.assertEqual(self.rule(signal="draft", title="Návrh zákona o daních", candidate_key="DRAFT-CZ:psp:1",
                                   designation=None), "R9-model")
        self.assertEqual(self.rule(), "R9-model")

    def test_duplicates(self):
        # the same act in the same language is a duplicate (R1), in another language a variant (R7)
        found = triage.duplicate_of(candidate(candidate_key="EU:2019/942", designation="(EU) 2019/942", language="EN"),
                                    INDEX)
        self.assertEqual(found[0], 2)
        self.assertIn("ve stejném jazyce (EN)", found[1])
        self.assertEqual(triage.duplicate_of(candidate(candidate_key="EU:2019/942", designation="(EU) 2019/942"),
                                             INDEX)[0], 1)
        self.assertIsNone(triage.duplicate_of(candidate(candidate_key="EU:2019/942", language="SK"), INDEX))
        self.assertEqual([d[0] for d in triage.language_variant_of(candidate(candidate_key="EU:2019/942",
                                                                            language="SK"), INDEX)], [1, 2])
        self.assertEqual(triage.language_variant_of(candidate(candidate_key="EU:2019/942", language="DE"), INDEX), [])
        self.assertEqual(triage.duplicate_of(candidate(candidate_key="NORM:EN 17124", designation="ČSN EN 17124"),
                                             INDEX)[0], 3)
        # a draft amending a document of the database is no duplicate of it
        self.assertIsNone(triage.duplicate_of(candidate(candidate_key="DRAFT-CZ:psp:2", designation=None,
                                                        title="Návrh zákona, kterým se mění zákon č. 458/2000 Sb."),
                                              INDEX))
        self.assertIsNone(triage.duplicate_of(candidate(), INDEX))

    def test_tpg_proposal(self):
        c = candidate(source="cps-tpg", candidate_key="NORM:TPG 982 03", designation="TPG 982 03", document_type="Norma",
                      title="TPG 982 03 Plnicí zařízení pro motorová vozidla s pohonným systémem CNG",
                      language=None, jurisdikce=None)
        decision = triage.decide(c, self.config, INDEX, TYPES)
        self.assertEqual((decision.rule, decision.action, decision.errors), ("R4-tpg", "propose", []))
        m = decision.metadata
        self.assertEqual((m["title"], m["document_type"], m["puvodce"], m["language"], m["jurisdikce"],
                          m["scope_areas"]),
                         ("Plnicí zařízení pro motorová vozidla s pohonným systémem CNG", "Norma",
                          "Český plynárenský svaz (ČPS)", "CS", "CZ", "4,5"))
        self.assertTrue(m["decision_note"].startswith("Automat (R4-tpg): "))

    def test_subject_areas_of_a_proposal(self):
        rule = {"proposal": {"areas_by_designation": {"TPG 9": [7], "TPG 934": [9]}, "default_areas": [3]}}
        self.assertEqual(triage.proposal_areas(candidate(designation="TPG 934 01"), rule, self.config), [9])
        self.assertEqual(triage.proposal_areas(candidate(designation="TPG 905 01"), rule, self.config), [7])
        self.assertEqual(triage.proposal_areas(candidate(scope_areas="2,8"), rule, self.config), [2, 8])
        self.assertEqual(triage.proposal_areas(candidate(), rule, self.config, {"scope_areas": [10]}), [10])
        self.assertEqual(triage.proposal_areas(candidate(designation="X", title="Netopené tlakové nádoby"), rule,
                                               self.config), [2])
        self.assertEqual(triage.proposal_areas(candidate(designation="X", title="Něco"), rule, self.config), [3])

    def test_without_an_area_the_rule_leaves_it_to_the_model(self):
        c = candidate(source="vestnik-unmz", signal="draft", document_type="Norma", designation=None,
                      candidate_key="DRAFT-NORM:CZ:1/1/26", title="Vodíkové technologie - Názvosloví")
        decision = triage.decide(c, self.config, INDEX, TYPES, rules_only=True)
        self.assertEqual((decision.rule, decision.action), ("R6-navrh-vodik", "model"))

    def test_language_variant_proposal(self):
        # the English text of an act the database has in Czech: `<designation> [EN]`, the areas of the Czech text
        c = candidate(candidate_key="CZ:458/2000", designation="458/2000 Sb.", language="EN", title="Energy Act",
                      document_type="Zákon")
        decision = triage.decide(c, self.config, INDEX, TYPES)
        self.assertEqual((decision.rule, decision.action, decision.errors), ("R7-jazykova-verze", "propose", []))
        self.assertEqual((decision.metadata["designation"], decision.metadata["scope_areas"]), ("458/2000 Sb. [EN]", "9"))
        self.assertIn("#4 458/2000 Sb. (CS)", decision.note)
        # the Czech text of an act the database has only in English keeps the plain designation
        c = candidate(candidate_key="EU:2018/2001", designation="(EU) 2018/2001", document_type="Směrnice EU",
                      title="Směrnice o podpoře energie z obnovitelných zdrojů", jurisdikce="EU")
        decision = triage.decide(c, self.config, INDEX, TYPES)
        self.assertEqual((decision.rule, decision.metadata["designation"], decision.metadata["scope_areas"]),
                         ("R7-jazykova-verze", "(EU) 2018/2001", "1,9"))

    def test_repealed_act_is_proposed_with_its_successor(self):
        c = candidate(candidate_key="CZ:7/2099", designation="7/2099 Sb.", validity_status="zrušený",
                      title="Vyhláška o bezpečnosti plynových zařízení")
        decision = triage.decide(c, self.config, INDEX, TYPES)
        self.assertEqual((decision.rule, decision.action, decision.errors), ("R8-zruseny", "propose", []))
        self.assertIn("Zrušil jej: CZ:8/2099.", decision.note)
        self.assertEqual(triage.repealing_acts(candidate(candidate_key="CZ:1/2000", evidence={
            "validity": {"repealed_by": ["CZ:2/2000"]}}), INDEX), ["CZ:2/2000"])

    def test_variant_designations_and_relation_directions(self):
        import candidates as cd
        self.assertEqual(cd.variant_designation("(EU) 2019/942 [EN]", "SK"), "(EU) 2019/942 [SK]")
        self.assertEqual(cd.variant_designation("(EU) 2019/942 [EN]", "CS"), "(EU) 2019/942")
        self.assertIsNone(cd.variant_designation("(EU) 2019/942", "DE"))
        self.assertEqual(cd.act_keys("(EU) 2019/942 [SK]"), {"EU:2019/942"})
        new_sk = (9, "(EU) 2019/942 [SK]", "SK")
        links = cd.translation_relations(new_sk, [(1, "(EU) 2019/942", "CS"), (2, "(EU) 2019/942 [EN]", "EN")])
        self.assertEqual([(a[0], b[0]) for a, b in links], [(9, 1), (9, 2)])
        new_cs = (9, "(EU) 2018/2001", "CS")
        links = cd.translation_relations(new_cs, [(5, "(EU) 2018/2001 [EN]", "EN"), (6, "(EU) 2018/2001 [SK]", "SK")])
        self.assertEqual([(a[0], b[0]) for a, b in links], [(5, 9), (6, 9)])

    def test_rejection_note_names_the_document(self):
        decision = triage.decide(candidate(candidate_key="CZ:458/2000", designation="458/2000 Sb."), self.config,
                                 INDEX, TYPES)
        self.assertEqual(decision.action, "reject")
        self.assertIn("#4", decision.note)

    def test_language_and_jurisdiction_guesses(self):
        self.assertEqual(triage.guess_language("Shell boilers - Part 8"), "EN")
        self.assertEqual(triage.guess_language("Kotle na plynná paliva"), "CS")
        self.assertEqual(triage.guess_jurisdiction(candidate(candidate_key="DRAFT-EU:2025/1(COD)")), "EU")
        self.assertEqual(triage.guess_jurisdiction(candidate(candidate_key="NORM:SAE J2601", designation="SAE J2601")),
                         "mezinárodní")


class ModelTestCase(unittest.TestCase):
    config = triage.load_config()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cache = pathlib.Path(self.tmp.name) / "cache.json"

    def assessor(self, answers, token_probability=1.0, **kwargs):
        client, completions = fake_client(answers, token_probability)
        return triage.ModelAssessor(self.config, TYPES, cache_path=self.cache, client=client, log=lambda *a: None,
                                    **kwargs), completions

    def test_payload_has_public_data_only(self):
        c = candidate(evidence={"citing_ids": [4], "contexts": {"4": {"count": 1, "places": [
            {"before": "podle ", "cited": "1/2099 Sb.", "after": " platí", "amendment": False}]}},
            "mpo_rows": [{"row": "MPO-1", "cislo": "1/2099 Sb.", "nazev": "Zákon", "nositel": "MPO",
                          "poznamka": "interní poznámka z tabulky"}]},
            proposed_by_name="Jan Editor", decision_note="interní poznámka editora")
        payload = triage.build_payload(c, {4: ("458/2000 Sb.", "Energetický zákon")})
        text = json.dumps(payload, ensure_ascii=False)
        for private in ("Jan Editor", "interní poznámka"):
            self.assertNotIn(private, text)
        self.assertEqual(payload["citujici_dokumenty"][0]["oznaceni"], "458/2000 Sb.")
        self.assertIn("[1/2099 Sb.]", payload["citujici_dokumenty"][0]["uryvky"][0])
        self.assertEqual(payload["radky_tabulky_mpo"], [{"cislo": "1/2099 Sb.", "nazev": "Zákon"}])

    def test_the_answer_is_cached_and_carries_the_measured_confidence(self):
        assessor, completions = self.assessor([answer()], token_probability=0.8)
        payload = {"kandidat": {"nazev": "Zákon o zkouškách"}}
        self.assertEqual(assessor.estimate([payload])[0], 1)
        result = assessor.assess(payload)
        self.assertAlmostEqual(result["token_confidence"], 0.8, places=3)
        self.assertAlmostEqual(triage.confidence(result), 0.8, places=3)
        self.assertEqual(completions.calls[0]["response_format"]["type"], "json_schema")
        self.assertEqual(completions.calls[0]["model"], "gpt-4o-mini")
        again, completions_again = self.assessor([])  # a new run reads the cache file, no call
        self.assertEqual(again.assess(payload)["recommendation"], "accept")
        self.assertEqual(completions_again.calls, [])
        self.assertEqual(again.estimate([payload])[0], 0)
        self.assertEqual(json.loads(self.cache.read_text())[assessor.key(payload)]["usage"]["prompt_tokens"], 4000)

    def test_the_counts_of_the_database_do_not_change_the_cache_key(self):
        a, _ = self.assessor([], composition="Norma 1000")
        b, _ = self.assessor([], composition="Norma 1001")
        self.assertNotEqual(a.system, b.system)
        self.assertEqual(a.key({"x": 1}), b.key({"x": 1}))

    def test_a_bad_or_failing_answer_leaves_the_candidate_to_the_editors(self):
        assessor, completions = self.assessor([RuntimeError("timeout"), answer(category="nesmysl"),
                                               answer(confidence=1.5)])
        with mock.patch.object(triage.time, "sleep"):
            self.assertIsNone(assessor.assess({"kandidat": {}}))
        self.assertEqual(len(completions.calls), 3)

    def test_cost(self):
        prices = self.config["model"]["prices_usd_per_million_tokens"]["gpt-4o-mini"]
        self.assertAlmostEqual(triage.cost({"prompt_tokens": 1_000_000, "completion_tokens": 1_000_000,
                                            "cached_tokens": 0}, prices), 0.75)
        self.assertAlmostEqual(triage.cost({"prompt_tokens": 1_000_000, "cached_tokens": 1_000_000}, prices), 0.075)

    def test_thresholds_and_approved_categories(self):
        config = self.config
        act = triage.model_action
        self.assertEqual(act(answer(confidence=0.97), config), "propose")
        self.assertEqual(act(answer(confidence=0.9), config), "recommend")
        self.assertEqual(act({**answer(confidence=0.97), "token_confidence": 0.6}, config), "recommend")
        self.assertEqual(act(answer(confidence=0.99, areas=()), config), "recommend")
        # out of scope: rejected, but only when the model recommends rejecting and is sure
        self.assertEqual(act(answer("reject", "mimo_rozsah", 0.99), config), "reject")
        self.assertEqual(act(answer("reject", "mimo_rozsah", 0.9), config), "recommend")
        self.assertEqual(act(answer("defer", "mimo_rozsah", 0.99), config), "recommend")
        self.assertEqual(act(answer("reject", "zahranicni", 0.99), config), "recommend")
        # taxes, obsolete acts, non-documents: deferred only with a relation to hydrogen
        for category in ("dane_dotace", "zastaraly", "neni_dokument"):
            self.assertEqual(act(answer("reject", category, 0.99), config), "recommend", category)
            self.assertEqual(act(answer("reject", category, 0.99, hydrogen=True), config), "defer", category)
        # ... or hydrogen named in the candidate's own texts
        self.assertEqual(act(answer("reject", "dane_dotace", 0.99), config,
                             candidate(title="Zákon o spotřební dani z vodíku")), "defer")
        # funds, programmes, procurement and general product rules: always deferred, even an acceptance
        self.assertEqual(act(answer("reject", "fondy_zakazky", 0.99), config), "defer")
        self.assertEqual(act(answer("accept", "obecne_vyrobky", 0.99), config), "defer")
        self.assertEqual(act(answer("accept", "obecne_vyrobky", 0.9), config), "recommend")

    def test_categories_by_title(self):
        act = triage.model_action
        # funds, programmes and procurement in the title: deferred whatever the model said and however sure it was
        fund = candidate(title="Nařízení, kterým se zřizuje Nástroj pro oživení a odolnost")
        self.assertEqual(triage.effective_category(answer(), fund, self.config), ("fondy_zakazky", True))
        self.assertEqual(act(answer(confidence=0.7), self.config, fund), "defer")
        self.assertEqual(act(answer(), self.config, candidate(title="Směrnice o zadávání veřejných zakázek")), "defer")
        self.assertEqual(act(answer(), self.config, candidate(title="Směrnice o strojních zařízeních")), "defer")
        # a standard is left to the model; so is a title without the pattern
        norm = candidate(title="Výbušné atmosféry - Část 28", document_type="Norma")
        self.assertEqual(triage.effective_category(answer(), norm, self.config), ("v_rozsahu", False))
        self.assertEqual(act(answer(), self.config, candidate(title="Zákon o podporovaných zdrojích energie")), "propose")

    def test_hydrogen_in_the_candidates_texts(self):
        self.assertTrue(triage.hydrogen_in_text(candidate(title="Směrnice o RFNBO")))
        self.assertTrue(triage.hydrogen_in_text(candidate(evidence={"contexts": {"4": {"places": [
            {"before": "plnicí stanice vodíku podle ", "cited": "1/2099 Sb.", "after": ""}]}}})))
        self.assertTrue(triage.hydrogen_in_text(candidate(evidence={"findings": {"x": {
            "title": "Vyhláška", "excerpt": "palivové články"}}})))
        self.assertFalse(triage.hydrogen_in_text(candidate(title="Zákon o myslivosti")))

    def test_a_proposal_of_the_model_passes_the_editors_validation(self):
        assessor, _ = self.assessor([answer(document_type="Vyhláška", puvodce="Ministerstvo průmyslu a obchodu",
                                            areas=(4,))])
        c = candidate(document_type="Nezařazeno", title="Vyhláška o měřidlech ...")
        decision = triage.decide(c, self.config, INDEX, TYPES, assessor=assessor)
        self.assertEqual((decision.action, decision.errors), ("propose", []))
        self.assertEqual((decision.metadata["document_type"], decision.metadata["puvodce"],
                          decision.metadata["scope_areas"]), ("Vyhláška", "Ministerstvo průmyslu a obchodu", "4"))
        self.assertIn("Model (gpt-4o-mini): přijmout", decision.note)
        # a type outside the list fails the validation: then only the recommendation stays
        assessor, _ = self.assessor([{**answer(), "document_type": None}])
        decision = triage.decide(candidate(document_type=None, candidate_key="CZ:2/2099", designation="2/2099 Sb."),
                                 self.config, INDEX, TYPES, assessor=assessor)
        self.assertEqual(decision.action, "recommend")
        self.assertIn("Vyberte typ dokumentu.", decision.errors)

    def test_schema_asks_for_the_reasoning_first(self):
        schema = triage.response_schema(TYPES)["schema"]
        self.assertEqual(list(schema["properties"])[0], "reasoning")
        self.assertEqual(set(schema["required"]), set(schema["properties"]))
        self.assertIn("Výroba vodíku", triage.system_prompt(TYPES, scope="(rozsah)"))


class CommandTestCase(unittest.TestCase):
    def test_apply_on_the_live_database_needs_approved_rules(self):
        conn = mock.MagicMock()
        lines = []
        unapproved = {**triage.load_config(), "approval": {"approved_by": None, "date": None}}
        with mock.patch.object(triage_candidates, "connect", return_value=(conn, "h2regdocs")), \
                mock.patch.object(triage, "load_config", return_value=unapproved):
            code = triage_candidates.main(["--apply", "--rules-only"], out=lines.append)
        self.assertEqual(code, 2)
        self.assertIn("not approved", lines[0])
        conn.cursor.assert_not_called()

    def test_select(self):
        queue = list(range(100))
        self.assertEqual(triage_candidates.select(queue, limit=3), [0, 1, 2])
        sample = triage_candidates.select(queue, sample=10, seed=1)
        self.assertEqual(len(set(sample)), 10)
        self.assertEqual(sample, triage_candidates.select(queue, sample=10, seed=1))


if __name__ == "__main__":
    unittest.main()
