"""The editors' "Ke kontrole" filter of the catalogue (parameter `kontrola`):
documents flagged Document.needs_review, narrowed by the reason of the flag.

* unit: who gets the filter (only a logged-in editor), the SQL condition of
  every choice, its place in the shared WHERE clause, the editor's export row;
* Flask with a fake database: a visitor's `kontrola=...` changes no query;
* integration on the TEST database (`.env.test`, `h2regdocs_test`, read only):
  the count of every choice equals the number of flagged documents whose
  review_reason (split on "; ") contains a reason of that kind, decided in
  Python independently of the SQL, and every flagged document falls into
  some choice."""
import os
import pathlib
import sys
import unittest
from unittest import mock

from dotenv import dotenv_values

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.append(str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src" / "tools"))

os.environ.setdefault("SECRET_KEY", "unit-test")
import app.app as webapp  # noqa: E402
from app import catalog_filters as cf  # noqa: E402
import testdb  # noqa: E402

BASE = {'q': '', 'type_id': '', 'eu_subtype': '', 'source_id': '', 'category_id': '',
        'jurisdiction': 'vse', 'synonyms': [], 'include_sk': True}

# The reasons as the pipeline writes them (see the live database, 2026-11-26).
MISSING = "chybí popis/anotace dokumentu"
MANUAL = "popis je třeba doplnit ručně"  # src/tools/act_provisions.py
LANGUAGE = "jazyk dokumentu byl automaticky odhadnut, ověřte (EN)"
RECORDS = "Kontrola záznamů: ISO poslední vydání zrušila"
FRAGMENT = "název vypadá jako useknutý fragment textu"
GESTOR = "EU akt: autoritativní gestor (DG/instituce) se v EUR-Lex/Cellar nepodařilo dohledat"


def kinds(reason):
    """The review filter keys a review_reason belongs to, decided in Python."""
    parts = [p.strip() for p in (reason or "").split(";") if p.strip()]
    found = {"vse"}
    for part in parts:
        if part.startswith(MISSING) or part.startswith(MANUAL):
            found.add("popis")
        if part.startswith("jazyk dokumentu byl automaticky odhadnut"):
            found.add("jazyk")
        if part.startswith("Kontrola záznamů"):
            found.add("kontrola-zaznamu")
        if part.startswith(FRAGMENT) or "značka není platné označení" in part or "autoritativní gestor" in part:
            found.add("oprava")
    return found


class WantsReviewTestCase(unittest.TestCase):
    def test_visitor_gets_no_filter(self):
        for value in cf.REVIEW_FILTERS:
            self.assertEqual(cf.wants_review({"kontrola": value}, logged_in=None), "")

    def test_editor_gets_a_known_choice(self):
        for value in cf.REVIEW_FILTERS:
            self.assertEqual(cf.wants_review({"kontrola": value}, logged_in=7), value)
        self.assertEqual(cf.wants_review({"kontrola": " jazyk "}, logged_in=7), "jazyk")

    def test_unknown_or_missing_value_means_no_filter(self):
        self.assertEqual(cf.wants_review({}, logged_in=7), "")
        self.assertEqual(cf.wants_review({"kontrola": "vsechno"}, logged_in=7), "")
        self.assertEqual(cf.wants_review({"kontrola": "1 OR 1=1"}, logged_in=7), "")

    def test_menu_starts_with_no_restriction(self):
        options = cf.review_options()
        self.assertEqual(options[0][0], "")
        self.assertEqual([v for v, _ in options[1:]], ["vse", "oprava", "kontrola-zaznamu", "jazyk", "popis"])


class ReviewConditionTestCase(unittest.TestCase):
    def test_everything_flagged(self):
        self.assertEqual(cf.review_condition("vse"), ("d.needs_review = 1", []))

    def test_no_or_unknown_key_adds_nothing(self):
        self.assertEqual(cf.review_condition(""), ("", []))
        self.assertEqual(cf.review_condition("nic"), ("", []))

    def test_defects_use_the_badge_markers(self):
        sql, params = cf.review_condition("oprava")
        self.assertEqual(sql, "d.needs_review = 1 AND (d.review_reason LIKE %s OR d.review_reason LIKE %s "
                              "OR d.review_reason LIKE %s)")
        self.assertEqual(params, [f"%{m}%" for m in cf.DEFECT_REASON_MARKERS])
        # the red badge and the filter read the same list
        self.assertEqual(webapp._DEFECT_REASON_MARKERS, cf.DEFECT_REASON_MARKERS)

    def test_single_marker_choices(self):
        self.assertEqual(cf.review_condition("kontrola-zaznamu")[1], ["%Kontrola záznamů%"])
        self.assertEqual(cf.review_condition("jazyk")[1], ["%jazyk dokumentu byl automaticky odhadnut%"])
        self.assertEqual(cf.review_condition("popis")[1], ["%chybí popis/anotace dokumentu%",
                                                           "%popis je třeba doplnit ručně%"])

    def test_alias(self):
        self.assertTrue(cf.review_condition("popis", alias="x")[0].startswith("x.needs_review = 1 AND (x."))

    def test_like_wildcards_are_escaped(self):
        self.assertEqual(cf.like_literal("50 %_a\\b"), "%50 \\%\\_a\\\\b%")

    def test_python_classification_of_the_known_reasons(self):
        self.assertEqual(kinds(f"{FRAGMENT}; {MISSING}; {RECORDS}"), {"vse", "oprava", "popis", "kontrola-zaznamu"})
        self.assertEqual(kinds(f"{MISSING}; {GESTOR}"), {"vse", "popis", "oprava"})
        self.assertEqual(kinds(f"{LANGUAGE}; {MISSING}"), {"vse", "jazyk", "popis"})
        self.assertEqual(kinds(MANUAL), {"vse", "popis"})


class FilterClauseTestCase(unittest.TestCase):
    def test_review_is_part_of_the_shared_clause(self):
        clause, params = webapp.build_filter_clause({**BASE, 'type_id': '3', 'review': 'jazyk'})
        self.assertIn("AND d.type_id = %s AND d.needs_review = 1 AND (d.review_reason LIKE %s)", clause)
        self.assertEqual(params, ['3', '%jazyk dokumentu byl automaticky odhadnut%'])

    def test_list_and_count_carry_the_same_condition(self):
        filters = {**BASE, 'q': 'vodík', 'review': 'popis'}
        count_sql, count_params = webapp.build_count_query(filters, group_variants=True)
        list_sql, list_params = webapp.build_document_query(filters, group_variants=True)
        self.assertIn("d.needs_review = 1", count_sql)
        self.assertIn("d.needs_review = 1", list_sql)
        self.assertEqual(count_params, list_params)

    def test_without_the_key_nothing_changes(self):
        self.assertEqual(webapp.build_filter_clause(BASE), webapp.build_filter_clause({**BASE, 'review': ''}))

    def test_parse_filters_takes_the_resolved_key(self):
        self.assertEqual(webapp.parse_filters({'kontrola': 'jazyk'})['review'], '')
        self.assertEqual(webapp.parse_filters({}, review='jazyk')['review'], 'jazyk')

    def test_review_filter_follows_the_login(self):
        with webapp.app.test_request_context("/?kontrola=oprava"):
            self.assertEqual(webapp.review_filter(), "")
            webapp.session["user_id"] = 1
            self.assertEqual(webapp.review_filter(), "oprava")


class EditorExportRowTestCase(unittest.TestCase):
    DOC = {'id': 1, 'slug': 'zakon-1', 'identifier': '1/2000 Sb.', 'title': 'T', 'description': None,
           'type_name': 'Zákon', 'source_name': 'MPO', 'language': 'CS', 'effective_date': None,
           'url': None, 'file_path': 'data/fulltext/x.pdf', 'restricted_fulltext': 0,
           'needs_review': 1, 'review_reason': f"{MISSING}; {RECORDS}"}

    def test_visitor_row_is_unchanged(self):
        with webapp.app.test_request_context("/"):
            row = webapp._rows_for_export([self.DOC], {})[0]
        self.assertEqual(list(row), webapp.EXPORT_FIELDS)

    def test_editor_row_adds_the_work_list_columns(self):
        with webapp.app.test_request_context("/", base_url="https://example.test/h2db"):
            row = webapp._rows_for_export([self.DOC], {}, editor=True)[0]
        self.assertEqual(list(row), webapp.EDITOR_EXPORT_FIELDS)
        self.assertEqual(row['identifier'], '1/2000 Sb.')
        self.assertEqual(row['record_url'], 'https://example.test/h2db/dokument/zakon-1')
        self.assertEqual(row['needs_review'], '1')
        self.assertEqual(row['review_reason'], f"{MISSING}; {RECORDS}")
        self.assertNotIn('file_path', row)


class VisitorParameterIgnoredTestCase(unittest.TestCase):
    """A visitor's `kontrola=...` reaches no query (fake database records them)."""

    def queries(self, path, logged_in=False):
        db = mock.MagicMock()
        cur = db.cursor.return_value.__enter__.return_value
        cur.fetchone.return_value = {'c': 0}
        cur.fetchall.return_value = []
        client = webapp.app.test_client()
        if logged_in:
            with client.session_transaction() as sess:
                sess["user_id"] = 1
        with mock.patch.object(webapp, "get_db", return_value=db), \
                mock.patch.object(webapp, "get_db_last_updated", return_value=None), \
                mock.patch.object(webapp, "has_column", return_value=False), \
                mock.patch.object(webapp, "areas_enabled", return_value=False):
            response = client.get(path)
        self.assertEqual(response.status_code, 200)
        return " ".join(str(c.args[0]) for c in cur.execute.call_args_list), response

    def test_catalogue(self):
        sql, response = self.queries("/?kontrola=oprava")
        self.assertNotIn("needs_review = 1", sql)
        self.assertNotIn('name="kontrola"', response.get_data(as_text=True))

    def test_exports(self):
        for fmt in ("csv", "json", "xml"):
            sql, response = self.queries(f"/export/{fmt}?kontrola=vse")
            self.assertNotIn("needs_review = 1", sql)
            self.assertNotIn("review_reason", response.get_data(as_text=True))

    def test_editor_gets_the_menu_and_the_condition(self):
        sql, response = self.queries("/?kontrola=oprava", logged_in=True)
        self.assertIn("d.needs_review = 1 AND (d.review_reason LIKE", sql)
        html = response.get_data(as_text=True)
        self.assertIn('name="kontrola"', html)
        self.assertIn('<option value="oprava" selected>', html)


class ReviewCountsOnTestDatabaseTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            env_path = testdb.find_env_file(".env.test")
        except testdb.TestDbError:
            raise unittest.SkipTest(".env.test not found — no rehearsal database configured")
        env = {**dotenv_values(env_path), **{k: v for k, v in os.environ.items() if k.startswith("DB_")}}
        if env.get("DB_NAME") != "h2regdocs_test":
            raise unittest.SkipTest("the test database is not h2regdocs_test — refusing to guess")
        env["DB_PORT"] = str(env.get("DB_PORT") or 3306)
        import pymysql
        cls.conn = testdb.connect(env, cursorclass=pymysql.cursors.DictCursor)
        with cls.conn.cursor() as cur:
            cur.execute("SELECT id, needs_review, review_reason FROM Document")
            cls.documents = cur.fetchall()
        if not any(d["needs_review"] for d in cls.documents):
            raise unittest.SkipTest("no flagged document in the test database")

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def count(self, filters, group_variants=False):
        sql, params = webapp.build_count_query(filters, group_variants=group_variants)
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()["c"]

    def test_every_choice_counts_the_documents_with_such_a_reason(self):
        for key in cf.REVIEW_FILTERS:
            expected = sum(1 for d in self.documents if d["needs_review"] and key in kinds(d["review_reason"]))
            with self.subTest(key=key):
                self.assertEqual(self.count({**BASE, 'review': key}), expected)

    def test_every_flagged_document_falls_into_some_choice(self):
        flagged = [d for d in self.documents if d["needs_review"]]
        orphans = [d["id"] for d in flagged if kinds(d["review_reason"]) == {"vse"}]
        self.assertEqual(orphans, [], "a reason the filter does not know about")
        self.assertTrue(all((d["review_reason"] or "").strip() for d in flagged))

    def test_choices_narrow_the_catalogue(self):
        everything = self.count(BASE, group_variants=True)
        flagged = self.count({**BASE, 'review': 'vse'}, group_variants=True)
        self.assertLess(flagged, everything)
        for key in ("oprava", "kontrola-zaznamu", "jazyk", "popis"):
            with self.subTest(key=key):
                self.assertLessEqual(self.count({**BASE, 'review': key}, group_variants=True), flagged)

    def test_combines_with_the_public_view_and_the_jurisdiction(self):
        public = {**BASE, 'include_sk': False, 'review': 'vse'}
        czech = {**public, 'jurisdiction': 'cz'}
        self.assertLessEqual(self.count(public), self.count({**BASE, 'review': 'vse'}))
        self.assertLessEqual(self.count(czech), self.count(public))
        with self.conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS c FROM Document WHERE needs_review = 1 AND jurisdikce = 'CZ'")
            self.assertEqual(self.count(czech), cur.fetchone()["c"])


if __name__ == "__main__":
    unittest.main()
