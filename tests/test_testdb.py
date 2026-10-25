"""Tests for src/tools/testdb.py, refresh_test_db.py and run_tests.py: the
guards, the dump command lines, the lock, the full-text symlink and the
helpers of the test runner. Only the lock tests touch a database (the
`.env.test` one, with a private lock name so a real test session is never
disturbed); they are skipped when it is not available."""
import http.server
import pathlib
import socket
import sys
import tempfile
import threading
import unittest
from unittest import mock

TOOLS = pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"
sys.path.insert(0, str(TOOLS))

import run_tests  # noqa: E402
import testdb  # noqa: E402


def env(name="h2regdocs", host="localhost", port="3306"):
    return {"DB_HOST": host, "DB_PORT": port, "DB_NAME": name, "DB_USER": "u", "DB_PASSWORD": "secret-pw"}


class GuardTestCase(unittest.TestCase):
    def test_target_must_end_with_test(self):
        with self.assertRaises(testdb.TestDbError):
            testdb.assert_safe_target(env("h2regdocs"), env("h2regdocs_staging"))

    def test_source_and_target_must_differ(self):
        with self.assertRaises(testdb.TestDbError):
            testdb.assert_safe_target(env("x_test"), env("x_test"))

    def test_a_test_database_next_to_the_real_one_is_accepted(self):
        testdb.assert_safe_target(env("h2regdocs"), env("h2regdocs_test"))

    def test_same_name_on_another_server_is_a_different_database(self):
        testdb.assert_safe_target(env("h2regdocs_test", host="a"), env("h2regdocs_test", host="b"))

    def test_read_env_reports_missing_keys_and_defaults_the_port(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / ".env"
            path.write_text("DB_HOST=localhost\nDB_NAME=x\n", encoding="utf-8")
            with self.assertRaises(testdb.TestDbError) as ctx:
                testdb.read_env(path)
            self.assertIn("DB_USER", str(ctx.exception))
            path.write_text("DB_HOST=h\nDB_NAME=x\nDB_USER=u\nDB_PASSWORD=p\n", encoding="utf-8")
            self.assertEqual(testdb.read_env(path)["DB_PORT"], "3306")


class DumpCommandTestCase(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(testdb, "_client", return_value="/usr/bin/mariadb-dump")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_editor_tables_are_left_out_of_the_data_dump_and_dumped_as_structure(self):
        data, structure = testdb.dump_commands(env(), ["Document", "User", "ReviewItem", "AuditLog"])
        self.assertIn("--ignore-table=h2regdocs.User", data)
        self.assertIn("--ignore-table=h2regdocs.ReviewItem", data)
        self.assertIn("--ignore-table=h2regdocs.AuditLog", data)
        self.assertIn("--no-data", structure)
        self.assertEqual(structure[-4:], ["h2regdocs", "User", "ReviewItem", "AuditLog"])

    def test_only_editor_tables_that_exist_are_mentioned(self):
        data, structure = testdb.dump_commands(env(), ["Document", "User"])
        self.assertEqual([a for a in data if a.startswith("--ignore-table")], ["--ignore-table=h2regdocs.User"])
        self.assertEqual(structure[-2:], ["h2regdocs", "User"])

    def test_no_structure_dump_without_editor_tables(self):
        data, structure = testdb.dump_commands(env(), ["Document"])
        self.assertIsNone(structure)
        self.assertNotIn("--no-data", data)

    def test_the_password_is_never_an_argument(self):
        data, structure = testdb.dump_commands(env(), ["Document", "User"])
        self.assertFalse(any("secret-pw" in arg for arg in data + structure))


class RefreshGuardTestCase(unittest.TestCase):
    def test_refuses_without_the_lock(self):
        with self.assertRaises(testdb.TestDbError) as ctx:
            testdb.refresh_test_db(env("h2regdocs"), env("h2regdocs_test"), None)
        self.assertIn("lock", str(ctx.exception))

    def test_refuses_when_the_lock_is_not_held_by_this_connection(self):
        lock = mock.Mock()
        lock.holds.return_value = False
        with self.assertRaises(testdb.TestDbError):
            testdb.refresh_test_db(env("h2regdocs"), env("h2regdocs_test"), lock)

    def test_refuses_a_non_test_target_before_anything_else(self):
        lock = mock.Mock()
        lock.holds.return_value = True
        with mock.patch.object(testdb, "list_tables") as list_tables:
            with self.assertRaises(testdb.TestDbError):
                testdb.refresh_test_db(env("h2regdocs"), env("h2regdocs"), lock)
            list_tables.assert_not_called()


class FulltextDirTestCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = pathlib.Path(tmp.name).resolve()
        self.main = root / "main"
        self.work = root / "work"
        (self.main / "data" / "fulltext" / "S").mkdir(parents=True)
        (self.main / "data" / "fulltext" / "S" / "a.html").write_text("x", encoding="utf-8")
        (self.work / "data").mkdir(parents=True)
        self.quiet = lambda *_: None

    def _ensure(self):
        return testdb.ensure_fulltext_dir(self.work, self.main, log=self.quiet)

    def test_missing_directory_becomes_a_symlink_to_the_main_tree(self):
        self.assertTrue(self._ensure())
        link = self.work / "data" / "fulltext"
        self.assertTrue(link.is_symlink())
        self.assertEqual(link.resolve(), (self.main / "data" / "fulltext").resolve())

    def test_empty_leftover_directory_is_replaced(self):
        (self.work / "data" / "fulltext").mkdir()
        self.assertTrue(self._ensure())
        self.assertTrue((self.work / "data" / "fulltext").is_symlink())

    def test_directory_with_content_is_left_alone(self):
        own = self.work / "data" / "fulltext"
        own.mkdir()
        (own / "mine.html").write_text("x", encoding="utf-8")
        self.assertTrue(self._ensure())
        self.assertFalse(own.is_symlink())

    def test_nothing_to_link_to_is_reported_not_raised(self):
        import shutil
        shutil.rmtree(self.main / "data" / "fulltext" / "S")
        messages = []
        self.assertFalse(testdb.ensure_fulltext_dir(self.work, self.main, log=messages.append))
        self.assertIn("warning", messages[0])
        self.assertFalse((self.work / "data" / "fulltext").exists())


class LocalFilesTestCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = pathlib.Path(tmp.name).resolve()
        self.main, self.work = root / "main", root / "work"
        self.main.mkdir()
        self.work.mkdir()

    def test_missing_file_is_linked_from_the_main_tree(self):
        (self.main / ".openapi_key").write_text("k", encoding="utf-8")
        missing = testdb.ensure_local_files(self.work, self.main, log=lambda *_: None)
        self.assertEqual(missing, [])
        self.assertEqual((self.work / ".openapi_key").read_text(encoding="utf-8"), "k")
        self.assertTrue((self.work / ".openapi_key").is_symlink())

    def test_an_existing_file_is_never_replaced(self):
        (self.main / ".openapi_key").write_text("main", encoding="utf-8")
        (self.work / ".openapi_key").write_text("own", encoding="utf-8")
        testdb.ensure_local_files(self.work, self.main, log=lambda *_: None)
        self.assertEqual((self.work / ".openapi_key").read_text(encoding="utf-8"), "own")

    def test_a_file_that_exists_nowhere_is_reported(self):
        self.assertEqual(testdb.ensure_local_files(self.work, self.main, log=lambda *_: None), [".openapi_key"])


class PortAndSmokeTestCase(unittest.TestCase):
    def test_port_is_free_only_while_nobody_listens(self):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            s.listen()
            port = s.getsockname()[1]
            self.assertFalse(testdb.port_is_free(port))
        self.assertTrue(testdb.port_is_free(port))

    def test_smoke_reports_every_page_that_is_not_200(self):
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200 if self.path == "/" else 404)
                self.end_headers()

            def log_message(self, *args):
                pass

        server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        failures = run_tests.smoke(f"http://127.0.0.1:{server.server_address[1]}", pages=("/", "/missing"))
        self.assertEqual(failures, ["/missing -> 404"])


class RunnerHelpersTestCase(unittest.TestCase):
    def test_database_backed_modules_are_separated_from_unit_tests(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("test_a", "test_admin", "test_search", "test_z"):
                (pathlib.Path(tmp) / f"{name}.py").write_text("", encoding="utf-8")
            (pathlib.Path(tmp) / "helper.py").write_text("", encoding="utf-8")
            unit, integration = run_tests.split_modules(tmp)
        self.assertEqual(unit, ["test_a", "test_z"])
        self.assertEqual(integration, ["test_admin", "test_search"])

    def test_session_environment_overrides_the_ambient_database_settings(self):
        with mock.patch.dict("os.environ", {"DB_NAME": "h2regdocs", "KEEP": "1"}):
            merged = run_tests.session_env(env("h2regdocs_test"))
        self.assertEqual(merged["DB_NAME"], "h2regdocs_test")
        self.assertEqual(merged["KEEP"], "1")


class LockTestCase(unittest.TestCase):
    """Live, against the `.env.test` database server — with a private lock
    name, never the one a real test session holds."""

    @classmethod
    def setUpClass(cls):
        try:
            cls.target = testdb.read_env(testdb.find_env_file(".env.test"))
            testdb.connect(cls.target).close()
        except Exception as e:  # no env file, or the server is unreachable
            raise unittest.SkipTest(f"test database not available: {e}")
        import os
        cls.name = f"h2db-test-suite-selftest-{os.getpid()}"

    def test_a_second_holder_is_refused_until_the_first_lets_go(self):
        with testdb.TestDbLock(self.target, name=self.name) as first:
            self.assertTrue(first.holds())
            with self.assertRaises(testdb.LockHeld):
                testdb.TestDbLock(self.target, name=self.name).__enter__()
        with testdb.TestDbLock(self.target, name=self.name) as again:
            self.assertTrue(again.holds())

    def test_a_lock_that_is_not_held_says_so(self):
        lock = testdb.TestDbLock(self.target, name=self.name)
        self.assertFalse(lock.holds())


if __name__ == "__main__":
    unittest.main()
