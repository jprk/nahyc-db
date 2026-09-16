"""One-time provisioning: create the h2regdocs MariaDB database and the
dedicated application user the app connects with day to day, then apply
the V01 baseline schema followed by the Konsolidace migration.

doc/PLAN.md §19/§20, 2026-09-17 (user-directed): the app's OWN credentials
(DB_USER/DB_PASSWORD in .env) must NEVER need a global CREATE DATABASE
privilege — this project's real deployment account doesn't have one
(confirmed via SHOW GRANTS: scoped to the h2regdocs database only), and
that's the correct, narrower shape for an application account. Two
separate credential sets, never mixed:

* ADMIN — used ONLY by this script, ONLY for this one-time bootstrap.
  Needs privilege to CREATE DATABASE, CREATE USER and GRANT. Never read
  from .env (which is git-ignored but still a persistent file on disk,
  and .env is meant to describe the APP's identity, not an admin's) —
  supplied via --admin-user/--admin-password, the DB_ADMIN_USER/
  DB_ADMIN_PASSWORD environment variables, or an interactive prompt if
  neither is given, so a bare invocation never silently reuses the app's
  own deliberately-narrow credentials for a step that needs more.
* APP — DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD from .env, exactly
  as every other script in this repo already reads them. This script
  CREATEs that user (if it doesn't exist yet) and grants it full rights
  on DB_NAME ONLY — never anything wider. The schema itself is then
  applied AS that user, not as admin: a real end-to-end check that the
  just-granted privileges are actually sufficient for normal operation,
  not just assumed to be.

Applies schema files via the `mariadb` CLI client (subprocess) rather than
parsing/splitting SQL in Python — the schema files contain inline comments
with embedded semicolons (e.g. node_branch's `-- ...popis; strojová...`),
which a naive ';'-split gets wrong. The CLI's own statement parser handles
this correctly, the same way it would for any DBA-applied dump. The
database/user bootstrap SQL is sent over stdin for the same reason AND so
the app password is never a subprocess argument (visible via `ps` while
the command runs) — only MYSQL_PWD, an environment variable, carries a
password on the wire to either account.

Safe to re-run: CREATE DATABASE / CREATE USER both use IF NOT EXISTS, and
the app user's password is (re-)applied via ALTER USER on every run, so a
changed .env password takes effect without needing to drop the user
first. The schema files themselves are still not idempotent (CREATE
TABLE without IF NOT EXISTS) — running this twice against an
already-provisioned database will fail applying the schema on the second
pass. That is intentional: this is a bootstrap script, not a migration
tool.

Usage:
    .venv/bin/python src/tools/provision_db.py
    .venv/bin/python src/tools/provision_db.py --admin-user root
    .venv/bin/python src/tools/provision_db.py --admin-user root --app-host '%'
    .venv/bin/python src/tools/provision_db.py --dry-run   # print the SQL, run nothing

    # Provision a second, disposable database/user pair for a live
    # end-to-end rehearsal — reads DB_HOST/PORT/NAME/USER/PASSWORD from
    # .env.test (repo-root, gitignored, same shape as .env.example, e.g.
    # DB_NAME=h2regdocs_test / DB_USER=h2regdocs_test) instead of .env,
    # so the real database/user are never touched:
    .venv/bin/python src/tools/provision_db.py --env-file .env.test

    # --schema-only: the database and app user ALREADY exist (e.g. a DBA
    # created them ahead of time, as for a test rehearsal) — skip the
    # admin bootstrap entirely (no admin credentials needed/asked for),
    # drop whatever tables are currently in DB_NAME, and reapply the
    # schema, all connected as the app account alone:
    .venv/bin/python src/tools/provision_db.py --env-file .env.test --schema-only
"""
import argparse
import getpass
import os
import pathlib
import subprocess

from dotenv import load_dotenv

BASE_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent
KONSOLIDACE_DIR = REPO_ROOT / "doc" / "konsolidace"

SCHEMA_FILES = [
    KONSOLIDACE_DIR / "V01-baseline-schema.sql",
    KONSOLIDACE_DIR / "Konsolidace-DB-schema.sql",
]


