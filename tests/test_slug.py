import os
import sys
import unittest

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "tools"))

from slug import assign_slugs, base_slug, slugify


class SlugifyTestCase(unittest.TestCase):
    def test_strips_diacritics(self):
        self.assertEqual(slugify("ČSN EN 17124"), "csn-en-17124")
        self.assertEqual(slugify("Úrad pre normalizáciu"), "urad-pre-normalizaciu")

    def test_punctuation_collapses_to_single_dash(self):
        self.assertEqual(slugify("(EU) 2022/869"), "eu-2022-869")
        self.assertEqual(slugify("458/2000 Sb."), "458-2000-sb")

    def test_no_leading_or_trailing_dash(self):
        self.assertEqual(slugify("  //ISO 21010//  "), "iso-21010")

    def test_text_without_alphanumerics_gives_empty_string(self):
        self.assertEqual(slugify("—/—"), "")
        self.assertEqual(slugify(""), "")


class BaseSlugTestCase(unittest.TestCase):
    def test_prefers_the_designation(self):
        self.assertEqual(base_slug("ČSN EN 17124", "Vodíkové palivo"), "csn-en-17124")

    def test_edition_suffix_is_not_part_of_the_slug(self):
        self.assertEqual(base_slug("STN EN 61982-4/ - 2016.08", "Akumulátorové batérie"),
                         "stn-en-61982-4")

    def test_designation_number_after_a_dash_is_kept(self):
        # Regression guard, 2026-09-16: the edition-suffix stripper used
        # to eat any trailing -NNNN, turning "ZP-5101" into "ZP" and
        # colliding two unrelated records onto one slug.
        self.assertEqual(base_slug("ZP-5101", "Verträglichkeit"), "zp-5101")
        self.assertEqual(base_slug("ZP-8106", "Ergänzungsprüfungen"), "zp-8106")

    def test_trailing_year_on_us_style_designations_is_still_stripped(self):
        self.assertEqual(base_slug("ASME B31.12-2019", "Hydrogen Piping"), "asme-b31-12")
        self.assertEqual(base_slug("AS 2022-1983", "Anhydrous ammonia"), "as-2022")

    def test_en_dash_edition_suffix_is_stripped_too(self):
        # The Sinay source mixes ASCII "-" and en-dash separators; 17
        # records kept their edition date purely because of that.
        self.assertEqual(base_slug("STN EN 13365/A1 – 2003.08", "Prepravné fľaše"),
                         "stn-en-13365-a1")

    def test_falls_back_to_a_title_hash_without_a_real_designation(self):
        slug = base_slug(None, "Standard Test Method for Measurement")
        self.assertTrue(slug.startswith("doc-"))
        self.assertEqual(len(slug), len("doc-") + 8)

    def test_hash_fallback_depends_only_on_the_title(self):
        # Derived from content alone, so it survives a rebuild.
        self.assertEqual(base_slug(None, "Migrating to Post-quantum cryptography"),
                         base_slug("", "Migrating to Post-quantum cryptography"))

    def test_identifier_that_is_not_a_designation_falls_back_to_the_hash(self):
        # A "designation" with no digit is a copy/fragment of the title,
        # not a real number — is_real_designation() already rejects it.
        self.assertTrue(base_slug("AGBF- Leitfaden – Wasserstoff",
                                  "AGBF- Leitfaden – Wasserstoff").startswith("doc-"))


class AssignSlugsTestCase(unittest.TestCase):
    def test_unique_designations_keep_their_bare_slug(self):
        got = assign_slugs([(1, "ČSN EN 17124", "a"), (2, "ISO 21010", "b")])
        self.assertEqual(got, {1: "csn-en-17124", 2: "iso-21010"})

    def test_collision_gets_a_numeric_suffix(self):
        got = assign_slugs([(1, "ZP 1", "a"), (2, "ZP 1", "b")])
        self.assertEqual(sorted(got.values()), ["zp-1", "zp-1-2"])

    def test_assignment_is_independent_of_input_order(self):
        # THE point of the module: collision suffixes are handed out in a
        # content-derived order, so two rebuilds that insert records in
        # different orders still produce identical slugs.
        records = [(1, "ZP 1", "alpha"), (2, "ZP 1", "beta"), (3, "ISO 21010", "gamma")]
        self.assertEqual(assign_slugs(records), assign_slugs(list(reversed(records))))

    def test_suffix_follows_content_order_not_key_order(self):
        forward = assign_slugs([(1, "ZP 1", "zulu"), (2, "ZP 1", "alpha")])
        # "alpha" sorts first on title, so it keeps the bare slug even
        # though its key is higher.
        self.assertEqual(forward[2], "zp-1")
        self.assertEqual(forward[1], "zp-1-2")

    def test_all_slugs_are_unique(self):
        records = [(i, "ZP 1", f"title {i}") for i in range(10)]
        got = assign_slugs(records)
        self.assertEqual(len(set(got.values())), 10)

    def test_empty_corpus(self):
        self.assertEqual(assign_slugs([]), {})


if __name__ == "__main__":
    unittest.main()
