"""Keywords of the documents (tables `Term` and `DocumentTerm`, vocabulary.py),
doc/KLICOVA_SLOVA.md.

The tables `SourceCategory`/`DocumentSourceCategory` hold the categories of the
source surveys (Sinay's "Verflüssigung", "Untertage Gasspeicher", ...), not the
keywords of a document. The keywords live in a central table `Term`, each with
its origin, linked to the documents by `DocumentTerm`:

- `eurovoc` — the EuroVoc descriptors of an EU act, from Cellar (fetch_eurovoc.py);
- `ics`     — the International Classification for Standards of a standard, from
              the catalogue of ČAS (fetch_ics.py);
- `cas`     — the descriptors and keywords the ČAS catalogue gives to a ČSN (fetch_ics.py);
- `model`   — keywords a language model drew from the title, the annotation and
              the full text we have (extract_keywords.py).

The fetchers write caches under data/ keyed by the document key (`document_keys()`:
the identifier, else `url-<hash of the address>`, else `title-<hash of the title>`), which survives a rebuild of
the database; this script writes the caches into the table:

    .venv/bin/python src/tools/document_terms.py                 # dry run, live DB
    .venv/bin/python src/tools/document_terms.py --apply --env-file .env.test
    .venv/bin/python src/tools/document_terms.py --similar      # keywords differing in case/diacritics

It replaces the rows of every origin it has a cache for, so a rerun after a
rebuild (init_db.py truncates the table) restores them.
"""
import argparse
import collections
import json
import pathlib
import sys

import fetch_ics
import fulltext_keys
import vocabulary
import state_paths

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
DATA = REPO_ROOT / "data"
CACHES = {
    "eurovoc": state_paths.data_file("eurovoc_cache.json"),
    "ics": state_paths.data_file("ics_cache.json"),
    "model": state_paths.data_file("keyword_model_cache.json"),
}
ORIGINS = ("eurovoc", "ics", "cas", "model")
ORIGIN_LABELS = {"eurovoc": "EuroVoc (Úřad pro publikace EU)", "ics": "třídník ICS (katalog ČAS)",
                 "cas": "deskriptory ČSN (katalog ČAS)", "model": "odvozeno jazykovým modelem"}

class LegacyLayoutError(Exception):
    """The database still has the old DocumentTerm (text per document): run migrate_vocabulary.py."""


def ensure_schema(cursor):
    """Creates Term and DocumentTerm (vocabulary.py) when missing; refuses the old layout."""
    if vocabulary.term_layout(cursor) == "legacy":
        raise LegacyLayoutError("DocumentTerm has the old layout — run src/tools/migrate_vocabulary.py --apply first")
    cursor.execute(vocabulary.TERM_SCHEMA)
    cursor.execute(vocabulary.DOCUMENT_TERM_SCHEMA.format(table="DocumentTerm"))


def doc_key(identifier, url, title=None, shared_urls=()):
    """The key a document is known by in the caches: its identifier, else its address
    (`url-<hash>`), else — or when other documents without an identifier have the same
    address, as the 14 BVEG leaflets under https://www.bveg.de/ — its title (`title-<hash>`)."""
    if identifier and identifier.strip():
        return identifier.strip()
    first = fulltext_keys.first_url(url)
    if first and first not in shared_urls:
        return fulltext_keys.url_designation(first)
    return fulltext_keys.title_designation(title) or None


def document_keys(documents):
    """{document id: key} for rows of fetch_documents() — (id, identifier, url, type, title, ...)."""
    counts = collections.Counter(fulltext_keys.first_url(r[2]) for r in documents
                                 if not (r[1] and r[1].strip()) and r[2])
    shared = {url for url, n in counts.items() if n > 1}
    return {r[0]: doc_key(r[1], r[2], r[4], shared) for r in documents}


