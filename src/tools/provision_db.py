"""One-time provisioning: create the h2regdocs MariaDB database and apply
the V01 baseline schema followed by the Konsolidace migration on top of it.

Credentials come from a repo-root .env (DB_HOST, DB_PORT, DB_NAME, DB_USER,
DB_PASSWORD) — see doc/PLAN.md Step 0.

Applies schema files via the `mariadb` CLI client (subprocess) rather than
parsing/splitting SQL in Python — the schema files contain inline comments
with embedded semicolons (e.g. node_branch's `-- ...popis; strojová...`),
which a naive ';'-split gets wrong. The CLI's own statement parser handles
this correctly, the same way it would for any DBA-applied dump.

Safe to re-run: CREATE DATABASE uses IF NOT EXISTS, but the schema files
themselves are not idempotent (CREATE TABLE without IF NOT EXISTS) — running
this twice against an already-provisioned database will fail on the second
pass. That is intentional: this is a bootstrap script, not a migration tool.
"""
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


def load_config():
    load_dotenv(REPO_ROOT / ".env")
    return {
        "host": os.environ["DB_HOST"],
        "port": os.environ["DB_PORT"],
        "user": os.environ["DB_USER"],
        "password": os.environ["DB_PASSWORD"],
        "database": os.environ["DB_NAME"],
    }


def run_mariadb(config, args, stdin_path=None):
    cmd = ["mariadb", "-h", config["host"], "-P", config["port"], "-u", config["user"], *args]
    env = os.environ.copy()
    env["MYSQL_PWD"] = config["password"]  # avoid exposing the password in argv/ps
    stdin = open(stdin_path, "rb") if stdin_path else None
    try:
        result = subprocess.run(cmd, stdin=stdin, env=env, capture_output=True)
    finally:
        if stdin:
            stdin.close()
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode(errors="replace"))
    return result.stdout.decode(errors="replace")


def main():
    config = load_config()
    db_name = config["database"]

    run_mariadb(config, [
        "-e",
        f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
        "CHARACTER SET utf8mb4 COLLATE utf8mb4_czech_ci",
    ])
    print(f"Database `{db_name}` ready.")

    for schema_file in SCHEMA_FILES:
        print(f"Applying {schema_file.relative_to(REPO_ROOT)} ...")
        run_mariadb(config, [db_name], stdin_path=schema_file)

    print("Provisioning complete.")


if __name__ == "__main__":
    main()
