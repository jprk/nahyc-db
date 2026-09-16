import pathlib
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from sites.eurlex import (celex_candidates_from_designation, celex_from_url,
                          eli_candidates_from_designation, extract,
                          fetch_responsible_gestor, resource_uris_from_text)


def _fake_session(bindings):
    """A requests.Session double whose .get() returns a canned SPARQL
    results.bindings payload — no real network call."""
    session = MagicMock()
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = {"results": {"bindings": bindings}}
    session.get.return_value = response
    return session


def _binding(lang, title):
    return {"lang": {"value": lang}, "title": {"value": title}}


class CelexFromUrlTestCase(unittest.TestCase):
    def test_extracts_celex_from_colon_style_url(self):
        self.assertEqual(
            celex_from_url("https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32014R1300"),
            "32014R1300")

    def test_extracts_celex_from_url_encoded_colon(self):
        self.assertEqual(
            celex_from_url("https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A52020DC0301"),
            "52020DC0301")

    def test_eli_style_url_returns_none(self):
        # Real corpus shape -- deliberately NOT resolved (see module
        # docstring): no verified, non-guessing path from ELI to CELEX.
        self.assertIsNone(celex_from_url("https://eur-lex.europa.eu/eli/dir/2019/692/oj"))

    def test_oj_reference_style_url_returns_none(self):
        self.assertIsNone(celex_from_url("https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=OJ:L_202401788"))

    def test_blank_url_returns_none(self):
        self.assertIsNone(celex_from_url(""))
        self.assertIsNone(celex_from_url(None))


class ExtractTestCase(unittest.TestCase):
    def test_prefers_czech_title_over_english(self):
        session = _fake_session([
            _binding("ENG", "English title"),
            _binding("CES", "Český název"),
        ])
        result = extract("https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32014R0559",
                          session=session)
        self.assertEqual(result, {"title": "Český název", "description": None})

    def test_falls_back_to_english_when_no_czech(self):
        session = _fake_session([_binding("ENG", "English only title")])
        result = extract("https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32014R0559",
                          session=session)
        self.assertEqual(result, {"title": "English only title", "description": None})

    def test_no_celex_in_url_is_none_without_querying(self):
        session = _fake_session([_binding("ENG", "Should never be returned")])
        result = extract("https://eur-lex.europa.eu/eli/dir/2019/692/oj", session=session)
        self.assertIsNone(result)
        session.get.assert_not_called()

    def test_empty_bindings_is_none(self):
        session = _fake_session([])
        result = extract("https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:99999X9999",
                          session=session)
        self.assertIsNone(result)



class ResourceUrisFromTextTestCase(unittest.TestCase):
    """doc/PLAN.md §16, 2026-09-16: matching Cellar via owl:sameAs on
    whichever URL shape the record already has, instead of trying to
    reconstruct a CELEX id."""

    def test_celex_style_url(self):
        self.assertEqual(
            resource_uris_from_text("https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32022R0869"),
            ["http://publications.europa.eu/resource/celex/32022R0869"])

    def test_eli_style_url(self):
        self.assertEqual(
            resource_uris_from_text("https://eur-lex.europa.eu/eli/reg_del/2023/1184/oj"),
            ["http://publications.europa.eu/resource/eli/reg_del/2023/1184/oj"])

    def test_bare_official_journal_reference(self):
        self.assertEqual(
            resource_uris_from_text("https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=OJ:L_202401788"),
            ["http://publications.europa.eu/resource/oj/L_202401788"])

    def test_every_url_in_a_multi_url_field_is_returned(self):
        # A known Excel-paste artifact: one `url` value holding two URLs,
        # where the FIRST is a consolidated-text CELEX (sector "0") that
        # Cellar has no owl:sameAs record for, and the real act's
        # sector-"3" CELEX comes second.
        field = ("https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:02022R0869-20250205\n\n"
                 "https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32022R0869")
        # The consolidation date after the hyphen is not part of the
        # CELEX id, so it drops out — but the sector-"0" id that remains
        # still has no owl:sameAs record, which is why the second URL has
        # to be tried at all.
        self.assertEqual(resource_uris_from_text(field),
                         ["http://publications.europa.eu/resource/celex/02022R0869",
                          "http://publications.europa.eu/resource/celex/32022R0869"])

    def test_unrecognized_url_yields_nothing_rather_than_a_guess(self):
        self.assertEqual(resource_uris_from_text("https://www.slov-lex.sk/pravne-predpisy/SK/ZZ/2010/75"), [])
        self.assertEqual(resource_uris_from_text(""), [])
        self.assertEqual(resource_uris_from_text(None), [])


class CelexCandidatesFromDesignationTestCase(unittest.TestCase):
    def test_type_decides_the_celex_letter(self):
        self.assertIn("http://publications.europa.eu/resource/celex/32023R2405",
                      celex_candidates_from_designation("(EU) 2023/2405", "Nařízení EU"))
        self.assertIn("http://publications.europa.eu/resource/celex/32023L2413",
                      celex_candidates_from_designation("(EU) 2023/2413", "Směrnice EU"))
        self.assertIn("http://publications.europa.eu/resource/celex/32022D2427",
                      celex_candidates_from_designation("(EU) 2022/2427", "Rozhodnutí EU"))

    def test_both_orderings_are_offered_when_either_could_be_the_year(self):
        # EU act numbering flipped in 2015: pre-2015 regulations read
        # "No 402/2013" (number first), everything since reads
        # "2023/2405" (year first). Rather than guess, offer both and let
        # the caller try each against Cellar.
        got = celex_candidates_from_designation("(EU) 402/2013", "Nařízení EU")
        self.assertIn("http://publications.europa.eu/resource/celex/32013R0402", got)

    def test_sequence_number_is_zero_padded_to_four_digits(self):
        self.assertIn("http://publications.europa.eu/resource/celex/32022R0869",
                      celex_candidates_from_designation("(EU) 2022/869", "Nařízení EU"))

    def test_unknown_type_yields_no_candidates(self):
        self.assertEqual(celex_candidates_from_designation("(EU) 2023/2405", "Zákon"), [])
        self.assertEqual(celex_candidates_from_designation("(EU) 2023/2405", None), [])

    def test_designation_without_a_digit_pair_yields_nothing(self):
        self.assertEqual(celex_candidates_from_designation("ADR 2025", "Nařízení EU"), [])
        self.assertEqual(celex_candidates_from_designation("", "Nařízení EU"), [])


