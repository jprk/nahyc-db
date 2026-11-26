"""The directory of the files that change in operation (src/tools/state_paths.py, doc/NASAZENI.md)."""
import os
import pathlib
import re
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "tools"))

import state_paths  # noqa: E402


class StatePathsTestCase(unittest.TestCase):
    def test_without_the_variable_the_files_stay_in_data(self):
        with mock.patch.dict(os.environ, {"H2DB_STATE_DIR": ""}):
            self.assertEqual(state_paths.data_file("manual_corrections.json"),
                             ROOT / "data" / "manual_corrections.json")

    def test_a_state_file_moves_and_an_input_stays(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"H2DB_STATE_DIR": tmp}):
            self.assertEqual(state_paths.data_file("accepted_candidates.json"), pathlib.Path(tmp) / "accepted_candidates.json")
            self.assertEqual(state_paths.data_file("triage_rules.json"), ROOT / "data" / "triage_rules.json")

    def test_seed_copies_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            copied = state_paths.seed(tmp)
            self.assertIn("manual_corrections.json", copied)
            (pathlib.Path(tmp) / "manual_corrections.json").write_text("{}", encoding="utf-8")
            self.assertNotIn("manual_corrections.json", state_paths.seed(tmp))
            self.assertEqual((pathlib.Path(tmp) / "manual_corrections.json").read_text(encoding="utf-8"), "{}")

    def test_no_state_file_is_addressed_in_data_directly(self):
        """Every path of a state file goes through state_paths.data_file()."""
        names = "|".join(re.escape(n) for n in state_paths.STATE_FILES)
        pattern = re.compile(r'"data"\s*/\s*"(' + names + r')"|\bDATA\s*/\s*"(' + names + r')"')
        offenders = []
        for path in list((ROOT / "src" / "tools").glob("*.py")) + list((ROOT / "app").glob("*.py")):
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if pattern.search(line):
                    offenders.append(f"{path.name}:{number}")
        self.assertEqual(offenders, [])

    def test_tests_run_without_a_state_directory(self):
        import run_tests
        self.assertEqual(run_tests.session_env({"DB_NAME": "x_test"})["H2DB_STATE_DIR"], "")


if __name__ == "__main__":
    unittest.main()
