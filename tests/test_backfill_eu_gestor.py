"""Tests for src/tools/backfill_eu_gestor.py: the review-reason helpers and the
rule that a document whose gestor has been found stops being flagged "gestor
not found" (it used to keep the flag forever — found on document 87 after its
number was corrected), while any other reason it carries stays."""
import contextlib
import io
import pathlib
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))

import backfill_eu_gestor as bg  # noqa: E402

NOT_FOUND = bg.UNRESOLVED_REVIEW_REASON


class ReasonHelpersTestCase(unittest.TestCase):
    def test_remove_the_only_reason_leaves_nothing(self):
        self.assertIsNone(bg.remove_review_reason(NOT_FOUND, NOT_FOUND))

    def test_another_reason_stays(self):
        self.assertEqual(bg.remove_review_reason(f"chybí popis; {NOT_FOUND}", NOT_FOUND), "chybí popis")
        self.assertEqual(bg.remove_review_reason(f"{NOT_FOUND}; chybí popis", NOT_FOUND), "chybí popis")

    def test_a_reason_that_is_not_there_changes_nothing(self):
        self.assertEqual(bg.remove_review_reason("chybí popis", NOT_FOUND), "chybí popis")
        self.assertIsNone(bg.remove_review_reason(None, NOT_FOUND))
        self.assertIsNone(bg.remove_review_reason("", NOT_FOUND))

    def test_append_then_remove_round_trips(self):
        added = bg.append_review_reason("chybí popis", NOT_FOUND)
        self.assertEqual(bg.remove_review_reason(added, NOT_FOUND), "chybí popis")


class FakeCursor:
    rowcount = 0

    def __init__(self, documents, log):
        self.documents, self.log = documents, log

    def execute(self, sql, params=()):
        self.log.append((" ".join(sql.split()), params))

    def fetchall(self):
        return self.documents


class FakeConn:
    def __init__(self, documents):
        self.log = []
        self._cursor = FakeCursor(documents, self.log)

    def cursor(self):
        return self._cursor

    def commit(self):
        pass

    def close(self):
        pass


def doc(doc_id, source, reason, needs_review=1, url=None):
    return {"id": doc_id, "identifier": f"X {doc_id}", "title": "t", "url": url or f"https://eur-lex.europa.eu/eli/reg/{doc_id}",
            "needs_review": needs_review, "review_reason": reason, "type_name": "Nařízení EU", "current_source": source}


class MainTestCase(unittest.TestCase):
    def run_main(self, documents, gestors, apply=True):
        conn = FakeConn(documents)
        argv = ["backfill_eu_gestor.py"] + (["--apply"] if apply else [])
        with mock.patch.object(bg, "get_connection", return_value=conn), \
                mock.patch.object(bg, "load_cache", return_value=dict(gestors)), \
                mock.patch.object(bg, "save_cache"), \
                mock.patch.object(bg, "fetch_responsible_gestor", return_value=None), \
                mock.patch.object(bg, "get_or_create_source", return_value=17), \
                mock.patch.object(sys, "argv", argv), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            bg.main()
        updates = [(sql, params) for sql, params in conn.log if sql.startswith("UPDATE")]
        return updates, out.getvalue()

    def test_a_found_gestor_removes_the_stale_flag_even_when_the_source_is_already_set(self):
        d = doc(87, "DG GROW", NOT_FOUND)
        updates, out = self.run_main([d], {d["url"]: "DG GROW"})
        self.assertEqual(updates, [("UPDATE Document SET needs_review=%s, review_reason=%s WHERE id=%s", (0, None, 87))])
        self.assertIn("stale 'not found' review flag removed: 1", out)

    def test_another_reason_keeps_the_document_flagged(self):
        d = doc(5, "DG GROW", f"chybí popis; {NOT_FOUND}")
        updates, _ = self.run_main([d], {d["url"]: "DG GROW"})
        self.assertEqual(updates[0][1], (1, "chybí popis", 5))

    def test_the_source_is_set_and_the_flag_removed_in_one_run(self):
        d = doc(6, None, NOT_FOUND)
        updates, _ = self.run_main([d], {d["url"]: "DG GROW"})
        self.assertEqual([p for _, p in updates], [(17, 6), (0, None, 6)])

    def test_a_document_with_no_stale_flag_is_untouched(self):
        d = doc(7, "DG GROW", "chybí popis")
        updates, out = self.run_main([d], {d["url"]: "DG GROW"})
        self.assertEqual(updates, [])
        self.assertIn("unchanged: 1", out)

    def test_dry_run_writes_nothing(self):
        d = doc(87, "DG GROW", NOT_FOUND)
        updates, out = self.run_main([d], {d["url"]: "DG GROW"}, apply=False)
        self.assertEqual(updates, [])
        self.assertIn("Dry run", out)

    def test_an_unresolved_document_is_still_flagged(self):
        d = doc(8, None, None)
        updates, _ = self.run_main([d], {})
        self.assertEqual(updates[0][1], (NOT_FOUND, 8))


if __name__ == "__main__":
    unittest.main()
