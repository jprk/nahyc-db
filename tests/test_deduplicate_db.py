import pathlib
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))

import deduplicate_db as dedup


def make_record(nazev_cz="", znacka="", **extra):
    record = {
        "zdroj_dat": extra.pop("zdroj_dat", "Test_Source"),
        "nazev_cz": nazev_cz,
        "znacka": znacka,
        "typ_dokumentu": "", "sekce": "", "kategorie_trida": "",
        "klicova_slova": [], "odkaz_hlavni": "", "nazev_eu": "", "odkaz_eu": "",
        "nazev_sk": "", "odkaz_sk": "", "platnost": "", "ratifikovan": "",
        "gestor": [], "jazyk": "", "anotace_poznamka": "",
    }
    record.update(extra)
    return record


class NormalizeAndCoreZnackaTestCase(unittest.TestCase):
    def test_normalize_collapses_whitespace_and_case(self):
        self.assertEqual(dedup.normalize_znacka("  ČSN   EN  17127 "), "čsn en 17127")
        self.assertEqual(dedup.normalize_znacka(""), "")
        self.assertEqual(dedup.normalize_znacka(None), "")

    def test_normalize_folds_dash_variants_to_a_plain_hyphen(self):
        # The Sinay PDF source uses "-" and "–" (en dash) interchangeably
        # for the same date separator — without folding, these silently
        # defeat exact-match deduplication (found in a real run,
        # doc/PLAN.md Step 1 follow-up #9).
        self.assertEqual(
            dedup.normalize_znacka("STN EN ISO 11114-1/ – 2020.12"),
            dedup.normalize_znacka("STN EN ISO 11114-1/ - 2020.12"),
        )

    def test_normalize_strips_trailing_edition_date_suffix(self):
        # A real, previously-missed duplicate: "ISO 16111" (already
        # merged) and "ISO 16111/ - 2018.08" (still raw Sinay form) are
        # the same standard — the Sinay parser doesn't always keep the
        # edition-date suffix, so it must be normalized away for exact
        # match, not just the dash variant it's written with.
        self.assertEqual(dedup.normalize_znacka("ISO 16111/ - 2018.08"),
                          dedup.normalize_znacka("ISO 16111"))
        self.assertEqual(dedup.normalize_znacka("ISO 16111/ – 2018.08"),
                          dedup.normalize_znacka("ISO 16111"))

    def test_normalize_does_not_strip_a_bare_trailing_year(self):
        # Some real znacka values legitimately end in a bare year (e.g.
        # "ADR 2025") -- only a "/ - YYYY.MM" edition-date suffix (with
        # the month component) should be stripped, never a bare year.
        self.assertEqual(dedup.normalize_znacka("ADR 2025"), "adr 2025")

    def test_normalize_keeps_amendment_marker_before_the_date(self):
        # A base standard and its amendment must NOT become
        # indistinguishable just because the date suffix is stripped --
        # that merge decision is deliberately deferred (doc/PLAN.md).
        base = dedup.normalize_znacka("STN EN 13445-2/ – 2021.08")
        amendment = dedup.normalize_znacka("STN EN 13445-2+A1/ - 2024.02")
        self.assertNotEqual(base, amendment)
        self.assertEqual(amendment, "stn en 13445-2+a1")

    def test_normalize_strips_bare_colon_year_suffix(self):
        # A rarer edition-year style found in the corpus: "ISO 11413 :2019"
        # (bare colon-year, no month) vs. "ISO 11413/ - 2019.03" (the more
        # common Sinay "/ - YYYY.MM" form) -- same standard either way.
        self.assertEqual(dedup.normalize_znacka("ISO 11413 :2019"),
                          dedup.normalize_znacka("ISO 11413/ - 2019.03"))

    def test_normalize_does_not_strip_a_2_digit_year_part_citation(self):
        # "CHMC 2:19" and "CSA HPIT 1:15 (R2020)" use "part:2-digit-year"
        # as their OWN citation convention -- must not be confused with
        # the 4-digit bare colon-year edition suffix above.
        self.assertEqual(dedup.normalize_znacka("CHMC 2:19"), "chmc 2:19")
        self.assertEqual(dedup.normalize_znacka("CSA HPIT 1:15 (R2020)"),
                          "csa hpit 1:15 (r2020)")

    def test_normalize_strips_sae_style_colon_year_dash_month_suffix(self):
        # A third edition-date suffix style, found on SAE designations:
        # "SAE J2601: 2020-05" vs. the bare "SAE J2601" -- same standard
        # (see doc/PLAN.md Step 1 follow-up #13, SAE research).
        self.assertEqual(dedup.normalize_znacka("SAE J2601: 2020-05"),
                          dedup.normalize_znacka("SAE J2601"))
        self.assertEqual(dedup.normalize_znacka("SAE J2600: 2015-10"),
                          dedup.normalize_znacka("SAE J2600"))

    def test_normalize_folds_known_series_separator_variants(self):
        # "CSA/ANSI" vs "CSA ANSI" and "IGEM/TD/1" vs "IGEM TD1" are the
        # same document series, just written with a "/" vs. " " vs. no
        # separator at all -- a real duplicate-title case found by
        # auditing the corpus (doc/PLAN.md Step 1 follow-up #11).
        self.assertEqual(dedup.normalize_znacka("CSA/ANSI HGV 2"),
                          dedup.normalize_znacka("CSA ANSI HGV 2"))
        self.assertEqual(dedup.normalize_znacka("IGEM/TD/1 Edition 6"),
                          dedup.normalize_znacka("IGEM TD1 Edition 6"))

    def test_normalize_does_not_fold_unrelated_slash_designations(self):
        # The known-series fold is a narrow allowlist, not a blanket
        # "remove every slash" rule -- "STN CLC/TR ..." vs "TNI CLC/TR
        # ..." are a genuinely different, unresolved question (deferred,
        # not the same fix) and must not be silently conflated.
        self.assertNotEqual(dedup.normalize_znacka("STN CLC/TR 60079-32-1"),
                             dedup.normalize_znacka("TNI CLC/TR 60079-32-1"))

    def test_normalize_folds_eiga_igc_doc_alias_for_the_same_edition(self):
        # EIGA's former name was IGC (International Gases Committee) --
        # "EIGA 121/14" and "IGC Doc 121/14" are the same 2014 edition,
        # just cited under the old vs. new org name (doc/PLAN.md Step 1
        # follow-up #14).
        self.assertEqual(dedup.normalize_znacka("EIGA 121/14"),
                          dedup.normalize_znacka("IGC Doc 121/14"))

    def test_normalize_does_not_fold_different_editions_of_the_same_code(self):
        # "EIGA Doc 6/19/E" (2019) vs "IGC Doc 6/02/E" (2002) are
        # DIFFERENT editions of the same underlying code, not just a
        # renamed org -- only the prefix is folded, so a genuinely
        # different edition suffix must still compare unequal.
        self.assertNotEqual(dedup.normalize_znacka("EIGA Doc 6/19/E"),
                             dedup.normalize_znacka("IGC Doc 6/02/E"))

    def test_core_strips_csn_prefix_only(self):
        self.assertEqual(dedup.core_znacka("ČSN EN 17127"), "en 17127")
        self.assertEqual(dedup.core_znacka("EN 17127"), "en 17127")
        # Does NOT strip "EN " — that ambiguity is handled by the ČSN
        # registry check (resolve_iso_csn_ambiguity), not core_znacka.
        self.assertEqual(dedup.core_znacka("ČSN ISO 14687"), "iso 14687")
        self.assertNotEqual(dedup.core_znacka("ČSN EN ISO 14687"), dedup.core_znacka("ČSN ISO 14687"))

    def test_digit_core_extracts_bare_number(self):
        self.assertEqual(dedup.digit_core("ČSN EN ISO 19880-1"), "19880-1")
        self.assertEqual(dedup.digit_core("ISO 14687"), "14687")
        self.assertEqual(dedup.digit_core(""), "")
        self.assertEqual(dedup.digit_core("RID"), "")


