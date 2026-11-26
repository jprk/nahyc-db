import datetime
import os
import pathlib
import subprocess
import sys
import unittest
from unittest.mock import MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.app import (
    build_document_query, build_count_query, build_filter_clause, build_page_range, parse_page, parse_filters,
    _rows_for_export, EXPORT_FIELDS, PAGE_SIZE,
    get_git_version, get_db_last_updated, get_active_document_count, get_upcoming_document_count,
    get_total_document_count, classify_review_severity, REVIEW_SEVERITY,
)


# include_sk: these tests are about the other filters; the Slovak restriction
# of the public view is tested in tests/test_catalog_filters.py.
NO_FILTERS = {'q': '', 'type_id': '', 'source_id': '', 'category_id': '', 'include_sk': True}


class BuildDocumentQueryTestCase(unittest.TestCase):
    """doc/REQUIREMENTS.md R2.5, 2026-09-11: pure, DB-independent — shared
    by index() (limit=100) and /export/<fmt> (limit=None, the full
    filtered set, not just the on-screen page)."""

    def test_no_filters_no_limit(self):
        sql, params = build_document_query(NO_FILTERS, limit=None)
        self.assertNotIn("AND (d.title", sql)
        self.assertNotIn("AND d.type_id", sql)
        self.assertNotIn("AND d.source_id", sql)
        self.assertNotIn("DocumentSourceCategory", sql)
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
        # doc/MPO_PRIPOMINKY.md, krok 2: the designation is searched too.
        filters = {**NO_FILTERS, 'q': 'hydrogen'}
        sql, params = build_document_query(filters)
        self.assertIn("AND (d.title LIKE %s OR d.description LIKE %s OR d.identifier LIKE %s OR ", sql)
        # doc/OBLASTI.md: the source categories stay searchable though no longer shown
        self.assertIn("FROM DocumentSourceCategory sk JOIN SourceCategory sw", sql)
        self.assertIn("sw.name LIKE %s", sql)
        self.assertEqual(params, ['%hydrogen%'] * 4)

    def test_area_filter(self):
        filters = {**NO_FILTERS, 'oblast': 'vybuch'}
        sql, params = build_document_query(filters)
        self.assertIn("fx.code = %s", sql)
        self.assertEqual(params, ['vybuch'])

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

    def test_category_id_filter(self):
        filters = {**NO_FILTERS, 'category_id': '9'}
        sql, params = build_document_query(filters)
        self.assertIn("EXISTS (SELECT 1 FROM DocumentSourceCategory fc WHERE fc.document_id = d.id "
                      "AND fc.category_id = %s)", sql)
        self.assertNotIn("JOIN DocumentSourceCategory", sql, "an EXISTS, no join that multiplies the rows")
        self.assertEqual(params, ['9'])

    def test_category_filter_before_the_migration(self):
        """src/tools/migrate_vocabulary.py: until it runs, the tables are Keyword/DocumentKeyword."""
        import vocabulary
        filters = {**NO_FILTERS, 'q': 'x', 'category_id': '9', 'categories': vocabulary.LEGACY_CATEGORIES}
        sql, params = build_document_query(filters)
        self.assertIn("FROM DocumentKeyword sk JOIN Keyword sw ON sw.id = sk.keyword_id", sql)
        self.assertIn("sw.keyword LIKE %s", sql)
        self.assertIn("fc.keyword_id = %s", sql)
        self.assertEqual(params, ['%x%'] * 4 + ['9'])

    def test_old_keyword_id_parameter_is_accepted(self):
        self.assertEqual(parse_filters({'keyword_id': '12'})['category_id'], '12')
        self.assertEqual(parse_filters({'category_id': '5', 'keyword_id': '12'})['category_id'], '5')

    def test_all_filters_combined_with_limit(self):
        # without 'include_sk': the public view, Slovak documents left out last
        filters = {'q': 'norma', 'type_id': '1', 'source_id': '2', 'category_id': '3'}
        sql, params = build_document_query(filters, limit=50)
        self.assertEqual(params, ['%norma%'] * 4 + ['1', '2', '3', 'SK', '%[SK]', 50])
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
        # NOT COUNT(*): a join with the category links would multiply a
        # document's rows by its category count, inflate the total and
        # paginate into empty pages (the R2.1 trap commit ebc1f60 fixed
        # once already with GROUP BY d.id).
        sql, _ = build_count_query(NO_FILTERS)
        self.assertIn("COUNT(DISTINCT d.id)", sql)

    def test_count_query_applies_the_same_filters_as_the_list(self):
        filters = {'q': 'vodík', 'type_id': '3', 'source_id': '7', 'category_id': '9', 'oblast': 'vybuch'}
        count_sql, count_params = build_count_query(filters)
        list_sql, list_params = build_document_query(filters, limit=None)
        for fragment in ("AND (d.title LIKE %s OR d.description LIKE %s OR d.identifier LIKE %s OR ",
                         "AND d.type_id = %s", "AND d.source_id = %s",
                         "AND fc.category_id = %s)", "fx.code = %s"):
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


