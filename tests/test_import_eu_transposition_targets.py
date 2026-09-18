import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))

import import_eu_transposition_targets as iet  # noqa: E402


class BuildEuActRegistryTestCase(unittest.TestCase):
    def test_indexes_both_digit_orderings(self):
        cache = {
            "https://www.zakonyprolidi.cz/cs/2001-100": {
                "status": "fetched",
                "nazev_eu": "Nařízení Evropského parlamentu a Rady (ES) č. 865/2006 ze dne 4. května 2006",
                "odkaz_eu": "https://eur-lex.europa.eu/eli/reg/2006/865/oj",
            }
        }
        registry = iet.build_eu_act_registry(cache)
        self.assertIn("2006/865", registry)
        self.assertIn("865/2006", registry)
        self.assertEqual(registry["2006/865"][1], "https://eur-lex.europa.eu/eli/reg/2006/865/oj")

    def test_multiple_acts_in_one_entry(self):
        cache = {
            "u1": {
                "status": "fetched",
                "nazev_eu": "Act A\nAct B",
                "odkaz_eu": "https://eur-lex.europa.eu/eli/dir/2001/42/oj\nhttps://eur-lex.europa.eu/eli/dir/2011/92/oj",
            }
        }
        registry = iet.build_eu_act_registry(cache)
        self.assertEqual(registry["2001/42"], ("Act A", "https://eur-lex.europa.eu/eli/dir/2001/42/oj"))
        self.assertEqual(registry["2011/92"], ("Act B", "https://eur-lex.europa.eu/eli/dir/2011/92/oj"))

    def test_non_fetched_status_is_ignored(self):
        cache = {"u1": {"status": "no_transposition"}}
        self.assertEqual(iet.build_eu_act_registry(cache), {})

    def test_mismatched_title_url_line_counts_are_skipped_defensively(self):
        cache = {"u1": {"status": "fetched", "nazev_eu": "A\nB", "odkaz_eu": "https://eur-lex.europa.eu/eli/dir/2001/42/oj"}}
        self.assertEqual(iet.build_eu_act_registry(cache), {})


class ParseActUrlTestCase(unittest.TestCase):
    def test_eli_directive(self):
        self.assertEqual(iet.parse_act_url("https://eur-lex.europa.eu/eli/dir/2011/92/oj"),
                          ("Směrnice EU", 2011, 92))

    def test_eli_regulation(self):
        self.assertEqual(iet.parse_act_url("https://eur-lex.europa.eu/eli/reg/2006/1013/oj"),
                          ("Nařízení EU", 2006, 1013))

    def test_eli_decision_variants(self):
        self.assertEqual(iet.parse_act_url("https://eur-lex.europa.eu/eli/dec/2018/546/oj"),
                          ("Rozhodnutí EU", 2018, 546))
        self.assertEqual(iet.parse_act_url("https://eur-lex.europa.eu/eli/dec_impl/2013/732/oj"),
                          ("Rozhodnutí EU", 2013, 732))

    def test_celex_style(self):
        self.assertEqual(
            iet.parse_act_url("https://eur-lex.europa.eu/legal-content/CS/TXT/?uri=CELEX:31998D2119"),
            ("Rozhodnutí EU", 1998, 2119))

    def test_unrecognized_shape_returns_none(self):
        self.assertIsNone(iet.parse_act_url("https://www.slov-lex.sk/pravne-predpisy/SK/ZZ/2010/75"))


class EraSuffixTestCase(unittest.TestCase):
    def test_pre_1993_is_ehs(self):
        self.assertEqual(iet.era_suffix(1985), "EHS")
        self.assertEqual(iet.era_suffix(1992), "EHS")

    def test_1993_to_2008_is_es(self):
        self.assertEqual(iet.era_suffix(1993), "ES")
        self.assertEqual(iet.era_suffix(2008), "ES")

    def test_2009_onward_is_eu(self):
        self.assertEqual(iet.era_suffix(2009), "EU")
        self.assertEqual(iet.era_suffix(2023), "EU")


class BuildZnackaTestCase(unittest.TestCase):
    def test_builds_bare_slash_style(self):
        self.assertEqual(iet.build_znacka(2001, 42), "2001/42/ES")
        self.assertEqual(iet.build_znacka(1985, 337), "1985/337/EHS")
        self.assertEqual(iet.build_znacka(2018, 2001), "2018/2001/EU")


