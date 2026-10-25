"""Shared plumbing for the test runner (`run_tests.py`) and the test-database
refresh (`refresh_test_db.py`): reading the env files, the server-wide
test-suite lock, the safety guards, and copying the main database into the
test database.

Why it exists: tests that touch a database must never share it with another
run, and must never touch the real one. The real database (`.env`,
`h2regdocs`) is only ever READ here (a dump); everything is written to the
database named by `.env.test` (`h2regdocs_test`), whose account has rights
on that one database only and so needs no admin credentials.

The lock is a MariaDB `GET_LOCK`, not a lock file: it lives on the server,
so it is shared by every worktree on the machine, and it is released by the
server itself if the process holding it dies. It is advisory — it protects
runs that take it, which is why `refresh_test_db()` refuses to write
without it.
"""
import os
import pathlib
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

import pymysql
from dotenv import dotenv_values

BASE_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent

LOCK_NAME = "h2db-test-suite"

# Holds editor accounts (password hashes of real people) and the review
# audit trail: the test database gets their structure only, never the rows.
EDITOR_TABLES = ("User", "ReviewItem", "AuditLog")

_REQUIRED_KEYS = ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD")


class TestDbError(Exception):
    __test__ = False  # not a test case, despite the name


class LockHeld(TestDbError):
    """Another run already holds the test-suite lock."""


def main_worktree_root(repo_root=REPO_ROOT):
    """Root of the main working tree. Gitignored, machine-local files
    (`.env`, `.env.test`, `data/fulltext/`) live only there, not in the
    other worktrees."""
    result = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
                            cwd=repo_root, capture_output=True, text=True)
    if result.returncode != 0:
        return pathlib.Path(repo_root)
    return pathlib.Path(result.stdout.strip()).parent


def find_env_file(name, repo_root=REPO_ROOT):
    """`name` in this worktree, else in the main working tree."""
    for root in (pathlib.Path(repo_root), main_worktree_root(repo_root)):
        candidate = root / name
        if candidate.is_file():
            return candidate
    raise TestDbError(f"{name} not found in {repo_root} or in the main working tree")


def read_env(path):
    values = dict(dotenv_values(path))
    missing = [k for k in _REQUIRED_KEYS if not values.get(k)]
    if missing:
        raise TestDbError(f"{path}: missing {', '.join(missing)}")
    values["DB_PORT"] = str(values.get("DB_PORT") or 3306)
    return values


def connect(env, **kwargs):
    return pymysql.connect(host=env["DB_HOST"], port=int(env["DB_PORT"]), user=env["DB_USER"],
                           password=env["DB_PASSWORD"], database=env["DB_NAME"], **kwargs)


def assert_safe_target(source_env, target_env):
    """The target must be a disposable `*_test` database and not the source."""
    if not target_env["DB_NAME"].endswith("_test"):
        raise TestDbError(f"refusing to write to {target_env['DB_NAME']!r}: "
                          "the test database name must end with '_test'")
    identity = lambda e: (e["DB_HOST"], e["DB_PORT"], e["DB_NAME"])  # noqa: E731
    if identity(source_env) == identity(target_env):
        raise TestDbError("source and target are the same database")


class TestDbLock:
    """Holds the server-wide test-suite lock on a connection of its own for
    as long as the `with` block runs. `wait` is the number of seconds to
    wait for a lock another run is holding (0 = fail at once)."""
    __test__ = False

    def __init__(self, env, name=LOCK_NAME, wait=0):
        self.env, self.name, self.wait = env, name, wait
        self.conn = None

    def __enter__(self):
        self.conn = connect(self.env, autocommit=True)
        with self.conn.cursor() as cur:
            cur.execute("SELECT GET_LOCK(%s, %s)", (self.name, self.wait))
            if cur.fetchone()[0] != 1:
                cur.execute("SELECT IS_USED_LOCK(%s)", (self.name,))
                holder = cur.fetchone()[0]
                self.conn.close()
                self.conn = None
                raise LockHeld(f"another test run holds lock {self.name!r}"
                               + (f" (MariaDB connection {holder})" if holder else ""))
        return self

    def holds(self):
        if self.conn is None:
            return False
        with self.conn.cursor() as cur:
            cur.execute("SELECT IS_USED_LOCK(%s) = CONNECTION_ID()", (self.name,))
            return cur.fetchone()[0] == 1

    def __exit__(self, *exc):
        if self.conn is not None:
            try:
                with self.conn.cursor() as cur:
                    cur.execute("SELECT RELEASE_LOCK(%s)", (self.name,))
            finally:
                self.conn.close()
                self.conn = None
        return False


