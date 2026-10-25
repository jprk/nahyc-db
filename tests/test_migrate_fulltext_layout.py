"""Tests for src/tools/migrate_fulltext_layout.py: planning the move to the
flat `data/fulltext/` layout, creating the new files without touching the old
ones, the database update (against a fake connection) and the cleanup that
only removes what nothing references any more. Temporary directories only."""
import hashlib
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))

import migrate_fulltext_layout as ml  # noqa: E402


def sha(data):
    return hashlib.sha256(data).hexdigest()


def entry(path, data, status="fetched"):
    return {"status": status, "local_path": path, "sha256": sha(data), "url": "https://example.test/x"}


class PlanTestCase(unittest.TestCase):
    def test_old_entries_get_flat_names_without_the_source_folder(self):
        manifest = {"Haltuf_Dokumenty|(EU) 2022/869|odkaz_hlavni":
                    entry("data/fulltext/Haltuf_Dokumenty/EU_2022_869__odkaz_hlavni.pdf", b"a")}
        (move,) = ml.plan_moves(manifest)
        self.assertEqual(move["new"], f"data/fulltext/EU_2022_869__{sha(b'a')[:8]}.pdf")

    def test_the_same_content_under_two_url_fields_is_one_new_file(self):
        manifest = {
            "Sinay_Zakony|(EU) 2022/869|odkaz_hlavni": entry("data/fulltext/Sinay_Zakony/EU_2022_869__odkaz_hlavni.html", b"same"),
            "Sinay_Zakony|(EU) 2022/869|odkaz_eu": entry("data/fulltext/Sinay_Zakony/EU_2022_869__odkaz_eu.html", b"same"),
        }
        moves = ml.plan_moves(manifest)
        self.assertEqual(len(moves), 2)
        self.assertEqual(len({m["new"] for m in moves}), 1)

    def test_different_content_for_one_designation_stays_two_files(self):
        manifest = {
            "Haltuf_Dokumenty|201/2012 Sb.|odkaz_hlavni": entry("data/fulltext/Haltuf_Dokumenty/201_2012_Sb.__odkaz_hlavni.html", b"cz"),
            "Sinay_Zakony|201/2012 Sb.|odkaz_hlavni": entry("data/fulltext/Sinay_Zakony/201_2012_Sb.__odkaz_hlavni.html", b"eu"),
        }
        self.assertEqual(len({m["new"] for m in ml.plan_moves(manifest)}), 2)

    def test_already_flat_failed_and_empty_entries_are_left_alone(self):
        manifest = {
            "a|X|f": entry("data/fulltext/X__12345678.pdf", b"1"),
            "b|Y|f": {"status": "failed", "url": "u"},
            "c|Z|f": {"status": "fetched", "local_path": "", "sha256": sha(b"2")},
        }
        self.assertEqual(ml.plan_moves(manifest), [])

    def test_a_missing_hash_is_an_error_not_a_guess(self):
        manifest = {"a|X|f": {"status": "fetched", "local_path": "data/fulltext/S/x.pdf"}}
        with self.assertRaises(ml.MigrationError):
            ml.plan_moves(manifest)

    def test_a_designation_containing_a_bar_is_kept_whole(self):
        self.assertEqual(ml.designation_of("Src|A | B|odkaz_eu"), "A | B")


class FilesTestCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = pathlib.Path(tmp.name)
        (self.root / "data" / "fulltext" / "S").mkdir(parents=True)

    def write(self, rel, data):
        path = self.root / rel
        path.write_bytes(data)
        return path

    def move(self, old, data, designation="DOC 1"):
        return {"key": f"S|{designation}|odkaz_hlavni", "old": old,
                "new": f"data/fulltext/DOC_1__{sha(data)[:8]}.html", "sha256": sha(data)}

    def test_new_file_is_created_and_the_old_one_stays(self):
        old = self.write("data/fulltext/S/a.html", b"content")
        move = self.move("data/fulltext/S/a.html", b"content")
        self.assertEqual(ml.apply_files([move], self.root), (1, 0))
        self.assertEqual((self.root / move["new"]).read_bytes(), b"content")
        self.assertTrue(old.exists())

    def test_duplicates_create_one_file_and_a_rerun_creates_nothing(self):
        self.write("data/fulltext/S/a.html", b"content")
        self.write("data/fulltext/S/b.html", b"content")
        moves = [self.move("data/fulltext/S/a.html", b"content"), self.move("data/fulltext/S/b.html", b"content")]
        self.assertEqual(ml.apply_files(moves, self.root), (1, 0))
        self.assertEqual(ml.apply_files(moves, self.root), (0, 1))

    def test_a_file_that_does_not_match_its_hash_is_refused(self):
        self.write("data/fulltext/S/a.html", b"tampered")
        move = self.move("data/fulltext/S/a.html", b"content")
        with self.assertRaises(ml.MigrationError):
            ml.apply_files([move], self.root)
        self.assertFalse((self.root / move["new"]).exists())

    def test_a_missing_source_is_refused(self):
        with self.assertRaises(ml.MigrationError):
            ml.apply_files([self.move("data/fulltext/S/gone.html", b"content")], self.root)

    def test_manifest_and_mapping_follow_the_moves(self):
        moves = [{"key": "k1", "old": "o1", "new": "n1", "sha256": "x"}, {"key": "k2", "old": "o1", "new": "n1", "sha256": "x"}]
        manifest = {"k1": {"local_path": "o1"}, "k2": {"local_path": "o1"}}
        self.assertEqual(ml.rewrite_manifest(manifest, moves), {"k1": {"local_path": "n1"}, "k2": {"local_path": "n1"}})
        self.assertEqual(ml.mapping_of(moves), {"o1": "n1"})


