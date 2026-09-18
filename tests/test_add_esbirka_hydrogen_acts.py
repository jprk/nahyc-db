import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))

import add_esbirka_hydrogen_acts as add_esbirka
from add_esbirka_hydrogen_acts import (assess_relevance, build_document_record, build_znacka,
                                       classify_relevance_with_llm, is_actual_hydrogen_mention,
                                       is_off_topic, resolve_znacka_for_uri, strip_html,
                                       strip_leading_znacka)


class IsActualHydrogenMentionTestCase(unittest.TestCase):
    def test_real_hydrogen_word_matches(self):
        self.assertTrue(is_actual_hydrogen_mention("409 - Čerpací stanice vodíku"))
        self.assertTrue(is_actual_hydrogen_mention("Vodní roztoky peroxydu vodíku"))

    def test_elevator_guide_rail_word_does_not_match(self):
        # "vodítko"/"vodítka"/"vodítek" share a 4-letter prefix with
        # "vodík" but mean "guide rail" — the exact false positive that
        # motivated tightening screen_esbirka.py's own keyword.
        self.assertFalse(is_actual_hydrogen_mention("musí býti vyčištěna a namazána vodítka"))
        self.assertFalse(is_actual_hydrogen_mention("Je-li výtah uspořádán uprostřed schodů, nesmí býti vodítka spojena"))

    def test_empty_snippet_does_not_match(self):
        self.assertFalse(is_actual_hydrogen_mention(""))
        self.assertFalse(is_actual_hydrogen_mention(None))


class StripHtmlTestCase(unittest.TestCase):
    def test_strips_tags_and_collapses_whitespace(self):
        html = '<table class="TABLEX"><tbody><tr><th>Číslo</th>\n<td>  Pojmenování  </td></tr></tbody></table>'
        self.assertEqual(strip_html(html), "Číslo Pojmenování")

    def test_plain_text_is_unchanged_besides_whitespace(self):
        self.assertEqual(strip_html("409 - Čerpací stanice vodíku"), "409 - Čerpací stanice vodíku")


class BuildZnackaTestCase(unittest.TestCase):
    def test_canonical_cz_format(self):
        self.assertEqual(build_znacka("2015", "294"), "294/2015 Sb.")

    def test_strips_leading_zeros_from_number(self):
        self.assertEqual(build_znacka("2021", "0283"), "283/2021 Sb.")


class StripLeadingZnackaTestCase(unittest.TestCase):
    def test_strips_zakonyprolidi_prefix(self):
        title = "294/2015 Sb. Vyhláška, kterou se provádějí pravidla provozu na pozemních komunikacích"
        self.assertEqual(strip_leading_znacka(title),
                         "Vyhláška, kterou se provádějí pravidla provozu na pozemních komunikacích")

    def test_no_prefix_is_unchanged(self):
        self.assertEqual(strip_leading_znacka("Vyhláška o něčem"), "Vyhláška o něčem")


class IsOffTopicTestCase(unittest.TestCase):
    def test_customs_tariff_is_off_topic(self):
        self.assertTrue(is_off_topic("Číslo československého celního sazebníku Pojmenování zboží"))

    def test_hydrogen_peroxide_old_spelling_is_off_topic(self):
        self.assertTrue(is_off_topic("Vodní roztoky peroxydu vodíku s více než 6% váhy"))

    def test_old_trade_treaty_is_off_topic(self):
        self.assertTrue(is_off_topic(
            "kterou se uvádí v prozatímní platnost obchodní smlouva mezi ČSR a Hospodářskou Unií"))

    def test_hydrogen_filling_station_sign_is_on_topic(self):
        self.assertFalse(is_off_topic("409 - Čerpací stanice vodíku"))

    def test_empty_snippet_is_not_off_topic(self):
        self.assertFalse(is_off_topic(""))
        self.assertFalse(is_off_topic(None))


