import pathlib
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from sites.eurlex import (cellar_language, fetch_cellar, fetch_cellar_document, resolve_celex,
                          celex_candidates_from_designation, celex_from_url,
                          eli_candidates_from_designation, extract,
                          fetch_responsible_gestor, resolve_eu_act_by_designation,
                          resource_uris_from_text)


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

class ResolveEuActByDesignationTestCase(unittest.TestCase):
    """doc/PLAN.md §38, 2026-09-18: resolving a national law's own free-
    text EU-transposition citation (not a stored corpus URL) against
    Cellar, by ELI."""

    def test_resolves_via_first_matching_eli_candidate(self):
        session = _fake_session([_binding("CES", "Směrnice 2011/92/EU")])
        got = resolve_eu_act_by_designation(
            "Směrnice Evropského parlamentu a Rady 2011/92/EU ze dne 13. prosince 2011",
            "Směrnice EU", session=session)
        self.assertEqual(got, {"title": "Směrnice 2011/92/EU",
                                "url": "https://eur-lex.europa.eu/eli/dir/2011/92/oj"})

    def test_no_bindings_at_all_returns_none(self):
        session = _fake_session([])
        got = resolve_eu_act_by_designation("2011/92", "Směrnice EU", session=session)
        self.assertIsNone(got)

    def test_unknown_type_returns_none_without_querying(self):
        session = _fake_session([_binding("CES", "Should never be returned")])
        got = resolve_eu_act_by_designation("2011/92", "Zákon", session=session)
        self.assertIsNone(got)
        session.get.assert_not_called()


