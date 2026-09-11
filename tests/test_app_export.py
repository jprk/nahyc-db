import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.app import build_document_query, _rows_for_export, EXPORT_FIELDS


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


if __name__ == '__main__':
    unittest.main()