class FindMissingEuActReferencesTestCase(unittest.TestCase):
    def test_deduplicates_across_citing_laws(self):
        missing = [
            {"znacka": "100/2001 Sb.", "cited_eu_reference": "2001/42/ES"},
            {"znacka": "24/2006 Z. z.", "cited_eu_reference": "2001/42/ES"},
            {"znacka": "100/2001 Sb.", "cited_eu_reference": "2011/92/EU"},
        ]
        self.assertEqual(iet.find_missing_eu_act_references(missing), {"2001/42", "2011/92"})

    def test_unparseable_reference_is_skipped(self):
        self.assertEqual(iet.find_missing_eu_act_references([{"cited_eu_reference": ""}]), set())


class ExistingCorpusDigitCoresTestCase(unittest.TestCase):
    def test_extracts_from_znacka(self):
        records = [{"znacka": "2001/42/ES"}, {"znacka": "ČSN EN 17124"}]
        self.assertEqual(iet.existing_corpus_digit_cores(records), {"2001/42"})


class LoadPreviouslyDiscoveredTestCase(unittest.TestCase):
    """Regression, found live (doc/PLAN.md §39): a second run of this
    script (to pick up one more target after `_normalized_digit_pair()`
    was separately fixed to handle 2-digit years) silently DISCARDED the
    first run's 91 records because `main()` used to write only the
    newly-`added` list, never merging with what was already on disk."""

    def test_missing_output_file_returns_empty_list(self):
        with patch.object(iet, "OUTPUT_PATH", pathlib.Path("/nonexistent/path/does-not-exist.json")):
            self.assertEqual(iet.load_previously_discovered(), [])

    def test_existing_output_file_is_loaded(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "discovered.json"
            path.write_text('[{"odkaz_hlavni": "https://eur-lex.europa.eu/eli/dir/1999/31/oj"}]', encoding="utf-8")
            with patch.object(iet, "OUTPUT_PATH", path):
                self.assertEqual(iet.load_previously_discovered(),
                                  [{"odkaz_hlavni": "https://eur-lex.europa.eu/eli/dir/1999/31/oj"}])


class MainIntegrationTestCase(unittest.TestCase):
    """End-to-end through the actual selection logic (not main()'s I/O),
    exercising the three real outcomes found live: a directly-cited,
    independently-resolved act is imported; an act already present in
    the corpus is skipped (idempotent); a secondary/incidental mention
    with no independently-resolved (title, url) pair is logged
    separately, never guessed."""

    def test_full_selection_logic(self):
        cache = {
            "u1": {
                "status": "fetched",
                "nazev_eu": "Směrnice Evropského parlamentu a Rady 2001/42/ES ze dne 27. června 2001 o...",
                "odkaz_eu": "https://eur-lex.europa.eu/eli/dir/2001/42/oj",
            }
        }
        missing_targets = [
            {"znacka": "100/2001 Sb.", "cited_eu_reference": "2001/42/ES"},  # directly cited, resolved -> import
            {"znacka": "100/2001 Sb.", "cited_eu_reference": "2007/46/ES"},  # already in corpus -> skip
            {"znacka": "165/2012 Sb.", "cited_eu_reference": "663/2009"},  # secondary mention, unresolved -> log
        ]
        records = [{"znacka": "2007/46/ES"}]  # already exists

        registry = iet.build_eu_act_registry(cache)
        existing_cores = iet.existing_corpus_digit_cores(records)
        referenced_cores = iet.find_missing_eu_act_references(missing_targets)

        imported, secondary = [], []
        for core in sorted(referenced_cores):
            from link_document_relations_auto import _normalized_digit_pair
            if any(v in existing_cores for v in _normalized_digit_pair(core)):
                continue
            hit = next((registry[v] for v in _normalized_digit_pair(core) if v in registry), None)
            if hit is None:
                secondary.append(core)
                continue
            title, url = hit
            imported.append((title, url))

        self.assertEqual(imported, [("Směrnice Evropského parlamentu a Rady 2001/42/ES ze dne 27. června 2001 o...",
                                      "https://eur-lex.europa.eu/eli/dir/2001/42/oj")])
        self.assertEqual(secondary, ["663/2009"])


if __name__ == "__main__":
    unittest.main()
