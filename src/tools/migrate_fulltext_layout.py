"""One-off migration of the downloaded full texts from the old layout
`data/fulltext/<source spreadsheet>/<designation>__<url field>.<ext>` to the
flat layout `data/fulltext/<designation>__<8 hex digits of the hash>.<ext>`
that `fetch_fulltext.py` now writes (see its `flat_name()`).

The old paths are recorded in three places, so the move is four separate,
individually re-runnable steps, and nothing is deleted until the database no
longer points at it:

  plan      (default) print what would move; touches nothing.
  files     --apply: hard-link (or copy) each file to its new name, verify its
            SHA-256 against the manifest, rewrite `local_path` in
            `data/fulltext_manifest.json`, and write the old->new mapping to
            `data/fulltext_layout_map.json` (gitignored). The old files stay,
            so a running application keeps working.
  db        --apply: `UPDATE Document SET file_path` from that mapping in one
            transaction, then verify that no old path is left. Needs the
            database account of `--env-file` (default `.env`, the real
            database — take a backup first).
  cleanup   --apply: delete old files whose new name exists and which no
            Document references any more, then the empty source folders.

Identical contents (the same document fetched from `odkaz_hlavni` and from
`odkaz_eu`) become one file; the clean texts under `data/fulltext_clean/` are
not moved — regenerate them with `extract_fulltext.py --apply`.

Usage:
    .venv/bin/python src/tools/migrate_fulltext_layout.py plan
    .venv/bin/python src/tools/migrate_fulltext_layout.py files --apply
    .venv/bin/python src/tools/migrate_fulltext_layout.py db --apply
    .venv/bin/python src/tools/migrate_fulltext_layout.py cleanup --apply
"""
import argparse
import hashlib
import json
import os
import pathlib
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import fetch_fulltext as ff  # noqa: E402

REPO_ROOT = ff.REPO_ROOT
MANIFEST_PATH = ff.MANIFEST_PATH
MAP_PATH = REPO_ROOT / "data" / "fulltext_layout_map.json"
FLAT_DIR = "data/fulltext"


class MigrationError(Exception):
    pass


def designation_of(key):
    """The designation inside a manifest key `source|designation|url field`."""
    return key.split("|", 1)[1].rsplit("|", 1)[0]


def is_flat(local_path):
    return pathlib.PurePosixPath(local_path).parent == pathlib.PurePosixPath(FLAT_DIR)


def plan_moves(manifest):
    """[{key, old, new, sha256}] for every fetched entry not yet in the flat
    layout. Raises if two different contents would get the same new name."""
    moves, owner = [], {}
    for key, entry in sorted(manifest.items()):
        old = entry.get("local_path")
        if entry.get("status") != "fetched" or not old or is_flat(old):
            continue
        sha = entry.get("sha256")
        if not sha:
            raise MigrationError(f"{key}: the manifest has no sha256, cannot name the file")
        ext = pathlib.PurePosixPath(old).suffix.lstrip(".")
        new = f"{FLAT_DIR}/{ff.flat_name(designation_of(key), sha, ext)}"
        if owner.setdefault(new, sha) != sha:
            raise MigrationError(f"two different contents would both become {new}")
        moves.append({"key": key, "old": old, "new": new, "sha256": sha})
    return moves


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def apply_files(moves, repo_root=REPO_ROOT, log=print):
    """Creates every new file (hard link, else copy) after verifying the
    content hash of the source. Returns (created, reused)."""
    created = reused = 0
    seen = set()
    for move in moves:
        if move["new"] in seen:
            continue
        seen.add(move["new"])
        src, dst = pathlib.Path(repo_root) / move["old"], pathlib.Path(repo_root) / move["new"]
        if dst.exists():
            if file_sha256(dst) != move["sha256"]:
                raise MigrationError(f"{move['new']} exists with different content")
            reused += 1
            continue
        if not src.is_file():
            raise MigrationError(f"{move['old']} is listed in the manifest but is not on disk")
        if file_sha256(src) != move["sha256"]:
            raise MigrationError(f"{move['old']} does not match the hash in the manifest")
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.link(src, dst)
        except OSError:
            shutil.copy2(src, dst)
        created += 1
    return created, reused


def rewrite_manifest(manifest, moves):
    for move in moves:
        manifest[move["key"]]["local_path"] = move["new"]
    return manifest


def mapping_of(moves):
    return {m["old"]: m["new"] for m in moves}


