import copy
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))
import source_registry as sr


class CommittedRegistryTestCase(unittest.TestCase):
    """The committed data/monitored_sources.json is consistent and keeps its layout."""

    def setUp(self):
        self.entries, self.groups = sr.load()

    def test_the_registry_validates(self):
        self.assertEqual(sr.validate(self.entries), [])

    def test_writing_it_back_changes_nothing(self):
        self.assertEqual(sr.dumps(self.entries, self.groups), sr.REGISTRY_PATH.read_text(encoding="utf-8"))

    def test_every_harvested_source_has_a_cadence_and_priority(self):
        for entry in self.entries:
            if entry["status"] not in sr.NOT_HARVESTED:
                self.assertIsNotNone(entry["cadence"], entry["id"])
                self.assertIsNotNone(entry["priority"], entry["id"])


class ValidateTestCase(unittest.TestCase):
    def setUp(self):
        entries, _ = sr.load()
        self.entry = copy.deepcopy(next(e for e in entries if e["id"] == "veklep-odok"))

    def test_values_outside_the_vocabulary_are_reported(self):
        for field, value in (("status", "maybe"), ("priority", 1), ("stage", "E9"), ("signal", ["news"]),
                             ("role", "L")):
            entry = {**self.entry, field: value}
            self.assertTrue(sr.validate([entry]), field)

    def test_a_prohibited_source_has_no_signal_and_a_manual_one_the_manual_stage(self):
        self.assertTrue(sr.validate([{**self.entry, "status": "prohibited"}]))
        self.assertTrue(sr.validate([{**self.entry, "status": "manual_only"}]))
        self.assertEqual(sr.validate([{**self.entry, "status": "manual_only", "stage": "manual"}]), [])

    def test_duplicates_and_missing_fields_are_reported(self):
        self.assertIn("duplicate", " ".join(sr.validate([self.entry, self.entry])))
        broken = dict(self.entry)
        del broken["stage"]
        self.assertTrue(sr.validate([broken]))


class LayoutAndSelectionTestCase(unittest.TestCase):
    def test_a_changed_field_changes_one_line(self):
        entries, groups = sr.load()
        original = sr.dumps(entries, groups).splitlines()
        entries[3]["verified_at"] = "2099-01-01"
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "r.json"
            sr.save(entries, groups, path)
            changed = path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(original), len(changed))
        self.assertEqual(sum(a != b for a, b in zip(original, changed)), 1)

    def test_urls_skip_templates_and_duplicates(self):
        entry = {"url": "https://a.test/", "access": {"method": "pdf_pattern", "endpoint": "https://a.test/v-{M}.pdf",
                                                      "feed": "https://a.test/"}}
        self.assertEqual(sr.urls(entry), ["https://a.test/"])
        entry["access"]["feed"] = "https://a.test/feed"
        self.assertEqual(sr.urls(entry), ["https://a.test/", "https://a.test/feed"])

    def test_select_by_id_stage_and_cadence(self):
        entries, _ = sr.load()
        self.assertEqual([e["id"] for e in sr.select(entries, ["otif-rid", "veklep-odok"])], ["otif-rid", "veklep-odok"])
        self.assertTrue(all(e["stage"] == "E2" for e in sr.select(entries, stage="E2")))
        weekly_e2 = sr.select(entries, stage="E2", cadence="weekly")
        self.assertTrue(weekly_e2 and all(e["cadence"] == "weekly" for e in weekly_e2))
        with self.assertRaises(KeyError):
            sr.select(entries, ["no-such-source"])


if __name__ == "__main__":
    unittest.main()
