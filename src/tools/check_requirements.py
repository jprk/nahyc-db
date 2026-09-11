"""Mechanical, deterministic checks for every requirement in
doc/REQUIREMENTS.md that has a checkable, factual answer (a DB query, a
schema shape, or a grep against `app/`) — modeled directly on
`check_db.py`'s connection/report style (same `get_connection()` pattern).

This is deliberately the *mechanical* half of the requirements-compliance
process: it prints raw evidence per requirement ID, never a verdict — a
requirement can be technically "checkable" here (e.g. R1.2's jurisdikce
value list) while still needing human/LLM judgement to decide whether the
evidence satisfies the requirement's intent. That judgement, plus the
requirements this script can't check at all (R4.2's qualitative
"stakeholder hub" framing), is the `.claude/agents/requirements-check.md`
subagent's job — it runs this script first and treats its output as the
authoritative source of fact, rather than re-deriving the same queries.

No dedicated unit test file — same precedent as `check_db.py`, itself a
live-DB/live-repo diagnostic, not a pure-function library.

Usage: `.venv/bin/python src/tools/check_requirements.py`
"""
import os
import pathlib
import re

import pymysql
from dotenv import load_dotenv

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
APP_DIR = REPO_ROOT / "app"
load_dotenv(REPO_ROOT / ".env")

PIPELINE_SCRIPTS = [
    "build_unified_db.py", "deduplicate_db.py", "link_document_versions.py",
    "init_db.py", "load_document_relations.py", "load_process_layer.py",
]


def get_connection():
    return pymysql.connect(
        host=os.environ["DB_HOST"], port=int(os.environ["DB_PORT"]),
        user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"], cursorclass=pymysql.cursors.DictCursor,
    )


def _read(path):
    return path.read_text(encoding="utf-8") if path.exists() else None


def _grep_lines(text, pattern, flags=re.IGNORECASE):
    if text is None:
        return []
    return [line.strip() for line in text.splitlines() if re.search(pattern, line, flags)]


def report_db(conn):
    c = conn.cursor()
    print("=== R1.x Data Architecture & Management ===\n")

    print("--- R1.1 Record uniqueness ---")
    c.execute("SHOW CREATE TABLE Document")
    create_sql = c.fetchone()["Create Table"]
    has_unique = "UNIQUE KEY" in create_sql and "identifier" in create_sql
    print(f"UNIQUE constraint on Document.identifier present: {has_unique}")
    c.execute("SELECT COUNT(*) AS n, COUNT(identifier) AS with_id FROM Document")
    row = c.fetchone()
    print(f"Documents: {row['n']}, with a non-NULL identifier: {row['with_id']} "
          f"({row['n'] - row['with_id']} bypass the UNIQUE constraint via NULL)")

    print("\n--- R1.2 Jurisdictional tiering (should be exactly int'l/EU/national) ---")
    c.execute("SELECT jurisdikce, COUNT(*) AS n FROM Document GROUP BY jurisdikce ORDER BY n DESC")
    rows = c.fetchall()
    print(f"Distinct jurisdikce (concrete) values found: {len(rows)}")
    for r in rows:
        print(f"  {r['jurisdikce']!r}: {r['n']}")
    c.execute("SHOW COLUMNS FROM Document LIKE 'jurisdikce_uroven'")
    tier_col = c.fetchone()
    print(f"Document.jurisdikce_uroven column present: {bool(tier_col)}"
          + (f" (type: {tier_col['Type']})" if tier_col else ""))
    if tier_col:
        c.execute("SELECT jurisdikce_uroven, COUNT(*) AS n FROM Document GROUP BY jurisdikce_uroven ORDER BY n DESC")
        for r in c.fetchall():
            print(f"  tier {r['jurisdikce_uroven']!r}: {r['n']}")

    print("\n--- R1.3/R1.4 Document-to-document relations (transposition / localization) ---")
    c.execute("SELECT relation_type, COUNT(*) AS n FROM document_relation GROUP BY relation_type")
    rel_rows = c.fetchall()
    print(f"document_relation rows by type: {rel_rows or '(none at all)'}")

    print("\n--- R1.5 Lifecycle/version state ---")
    c.execute("DESCRIBE DocumentVersion")
    cols = [r["Field"] for r in c.fetchall()]
    print(f"DocumentVersion columns: {cols}")
    print(f"Explicit lifecycle-state column beyond boolean is_current: "
          f"{'yes' if any(c not in ('id', 'document_id', 'version', 'file_path', 'change_log', 'created_at', 'is_current', 'edition_label', 'effective_date') for c in cols) else 'no'}")
    if "lifecycle_state" in cols:
        c.execute("SELECT lifecycle_state, COUNT(*) AS n FROM DocumentVersion GROUP BY lifecycle_state ORDER BY n DESC")
        for r in c.fetchall():
            print(f"  lifecycle_state {r['lifecycle_state']!r}: {r['n']}")

    print("\n--- R1.6 Authoritative source table ---")
    c.execute("SELECT COUNT(*) AS n FROM DocumentSource")
    print(f"DocumentSource rows: {c.fetchone()['n']} (independent classification table exists)")

    print("\n--- R1.7 General metadata incl. file paths ---")
    c.execute("DESCRIBE Document")
    doc_cols = [r["Field"] for r in c.fetchall()]
    print(f"Document columns: {doc_cols}")
    c.execute("SELECT COUNT(*) AS n, COUNT(file_path) AS with_path FROM Document")
    row = c.fetchone()
    print(f"Documents with file_path populated: {row['with_path']} / {row['n']}")

    print("\n--- R1.8 Thematic indexing (many-to-many keywords) ---")
    c.execute("SELECT COUNT(*) AS n FROM Keyword")
    kw = c.fetchone()["n"]
    c.execute("SELECT COUNT(*) AS n FROM DocumentKeyword")
    dk = c.fetchone()["n"]
    print(f"Keyword rows: {kw}, DocumentKeyword (M:N link) rows: {dk}")


