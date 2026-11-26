"""The two vocabularies a document carries (doc/KLICOVA_SLOVA.md, doc/OBLASTI.md):

* **source categories** — `SourceCategory` / `DocumentSourceCategory`: the values of the
  "keyword", section and class columns of the source surveys (Sinay, Prokop, Haltuf),
  e.g. "Explosionsschutz", "STN (prijatá v sústave)", "6972 - Kryogenické nádoby". They
  describe groups of documents in the source spreadsheets, not a document's content;
  until migrate_vocabulary.py the tables were called `Keyword` / `DocumentKeyword`
  (columns `keyword`, `keyword_id`);
* **keywords** — `Term` / `DocumentTerm`: one row per keyword (EuroVoc descriptor, ICS
  class, ČAS descriptor, keyword of a language model) and the links of the documents to
  them. Until migrate_vocabulary.py `DocumentTerm` held the text of the keyword itself,
  one row per document and keyword.

Code that may meet a database before the migration (the web application, which is
deployed by `git pull` before the migration runs) asks `category_tables()` and
`term_layout()` which layout it has. The tools of the rebuild and of the write order
run after the migration and use the new names.
"""
import collections
import re
import unicodedata

CategoryTables = collections.namedtuple("CategoryTables", "table link name fk")

CATEGORIES = CategoryTables("SourceCategory", "DocumentSourceCategory", "name", "category_id")
LEGACY_CATEGORIES = CategoryTables("Keyword", "DocumentKeyword", "keyword", "keyword_id")

TERM_ORIGINS = ("eurovoc", "ics", "cas", "model")
# origins whose keyword is identified by its code (EuroVoc descriptor, ICS class); the
# others by their text
CODED_ORIGINS = ("eurovoc", "ics")

TERM_SCHEMA = """
CREATE TABLE IF NOT EXISTS Term (
  id INT AUTO_INCREMENT PRIMARY KEY,
  origin ENUM('eurovoc','ics','cas','model') NOT NULL,
  code VARCHAR(100) NULL,
  term VARCHAR(255) NOT NULL,
  term_en VARCHAR(255) NULL,
  term_key VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
  term_norm VARCHAR(255) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_term_origin_key (origin, term_key),
  KEY ix_term_term (term),
  KEY ix_term_norm (term_norm)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_czech_ci
"""

DOCUMENT_TERM_SCHEMA = """
CREATE TABLE IF NOT EXISTS {table} (
  document_id INT NOT NULL,
  term_id INT NOT NULL,
  position SMALLINT NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (document_id, term_id),
  KEY ix_document_term_term (term_id),
  CONSTRAINT fk_document_term_document FOREIGN KEY (document_id) REFERENCES Document (id) ON DELETE CASCADE,
  CONSTRAINT fk_document_term_term FOREIGN KEY (term_id) REFERENCES Term (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_czech_ci
"""


def _first(row):
    return list(row.values())[0] if isinstance(row, dict) else row[0]


def table_names(cursor):
    """The tables of both vocabularies the connected database has."""
    cursor.execute("SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME "
                   "IN ('SourceCategory', 'DocumentSourceCategory', 'Keyword', 'DocumentKeyword', 'Term', "
                   "'DocumentTerm')")
    return {_first(r) for r in cursor.fetchall()}


def columns(cursor, table):
    cursor.execute("SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() "
                   "AND TABLE_NAME = %s", (table,))
    return {_first(r) for r in cursor.fetchall()}


def category_tables(cursor, tables=None):
    """CATEGORIES after the migration, LEGACY_CATEGORIES before it, None without either."""
    tables = table_names(cursor) if tables is None else tables
    if "SourceCategory" in tables:
        return CATEGORIES
    if "Keyword" in tables:
        return LEGACY_CATEGORIES
    return None


def term_layout(cursor, tables=None):
    """'term' — Term + DocumentTerm(document_id, term_id); 'legacy' — DocumentTerm with the
    text of the keyword (before the migration); None — no keywords yet."""
    tables = table_names(cursor) if tables is None else tables
    if "DocumentTerm" not in tables:
        return None
    return "term" if "term_id" in columns(cursor, "DocumentTerm") else "legacy"


def clean(text):
    """The text of a keyword as stored: whitespace collapsed, at most 255 characters."""
    return " ".join((text or "").split())[:255]


def term_key(origin, code, term):
    """What identifies a keyword within its origin: the code of a EuroVoc descriptor or
    an ICS class (its text is a label that may change), else the exact text. Forms that
    differ in case or diacritics stay separate keywords; term_norm() finds them."""
    if origin in CODED_ORIGINS and code:
        return clean(code)
    return clean(term)


_MARKS = re.compile(r"[̀-ͯ]")


def term_norm(term):
    """The text without case and diacritics ("Palivové články" -> "palivove clanky"),
    for similar keywords and for suggestions."""
    decomposed = unicodedata.normalize("NFKD", clean(term).casefold())
    return unicodedata.normalize("NFC", _MARKS.sub("", decomposed))[:255]


def similar_groups(terms):
    """[(norm, [term, ...])] of the keywords whose forms differ only in case or
    diacritics; `terms` are texts (any origin). Each group lists its distinct forms."""
    groups = collections.defaultdict(set)
    for term in terms:
        groups[term_norm(term)].add(clean(term))
    return sorted(((norm, sorted(forms)) for norm, forms in groups.items() if len(forms) > 1),
                  key=lambda g: (-len(g[1]), g[0]))
