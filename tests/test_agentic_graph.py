import pathlib
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from agentic.graph import build_graph
from agentic.state import initial_state

GOOD_SOURCE = "Regulation (EU) 2023/1804 establishes hydrogen refuelling infrastructure requirements."
CANDIDATE = {"url": "https://example.org/act", "title": "Hydrogen act", "source": "EUR-Lex"}


class _FakeCursor:
    def __init__(self, rows=None):
        self._rows = rows or []

    def execute(self, *args, **kwargs):
        pass

    def fetchall(self):
        return self._rows

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class _FakeConnection:
    def __init__(self, rows=None):
        self._rows = rows or []

    def cursor(self):
        return _FakeCursor(self._rows)

    def close(self):
        pass


def _good_parse(url):
    return GOOD_SOURCE, None


def _good_extractor(source_text):
    return {
        "znacka": "(EU) 2023/1804",
        "nazev": "Hydrogen refuelling infrastructure regulation",
        "typ_dokumentu": "Nařízení EU",
        "gestor": "Evropská komise",
        "verification_evidence": ["Regulation (EU) 2023/1804 establishes hydrogen refuelling"],
    }


class GraphHappyPathTestCase(unittest.TestCase):
    def test_verified_and_new_reaches_end_without_escalation(self):
        app = build_graph(parse_source=_good_parse, llm_extractor=_good_extractor,
                          get_connection=lambda: _FakeConnection())
        result = app.invoke(initial_state(CANDIDATE))
        self.assertTrue(result["verified"])
        self.assertFalse(result["escalated"])
        self.assertEqual(result["reconciliation_action"], "new")
        self.assertEqual(result["retry_count"], 1)


class GraphParseFailureTestCase(unittest.TestCase):
    def test_parse_failure_escalates_without_calling_extractor(self):
        extractor = MagicMock()
        app = build_graph(parse_source=lambda url: (None, "fetch failed: timeout"),
                          llm_extractor=extractor, get_connection=lambda: _FakeConnection())
        result = app.invoke(initial_state(CANDIDATE))
        self.assertTrue(result["escalated"])
        self.assertIn("parse failed", result["escalation_reason"])
        extractor.assert_not_called()


class GraphVerificationRetryTestCase(unittest.TestCase):
    def test_bad_evidence_retries_then_escalates_at_cap(self):
        call_count = {"n": 0}

        def bad_extractor(source_text):
            call_count["n"] += 1
            return {"znacka": "X", "nazev": "Y", "typ_dokumentu": "Zákon",
                    "verification_evidence": ["a quote never present in the source text"]}

        app = build_graph(parse_source=_good_parse, llm_extractor=bad_extractor,
                          get_connection=lambda: _FakeConnection())
        result = app.invoke(initial_state(CANDIDATE))
        self.assertFalse(result["verified"])
        self.assertTrue(result["escalated"])
        self.assertEqual(call_count["n"], 3)
        self.assertIn("verification failed after 3 attempt", result["escalation_reason"])

    def test_recovers_after_one_bad_attempt(self):
        call_count = {"n": 0}

        def flaky_extractor(source_text):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return {"znacka": "X", "verification_evidence": ["not in the source"]}
            return _good_extractor(source_text)

        app = build_graph(parse_source=_good_parse, llm_extractor=flaky_extractor,
                          get_connection=lambda: _FakeConnection())
        result = app.invoke(initial_state(CANDIDATE))
        self.assertTrue(result["verified"])
        self.assertFalse(result["escalated"])
        self.assertEqual(call_count["n"], 2)


class GraphExtractionUnavailableTestCase(unittest.TestCase):
    def test_extractor_returning_none_escalates_at_cap_not_a_crash(self):
        app = build_graph(parse_source=_good_parse, llm_extractor=lambda text: None,
                          get_connection=lambda: _FakeConnection())
        result = app.invoke(initial_state(CANDIDATE))
        self.assertTrue(result["escalated"])
        self.assertEqual(result["retry_count"], 3)


class GraphResearchTestCase(unittest.TestCase):
    def test_research_fills_missing_field_and_is_flagged_applied(self):
        def extractor_missing_gestor(source_text):
            result = _good_extractor(source_text)
            result["gestor"] = None
            return result

        def fake_research_applier(extracted, url):
            filled = dict(extracted)
            filled["gestor"] = "Evropská komise"
            return filled

        app = build_graph(parse_source=_good_parse, llm_extractor=extractor_missing_gestor,
                          get_connection=lambda: _FakeConnection(), research_applier=fake_research_applier)
        result = app.invoke(initial_state(CANDIDATE))
        self.assertTrue(result["research_applied"])
        self.assertEqual(result["extracted"]["gestor"], "Evropská komise")

    def test_no_missing_fields_skips_research(self):
        app = build_graph(parse_source=_good_parse, llm_extractor=_good_extractor,
                          get_connection=lambda: _FakeConnection())
        result = app.invoke(initial_state(CANDIDATE))
        self.assertFalse(result["research_applied"])


class GraphReconciliationTestCase(unittest.TestCase):
    def test_exact_identifier_match_is_existing_not_escalated(self):
        app = build_graph(parse_source=_good_parse, llm_extractor=_good_extractor,
                          get_connection=lambda: _FakeConnection(rows=[("(EU) 2023/1804",)]))
        result = app.invoke(initial_state(CANDIDATE))
        self.assertEqual(result["reconciliation_action"], "existing")
        self.assertFalse(result["escalated"])

    def test_ambiguous_title_match_escalates(self):
        # Same title text as _good_extractor's "nazev", under a different
        # identifier -- the real-world ambiguous case (a duplicate title
        # posted under two references), not a coincidental partial match.
        rows = [("(EU) 2020/1", "Hydrogen refuelling infrastructure regulation")]

        class _AmbiguousConnection(_FakeConnection):
            def cursor(self):
                fetch_calls = {"n": 0}
                cursor = _FakeCursor()

                def fetchall():
                    fetch_calls["n"] += 1
                    return [] if fetch_calls["n"] == 1 else rows

                cursor.fetchall = fetchall
                return cursor

        app = build_graph(parse_source=_good_parse, llm_extractor=_good_extractor,
                          get_connection=lambda: _AmbiguousConnection())
        result = app.invoke(initial_state(CANDIDATE))
        self.assertEqual(result["reconciliation_action"], "ambiguous")
        self.assertTrue(result["escalated"])
        self.assertIn("ambiguous match", result["escalation_reason"])


if __name__ == "__main__":
    unittest.main()
