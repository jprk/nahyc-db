import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))
import fulltext_keys as fk


class FirstUrlTestCase(unittest.TestCase):
    def test_only_the_first_of_several_joined_addresses_is_taken(self):
        self.assertEqual(fk.first_url("https://a/x\n\nhttps://b/y"), "https://a/x")
        self.assertEqual(fk.first_url("  "), "")
        self.assertEqual(fk.first_url(None), "")


class DesignationTestCase(unittest.TestCase):
    def test_the_designation_of_an_address_is_stable_and_differs_between_addresses(self):
        a = fk.url_designation("https://x/a.pdf")
        self.assertEqual(a, fk.url_designation("https://x/a.pdf"))
        self.assertNotEqual(a, fk.url_designation("https://x/b.pdf"))
        self.assertRegex(a, r"^url-[0-9a-f]{8}$")

    def test_a_znacka_is_the_designation_whatever_the_field(self):
        self.assertEqual(fk.designation({"znacka": " 12/2020 Sb. ", "odkaz_eu": "https://x"}, "odkaz_eu"), "12/2020 Sb.")

    def test_without_a_znacka_the_address_of_the_field_decides(self):
        record = {"znacka": "", "odkaz_hlavni": "https://x/a.pdf", "odkaz_eu": "https://x/b.pdf"}
        self.assertEqual(fk.designation(record, "odkaz_hlavni"), fk.url_designation("https://x/a.pdf"))
        self.assertEqual(fk.designation(record, "odkaz_eu"), fk.url_designation("https://x/b.pdf"))
        self.assertEqual(fk.designation(record, "odkaz_sk"), "")


if __name__ == "__main__":
    unittest.main()
