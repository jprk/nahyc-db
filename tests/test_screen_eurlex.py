import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))

import screen_eurlex as se


class CelexCandidateZnackasTestCase(unittest.TestCase):
    def test_regulation_celex(self):
        self.assertEqual(sorted(se.celex_candidate_znackas("32014R0559")),
                          sorted(["2014/559", "559/2014"]))

    def test_consolidated_text_celex_still_parses(self):
        # sector '0' (consolidated text) still carries the original year/number
        self.assertEqual(sorted(se.celex_candidate_znackas("02014D0450")),
                          sorted(["2014/450", "450/2014"]))

    def test_unparseable_celex_returns_empty(self):
        self.assertEqual(se.celex_candidate_znackas("C2009/150/12"), [])


class NormalizeForDiffTestCase(unittest.TestCase):
    def test_strips_everything_but_digits_and_slash(self):
        self.assertEqual(se.normalize_for_diff("(EU) 2024/1788"), "2024/1788")
        self.assertEqual(se.normalize_for_diff("2024/1788"), "2024/1788")

    def test_empty_input(self):
        self.assertEqual(se.normalize_for_diff(""), "")
        self.assertEqual(se.normalize_for_diff(None), "")


class LoadKnownZnackaDigitsTestCase(unittest.TestCase):
    def test_ignores_empty_znacka(self):
        raw = [{"znacka": ""}, {"znacka": "(EU) 2024/1788"}]
        self.assertEqual(se.load_known_znacka_digits(raw), {"2024/1788"})


class FindNewCandidatesTestCase(unittest.TestCase):
    def _binding(self, celex, title):
        return {"celex": {"value": celex}, "title": {"value": title}}

    def test_known_celex_is_excluded(self):
        bindings = [self._binding("32024R1788", "Regulation on hydrogen")]
        known = {"2024/1788"}
        self.assertEqual(se.find_new_candidates(bindings, known, "hydrogen"), [])

    def test_unknown_celex_is_reported(self):
        bindings = [self._binding("32020R9999", "Some new hydrogen regulation")]
        known = {"2024/1788"}
        result = se.find_new_candidates(bindings, known, "hydrogen")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["celex"], "32020R9999")
        self.assertIn("CELEX:32020R9999", result[0]["url"])

    def test_unparseable_celex_is_reported_too(self):
        # can't compute a candidate znacka to diff against -- report it
        # rather than silently drop it, consistent with the rest of this
        # codebase's "never guess, escalate instead" convention.
        bindings = [self._binding("C2009/150/12", "Call for proposals on hydrogen")]
        result = se.find_new_candidates(bindings, set(), "hydrogen")
        self.assertEqual(len(result), 1)

    def test_duplicate_celex_in_bindings_reported_once(self):
        bindings = [self._binding("32020R9999", "x"), self._binding("32020R9999", "x")]
        result = se.find_new_candidates(bindings, set(), "hydrogen")
        self.assertEqual(len(result), 1)


class BuildQueryTestCase(unittest.TestCase):
    def test_keyword_and_limit_are_interpolated(self):
        query = se.build_query("hydrogen", limit=50)
        self.assertIn("'hydrogen'", query)
        self.assertIn("LIMIT 50", query)


if __name__ == "__main__":
    unittest.main()
