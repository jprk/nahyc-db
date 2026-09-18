"""Creates a new editor account in the `User` table (app/admin.py's
login system) — doc/PLAN.md §43, 2026-09-18, user-directed.

Supersedes `src/tools/create_editor_user.py` (removed) — same `[--apply]`
dry-run discipline as every `backfill_*.py` script, split from password
changes (see `dbuser_passwd.py`), and now also captures the editor's
human-readable `name` and contact `email`, not just their login.

No self-registration exists (and won't) — a small, trusted-user-only
feature is provisioned by hand.

Usage:
    .venv/bin/python src/db/dbuser_add.py <login> <name> <email> [--apply] [--env-file .env]
"""
import argparse
import getpass
import os
import pathlib
import re

import pymysql
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent

# Deliberately loose — a sanity check against an obvious typo, not a full
# RFC 5322 validator (which would reject plenty of real addresses anyway).
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


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
    parser.add_argument("login", help="login/username used to sign in")
    parser.add_argument("name", help="the editor's human-readable name")
    parser.add_argument("email", help="the editor's contact e-mail address")
    parser.add_argument("--apply", action="store_true",
                         help="write the new account to the database (default: dry-run report only)")
    parser.add_argument("--env-file", default=".env",
                         help="repo-root-relative dotenv file to read DB_* from (default: .env; "
                              "pass .env.test for a rehearsal database)")
    args = parser.parse_args()

    if not _EMAIL_RE.match(args.email):
        print(f"{args.email!r} doesn't look like a valid e-mail address — refusing to guess. "
              "No account created.")
        return

    conn = get_connection(args.env_file)
    cur = conn.cursor()

    cur.execute("SELECT id FROM User WHERE username=%s OR email=%s", (args.login, args.email))
    existing = cur.fetchone()
    if existing:
        print(f"A user with login {args.login!r} or e-mail {args.email!r} already exists — nothing to do.")
        conn.close()
        return

    password = getpass.getpass(f"Password for new editor {args.login!r} ({args.name} <{args.email}>): ")
    if not password:
        print("Empty password refused — no account created.")
        conn.close()
        return
    password_hash = generate_password_hash(password)

    print(f"Would create editor account {args.login!r} ({args.name} <{args.email}>).")
    if not args.apply:
        print("Dry run — pass --apply to write it.")
        conn.close()
        return

    cur.execute("INSERT INTO User (username, name, email, password_hash) VALUES (%s, %s, %s, %s)",
                (args.login, args.name, args.email, password_hash))
    conn.commit()
    print(f"Created editor account {args.login!r} ({args.name} <{args.email}>), id={cur.lastrowid}.")
    conn.close()


if __name__ == "__main__":
    main()
