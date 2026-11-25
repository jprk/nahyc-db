"""Keywords of the documents (table `DocumentTerm`), doc/KLICOVA_SLOVA.md.

The table `Keyword`/`DocumentKeyword` holds the categories of the source
surveys (Sinay's "Verflüssigung", "Untertage Gasspeicher", ...), not the
keywords of a document. The keywords live in a table of their own, each with
its origin:

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

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
DATA = REPO_ROOT / "data"
CACHES = {
    "eurovoc": DATA / "eurovoc_cache.json",
    "ics": DATA / "ics_cache.json",
    "model": DATA / "keyword_model_cache.json",
}
ORIGINS = ("eurovoc", "ics", "cas", "model")
ORIGIN_LABELS = {"eurovoc": "EuroVoc (Úřad pro publikace EU)", "ics": "třídník ICS (katalog ČAS)",
                 "cas": "deskriptory ČSN (katalog ČAS)", "model": "odvozeno jazykovým modelem"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS DocumentTerm (
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


def ensure_schema(cursor):
    cursor.execute(SCHEMA)


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
                term = " ".join((t["term"] or "").split())[:255]
                if not term or term.lower() in seen:
                    continue
                seen.add(term.lower())
                rows.append((doc_id, origin, position, t.get("code"), term, (t.get("term_en") or None)))
    return rows


def write(cursor, rows, origins):
    ensure_schema(cursor)
    for origin in origins:
        cursor.execute("DELETE FROM DocumentTerm WHERE origin = %s", (origin,))
    cursor.executemany("INSERT INTO DocumentTerm (document_id, origin, position, code, term, term_en) "
                       "VALUES (%s, %s, %s, %s, %s, %s)", rows)


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
    args = parser.parse_args(argv)
    conn = connect(args.env_file)
    try:
        cur = conn.cursor()
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
        if args.apply:
            write(cur, rows, origins)
            conn.commit()
            print("written")
        else:
            print("dry run, nothing written (--apply)")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