def _client(*names):
    for name in names:
        path = shutil.which(name)
        if path:
            return path
    raise TestDbError(f"none of {', '.join(names)} found on PATH")


def _cli_args(env):
    return ["-h", env["DB_HOST"], "-P", env["DB_PORT"], "-u", env["DB_USER"]]


def _run(command, env, input_bytes=None):
    # The password travels in MYSQL_PWD, never as an argument visible to `ps`.
    result = subprocess.run(command, input=input_bytes, capture_output=True,
                            env=dict(os.environ, MYSQL_PWD=env["DB_PASSWORD"]))
    if result.returncode != 0:
        raise TestDbError(f"{pathlib.Path(command[0]).name} failed: "
                          f"{result.stderr.decode('utf-8', 'replace').strip()[:500]}")
    return result.stdout


def list_tables(env):
    with connect(env) as conn, conn.cursor() as cur:
        cur.execute("SHOW TABLES")
        return [row[0] for row in cur.fetchall()]


def dump_commands(source_env, tables):
    """The two dump invocations: every table's rows and structure except the
    editor tables, then the editor tables' structure alone."""
    exe = _client("mariadb-dump", "mysqldump")
    db = source_env["DB_NAME"]
    editors = [t for t in EDITOR_TABLES if t in tables]
    data = [exe, *_cli_args(source_env), "--single-transaction", "--skip-comments",
            *[f"--ignore-table={db}.{t}" for t in editors], db]
    structure = ([exe, *_cli_args(source_env), "--no-data", "--skip-comments", db, *editors]
                 if editors else None)
    return data, structure


