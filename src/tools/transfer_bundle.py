"""A bundle that carries the database and the files that change in operation from one
machine to another (doc/NASAZENI.md).

Two uses, the same bundle:
- the first deployment: the development machine (nahyc.fd.cvut.cz) exports, the
  production machine (nahyc.fel.zcu.cz) pulls the bundle over SSH and installs it;
- the copy for the test web: production exports, pushes the bundle to the development
  machine, which installs it into its database (the test web then shows a copy of
  production).

A bundle is a directory:

    db.sql.gz        mariadb-dump --single-transaction --routines of the database of .env
    state/           the files that change in operation (state_paths.STATE_FILES)
    meta.json        when, from where, the git commit, the row count of every table,
                     the SHA-256 of every file of the bundle

The full texts (data/fulltext/, about 450 MB) do not go into the bundle: rsync copies
them, and only what changed (deploy/production/*.sh).

    .venv/bin/python src/tools/transfer_bundle.py export --dir ~/h2db-export
    .venv/bin/python src/tools/transfer_bundle.py verify --dir ~/h2db-export/20261126_120000
    .venv/bin/python src/tools/transfer_bundle.py install --dir <bundle> [--replace-db] [--env-file .env]

`install` refuses a database with tables unless `--replace-db`, and then backs it up
first (backup_db.py). It checks the row counts after the import and copies the state
files into the state directory (H2DB_STATE_DIR, state_paths.py), keeping a copy of
the files it replaces.
"""
import argparse
import datetime
import gzip
import hashlib
import json
import os
import pathlib
import shutil
import socket
import subprocess
import sys

import backup_db
import state_paths
import testdb

META = "meta.json"
DUMP = "db.sql.gz"
STATE = "state"


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit(root=state_paths.REPO_ROOT):
    result = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True)
    return result.stdout.strip() or None


def row_counts(env):
    with testdb.connect(env) as conn, conn.cursor() as cur:
        cur.execute("SHOW FULL TABLES WHERE Table_type = 'BASE TABLE'")
        tables = [row[0] for row in cur.fetchall()]
        counts = {}
        for table in tables:
            cur.execute(f"SELECT COUNT(*) FROM `{table}`")
            counts[table] = cur.fetchone()[0]
        return counts


def dump(env, path):
    """Writes a gzipped dump of the database of `env` to `path`."""
    partial = path.with_name(path.name + ".part")
    with gzip.open(partial, "wb") as out:
        process = subprocess.Popen(backup_db.dump_command(env) + ["--default-character-set=utf8mb4"],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   env=dict(os.environ, MYSQL_PWD=env["DB_PASSWORD"]))
        for chunk in iter(lambda: process.stdout.read(1 << 20), b""):
            out.write(chunk)
        error = process.stderr.read().decode("utf-8", "replace").strip()
        if process.wait() != 0:
            partial.unlink(missing_ok=True)
            raise RuntimeError(f"dump failed: {error[:500]}")
    partial.rename(path)


def export(env, target, state_dir=None):
    """Creates a bundle in the new directory `target`; returns its meta."""
    target = pathlib.Path(target)
    target.mkdir(parents=True)
    counts = row_counts(env)
    dump(env, target / DUMP)
    source = pathlib.Path(state_dir) if state_dir else state_paths.state_dir()
    (target / STATE).mkdir()
    for name in sorted(state_paths.STATE_FILES):
        if (source / name).is_file():
            shutil.copy2(source / name, target / STATE / name)
    files = sorted(p for p in target.rglob("*") if p.is_file())
    meta = {"created": datetime.datetime.now().isoformat(timespec="seconds"), "host": socket.getfqdn(),
            "database": env["DB_NAME"], "git_commit": git_commit(), "row_counts": counts,
            "sha256": {str(p.relative_to(target)): sha256(p) for p in files}}
    (target / META).write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return meta


def verify(bundle):
    """[problems] of a bundle: missing or changed files."""
    bundle = pathlib.Path(bundle)
    meta = json.loads((bundle / META).read_text(encoding="utf-8"))
    problems = []
    for name, digest in meta["sha256"].items():
        path = bundle / name
        if not path.is_file():
            problems.append(f"missing: {name}")
        elif sha256(path) != digest:
            problems.append(f"checksum differs: {name}")
    if not (bundle / DUMP).is_file():
        problems.append(f"missing: {DUMP}")
    return problems


