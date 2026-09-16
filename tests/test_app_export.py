import datetime
import os
import subprocess
import sys
import unittest
from unittest.mock import MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.app import (
    build_document_query, build_count_query, build_page_range, parse_page,
    _rows_for_export, EXPORT_FIELDS, PAGE_SIZE,
    get_git_version, get_db_last_updated, get_active_document_count,
    get_total_document_count,
)


NO_FILTERS = {'q': '', 'type_id': '', 'source_id': '', 'keyword_id': ''}


class BuildDocumentQueryTestCase(unittest.TestCase):
    """doc/REQUIREMENTS.md R2.5, 2026-09-11: pure, DB-independent — shared
    by index() (limit=100) and /export/<fmt> (limit=None, the full
    filtered set, not just the on-screen page)."""

    def test_no_filters_no_limit(self):
        sql, params = build_document_query(NO_FILTERS, limit=None)
        self.assertNotIn("AND (d.title", sql)
        self.assertNotIn("AND d.type_id", sql)
        self.assertNotIn("AND d.source_id", sql)
        self.assertNotIn("AND dk.keyword_id", sql)
        self.assertNotIn("LIMIT", sql)
        self.assertEqual(params, [])

    def test_limit_appends_limit_clause_and_param(self):
        sql, params = build_document_query(NO_FILTERS, limit=100)
        self.assertIn("LIMIT %s", sql)
        self.assertEqual(params, [100])

    def test_no_limit_means_no_limit_clause_at_all(self):
        # Regression guard: export must not silently inherit index()'s
        # page-size cap.
        sql, _ = build_document_query(NO_FILTERS, limit=None)
        self.assertNotIn("LIMIT", sql)

    def test_q_filter_adds_like_clause(self):
        filters = {**NO_FILTERS, 'q': 'hydrogen'}
        sql, params = build_document_query(filters)
        self.assertIn("AND (d.title LIKE %s OR d.description LIKE %s)", sql)
        self.assertEqual(params, ['%hydrogen%', '%hydrogen%'])

    def test_type_id_filter(self):
        filters = {**NO_FILTERS, 'type_id': '3'}
        sql, params = build_document_query(filters)
        self.assertIn("AND d.type_id = %s", sql)
        self.assertEqual(params, ['3'])

    def test_source_id_filter(self):
        filters = {**NO_FILTERS, 'source_id': '7'}
        sql, params = build_document_query(filters)
        self.assertIn("AND d.source_id = %s", sql)
        self.assertEqual(params, ['7'])

    def test_keyword_id_filter(self):
        filters = {**NO_FILTERS, 'keyword_id': '9'}
        sql, params = build_document_query(filters)
        self.assertIn("AND dk.keyword_id = %s", sql)
        self.assertEqual(params, ['9'])

    def test_all_filters_combined_with_limit(self):
        filters = {'q': 'norma', 'type_id': '1', 'source_id': '2', 'keyword_id': '3'}
        sql, params = build_document_query(filters, limit=50)
        self.assertEqual(params, ['%norma%', '%norma%', '1', '2', '3', 50])
        self.assertTrue(sql.rstrip().endswith("LIMIT %s"))


