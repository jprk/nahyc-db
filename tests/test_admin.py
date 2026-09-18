"""Live-DB integration test for app/admin.py (doc/PLAN.md §42,
2026-09-18) — the full login -> propose -> (different editor) confirm ->
audit-log path, the one behavior that genuinely can't be meaningfully
faked with a mocked cursor.

**Deliberately targets `.env.test`, never the real `.env`/production
`h2regdocs`** — unlike `test_search.py`'s read-only checks, this test
WRITES (a `Document` row, `ReviewItem`s, `AuditLog` rows). `os.environ`
is saved and restored around the whole test class so this doesn't leak
into any other test running in the same `unittest discover` process, and
every write is additionally guarded by a hard assertion that `DB_NAME`
really is the test database before touching it — a mistaken write
against production is exactly the kind of thing this project's
established discipline treats as unacceptable.

Requires `.venv/bin/python src/tools/provision_db.py --env-file
.env.test --schema-only` to have been run at least once (creates the
`User`/`ReviewItem`/`AuditLog` tables this test needs) — skipped, not
failed, if `.env.test` doesn't exist at all, so a fresh checkout without
a rehearsal database doesn't break the suite. `setUpClass` always starts
from a clean slate for its own fixtures (deletes then recreates its
`alice`/`bob` test users and its own test `Document` row) rather than
reusing whatever a previous run left behind — found live, this test is
NOT safely re-runnable against a non-empty rehearsal database otherwise
(a leftover already-`confirmed` `ReviewItem` from a prior run made a
second run fail, even though the app itself was behaving correctly).
"""
import os
import pathlib
import sys
import unittest

from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.admin import recompute_needs_review  # noqa: E402

ENV_TEST_PATH = REPO_ROOT / ".env.test"


class RecomputeNeedsReviewTestCase(unittest.TestCase):
    """Pure logic — reuses `init_db.py`'s own `is_garbled_znacka`/
    `is_fragment_title` checks directly, so a confirmed fix is judged by
    the identical rule that flagged it in the first place."""

    def test_all_three_reasons_can_apply_at_once(self):
        needs_review, reason = recompute_needs_review("- 2024.09", "- fragment", "")
        self.assertTrue(needs_review)
        self.assertIn("značka není platné označení dokumentu", reason)
        self.assertIn("název vypadá jako useknutý fragment textu", reason)
        self.assertIn("chybí popis/anotace dokumentu", reason)

    def test_all_fixed_clears_needs_review(self):
        needs_review, reason = recompute_needs_review(
            "266/1994 Sb.", "Zákon o dráhách", "A real description.")
        self.assertFalse(needs_review)
        self.assertIsNone(reason)

    def test_partial_fix_still_flags_remaining_reason(self):
        needs_review, reason = recompute_needs_review("266/1994 Sb.", "Zákon o dráhách", "")
        self.assertTrue(needs_review)
        self.assertEqual(reason, "chybí popis/anotace dokumentu")