class ValidateMergeTestCase(unittest.TestCase):
    def test_accepts_a_faithful_merge(self):
        inputs = [make_record(znacka="ČSN EN 17127"), make_record(znacka="EN 17127")]
        merged = [make_record(znacka="ČSN EN 17127")]
        valid, reason = dedup.validate_merge(inputs, merged)
        self.assertTrue(valid)
        self.assertIsNone(reason)

    def test_rejects_an_invented_znacka(self):
        inputs = [make_record(znacka="ČSN EN 17127")]
        merged = [make_record(znacka="ČSN EN 99999")]
        valid, reason = dedup.validate_merge(inputs, merged)
        self.assertFalse(valid)
        self.assertIn("invented", reason)

    def test_rejects_the_same_znacka_split_across_outputs(self):
        inputs = [make_record(znacka="2012/18/EU"), make_record(znacka="2012/18/EU")]
        merged = [make_record(nazev_cz="CZ version", znacka="2012/18/EU"),
                  make_record(nazev_cz="EN version", znacka="2012/18/EU")]
        valid, reason = dedup.validate_merge(inputs, merged)
        self.assertFalse(valid)
        self.assertIn("split across multiple output records", reason)

    def test_records_with_no_znacka_never_trigger_either_check(self):
        inputs = [make_record(), make_record()]
        merged = [make_record(), make_record()]
        valid, reason = dedup.validate_merge(inputs, merged)
        self.assertTrue(valid)


