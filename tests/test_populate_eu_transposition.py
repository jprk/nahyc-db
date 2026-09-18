import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))

import populate_eu_transposition as pet  # noqa: E402

CZ_FOOTNOTE_HTML = """
<p class="L5"><a id="f2179919"></a><var>(1)</var> Zákon v souladu s právem Evropské unie<a class="linknote" href="#f4456505"><sup>1</sup>)</a> upravuje...</p>
<h4 class="VPPC L0"><a id="f4920103"><i id="poznamky"></i></a>Poznámky pod čarou</h4>
<p class="L1 PPC0"><a id="f4456505"><i id="pozn1"></i></a><var><sup>1</sup>)</var> Směrnice 2001/42/ES Evropského parlamentu a Rady ze dne 27. června 2001 o posuzování vlivů některých plánů a programů na životní prostředí.<br/>
Směrnice Evropského parlamentu a Rady 2011/92/EU ze dne 13. prosince 2011 o posuzování vlivů některých veřejných a soukromých záměrů na životní prostředí.</p>
<p class="L1 PPC0"><a id="f4456506"><i id="pozn1b"></i></a><var><sup>1b</sup>)</var> Zákon č. 17/1992 Sb., o životním prostředí.</p>
"""

CZ_NO_TRANSPOSITION_HTML = """
<h4 class="VPPC L0"><a id="f1"><i id="poznamky"></i></a>Poznámky pod čarou</h4>
<p class="L1 PPC0"><a id="f2"><i id="pozn1a"></i></a><var><sup>1a</sup>)</var> Něco jiného.</p>
"""

SK_ANNEX_HTML = """
<div> § 66 Týmto zákonom sa preberajú právne záväzné akty Európskej únie uvedené v prílohe č. 16 . </div>
<div>Príloha č. 16 k zákonu č. 24/2006 Z. z. ZOZNAM PREBERANÝCH PRÁVNE ZÁVÄZNÝCH AKTOV EURÓPSKEJ ÚNIE
1. Smernica Európskeho parlamentu a Rady 2001/42/ES z 27. júna 2001 o posudzovaní účinkov určitých plánov a programov na životné prostredie.
2. Smernica Európskeho parlamentu a Rady 2011/92/EÚ z 13. decembra 2011 o posudzovaní vplyvov určitých verejných a súkromných projektov.
</div>
<div>Poznámky 1) § 2 zákona č. 17/1992 Zb. o životnom prostredí.</div>
"""

SK_NO_TRANSPOSITION_HTML = """
<div>§ 10 Účinnosť tohto zákona nastáva dňom vyhlásenia.</div>
"""


class ClassifyCitationTypeTestCase(unittest.TestCase):
    def test_czech_keywords(self):
        self.assertEqual(pet.classify_citation_type("Směrnice Evropského parlamentu..."), "Směrnice EU")
        self.assertEqual(pet.classify_citation_type("Nařízení Rady (ES) č. 1/2003..."), "Nařízení EU")
        self.assertEqual(pet.classify_citation_type("Rozhodnutí Komise 2013/732/EU..."), "Rozhodnutí EU")

    def test_slovak_keywords(self):
        self.assertEqual(pet.classify_citation_type("Smernica Európskeho parlamentu..."), "Směrnice EU")
        self.assertEqual(pet.classify_citation_type("Nariadenie Európskeho parlamentu..."), "Nařízení EU")
        self.assertEqual(pet.classify_citation_type("Rozhodnutie Komisie..."), "Rozhodnutí EU")

    def test_unrecognized_or_empty_returns_none(self):
        self.assertIsNone(pet.classify_citation_type("Zákon č. 17/1992 Sb...."))
        self.assertIsNone(pet.classify_citation_type(""))
        self.assertIsNone(pet.classify_citation_type(None))


