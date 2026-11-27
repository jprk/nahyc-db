"""Where the files that change while the database runs live (doc/NASAZENI.md).

Most files under data/ are inputs of the rebuild: the developers change them and git
keeps them. Some change in operation — the editors' web application writes the
corrections, accepted candidates and relations they confirm; the scheduler writes
the caches of the validity checks and the harvest; the full-text fetch writes its
manifest. On a production machine these must not live in the git working tree,
where a `git pull` would collide with them (decided 2026-11-26).

`H2DB_STATE_DIR` (in the environment or in the `.env` of the working tree) names the
directory of these files. Without it they stay in data/ as before — the development
machine and the tests do not set it. An empty value also means data/: run_tests.py
sets it so that tests never touch a production state directory.

    import state_paths
    CORRECTIONS_PATH = state_paths.data_file("manual_corrections.json")
"""
import os
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
DATA_DIR = REPO_ROOT / "data"
ENV_VAR = "H2DB_STATE_DIR"

# the files that change in operation (who writes them)
STATE_FILES = frozenset({
    "manual_corrections.json",          # editors (app/admin.py), corrections of the record checks
    "accepted_candidates.json",         # editors (app/candidates_admin.py)
    "document_relations_editor.json",   # editors (app/candidates_admin.py)
    "validity_cache.json",              # editors, check_validity.py, harvest
    "norm_validity_cache.json",         # harvest of the standards catalogues
    "harvest_not_imported.json",        # harvest
    "source_checks.jsonl",              # harvest: the log of every check of a source
    "document_relations_validity.json",  # backfill_document_states.py
    "eu_consolidation_cache.json",      # refresh_eu_consolidations.py
    "fulltext_manifest.json",           # fetch_fulltext.py, refresh_eu_consolidations.py
    "triage_model_cache.json",          # triage of the candidate queue
    "eurovoc_cache.json",               # keywords of new documents (doc/KLICOVA_SLOVA.md)
    "ics_cache.json",
    "keyword_model_cache.json",
    "official_titles_cache.json",       # record checks (doc/KONTROLA_ZAZNAMU.md)
    "record_check_model_cache.json",
    "record_checks.json",
    "record_checks_model.json",
    "act_descriptions.json",            # descriptions of the legal acts (issue #37, doc/ANOTACE_PREDPISU.md)
})


def _configured():
    if ENV_VAR in os.environ:
        return os.environ[ENV_VAR]
    env_file = REPO_ROOT / ".env"
    if env_file.is_file():
        from dotenv import dotenv_values
        return dotenv_values(env_file).get(ENV_VAR) or ""
    return ""


def state_dir():
    """The directory of the files that change in operation."""
    value = _configured().strip()
    return pathlib.Path(value).expanduser() if value else DATA_DIR


def data_file(name):
    """The path of the file `name` of data/: in the state directory for a state file."""
    return (state_dir() if name in STATE_FILES else DATA_DIR) / name


def seed(target=None, overwrite=False):
    """Copies the state files of data/ into the state directory (the first deployment);
    returns the names copied. An existing file is kept unless `overwrite`."""
    import shutil
    target = pathlib.Path(target) if target else state_dir()
    target.mkdir(parents=True, exist_ok=True)
    copied = []
    for name in sorted(STATE_FILES):
        source, destination = DATA_DIR / name, target / name
        if source.is_file() and source.resolve() != destination.resolve() and (overwrite or not destination.exists()):
            shutil.copy2(source, destination)
            copied.append(name)
    return copied


def main(argv=None):
    """`state_paths.py --seed`: copies into the state directory the state files it does
    not have yet — after a `git pull` that added a file to STATE_FILES (act_descriptions.json
    came with PR #40, after the state directories were set up). Never overwrites."""
    import argparse
    parser = argparse.ArgumentParser(description=main.__doc__.split("\n")[0])
    parser.add_argument("--seed", action="store_true", help="copy the missing state files from data/")
    args = parser.parse_args(argv)
    print(f"state directory: {state_dir()}")
    if args.seed:
        copied = seed()
        print("copied: " + (", ".join(copied) if copied else "nothing (all present)"))
    else:
        missing = [name for name in sorted(STATE_FILES) if (DATA_DIR / name).is_file() and not (state_dir() / name).exists()]
        print("missing: " + (", ".join(missing) if missing else "none") + ("; add --seed to copy them" if missing else ""))


if __name__ == "__main__":
    main()