class IsPureZnackaClusterTestCase(unittest.TestCase):
    def test_true_when_all_share_the_same_core(self):
        records = [make_record(znacka="ČSN EN 17127"), make_record(znacka="EN 17127")]
        self.assertTrue(dedup.is_pure_znacka_cluster(records))

    def test_false_when_any_record_has_no_znacka(self):
        records = [make_record(znacka="EN 17127"), make_record(znacka="")]
        self.assertFalse(dedup.is_pure_znacka_cluster(records))

    def test_false_when_cores_differ(self):
        records = [make_record(znacka="EN 17127"), make_record(znacka="EN 17339")]
        self.assertFalse(dedup.is_pure_znacka_cluster(records))

    def test_false_when_known_jurisdictions_conflict_despite_same_core(self):
        records = [make_record(znacka="EN 17124", jurisdikce="CZ"),
                   make_record(znacka="EN 17124", jurisdikce="SK")]
        self.assertFalse(dedup.is_pure_znacka_cluster(records))

    def test_true_when_one_side_has_unknown_jurisdiction(self):
        records = [make_record(znacka="EN 17124", jurisdikce="CZ"),
                   make_record(znacka="EN 17124", jurisdikce="")]
        self.assertTrue(dedup.is_pure_znacka_cluster(records))


class ProgrammaticMergeTestCase(unittest.TestCase):
    def test_picks_longest_title_and_unions_list_fields(self):
        records = [
            make_record(nazev_cz="EN 17127", znacka="EN 17127", zdroj_dat="Haltuf_Dokumenty",
                        klicova_slova=["vodík"], gestor=["MPO"]),
            make_record(nazev_cz="ČSN EN 17127 (697280) Delší a úplnější název normy", znacka="ČSN EN 17127",
                        zdroj_dat="Prokop_Normy", klicova_slova=["čerpací stanice"], gestor=["MPO", "MŽP"]),
        ]
        merged = dedup.programmatic_merge(records)
        self.assertEqual(merged["nazev_cz"], "ČSN EN 17127 (697280) Delší a úplnější název normy")
        self.assertEqual(set(merged["klicova_slova"]), {"vodík", "čerpací stanice"})
        self.assertEqual(set(merged["gestor"]), {"MPO", "MŽP"})
        self.assertIn("Haltuf_Dokumenty", merged["zdroj_dat"])
        self.assertIn("Prokop_Normy", merged["zdroj_dat"])

    def test_prefers_csn_prefixed_znacka_variant(self):
        records = [make_record(znacka="EN 17127"), make_record(znacka="ČSN EN 17127")]
        merged = dedup.programmatic_merge(records)
        self.assertEqual(merged["znacka"], "ČSN EN 17127")

    def test_backfills_blank_scalar_fields_from_any_member(self):
        records = [
            make_record(nazev_cz="Norma A" * 3, znacka="X", platnost=""),
            make_record(nazev_cz="Norma", znacka="X", platnost="od 1.1.2020"),
        ]
        merged = dedup.programmatic_merge(records)
        self.assertEqual(merged["platnost"], "od 1.1.2020")

    def test_drops_internal_clustering_keys(self):
        records = [make_record(znacka="X", _search_text="x", _embedding=[0.1])]
        merged = dedup.programmatic_merge(records)
        self.assertNotIn("_search_text", merged)
        self.assertNotIn("_embedding", merged)