class ClassifyReviewSeverityTestCase(unittest.TestCase):
    """doc/PLAN.md §18, 2026-09-17: needs_review used to be one
    undifferentiated red "Vyžaduje kontrolu" flag for everything from a
    garbled designation to a simply-not-yet-written description — 374 of
    1238 documents, but only 8 of those are an actual defect. This
    classifier is what tells them apart, so the badge reads honestly."""

    def test_not_flagged_at_all(self):
        self.assertIsNone(classify_review_severity({'needs_review': 0}))
        self.assertIsNone(classify_review_severity({'needs_review': False}))

    def test_garbled_designation_is_a_defect(self):
        doc = {'needs_review': 1, 'review_reason': 'značka není platné označení dokumentu'}
        self.assertEqual(classify_review_severity(doc), 'defect')

    def test_fragment_title_is_a_defect(self):
        doc = {'needs_review': 1, 'review_reason': 'název vypadá jako useknutý fragment textu'}
        self.assertEqual(classify_review_severity(doc), 'defect')

    def test_unresolved_eu_gestor_is_a_defect(self):
        # The reason string carries a dynamic "(DG/instituce)" suffix —
        # must match by substring, not equality.
        doc = {'needs_review': 1,
               'review_reason': 'EU akt: autoritativní gestor (DG/instituce) se v EUR-Lex/Cellar nepodařilo dohledat'}
        self.assertEqual(classify_review_severity(doc), 'defect')

    def test_missing_description_alone_is_incomplete_not_a_defect(self):
        doc = {'needs_review': 1, 'review_reason': 'chybí popis/anotace dokumentu',
               'popis_priblizny': None, 'description': ''}
        self.assertEqual(classify_review_severity(doc), 'incomplete')

    def test_uncertain_language_alone_is_incomplete(self):
        doc = {'needs_review': 1,
               'review_reason': 'jazyk dokumentu byl automaticky odhadnut, ověřte (DE)'}
        self.assertEqual(classify_review_severity(doc), 'incomplete')

    def test_approximate_summary_with_no_real_description(self):
        doc = {'needs_review': 1, 'review_reason': 'chybí popis/anotace dokumentu',
               'popis_priblizny': 'Norma se zabývá...', 'description': ''}
        self.assertEqual(classify_review_severity(doc), 'approximate')

    def test_approximate_summary_is_ignored_once_a_real_description_exists(self):
        # A record that later gained a real description (the fetch tier)
        # must not still read as merely "approximate" — description wins.
        doc = {'needs_review': 1, 'review_reason': 'chybí popis/anotace dokumentu',
               'popis_priblizny': 'Norma se zabývá...', 'description': 'Skutečný popis.'}
        self.assertEqual(classify_review_severity(doc), 'incomplete')

    def test_defect_marker_wins_even_alongside_an_approximate_summary(self):
        doc = {'needs_review': 1,
               'review_reason': 'název vypadá jako useknutý fragment textu; chybí popis/anotace dokumentu',
               'popis_priblizny': 'Norma se zabývá...', 'description': ''}
        self.assertEqual(classify_review_severity(doc), 'defect')

    def test_blank_or_missing_fields_do_not_raise(self):
        self.assertEqual(classify_review_severity({'needs_review': 1}), 'incomplete')

    def test_every_severity_has_a_label_and_icon(self):
        for severity in ('defect', 'approximate', 'incomplete'):
            self.assertIn('label', REVIEW_SEVERITY[severity])
            self.assertIn('icon', REVIEW_SEVERITY[severity])


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
        rows = _rows_for_export(documents, {1: ['vodik', 'energetika']}, {1: ['vodík', 'palivový článek']})
        self.assertEqual(len(rows), 1)
        self.assertEqual(set(rows[0].keys()), set(EXPORT_FIELDS))
        self.assertNotIn('file_path', rows[0])
        self.assertNotIn('restricted_fulltext', rows[0])
        self.assertNotIn('id', rows[0])
        self.assertEqual(rows[0]['source_categories'], 'vodik, energetika')
        self.assertEqual(rows[0]['keywords'], 'vodík, palivový článek')

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
        self.assertEqual(row['source_categories'], '')
        self.assertEqual(row['keywords'], '')

    def test_document_with_no_tags_gets_empty_keywords(self):
        documents = [{
            'id': 3, 'title': 'T', 'description': '', 'type_name': '',
            'source_name': '', 'language': '', 'effective_date': '',
            'url': '', 'file_path': None, 'restricted_fulltext': False,
        }]
        rows = _rows_for_export(documents, {1: ['other-doc-tag']}, {1: ['other-doc-term']})
        self.assertEqual(rows[0]['source_categories'], '')
        self.assertEqual(rows[0]['keywords'], '')


