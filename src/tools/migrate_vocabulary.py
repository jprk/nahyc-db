"""Migrates the two vocabularies of the documents to their new tables (vocabulary.py,
doc/KLICOVA_SLOVA.md odstavec 4, doc/OBLASTI.md odstavec 4):

1. the categories of the source surveys: `Keyword` -> `SourceCategory` (column
   `keyword` -> `name`), `DocumentKeyword` -> `DocumentSourceCategory` (`keyword_id`
   -> `category_id`). The rows and their ids stay, so an old link `?keyword_id=N`
   still finds its category;
2. the keywords: the old `DocumentTerm` (one row per document and keyword, with the
   text) becomes one central table `Term` (origin, code, term, term_en; unique by
   origin and code for EuroVoc and ICS, by the exact text for ČAS and the model) and
   the link table `DocumentTerm` (document_id, term_id, position). Every old row
   becomes one link; the script compares the old rows with the new ones before it
   swaps the tables and drops the old one.

It counts the rows before and after and lists the groups of keywords whose forms
differ only in case or diacritics (it does not merge them; `--similar` lists all).
Idempotent: a migrated database is left as it is. Dry run unless --apply; back up
the database first (backup_db.py). The web application works with both layouts, so
the migration may follow the deployment of the code; run_tests.py applies it to the
test database after each refresh until the live database is migrated.

Usage: .venv/bin/python src/tools/migrate_vocabulary.py [--apply] [--env-file FILE] [--similar] [--quiet]
"""
import argparse
import collections
import pathlib
import sys

import pymysql

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import vocabulary  # noqa: E402

NEW_LINKS = "DocumentTerm_new"
OLD_LINKS = "DocumentTerm_legacy"


class MigrationError(Exception):
    pass


# ---------------------------------------------------------------- the plan (no database)

def plan_terms(rows):
    """The central keywords and the links for the rows of the old DocumentTerm —
    (document_id, origin, code, term, term_en, position, created_at). Returns a dict:
    `terms` {(origin, key): {"code", "term", "term_en", "created_at"}}, `links`
    [(document_id, (origin, key), position, created_at)], `conflicts` [(origin, key,
    [term, ...])] — a code with several texts (the most frequent one wins) — and
    `duplicates` [(document_id, origin, key)], rows that would become the same link."""
    texts = collections.defaultdict(collections.Counter)
    created = {}
    links = {}
    duplicates = []
    for document_id, origin, code, term, term_en, position, created_at in rows:
        key = vocabulary.term_key(origin, code, term)
        ident = (origin, key)
        texts[ident][(vocabulary.clean(term), (term_en or None), (code or None))] += 1
        if ident not in created or (created_at and created[ident] and created_at < created[ident]):
            created[ident] = created_at
        link = (document_id, ident)
        if link in links:
            duplicates.append((document_id, origin, key))
            if position < links[link][0]:
                links[link] = (position, created_at)
        else:
            links[link] = (position, created_at)
    terms, conflicts = {}, []
    for ident, counter in texts.items():
        (term, term_en, code), _ = max(counter.items(), key=lambda item: (item[1], item[0][0]))
        terms[ident] = {"code": code, "term": term, "term_en": term_en, "created_at": created.get(ident)}
        if len({t for t, _, _ in counter}) > 1:
            conflicts.append((ident[0], ident[1], sorted({t for t, _, _ in counter})))
    return {"terms": terms,
            "links": [(doc, ident, pos, at) for (doc, ident), (pos, at) in sorted(links.items(),
                                                                                  key=lambda i: (i[0][0], i[0][1]))],
            "conflicts": conflicts, "duplicates": duplicates}


def per_origin(idents):
    counts = collections.Counter(origin for origin, _ in idents)
    return {origin: counts.get(origin, 0) for origin in vocabulary.TERM_ORIGINS}


def format_origins(counts):
    return ", ".join(f"{origin} {counts.get(origin, 0)}" for origin in vocabulary.TERM_ORIGINS)


# ---------------------------------------------------------------- the database

def scalar(cursor, sql, params=()):
    cursor.execute(sql, params)
    return cursor.fetchone()[0]


def foreign_keys(cursor, table):
    cursor.execute("SELECT CONSTRAINT_NAME FROM information_schema.REFERENTIAL_CONSTRAINTS "
                   "WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME = %s", (table,))
    return {r[0] for r in cursor.fetchall()}