class CellarDocumentTestCase(unittest.TestCase):
    """The text of an act from Cellar instead of EUR-Lex, which answers automated
    clients with a firewall challenge (doc/MPO_PRIPOMINKY.md, 2026-11-19)."""

    def response(self, status, text="", content=b"", content_type="application/xhtml+xml"):
        resp = MagicMock()
        resp.status_code, resp.text, resp.content = status, text, content
        resp.headers = {"Content-Type": content_type}
        return resp

    def test_the_language_comes_from_the_address(self):
        self.assertEqual(cellar_language("https://eur-lex.europa.eu/legal-content/SK/TXT/?uri=CELEX:52020DC0301"), "slk")
        self.assertEqual(cellar_language("https://eur-lex.europa.eu/eli/reg/2008/1272/oj/ces"), "ces")
        self.assertEqual(cellar_language("https://eur-lex.europa.eu/eli/reg/2008/1272/oj"), "eng")

    def test_the_main_item_of_a_multiple_choice_answer_is_downloaded(self):
        session = MagicMock()
        listing = '<a href="http://publications.europa.eu/resource/cellar/abc.0024.03/DOC_1">x</a>'
        session.get.side_effect = [self.response(300, text=listing), self.response(200, content=b"<html/>")]
        status, content, _ = fetch_cellar_document(
            "https://eur-lex.europa.eu/legal-content/CS/TXT/?uri=CELEX:52022DC0230", session=session)
        self.assertEqual((status, content), (200, b"<html/>"))
        first, second = session.get.call_args_list
        self.assertEqual(first.args[0], "http://publications.europa.eu/resource/celex/52022DC0230")
        self.assertEqual(first.kwargs["headers"]["Accept-Language"], "ces")
        self.assertEqual(second.args[0], "http://publications.europa.eu/resource/cellar/abc.0024.03/DOC_1")

    def test_a_pdf_address_asks_for_a_pdf_and_a_celex_suffix_is_encoded(self):
        session = MagicMock()
        session.get.return_value = self.response(200, content=b"%PDF-", content_type="application/pdf;type=pdfa1a")
        fetch_cellar_document("https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:42015X0331(01)",
                              session=session)
        call = session.get.call_args
        self.assertEqual(call.args[0], "http://publications.europa.eu/resource/celex/42015X0331%2801%29")
        self.assertTrue(call.kwargs["headers"]["Accept"].startswith("application/pdf"))

    def test_an_address_without_an_act_asks_nothing(self):
        session = MagicMock()
        self.assertIsNone(fetch_cellar_document(
            "https://eur-lex.europa.eu/legal-content/CS/TXT/PDF/?uri=OJ:L:2014:096:FULL", session=session))
        session.get.assert_not_called()

    def sparql(self, *numbers):
        resp = MagicMock()
        resp.json.return_value = {"results": {"bindings": [
            {"celex": {"value": n}} for n in numbers]}}
        resp.raise_for_status.return_value = None
        return resp

    def test_an_eli_is_resolved_to_its_celex_through_cellar(self):
        session = MagicMock()
        session.get.return_value = self.sparql("32008R1272")
        self.assertEqual(resolve_celex("https://eur-lex.europa.eu/eli/reg/2008/1272/oj/ces", session), "32008R1272")
        query = session.get.call_args.kwargs["params"]["query"]
        self.assertIn("<http://publications.europa.eu/resource/eli/reg/2008/1272/oj>", query)

    def test_an_official_journal_id_is_resolved_too(self):
        session = MagicMock()
        session.get.return_value = self.sparql("32023L2413")
        self.assertEqual(resolve_celex(
            "https://eur-lex.europa.eu/legal-content/CS/TXT/HTML/?uri=OJ:L_202302413", session), "32023L2413")
        self.assertIn("<http://publications.europa.eu/resource/oj/L_202302413>",
                      session.get.call_args.kwargs["params"]["query"])

    def test_a_consolidated_version_is_not_taken_for_the_act(self):
        session = MagicMock()
        session.get.return_value = self.sparql("32018R0858", "02018R0858-20240101")
        self.assertEqual(resolve_celex("https://eur-lex.europa.eu/eli/reg/2018/858/oj", session), "32018R0858")

    def test_a_consolidated_version_keeps_its_date(self):
        self.assertEqual(resolve_celex(
            "https://eur-lex.europa.eu/legal-content/CS/TXT/PDF/?uri=CELEX:02022R0869-20250205", MagicMock()),
            "02022R0869-20250205")

    def test_an_eli_cellar_has_not_linked_is_accepted_only_with_its_number_in_the_title(self):
        session = MagicMock()
        title = MagicMock()
        title.raise_for_status.return_value = None
        title.json.return_value = {"results": {"bindings": [
            {"title": {"value": "Nařízení Komise v přenesené pravomoci (EU) 2021/535 ze dne"}, "lang": {"value": "CES"}}]}}
        session.get.side_effect = [self.sparql(), title]
        self.assertEqual(resolve_celex("https://eur-lex.europa.eu/eli/reg/2021/535/oj/ces", session), "32021R0535")
        session.get.side_effect = [self.sparql(), self.sparql()]
        self.assertIsNone(resolve_celex("https://eur-lex.europa.eu/eli/reg/2021/535/oj/ces", session))

    def test_two_acts_for_one_address_are_not_guessed(self):
        session = MagicMock()
        session.get.side_effect = [self.sparql("32018R0858", "32018R0858R(01)"), self.sparql()]
        self.assertIsNone(resolve_celex("https://eur-lex.europa.eu/eli/reg/2018/858/oj", session))

    def test_an_eli_is_downloaded_from_cellar_in_its_language(self):
        session = MagicMock()
        session.get.side_effect = [self.sparql("32014L0094"), self.response(200, content=b"<html/>")]
        found = fetch_cellar("https://eur-lex.europa.eu/eli/dir/2014/94/oj/ces", session=session)
        self.assertEqual((found["celex"], found["content"], found["items"]), ("32014L0094", b"<html/>", 1))
        download = session.get.call_args_list[1]
        self.assertEqual(download.args[0], "http://publications.europa.eu/resource/celex/32014L0094")
        self.assertEqual(download.kwargs["headers"]["Accept-Language"], "ces")
        for call in session.get.call_args_list:
            self.assertNotIn("eur-lex.europa.eu", call.args[0])

    def test_items_of_a_multiple_choice_answer_are_counted(self):
        session = MagicMock()
        listing = ('<a href="http://publications.europa.eu/resource/cellar/abc.0024.03/DOC_1">x</a>'
                   '<a href="http://publications.europa.eu/resource/cellar/abc.0024.03/DOC_2">y</a>')
        session.get.side_effect = [self.response(300, text=listing), self.response(200, content=b"%PDF-")]
        found = fetch_cellar("https://eur-lex.europa.eu/legal-content/CS/TXT/PDF/?uri=CELEX:32008R1272",
                             session=session)
        self.assertEqual(found["items"], 2)


if __name__ == "__main__":
    unittest.main()
