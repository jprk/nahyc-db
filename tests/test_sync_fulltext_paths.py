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
        self.assertTrue(all("WHERE id = %s AND file_path = %s" in s for s, _ in conn.statements))
        self.assertTrue(conn.committed)


if __name__ == "__main__":
    unittest.main()