def index_on(cursor, table, column):
    """The names of the secondary indexes whose first column is `column`."""
    cursor.execute("SELECT INDEX_NAME FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = DATABASE() "
                   "AND TABLE_NAME = %s AND COLUMN_NAME = %s AND SEQ_IN_INDEX = 1 AND INDEX_NAME <> 'PRIMARY'",
                   (table, column))
    return [r[0] for r in cursor.fetchall()]


def category_counts(cursor, layout):
    if layout is None:
        return None
    return (scalar(cursor, f"SELECT COUNT(*) FROM {layout.table}"),
            scalar(cursor, f"SELECT COUNT(*) FROM {layout.link}"),
            scalar(cursor, f"SELECT COUNT(DISTINCT document_id) FROM {layout.link}"))


def migrate_categories(cursor, apply):
    """Renames Keyword/DocumentKeyword, their columns, indexes and foreign keys; returns
    the steps (done with `apply`, else to do)."""
    tables = vocabulary.table_names(cursor)
    if "Keyword" in tables and "SourceCategory" in tables:
        raise MigrationError("both Keyword and SourceCategory exist — resolve by hand")
    if "Keyword" not in tables and "SourceCategory" not in tables:
        return []
    steps = []
    if "Keyword" in tables:
        steps.append("RENAME TABLE Keyword TO SourceCategory, DocumentKeyword TO DocumentSourceCategory")
        if not apply:
            return steps + ["columns keyword -> name, keyword_id -> category_id; indexes and foreign keys renamed"]
        cursor.execute(steps[0])

    def step(description, *statements):
        steps.append(description)
        if apply:
            for statement in statements:
                cursor.execute(statement)

    if "keyword" in vocabulary.columns(cursor, "SourceCategory"):
        step("SourceCategory: keyword -> name", "ALTER TABLE SourceCategory CHANGE keyword name VARCHAR(255) NOT NULL")
    for index in index_on(cursor, "SourceCategory", "name"):
        if index != "uq_source_category_name":
            step(f"SourceCategory: index {index} -> uq_source_category_name",
                 f"ALTER TABLE SourceCategory RENAME INDEX `{index}` TO uq_source_category_name")
    wanted = {"fk_document_source_category_document": ("document_id", "Document"),
              "fk_document_source_category_category": ("category_id", "SourceCategory")}
    present = foreign_keys(cursor, "DocumentSourceCategory")
    for name in sorted(present - set(wanted)):
        step(f"DocumentSourceCategory: foreign key {name} dropped",
             f"ALTER TABLE DocumentSourceCategory DROP FOREIGN KEY `{name}`")
    present &= set(wanted)
    if "keyword_id" in vocabulary.columns(cursor, "DocumentSourceCategory"):
        step("DocumentSourceCategory: keyword_id -> category_id",
             "ALTER TABLE DocumentSourceCategory CHANGE keyword_id category_id INT NOT NULL")
    link_columns = vocabulary.columns(cursor, "DocumentSourceCategory")
    if apply or "category_id" in link_columns:
        for index in index_on(cursor, "DocumentSourceCategory", "category_id"):
            if index != "ix_document_source_category_category":
                step(f"DocumentSourceCategory: index {index} -> ix_document_source_category_category",
                     f"ALTER TABLE DocumentSourceCategory RENAME INDEX `{index}` "
                     "TO ix_document_source_category_category")
    for name, (column, parent) in wanted.items():
        if name not in present:
            step(f"DocumentSourceCategory: foreign key {name}",
                 f"ALTER TABLE DocumentSourceCategory ADD CONSTRAINT {name} FOREIGN KEY ({column}) "
                 f"REFERENCES {parent} (id)")
    return steps


def legacy_rows(cursor, table="DocumentTerm"):
    cursor.execute(f"SELECT document_id, origin, code, term, term_en, position, created_at FROM {table} "
                   "ORDER BY document_id, origin, position, id")
    return cursor.fetchall()


def migrated_rows(cursor, links=NEW_LINKS):
    """(document_id, origin, term key, position) of the new links."""
    cursor.execute(f"SELECT l.document_id, t.origin, t.term_key, l.position FROM {links} l "
                   "JOIN Term t ON t.id = l.term_id")
    return {(d, o, k, p) for d, o, k, p in cursor.fetchall()}


