import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))

from build_unified_db import extract_znacka_from_title, resolve_prokop_jurisdikce


class ResolveProkopJurisdikceTestCase(unittest.TestCase):
    """Step 1 follow-up #14: Prokop is a curated hydrogen-standards list,
    not exclusively a ČSN catalog -- a bare international ISO/IEC
    designation must never be marked CZ just because it came from this
    source (real cases: "ISO 22734:2019", "ISO 11114-4", "ISO 19880-9")."""

    def test_bare_iso_designation_is_mezinarodni_not_cz(self):
        self.assertEqual(resolve_prokop_jurisdikce("ISO 22734:2019"), "mezinárodní")
        self.assertEqual(resolve_prokop_jurisdikce("ISO 11114-4"), "mezinárodní")
        self.assertEqual(resolve_prokop_jurisdikce("ISO 19880-9"), "mezinárodní")

    def test_real_csn_designation_is_still_cz(self):
        self.assertEqual(resolve_prokop_jurisdikce("ČSN ISO 14687"), "CZ")
        self.assertEqual(resolve_prokop_jurisdikce("ČSN EN 17127"), "CZ")

    def test_bare_en_iso_designation_is_eu_not_cz(self):
        # Step 1 follow-up #16: the European (CEN/CENELEC) adoption of an
        # ISO/IEC standard, no ČSN prefix, is not a ČSN adoption either.
        self.assertEqual(resolve_prokop_jurisdikce("EN ISO 14687"), "EU")
        self.assertEqual(resolve_prokop_jurisdikce("prEN ISO 22734-1"), "EU")


class ExtractZnackaFromTitleTestCase(unittest.TestCase):
    """Covers every pattern found in the real Haltuf/Sinay data this
    session (see doc/PLAN.md Step 1 follow-ups #3/#4/#6) plus the two
    regressions caught along the way, so a future edit to this function
    can't silently reintroduce them."""

    def test_empty_and_no_number(self):
        self.assertEqual(extract_znacka_from_title(""), "")
        self.assertEqual(extract_znacka_from_title("Vodíková stratégia pre klimaticky neutrálnu Európu"), "")

    def test_bare_code_no_separator(self):
        self.assertEqual(extract_znacka_from_title("EN 17339"), "EN 17339")
        self.assertEqual(extract_znacka_from_title("ISO 14687"), "ISO 14687")

    def test_bare_code_with_internal_part_number_dash_not_truncated(self):
        # Regression: a bare part-numbered code has a hyphen with NO
        # surrounding whitespace ("...19880-1") and must NOT be mistaken
        # for the leading-code-plus-dash separator pattern (case C), which
        # used to truncate this to "ČSN EN ISO 19880", dropping the "-1".
        self.assertEqual(extract_znacka_from_title("ČSN EN ISO 19880-1"), "ČSN EN ISO 19880-1")
        self.assertEqual(extract_znacka_from_title("ČSN ISO 19880-8"), "ČSN ISO 19880-8")

    def test_leading_code_with_dash_separator(self):
        self.assertEqual(
            extract_znacka_from_title("(EU) 2024/1788 - SMĚRNICE EVROPSKÉHO PARLAMENTU A RADY (EU)"),
            "(EU) 2024/1788",
        )
        self.assertEqual(
            extract_znacka_from_title("2014/68/EU - DIRECTIVE OF THE EUROPEAN PARLIAMENT"),
            "2014/68/EU",
        )
        # The "(ATEX 137)" nickname is dropped here (case B's trailing-EU/ES
        # pattern matches first and stops at the number) — still uniquely
        # identifies the act, just shorter than case C alone would give.
        self.assertEqual(
            extract_znacka_from_title("1999/92/ES (ATEX 137) - \nSMĚRNICE EVROPSKÉHO PARLAMENTU A RADY"),
            "1999/92/ES",
        )

    def test_leading_code_with_no_separator_at_all(self):
        # No dash follows at all — its Czech counterpart above has one,
        # this variant doesn't, and must still be caught (case B).
        self.assertEqual(
            extract_znacka_from_title("2014/34/EU \nDIRECTIVE  OF THE EUROPEAN PARLIAMENT AND OF THE COUNCIL"),
            "2014/34/EU",
        )

    def test_trailing_bracketed_oj_reference(self):
        cz = ("Předpis Evropské hospodářské komise Organizace spojených národů (EHK OSN) "
              "č. 134 – Jednotná ustanovení ... [2019/795]")
        en = ("Regulation No 134 of the Economic Commission for Europe of the United "
              "Nations (UN/ECE) ... [2019/795]")
        self.assertEqual(extract_znacka_from_title(cz), "[2019/795]")
        self.assertEqual(extract_znacka_from_title(en), "[2019/795]")

    def test_czech_sb_citation_anywhere(self):
        self.assertEqual(
            extract_znacka_from_title("Zákon o ochraně ovzduší (č. 201/2012 Sb.)"),
            "201/2012 Sb.",
        )
        self.assertEqual(
            extract_znacka_from_title("Nařízení vlády č. 116/2016 Sb., o technických požadavcích na zařízení"),
            "116/2016 Sb.",
        )
        self.assertEqual(
            extract_znacka_from_title("Zákon č. 22/1997 Sb. – Posuzování shody a technické požadavky na výrobky"),
            "22/1997 Sb.",
        )

    def test_slovak_z_z_citation_tolerates_messy_spacing(self):
        self.assertEqual(extract_znacka_from_title("Vyhláška č. 124/2000 Z. z"), "124/2000 Z. z.")
        self.assertEqual(extract_znacka_from_title("vyhlášky  č. 94/2004 Z .z."), "94/2004 Z. z.")
        self.assertEqual(extract_znacka_from_title("Vyhláška MV SR č.699/2004 Z. z"), "699/2004 Z. z.")

    def test_eu_act_number_anywhere_in_prose(self):
        self.assertEqual(
            extract_znacka_from_title(
                "Nařízení Evropského parlamentu a Rady (EU) 2022/869 ze dne 30. května 2022 o pokynech"
            ),
            "(EU) 2022/869",
        )

    def test_eu_es_normalized_to_eu(self):
        # EÚ (Slovak) and ES (pre-Lisbon designation) must normalize to EU
        # so the same act cited under any of the three compares equal.
        self.assertEqual(
            extract_znacka_from_title(
                "REDIII - Smernica Európskeho parlamentu a Rady (EÚ) 2023/2413 z 18. októbra 2023"
            ),
            "(EU) 2023/2413",
        )

    def test_amending_reference_does_not_override_own_number(self):
        # The document's own number appears before any "kterym se meni"
        # (amends) clause citing a different act — must extract the first
        # (its own), not a later-mentioned one.
        self.assertEqual(
            extract_znacka_from_title(
                "Nařízení Komise (EU) 2021/535 ze dne 31. března 2021, kterým se mění nařízení (ES) č. 1881/2006"
            ),
            "(EU) 2021/535",
        )

    def test_no_false_positive_on_short_non_numeric_prefix(self):
        # "RID" has no digit and must not be force-matched as a code —
        # different RID appendices are genuinely different documents.
        self.assertEqual(extract_znacka_from_title("RID - Přípojek C – Řád pro mezinárodní železniční přepravu"), "")


if __name__ == "__main__":
    unittest.main()