def load_cache(path):
    path = pathlib.Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def save_cache(path, cache):
    path = pathlib.Path(path)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(cache, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def terms_from_caches(caches=None):
    """{origin: {doc key: [{"code", "term", "term_en"}]}} from the caches on disk.
    The ICS cache holds both `ics` and `cas` terms."""
    caches = caches or {name: load_cache(path) for name, path in CACHES.items()}
    out = {origin: {} for origin in ORIGINS}
    for key, entry in caches.get("eurovoc", {}).items():
        out["eurovoc"][key] = [{"code": t["code"], "term": t["cs"] or t["en"], "term_en": t["en"]}
                               for t in entry.get("terms", []) if t.get("cs") or t.get("en")]
    ics_names = {t["code"]: t["name"] for entry in caches.get("ics", {}).values() for t in entry.get("ics", [])
                 if t.get("name")}
    for key, entry in caches.get("ics", {}).items():
        classes = entry.get("ics") or [{"code": code, "name": ics_names.get(code, "")}
                                       for code in ((entry.get("iso") or {}).get("ics") or [])]
        out["ics"][key] = [{"code": t["code"], "term": f'{t["code"]} {t["name"]}'.strip(), "term_en": None}
                           for t in classes]
        out["cas"][key] = [{"code": None, "term": t, "term_en": None} for t in entry.get("descriptors", [])
                           if fetch_ics._WORD.search(t)]
    for key, entry in caches.get("model", {}).items():
        result = entry.get("result") or {}
        out["model"][key] = [{"code": None, "term": t, "term_en": None} for t in result.get("keywords", [])]
    return out


def plan(documents, terms):
    """[(document_id, origin, position, code, term, term_en)] for `documents` — rows of
    fetch_documents(), (id, identifier, url, type, title, ...) — and `terms` from terms_from_caches()."""
    rows = []
    keys = document_keys(documents)
    for document in documents:
        doc_id = document[0]
        key = keys[doc_id]
        if not key:
            continue
        for origin in ORIGINS:
            seen = set()
            for position, t in enumerate(terms.get(origin, {}).get(key, [])):
                term = vocabulary.clean(t["term"])
                ident = vocabulary.term_key(origin, t.get("code"), term)
                if not term or term.lower() in seen or ident in seen:
                    continue
                seen.update((term.lower(), ident))
                rows.append((doc_id, origin, position, t.get("code"), term, (t.get("term_en") or None)))
    return rows


def write(cursor, rows, origins):
    """Replaces the links of `origins` by `rows` of plan(): every keyword goes once into
    Term (unique by origin and code or text, vocabulary.term_key()), every row becomes a
    link in DocumentTerm. Keywords of these origins no document uses any more are dropped."""
    ensure_schema(cursor)
    for origin in origins:
        cursor.execute("DELETE l FROM DocumentTerm l JOIN Term t ON t.id = l.term_id WHERE t.origin = %s", (origin,))
    terms = {}
    for _doc, origin, _pos, code, term, term_en in rows:
        terms.setdefault((origin, vocabulary.term_key(origin, code, term)), (code, term, term_en))
    cursor.executemany("INSERT INTO Term (origin, code, term, term_en, term_key, term_norm) "
                       "VALUES (%s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE code = VALUES(code), "
                       "term = VALUES(term), term_en = VALUES(term_en), term_norm = VALUES(term_norm)",
                       [(origin, code, term, term_en, key, vocabulary.term_norm(term))
                        for (origin, key), (code, term, term_en) in terms.items()])
    cursor.execute("SELECT origin, term_key, id FROM Term")
    ids = {(r[0], r[1]): r[2] for r in cursor.fetchall()}
    cursor.executemany("INSERT IGNORE INTO DocumentTerm (document_id, term_id, position) VALUES (%s, %s, %s)",
                       [(doc, ids[(origin, vocabulary.term_key(origin, code, term))], pos)
                        for doc, origin, pos, code, term, _ in rows])
    for origin in origins:
        cursor.execute("DELETE t FROM Term t LEFT JOIN DocumentTerm l ON l.term_id = t.id "
                       "WHERE t.origin = %s AND l.term_id IS NULL", (origin,))


def similar(cursor):
    """vocabulary.similar_groups() over the keywords in Term."""
    cursor.execute("SELECT DISTINCT BINARY term FROM Term")
    return vocabulary.similar_groups(r[0].decode("utf-8") if isinstance(r[0], bytes) else r[0]
                                     for r in cursor.fetchall())


def connect(env_file=None):
    import pymysql
    from dotenv import dotenv_values
    import testdb
    env = dotenv_values(env_file or str(testdb.find_env_file(".env")))
    return pymysql.connect(host=env["DB_HOST"], port=int(env.get("DB_PORT") or 3306), user=env["DB_USER"],
                           password=env["DB_PASSWORD"], database=env["DB_NAME"], charset="utf8mb4")


def fetch_documents(cursor):
    """[(id, identifier, url, type name, title, language, description, file_path)] of every document."""
    cursor.execute("SELECT d.id, d.identifier, d.url, dt.name, d.title, d.language, "
                   "COALESCE(NULLIF(d.popis_autoritativni, ''), NULLIF(d.description, '')), d.file_path "
                   "FROM Document d LEFT JOIN DocumentType dt ON dt.id = d.type_id ORDER BY d.id")
    return cursor.fetchall()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--apply", action="store_true", help="write to the database (dry run without it)")
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--similar", action="store_true",
                        help="only list the keywords whose forms differ in case or diacritics (no writing)")
    args = parser.parse_args(argv)
    conn = connect(args.env_file)
    try:
        cur = conn.cursor()
        if args.similar:
            if vocabulary.term_layout(cur) != "term":
                print("no table Term — run migrate_vocabulary.py --apply first")
                return 1
            groups = similar(cur)
            print(f"groups of keywords differing only in case or diacritics: {len(groups)}")
            for _norm, forms in groups:
                print("  " + " | ".join(forms))
            return 0
        documents = fetch_documents(cur)
        terms = terms_from_caches()
        rows = plan(documents, terms)
        origins = [o for o in ORIGINS if terms[o]]
        per_origin = collections.Counter(r[1] for r in rows)
        docs = collections.defaultdict(set)
        for r in rows:
            docs[r[1]].add(r[0])
        for origin in ORIGINS:
            print(f"{origin:8s} {per_origin[origin]:6d} terms over {len(docs[origin]):5d} documents")
        print(f"documents with any term: {len({r[0] for r in rows})} of {len(documents)}")
        print(f"distinct keywords (Term): {len({(r[1], vocabulary.term_key(r[1], r[3], r[4])) for r in rows})}")
        if args.apply:
            try:
                write(cur, rows, origins)
            except LegacyLayoutError as error:
                conn.rollback()
                print(f"error: {error}", file=sys.stderr)
                return 1
            conn.commit()
            print("written")
        else:
            print("dry run, nothing written (--apply)")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