def write_terms(cursor, planned):
    """Fills Term and DocumentTerm_new from plan_terms(); returns {(origin, key): id}."""
    for (origin, key), t in planned["terms"].items():
        cursor.execute("INSERT INTO Term (origin, code, term, term_en, term_key, term_norm, created_at) "
                       "VALUES (%s, %s, %s, %s, %s, %s, COALESCE(%s, CURRENT_TIMESTAMP)) "
                       "ON DUPLICATE KEY UPDATE code = VALUES(code), term = VALUES(term), term_en = VALUES(term_en), "
                       "term_norm = VALUES(term_norm)",
                       (origin, t["code"], t["term"], t["term_en"], key, vocabulary.term_norm(t["term"]),
                        t["created_at"]))
    cursor.execute("SELECT origin, term_key, id FROM Term")
    ids = {(o, k): i for o, k, i in cursor.fetchall()}
    cursor.executemany(f"INSERT INTO {NEW_LINKS} (document_id, term_id, position, created_at) "
                       "VALUES (%s, %s, %s, COALESCE(%s, CURRENT_TIMESTAMP))",
                       [(doc, ids[ident], pos, at) for doc, ident, pos, at in planned["links"]])
    return ids


def migrate_terms(conn, apply):
    """Converts the old DocumentTerm; returns (layout before, planned or None, steps)."""
    cursor = conn.cursor()
    tables = vocabulary.table_names(cursor)
    layout = vocabulary.term_layout(cursor, tables)
    steps = []
    if layout == "term":
        return layout, None, steps
    if layout is None:
        steps.append("CREATE TABLE Term, DocumentTerm (empty)")
        if apply:
            cursor.execute(vocabulary.TERM_SCHEMA)
            cursor.execute(vocabulary.DOCUMENT_TERM_SCHEMA.format(table="DocumentTerm"))
        return layout, None, steps
    rows = legacy_rows(cursor)
    planned = plan_terms(rows)
    steps.append(f"Term: {len(planned['terms'])} keywords; DocumentTerm: {len(planned['links'])} links "
                 f"from {len(rows)} rows; old table dropped")
    if not apply:
        return layout, planned, steps
    if "Term" in tables and scalar(cursor, "SELECT COUNT(*) FROM Term"):
        raise MigrationError("Term already has rows while DocumentTerm still has the old layout — resolve by hand")
    cursor.execute(vocabulary.TERM_SCHEMA)
    cursor.execute(f"DROP TABLE IF EXISTS {NEW_LINKS}")  # left by an interrupted run
    cursor.execute(vocabulary.DOCUMENT_TERM_SCHEMA.format(table=NEW_LINKS))
    try:
        write_terms(cursor, planned)
        conn.commit()
        expected = {(d, o, vocabulary.term_key(o, c, t), p) for d, o, c, t, _, p, _ in rows}
        found = migrated_rows(cursor)
        if len(rows) - len(planned["duplicates"]) != scalar(cursor, f"SELECT COUNT(*) FROM {NEW_LINKS}") \
                or (not planned["duplicates"] and found != expected) or not found <= expected:
            raise MigrationError(f"the new links do not match the old rows: {len(found)} links, {len(rows)} rows")
    except Exception:
        conn.rollback()
        cursor.execute(f"DROP TABLE IF EXISTS {NEW_LINKS}")
        cursor.execute("DELETE FROM Term")
        conn.commit()
        raise
    cursor.execute(f"RENAME TABLE DocumentTerm TO {OLD_LINKS}, {NEW_LINKS} TO DocumentTerm")
    cursor.execute(f"DROP TABLE {OLD_LINKS}")
    return layout, planned, steps


def term_counts(cursor):
    """{"terms": {origin: n}, "links": {origin: n}, "documents": n} in the current layout."""
    layout = vocabulary.term_layout(cursor)
    if layout is None:
        return None
    if layout == "legacy":
        cursor.execute("SELECT origin, code, term FROM DocumentTerm")
        rows = cursor.fetchall()
        terms = per_origin({(o, vocabulary.term_key(o, c, t)) for o, c, t in rows})
        links = per_origin([(o, None) for o, _, _ in rows])
        documents = scalar(cursor, "SELECT COUNT(DISTINCT document_id) FROM DocumentTerm")
    else:
        cursor.execute("SELECT origin, COUNT(*) FROM Term GROUP BY origin")
        terms = {o: 0 for o in vocabulary.TERM_ORIGINS} | dict(cursor.fetchall())
        cursor.execute("SELECT t.origin, COUNT(*) FROM DocumentTerm l JOIN Term t ON t.id = l.term_id "
                       "GROUP BY t.origin")
        links = {o: 0 for o in vocabulary.TERM_ORIGINS} | dict(cursor.fetchall())
        documents = scalar(cursor, "SELECT COUNT(DISTINCT document_id) FROM DocumentTerm")
    return {"terms": terms, "links": links, "documents": documents}


