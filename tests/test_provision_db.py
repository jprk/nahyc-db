import os
import sys
import unittest
from unittest import mock

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "tools"))

from provision_db import (REPO_ROOT, build_drop_tables_sql, build_provisioning_sql,
                          load_app_config, resolve_admin_credentials, sql_string_literal)


class SqlStringLiteralTestCase(unittest.TestCase):
    def test_plain_value(self):
        self.assertEqual(sql_string_literal("changeme"), "'changeme'")

    def test_single_quote_is_escaped(self):
        # A generated literal must survive a password containing a quote
        # — this SQL is built, not typed by a human who'd avoid it.
        self.assertEqual(sql_string_literal("it's"), "'it\\'s'")

    def test_backslash_is_escaped(self):
        self.assertEqual(sql_string_literal("back\\slash"), "'back\\\\slash'")

    def test_empty_password(self):
        self.assertEqual(sql_string_literal(""), "''")


class BuildProvisioningSqlTestCase(unittest.TestCase):
    """doc/PLAN.md §19/§20, 2026-09-17: the app's own account is CREATEd
    with rights scoped to its own database ONLY — never a global CREATE
    DATABASE privilege, which this project's real deployment account
    doesn't have."""

    def setUp(self):
        self.sql = build_provisioning_sql("h2regdocs", "h2regdocs", "s3cret", "localhost")

    def test_creates_the_database(self):
        self.assertIn("CREATE DATABASE IF NOT EXISTS `h2regdocs`", self.sql)

    def test_creates_the_app_user_scoped_to_its_own_host(self):
        self.assertIn("CREATE USER IF NOT EXISTS 'h2regdocs'@'localhost'", self.sql)

    def test_password_is_reapplied_so_a_changed_env_password_takes_effect(self):
        # CREATE USER IF NOT EXISTS silently no-ops on an existing user,
        # so a password change in .env needs the separate ALTER USER to
        # actually take effect on a re-run.
        self.assertIn("ALTER USER 'h2regdocs'@'localhost' IDENTIFIED BY 's3cret'", self.sql)

    def test_grant_is_scoped_to_this_database_only(self):
        self.assertIn("GRANT ALL PRIVILEGES ON `h2regdocs`.* TO 'h2regdocs'@'localhost'", self.sql)
        self.assertNotIn("ON *.*", self.sql)

    def test_password_is_properly_quoted_not_interpolated_raw(self):
        sql = build_provisioning_sql("db", "user", "pa'ss", "localhost")
        self.assertIn("IDENTIFIED BY 'pa\\'ss'", sql)

    def test_app_host_is_configurable(self):
        sql = build_provisioning_sql("h2regdocs", "h2regdocs", "s3cret", "%")
        self.assertIn("'h2regdocs'@'%'", sql)


