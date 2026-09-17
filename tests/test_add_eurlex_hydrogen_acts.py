import pathlib
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))

import add_eurlex_hydrogen_acts as add_eurlex
from add_eurlex_hydrogen_acts import (assess_relevance, build_document_record, build_znacka,
                                      celex_document_type_letter, classify_candidate,
                                      classify_relevance_with_llm, is_off_topic)


class CelexDocumentTypeLetterTestCase(unittest.TestCase):
    def test_regulation(self):
        self.assertEqual(celex_document_type_letter("32014R0559"), "R")

    def test_directive(self):
        self.assertEqual(celex_document_type_letter("32018L2001"), "L")

    def test_decision(self):
        self.assertEqual(celex_document_type_letter("32013D0732"), "D")

    def test_non_standard_shape_returns_none(self):
        # OJ "C" series notices and multi-letter preparatory-act ids
        # don't match the standard sector-3 single-letter shape.
        self.assertIsNone(celex_document_type_letter("C2009/150/12"))
        self.assertIsNone(celex_document_type_letter("52015TA1217(06)"))


class ClassifyCandidateTestCase(unittest.TestCase):
    def test_regulation_is_binding(self):
        self.assertEqual(classify_candidate({"celex": "32014R0559"}), "Nařízení EU")

    def test_directive_is_binding(self):
        self.assertEqual(classify_candidate({"celex": "32018L2001"}), "Směrnice EU")

    def test_decision_is_binding(self):
        self.assertEqual(classify_candidate({"celex": "32013D0732"}), "Rozhodnutí EU")

    def test_recommendation_is_not_whitelisted(self):
        # "H" (Recommendation) is deliberately NOT auto-included —
        # conservative allow-list, logged for review instead.
        self.assertIsNone(classify_candidate({"celex": "32021H0001"}))

    def test_non_standard_shape_is_not_binding(self):
        self.assertIsNone(classify_candidate({"celex": "C2009/150/12"}))


class BuildZnackaTestCase(unittest.TestCase):
    def test_canonical_eu_format(self):
        self.assertEqual(build_znacka("32014R0559"), "(EU) 2014/559")

    def test_strips_leading_zeros_from_number(self):
        self.assertEqual(build_znacka("32018L2001"), "(EU) 2018/2001")

    def test_non_standard_shape_returns_none(self):
        self.assertIsNone(build_znacka("C2009/150/12"))


class BuildDocumentRecordTestCase(unittest.TestCase):
    def test_full_record_shape(self):
        candidate = {"celex": "32014R0559", "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32014R0559",
                    "matched_keyword": "hydrogen"}
        record = build_document_record(
            candidate, "Nařízení EU", {"primary": "Council Regulation (EU) No 559/2014"}, "Evropská komise")
        self.assertEqual(record["znacka"], "(EU) 2014/559")
        self.assertEqual(record["typ_dokumentu"], "Nařízení EU")
        self.assertEqual(record["nazev_cz"], "Council Regulation (EU) No 559/2014")
        self.assertEqual(record["nazev_eu"], record["nazev_cz"])
        self.assertEqual(record["odkaz_hlavni"], candidate["url"])
        self.assertEqual(record["odkaz_eu"], candidate["url"])
        self.assertEqual(record["jurisdikce"], "EU")
        self.assertEqual(record["gestor"], ["Evropská komise"])
        self.assertEqual(record["jazyk"], "")
        self.assertIn("32014R0559", record["anotace_poznamka"])
        self.assertIn("hydrogen", record["anotace_poznamka"])

    def test_no_gestor_resolved_gives_empty_list(self):
        candidate = {"celex": "32014R0559", "url": "https://x", "matched_keyword": "hydrogen"}
        record = build_document_record(candidate, "Nařízení EU", {"primary": "T"}, None)
        self.assertEqual(record["gestor"], [])


class IsOffTopicTestCase(unittest.TestCase):
    def test_hydrogen_peroxide_biocide_is_off_topic(self):
        self.assertTrue(is_off_topic(
            "Prováděcí nařízení Komise (EU) 2022/1185 o udělení povolení Unie pro kategorii "
            "biocidních přípravků „Contec Hydrogen Peroxide Biocidal Product Family“"))

    def test_hydrogen_carbonate_pesticide_is_off_topic(self):
        self.assertTrue(is_off_topic(
            "kterým se mění prováděcí nařízení (EU) č. 540/2011, pokud jde o podmínky schválení "
            "účinné látky hydrogenuhličitan draselný"))

    def test_hydrogen_cyanide_is_off_topic(self):
        self.assertTrue(is_off_topic("kyanovodík jako stávající účinná látka pro biocidní přípravky"))

    def test_customs_tariff_is_off_topic(self):
        self.assertTrue(is_off_topic(
            "re-establishing the levying of customs duties on sodium hydrogen glutamate"))

    def test_fuel_cell_joint_undertaking_is_on_topic(self):
        self.assertFalse(is_off_topic(
            "o založení společného podniku pro palivové články a vodík 2"))

    def test_hydrogen_vehicle_type_approval_is_on_topic(self):
        self.assertFalse(is_off_topic(
            "o schvalování typu vozidel na vodíkový pohon a o změně směrnice 2007/46/ES"))

    def test_hydrogen_market_mechanism_is_on_topic(self):
        self.assertFalse(is_off_topic(
            "dočasné vyloučení nabídek na dodávání vodíku z účasti na shromažďování v rámci "
            "mechanismu na podporu rozvoje trhu s vodíkem"))

    def test_empty_title_is_not_off_topic(self):
        self.assertFalse(is_off_topic(""))
        self.assertFalse(is_off_topic(None))