class FakeCursor:
    def __init__(self, db):
        self.db, self.result = db, None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=()):
        self.db.statements.append((sql, params))
        if sql.startswith("SELECT COUNT(*) FROM Document WHERE file_path = "):
            self.result = (self.db.rows.get(params[0], 0),)
        elif sql.startswith("UPDATE"):
            new, old = params
            self.db.rows[new] = self.db.rows.get(new, 0) + self.db.rows.pop(old, 0)
        elif sql.startswith("SELECT COUNT(*) FROM Document WHERE file_path IN"):
            self.result = (sum(self.db.rows.get(p, 0) for p in params),)
        elif sql.startswith("SELECT DISTINCT"):
            self.result = None

    def fetchone(self):
        return self.result

    def fetchall(self):
        return [(p,) for p in self.db.rows if self.db.rows[p]]


class FakeConn:
    def __init__(self, rows):
        self.rows, self.statements, self.committed, self.rolled_back = dict(rows), [], False, False

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


class DatabaseTestCase(unittest.TestCase):
    def test_dry_run_counts_and_changes_nothing(self):
        conn = FakeConn({"old/a": 1, "old/b": 2})
        self.assertEqual(ml.update_documents(conn, {"old/a": "new/a", "old/b": "new/b"}), 3)
        self.assertFalse(any(s.startswith("UPDATE") for s, _ in conn.statements))
        self.assertFalse(conn.committed)

    def test_apply_updates_and_commits_once(self):
        conn = FakeConn({"old/a": 1})
        self.assertEqual(ml.update_documents(conn, {"old/a": "new/a"}, apply=True), 1)
        self.assertEqual(conn.rows, {"new/a": 1})
        self.assertTrue(conn.committed)

    def test_rerun_after_the_update_changes_nothing(self):
        conn = FakeConn({"new/a": 1})
        self.assertEqual(ml.update_documents(conn, {"old/a": "new/a"}, apply=True), 0)

    def test_a_surviving_old_path_rolls_the_whole_update_back(self):
        conn = FakeConn({"old/a": 1})
        with mock.patch.object(FakeCursor, "execute", autospec=True) as execute:
            def fake(cursor, sql, params=()):
                cursor.db.statements.append((sql, params))
                if sql.startswith("SELECT COUNT(*) FROM Document WHERE file_path = "):
                    cursor.result = (1,)
                elif sql.startswith("SELECT COUNT(*) FROM Document WHERE file_path IN"):
                    cursor.result = (1,)  # the UPDATE did not take
            execute.side_effect = fake
            with self.assertRaises(ml.MigrationError):
                ml.update_documents(conn, {"old/a": "new/a"}, apply=True)
        self.assertTrue(conn.rolled_back)
        self.assertFalse(conn.committed)


class CleanupTestCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = pathlib.Path(tmp.name)
        (self.root / "data" / "fulltext" / "S").mkdir(parents=True)
        for rel in ("data/fulltext/S/a.html", "data/fulltext/S/b.html", "data/fulltext/A__1.html"):
            (self.root / rel).write_text("x", encoding="utf-8")
        self.mapping = {"data/fulltext/S/a.html": "data/fulltext/A__1.html",
                        "data/fulltext/S/b.html": "data/fulltext/B__2.html"}

    def test_dry_run_removes_nothing(self):
        removed, kept = ml.cleanup(self.mapping, set(), self.root)
        self.assertEqual(removed, ["data/fulltext/S/a.html"])
        self.assertTrue((self.root / "data/fulltext/S/a.html").exists())

    def test_removes_only_what_has_a_new_file_and_no_reference(self):
        removed, kept = ml.cleanup(self.mapping, set(), self.root, apply=True)
        self.assertEqual(removed, ["data/fulltext/S/a.html"])
        self.assertEqual(kept, ["data/fulltext/S/b.html"], "no new file for b yet")
        self.assertTrue((self.root / "data/fulltext/S/b.html").exists())

    def test_a_path_the_database_still_references_is_kept(self):
        removed, kept = ml.cleanup(self.mapping, {"data/fulltext/S/a.html"}, self.root, apply=True)
        self.assertEqual(removed, [])
        self.assertTrue((self.root / "data/fulltext/S/a.html").exists())

    def test_emptied_source_folder_goes_but_the_flat_directory_stays(self):
        (self.root / "data/fulltext/B__2.html").write_text("x", encoding="utf-8")
        ml.cleanup(self.mapping, set(), self.root, apply=True)
        self.assertFalse((self.root / "data/fulltext/S").exists())
        self.assertTrue((self.root / "data/fulltext").is_dir())


if __name__ == "__main__":
    unittest.main()