class AdminReviewWorkflowTestCase(unittest.TestCase):
    ALICE_PASSWORD = "alice-test-password"
    BOB_PASSWORD = "bob-test-password"

    @classmethod
    def setUpClass(cls):
        if not ENV_TEST_PATH.exists():
            raise unittest.SkipTest(".env.test not found — no rehearsal database configured")
        cls._saved_environ = dict(os.environ)
        load_dotenv(ENV_TEST_PATH, override=True)
        if os.environ.get("DB_NAME") != "h2regdocs_test":
            raise unittest.SkipTest(".env.test does not point at h2regdocs_test — refusing to guess")

        # Imported only now, after the environment points at the test
        # database — app/app.py's own module-level load_dotenv(".env")
        # would otherwise have already run against production.
        from app.app import app
        cls.app = app
        cls.client = app.test_client()

        import pymysql
        cls.conn = pymysql.connect(
            host=os.environ["DB_HOST"], port=int(os.environ["DB_PORT"]),
            user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
            database=os.environ["DB_NAME"], cursorclass=pymysql.cursors.DictCursor,
        )
        # Without this, MariaDB's REPEATABLE READ default pins this
        # connection's own transaction snapshot at its first SELECT —
        # it would never see writes the Flask app under test commits on
        # its OWN, separate connection (found live: the app's confirm()
        # write genuinely landed, but this test's verification query
        # kept reading the pre-write snapshot and reported it as missing).
        cls.conn.autocommit(True)
        cls._assert_test_database()

        # Always starts from a clean slate for its own fixtures, rather
        # than reusing whatever a PREVIOUS run left behind — found live:
        # reusing an existing (already-`confirmed`) ReviewItem/Document
        # combination from a prior run made this test fail the second
        # time it ran against a non-empty rehearsal database, even
        # though the app itself was behaving correctly.
        _TEST_DOC_TITLE = "Test doc for admin workflow"
        with cls.conn.cursor() as cur:
            cur.execute("DELETE FROM AuditLog WHERE record_id IN "
                        "(SELECT id FROM Document WHERE title=%s)", (_TEST_DOC_TITLE,))
            cur.execute("DELETE FROM ReviewItem WHERE document_id IN "
                        "(SELECT id FROM Document WHERE title=%s)", (_TEST_DOC_TITLE,))
            cur.execute("DELETE FROM Document WHERE title=%s", (_TEST_DOC_TITLE,))
            cur.execute("DELETE FROM User WHERE username IN ('alice', 'bob')")

            cur.execute("INSERT INTO Document (title, needs_review, review_reason) "
                        "VALUES (%s, 1, 'chybí popis/anotace dokumentu')", (_TEST_DOC_TITLE,))
            cls.document_id = cur.lastrowid

            for username, password in (("alice", cls.ALICE_PASSWORD), ("bob", cls.BOB_PASSWORD)):
                cur.execute("INSERT INTO User (username, password_hash) VALUES (%s, %s)",
                            (username, generate_password_hash(password)))

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "conn"):
            cls.conn.close()
        if hasattr(cls, "_saved_environ"):
            os.environ.clear()
            os.environ.update(cls._saved_environ)

    @classmethod
    def _assert_test_database(cls):
        assert os.environ["DB_NAME"] == "h2regdocs_test", (
            "Refusing to run a WRITE test against a database that isn't h2regdocs_test")

    def _login(self, username, password):
        return self.client.post("/admin/login", data={"username": username, "password": password},
                                 follow_redirects=True)

    def test_full_propose_and_confirm_workflow(self):
        self._assert_test_database()

        # Not logged in -> redirected to login.
        resp = self.client.get("/admin/review")
        self.assertEqual(resp.status_code, 302)

        # Alice logs in and proposes a fix.
        resp = self._login("alice", self.ALICE_PASSWORD)
        self.assertEqual(resp.status_code, 200)
        resp = self.client.post(f"/admin/review/{self.document_id}/edit",
                                 data={"anotace_poznamka": "A real description now."},
                                 follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        with self.conn.cursor() as cur:
            cur.execute("SELECT * FROM ReviewItem WHERE document_id=%s ORDER BY id DESC LIMIT 1",
                        (self.document_id,))
            review_item = cur.fetchone()
        self.assertEqual(review_item["status"], "proposed")

        with self.client.session_transaction() as sess:
            sess.clear()

        # Alice cannot confirm her own proposal.
        self._login("alice", self.ALICE_PASSWORD)
        resp = self.client.get(f"/admin/review/{review_item['id']}/confirm")
        self.assertEqual(resp.status_code, 403)

        with self.client.session_transaction() as sess:
            sess.clear()

        # Bob (a different editor) confirms it.
        self._login("bob", self.BOB_PASSWORD)
        resp = self.client.post(f"/admin/review/{review_item['id']}/confirm",
                                 data={"action": "confirm"}, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        with self.conn.cursor() as cur:
            cur.execute("SELECT description, needs_review FROM Document WHERE id=%s", (self.document_id,))
            doc = cur.fetchone()
            cur.execute("SELECT status, confirmed_by_user_id FROM ReviewItem WHERE id=%s",
                        (review_item["id"],))
            ri = cur.fetchone()
            cur.execute("SELECT COUNT(*) AS c FROM AuditLog WHERE review_item_id=%s", (review_item["id"],))
            audit_count = cur.fetchone()["c"]

        self.assertEqual(doc["description"], "A real description now.")
        self.assertEqual(doc["needs_review"], 0)
        self.assertEqual(ri["status"], "confirmed")
        self.assertNotEqual(ri["confirmed_by_user_id"], review_item.get("proposed_by_user_id"))
        self.assertEqual(audit_count, 1)

        # The audit log page (visible to any logged-in editor) shows it.
        resp = self.client.get("/admin/audit-log")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"bob", resp.data)


if __name__ == "__main__":
    unittest.main()
