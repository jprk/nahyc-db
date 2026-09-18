"""Updates the password for an existing editor account (the `User`
table, app/admin.py's login system) — doc/PLAN.md §43, 2026-09-18,
user-directed.

Deliberately separate from `dbuser_add.py` (creating a new account) —
a password change is its own, narrower operation, requiring the account
to already exist rather than silently creating one.

Usage:
    .venv/bin/python src/db/dbuser_passwd.py <login> [--apply] [--env-file .env]
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
    parser.add_argument("login", help="login/username of the existing account")
    parser.add_argument("--apply", action="store_true",
                         help="write the new password to the database (default: dry-run report only)")
    parser.add_argument("--env-file", default=".env",
                         help="repo-root-relative dotenv file to read DB_* from (default: .env; "
                              "pass .env.test for a rehearsal database)")
    args = parser.parse_args()

    conn = get_connection(args.env_file)
    cur = conn.cursor()

    cur.execute("SELECT id, name, email FROM User WHERE username=%s", (args.login,))
    user = cur.fetchone()
    if not user:
        print(f"No user logging in as {args.login!r} exists — nothing to do.")
        conn.close()
        return

    password = getpass.getpass(f"New password for {args.login!r} ({user['name']} <{user['email']}>): ")
    if not password:
        print("Empty password refused — password not changed.")
        conn.close()
        return
    confirm = getpass.getpass("Confirm new password: ")
    if password != confirm:
        print("Passwords did not match — password not changed.")
        conn.close()
        return
    password_hash = generate_password_hash(password)

    print(f"Would update the password for {args.login!r} ({user['name']}).")
    if not args.apply:
        print("Dry run — pass --apply to write it.")
        conn.close()
        return

    cur.execute("UPDATE User SET password_hash=%s WHERE id=%s", (password_hash, user["id"]))
    conn.commit()
    print(f"Password updated for {args.login!r}.")
    conn.close()


if __name__ == "__main__":
    main()