class ResolveZnackaForUriTestCase(unittest.TestCase):
    def test_fragment_node_one_hop(self):
        fake_sparql = MagicMock(return_value=[
            {"s": {"value": "https://opendata.eselpoint.gov.cz/esel-esb/eli/cz/sb/2015/294/2022-01-01/"
                            "dokument/prilohy/priloha_7/bod_4/frag_8661195"}},
        ])
        with patch.object(add_esbirka, "run_sparql", fake_sparql):
            result = resolve_znacka_for_uri(
                "https://opendata.eselpoint.gov.cz/esel-esb/právní-akt-fragment/8661195", session=None)
        self.assertEqual(result, ("2015", "294"))
        fake_sparql.assert_called_once()

    def test_binary_soubor_node_two_hops(self):
        frag_result = [{"s": {"value": "https://opendata.eselpoint.gov.cz/esel-esb/právní-akt-fragment/8661195"}}]
        act_result = [{"s": {"value": "https://opendata.eselpoint.gov.cz/esel-esb/eli/cz/sb/2025/205/0000-00-00/"
                                       "dokument/novela/cl_1/bod_25/frag_1075596211"}}]
        fake_sparql = MagicMock(side_effect=[frag_result, act_result])
        with patch.object(add_esbirka, "run_sparql", fake_sparql):
            result = resolve_znacka_for_uri(
                "https://opendata.eselpoint.gov.cz/esel-esb/právní-akt-binární-soubor/1535809", session=None)
        self.assertEqual(result, ("2025", "205"))
        self.assertEqual(fake_sparql.call_count, 2)

    def test_metadata_node_is_never_resolvable(self):
        fake_sparql = MagicMock()
        with patch.object(add_esbirka, "run_sparql", fake_sparql):
            result = resolve_znacka_for_uri(
                "https://opendata.eselpoint.gov.cz/esel-esb/právní-akt-metadata/40449", session=None)
        self.assertIsNone(result)
        fake_sparql.assert_not_called()

    def test_empty_reverse_query_result_is_unresolved(self):
        fake_sparql = MagicMock(return_value=[])
        with patch.object(add_esbirka, "run_sparql", fake_sparql):
            result = resolve_znacka_for_uri(
                "https://opendata.eselpoint.gov.cz/esel-esb/právní-akt-fragment/99999999", session=None)
        self.assertIsNone(result)


class ClassifyRelevanceWithLlmTestCase(unittest.TestCase):
    """Mocks add_esbirka_hydrogen_acts.client so no real OpenAI call is made."""

    def _fake_completion(self, content):
        completion = MagicMock()
        completion.choices = [MagicMock(message=MagicMock(content=content))]
        return completion

    def test_client_not_configured_returns_none(self):
        with patch.object(add_esbirka, "client", None):
            self.assertIsNone(classify_relevance_with_llm("some snippet"))

    def test_valid_response_is_parsed(self):
        response = '{"off_topic_probability": 85, "reasoning": "customs tariff listing"}'
        with patch.object(add_esbirka, "client", MagicMock()) as mock_client:
            mock_client.chat.completions.create.return_value = self._fake_completion(response)
            result = classify_relevance_with_llm("some snippet", "1/1925 Sb.")
        self.assertEqual(result, {"off_topic_probability": 85, "reasoning": "customs tariff listing"})

    def test_exhausting_all_retries_returns_none(self):
        with patch.object(add_esbirka, "client", MagicMock()) as mock_client, \
             patch.object(add_esbirka.time, "sleep"):
            mock_client.chat.completions.create.side_effect = RuntimeError("down")
            result = classify_relevance_with_llm("some snippet")
        self.assertIsNone(result)
        self.assertEqual(mock_client.chat.completions.create.call_count, add_esbirka.MAX_LLM_ATTEMPTS)


class AssessRelevanceTestCase(unittest.TestCase):
    def test_pattern_hit_short_circuits_without_calling_llm(self):
        fake_llm = MagicMock()
        result = assess_relevance("Číslo celního sazebníku francouzského", llm_classifier=fake_llm)
        self.assertEqual(result["verdict"], "off_topic")
        self.assertEqual(result["method"], "pattern")
        fake_llm.assert_not_called()

    def test_high_llm_score_is_off_topic(self):
        fake_llm = MagicMock(return_value={"off_topic_probability": 90, "reasoning": "unrelated"})
        result = assess_relevance("some novel off-topic snippet", llm_classifier=fake_llm)
        self.assertEqual(result["verdict"], "off_topic")
        self.assertEqual(result["method"], "llm")

    def test_low_llm_score_is_on_topic(self):
        fake_llm = MagicMock(return_value={"off_topic_probability": 5, "reasoning": "hydrogen refuelling"})
        result = assess_relevance("some genuine hydrogen-energy snippet", llm_classifier=fake_llm)
        self.assertEqual(result["verdict"], "on_topic")

    def test_middle_llm_score_needs_review(self):
        fake_llm = MagicMock(return_value={"off_topic_probability": 50, "reasoning": "ambiguous"})
        result = assess_relevance("an ambiguous snippet", llm_classifier=fake_llm)
        self.assertEqual(result["verdict"], "needs_review")

    def test_llm_unavailable_needs_review_not_a_guess(self):
        fake_llm = MagicMock(return_value=None)
        result = assess_relevance("anything", llm_classifier=fake_llm)
        self.assertEqual(result["verdict"], "needs_review")
        self.assertEqual(result["method"], "llm_unavailable")


