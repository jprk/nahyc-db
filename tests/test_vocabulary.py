"""The two vocabularies of a document (src/tools/vocabulary.py, migrate_vocabulary.py,
doc/KLICOVA_SLOVA.md odstavec 4): the identity of a keyword, the similar forms, the
plan of the migration of the old DocumentTerm, the renaming of Keyword, and the app
before and after the migration. No database (tests/test_migrate_vocabulary_db.py has one)."""
import datetime
import os
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "tools"))
sys.path.append(str(ROOT))

import migrate_vocabulary as mv  # noqa: E402
import vocabulary  # noqa: E402


class TermIdentityTestCase(unittest.TestCase):
    def test_eurovoc_and_ics_by_code_the_others_by_exact_text(self):
        self.assertEqual(vocabulary.term_key("eurovoc", "1252", "homologace"), "1252")
        self.assertEqual(vocabulary.term_key("ics", " 71.100.20 ", "71.100.20 Plyny"), "71.100.20")
        self.assertEqual(vocabulary.term_key("model", None, " palivový  článek "), "palivový článek")
        self.assertEqual(vocabulary.term_key("cas", None, "Kotle"), "Kotle")
        self.assertNotEqual(vocabulary.term_key("model", None, "Kotle"), vocabulary.term_key("model", None, "kotle"),
                            "forms differing in case stay two keywords: the editor decides, not the migration")
        self.assertEqual(vocabulary.term_key("eurovoc", None, "bez kódu"), "bez kódu")

    def test_norm_drops_case_and_diacritics(self):
        self.assertEqual(vocabulary.term_norm("Palivové  Články"), "palivove clanky")
        self.assertEqual(vocabulary.term_norm("emise CO₂"), vocabulary.term_norm("emise CO2"))
        self.assertEqual(len(vocabulary.term_norm("x" * 400)), 255)

    def test_similar_groups(self):
        groups = vocabulary.similar_groups(["Kotle", "kotle", "kotle", "motorový benzin", "motorový benzín",
                                            "vodík", "lahve na plyny"])
        self.assertEqual(groups, [("kotle", ["Kotle", "kotle"]),
                                  ("motorovy benzin", ["motorový benzin", "motorový benzín"])])

    def test_layout_detection(self):
        self.assertEqual(vocabulary.category_tables(None, {"SourceCategory", "DocumentSourceCategory"}),
                         vocabulary.CATEGORIES)
        self.assertEqual(vocabulary.category_tables(None, {"Keyword", "DocumentKeyword"}),
                         vocabulary.LEGACY_CATEGORIES)
        self.assertIsNone(vocabulary.category_tables(None, set()))
        self.assertIsNone(vocabulary.term_layout(None, set()))


class PlanTermsTestCase(unittest.TestCase):
    T1 = datetime.datetime(2026, 11, 23, 10, 0)
    T2 = datetime.datetime(2026, 11, 22, 10, 0)

    def rows(self):
        return [(1, "eurovoc", "1252", "homologace", "approval", 0, self.T1),
                (2, "eurovoc", "1252", "homologace", "approval", 3, self.T2),
                (1, "ics", "71.100.20", "71.100.20 Plyny", None, 0, self.T1),
                (2, "ics", "71.100.20", "71.100.20 Plyny pro průmysl", None, 0, self.T1),
                (3, "ics", "71.100.20", "71.100.20 Plyny", None, 0, self.T1),
                (1, "model", None, "Kotle", None, 1, self.T1),
                (2, "model", None, "kotle", None, 0, self.T1),
                (2, "cas", None, "kotle", None, 0, self.T1)]

    def test_every_row_becomes_a_link_and_each_keyword_one_row(self):
        planned = mv.plan_terms(self.rows())
        self.assertEqual(len(planned["links"]), len(self.rows()))
        self.assertEqual(sorted(planned["terms"]), [("cas", "kotle"), ("eurovoc", "1252"), ("ics", "71.100.20"),
                                                    ("model", "Kotle"), ("model", "kotle")])
        self.assertEqual(planned["terms"][("eurovoc", "1252")],
                         {"code": "1252", "term": "homologace", "term_en": "approval", "created_at": self.T2})
        self.assertEqual(planned["duplicates"], [])
        self.assertIn((2, ("eurovoc", "1252"), 3, self.T2), planned["links"], "the position stays")

    def test_a_code_with_several_texts_keeps_the_most_frequent_one(self):
        planned = mv.plan_terms(self.rows())
        self.assertEqual(planned["terms"][("ics", "71.100.20")]["term"], "71.100.20 Plyny")
        self.assertEqual(planned["conflicts"], [("ics", "71.100.20", ["71.100.20 Plyny",
                                                                      "71.100.20 Plyny pro průmysl"])])

    def test_two_rows_of_one_document_with_one_code_become_one_link(self):
        planned = mv.plan_terms([(1, "ics", "1", "1 a", None, 2, None), (1, "ics", "1", "1 b", None, 0, None)])
        self.assertEqual(planned["links"], [(1, ("ics", "1"), 0, None)])
        self.assertEqual(planned["duplicates"], [(1, "ics", "1")])

    def test_counts_per_origin(self):
        planned = mv.plan_terms(self.rows())
        self.assertEqual(mv.per_origin(planned["terms"]), {"eurovoc": 1, "ics": 1, "cas": 1, "model": 2})


