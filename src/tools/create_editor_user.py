"""One-off provisioning of an editor account for the admin review UI
(`app/admin.py`) — doc/PLAN.md §42, 2026-09-18, user-directed.

No self-registration exists (and won't) — this small, trusted-user-only
feature is provisioned by hand, same discipline as every other
`backfill_*.py` script in this directory: `--apply` writes to the
database, its absence is a dry-run report only.

Usage:
    .venv/bin/python src/tools/create_editor_user.py <username> [--apply] [--env-file .env]
"""
import argparse
import getpass
import os
import pathlib

import pymysql
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent


def get_connection(env_file):
    load_dotenv(REPO_ROOT / env_file, override=True)
    return pymysql.connect(
        host=os.environ["DB_HOST"], port=int(os.environ["DB_PORT"]),
        user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"], cursorclass=pymysql.cursors.DictCursor,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("username")
    parser.add_argument("--apply", action="store_true",
                         help="write the new account to the database (default: dry-run report only)")
    parser.add_argument("--env-file", default=".env",
                         help="repo-root-relative dotenv file to read DB_* from (default: .env; "
                              "pass .env.test for a rehearsal database)")
    args = parser.parse_args()

    conn = get_connection(args.env_file)
    cur = conn.cursor()

    cur.execute("SELECT id FROM User WHERE username=%s", (args.username,))
    if cur.fetchone():
        print(f"A user named {args.username!r} already exists — nothing to do.")
        conn.close()
        return

    password = getpass.getpass(f"Password for new editor {args.username!r}: ")
    if not password:
        print("Empty password refused — no account created.")
        conn.close()
        return
    password_hash = generate_password_hash(password)

    print(f"Would create editor account {args.username!r}.")
    if not args.apply:
        print("Dry run — pass --apply to write it.")
        conn.close()
        return

    cur.execute("INSERT INTO User (username, password_hash) VALUES (%s, %s)",
                (args.username, password_hash))
    conn.commit()
    print(f"Created editor account {args.username!r} (id={cur.lastrowid}).")
    conn.close()


if __name__ == "__main__":
    main()
