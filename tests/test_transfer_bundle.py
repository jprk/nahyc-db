"""The bundle that carries the database and the state files between machines
(src/tools/transfer_bundle.py, doc/NASAZENI.md). No database: the dump and the import
are tried by hand (doc/NASAZENI.md, odstavec 4)."""
import gzip
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "tools"))

import transfer_bundle as tb  # noqa: E402


def make_bundle(directory):
    bundle = pathlib.Path(directory) / "b"
    (bundle / tb.STATE).mkdir(parents=True)
    with gzip.open(bundle / tb.DUMP, "wb") as f:
        f.write(b"-- dump\n")
    (bundle / tb.STATE / "manual_corrections.json").write_text('{"A": {}}', encoding="utf-8")
    (bundle / tb.STATE / "not_a_state_file.json").write_text("{}", encoding="utf-8")
    files = sorted(p for p in bundle.rglob("*") if p.is_file())
    meta = {"host": "test", "created": "2026-11-26T12:00:00", "git_commit": "abc", "row_counts": {"Document": 1},
            "sha256": {str(p.relative_to(bundle)): tb.sha256(p) for p in files}}
    (bundle / tb.META).write_text(json.dumps(meta), encoding="utf-8")
    return bundle


class BundleTestCase(unittest.TestCase):
    def test_verify_finds_a_changed_or_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = make_bundle(tmp)
            self.assertEqual(tb.verify(bundle), [])
            (bundle / tb.STATE / "manual_corrections.json").write_text("{}", encoding="utf-8")
            (bundle / tb.DUMP).unlink()
            # the dump is missing both as a listed file and as the dump itself
            self.assertEqual(sorted(tb.verify(bundle)), ["checksum differs: state/manual_corrections.json",
                                                         "missing: db.sql.gz", "missing: db.sql.gz"])

    def test_install_state_keeps_what_it_replaces_and_skips_other_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = make_bundle(tmp)
            state, keep = pathlib.Path(tmp) / "state", pathlib.Path(tmp) / "keep"
            state.mkdir()
            (state / "manual_corrections.json").write_text('{"old": {}}', encoding="utf-8")
            self.assertEqual(tb.install_state(bundle, state, keep), ["manual_corrections.json"])
            self.assertEqual((state / "manual_corrections.json").read_text(encoding="utf-8"), '{"A": {}}')
            self.assertEqual((keep / "manual_corrections.json").read_text(encoding="utf-8"), '{"old": {}}')
            self.assertFalse((state / "not_a_state_file.json").exists())


if __name__ == "__main__":
    unittest.main()