class PaginationQueryTestCase(unittest.TestCase):
    """doc/PLAN.md §16, 2026-09-16: the list is paged instead of capped
    at a hardcoded 100 rows."""

    def test_offset_is_appended_with_the_limit(self):
        sql, params = build_document_query(NO_FILTERS, limit=50, offset=100)
        self.assertIn("LIMIT %s", sql)
        self.assertIn("OFFSET %s", sql)
        self.assertEqual(params, [50, 100])

    def test_first_page_needs_no_offset_clause(self):
        sql, params = build_document_query(NO_FILTERS, limit=50, offset=0)
        self.assertNotIn("OFFSET", sql)
        self.assertEqual(params, [50])

    def test_offset_without_a_limit_is_ignored(self):
        # Export passes limit=None and must never be paged.
        sql, params = build_document_query(NO_FILTERS, limit=None, offset=500)
        self.assertNotIn("LIMIT", sql)
        self.assertNotIn("OFFSET", sql)
        self.assertEqual(params, [])

    def test_count_query_counts_distinct_documents(self):
        # NOT COUNT(*): the DocumentKeyword join multiplies a document's
        # rows by its keyword count, which would inflate the total and
        # paginate into empty pages (the R2.1 trap commit ebc1f60 fixed
        # once already with GROUP BY d.id).
        sql, _ = build_count_query(NO_FILTERS)
        self.assertIn("COUNT(DISTINCT d.id)", sql)

    def test_count_query_applies_the_same_filters_as_the_list(self):
        filters = {'q': 'vodík', 'type_id': '3', 'source_id': '7', 'keyword_id': '9'}
        count_sql, count_params = build_count_query(filters)
        list_sql, list_params = build_document_query(filters, limit=None)
        for fragment in ("AND (d.title LIKE %s OR d.description LIKE %s)",
                         "AND d.type_id = %s", "AND d.source_id = %s",
                         "AND dk.keyword_id = %s"):
            self.assertIn(fragment, count_sql)
            self.assertIn(fragment, list_sql)
        self.assertEqual(count_params, list_params)

    def test_page_size_is_positive(self):
        self.assertGreater(PAGE_SIZE, 0)


class ParsePageTestCase(unittest.TestCase):
    def test_defaults_to_first_page(self):
        self.assertEqual(parse_page({}, 10), 1)

    def test_reads_a_valid_page(self):
        self.assertEqual(parse_page({'page': '4'}, 10), 4)

    def test_clamps_out_of_range(self):
        self.assertEqual(parse_page({'page': '999'}, 10), 10)
        self.assertEqual(parse_page({'page': '0'}, 10), 1)
        self.assertEqual(parse_page({'page': '-5'}, 10), 1)

    def test_garbage_falls_back_rather_than_raising(self):
        self.assertEqual(parse_page({'page': 'abc'}, 10), 1)
        self.assertEqual(parse_page({'page': ''}, 10), 1)


class BuildPageRangeTestCase(unittest.TestCase):
    def test_single_page_needs_no_pager(self):
        self.assertEqual(build_page_range(1, 1), [])
        self.assertEqual(build_page_range(1, 0), [])

    def test_short_range_is_listed_in_full(self):
        self.assertEqual(build_page_range(1, 4), [1, 2, 3, 4])

    def test_long_range_elides_with_none_as_the_gap_marker(self):
        got = build_page_range(13, 25)
        self.assertEqual(got[0], 1)
        self.assertEqual(got[-1], 25)
        self.assertIn(None, got)
        self.assertIn(13, got)

    def test_always_includes_first_current_and_last(self):
        for page in (1, 2, 12, 24, 25):
            got = build_page_range(page, 25)
            self.assertIn(1, got)
            self.assertIn(page, got)
            self.assertIn(25, got)

    def test_page_numbers_are_ascending_and_unique(self):
        numbers = [p for p in build_page_range(13, 25) if p is not None]
        self.assertEqual(numbers, sorted(set(numbers)))


