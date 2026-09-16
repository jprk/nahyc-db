import os
import sys
import unittest

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "tools"))

from language import (CONFIDENCE_THRESHOLD, detect_language, normalize_raw_language,
                      resolve_domain_language_override)


class ResolveDomainLanguageOverrideTestCase(unittest.TestCase):
    """doc/PLAN.md §23, 2026-09-17: e-sbirka.gov.cz is the Czech
    Republic's own legal-register portal and structurally can only ever
    host Czech legislation — langdetect confusing a short Czech legal
    title for Slovak (2 real cases found in the live corpus) must not
    survive this override."""

    def test_e_sbirka_url_forces_cs(self):
        self.assertEqual(
            resolve_domain_language_override("https://e-sbirka.gov.cz/sb/2002/76"), "CS")

    def test_case_insensitive(self):
        self.assertEqual(
            resolve_domain_language_override("HTTPS://E-SBIRKA.GOV.CZ/sb/2010/133"), "CS")

    def test_unrelated_url_returns_none(self):
        self.assertIsNone(resolve_domain_language_override("https://www.zakonyprolidi.cz/cs/2021-283"))

    def test_blank_or_none_returns_none(self):
        self.assertIsNone(resolve_domain_language_override(""))
        self.assertIsNone(resolve_domain_language_override(None))


class NormalizeRawLanguageTestCase(unittest.TestCase):
    """The source spreadsheets spell the same language several ways."""

    def test_known_spellings_map_to_the_four_codes(self):
        self.assertEqual(normalize_raw_language("čeština"), "CS")
        self.assertEqual(normalize_raw_language("angličtina"), "EN")
        self.assertEqual(normalize_raw_language("EN"), "EN")

    def test_cz_is_normalized_to_the_iso_code_cs(self):
        # "CZ" is a country code, not a language code.
        self.assertEqual(normalize_raw_language("CZ"), "CS")

    def test_case_and_whitespace_insensitive(self):
        self.assertEqual(normalize_raw_language("  Čeština  "), "CS")
        self.assertEqual(normalize_raw_language("en"), "EN")

    def test_blank_or_unknown_returns_none_so_detection_runs(self):
        self.assertIsNone(normalize_raw_language(""))
        self.assertIsNone(normalize_raw_language(None))
        self.assertIsNone(normalize_raw_language("klingonština"))


class DetectLanguageTestCase(unittest.TestCase):
    def test_detects_each_of_the_four_corpus_languages(self):
        cases = [
            ("Ručne ovládané armatúry pre spotrebiče na plynné palivá", "SK"),
            ("Vodíkové palivo - Specifikace produktu a zajištění kvality pro čerpací stanice", "CS"),
            ("Liquid Organic Hydrogen Carrier auf Basis von Toluol - Bewertung und Sicherheit", "DE"),
            ("Hydrogen generators using water electrolysis - Industrial applications", "EN"),
        ]
        for title, expected in cases:
            code, confident = detect_language(title)
            self.assertEqual(code, expected, title)
            self.assertTrue(confident, title)

    def test_title_wins_over_a_description_in_another_language(self):
        # THE regression this module exists for (2026-09-15): many
        # records carry a scope/abstract in a different language than the
        # document itself. Detecting over title+description let the long
        # German description drown out the short Slovak title and
        # mislabelled 217 of 424 jurisdikce=SK records as DE.
        slovak_title = "Ručne ovládané armatúry pre spotrebiče na plynné palivá"
        german_description = (
            "Diese Europäische Norm legt Anforderungen an die Sicherheit sowie Bau und "
            "Funktionsanforderungen an handbetätigte und voreingestellte Einstellgeräte "
            "fest, die für die Verwendung mit Gasgeräten sowie gleichwertige "
            "Verwendungszwecke vorgesehen sind und im Folgenden als Einstellgeräte "
            "bezeichnet werden."
        )
        code, confident = detect_language(slovak_title, german_description)
        self.assertEqual(code, "SK")
        self.assertTrue(confident)

    def test_description_is_used_when_the_title_is_empty(self):
        code, _ = detect_language("", "Diese Europäische Norm legt Anforderungen an die "
                                      "Sicherheit von Gasgeräten fest und beschreibt sie.")
        self.assertEqual(code, "DE")

    def test_nothing_to_go_on_returns_en_flagged_unconfident(self):
        code, confident = detect_language("", "")
        self.assertEqual(code, "EN")
        self.assertFalse(confident)
        self.assertFalse(detect_language(None, None)[1])

    def test_untypable_text_is_flagged_rather_than_asserted(self):
        # Digits and punctuation carry no language signal.
        code, confident = detect_language("12345 --- 678")
        self.assertEqual(code, "EN")
        self.assertFalse(confident)

    def test_result_is_always_one_of_the_four_codes(self):
        for text in ("Bezpečnosť strojov", "Sicherheit von Maschinen",
                     "Machinery safety", "Bezpečnost strojních zařízení", "???"):
            self.assertIn(detect_language(text)[0], {"EN", "CS", "SK", "DE"}, text)

    def test_detection_is_deterministic(self):
        title = "Plynárenská infraštruktúra. Kompresorové stanice. Požiadavky na prevádzku"
        self.assertEqual([detect_language(title) for _ in range(5)],
                         [detect_language(title)] * 5)

    def test_confidence_threshold_is_a_probability(self):
        self.assertTrue(0 < CONFIDENCE_THRESHOLD <= 1)


if __name__ == "__main__":
    unittest.main()