class GetGitVersionTestCase(unittest.TestCase):
    """Footer version display, 2026-09-13: never raises, and reflects the
    actual repo this test runs from (a real git checkout in CI/dev)."""

    def test_returns_a_non_empty_string_in_a_real_checkout(self):
        version = get_git_version()
        self.assertIsInstance(version, str)
        self.assertTrue(version)

    def test_git_not_found_reads_the_commit_from_the_git_files(self):
        """doc/NASAZENI.md, odstavec 4.5: the web server's user may not run git in a
        repository it does not own; the commit then comes from .git itself."""
        import app.app as app_module
        with unittest.mock.patch.object(app_module.subprocess, "run", side_effect=FileNotFoundError):
            self.assertRegex(app_module.get_git_version(), r"^[0-9a-f]{7}( \(.+\))?$")

    def test_subprocess_error_without_a_repository_returns_none_not_raise(self):
        import app.app as app_module
        with unittest.mock.patch.object(
                app_module.subprocess, "run",
                side_effect=subprocess.CalledProcessError(1, "git")), \
                unittest.mock.patch.object(app_module, "read_git_head", return_value=None):
            self.assertIsNone(app_module.get_git_version())


class ReadGitHeadTestCase(unittest.TestCase):
    def make_repo(self, root, packed=False):
        git = pathlib.Path(root) / ".git"
        (git / "refs" / "heads" / "feature").mkdir(parents=True)
        (git / "HEAD").write_text("ref: refs/heads/feature/x\n")
        sha = "0123456789abcdef0123456789abcdef01234567"
        if packed:
            (git / "packed-refs").write_text(f"# pack-refs\n{sha} refs/heads/feature/x\n")
        else:
            (git / "refs" / "heads" / "feature" / "x").write_text(sha + "\n")
        return git

    def test_branch_loose_and_packed(self):
        import tempfile
        from app.app import read_git_head
        for packed in (False, True):
            with tempfile.TemporaryDirectory() as tmp:
                self.make_repo(tmp, packed)
                self.assertEqual(read_git_head(tmp), "0123456 (feature/x)")

    def test_detached_head_worktree_file_and_no_repository(self):
        import tempfile
        from app.app import read_git_head
        with tempfile.TemporaryDirectory() as tmp:
            git = self.make_repo(pathlib.Path(tmp) / "main")
            (git / "worktrees" / "w").mkdir(parents=True)
            (git / "worktrees" / "w" / "HEAD").write_text("ref: refs/heads/feature/x\n")
            (git / "worktrees" / "w" / "commondir").write_text("../..\n")
            work = pathlib.Path(tmp) / "w"
            work.mkdir()
            (work / ".git").write_text(f"gitdir: {git / 'worktrees' / 'w'}\n")
            self.assertEqual(read_git_head(work), "0123456 (feature/x)")
            (git / "HEAD").write_text("fedcba9876543210fedcba9876543210fedcba98\n")
            self.assertEqual(read_git_head(pathlib.Path(tmp) / "main"), "fedcba9")
            self.assertIsNone(read_git_head(pathlib.Path(tmp) / "nothing"))


class TestInstanceTestCase(unittest.TestCase):
    """doc/NASAZENI.md, odstavec 4.5: H2DB_INSTANCE=test marks the test web."""

    def test_only_test_marks_the_instance(self):
        import os
        from app.app import is_test_instance
        for value, expected in (("test", True), (" Test ", True), ("", False), ("production", False)):
            with unittest.mock.patch.dict(os.environ, {"H2DB_INSTANCE": value}):
                self.assertEqual(is_test_instance(), expected)


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


class GetUpcomingDocumentCountTestCase(unittest.TestCase):
    """doc/MPO_OVERENI_WEBU.md Z1: drafts / promulgated acts are counted
    separately, not as "historických"."""

    def test_queries_draft_and_promulgated(self):
        db = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = {"c": 145}
        db.cursor.return_value.__enter__.return_value = cursor
        self.assertEqual(get_upcoming_document_count(db), 145)
        sql, params = cursor.execute.call_args[0]
        self.assertIn("lifecycle_state IN", sql)
        self.assertEqual(params[:2], ['draft', 'promulgated'])

    def test_no_rows_returns_zero(self):
        db = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        db.cursor.return_value.__enter__.return_value = cursor
        self.assertEqual(get_upcoming_document_count(db), 0)


if __name__ == '__main__':
    unittest.main()