class BuildDocumentRecordTestCase(unittest.TestCase):
    def test_full_record_shape(self):
        candidate = {"uri": "https://opendata.eselpoint.gov.cz/esel-esb/právní-akt-binární-soubor/1535953",
                    "matched_keyword": "vodík*"}
        record = build_document_record(
            "294/2015 Sb.",
            "294/2015 Sb. Vyhláška, kterou se provádějí pravidla provozu na pozemních komunikacích",
            "Vyhláška",
            "https://www.zakonyprolidi.cz/cs/2015-294",
            candidate,
            "409 - Čerpací stanice vodíku")
        self.assertEqual(record["znacka"], "294/2015 Sb.")
        self.assertEqual(record["typ_dokumentu"], "Vyhláška")
        self.assertIn("Vyhláška", record["nazev_cz"])
        self.assertEqual(record["odkaz_hlavni"], "https://www.zakonyprolidi.cz/cs/2015-294")
        self.assertEqual(record["jurisdikce"], "CZ")
        self.assertEqual(record["gestor"], [])
        self.assertEqual(record["jazyk"], "")
        self.assertIn("Čerpací stanice vodíku", record["anotace_poznamka"])


class MainHumanExclusionTestCase(unittest.TestCase):
    """doc/PLAN.md §33: a human's review-queue decision must survive a
    future re-run even though the LLM score that originally produced
    that queue entry is not deterministic — end-to-end through main()
    with every path constant redirected into a temp directory and the
    network-touching pieces mocked."""

    def _write_json(self, path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def test_excluded_znacka_is_never_reclassified_or_readded(self):
        # Under add_esbirka.REPO_ROOT, not the system temp dir — main()
        # prints paths via .relative_to(REPO_ROOT), which raises for a
        # path outside it.
        with tempfile.TemporaryDirectory(dir=add_esbirka.REPO_ROOT) as tmp:
            tmp = pathlib.Path(tmp)
            candidates_path = tmp / "candidates.json"
            raw_db_path = tmp / "raw.json"
            output_path = tmp / "discovered.json"
            off_topic_path = tmp / "off_topic.json"
            review_queue_path = tmp / "review_queue.json"
            unresolved_path = tmp / "unresolved.json"
            human_excluded_path = tmp / "human_excluded.json"

            self._write_json(candidates_path, {"e-Sbirka": [
                {"uri": "https://opendata.eselpoint.gov.cz/esel-esb/právní-akt-fragment/173675",
                 "snippet": "kotlové vozy s vodíkem musí míti nálepky", "matched_keyword": "vodík*"},
            ]})
            self._write_json(raw_db_path, [])
            self._write_json(output_path, [])
            self._write_json(off_topic_path, [])
            self._write_json(review_queue_path, [])
            self._write_json(unresolved_path, [])
            self._write_json(human_excluded_path, [
                {"znacka": "1/1946 Sb.", "reason": "test exclusion", "decided_at": "2026-09-17"},
            ])

            # If the exclusion check didn't run first, this LLM mock
            # would score it as confidently on_topic (0) and it would
            # get added — the test only passes if the human-excluded
            # check short-circuits before this is ever consulted.
            fake_llm = MagicMock(return_value={"off_topic_probability": 0, "reasoning": "would be added"})

            with patch.object(add_esbirka, "CANDIDATES_PATH", candidates_path), \
                 patch.object(add_esbirka, "RAW_DB_PATH", raw_db_path), \
                 patch.object(add_esbirka, "OUTPUT_PATH", output_path), \
                 patch.object(add_esbirka, "OFF_TOPIC_PATH", off_topic_path), \
                 patch.object(add_esbirka, "REVIEW_QUEUE_PATH", review_queue_path), \
                 patch.object(add_esbirka, "UNRESOLVED_PATH", unresolved_path), \
                 patch.object(add_esbirka, "HUMAN_EXCLUDED_PATH", human_excluded_path), \
                 patch.object(add_esbirka, "resolve_znacka_for_uri", return_value=("1946", "1")), \
                 patch.object(add_esbirka, "classify_relevance_with_llm", fake_llm), \
                 patch.object(add_esbirka, "zakonyprolidi_extract"), \
                 patch.object(add_esbirka.time, "sleep"), \
                 patch.object(sys, "argv", ["add_esbirka_hydrogen_acts.py"]):
                add_esbirka.main()

            with open(output_path, "r", encoding="utf-8") as f:
                self.assertEqual(json.load(f), [])
            with open(review_queue_path, "r", encoding="utf-8") as f:
                self.assertEqual(json.load(f), [])
            with open(off_topic_path, "r", encoding="utf-8") as f:
                self.assertEqual(json.load(f), [])
            fake_llm.assert_not_called()


if __name__ == "__main__":
    unittest.main()