class ResolveAdminCredentialsTestCase(unittest.TestCase):
    """Precedence: --admin-user/--admin-password, then DB_ADMIN_USER/
    DB_ADMIN_PASSWORD, then an interactive prompt — so a bare invocation
    never silently reuses the app's own narrow .env credentials."""

    def test_cli_args_win(self):
        config = resolve_admin_credentials(
            "root", "cli-pw", "localhost", "3306",
            env={"DB_ADMIN_USER": "envuser", "DB_ADMIN_PASSWORD": "env-pw"},
            prompt_user=lambda *_: self.fail("should not prompt"),
            prompt_password=lambda *_: self.fail("should not prompt"))
        self.assertEqual(config, {"host": "localhost", "port": "3306",
                                  "user": "root", "password": "cli-pw"})

    def test_env_vars_used_when_no_cli_args(self):
        config = resolve_admin_credentials(
            None, None, "localhost", "3306",
            env={"DB_ADMIN_USER": "envuser", "DB_ADMIN_PASSWORD": "env-pw"},
            prompt_user=lambda *_: self.fail("should not prompt"),
            prompt_password=lambda *_: self.fail("should not prompt"))
        self.assertEqual(config["user"], "envuser")
        self.assertEqual(config["password"], "env-pw")

    def test_prompts_when_nothing_else_given(self):
        config = resolve_admin_credentials(
            None, None, "localhost", "3306", env={},
            prompt_user=lambda *_: "typed-admin",
            prompt_password=lambda *_: "typed-pw")
        self.assertEqual(config["user"], "typed-admin")
        self.assertEqual(config["password"], "typed-pw")

    def test_blank_prompted_username_defaults_to_root(self):
        config = resolve_admin_credentials(
            None, None, "localhost", "3306", env={},
            prompt_user=lambda *_: "",
            prompt_password=lambda *_: "typed-pw")
        self.assertEqual(config["user"], "root")

    def test_empty_string_admin_password_is_accepted_not_re_prompted(self):
        # A genuinely empty admin password (unusual, but a passwordless
        # local root account is real) must not be treated as "unset".
        config = resolve_admin_credentials(
            "root", "", "localhost", "3306", env={},
            prompt_password=lambda *_: self.fail("should not prompt"))
        self.assertEqual(config["password"], "")

    def test_targets_the_same_host_and_port_as_the_app_config(self):
        # The admin connects to the SAME server as the app — that's
        # where the database needs to be created — just as a different,
        # more privileged account.
        config = resolve_admin_credentials(
            "root", "pw", "db.example.org", "3307", env={})
        self.assertEqual(config["host"], "db.example.org")
        self.assertEqual(config["port"], "3307")


class BuildDropTablesSqlTestCase(unittest.TestCase):
    """--schema-only clears a database/user created ahead of time by
    someone else, using ONLY the app account (which already has full
    rights on its own database — no admin needed for a DROP)."""

    def test_empty_list_yields_nothing_to_run(self):
        self.assertEqual(build_drop_tables_sql([]), "")

    def test_drops_every_named_table_in_one_statement(self):
        sql = build_drop_tables_sql(["Document", "node_document"])
        self.assertIn("DROP TABLE IF EXISTS `Document`, `node_document`;", sql)

    def test_suspends_foreign_key_checks_around_the_drop(self):
        # Cross-table FKs (e.g. node_document -> Document) would otherwise
        # block dropping tables in an arbitrary order.
        sql = build_drop_tables_sql(["Document"])
        self.assertIn("SET FOREIGN_KEY_CHECKS=0;", sql)
        self.assertIn("SET FOREIGN_KEY_CHECKS=1;", sql)


class LoadAppConfigTestCase(unittest.TestCase):
    """doc/PLAN.md §19/§20, 2026-09-16: --env-file lets a second,
    disposable database/user pair (e.g. .env.test) be provisioned for a
    live end-to-end rehearsal without ever touching the real .env."""

    def setUp(self):
        self.env_path = REPO_ROOT / ".env.provision_db_test_case_scratch"
        self.env_path.write_text(
            "DB_HOST=testhost\nDB_PORT=3307\nDB_NAME=h2regdocs_test\n"
            "DB_USER=h2regdocs_test\nDB_PASSWORD=test-pw\n")
        self.addCleanup(self.env_path.unlink)
        # load_app_config() calls load_dotenv(..., override=True) so a
        # real --env-file invocation always wins over whatever a prior
        # .env load already put in os.environ (needed so
        # `--env-file .env.test` can't silently keep stale real-.env
        # values within the same process) — but that means calling it
        # here would otherwise leak DB_* into every other test sharing
        # this unittest process (e.g. test_search.py, which then tries to
        # connect to this test's fake "testhost"). Snapshot and restore
        # the whole environment around this one test.
        self._env_patcher = mock.patch.dict(os.environ, clear=False)
        self._env_patcher.start()
        self.addCleanup(self._env_patcher.stop)

    def test_reads_the_given_env_file_not_the_real_env(self):
        config = load_app_config(self.env_path.name)
        self.assertEqual(config, {"host": "testhost", "port": "3307",
                                  "user": "h2regdocs_test", "password": "test-pw",
                                  "database": "h2regdocs_test"})


if __name__ == "__main__":
    unittest.main()