class RowsForExportTestCase(unittest.TestCase):
    """doc/REQUIREMENTS.md R2.5/R4.1, 2026-09-11: the actual metadata-only
    boundary in code — must never surface file_path/restricted_fulltext/id."""

    def test_output_keys_are_exactly_export_fields(self):
        documents = [{
            'id': 1, 'title': 'T', 'description': 'D', 'type_name': 'Zákon',
            'source_name': 'MPO', 'language': 'cs', 'effective_date': '2020-01-01',
            'url': 'https://example.test', 'file_path': 'data/fulltext/x.pdf',
            'restricted_fulltext': False,
        }]
        rows = _rows_for_export(documents, {1: ['vodik', 'energetika']})
        self.assertEqual(len(rows), 1)
        self.assertEqual(set(rows[0].keys()), set(EXPORT_FIELDS))
        self.assertNotIn('file_path', rows[0])
        self.assertNotIn('restricted_fulltext', rows[0])
        self.assertNotIn('id', rows[0])
        self.assertEqual(rows[0]['keywords'], 'vodik, energetika')

    def test_none_fields_become_empty_string(self):
        documents = [{
            'id': 2, 'title': 'T', 'description': None, 'type_name': None,
            'source_name': None, 'language': None, 'effective_date': None,
            'url': None, 'file_path': None, 'restricted_fulltext': False,
        }]
        rows = _rows_for_export(documents, {})
        row = rows[0]
        for field in ('description', 'type_name', 'source_name', 'language', 'url'):
            self.assertEqual(row[field], '')
        self.assertEqual(row['effective_date'], '')
        self.assertEqual(row['keywords'], '')

    def test_document_with_no_tags_gets_empty_keywords(self):
        documents = [{
            'id': 3, 'title': 'T', 'description': '', 'type_name': '',
            'source_name': '', 'language': '', 'effective_date': '',
            'url': '', 'file_path': None, 'restricted_fulltext': False,
        }]
        rows = _rows_for_export(documents, {1: ['other-doc-tag']})
        self.assertEqual(rows[0]['keywords'], '')


class GetGitVersionTestCase(unittest.TestCase):
    """Footer version display, 2026-09-13: never raises, and reflects the
    actual repo this test runs from (a real git checkout in CI/dev)."""

    def test_returns_a_non_empty_string_in_a_real_checkout(self):
        version = get_git_version()
        self.assertIsInstance(version, str)
        self.assertTrue(version)

    def test_git_not_found_returns_none_not_raise(self):
        import app.app as app_module
        with unittest.mock.patch.object(
                app_module.subprocess, "run", side_effect=FileNotFoundError):
            self.assertIsNone(app_module.get_git_version())

    def test_subprocess_error_returns_none_not_raise(self):
        import app.app as app_module
        with unittest.mock.patch.object(
                app_module.subprocess, "run",
                side_effect=subprocess.CalledProcessError(1, "git")):
            self.assertIsNone(app_module.get_git_version())


class GetDbLastUpdatedTestCase(unittest.TestCase):
    def test_returns_the_max_updated_at(self):
        expected = datetime.datetime(2026, 9, 11, 22, 39, 47)
        db = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = {"last_updated": expected}
        db.cursor.return_value.__enter__.return_value = cursor
        self.assertEqual(get_db_last_updated(db), expected)

    def test_empty_table_returns_none(self):
        db = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = {"last_updated": None}
        db.cursor.return_value.__enter__.return_value = cursor
        self.assertIsNone(get_db_last_updated(db))


class GetTotalDocumentCountTestCase(unittest.TestCase):
    """The hero headline used to hardcode "300" — this replaces it with a
    real COUNT(*) of every Document row."""

    def test_returns_the_count(self):
        db = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = {"c": 1214}
        db.cursor.return_value.__enter__.return_value = cursor
        self.assertEqual(get_total_document_count(db), 1214)

    def test_no_rows_returns_zero(self):
        db = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        db.cursor.return_value.__enter__.return_value = cursor
        self.assertEqual(get_total_document_count(db), 0)


class GetActiveDocumentCountTestCase(unittest.TestCase):
    """Feeds the hero section's active/inactive breakdown note — a real
    count of documents whose CURRENT version's lifecycle_state is
    'active' (not every Document row — a draft/superseded-only document
    shouldn't count as active). The "inactive" number shown alongside it
    is computed by the caller (index()) as total - active, not a
    separate query — see get_active_document_count()'s own docstring."""

    def test_returns_the_count(self):
        db = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = {"c": 1061}
        db.cursor.return_value.__enter__.return_value = cursor
        self.assertEqual(get_active_document_count(db), 1061)

    def test_no_rows_returns_zero(self):
        db = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        db.cursor.return_value.__enter__.return_value = cursor
        self.assertEqual(get_active_document_count(db), 0)


if __name__ == '__main__':
    unittest.main()
