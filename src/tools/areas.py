"""Areas of the catalogue (data/areas.json, doc/OBLASTI.md): a small Czech set of
subject areas tied to the subject circles of doc/DATABASE_SCOPE.md, replacing the
238 keywords of the source spreadsheets in the "Oblast" filter and in the tags.

A document gets its areas from its original keywords (exact values and patterns of
technical committees; issuers, STN states and generic labels are ignored) and from
its title and designation (title_rules). A document none of the rules give an area
gets the fallback area ("Obecné a průřezové předpisy") and is reported as uncertain.

The original keywords stay in Keyword/DocumentKeyword: they are searched (hidden)
and exported, only no longer offered in the filter. Stored in `Area` and
`DocumentArea` (origin `keyword`, `identifier`, `type`, `title` or `fallback`)."""
import json
import pathlib
import re

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = REPO_ROOT / "data" / "areas.json"

SCHEMA = (
    """CREATE TABLE IF NOT EXISTS Area (
      id INT AUTO_INCREMENT PRIMARY KEY,
      code VARCHAR(40) NOT NULL UNIQUE,
      name VARCHAR(200) NOT NULL,
      okruh TINYINT NULL,
      sort INT NOT NULL DEFAULT 0,
      public TINYINT(1) NOT NULL DEFAULT 1
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS DocumentArea (
      document_id INT NOT NULL,
      area_id INT NOT NULL,
      origin VARCHAR(20) NOT NULL,
      PRIMARY KEY (document_id, area_id),
      KEY idx_document_area_area (area_id),
      CONSTRAINT fk_document_area_document FOREIGN KEY (document_id) REFERENCES Document(id) ON DELETE CASCADE,
      CONSTRAINT fk_document_area_area FOREIGN KEY (area_id) REFERENCES Area(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
)


class Rules:
    def __init__(self, config):
        self.areas = config["areas"]
        self.codes = [a["code"] for a in self.areas]
        self.fallback = config["fallback"]
        self.keywords = config["keywords"]
        self.committees = [(re.compile(r["pattern"]), r["areas"]) for r in config["committee_rules"]]
        self.ignore = [re.compile(p) for p in config["ignore"]]
        self.categories = set(config.get("source_categories", []))
        self.types = config.get("type_rules", {})
        self.identifiers = config.get("identifiers", {})
        self.titles = [(r["area"], re.compile(r["pattern"], re.IGNORECASE),
                        re.compile(r["unless"], re.IGNORECASE) if r.get("unless") else None)
                       for r in config["title_rules"]]

    def keyword_areas(self, keyword):
        """(areas, known): the areas a keyword gives, and whether a rule knows it."""
        keyword = (keyword or "").strip()
        if keyword in self.keywords:
            return list(self.keywords[keyword]), True
        found = []
        for pattern, codes in self.committees:
            if pattern.search(keyword):
                found += [c for c in codes if c not in found]
        if found:
            return found, True
        return [], keyword in self.categories or any(p.search(keyword) for p in self.ignore)

    def title_areas(self, text):
        text = text or ""
        return [code for code, pattern, unless in self.titles
                if pattern.search(text) and not (unless and unless.search(text))]

    def assign(self, document):
        """{code: origin} for a document {identifier, title, keywords}, in the order of the areas."""
        found = {}
        for keyword in document.get("keywords") or []:
            for code in self.keyword_areas(keyword)[0]:
                found.setdefault(code, "keyword")
        for code in self.identifiers.get((document.get("identifier") or "").strip(), []):
            found.setdefault(code, "identifier")
        for code in self.types.get(document.get("type") or "", []):
            found.setdefault(code, "type")
        text = " ".join(filter(None, (document.get("identifier"), document.get("title"))))
        for code in self.title_areas(text):
            found.setdefault(code, "title")
        if not found:
            found[self.fallback] = "fallback"
        return {c: found[c] for c in self.codes if c in found}

    def unknown_keywords(self, keywords):
        return sorted(k for k in set(keywords) if not self.keyword_areas(k)[1])


def load(path=CONFIG_PATH):
    return Rules(json.loads(pathlib.Path(path).read_text(encoding="utf-8")))


def ensure_schema(cursor):
    for statement in SCHEMA:
        cursor.execute(statement)
    # Area.public (2026-11-23): an area left out of the public filter ("Oblast dosud neurčena")
    cursor.execute("SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() "
                   "AND TABLE_NAME = 'Area' AND COLUMN_NAME = 'public'")
    row = cursor.fetchone()
    if not (row[0] if not isinstance(row, dict) else list(row.values())[0]):
        cursor.execute("ALTER TABLE Area ADD COLUMN public TINYINT(1) NOT NULL DEFAULT 1")


def _tuples(cursor):
    """The fetched rows as tuples, whatever the cursor class (the app uses DictCursor)."""
    return [tuple(r.values()) if isinstance(r, dict) else tuple(r) for r in cursor.fetchall()]


def load_documents(cursor, document_id=None):
    """[{id, identifier, title, type, keywords}] of every document."""
    where, params = (" WHERE d.id = %s", (document_id,)) if document_id is not None else ("", ())
    cursor.execute("SELECT d.id, d.identifier, d.title, dt.name FROM Document d "
                   "LEFT JOIN DocumentType dt ON dt.id = d.type_id" + where, params)
    documents = {r[0]: {"id": r[0], "identifier": r[1], "title": r[2], "type": r[3], "keywords": []}
                 for r in _tuples(cursor)}
    where = " WHERE dk.document_id = %s" if document_id is not None else ""
    cursor.execute("SELECT dk.document_id, k.keyword FROM DocumentKeyword dk JOIN Keyword k ON k.id = dk.keyword_id"
                   + where, params)
    for doc_id, keyword in _tuples(cursor):
        if doc_id in documents:
            documents[doc_id]["keywords"].append(keyword)
    return list(documents.values())


def has_table(cursor, name):
    cursor.execute("SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s",
                   (name,))
    row = cursor.fetchone()
    return bool(row[0] if not isinstance(row, dict) else list(row.values())[0])


def current(cursor):
    """{document id: {code: origin}} stored now (empty without the tables)."""
    if not has_table(cursor, "DocumentArea"):
        return {}
    cursor.execute("SELECT da.document_id, a.code, da.origin FROM DocumentArea da JOIN Area a ON a.id = da.area_id")
    stored = {}
    for doc_id, code, origin in _tuples(cursor):
        stored.setdefault(doc_id, {})[code] = origin
    return stored


def plan(rules, documents, stored):
    """{document id: {code: origin}} of the documents whose areas change."""
    changes = {}
    for document in documents:
        wanted = rules.assign(document)
        if stored.get(document["id"]) != wanted:
            changes[document["id"]] = wanted
    return changes


def execute(cursor, rules, changes, create=True):
    """Writes the areas (the Area rows first: names and order follow the data file).
    `create=False` skips the DDL (an implicit commit) inside a transaction of the app."""
    if create:
        ensure_schema(cursor)
    for sort, area in enumerate(rules.areas):
        cursor.execute("INSERT INTO Area (code, name, okruh, sort, public) VALUES (%s, %s, %s, %s, %s) "
                       "ON DUPLICATE KEY UPDATE name = VALUES(name), okruh = VALUES(okruh), sort = VALUES(sort), "
                       "public = VALUES(public)",
                       (area["code"], area["name"], area.get("okruh"), sort, int(area.get("public", True))))
    cursor.execute("SELECT code, id FROM Area")
    ids = dict(_tuples(cursor))
    for doc_id, wanted in changes.items():
        cursor.execute("DELETE FROM DocumentArea WHERE document_id = %s", (doc_id,))
        for code, origin in wanted.items():
            cursor.execute("INSERT INTO DocumentArea (document_id, area_id, origin) VALUES (%s, %s, %s)",
                           (doc_id, ids[code], origin))
    # an area dropped from the data file goes with its links
    cursor.execute("DELETE FROM Area WHERE code NOT IN (" + ", ".join(["%s"] * len(rules.codes)) + ")", rules.codes)


def assign_document(cursor, document_id, rules=None):
    """Gives one new document its areas (app/candidates_admin.py on acceptance), when the
    database has the tables; returns the codes, or None without the tables."""
    if not has_table(cursor, "DocumentArea"):
        return None
    rules = rules or load()
    documents = load_documents(cursor, document_id)
    if not documents:
        return []
    changes = {document_id: rules.assign(documents[0])}
    execute(cursor, rules, changes, create=False)
    return list(changes[document_id])
