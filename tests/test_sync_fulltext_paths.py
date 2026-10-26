"""Tests for src/tools/sync_fulltext_paths.py: only documents whose file is
missing are touched, and they are pointed at the manifest's best fetched
entry for their designation (or cleared)."""
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))

import sync_fulltext_paths as sp  # noqa: E402


def fetched(path):
    return {"status": "fetched", "local_path": path}


class ResolveTestCase(unittest.TestCase):
    MANIFEST = {
        "Sinay_Zakony|(EU) 2023/1234|odkaz_hlavni": fetched("data/fulltext/H.html"),
        "Sinay_Zakony|(EU) 2023/1234|odkaz_eu": fetched("data/fulltext/E.html"),
        "Sinay_Zakony|56/2001 Sb.|odkaz_eu": fetched("data/fulltext/Z.html"),
        "Sinay_Zakony|56/2001 Sb.|odkaz_hlavni": {"status": "failed"},
    }

    def test_prefers_odkaz_hlavni_then_eu(self):
        self.assertEqual(sp.resolve_by_identifier(self.MANIFEST, "(EU) 2023/1234"), "data/fulltext/H.html")
        self.assertEqual(sp.resolve_by_identifier(self.MANIFEST, "56/2001 Sb."), "data/fulltext/Z.html")

    def test_none_when_nothing_fetched_or_unknown(self):
        self.assertIsNone(sp.resolve_by_identifier(self.MANIFEST, "unknown"))
        self.assertIsNone(sp.resolve_by_identifier({"S|X|odkaz_eu": {"status": "failed"}}, "X"))

    def test_a_designation_containing_a_bar_matches_whole(self):
        self.assertEqual(sp.resolve_by_identifier({"S|A | B|odkaz_eu": fetched("p")}, "A | B"), "p")


class PlanTestCase(unittest.TestCase):
    def test_only_missing_files_are_changed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "data" / "fulltext").mkdir(parents=True)
            (root / "data/fulltext/present.html").write_text("x", encoding="utf-8")
            manifest = {"S|B|odkaz_hlavni": fetched("data/fulltext/new.html")}
            rows = [(1, "A", "data/fulltext/present.html"), (2, "B", "data/fulltext/gone.html"),
                    (3, "C", "data/fulltext/gone2.html"), (4, "D", None)]
            self.assertEqual(sp.plan_changes(rows, manifest, root),
                             [(2, "B", "data/fulltext/gone.html", "data/fulltext/new.html"),
                              (3, "C", "data/fulltext/gone2.html", None)])


class FakeConn:
    def __init__(self):
        self.statements, self.committed = [], False

    def cursor(self):
        conn = self

        class Cur:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def execute(self, sql, params):
                conn.statements.append((sql, params))
        return Cur()

    def commit(self):
        self.committed = True


class ApplyTestCase(unittest.TestCase):
    def test_updates_by_id_and_old_path_and_commits_once(self):
        conn = FakeConn()
        sp.apply_changes(conn, [(2, "B", "old", "new"), (3, "C", "old2", None)])
        self.assertEqual([p for _, p in conn.statements], [("new", 2, "old"), (None, 3, "old2")])
        self.assertTrue(all("WHERE id = %s AND file_path <=> %s" in s for s, _ in conn.statements))
        self.assertTrue(conn.committed)


class FillTestCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = pathlib.Path(tmp.name)
        (self.root / "data" / "fulltext").mkdir(parents=True)
        (self.root / "data/fulltext/new.html").write_text("x", encoding="utf-8")
        self.manifest = {"S|124/2000 Z. z.|odkaz_hlavni": fetched("data/fulltext/new.html"),
                         "S|EN 17127|odkaz_hlavni": fetched("data/fulltext/new.html"),
                         "S|ghost|odkaz_hlavni": fetched("data/fulltext/ghost.html")}

    def test_without_fill_a_document_with_no_path_is_left_alone(self):
        rows = [(1, "124/2000 Z. z.", None, 0)]
        self.assertEqual(sp.plan_changes(rows, self.manifest, self.root), [])

    def test_fill_gives_a_path_to_a_document_that_has_none(self):
        rows = [(1, "124/2000 Z. z.", None, 0)]
        self.assertEqual(sp.plan_changes(rows, self.manifest, self.root, fill=True),
                         [(1, "124/2000 Z. z.", None, "data/fulltext/new.html")])

    def test_a_restricted_type_is_never_filled(self):
        rows = [(2, "EN 17127", None, 1)]
        self.assertEqual(sp.plan_changes(rows, self.manifest, self.root, fill=True), [])

    def test_a_manifest_entry_whose_file_is_missing_is_not_filled(self):
        rows = [(3, "ghost", None, 0)]
        self.assertEqual(sp.plan_changes(rows, self.manifest, self.root, fill=True), [])

    def test_a_document_that_already_has_a_working_path_is_untouched(self):
        rows = [(4, "124/2000 Z. z.", "data/fulltext/new.html", 0)]
        self.assertEqual(sp.plan_changes(rows, self.manifest, self.root, fill=True), [])

    def test_apply_uses_a_null_safe_comparison_for_a_filled_document(self):
        conn = FakeConn()
        sp.apply_changes(conn, [(1, "x", None, "new")])
        self.assertEqual(conn.statements[0][1], ("new", 1, None))


class OwnSourceTestCase(unittest.TestCase):
    MANIFEST = {"Sinay_Zakony|2010/75/EU|odkaz_hlavni": {"status": "failed"},
                "EU_Transposition_Targets|2010/75/EU|odkaz_eu": fetched("data/fulltext/directive.html")}

    def test_a_document_of_another_source_does_not_get_the_files_of_a_namesake(self):
        self.assertIsNone(sp.resolve_by_identifier(self.MANIFEST, "2010/75/EU", {"Sinay_Zakony"}))
        self.assertEqual(sp.resolve_by_identifier(self.MANIFEST, "2010/75/EU", {"EU_Transposition_Targets"}),
                         "data/fulltext/directive.html")

    def test_without_sources_the_designation_alone_decides_as_before(self):
        self.assertEqual(sp.resolve_by_identifier(self.MANIFEST, "2010/75/EU"), "data/fulltext/directive.html")

    def test_a_merged_document_may_use_any_of_its_sources(self):
        self.assertEqual(sp.document_sources("Sinay_Zakony, EU_Transposition_Targets"),
                         {"Sinay_Zakony", "EU_Transposition_Targets"})
        self.assertEqual(sp.resolve_by_identifier(self.MANIFEST, "2010/75/EU", sp.document_sources("Sinay_Zakony, EU_Transposition_Targets")),
                         "data/fulltext/directive.html")

    def test_fill_respects_the_documents_own_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "data" / "fulltext").mkdir(parents=True)
            (root / "data/fulltext/directive.html").write_text("x", encoding="utf-8")
            rows = [(62, "2010/75/EU", None, 0, "Sinay_Zakony"), (1222, "2010/75/EU", None, 0, "EU_Transposition_Targets")]
            self.assertEqual(sp.plan_changes(rows, self.MANIFEST, root, fill=True),
                             [(1222, "2010/75/EU", None, "data/fulltext/directive.html")])


