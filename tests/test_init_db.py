import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))

from init_db import (
    resolve_identifier, resolve_document_type, normalize_jurisdikce,
    build_gestor_jurisdiction_map, resolve_source_jurisdiction,
    resolve_document_versions, classify_lifecycle_state, FALLBACK_DOCUMENT_TYPE,
    is_restricted_document_type, resolve_file_path,
)


class IsRestrictedDocumentTypeTestCase(unittest.TestCase):
    def test_norma_is_restricted(self):
        self.assertTrue(is_restricted_document_type("Norma"))

    def test_laws_and_fallback_are_not_restricted(self):
        self.assertFalse(is_restricted_document_type("Zákon"))
        self.assertFalse(is_restricted_document_type("Nařízení EU"))
        self.assertFalse(is_restricted_document_type(FALLBACK_DOCUMENT_TYPE))


class ResolveFilePathTestCase(unittest.TestCase):
    """R1.7: looks up a record's locally-cached full text in the
    fetch_fulltext.py manifest, keyed by the RAW per-source
    "zdroj_dat|znacka|url_field" triple -- a merged record's own zdroj_dat
    can be a comma-joined list of contributing sources."""

    def test_single_source_hit(self):
        manifest = {
            "Haltuf_Dokumenty|(EU) 1300/2014|odkaz_eu": {
                "status": "fetched", "local_path": "data/fulltext/Haltuf_Dokumenty/x.pdf"},
        }
        item = {"znacka": "(EU) 1300/2014", "zdroj_dat": "Haltuf_Dokumenty"}
        self.assertEqual(resolve_file_path(item, manifest),
                          "data/fulltext/Haltuf_Dokumenty/x.pdf")

    def test_merged_source_tries_every_component(self):
        manifest = {
            "Haltuf_Dokumenty|458/2000 Sb.|odkaz_eu": {
                "status": "fetched", "local_path": "data/fulltext/Haltuf_Dokumenty/y.pdf"},
        }
        item = {"znacka": "458/2000 Sb.", "zdroj_dat": "Sinay_Zakony, Haltuf_Dokumenty"}
        self.assertEqual(resolve_file_path(item, manifest),
                          "data/fulltext/Haltuf_Dokumenty/y.pdf")

    def test_failed_fetch_is_not_a_hit(self):
        manifest = {"Haltuf_Dokumenty|100/2001 Sb.|odkaz_eu": {"status": "failed"}}
        item = {"znacka": "100/2001 Sb.", "zdroj_dat": "Haltuf_Dokumenty"}
        self.assertIsNone(resolve_file_path(item, manifest))

    def test_no_manifest_entry_is_none(self):
        item = {"znacka": "ISO 14687", "zdroj_dat": "Sinay_Normy"}
        self.assertIsNone(resolve_file_path(item, {}))

    def test_blank_znacka_is_none(self):
        self.assertIsNone(resolve_file_path({"znacka": "", "zdroj_dat": "Haltuf_Dokumenty"}, {}))


class ClassifyLifecycleStateTestCase(unittest.TestCase):
    """doc/REQUIREMENTS.md R1.5: a non-current version is always
    "superseded" regardless of its own platnost text; a current version is
    "draft" only when its platnost/effective_date carries a real
    draft/work-item marker (real corpus strings, German/Czech/Slovak
    standards-body terminology), else "active"."""

    def test_not_current_is_always_superseded(self):
        self.assertEqual(classify_lifecycle_state("Veröffentlicht-Publikovaný / 2021-08", False),
                          "superseded")
        self.assertEqual(classify_lifecycle_state("Entwurf-Návrh", False), "superseded")
        self.assertEqual(classify_lifecycle_state("", False), "superseded")

    def test_current_with_draft_marker_is_draft(self):
        self.assertEqual(classify_lifecycle_state("Entwurf-Návrh", True), "draft")
        self.assertEqual(
            classify_lifecycle_state(
                "Arbeitsdokument (Work Item)-Pracovný dokument (pracovná položka)", True),
            "draft")
        self.assertEqual(
            classify_lifecycle_state(
                "vorläufiges Arbeitsdokument (PWI)-predbežný pracovný dokument (PWI)", True),
            "draft")

    def test_current_without_draft_marker_is_active(self):
        self.assertEqual(classify_lifecycle_state("od 02/2024", True), "active")
        self.assertEqual(
            classify_lifecycle_state("Veröffentlicht-Publikovaný / 2023-01", True), "active")
        self.assertEqual(classify_lifecycle_state("", True), "active")
        self.assertEqual(classify_lifecycle_state(None, True), "active")


class ResolveDocumentVersionsTestCase(unittest.TestCase):
    """Step 1 follow-up #16: a record without a "versions" list (the
    common case) keeps the historical single-row behavior; one with a
    "versions" list (built by link_document_versions.py for a norm
    base+amendment group) gets one DocumentVersion row per entry, in
    order, with its own edition_label/effective_date/is_current. R1.5:
    every row also gets lifecycle_state via classify_lifecycle_state()."""

    def test_no_versions_list_is_the_historical_single_row(self):
        rows = resolve_document_versions({"znacka": "STN EN 1"})
        self.assertEqual(rows, [{"version": 1, "edition_label": None,
                                  "effective_date": None, "is_current": True,
                                  "lifecycle_state": "active"}])

    def test_no_versions_list_uses_own_platnost_for_lifecycle_state(self):
        rows = resolve_document_versions({"znacka": "ISO 23802", "platnost": "Entwurf-Návrh / 2022-08"})
        self.assertEqual(rows[0]["lifecycle_state"], "draft")
        # ... but does NOT get written into this row's own effective_date
        # column (that column keeps its existing "real per-edition date,
        # never generic platnost text" meaning for the unversioned case).
        self.assertIsNone(rows[0]["effective_date"])

    def test_versions_list_becomes_one_row_each_in_order(self):
        item = {"versions": [
            {"znacka": "STN EN 1/ - 2021.08", "edition_label": "STN EN 1/ - 2021.08",
             "effective_date": "Veröffentlicht-Publikovaný / 2021-08", "is_current": False},
            {"znacka": "STN EN 1+A1/ - 2024.02", "edition_label": "STN EN 1+A1/ - 2024.02",
             "effective_date": "od 02/2024", "is_current": True},
        ]}
        rows = resolve_document_versions(item)
        self.assertEqual([r["version"] for r in rows], [1, 2])
        self.assertEqual([r["is_current"] for r in rows], [False, True])
        self.assertEqual(rows[1]["edition_label"], "STN EN 1+A1/ - 2024.02")
        self.assertEqual(rows[1]["effective_date"], "od 02/2024")
        # The superseded (non-current) member is "superseded" even though
        # its own platnost ("Veröffentlicht-Publikovaný", i.e. published)
        # would otherwise read as "active" -- is_current wins.
        self.assertEqual(rows[0]["lifecycle_state"], "superseded")
        self.assertEqual(rows[1]["lifecycle_state"], "active")

    def test_versions_list_current_member_with_draft_marker_is_draft(self):
        item = {"versions": [
            {"znacka": "IEC 62351-14", "edition_label": "IEC 62351-14",
             "effective_date": "Entwurf-Návrh", "is_current": True},
        ]}
        rows = resolve_document_versions(item)
        self.assertEqual(rows[0]["lifecycle_state"], "draft")

    def test_empty_versions_list_falls_back_to_single_row(self):
        self.assertEqual(resolve_document_versions({"versions": []}),
                          resolve_document_versions({}))


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
