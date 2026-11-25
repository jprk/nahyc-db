"""Integration test of src/tools/migrate_vocabulary.py against the TEST database
(`.env.test`, `h2regdocs_test`), never the real one. run_tests.py migrates the test
copy of the live database before the tests; this test turns it back into the old
layout (Keyword/DocumentKeyword, DocumentTerm with the text of the keyword, as the
live database has it until the migration), runs the migration and checks that every
category, every link and every keyword of every document is back unchanged, and that
a second run changes nothing. If it fails half-way, the test database may stay in the
old layout; the application reads both and the next run_tests.py refreshes it."""
import pathlib
import sys
import unittest

from dotenv import dotenv_values

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src" / "tools"))
import migrate_vocabulary as mv  # noqa: E402
import testdb  # noqa: E402
import vocabulary  # noqa: E402

LEGACY_DOCUMENT_TERM = """
CREATE TABLE DocumentTerm_old (
  id INT AUTO_INCREMENT PRIMARY KEY,
  document_id INT NOT NULL,
  origin ENUM('eurovoc','ics','cas','model') NOT NULL,
  code VARCHAR(100) NULL,
  term VARCHAR(255) NOT NULL,
  term_en VARCHAR(255) NULL,
  position SMALLINT NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_document_term (document_id, origin, term),
  KEY ix_document_term_term (term),
  CONSTRAINT fk_documentterm_document FOREIGN KEY (document_id) REFERENCES Document (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_czech_ci
"""


def downgrade(cursor):
    """The migrated test database back in the layout the live database has before the migration."""
    cursor.execute("RENAME TABLE SourceCategory TO Keyword, DocumentSourceCategory TO DocumentKeyword")
    cursor.execute("ALTER TABLE DocumentKeyword DROP FOREIGN KEY fk_document_source_category_document, "
                   "DROP FOREIGN KEY fk_document_source_category_category")
    cursor.execute("ALTER TABLE Keyword CHANGE name keyword VARCHAR(255) NOT NULL, "
                   "RENAME INDEX uq_source_category_name TO keyword")
    cursor.execute("ALTER TABLE DocumentKeyword CHANGE category_id keyword_id INT NOT NULL, "
                   "RENAME INDEX ix_document_source_category_category TO fk_documentkeyword_keyword")
    cursor.execute("ALTER TABLE DocumentKeyword ADD CONSTRAINT fk_documentkeyword_document FOREIGN KEY (document_id) "
                   "REFERENCES Document (id), ADD CONSTRAINT fk_documentkeyword_keyword FOREIGN KEY (keyword_id) "
                   "REFERENCES Keyword (id)")
    cursor.execute("DROP TABLE IF EXISTS DocumentTerm_old")
    cursor.execute(LEGACY_DOCUMENT_TERM)
    cursor.execute("INSERT INTO DocumentTerm_old (document_id, origin, code, term, term_en, position, created_at) "
                   "SELECT l.document_id, t.origin, t.code, t.term, t.term_en, l.position, l.created_at "
                   "FROM DocumentTerm l JOIN Term t ON t.id = l.term_id")
    cursor.execute("DROP TABLE DocumentTerm")
    cursor.execute("DROP TABLE Term")
    cursor.execute("RENAME TABLE DocumentTerm_old TO DocumentTerm")


def snapshot(cursor):
    cat = vocabulary.category_tables(cursor)
    cursor.execute(f"SELECT id, {cat.name} FROM {cat.table}")
    categories = set(cursor.fetchall())
    cursor.execute(f"SELECT document_id, {cat.fk} FROM {cat.link}")
    links = set(cursor.fetchall())
    if vocabulary.term_layout(cursor) == "legacy":
        cursor.execute("SELECT document_id, origin, code, BINARY term, term_en, position FROM DocumentTerm")
    else:
        cursor.execute("SELECT l.document_id, t.origin, t.code, BINARY t.term, t.term_en, l.position "
                       "FROM DocumentTerm l JOIN Term t ON t.id = l.term_id")
    terms = sorted(cursor.fetchall())
    return categories, links, terms


class MigrateVocabularyDatabaseTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        env = dotenv_values(testdb.find_env_file(".env.test"))
        if env.get("DB_NAME") != "h2regdocs_test":
            raise unittest.SkipTest(".env.test does not point at h2regdocs_test — refusing to guess")
        cls.env_file = str(testdb.find_env_file(".env.test"))

    def connect(self):
        conn, name = mv.connect(self.env_file)
        self.assertEqual(name, "h2regdocs_test")
        return conn

    def test_round_trip_from_the_old_layout(self):
        conn = self.connect()
        try:
            cursor = conn.cursor()
            if vocabulary.term_layout(cursor) != "term" or vocabulary.category_tables(cursor) != vocabulary.CATEGORIES:
                mv.migrate(conn, apply=True)  # a database a previous failed run left in the old layout
            before = snapshot(cursor)
            self.assertTrue(before[2], "the test copy of the live database has keywords")
            downgrade(cursor)
            conn.commit()
            self.assertEqual(vocabulary.category_tables(cursor), vocabulary.LEGACY_CATEGORIES)
            self.assertEqual(vocabulary.term_layout(cursor), "legacy")
            self.assertEqual(snapshot(cursor), before, "the downgrade itself loses nothing")

            dry = mv.migrate(conn, apply=False)
            self.assertEqual(vocabulary.term_layout(cursor), "legacy", "a dry run changes nothing")
            self.assertTrue(any(line.startswith("to do: RENAME TABLE Keyword") for line in dry), dry)

            lines = mv.migrate(conn, apply=True)
            self.assertEqual(vocabulary.category_tables(cursor), vocabulary.CATEGORIES)
            self.assertEqual(vocabulary.term_layout(cursor), "term")
            self.assertEqual(snapshot(cursor), before, "every category, link and keyword is back")
            before_line = next(line for line in lines if line.startswith("before: keywords"))
            after_line = next(line for line in lines if line.startswith("after: keywords"))
            self.assertEqual(before_line.split("links", 1)[1], after_line.split("links", 1)[1])
            cursor.execute("SHOW TABLES LIKE 'DocumentTerm\\_%'")
            self.assertEqual(cursor.fetchall(), (), "no table of the migration is left behind")

            again = mv.migrate(conn, apply=True)
            self.assertEqual(again[-1], "done: nothing, already migrated")
            self.assertEqual(snapshot(cursor), before)
        finally:
            conn.close()

    def test_keywords_are_unique_per_origin_and_key(self):
        conn = self.connect()
        try:
            cursor = conn.cursor()
            if vocabulary.term_layout(cursor) != "term":
                self.skipTest("the test database is not migrated")
            cursor.execute("SELECT COUNT(*) FROM Term t LEFT JOIN DocumentTerm l ON l.term_id = t.id "
                           "WHERE l.term_id IS NULL")
            self.assertEqual(cursor.fetchone()[0], 0, "no keyword without a document")
            cursor.execute("SELECT COUNT(*) FROM Term WHERE origin IN ('eurovoc', 'ics') AND term_key <> code")
            self.assertEqual(cursor.fetchone()[0], 0, "EuroVoc and ICS keywords are identified by their code")
            cursor.execute("SELECT id, term, term_norm FROM Term ORDER BY id LIMIT 200")
            for _id, term, norm in cursor.fetchall():
                self.assertEqual(norm, vocabulary.term_norm(term))
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