class UnidentifiedTestCase(unittest.TestCase):
    URL = "https://www.hytep.cz/a.pdf"

    def setUp(self):
        import fulltext_keys
        import slug as slug_module
        self.item = {"zdroj_dat": "HYTEP", "znacka": "", "nazev_cz": "Vodíková strategie", "typ_dokumentu": "Strategický dokument",
                     "odkaz_hlavni": self.URL}
        self.slug = slug_module.base_slug(None, "Vodíková strategie")
        self.key = f"HYTEP|{fulltext_keys.url_designation(self.URL)}|odkaz_hlavni"

    def _repo(self, tmp):
        (pathlib.Path(tmp) / "data" / "fulltext").mkdir(parents=True)
        (pathlib.Path(tmp) / "data" / "fulltext" / "u__ab.pdf").write_bytes(b"%PDF-")
        return {self.key: {"status": "fetched", "local_path": "data/fulltext/u__ab.pdf"}}

    def test_a_document_without_designation_gets_the_file_the_manifest_has_for_its_address(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self._repo(tmp)
            rows = [(7, None, None, 0, "HYTEP", self.slug, self.URL)]
            self.assertEqual(sp.plan_unidentified(rows, [self.item], manifest, repo_root=tmp),
                             [(7, f"slug {self.slug}", None, "data/fulltext/u__ab.pdf")])

    def test_a_document_that_has_a_designation_or_a_path_or_is_restricted_is_left_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self._repo(tmp)
            for row in ((7, "X 1", None, 0, "HYTEP", self.slug, self.URL), (7, None, "data/fulltext/o.pdf", 0, "HYTEP", self.slug, self.URL),
                        (7, None, None, 1, "HYTEP", self.slug, self.URL)):
                self.assertEqual(sp.plan_unidentified([row], [self.item], manifest, repo_root=tmp), [])

    def test_a_missing_file_or_another_title_gives_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self._repo(tmp)
            (pathlib.Path(tmp) / "data" / "fulltext" / "u__ab.pdf").unlink()
            self.assertEqual(sp.plan_unidentified([(7, None, None, 0, "HYTEP", self.slug, self.URL)], [self.item], manifest, repo_root=tmp), [])
            self.assertEqual(sp.plan_unidentified([(7, None, None, 0, "HYTEP", "doc-00000000", self.URL)], [self.item], manifest, repo_root=tmp), [])

    def test_records_with_one_title_are_told_apart_by_address_and_a_suffixed_slug_still_matches(self):
        import fulltext_keys
        other = {**self.item, "odkaz_hlavni": "https://www.hytep.cz/b.pdf"}
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self._repo(tmp)
            manifest[f"HYTEP|{fulltext_keys.url_designation('https://www.hytep.cz/b.pdf')}|odkaz_hlavni"] = {
                "status": "fetched", "local_path": "data/fulltext/u__ab.pdf"}
            rows = [(7, None, None, 0, "HYTEP", self.slug, self.URL), (8, None, None, 0, "HYTEP", self.slug + "-2", "https://www.hytep.cz/b.pdf")]
            changes = sp.plan_unidentified(rows, [self.item, other], manifest, repo_root=tmp)
            self.assertEqual([c[0] for c in changes], [7, 8])
            rows_unknown_url = [(7, None, None, 0, "HYTEP", self.slug, "https://elsewhere/")]
            self.assertEqual(sp.plan_unidentified(rows_unknown_url, [self.item, other], manifest, repo_root=tmp), [])

    def test_a_record_with_a_designation_that_another_document_holds_is_matched_too(self):
        import fulltext_keys  # noqa: F401
        item = {**self.item, "znacka": "2010/75/EU"}
        manifest = {"HYTEP|2010/75/EU|odkaz_hlavni": {"status": "fetched", "local_path": "data/fulltext/u__ab.pdf"}}
        with tempfile.TemporaryDirectory() as tmp:
            self._repo(tmp)
            changes = sp.plan_unidentified([(7, None, None, 0, "HYTEP", self.slug, self.URL)], [item], manifest, repo_root=tmp)
            self.assertEqual([c[0] for c in changes], [7])

    def test_a_norm_record_is_never_matched(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self._repo(tmp)
            norm = {**self.item, "typ_dokumentu": "Norma"}
            self.assertEqual(sp.plan_unidentified([(7, None, None, 0, "HYTEP", self.slug, self.URL)], [norm], manifest, repo_root=tmp), [])


if __name__ == "__main__":
    unittest.main()