class MatchTypeForGroupTestCase(unittest.TestCase):
    def test_deterministic_when_core_znacka_repeats(self):
        records = [make_record(znacka="EN 17127"), make_record(znacka="ČSN EN 17127")]
        self.assertEqual(dedup.match_type_for_group(records), "deterministic")

    def test_semantic_when_multiple_records_without_a_shared_znacka(self):
        records = [make_record(znacka=""), make_record(znacka="")]
        self.assertEqual(dedup.match_type_for_group(records), "semantic")

    def test_none_for_a_singleton(self):
        self.assertEqual(dedup.match_type_for_group([make_record()]), "none")


class BuildClustersTestCase(unittest.TestCase):
    """Uses hand-picked embeddings (identical => similarity 1.0, orthogonal
    => similarity 0.0) rather than real OpenAI vectors, so clustering logic
    is tested without any network dependency."""

    IDENTICAL_A = [1.0, 0.0]
    IDENTICAL_B = [1.0, 0.0]
    ORTHOGONAL = [0.0, 1.0]

    @staticmethod
    def _clusters_as_sets(clusters):
        return {frozenset(c) for c in clusters}

    def test_same_znacka_unions_despite_dissimilar_titles(self):
        data = [
            make_record(znacka="2012/18/EU", _embedding=self.IDENTICAL_A),
            make_record(znacka="2012/18/EU", _embedding=self.ORTHOGONAL),
        ]
        clusters = dedup.build_clusters(data)
        self.assertEqual(self._clusters_as_sets(clusters), {frozenset({0, 1})})

    def test_different_znacka_vetoes_even_identical_embeddings(self):
        data = [
            make_record(znacka="ČSN EN 62282-3-300", _embedding=self.IDENTICAL_A),
            make_record(znacka="ČSN EN 62282-3-200", _embedding=self.IDENTICAL_B),
        ]
        clusters = dedup.build_clusters(data)
        self.assertEqual(self._clusters_as_sets(clusters), {frozenset({0}), frozenset({1})})

    def test_no_znacka_falls_back_to_semantic_similarity(self):
        data = [
            make_record(znacka="", _embedding=self.IDENTICAL_A),
            make_record(znacka="", _embedding=self.IDENTICAL_B),
            make_record(znacka="", _embedding=self.ORTHOGONAL),
        ]
        clusters = dedup.build_clusters(data, similarity_threshold=0.85)
        self.assertEqual(self._clusters_as_sets(clusters), {frozenset({0, 1}), frozenset({2})})

    def test_one_sided_znacka_does_not_veto_a_semantic_match(self):
        # Only one of the two records has a znacka at all — the veto only
        # applies when BOTH sides have a non-empty, differing znacka.
        data = [
            make_record(znacka="EN 17127", _embedding=self.IDENTICAL_A),
            make_record(znacka="", _embedding=self.IDENTICAL_B),
        ]
        clusters = dedup.build_clusters(data)
        self.assertEqual(self._clusters_as_sets(clusters), {frozenset({0, 1})})

    def test_matching_core_znacka_but_conflicting_jurisdiction_stays_separate(self):
        # E.g. a Czech ČSN and a Slovak STN adoption of the same EN
        # standard — same core znacka, but legally distinct documents.
        # This is the exact scenario doc/PLAN.md Step 1 follow-up #8
        # exists to prevent (a bare foreign "EN 17124" reference sharing
        # its core with a Czech "ČSN EN 17124" is the realistic case —
        # core_znacka doesn't strip "STN ", so this exercises the veto
        # directly against a shared core rather than via a real STN string).
        data = [
            make_record(znacka="EN 17124", jurisdikce="CZ", _embedding=self.IDENTICAL_A),
            make_record(znacka="EN 17124", jurisdikce="SK", _embedding=self.IDENTICAL_B),
        ]
        clusters = dedup.build_clusters(data)
        self.assertEqual(self._clusters_as_sets(clusters), {frozenset({0}), frozenset({1})})

    def test_three_records_same_core_split_into_two_jurisdiction_islands(self):
        data = [
            make_record(znacka="EN 17124", jurisdikce="CZ", _embedding=self.IDENTICAL_A),
            make_record(znacka="EN 17124", jurisdikce="CZ", _embedding=self.IDENTICAL_B),
            make_record(znacka="EN 17124", jurisdikce="SK", _embedding=self.ORTHOGONAL),
        ]
        clusters = dedup.build_clusters(data)
        self.assertEqual(self._clusters_as_sets(clusters), {frozenset({0, 1}), frozenset({2})})

    def test_unknown_jurisdiction_does_not_veto_a_same_core_match(self):
        data = [
            make_record(znacka="EN 17124", jurisdikce="CZ", _embedding=self.IDENTICAL_A),
            make_record(znacka="EN 17124", jurisdikce="", _embedding=self.ORTHOGONAL),
        ]
        clusters = dedup.build_clusters(data)
        self.assertEqual(self._clusters_as_sets(clusters), {frozenset({0, 1})})

    def test_neurceno_jurisdiction_does_not_veto_a_same_core_match(self):
        data = [
            make_record(znacka="EN 17124", jurisdikce="CZ", _embedding=self.IDENTICAL_A),
            make_record(znacka="EN 17124", jurisdikce="neurčeno", _embedding=self.ORTHOGONAL),
        ]
        clusters = dedup.build_clusters(data)
        self.assertEqual(self._clusters_as_sets(clusters), {frozenset({0, 1})})


