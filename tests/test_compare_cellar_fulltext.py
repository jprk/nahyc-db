"""src/tools/compare_cellar_fulltext.py (doc/CELLAR_FULLTEXT.md): the verdict
on a Cellar text and the switch of the manifest. No network."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))

import compare_cellar_fulltext as cc  # noqa: E402


def row(**changes):
    base = {"local_path": "data/fulltext/A__11111111.html", "keys": ["S|A|odkaz_eu"], "url": "u",
            "designation": "A", "old_sha256": "1" * 64, "cellar_sha256": "2" * 64, "celex": "32022D2427",
            "cellar_file": "data/fulltext_mpo_cellar/A__22222222.html", "old_length": 1000,
            "cellar_length": 1000, "old_language": "CS", "cellar_language": "CS", "old_annexes": 1,
            "cellar_annexes": 1, "cellar_title_has_number": True, "title_similarity": 1.0, "verdict": "complete"}
    base.update(changes)
    return base


class VerdictTestCase(unittest.TestCase):
    def test_same_text_is_complete_and_same_bytes_identical(self):
        self.assertEqual(cc.verdict(row()), "complete")
        self.assertEqual(cc.verdict(row(cellar_sha256="1" * 64)), "identical")

    def test_a_missing_annex_a_shorter_text_or_another_language_is_not(self):
        self.assertIn("annexes 0 of 1", cc.verdict(row(cellar_annexes=0)))
        self.assertIn("shorter", cc.verdict(row(cellar_length=500)))
        self.assertIn("language EN", cc.verdict(row(cellar_language="EN")))
        self.assertIn("different beginning", cc.verdict(row(title_similarity=0.3)))

    def test_number_in_title(self):
        self.assertTrue(cc.number_in_title("32001L0042", "Směrnice Evropského parlamentu a Rady 2001/42/ES ze dne"))
        self.assertTrue(cc.number_in_title("32006R1907", "NAŘÍZENÍ (ES) č. 1907/2006"))
        self.assertFalse(cc.number_in_title("32006R1907", "NAŘÍZENÍ (ES) č. 1272/2008"))
        self.assertTrue(cc.number_in_title("52020DC0301", "anything"))

    def test_annex_headings_are_counted(self):
        self.assertEqual(cc.annex_count("Článek 1\nPŘÍLOHA I\ntext PŘÍLOHA\nANNEX II\nPříloha 3\n"), 3)


class SwitchManifestTestCase(unittest.TestCase):
    def manifest(self):
        return {"S|A|odkaz_eu": {"status": "fetched", "url": "u", "local_path": "data/fulltext/A__11111111.html",
                                 "sha256": "1" * 64}}

    def test_a_verified_file_is_switched_to_cellar(self):
        manifest = self.manifest()
        switched, kept = cc.switch_manifest(manifest, {"files": [row()]}, now="t")
        self.assertEqual((switched, kept), (["S|A|odkaz_eu"], []))
        entry = manifest["S|A|odkaz_eu"]
        self.assertEqual(entry["local_path"], "data/fulltext/A__22222222.html")
        self.assertEqual((entry["via"], entry["celex"], entry["sha256"], entry["url"]),
                         ("cellar", "32022D2427", "2" * 64, "u"))

    def test_an_incomplete_one_keeps_its_file_with_the_reason(self):
        manifest = self.manifest()
        switched, kept = cc.switch_manifest(manifest, {"files": [row(cellar_annexes=0, verdict="annexes 0 of 1")]})
        self.assertEqual(switched, [])
        self.assertEqual(manifest["S|A|odkaz_eu"]["local_path"], "data/fulltext/A__11111111.html")
        self.assertEqual(manifest["S|A|odkaz_eu"]["cellar_check"], "annexes 0 of 1")


if __name__ == "__main__":
    unittest.main()
