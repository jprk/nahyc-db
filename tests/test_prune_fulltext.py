import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))
import prune_fulltext as pf


class OrphansTestCase(unittest.TestCase):
    def test_only_files_without_a_manifest_entry_are_orphans(self):
        with tempfile.TemporaryDirectory() as tmp:
            full, clean = pathlib.Path(tmp, "full"), pathlib.Path(tmp, "clean")
            full.mkdir(), clean.mkdir()
            for name in ("a__1.html", "a__2.html", "b__3.pdf"):
                (full / name).write_text("x")
            for name in ("a__1.html", "a__2.html", "b__3.html"):
                (clean / name).write_text("x")
            manifest = {"k": {"status": "fetched", "local_path": "data/fulltext/a__2.html"},
                        "l": {"status": "fetched", "local_path": "data/fulltext/b__3.pdf"},
                        "m": {"status": "failed", "local_path": "data/fulltext/a__1.html"}}
            found = sorted(p.parent.name + "/" + p.name for p in pf.orphans(manifest, full, clean))
            self.assertEqual(found, ["clean/a__1.html", "full/a__1.html"])


if __name__ == "__main__":
    unittest.main()