class FakeCursor:
    """Answers the information_schema queries of migrate_categories() from a description of the tables."""

    def __init__(self, tables, columns, foreign_keys, indexes):
        self.tables, self.columns, self.fks, self.indexes = tables, columns, foreign_keys, indexes
        self.executed = []
        self.result = []

    def execute(self, sql, params=None):
        if "information_schema.TABLES" in sql:
            self.result = [(t,) for t in self.tables]
        elif "information_schema.COLUMNS" in sql:
            self.result = [(c,) for c in self.columns.get(params[0], ())]
        elif "REFERENTIAL_CONSTRAINTS" in sql:
            self.result = [(f,) for f in self.fks.get(params[0], ())]
        elif "information_schema.STATISTICS" in sql:
            self.result = [(i,) for i in self.indexes.get(params, ())]
        else:
            self.executed.append(sql)
            self.result = []

    def fetchall(self):
        return self.result


class MigrateCategoriesTestCase(unittest.TestCase):
    def legacy(self):
        return FakeCursor({"Keyword", "DocumentKeyword", "Document"}, {}, {}, {})

    def test_dry_run_changes_nothing(self):
        cursor = self.legacy()
        steps = mv.migrate_categories(cursor, apply=False)
        self.assertEqual(cursor.executed, [])
        self.assertEqual(steps[0], "RENAME TABLE Keyword TO SourceCategory, DocumentKeyword TO DocumentSourceCategory")

    def test_apply_renames_tables_columns_indexes_and_foreign_keys(self):
        cursor = FakeCursor({"Keyword", "DocumentKeyword"},
                            {"SourceCategory": ("id", "keyword"), "DocumentSourceCategory": ("document_id", "keyword_id")},
                            {"DocumentSourceCategory": ("fk_documentkeyword_document", "fk_documentkeyword_keyword")},
                            {("SourceCategory", "name"): ("keyword",),
                             ("DocumentSourceCategory", "category_id"): ("fk_documentkeyword_keyword",)})
        mv.migrate_categories(cursor, apply=True)
        self.assertEqual(cursor.executed, [
            "RENAME TABLE Keyword TO SourceCategory, DocumentKeyword TO DocumentSourceCategory",
            "ALTER TABLE SourceCategory CHANGE keyword name VARCHAR(255) NOT NULL",
            "ALTER TABLE SourceCategory RENAME INDEX `keyword` TO uq_source_category_name",
            "ALTER TABLE DocumentSourceCategory DROP FOREIGN KEY `fk_documentkeyword_document`",
            "ALTER TABLE DocumentSourceCategory DROP FOREIGN KEY `fk_documentkeyword_keyword`",
            "ALTER TABLE DocumentSourceCategory CHANGE keyword_id category_id INT NOT NULL",
            "ALTER TABLE DocumentSourceCategory RENAME INDEX `fk_documentkeyword_keyword` "
            "TO ix_document_source_category_category",
            "ALTER TABLE DocumentSourceCategory ADD CONSTRAINT fk_document_source_category_document "
            "FOREIGN KEY (document_id) REFERENCES Document (id)",
            "ALTER TABLE DocumentSourceCategory ADD CONSTRAINT fk_document_source_category_category "
            "FOREIGN KEY (category_id) REFERENCES SourceCategory (id)"])

    def test_a_migrated_database_is_left_alone(self):
        cursor = FakeCursor({"SourceCategory", "DocumentSourceCategory"},
                            {"SourceCategory": ("id", "name"), "DocumentSourceCategory": ("document_id", "category_id")},
                            {"DocumentSourceCategory": ("fk_document_source_category_document",
                                                        "fk_document_source_category_category")},
                            {("SourceCategory", "name"): ("uq_source_category_name",),
                             ("DocumentSourceCategory", "category_id"): ("ix_document_source_category_category",)})
        self.assertEqual(mv.migrate_categories(cursor, apply=True), [])
        self.assertEqual(cursor.executed, [])

    def test_both_layouts_at_once_is_an_error(self):
        with self.assertRaises(mv.MigrationError):
            mv.migrate_categories(FakeCursor({"Keyword", "SourceCategory"}, {}, {}, {}), apply=True)


class AppBeforeTheMigrationTestCase(unittest.TestCase):
    """The code is deployed (git pull) before the migration runs: the app reads both layouts."""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("SECRET_KEY", "test")
        import app.app as application
        cls.app = application

    def test_vocab_is_read_per_request(self):
        answers = {"tables": [("Keyword",), ("DocumentKeyword",), ("DocumentTerm",)],
                   "columns": [("document_id",), ("term",)]}

        class Cursor:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def execute(self, sql, params=None):
                self.rows = answers["tables"] if "TABLES" in sql else answers["columns"]

            def fetchall(self):
                return [{"n": r[0]} for r in self.rows]

        db = type("Db", (), {"cursor": lambda self: Cursor()})()
        with self.app.app.test_request_context("/"):
            layout = self.app.vocab(db)
            self.assertEqual(layout, {"categories": vocabulary.LEGACY_CATEGORIES, "terms": "legacy"})
            filters = self.app.apply_vocab({}, db)
            self.assertTrue(filters["legacy_terms"])
        answers.update(tables=[("SourceCategory",), ("DocumentSourceCategory",), ("Term",), ("DocumentTerm",)],
                       columns=[("document_id",), ("term_id",)])
        with self.app.app.test_request_context("/"):
            self.assertEqual(self.app.vocab(db), {"categories": vocabulary.CATEGORIES, "terms": "term"},
                             "after the migration the next request sees the new layout without a restart")


if __name__ == "__main__":
    unittest.main()