def load_app_config(env_file=".env"):
    """The app's OWN connection identity (DB_HOST/PORT/NAME/USER/PASSWORD
    from `env_file`, repo-root-relative) — the account provisioning
    CREATEs and grants database-scoped rights to, never the account
    provisioning itself runs as. `env_file` defaults to the real `.env`;
    pass e.g. `.env.test` to provision a second, disposable database/user
    pair for a live end-to-end rehearsal without ever touching the real
    one (doc/PLAN.md §19/§20)."""
    load_dotenv(REPO_ROOT / env_file, override=True)
    return {
        "host": os.environ["DB_HOST"],
        "port": os.environ["DB_PORT"],
        "user": os.environ["DB_USER"],
        "password": os.environ["DB_PASSWORD"],
        "database": os.environ["DB_NAME"],
    }


def resolve_admin_credentials(cli_user, cli_password, app_host, app_port,
                              env=os.environ, prompt_user=input, prompt_password=getpass.getpass):
    """The ADMIN identity for this one-time bootstrap, connecting to the
    SAME server (host/port) the app config points at — that's where the
    database needs to exist — but as a different, more privileged
    account. Precedence: --admin-user/--admin-password, then
    DB_ADMIN_USER/DB_ADMIN_PASSWORD, then an interactive prompt.
    `prompt_user`/`prompt_password` are injectable so this stays testable
    without a real terminal."""
    user = cli_user or env.get("DB_ADMIN_USER")
    if not user:
        user = prompt_user(f"MariaDB admin user for {app_host}:{app_port} [root]: ").strip() or "root"
    password = cli_password if cli_password is not None else env.get("DB_ADMIN_PASSWORD")
    if password is None:
        password = prompt_password(f"MariaDB admin password for {user}@{app_host}: ")
    return {"host": app_host, "port": app_port, "user": user, "password": password}


def sql_string_literal(value):
    """A single-quoted SQL string literal for `value`, with backslash and
    quote characters escaped (MariaDB's default NO_BACKSLASH_ESCAPES=off
    behaviour) — used for the app password and identifiers that might
    contain either, since this SQL is generated, not typed by a human who
    would naturally avoid the problem."""
    escaped = value.replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"


def build_provisioning_sql(db_name, app_user, app_password, app_host):
    """The bootstrap SQL: create the database, create the app's own user
    if it doesn't exist, (re-)apply its password unconditionally so a
    changed .env password takes effect on a re-run, and grant it rights
    on THIS DATABASE ONLY — never anything wider. Pure and testable; no
    I/O, no f-string injection of anything that isn't itself already
    quoted via sql_string_literal() or backtick-quoted below."""
    password_literal = sql_string_literal(app_password)
    return (
        f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
        "CHARACTER SET utf8mb4 COLLATE utf8mb4_czech_ci;\n"
        f"CREATE USER IF NOT EXISTS '{app_user}'@'{app_host}' IDENTIFIED BY {password_literal};\n"
        f"ALTER USER '{app_user}'@'{app_host}' IDENTIFIED BY {password_literal};\n"
        f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{app_user}'@'{app_host}';\n"
        "FLUSH PRIVILEGES;\n"
    )


def build_drop_tables_sql(table_names):
    """SQL to drop `table_names` (as returned by SHOW TABLES) in one
    statement, with foreign-key checks suspended around it — the schema
    files have cross-table FKs (e.g. node_document -> Document), so
    dropping in an arbitrary order would otherwise fail. Empty input
    yields "" (nothing to drop, e.g. a freshly created database)."""
    if not table_names:
        return ""
    quoted = ", ".join(f"`{name}`" for name in table_names)
    return (
        "SET FOREIGN_KEY_CHECKS=0;\n"
        f"DROP TABLE IF EXISTS {quoted};\n"
        "SET FOREIGN_KEY_CHECKS=1;\n"
    )


def list_existing_tables(config):
    """Table names currently in `config["database"]`, connected as
    `config`'s own account — used by --schema-only to clear a database
    that already exists (created ahead of time by someone else) before
    reapplying the non-idempotent schema files."""
    output = run_mariadb(config, [config["database"], "-N", "-e", "SHOW TABLES;"])
    return [line for line in output.splitlines() if line.strip()]


