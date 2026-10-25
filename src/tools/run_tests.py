"""One command for a full test session against the TEST database.

Order of a session (see CLAUDE.md, "Jak se testuje aplikace"):
  1. take the server-wide test-suite lock (a second session fails at once, or
     waits with --wait N) — skipped for --unit alone, which touches no database;
  2. refresh the test database (`.env.test`) from the main one (`.env`) —
     `refresh_test_db.py`; the main database is only read;
  3. unit tests (no database), then the database-backed tests
     (`INTEGRATION_MODULES`) — both with the environment of `.env.test`, so
     nothing in the session can read or write the real database;
  4. the Flask debug server (no WSGI, default port 5001) started from this
     worktree on the same test database, a smoke check of its main pages, and
     the browser tests in `tests/e2e/` (Playwright), if there are any;
  5. stop the server, release the lock, print a summary.

Run it with the main working tree's interpreter (worktrees have no `.venv`):
    /home/laborator/DEVEL/nahyc-h2db/.venv/bin/python src/tools/run_tests.py
    ... --unit            # unit tests only, no database, no lock
    ... --integration     # database-backed tests only
    ... --e2e             # server + smoke + browser tests only
    ... --no-refresh      # keep the test database as it is
    ... --wait 300        # wait up to 5 minutes for another session's lock
The exit status is non-zero when anything failed.
"""
import argparse
import datetime
import pathlib
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import testdb  # noqa: E402

REPO_ROOT = testdb.REPO_ROOT
TESTS_DIR = REPO_ROOT / "tests"
E2E_DIR = TESTS_DIR / "e2e"

# Test modules that need a live database; every other tests/test_*.py is a unit test.
INTEGRATION_MODULES = ("test_admin", "test_search")

SMOKE_PAGES = ("/", "/procesy", "/export/csv", "/admin/login")


def split_modules(tests_dir=TESTS_DIR):
    names = sorted(p.stem for p in pathlib.Path(tests_dir).glob("test_*.py"))
    integration = [n for n in names if n in INTEGRATION_MODULES]
    unit = [n for n in names if n not in INTEGRATION_MODULES]
    return unit, integration


def session_env(target_env):
    """The process environment for every test child: the test database's
    settings win over anything the application would read from `.env`."""
    import os
    return {**os.environ, **{k: str(v) for k, v in target_env.items() if v is not None}}


SHOT_ROOT = REPO_ROOT / "data" / "test_screenshots"
KEEP_SHOT_SESSIONS = 5


def new_screenshot_dir(root=SHOT_ROOT, keep=KEEP_SHOT_SESSIONS):
    """A fresh folder for this session's screenshots; only the newest `keep`
    sessions are kept (the folder is gitignored and the pictures are big)."""
    root = pathlib.Path(root)
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = root / stamp
    folder.mkdir(exist_ok=True)
    sessions = sorted(p for p in root.iterdir() if p.is_dir() and p.name[:8].isdigit())
    for old in sessions[:-keep]:
        shutil.rmtree(old, ignore_errors=True)
    return folder


def extract_clean_texts(env):
    """Regenerates data/fulltext_clean/ from the downloaded originals, so the
    browser scenarios never read texts left by an older extractor. Only where
    the extractor exists and the originals are on this machine."""
    script = REPO_ROOT / "src" / "tools" / "extract_fulltext.py"
    fulltext = REPO_ROOT / "data" / "fulltext"
    if not script.is_file() or not fulltext.is_dir():
        return
    result = subprocess.run([sys.executable, str(script), "--apply"], cwd=REPO_ROOT, env=env,
                            capture_output=True, text=True)
    summary = [line.strip() for line in result.stdout.splitlines() if "extracted" in line]
    print("clean texts:", "; ".join(summary) if summary else f"extraction exited with {result.returncode}")


def run_unittest(args, env):
    return subprocess.run([sys.executable, "-m", "unittest", *args], cwd=REPO_ROOT, env=env).returncode


def smoke(base_url, pages=SMOKE_PAGES):
    failures = []
    for page in pages:
        try:
            status = urllib.request.urlopen(base_url + page, timeout=30).status
        except urllib.error.HTTPError as e:
            status = e.code
        except OSError as e:
            status = repr(e)
        if status != 200:
            failures.append(f"{page} -> {status}")
    return failures


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--unit", action="store_true", help="unit tests only")
    parser.add_argument("--integration", action="store_true", help="database-backed tests only")
    parser.add_argument("--e2e", action="store_true", help="debug server, smoke check and browser tests only")
    parser.add_argument("--no-refresh", action="store_true", help="do not copy the main database into the test database")
    parser.add_argument("--wait", type=int, default=0, help="seconds to wait for another session's lock")
    parser.add_argument("--port", type=int, default=5001, help="port of the debug server (default 5001)")
    parser.add_argument("--source-env", default=".env", help="main database (read only)")
    parser.add_argument("--target-env", default=".env.test", help="test database (overwritten)")
    args = parser.parse_args(argv)

    chosen = [args.unit, args.integration, args.e2e]
    run_unit, run_integration, run_e2e = chosen if any(chosen) else (True, True, True)
    needs_database = run_integration or run_e2e

    results = []
    try:
        source = testdb.read_env(testdb.find_env_file(args.source_env))
        target = testdb.read_env(testdb.find_env_file(args.target_env))
        testdb.assert_safe_target(source, target)
        env = session_env(target)
        unit_modules, integration_modules = split_modules()
        for name in testdb.ensure_local_files():
            print(f"warning: {name} not found in the main working tree either")

        lock = testdb.TestDbLock(target, wait=args.wait) if needs_database else None
        try:
            if lock:
                lock.__enter__()
                if not args.no_refresh:
                    testdb.refresh_test_db(source, target, lock)
            if run_integration or run_e2e:
                testdb.ensure_fulltext_dir()

            if run_unit:
                results.append(("unit", run_unittest([f"tests.{m}" for m in unit_modules], env) == 0))
            if run_integration:
                results.append(("integration", run_unittest([f"tests.{m}" for m in integration_modules], env) == 0))
            if run_e2e:
                extract_clean_texts(env)
                with testdb.DebugServer(env, port=args.port) as server:
                    failures = smoke(server.url)
                    for failure in failures:
                        print(f"smoke check failed: {failure}")
                    results.append(("smoke", not failures))
                    if any(E2E_DIR.glob("test_*.py")):
                        shots = new_screenshot_dir()
                        e2e_env = {**env, "H2DB_BASE_URL": server.url, "H2DB_SHOT_DIR": str(shots)}
                        print(f"screenshots: {shots}")
                        results.append(("e2e", run_unittest(["discover", "-s", str(E2E_DIR), "-p", "test_*.py"], e2e_env) == 0))
        finally:
            if lock:
                lock.__exit__(None, None, None)
    except testdb.TestDbError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    print("\nsummary:")
    for name, ok in results:
        print(f"  {'ok  ' if ok else 'FAIL'} {name}")
    return 0 if results and all(ok for _, ok in results) else 1


if __name__ == "__main__":
    sys.exit(main())