class ExpandTwoDigitYearTestCase(unittest.TestCase):
    def test_expands_pre_2000_style_citation(self):
        self.assertEqual(pet.expand_two_digit_year("Směrnice Rady 85/337/EHS ze dne..."),
                          "Směrnice Rady 1985/337/EHS ze dne...")

    def test_leaves_four_digit_year_untouched(self):
        text = "Směrnice Evropského parlamentu a Rady 2011/92/EU ze dne..."
        self.assertEqual(pet.expand_two_digit_year(text), text)

    def test_leaves_unrelated_two_digit_pairs_untouched(self):
        # No EU-act-type suffix right after the digit pair -> not touched.
        self.assertEqual(pet.expand_two_digit_year("§ 85/2001 something"), "§ 85/2001 something")


CZ_FOOTNOTE_EMBEDDED_HTML = """
<h4 class="VPPC L0"><a id="f1"><i id="poznamky"></i></a>Poznámky pod čarou</h4>
<p class="L1 PPC0"><a id="f2"><i id="pozn1"></i></a><var><sup>1</sup>)</var> Směrnice Rady 90/270/EHS ze dne 29. května 1990 o minimálních požadavcích (pátá samostatná směrnice ve smyslu čl. 16 odst. 1 směrnice 89/391/EHS). Směrnice Rady 92/57/EHS ze dne 24. června 1992 o minimálních požadavcích na staveništích.</p>
"""


class ExpandTwoDigitYearBothOrderingsTestCase(unittest.TestCase):
    def test_expands_number_first_year_last_ordering(self):
        self.assertEqual(
            pet.expand_two_digit_year("Rozhodnutí Evropského parlamentu a Rady č. 2119/98/ES ze dne..."),
            "Rozhodnutí Evropského parlamentu a Rady č. 2119/1998/ES ze dne...")

    def test_still_expands_year_first_ordering(self):
        self.assertEqual(pet.expand_two_digit_year("Směrnice Rady 85/337/EHS ze dne..."),
                          "Směrnice Rady 1985/337/EHS ze dne...")

    def test_regression_modern_year_first_short_number_is_never_touched(self):
        # "2001/42/ES" is already YYYY/NN (year first, NN a short
        # sequence number) -- must NOT be misread as a "number/2-digit-
        # year" citation and corrupted into "2001/1942/ES". Found live,
        # doc/PLAN.md §38: an earlier version of this expansion broke
        # this real, previously-working citation.
        text = "Směrnice 2001/42/ES Evropského parlamentu a Rady ze dne 27. června 2001 o..."
        self.assertEqual(pet.expand_two_digit_year(text), text)


class DesignationTextForResolutionTestCase(unittest.TestCase):
    def test_prefers_trailing_bare_designation_over_earlier_cross_reference(self):
        text = ("Směrnice Rady ze dne 30. listopadu 1989 o minimálních požadavcích (třetí samostatná "
                "směrnice ve smyslu čl. 16 odst. 1 směrnice 89/391/EHS) (89/656/EHS).")
        self.assertEqual(pet.designation_text_for_resolution(text), "89/656/EHS")

    def test_no_trailing_bare_designation_returns_text_unchanged(self):
        text = "Směrnice 2001/42/ES Evropského parlamentu a Rady ze dne 27. června 2001 o..."
        self.assertEqual(pet.designation_text_for_resolution(text), text)


class ExtractCzFootnote1ItemsTestCase(unittest.TestCase):
    def test_two_citations_glued_in_one_line_are_split(self):
        items = pet.extract_cz_footnote1_items(CZ_FOOTNOTE_EMBEDDED_HTML)
        self.assertEqual(items, [
            "Směrnice Rady 90/270/EHS ze dne 29. května 1990 o minimálních požadavcích (pátá samostatná "
            "směrnice ve smyslu čl. 16 odst. 1 směrnice 89/391/EHS).",
            "Směrnice Rady 92/57/EHS ze dne 24. června 1992 o minimálních požadavcích na staveništích.",
        ])

    def test_extracts_exactly_footnote_one_items(self):
        items = pet.extract_cz_footnote1_items(CZ_FOOTNOTE_HTML)
        self.assertEqual(items, [
            "Směrnice 2001/42/ES Evropského parlamentu a Rady ze dne 27. června 2001 o posuzování vlivů "
            "některých plánů a programů na životní prostředí.",
            "Směrnice Evropského parlamentu a Rady 2011/92/EU ze dne 13. prosince 2011 o posuzování vlivů "
            "některých veřejných a soukromých záměrů na životní prostředí.",
        ])

    def test_footnote_1b_is_never_picked_up_as_footnote_1(self):
        items = pet.extract_cz_footnote1_items(CZ_NO_TRANSPOSITION_HTML)
        self.assertEqual(items, [])

    def test_no_footnotes_section_at_all_returns_empty_list(self):
        self.assertEqual(pet.extract_cz_footnote1_items("<p>no footnotes here</p>"), [])
        self.assertEqual(pet.extract_cz_footnote1_items(""), [])