def load_dump(env, path):
    with gzip.open(path, "rb") as f:
        data = f.read()
    result = subprocess.run([testdb._client("mariadb", "mysql"), *testdb._cli_args(env), "--default-character-set=utf8mb4",
                             env["DB_NAME"]], input=data, capture_output=True,
                            env=dict(os.environ, MYSQL_PWD=env["DB_PASSWORD"]))
    if result.returncode != 0:
        raise RuntimeError("import failed: " + result.stderr.decode("utf-8", "replace").strip()[:500])


def install_state(bundle, state_dir=None, keep=None):
    """Copies the state files of the bundle into the state directory; a replaced file is
    kept in `keep` (a directory). Returns the names installed."""
    source = pathlib.Path(bundle) / STATE
    target = pathlib.Path(state_dir) if state_dir else state_paths.state_dir()
    target.mkdir(parents=True, exist_ok=True)
    installed = []
    for path in sorted(source.glob("*")):
        if path.name not in state_paths.STATE_FILES:
            continue
        destination = target / path.name
        if destination.exists() and keep is not None:
            pathlib.Path(keep).mkdir(parents=True, exist_ok=True)
            shutil.copy2(destination, pathlib.Path(keep) / path.name)
        shutil.copy2(path, destination)
        installed.append(path.name)
    return installed


def install(env, bundle, replace_db=False, state_dir=None, log=print):
    bundle = pathlib.Path(bundle)
    problems = verify(bundle)
    if problems:
        raise RuntimeError("the bundle is damaged: " + "; ".join(problems))
    meta = json.loads((bundle / META).read_text(encoding="utf-8"))
    existing = row_counts(env)
    if existing and not replace_db:
        raise RuntimeError(f"database {env['DB_NAME']} has {len(existing)} tables; add --replace-db to replace it "
                           "(it is backed up first)")
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    if existing:
        backups = testdb.main_worktree_root() / "backups"
        backups.mkdir(exist_ok=True)
        path = backup_db.backup_path(backups, env["DB_NAME"], "before_bundle_install")
        dump(env, path)
        log(f"backup of {env['DB_NAME']}: {path}")
        testdb.drop_all_tables(env)
    load_dump(env, bundle / DUMP)
    after = row_counts(env)
    differences = {t: (n, after.get(t)) for t, n in meta["row_counts"].items() if after.get(t) != n}
    if differences:
        raise RuntimeError(f"row counts differ after the import: {differences}")
    keep = state_paths.REPO_ROOT / "backups" / f"state_before_bundle_{stamp}"
    installed = install_state(bundle, state_dir, keep=keep)
    log(f"{env['DB_NAME']}: {len(after)} tables, {after.get('Document')} documents, {after.get('User')} accounts "
        f"from {meta['host']} ({meta['created']}, commit {str(meta.get('git_commit'))[:7]}); "
        f"{len(installed)} state files into {state_dir or state_paths.state_dir()}")
    return meta


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p_export = sub.add_parser("export", help="create a bundle")
    p_export.add_argument("--dir", required=True, help="parent directory; the bundle is <dir>/<timestamp>")
    p_verify = sub.add_parser("verify", help="check the checksums of a bundle")
    p_verify.add_argument("--dir", required=True)
    p_install = sub.add_parser("install", help="load a bundle into the database of .env")
    p_install.add_argument("--dir", required=True)
    p_install.add_argument("--replace-db", action="store_true")
    for p in (p_export, p_install):
        p.add_argument("--env-file", default=None)
        p.add_argument("--state-dir", default=None, help="instead of H2DB_STATE_DIR")
    args = parser.parse_args(argv)
    if args.command == "verify":
        problems = verify(args.dir)
        print("\n".join(problems) or "bundle OK")
        return 1 if problems else 0
    env = testdb.read_env(args.env_file or testdb.find_env_file(".env"))
    env.setdefault("DB_PORT", "3306")
    if args.command == "export":
        target = pathlib.Path(args.dir).expanduser() / datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        meta = export(env, target, args.state_dir)
        latest = target.parent / "latest"
        if latest.is_symlink() or not latest.exists():
            latest.unlink(missing_ok=True)
            latest.symlink_to(target.name)
        print(f"{target}: {meta['row_counts'].get('Document')} documents, {len(meta['sha256'])} files, "
              f"commit {str(meta['git_commit'])[:7]}")
        return 0
    try:
        install(env, pathlib.Path(args.dir).expanduser(), args.replace_db, args.state_dir)
    except RuntimeError as error:
        print(f"install refused: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