class FindIsoCsnAmbiguousGroupsTestCase(unittest.TestCase):
    def test_finds_a_group_split_by_the_en_infix(self):
        dataset = [
            make_record(znacka="ISO 14687"),
            make_record(znacka="ČSN EN ISO 14687"),
            make_record(znacka="EN 17127"),  # unrelated, not ISO
        ]
        groups = dedup.find_iso_csn_ambiguous_groups(dataset)
        self.assertEqual(set(groups.keys()), {"14687"})
        self.assertEqual(set(groups["14687"]), {0, 1})

    def test_ignores_non_iso_and_already_unambiguous_records(self):
        dataset = [
            make_record(znacka="ISO 14687"),
            make_record(znacka="ISO 14687"),  # same core, not ambiguous
            make_record(znacka=""),
        ]
        self.assertEqual(dedup.find_iso_csn_ambiguous_groups(dataset), {})

    def test_excludes_a_known_non_cz_jurisdiction_record_from_the_group(self):
        # Regression: this exact scenario merged a Slovak STN amendment
        # record into a Czech ČSN record in a real run (2026-09-09,
        # doc/PLAN.md Step 1 follow-up #9) before this filter existed —
        # find_iso_csn_ambiguous_groups predates jurisdikce and originally
        # had no awareness of it at all.
        dataset = [
            make_record(znacka="ČSN EN ISO 11114-1", jurisdikce="CZ"),
            make_record(znacka="ISO 11114-1", jurisdikce="CZ"),
            make_record(znacka="STN EN ISO 11114-1/Zmena", jurisdikce="SK"),
        ]
        groups = dedup.find_iso_csn_ambiguous_groups(dataset)
        self.assertEqual(set(groups.keys()), {"11114-1"})
        self.assertEqual(set(groups["11114-1"]), {0, 1})  # index 2 (SK) excluded

    def test_all_foreign_group_is_never_flagged_even_if_ambiguous_among_itself(self):
        # A cluster of purely non-CZ draft-standard citations (no CZ
        # record at all) must never be surfaced here either — resolving
        # it would mislabel foreign/draft documents with a "ČSN ..."
        # designation as if one of them were the actual Czech standard.
        dataset = [
            make_record(znacka="prEN ISO 22734-1", jurisdikce="DE"),
            make_record(znacka="ISO/FDIS 22734-1", jurisdikce="mezinárodní"),
        ]
        self.assertEqual(dedup.find_iso_csn_ambiguous_groups(dataset), {})

    def test_unknown_jurisdiction_records_still_participate(self):
        # A record with no jurisdikce info at all (e.g. Haltuf, which
        # doesn't populate it) is still a valid candidate — only a KNOWN
        # non-CZ jurisdiction excludes a record.
        dataset = [
            make_record(znacka="ISO 14687", jurisdikce=""),
            make_record(znacka="ČSN EN ISO 14687", jurisdikce="CZ"),
        ]
        groups = dedup.find_iso_csn_ambiguous_groups(dataset)
        self.assertEqual(set(groups.get("14687", [])), {0, 1})


