"""Backs up a database (default: the one of `.env`, the live `h2regdocs`) to
`backups/<database>_<YYYYmmdd_HHMMSS>_<reason>.sql.gz` in the main working tree —
the naming the backups made by hand so far use. The dump runs in one
transaction (`--single-transaction`), so the database stays readable and writable
meanwhile; the password travels in MYSQL_PWD, never on the command line. Prints
the path of the backup; the database is only read.

Usage: .venv/bin/python src/tools/backup_db.py --reason before_harvest [--env-file FILE]
"""
import argparse
import datetime
import gzip
import os
import pathlib
import re
import subprocess
import sys

import testdb


def backup_path(directory, database, reason, now=None):
    stamp = (now or datetime.datetime.now()).strftime("%Y%m%d_%H%M%S")
    reason = re.sub(r"[^A-Za-z0-9_-]+", "_", reason).strip("_") or "backup"
    return pathlib.Path(directory) / f"{database}_{stamp}_{reason}.sql.gz"


def dump_command(env):
    return [testdb._client("mariadb-dump", "mysqldump"), *testdb._cli_args(env), "--single-transaction",
            "--routines", env["DB_NAME"]]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--reason", required=True, help="why the backup is made (part of the file name)")
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--dir", default=None, help="target directory (default backups/ of the main working tree)")
    args = parser.parse_args(argv)
    env = testdb.read_env(args.env_file or testdb.find_env_file(".env"))
    env.setdefault("DB_PORT", "3306")
    directory = pathlib.Path(args.dir or testdb.main_worktree_root() / "backups")
    directory.mkdir(parents=True, exist_ok=True)
    path = backup_path(directory, env["DB_NAME"], args.reason)
    partial = path.with_name(path.name + ".part")
    with gzip.open(partial, "wb") as out:
        process = subprocess.Popen(dump_command(env), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   env=dict(os.environ, MYSQL_PWD=env["DB_PASSWORD"]))
        for chunk in iter(lambda: process.stdout.read(1 << 20), b""):
            out.write(chunk)
        error = process.stderr.read().decode("utf-8", "replace").strip()
        if process.wait() != 0:
            partial.unlink(missing_ok=True)
            print(f"backup failed: {error[:500]}", file=sys.stderr)
            return 1
    partial.rename(path)
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