def update_documents(conn, mapping, apply=False, log=print):
    """UPDATE Document.file_path old -> new in one transaction. Returns the
    number of rows changed; refuses (and rolls back) if an old path survives."""
    changed = 0
    with conn.cursor() as cur:
        for old, new in sorted(mapping.items()):
            cur.execute("SELECT COUNT(*) FROM Document WHERE file_path = %s", (old,))
            rows = cur.fetchone()
            rows = rows[0] if not isinstance(rows, dict) else next(iter(rows.values()))
            if rows and apply:
                cur.execute("UPDATE Document SET file_path = %s WHERE file_path = %s", (new, old))
            changed += rows
        if apply:
            placeholders = ",".join(["%s"] * len(mapping)) or "NULL"
            cur.execute(f"SELECT COUNT(*) FROM Document WHERE file_path IN ({placeholders})", list(mapping))
            left = cur.fetchone()
            left = left[0] if not isinstance(left, dict) else next(iter(left.values()))
            if left:
                conn.rollback()
                raise MigrationError(f"{left} documents still point at an old path; rolled back")
            conn.commit()
    return changed


def referenced_paths(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT file_path FROM Document WHERE file_path IS NOT NULL")
        return {row[0] if not isinstance(row, dict) else next(iter(row.values())) for row in cur.fetchall()}


def cleanup(mapping, referenced, repo_root=REPO_ROOT, apply=False, log=print):
    """Removes old files that are safe to remove: the new name exists and no
    Document references the old one. Returns (removed, kept) path lists."""
    root = pathlib.Path(repo_root)
    removed, kept = [], []
    for old, new in sorted(mapping.items()):
        src = root / old
        if not src.exists():
            continue
        if old in referenced or not (root / new).is_file():
            kept.append(old)
            continue
        if apply:
            src.unlink()
        removed.append(old)
    if apply:
        for folder in sorted({(root / old).parent for old in mapping}, key=lambda p: -len(p.parts)):
            if folder != root / FLAT_DIR and folder.is_dir() and not any(folder.iterdir()):
                folder.rmdir()
    return removed, kept


def load_manifest():
    return ff.load_manifest()


def save_manifest(manifest):
    ff.save_manifest(manifest)  # same format as the fetcher, so the diff is only the paths


def connect(env_file):
    import pymysql
    from dotenv import dotenv_values
    env = dotenv_values(env_file)
    return pymysql.connect(host=env["DB_HOST"], port=int(env.get("DB_PORT") or 3306), user=env["DB_USER"],
                           password=env["DB_PASSWORD"], database=env["DB_NAME"]), env["DB_NAME"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("step", nargs="?", default="plan", choices=("plan", "files", "db", "cleanup"))
    parser.add_argument("--apply", action="store_true", help="do it (every step is a dry run without this)")
    parser.add_argument("--env-file", default=None,
                        help="database account for the db and cleanup steps (default: .env, the real database, "
                             "from this tree or the main working tree)")
    args = parser.parse_args(argv)
    try:
        if args.step in ("plan", "files"):
            manifest = load_manifest()
            moves = plan_moves(manifest)
            new_files = len({m["new"] for m in moves})
            print(f"{len(moves)} manifest entries in the old layout -> {new_files} files in {FLAT_DIR}/ "
                  f"({len(moves) - new_files} duplicates of identical content merged)")
            if args.step == "files" and args.apply:
                created, reused = apply_files(moves)
                save_manifest(rewrite_manifest(manifest, moves))
                MAP_PATH.write_text(json.dumps(mapping_of(moves), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                                    encoding="utf-8")
                print(f"{created} files created, {reused} already there; manifest rewritten; "
                      f"mapping saved to {MAP_PATH.relative_to(REPO_ROOT)}")
            elif args.step == "files":
                print("(dry run — pass --apply)")
            return 0
        mapping = json.loads(MAP_PATH.read_text(encoding="utf-8"))
        import testdb
        conn, name = connect(args.env_file or str(testdb.find_env_file('.env')))
        try:
            if args.step == "db":
                changed = update_documents(conn, mapping, apply=args.apply)
                print(f"{changed} documents in database {name} "
                      f"{'updated' if args.apply else 'would be updated'}" + ("" if args.apply else " (dry run — pass --apply)"))
            else:
                removed, kept = cleanup(mapping, referenced_paths(conn), apply=args.apply)
                print(f"{len(removed)} old files {'removed' if args.apply else 'would be removed'}; "
                      f"{len(kept)} kept (still referenced by {name}, or the new file is missing)")
                if not args.apply:
                    print("(dry run — pass --apply)")
        finally:
            conn.close()
    except (MigrationError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