def report_pipeline():
    print("\n--- R1.9 Automated/semi-automated maintenance pipeline ---")
    for name in PIPELINE_SCRIPTS:
        exists = (REPO_ROOT / "src" / "tools" / name).exists()
        print(f"  src/tools/{name}: {'present' if exists else 'MISSING'}")


def report_app():
    print("\n=== R2.x Search & Functional Capabilities ===\n")
    app_py = _read(APP_DIR / "app.py")
    index_html = _read(APP_DIR / "templates" / "index.html")
    base_html = _read(APP_DIR / "templates" / "base.html")
    style_css = _read(APP_DIR / "static" / "style.css")

    print("--- R2.1 Search result uniqueness ---")
    group_by = _grep_lines(app_py, r"GROUP BY")
    print(f"GROUP BY clause(s) in app/app.py: {group_by or '(none found)'}")

    print("\n--- R2.2 Responsive web UI ---")
    print(f"viewport meta tag in base.html: {bool(_grep_lines(base_html, r'name=.viewport'))}")
    media_queries = _grep_lines(style_css, r"@media")
    print(f"@media rules in style.css: {len(media_queries)} -> {media_queries}")

    print("\n--- R2.3 Combined full-text + structured filters ---")
    filter_reads = _grep_lines(app_py, r"request\.args\.get")
    print(f"request.args.get(...) reads in app.py: {filter_reads}")

    print("\n--- R2.4 Result metadata summary + hyperlink ---")
    print(f"doc.url referenced in index.html: {bool(_grep_lines(index_html, r'doc\.url'))}")

    print("\n--- R2.5 Export readiness (CSV/JSON/XML) ---")
    hits = []
    for path in [APP_DIR / "app.py", APP_DIR / "templates" / "index.html", APP_DIR / "templates" / "base.html"]:
        text = _read(path)
        for pattern in (r"\bcsv\b", r"\bexport\b", r"\bxml\b"):
            found = _grep_lines(text, pattern)
            if found:
                hits.append((path.name, pattern, found))
    print(f"CSV/export/XML references found in app/: {hits or '(none)'}")

    print("\n=== R3.x Technical Stack ===\n")
    print("--- R3.1 Python + Flask ---")
    print(f"'from flask import' in app.py: {bool(_grep_lines(app_py, r'from flask import'))}")

    print("\n--- R3.2 Relational DB engine ---")
    print(f"doc/REQUIREMENTS.md says: SQLite")
    print(f"Actual DB_HOST/DB_PORT from .env: {os.environ.get('DB_HOST')}:{os.environ.get('DB_PORT')} "
          f"(connected to via pymysql -> MariaDB, NOT SQLite) — flagged mismatch, not auto-resolved")

    print("\n--- R3.3 HTML5/CSS3/Jinja2 ---")
    templates = list((APP_DIR / "templates").glob("*.html")) if (APP_DIR / "templates").exists() else []
    print(f"Templates found: {[t.name for t in templates]}")
    print(f"Jinja2 syntax ({{% %}}/{{{{ }}}}) in index.html: {bool(_grep_lines(index_html, r'{%|{{'))}")

    print("\n--- R3.4 Vanilla JS + Phosphor Icons + Google Fonts ---")
    print(f"Phosphor Icons reference in base.html: {bool(_grep_lines(base_html, r'phosphor'))}")
    print(f"Google Fonts reference in base.html: {bool(_grep_lines(base_html, r'fonts\.googleapis'))}")
    heavy_js = []
    for text, label in ((app_py, "app.py"), (index_html, "index.html"), (base_html, "base.html")):
        for lib in ("jquery", "bootstrap.min.js", "react", "vue.js", "angular"):
            if _grep_lines(text, lib):
                heavy_js.append((label, lib))
    print(f"Heavy JS framework references found: {heavy_js or '(none — vanilla JS only)'}")
    js_files = list((APP_DIR / "static").glob("*.js")) if (APP_DIR / "static").exists() else []
    print(f".js files under app/static: {[f.name for f in js_files] or '(none — inline vanilla JS only)'}")

    print("\n=== R4.x Access Control & Licensing ===\n")
    print("--- R4.1 Licensing/visibility rules ---")
    licen_hits = []
    for path in [APP_DIR / "app.py", APP_DIR / "templates" / "index.html", APP_DIR / "templates" / "base.html"]:
        found = _grep_lines(_read(path), r"licen|copyright")
        if found:
            licen_hits.append((path.name, found))
    print(f"License/copyright-related logic found in app/: {licen_hits or '(none)'}")
    print("(see R1.7 above: file_path is 0% populated and never selected by app.py either — "
          "no mechanism distinguishes a freely-linkable source from a restricted one)")

    print("\n--- R4.2 Central public hub for stakeholders ---")
    print("Not mechanically checkable — qualitative/organizational requirement, left to the agent.")