def _agent(uri):
    return {"value": f"http://publications.europa.eu/resource/authority/corporate-body/{uri}"}


class FetchResponsibleGestorTestCase(unittest.TestCase):
    def test_prefers_the_responsible_directorate_general(self):
        session = _fake_session([
            {"dg": _agent("ENER"), "agent": _agent("EP")},
            {"dg": _agent("ENER"), "agent": _agent("CONSIL")},
            {"label": {"value": "Generální ředitelství pro energetiku"}, "lang": {"value": "cs"}},
        ])
        got = fetch_responsible_gestor("https://eur-lex.europa.eu/eli/reg/2023/2405/oj", session=session)
        self.assertEqual(got, "Generální ředitelství pro energetiku")

    def test_a_dg_hiding_in_work_created_by_agent_is_still_found(self):
        # A Commission-only implementing act was found carrying its DG
        # only here, not in the "responsibility" property.
        session = _fake_session([
            {"agent": _agent("COM")},
            {"agent": _agent("ENV")},
            {"label": {"value": "Generální ředitelství pro životní prostředí"}, "lang": {"value": "cs"}},
        ])
        got = fetch_responsible_gestor("https://eur-lex.europa.eu/eli/dec_impl/2022/2427/oj", session=session)
        self.assertEqual(got, "Generální ředitelství pro životní prostředí")

    def test_co_decided_act_without_a_dg_names_both_legislators(self):
        session = _fake_session([{"agent": _agent("EP")}, {"agent": _agent("CONSIL")}])
        got = fetch_responsible_gestor("https://eur-lex.europa.eu/eli/dir/2019/692/oj", session=session)
        self.assertEqual(got, "Evropský parlament a Rada Evropské unie")

    def test_commission_only_act_without_a_dg_names_the_commission(self):
        session = _fake_session([{"agent": _agent("COM")}])
        got = fetch_responsible_gestor("https://eur-lex.europa.eu/eli/dec_impl/2013/732/oj", session=session)
        self.assertEqual(got, "Evropská komise")

    def test_no_cellar_match_returns_none(self):
        got = fetch_responsible_gestor("https://eur-lex.europa.eu/eli/reg/2023/1234/oj",
                                       session=_fake_session([]))
        self.assertIsNone(got)

    def test_url_with_no_reference_and_no_designation_returns_none(self):
        got = fetch_responsible_gestor("https://www.slov-lex.sk/pravne-predpisy/SK/ZZ/2010/75",
                                       session=_fake_session([]))
        self.assertIsNone(got)


class CelexSuffixTestCase(unittest.TestCase):
    """Regression guard, 2026-09-16: the trailing "(NN)" is part of the
    CELEX id, not noise. EUR-Lex uses it to separate acts that would
    otherwise share a number — Decision (EU) 2018/546 of the ECB is
    "32018D0010(01)", while the bare "32018D0010" is an unrelated
    Commission decision on Danish state aid. Dropping the suffix
    resolved that other act and put its title into the ECB record's
    `nazev_autoritativni`."""

    def test_parenthesised_suffix_is_kept(self):
        self.assertEqual(
            celex_from_url("https://eur-lex.europa.eu/legal-content/CS/TXT/PDF/?uri=CELEX:32018D0010(01)&qid=1751365968461"),
            "32018D0010(01)")

    def test_query_string_is_not_swallowed(self):
        self.assertEqual(
            celex_from_url("https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32014R1300&qid=99"),
            "32014R1300")

    def test_plain_celex_is_unaffected(self):
        self.assertEqual(
            celex_from_url("https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32022R0869"),
            "32022R0869")


class EliCandidatesFromDesignationTestCase(unittest.TestCase):
    """Cellar does not index every act under the CELEX its stored URL
    carries — the ECB decision above is reachable only as
    eli/dec/2018/546/oj — so the ELI is built as a further candidate."""

    def test_type_decides_the_eli_path_segment(self):
        self.assertIn("http://publications.europa.eu/resource/eli/dec/2018/546/oj",
                      eli_candidates_from_designation("(EU) 2018/546", "Rozhodnutí EU"))
        self.assertIn("http://publications.europa.eu/resource/eli/reg/2023/2405/oj",
                      eli_candidates_from_designation("(EU) 2023/2405", "Nařízení EU"))
        self.assertIn("http://publications.europa.eu/resource/eli/dir/2023/2413/oj",
                      eli_candidates_from_designation("(EU) 2023/2413", "Směrnice EU"))

    def test_sequence_number_is_not_zero_padded_in_an_eli(self):
        got = eli_candidates_from_designation("(EU) 2022/869", "Nařízení EU")
        self.assertIn("http://publications.europa.eu/resource/eli/reg/2022/869/oj", got)

    def test_unknown_type_or_no_digits_yields_nothing(self):
        self.assertEqual(eli_candidates_from_designation("(EU) 2018/546", "Zákon"), [])
        self.assertEqual(eli_candidates_from_designation("ADR 2025", "Rozhodnutí EU"), [])

if __name__ == "__main__":
    unittest.main()