class ResolveIsoCsnAmbiguityTestCase(unittest.TestCase):
    def test_merges_when_exactly_one_valid_designation_is_confirmed(self):
        dataset = [
            make_record(nazev_cz="ISO 14687", znacka="ISO 14687"),
            make_record(nazev_cz="ČSN EN ISO 14687", znacka="ČSN EN ISO 14687"),
        ]
        fake_search = MagicMock(return_value=[
            {"designation": "ČSN ISO 14687", "is_valid": True},
            {"designation": "ČSN ISO 14687-1", "is_valid": False},
        ])
        result, log = dedup.resolve_iso_csn_ambiguity(dataset, csn_search=fake_search)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["znacka"], "ČSN ISO 14687")
        self.assertEqual(log[0]["action"], "merged_by_csn_registry")
        fake_search.assert_called_once_with("ISO 14687")

    def test_leaves_group_untouched_when_no_valid_designation_found(self):
        dataset = [
            make_record(znacka="ISO 14687"),
            make_record(znacka="ČSN EN ISO 14687"),
        ]
        fake_search = MagicMock(return_value=[{"designation": "ČSN ISO 14687", "is_valid": False}])
        result, log = dedup.resolve_iso_csn_ambiguity(dataset, csn_search=fake_search)
        self.assertEqual(len(result), 2)
        self.assertEqual(log[0]["action"], "csn_lookup_inconclusive")

    def test_leaves_group_untouched_when_multiple_valid_designations_found(self):
        dataset = [
            make_record(znacka="ISO 14687"),
            make_record(znacka="ČSN EN ISO 14687"),
        ]
        fake_search = MagicMock(return_value=[
            {"designation": "ČSN ISO 14687", "is_valid": True},
            {"designation": "ČSN EN ISO 14687", "is_valid": True},
        ])
        result, log = dedup.resolve_iso_csn_ambiguity(dataset, csn_search=fake_search)
        self.assertEqual(len(result), 2)
        self.assertEqual(log[0]["action"], "csn_lookup_inconclusive")

    def test_network_failure_is_caught_and_logged_not_raised(self):
        dataset = [make_record(znacka="ISO 14687"), make_record(znacka="ČSN EN ISO 14687")]
        fake_search = MagicMock(side_effect=ConnectionError("boom"))
        result, log = dedup.resolve_iso_csn_ambiguity(dataset, csn_search=fake_search)
        self.assertEqual(result, dataset)
        self.assertEqual(log[0]["action"], "csn_lookup_failed")

    def test_no_ambiguous_groups_is_a_no_op(self):
        dataset = [make_record(znacka="EN 17127"), make_record(znacka="")]
        fake_search = MagicMock()
        result, log = dedup.resolve_iso_csn_ambiguity(dataset, csn_search=fake_search)
        self.assertEqual(result, dataset)
        self.assertEqual(log, [])
        fake_search.assert_not_called()