def drop_all_tables(env):
    with connect(env, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute("SHOW TABLES")
        names = [row[0] for row in cur.fetchall()]
        cur.execute("SET FOREIGN_KEY_CHECKS=0")
        for name in names:
            cur.execute(f"DROP TABLE IF EXISTS `{name}`")
        cur.execute("SET FOREIGN_KEY_CHECKS=1")
    return len(names)


def _row_counts(env, tables):
    with connect(env) as conn, conn.cursor() as cur:
        counts = {}
        for name in tables:
            cur.execute(f"SELECT COUNT(*) FROM `{name}`")
            counts[name] = cur.fetchone()[0]
        return counts


def refresh_test_db(source_env, target_env, lock, log=print):
    """Replaces the contents of the test database with a copy of the source
    database (editor tables: structure only), then checks the row counts.
    Requires the test-suite lock, held on `lock`."""
    assert_safe_target(source_env, target_env)
    if lock is None or not lock.holds():
        raise TestDbError("refusing to refresh the test database without holding the "
                          f"{LOCK_NAME!r} lock")
    tables = list_tables(source_env)
    data_cmd, structure_cmd = dump_commands(source_env, tables)
    dump = _run(data_cmd, source_env)
    if structure_cmd:
        dump += _run(structure_cmd, source_env)
    dropped = drop_all_tables(target_env)
    _run([_client("mariadb", "mysql"), *_cli_args(target_env), target_env["DB_NAME"]],
         target_env, b"SET FOREIGN_KEY_CHECKS=0;\n" + dump)

    with connect(target_env, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute("CREATE TABLE _copy_meta (source_db VARCHAR(100) NOT NULL, "
                    "copied_at DATETIME NOT NULL)")
        cur.execute("INSERT INTO _copy_meta VALUES (%s, NOW())", (source_env["DB_NAME"],))

    copied = [t for t in tables if t not in EDITOR_TABLES]
    source_counts = _row_counts(source_env, copied)
    target_counts = _row_counts(target_env, [t for t in tables])
    wrong = {t: (source_counts[t], target_counts.get(t)) for t in copied
             if source_counts[t] != target_counts.get(t)}
    leaked = {t: n for t, n in target_counts.items() if t in EDITOR_TABLES and n}
    if wrong or leaked:
        raise TestDbError(f"copy verification failed: row counts {wrong}, editor rows {leaked}")
    log(f"test database refreshed from {source_env['DB_NAME']}: {len(tables)} tables "
        f"({dropped} dropped first), {sum(source_counts.values())} rows")
    return {"tables": len(tables), "rows": sum(source_counts.values())}


def ensure_fulltext_dir(repo_root=REPO_ROOT, main_root=None, log=print):
    """`data/fulltext/` (the downloaded originals) exists only in the main
    working tree; give a worktree a symlink to it. An EMPTY directory left
    behind by an earlier run is replaced. Returns True if the directory is
    usable afterwards."""
    repo_root = pathlib.Path(repo_root)
    target = repo_root / "data" / "fulltext"
    if target.is_symlink() or (target.is_dir() and any(target.iterdir())):
        return target.exists()
    main_root = pathlib.Path(main_root) if main_root else main_worktree_root(repo_root)
    source = main_root / "data" / "fulltext"
    if source.resolve() == target.resolve() or not (source.is_dir() and any(source.iterdir())):
        log(f"warning: no downloaded full texts at {source}; full-text tests will fail")
        return False
    if target.is_dir():
        target.rmdir()
    target.symlink_to(source, target_is_directory=True)
    log(f"linked {target} -> {source}")
    return True


def ensure_local_files(repo_root=REPO_ROOT, main_root=None, names=(".openapi_key",), log=print):
    """Gitignored, machine-local files that some modules read when they are
    imported (`deduplicate_db.py` reads `.openapi_key`) exist only in the main
    working tree; give a worktree a symlink, so the unit tests can import them.
    Returns the names that are still missing."""
    repo_root = pathlib.Path(repo_root)
    main_root = pathlib.Path(main_root) if main_root else main_worktree_root(repo_root)
    missing = []
    for name in names:
        target, source = repo_root / name, main_root / name
        if target.exists() or target.is_symlink():
            continue
        if source.is_file() and source.resolve() != target.resolve():
            target.symlink_to(source)
            log(f"linked {target} -> {source}")
        else:
            missing.append(name)
    return missing


def port_is_free(port, host="127.0.0.1"):
    try:
        with socket.create_connection((host, port), timeout=1):
            return False
    except OSError:
        return True


class DebugServer:
    """The Flask development server (no WSGI), run from this worktree as a
    child process with the given environment, and stopped by its own PID
    when the block ends."""

    def __init__(self, env, port=5001, repo_root=REPO_ROOT, startup_timeout=30):
        self.env, self.port = env, port
        self.repo_root = pathlib.Path(repo_root)
        self.startup_timeout = startup_timeout
        self.proc = None
        self.url = f"http://127.0.0.1:{port}"

    def __enter__(self):
        if not port_is_free(self.port):
            raise TestDbError(f"port {self.port} is already in use")
        log_dir = self.repo_root / "log"
        log_dir.mkdir(exist_ok=True)
        code = (f"import sys; sys.path.insert(0, {str(self.repo_root)!r}); "
                "from app.app import app; "
                f"app.run(host='127.0.0.1', port={self.port}, debug=False, threaded=True)")
        self.log = open(log_dir / "test_server.log", "wb")
        self.proc = subprocess.Popen([sys.executable, "-c", code], cwd=self.repo_root,
                                     env=self.env, stdout=self.log, stderr=subprocess.STDOUT)
        deadline = time.monotonic() + self.startup_timeout
        while time.monotonic() < deadline:
            if self.proc.poll() is not None:
                self._cleanup()
                raise TestDbError("the debug server exited during startup "
                                  f"(see {log_dir / 'test_server.log'})")
            try:
                urllib.request.urlopen(self.url + "/", timeout=2).close()
                return self
            except urllib.error.HTTPError:
                return self
            except OSError:
                time.sleep(0.3)
        self._cleanup()
        raise TestDbError(f"the debug server did not answer within {self.startup_timeout}s")

    def _cleanup(self):
        if self.proc is not None and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()
        self.proc = None
        self.log.close()

    def __exit__(self, *exc):
        self._cleanup()
        return False