def stored_terms(cursor):
    """The texts of the keywords in the current layout."""
    layout = vocabulary.term_layout(cursor)
    if layout is None:
        return []
    cursor.execute("SELECT DISTINCT BINARY term FROM " + ("Term" if layout == "term" else "DocumentTerm"))
    return [r[0].decode("utf-8") if isinstance(r[0], bytes) else r[0] for r in cursor.fetchall()]


def describe(label, cats, terms):
    lines = []
    if cats is None:
        lines.append(f"{label}: no source categories")
    else:
        lines.append(f"{label}: source categories {cats[0]}, links {cats[1]} ({cats[2]} documents)")
    if terms is None:
        lines.append(f"{label}: no keywords")
    else:
        lines.append(f"{label}: keywords {sum(terms['terms'].values())} ({format_origins(terms['terms'])}); "
                     f"links {sum(terms['links'].values())} ({format_origins(terms['links'])}; "
                     f"{terms['documents']} documents)")
    return lines


def connect(env_file=None):
    from dotenv import dotenv_values
    import testdb
    env = dotenv_values(env_file or str(testdb.find_env_file(".env")))
    conn = pymysql.connect(host=env["DB_HOST"], port=int(env.get("DB_PORT") or 3306), user=env["DB_USER"],
                           password=env["DB_PASSWORD"], database=env["DB_NAME"], charset="utf8mb4",
                           autocommit=False)
    return conn, env["DB_NAME"]


def migrate(conn, apply):
    """Runs both parts; returns the printed lines."""
    cursor = conn.cursor()
    lines = []
    before_cats = category_counts(cursor, vocabulary.category_tables(cursor))
    before_terms = term_counts(cursor)
    lines += describe("before", before_cats, before_terms)
    cat_steps = migrate_categories(cursor, apply)
    _layout, planned, term_steps = migrate_terms(conn, apply)
    conn.commit()
    if apply:
        after_cats = category_counts(cursor, vocabulary.category_tables(cursor))
        after_terms = term_counts(cursor)
    else:
        after_cats = before_cats
        after_terms = before_terms if planned is None else {
            "terms": per_origin(planned["terms"]), "links": per_origin([i for _, i, _, _ in planned["links"]]),
            "documents": len({d for d, _, _, _ in planned["links"]})}
    lines += describe("after" if apply else "after (planned)", after_cats, after_terms)
    if before_cats and after_cats and before_cats != after_cats:
        raise MigrationError(f"source categories changed: {before_cats} -> {after_cats}")
    if before_terms and after_terms and planned is not None and not planned["duplicates"] \
            and before_terms["links"] != after_terms["links"]:
        raise MigrationError(f"keyword links changed: {before_terms['links']} -> {after_terms['links']}")
    if planned is not None:
        lines.append(f"codes with several texts (the most frequent kept): {len(planned['conflicts'])}")
        lines += [f"  {o} {k}: {' | '.join(t)}" for o, k, t in planned["conflicts"][:20]]
        lines.append(f"old rows that became one link: {len(planned['duplicates'])}")
    steps = cat_steps + term_steps
    lines.append(("done: " if apply else "to do: ") + ("; ".join(steps) if steps else "nothing, already migrated"))
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--apply", action="store_true", help="change the database (dry run without it)")
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--similar", action="store_true", help="list every group of similar keywords")
    parser.add_argument("--quiet", action="store_true", help="print only the summary")
    args = parser.parse_args(argv)
    conn, name = connect(args.env_file)
    try:
        lines = migrate(conn, args.apply)
        groups = vocabulary.similar_groups(stored_terms(conn.cursor()))
        lines.append(f"groups of keywords differing only in case or diacritics: {len(groups)} "
                     f"({sum(len(f) for _, f in groups)} forms; not merged)")
        shown = groups if args.similar else groups[:15]
        lines += [f"  {' | '.join(forms)}" for _, forms in shown]
        summary = (f"{name}: " + ("migrated" if args.apply else "dry run — add --apply") + "; "
                   + lines[-1 - len(shown)])
    except MigrationError as error:
        conn.rollback()
        print(f"error: {error}", file=sys.stderr)
        return 1
    finally:
        conn.close()
    if not args.quiet:
        print("\n".join(lines))
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