class ExtractSkAnnexItemsTestCase(unittest.TestCase):
    def test_extracts_annex_items_stopping_before_footnotes(self):
        items = pet.extract_sk_annex_items(SK_ANNEX_HTML)
        self.assertEqual(items, [
            "Smernica Európskeho parlamentu a Rady 2001/42/ES z 27. júna 2001 o posudzovaní účinkov "
            "určitých plánov a programov na životné prostredie.",
            "Smernica Európskeho parlamentu a Rady 2011/92/EÚ z 13. decembra 2011 o posudzovaní vplyvov "
            "určitých verejných a súkromných projektov.",
        ])

    def test_no_cross_reference_returns_empty_list(self):
        self.assertEqual(pet.extract_sk_annex_items(SK_NO_TRANSPOSITION_HTML), [])
        self.assertEqual(pet.extract_sk_annex_items(""), [])


class ExtractDateSignalTestCase(unittest.TestCase):
    def test_extracts_and_translates_slovak_month(self):
        self.assertEqual(
            pet.extract_date_signal("Smernica Rady 2009/31/ES z 23. apríla 2009 o..."),
            ("23", "dubna", "2009"))

    def test_leaves_czech_month_as_is(self):
        self.assertEqual(
            pet.extract_date_signal("Směrnice Rady 2009/31/ES ze dne 23. dubna 2009 o..."),
            ("23", "dubna", "2009"))

    def test_no_date_in_text_returns_none(self):
        self.assertIsNone(pet.extract_date_signal("Nařízení (EU) 2022/869"))


class TitleMatchesDateTestCase(unittest.TestCase):
    def test_matching_date_passes(self):
        self.assertTrue(pet.title_matches_date(
            "Směrnice ... ze dne 7. července 2021 o...", ("7", "července", "2021")))

    def test_mismatched_date_fails(self):
        self.assertFalse(pet.title_matches_date(
            "Nařízení Komise (EU) č. 92/2011 ze dne 3. února 2011 ...", ("13", "prosince", "2011")))

    def test_no_date_signal_never_blocks(self):
        self.assertTrue(pet.title_matches_date("anything at all", None))