class ClassifyRelevanceWithLlmTestCase(unittest.TestCase):
    """Mocks add_eurlex_hydrogen_acts.client so no real OpenAI call is made."""

    def _fake_completion(self, content):
        completion = MagicMock()
        completion.choices = [MagicMock(message=MagicMock(content=content))]
        return completion

    def test_client_not_configured_returns_none(self):
        with patch.object(add_eurlex, "client", None):
            self.assertIsNone(classify_relevance_with_llm("some title"))

    def test_valid_response_is_parsed(self):
        response = '{"off_topic_probability": 90, "reasoning": "about a biocide, not fuel"}'
        with patch.object(add_eurlex, "client", MagicMock()) as mock_client:
            mock_client.chat.completions.create.return_value = self._fake_completion(response)
            result = classify_relevance_with_llm("some title", "hydrogen", "32020R0001")
        self.assertEqual(result, {"off_topic_probability": 90, "reasoning": "about a biocide, not fuel"})

    def test_invalid_score_is_retried_then_gives_up(self):
        bad = '{"off_topic_probability": "n/a", "reasoning": "unsure"}'
        with patch.object(add_eurlex, "client", MagicMock()) as mock_client, \
             patch.object(add_eurlex.time, "sleep"):
            mock_client.chat.completions.create.return_value = self._fake_completion(bad)
            result = classify_relevance_with_llm("some title")
        self.assertIsNone(result)
        self.assertEqual(mock_client.chat.completions.create.call_count, add_eurlex.MAX_LLM_ATTEMPTS)

    def test_api_exception_is_retried_then_succeeds(self):
        good = '{"off_topic_probability": 10, "reasoning": "clearly about hydrogen vehicles"}'
        with patch.object(add_eurlex, "client", MagicMock()) as mock_client, \
             patch.object(add_eurlex.time, "sleep"):
            mock_client.chat.completions.create.side_effect = [
                RuntimeError("connection reset"), self._fake_completion(good)]
            result = classify_relevance_with_llm("some title")
        self.assertEqual(result["off_topic_probability"], 10)
        self.assertEqual(mock_client.chat.completions.create.call_count, 2)

    def test_exhausting_all_retries_returns_none(self):
        with patch.object(add_eurlex, "client", MagicMock()) as mock_client, \
             patch.object(add_eurlex.time, "sleep"):
            mock_client.chat.completions.create.side_effect = RuntimeError("down")
            result = classify_relevance_with_llm("some title")
        self.assertIsNone(result)
        self.assertEqual(mock_client.chat.completions.create.call_count, add_eurlex.MAX_LLM_ATTEMPTS)


class AssessRelevanceTestCase(unittest.TestCase):
    def test_pattern_hit_short_circuits_without_calling_llm(self):
        fake_llm = MagicMock()
        result = assess_relevance("peroxid vodíku pro biocidní přípravky", llm_classifier=fake_llm)
        self.assertEqual(result["verdict"], "off_topic")
        self.assertEqual(result["method"], "pattern")
        fake_llm.assert_not_called()

    def test_high_llm_score_is_off_topic(self):
        fake_llm = MagicMock(return_value={"off_topic_probability": 90, "reasoning": "unrelated"})
        result = assess_relevance("some novel off-topic title", llm_classifier=fake_llm)
        self.assertEqual(result["verdict"], "off_topic")
        self.assertEqual(result["method"], "llm")
        self.assertEqual(result["score"], 90)

    def test_low_llm_score_is_on_topic(self):
        fake_llm = MagicMock(return_value={"off_topic_probability": 5, "reasoning": "hydrogen vehicles"})
        result = assess_relevance("some genuine hydrogen-energy title", llm_classifier=fake_llm)
        self.assertEqual(result["verdict"], "on_topic")

    def test_middle_llm_score_needs_review(self):
        fake_llm = MagicMock(return_value={"off_topic_probability": 50, "reasoning": "ambiguous"})
        result = assess_relevance("an ambiguous title", llm_classifier=fake_llm)
        self.assertEqual(result["verdict"], "needs_review")
        self.assertEqual(result["method"], "llm")

    def test_llm_unavailable_needs_review_not_a_guess(self):
        fake_llm = MagicMock(return_value=None)
        result = assess_relevance("anything", llm_classifier=fake_llm)
        self.assertEqual(result["verdict"], "needs_review")
        self.assertEqual(result["method"], "llm_unavailable")

    def test_threshold_boundaries_are_inclusive(self):
        # Exactly at HIGH_OFF_TOPIC_THRESHOLD -> off_topic, not needs_review.
        fake_llm = MagicMock(return_value={"off_topic_probability": add_eurlex.HIGH_OFF_TOPIC_THRESHOLD,
                                            "reasoning": "boundary"})
        self.assertEqual(assess_relevance("x", llm_classifier=fake_llm)["verdict"], "off_topic")
        # Exactly at LOW_ON_TOPIC_THRESHOLD -> on_topic, not needs_review.
        fake_llm = MagicMock(return_value={"off_topic_probability": add_eurlex.LOW_ON_TOPIC_THRESHOLD,
                                            "reasoning": "boundary"})
        self.assertEqual(assess_relevance("x", llm_classifier=fake_llm)["verdict"], "on_topic")


if __name__ == "__main__":
    unittest.main()