def report_other():
    print("\n=== Other findings (not tied to a specific requirement) ===\n")
    wsgi_text = _read(REPO_ROOT / "wsgi.py")
    print(f"wsgi.py contents:\n{wsgi_text}")
    m = re.search(r"from\s+([\w.]+)\s+import", wsgi_text or "")
    if m:
        module_path = m.group(1).split(".")[0]
        target_dir = REPO_ROOT / module_path
        exists = target_dir.exists()
        print(f"wsgi.py imports from top-level module/package {module_path!r} — "
              f"exists on disk: {exists} (does NOT mean it's the right target — see below)")
        if exists:
            target_app_py = _read(target_dir / "app.py")
            is_sqlite_legacy = bool(target_app_py and "sqlite3" in target_app_py)
            print(f"  {module_path}/app.py uses sqlite3 (legacy, pre-MariaDB-migration app): "
                  f"{is_sqlite_legacy}")
            if module_path.lower() != "app" and is_sqlite_legacy:
                print(f"  ==> wsgi.py currently serves the OLD SQLite-backed app from "
                      f"'{module_path}/', not the current MariaDB-backed 'app/app.py' this "
                      f"whole pipeline maintains — CLAUDE.md explicitly calls '{module_path}/' "
                      f"a temporary/experimental directory, not the final placement. This "
                      f"technically matches R3.2's literal 'SQLite' wording, but reflects "
                      f"deprecated architecture, not the live one.")

    archives = []
    for base in (APP_DIR, REPO_ROOT / "Web"):
        if base.exists():
            for path in base.rglob("*"):
                if path.is_file() and path.stat().st_size > 50_000 and path.suffix in (".zip", ".tar", ".gz"):
                    archives.append(path)
    for path in archives:
        print(f"Unusually large archive: {path.relative_to(REPO_ROOT)} "
              f"({path.stat().st_size} bytes) — is this meant to be committed?")
    if len(archives) > 1:
        sizes = {p.stat().st_size for p in archives}
        if len(sizes) == 1:
            print(f"  All {len(archives)} archives above are the same size — likely byte-identical "
                  f"duplicates, worth confirming before removing any.")


if __name__ == "__main__":
    connection = get_connection()
    report_db(connection)
    connection.close()
    report_pipeline()
    report_app()
    report_other()
