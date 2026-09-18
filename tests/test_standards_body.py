import os
import sys
import unittest

sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "tools"))

from standards_body import (STANDARDS_BODY_MAP, resolve_standards_body,
                            _JURISDIKCE_BY_BODY, resolve_norma_jurisdikce)


class ResolveStandardsBodyTestCase(unittest.TestCase):
    """doc/PLAN.md §16, 2026-09-16 — repairs the R1.6 gap where no
    standard-setting body appeared in DocumentSource at all."""

    def test_national_institute_from_leading_token(self):
        self.assertIn("ÚNMS SR", resolve_standards_body("STN EN 61982-4"))
        self.assertIn("ČAS", resolve_standards_body("ČSN EN 17124"))
        self.assertIn("DIN", resolve_standards_body("DIN 3384-1"))

    def test_national_adoption_resolves_to_the_adopting_institute(self):
        # "STN EN ISO 1234" is published BY the Slovak institute even
        # though the underlying norm is European/international — the
        # leading token is what identifies the publisher.
        self.assertIn("ÚNMS SR", resolve_standards_body("STN EN ISO 21010"))
        self.assertIn("ČAS", resolve_standards_body("ČSN EN IEC 62282-2-100"))

    def test_international_bodies(self):
        self.assertIn("ISO", resolve_standards_body("ISO 21010"))
        self.assertIn("IEC", resolve_standards_body("IEC/TS 62351-100-1"))

    def test_iso_stage_prefixes_are_their_own_tokens_not_shadowed_by_iso(self):
        # "ISO/AWI" must not be mistaken for the bare "ISO" token nor
        # missed entirely — draft-stage designations are still ISO's.
        for stage in ("ISO/AWI", "ISO/DIS", "ISO/CD", "ISO/TR", "ISO/TS",
                      "ISO/FDIS", "ISO/WD", "ISO/PWI"):
            self.assertIn("ISO", resolve_standards_body(f"{stage} 24078"), stage)

    def test_dvgw_family_shares_one_body(self):
        # Verified from the records themselves: the G-series titles cite
        # the DVGW-Regelwerk directly and the whole family uses DVGW's
        # (A)/(M) Arbeitsblatt/Merkblatt convention.
        bodies = {resolve_standards_body(d) for d in
                  ("G 260 (A)", "GW 350 (A)", "C 260 (A)", "ZP 4110",
                   "Gas-Information Nr. 25", "G269")}
        self.assertEqual(len(bodies), 1)
        self.assertIn("DVGW", bodies.pop())

    def test_eiga_and_its_former_name_igc_resolve_together(self):
        # Same organisation before and after its renaming — an
        # equivalence deduplicate_db.py already encodes.
        self.assertEqual(resolve_standards_body("EIGA 121/14"),
                         resolve_standards_body("IGC Doc 121/14"))

    def test_edition_suffix_is_stripped_before_matching(self):
        self.assertEqual(resolve_standards_body("STN EN 61982-4/ - 2016.08"),
                         resolve_standards_body("STN EN 61982-4"))

    def test_number_glued_to_the_prefix_still_resolves(self):
        # "ZP-5101" has no space, so the first whitespace token is not
        # itself a map key; the leading alphabetic run is. Verified
        # corpus-wide (2026-09-16) to change the answer for exactly these
        # two records and never to invent a body for an unmapped token.
        self.assertIn("DVGW", resolve_standards_body("ZP-5101"))
        self.assertIn("DVGW", resolve_standards_body("ZP-8106"))

    def test_the_prefix_fallback_never_invents_a_body(self):
        for unknown in ("A-A-59874", "FBETEM-007", "XYZ-1234"):
            self.assertIsNone(resolve_standards_body(unknown), unknown)

    def test_unrecognized_designation_returns_none_never_guesses(self):
        for unknown in ("MB DRGA 514", "SEP 1970", "AR 214", "TB. 11/114",
                        "Part 1", "Band 27", "FBETEM-007"):
            self.assertIsNone(resolve_standards_body(unknown), unknown)

    def test_blank_and_none_return_none(self):
        self.assertIsNone(resolve_standards_body(None))
        self.assertIsNone(resolve_standards_body(""))
        self.assertIsNone(resolve_standards_body("   "))

    def test_match_is_case_insensitive_as_a_fallback(self):
        self.assertEqual(resolve_standards_body("stn en 12345"),
                         resolve_standards_body("STN EN 12345"))

    def test_map_has_no_blank_values(self):
        for token, body in STANDARDS_BODY_MAP.items():
            self.assertTrue(body and body.strip(), token)


class ResolveNormaJurisdikceTestCase(unittest.TestCase):
    """doc/PLAN.md §41, 2026-09-18: jurisdikce derived from the same
    issuing-body resolution above — never a separate guess."""

    def test_every_body_in_the_map_has_a_jurisdikce_entry(self):
        # Regression guard: a body added to STANDARDS_BODY_MAP with no
        # matching jurisdikce here would silently return None for every
        # record using it -- this test forces the two to be kept in sync.
        for body in set(STANDARDS_BODY_MAP.values()):
            self.assertIn(body, _JURISDIKCE_BY_BODY, body)

    def test_national_institute_gives_its_own_country(self):
        self.assertEqual(resolve_norma_jurisdikce("STN EN 12345"), "SK")
        self.assertEqual(resolve_norma_jurisdikce("ČSN ISO 14687"), "CZ")
        self.assertEqual(resolve_norma_jurisdikce("SAE J2601"), "US")

    def test_genuinely_international_body_is_mezinarodni(self):
        self.assertEqual(resolve_norma_jurisdikce("ISO 22734"), "mezinárodní")
        self.assertEqual(resolve_norma_jurisdikce("IMO IGF Code"), "mezinárodní")
        self.assertEqual(resolve_norma_jurisdikce("DNV/RP"), "mezinárodní")

    def test_european_body_is_eu(self):
        self.assertEqual(resolve_norma_jurisdikce("EN 17127"), "EU")
        self.assertEqual(resolve_norma_jurisdikce("EIGA Doc 15/06"), "EU")

    def test_unrecognized_designation_returns_none(self):
        self.assertIsNone(resolve_norma_jurisdikce("TPP 702 10"))
        self.assertIsNone(resolve_norma_jurisdikce(None))


if __name__ == "__main__":
    unittest.main()
