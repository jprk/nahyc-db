"""Deletes the files in data/fulltext/ and data/fulltext_clean/ that no manifest
entry points at any more (typically the old copies after a document was fetched
again, e.g. in another language). Dry run unless --apply."""
import argparse
import pathlib

import fetch_fulltext as ff

FULLTEXT_DIR = ff.REPO_ROOT / "data" / "fulltext"
CLEAN_DIR = ff.REPO_ROOT / "data" / "fulltext_clean"


def referenced_names(manifest):
    return {pathlib.Path(e["local_path"]).name for e in manifest.values()
            if e.get("status") == "fetched" and e.get("local_path")}


def orphans(manifest, fulltext_dir=FULLTEXT_DIR, clean_dir=CLEAN_DIR):
    """Files of `fulltext_dir` not named by the manifest, and clean texts whose
    original (same stem) is not either."""
    names = referenced_names(manifest)
    stems = {pathlib.Path(n).stem for n in names}
    found = [p for p in sorted(pathlib.Path(fulltext_dir).glob("*")) if p.is_file() and p.name not in names]
    found += [p for p in sorted(pathlib.Path(clean_dir).glob("*")) if p.is_file() and p.stem not in stems]
    return found


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--apply", action="store_true", help="delete (dry run without it)")
    args = parser.parse_args(argv)
    found = orphans(ff.load_manifest())
    for path in found:
        print(path.relative_to(ff.REPO_ROOT))
        if args.apply:
            path.unlink()
    print(f"{len(found)} files " + ("deleted" if args.apply else "would be deleted (dry run — add --apply)"))


if __name__ == "__main__":
    main()
