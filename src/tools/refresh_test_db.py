"""Replaces the contents of the test database (`.env.test`, `h2regdocs_test`)
with a copy of the main database (`.env`, `h2regdocs`).

The main database is only read (a `mariadb-dump`). The editor tables (`User`,
`ReviewItem`, `AuditLog`) are copied as structure only — the test database must
never hold the password hashes of real editors. Needs no admin credentials: the
test account owns its own database. Takes the server-wide test-suite lock for
the duration, and refuses to run while another test run holds it.

This is not `provision_db.py`: that one creates an empty database and account
once, with admin rights, and fails when run twice. This one is run before every
test session.

Usage:
    .venv/bin/python src/tools/refresh_test_db.py
    .venv/bin/python src/tools/refresh_test_db.py --wait 120   # wait for another run
"""
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testdb  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--source-env", default=".env", help="env file of the database to copy (read only)")
    parser.add_argument("--target-env", default=".env.test", help="env file of the test database (overwritten)")
    parser.add_argument("--wait", type=int, default=0,
                        help="seconds to wait for a test run that holds the lock (default: fail at once)")
    args = parser.parse_args(argv)
    try:
        source = testdb.read_env(testdb.find_env_file(args.source_env))
        target = testdb.read_env(testdb.find_env_file(args.target_env))
        testdb.assert_safe_target(source, target)
        with testdb.TestDbLock(target, wait=args.wait) as lock:
            testdb.refresh_test_db(source, target, lock)
    except testdb.TestDbError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