class DeduplicateClusterWithLlmTestCase(unittest.TestCase):
    """Mocks deduplicate_db.client so no real OpenAI call is ever made."""

    def _fake_completion(self, content):
        completion = MagicMock()
        completion.choices = [MagicMock(message=MagicMock(content=content))]
        return completion

    def test_succeeds_on_the_first_valid_response(self):
        cluster = [make_record(znacka="EN 17127"), make_record(znacka="ČSN EN 17127")]
        response_json = '{"records": [{"znacka": "ČSN EN 17127", "nazev_cz": "ČSN EN 17127"}]}'
        with patch.object(dedup.client.chat.completions, "create",
                           return_value=self._fake_completion(response_json)) as mock_create:
            merged, error = dedup.deduplicate_cluster_with_llm(cluster)
        self.assertIsNone(error)
        self.assertEqual(len(merged), 1)
        mock_create.assert_called_once()

    def test_retries_with_corrective_feedback_then_succeeds(self):
        cluster = [make_record(znacka="EN 17127"), make_record(znacka="ČSN EN 17127")]
        bad = '{"records": [{"znacka": "EN 17127", "nazev_cz": "A"}, {"znacka": "EN 17127", "nazev_cz": "B"}]}'  # split, invalid
        good = '{"records": [{"znacka": "ČSN EN 17127"}]}'
        with patch.object(dedup.client.chat.completions, "create",
                           side_effect=[self._fake_completion(bad), self._fake_completion(good)]) as mock_create, \
             patch.object(dedup.time, "sleep"):
            merged, error = dedup.deduplicate_cluster_with_llm(cluster)
        self.assertIsNone(error)
        self.assertEqual(len(merged), 1)
        self.assertEqual(mock_create.call_count, 2)
        # The retry must include the specific rejection reason, not resend
        # an identical prompt (which would reproduce the same bad output
        # at temperature=0.0).
        second_call_messages = mock_create.call_args_list[1].kwargs["messages"]
        self.assertIn("rejected", second_call_messages[-1]["content"])

    def test_exhausting_all_retries_returns_none_and_an_error(self):
        cluster = [make_record(znacka="EN 17127"), make_record(znacka="ČSN EN 17127")]
        always_bad = '{"records": [{"znacka": "EN 17127", "nazev_cz": "A"}, {"znacka": "EN 17127", "nazev_cz": "B"}]}'
        with patch.object(dedup.client.chat.completions, "create",
                           return_value=self._fake_completion(always_bad)) as mock_create, \
             patch.object(dedup.time, "sleep"):
            merged, error = dedup.deduplicate_cluster_with_llm(cluster)
        self.assertIsNone(merged)
        self.assertIsNotNone(error)
        self.assertEqual(mock_create.call_count, dedup.MAX_LLM_ATTEMPTS)

    def test_api_exception_is_retried_not_raised(self):
        cluster = [make_record(znacka="EN 17127"), make_record(znacka="ČSN EN 17127")]
        good = '{"records": [{"znacka": "ČSN EN 17127"}]}'
        with patch.object(dedup.client.chat.completions, "create",
                           side_effect=[RuntimeError("connection reset"), self._fake_completion(good)]), \
             patch.object(dedup.time, "sleep"):
            merged, error = dedup.deduplicate_cluster_with_llm(cluster)
        self.assertIsNone(error)
        self.assertEqual(len(merged), 1)


if __name__ == "__main__":
    unittest.main()