class ResolveCitationsTestCase(unittest.TestCase):
    """`resolve_eu_act_by_designation` itself is mocked here — its own
    Cellar-query behavior is tested in test_sites_eurlex.py. This is
    about the ORCHESTRATION: primary type first, fallback only accepted
    if the date matches, never accepted otherwise."""

    def test_primary_type_match_is_used_first(self):
        with patch.object(pet, "resolve_eu_act_by_designation") as mock_resolve:
            mock_resolve.return_value = {
                "title": "Směrnice ... ze dne 13. prosince 2011 o...", "url": "https://eur-lex.europa.eu/eli/dir/2011/92/oj"}
            resolved, unresolved = pet.resolve_citations(
                ["Směrnice Evropského parlamentu a Rady 2011/92/EU ze dne 13. prosince 2011 o..."],
                session=None)
            self.assertEqual(len(resolved), 1)
            self.assertEqual(unresolved, [])
            # only the primary type ("Směrnice EU") should have been tried
            self.assertEqual(mock_resolve.call_count, 1)
            self.assertEqual(mock_resolve.call_args.args[1], "Směrnice EU")

    def test_fallback_type_accepted_only_when_date_matches(self):
        # Primary type ("Směrnice EU") resolves to nothing; the fallback
        # ("Nařízení EU") resolves but to a DIFFERENT act's date -> must
        # be rejected, not silently accepted on digit-pair coincidence.
        def fake_resolve(text, type_name, session=None):
            if type_name == "Nařízení EU":
                return {"title": "Nařízení Komise (EU) č. 92/2011 ze dne 3. února 2011 o sýru",
                        "url": "https://eur-lex.europa.eu/eli/reg/2011/92/oj"}
            return None

        with patch.object(pet, "resolve_eu_act_by_designation", side_effect=fake_resolve):
            resolved, unresolved = pet.resolve_citations(
                ["Směrnice Evropského parlamentu a Rady 2011/92/EU ze dne 13. prosince 2011 o životním prostředí"],
                session=None)
            self.assertEqual(resolved, [])
            self.assertEqual(len(unresolved), 1)

    def test_fallback_type_accepted_when_date_matches(self):
        # Real case found live (doc/PLAN.md §38): Regulation (EU)
        # 2021/1187's own title literally starts with "Směrnice", but it
        # only resolves under the "Nařízení EU"/reg ELI path -- accepted
        # here because the date matches.
        def fake_resolve(text, type_name, session=None):
            if type_name == "Nařízení EU":
                return {"title": "Směrnice Evropského parlamentu a Rady (EU) 2021/1187 ze dne 7. července 2021 o...",
                        "url": "https://eur-lex.europa.eu/eli/reg/2021/1187/oj"}
            return None

        with patch.object(pet, "resolve_eu_act_by_designation", side_effect=fake_resolve):
            resolved, unresolved = pet.resolve_citations(
                ["Smernica Európskeho parlamentu a Rady (EÚ) 2021/1187 zo 7. júla 2021 o..."],
                session=None)
            self.assertEqual(len(resolved), 1)
            self.assertEqual(unresolved, [])

    def test_nothing_resolves_is_reported_as_unresolved(self):
        with patch.object(pet, "resolve_eu_act_by_designation", return_value=None):
            resolved, unresolved = pet.resolve_citations(["Směrnice 9999/9999/EU o ničem"], session=None)
            self.assertEqual(resolved, [])
            self.assertEqual(unresolved, ["Směrnice 9999/9999/EU o ničem"])


class BuildCacheEntryTestCase(unittest.TestCase):
    def test_no_raw_items_is_no_transposition(self):
        entry = pet.build_cache_entry([], [], [], "zakonyprolidi.cz")
        self.assertEqual(entry, {"status": "no_transposition", "domain": "zakonyprolidi.cz"})

    def test_raw_items_but_nothing_resolved_is_unresolved_status(self):
        entry = pet.build_cache_entry([], ["Směrnice X"], ["Směrnice X"], "zakonyprolidi.cz")
        self.assertEqual(entry["status"], "unresolved")
        self.assertEqual(entry["raw_items"], ["Směrnice X"])

    def test_resolved_items_are_joined_by_newline(self):
        resolved = [{"title": "A", "url": "u1"}, {"title": "B", "url": "u2"}]
        entry = pet.build_cache_entry(resolved, [], ["raw a", "raw b"], "slov-lex.sk")
        self.assertEqual(entry["status"], "fetched")
        self.assertEqual(entry["nazev_eu"], "A\nB")
        self.assertEqual(entry["odkaz_eu"], "u1\nu2")


class IsTargetRecordTestCase(unittest.TestCase):
    def test_law_type_without_eu_fields_is_a_target(self):
        self.assertTrue(pet.is_target_record({"typ_dokumentu": "Zákon", "nazev_eu": "", "odkaz_eu": ""}))

    def test_already_populated_is_not_a_target(self):
        self.assertFalse(pet.is_target_record(
            {"typ_dokumentu": "Zákon", "nazev_eu": "Something", "odkaz_eu": ""}))

    def test_norm_type_is_never_a_target(self):
        self.assertFalse(pet.is_target_record({"typ_dokumentu": "Norma", "nazev_eu": "", "odkaz_eu": ""}))


if __name__ == "__main__":
    unittest.main()