def run_mariadb(config, args, stdin_path=None, input_text=None):
    """Runs the `mariadb` CLI. Exactly one of `stdin_path` (a file, for
    the schema dumps) or `input_text` (a generated SQL string, for the
    bootstrap step — never a file on disk, so a transient credential
    never touches the filesystem) may be given."""
    assert not (stdin_path and input_text is not None), "pass at most one of stdin_path/input_text"
    cmd = ["mariadb", "-h", config["host"], "-P", str(config["port"]), "-u", config["user"], *args]
    env = os.environ.copy()
    env["MYSQL_PWD"] = config["password"]  # avoid exposing the password in argv/ps
    stdin = open(stdin_path, "rb") if stdin_path else None
    try:
        result = subprocess.run(
            cmd, stdin=stdin, input=input_text.encode() if input_text is not None else None,
            env=env, capture_output=True)
    finally:
        if stdin:
            stdin.close()
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode(errors="replace"))
    return result.stdout.decode(errors="replace")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--admin-user", help="MariaDB admin account for this one-time bootstrap "
                                             "(default: prompt, or DB_ADMIN_USER)")
    parser.add_argument("--admin-password", help="MariaDB admin password (default: prompt, or "
                                                 "DB_ADMIN_PASSWORD — prefer the prompt or the "
                                                 "environment variable over this flag, which is "
                                                 "visible in shell history/ps)")
    parser.add_argument("--app-host", default="localhost",
                         help="host pattern the APP's own MariaDB user is scoped to connect FROM "
                              "(not DB_HOST, which is where the server IS) — 'localhost' when "
                              "the app and the database run on the same machine (the default, "
                              "and this project's own real deployment shape), '%%' for any host, "
                              "or a specific hostname/IP/subnet for anything else")
    parser.add_argument("--dry-run", action="store_true",
                         help="print the bootstrap SQL and the schema files that would be "
                              "applied, but run nothing")
    parser.add_argument("--env-file", default=".env",
                         help="repo-root-relative dotenv file to read DB_HOST/PORT/NAME/USER/"
                              "PASSWORD from (default: .env). Pass '.env.test' to provision a "
                              "second, disposable database/user pair for a live rehearsal "
                              "without touching the real .env")
    parser.add_argument("--schema-only", action="store_true",
                         help="the database and app user ALREADY exist (created ahead of time "
                              "by someone else) — skip the admin bootstrap entirely (no admin "
                              "credentials needed or asked for), drop any existing tables in "
                              "DB_NAME, and reapply the schema, connected as the app account "
                              "alone")
    args = parser.parse_args()

    app_config = load_app_config(args.env_file)
    db_name = app_config["database"]

    if args.schema_only:
        if args.dry_run:
            print("--- schema-only mode: app account only, no admin needed ---")
            print(f"Would drop any existing tables in `{db_name}` and reapply:")
            for schema_file in SCHEMA_FILES:
                print(f"  {schema_file.relative_to(REPO_ROOT)}")
            return

        existing_tables = list_existing_tables(app_config)
        if existing_tables:
            run_mariadb(app_config, [db_name], input_text=build_drop_tables_sql(existing_tables))
            print(f"Dropped {len(existing_tables)} existing table(s) in `{db_name}`.")
        else:
            print(f"`{db_name}` has no existing tables — nothing to drop.")

        for schema_file in SCHEMA_FILES:
            print(f"Applying {schema_file.relative_to(REPO_ROOT)} ...")
            run_mariadb(app_config, [db_name], stdin_path=schema_file)

        print("Schema reapplied.")
        return

    bootstrap_sql = build_provisioning_sql(db_name, app_config["user"], app_config["password"],
                                           args.app_host)

    if args.dry_run:
        # The real password is never printed, even in a dry run.
        redacted = bootstrap_sql.replace(sql_string_literal(app_config["password"]), "'***'")
        print("--- bootstrap SQL (admin) ---")
        print(redacted)
        print("--- schema files (app user) ---")
        for schema_file in SCHEMA_FILES:
            print(f"  {schema_file.relative_to(REPO_ROOT)}")
        return

    admin_config = resolve_admin_credentials(args.admin_user, args.admin_password,
                                             app_config["host"], app_config["port"])

    run_mariadb(admin_config, [], input_text=bootstrap_sql)
    print(f"Database `{db_name}` and user `{app_config['user']}`@`{args.app_host}` ready.")

    for schema_file in SCHEMA_FILES:
        print(f"Applying {schema_file.relative_to(REPO_ROOT)} ...")
        run_mariadb(app_config, [db_name], stdin_path=schema_file)

    print("Provisioning complete.")


if __name__ == "__main__":
    main()
