import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))

from init_db import (
    resolve_identifier, resolve_document_type, normalize_jurisdikce,
    build_gestor_jurisdiction_map, resolve_source_jurisdiction,
    FALLBACK_DOCUMENT_TYPE,
)


class ResolveIdentifierTestCase(unittest.TestCase):
    def test_blank_znacka_is_none(self):
        seen = set()
        self.assertIsNone(resolve_identifier("", seen))
        self.assertIsNone(resolve_identifier("   ", seen))
        self.assertEqual(seen, set())

    def test_first_occurrence_gets_the_identifier(self):
        seen = set()
        self.assertEqual(resolve_identifier("458/2000 Sb.", seen), "458/2000 Sb.")
        self.assertIn("458/2000 Sb.", seen)

    def test_second_occurrence_of_same_znacka_is_none(self):
        seen = set()
        resolve_identifier("ASTM F1624-12", seen)
        self.assertIsNone(resolve_identifier("ASTM F1624-12", seen))

    def test_whitespace_is_stripped_before_comparison(self):
        seen = set()
        resolve_identifier("183/2006 Sb.", seen)
        self.assertIsNone(resolve_identifier("  183/2006 Sb.  ", seen))

    def test_znacka_longer_than_column_limit_is_none(self):
        # A real case found in data/database_merged_deduplicated.json: a
        # Sinay-parsed record bundles several newline-joined STN
        # designations into one znacka field (a PDF-parsing artifact) —
        # too long for VARCHAR(100), and not a real single identifier
        # anyway, so it must not be stored (nor silently truncated).
        seen = set()
        bundle = "STN EN 1514-1/ – 2001.04\nSTN EN 1514-2+A1/ – 2021.07\n" * 3
        self.assertGreater(len(bundle), 100)
        self.assertIsNone(resolve_identifier(bundle, seen))
        self.assertEqual(seen, set())


class ResolveDocumentTypeTestCase(unittest.TestCase):
    def test_real_label_passes_through(self):
        self.assertEqual(resolve_document_type("Norma"), "Norma")
        self.assertEqual(resolve_document_type("Zákon"), "Zákon")

    def test_purely_numeric_code_falls_back(self):
        for code in ("1", "2", "9", "10", "11"):
            self.assertEqual(resolve_document_type(code), FALLBACK_DOCUMENT_TYPE)

    def test_blank_falls_back(self):
        self.assertEqual(resolve_document_type(""), FALLBACK_DOCUMENT_TYPE)
        self.assertEqual(resolve_document_type("   "), FALLBACK_DOCUMENT_TYPE)


class NormalizeJurisdikceTestCase(unittest.TestCase):
    def test_blank_is_none(self):
        self.assertIsNone(normalize_jurisdikce(""))
        self.assertIsNone(normalize_jurisdikce("   "))

    def test_neurceno_is_kept_verbatim(self):
        # "we tried and couldn't tell" is different from "field never set"
        self.assertEqual(normalize_jurisdikce("neurčeno"), "neurčeno")

    def test_real_value_is_stripped(self):
        self.assertEqual(normalize_jurisdikce("  SK  "), "SK")


class BuildGestorJurisdictionMapTestCase(unittest.TestCase):
    def test_blank_gestor_ignored(self):
        records = [{"gestor": [], "jurisdikce": "CZ"}]
        self.assertEqual(build_gestor_jurisdiction_map(records), {})

    def test_unknown_jurisdikce_not_recorded(self):
        records = [{"gestor": "MPO", "jurisdikce": "neurčeno"},
                   {"gestor": "MPO", "jurisdikce": ""}]
        self.assertEqual(build_gestor_jurisdiction_map(records), {})

    def test_first_real_value_wins_over_later_blank(self):
        # Ordering matters: DocumentSource rows are get_or_create'd, so
        # whichever record for a gestor is processed first decides what's
        # inserted -- the map must resolve the real value regardless of
        # which record (blank-jurisdikce or real) happens to come first
        # in the source list.
        records = [{"gestor": "MPO", "jurisdikce": ""},
                   {"gestor": "MPO", "jurisdikce": "CZ"}]
        self.assertEqual(build_gestor_jurisdiction_map(records), {"MPO": "CZ"})

    def test_list_gestor_is_joined(self):
        records = [{"gestor": ["MPO", "MŽP"], "jurisdikce": "CZ"}]
        self.assertEqual(build_gestor_jurisdiction_map(records), {"MPO, MŽP": "CZ"})


class ResolveSourceJurisdictionTestCase(unittest.TestCase):
    def test_blank_gestor_gives_none_none(self):
        self.assertEqual(resolve_source_jurisdiction("", {"MPO": "CZ"}), (None, None))

    def test_known_gestor_gives_jurisdiction_only(self):
        # institution_type is never populated this pass -- no reliable
        # source signal for it (see doc/PLAN.md Step 2).
        self.assertEqual(resolve_source_jurisdiction("MPO", {"MPO": "CZ"}), (None, "CZ"))

    def test_unmapped_gestor_gives_none_none(self):
        self.assertEqual(resolve_source_jurisdiction("Unknown Body", {"MPO": "CZ"}), (None, None))


if __name__ == "__main__":
    unittest.main()
