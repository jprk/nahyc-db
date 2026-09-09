import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))

from parse_sinay_norms import classify_jurisdikce, _pdf_row_to_record


class ClassifyJurisdikceTestCase(unittest.TestCase):
    def test_stn_designation_is_slovak(self):
        self.assertEqual(classify_jurisdikce("STN EN 17124/ - 2022.06"), "SK")

    def test_german_bodies_are_de(self):
        for kategorie in ("DVGW-Arbeitsblatt (DVGW G-TK-1-4)", "Norm (DIN)", "Technischer Bericht (VDI)",
                          "Merkblatt (DASt)", "Technische Regel (BAuA)"):
            self.assertEqual(classify_jurisdikce("G 102-2 (A)", kategorie), "DE", msg=kategorie)

    def test_international_bodies_are_mezinarodni(self):
        self.assertEqual(classify_jurisdikce("22734", "ISO/TC 197 Hydrogen Technologies"), "mezinárodní")
        self.assertEqual(classify_jurisdikce("60092-506", "IEC/TC 18"), "mezinárodní")

    def test_cen_cenelec_and_eiga_are_eu(self):
        self.assertEqual(classify_jurisdikce("13480-9", "CEN/TC 54"), "EU")
        self.assertEqual(classify_jurisdikce("IGC 15", "EIGA"), "EU")

    def test_bare_en_designation_with_no_national_prefix_is_eu(self):
        self.assertEqual(classify_jurisdikce("EN 1717"), "EU")
        self.assertEqual(classify_jurisdikce("prEN 13480-9"), "EU")
        self.assertEqual(classify_jurisdikce("FprEN 62282-3-400"), "EU")

    def test_stn_en_prefix_is_still_slovak_not_eu(self):
        # STN must win over the bare-EN fallback — checked first in the
        # marker list, and this designation does have a national prefix.
        self.assertEqual(classify_jurisdikce("STN EN 17124/ - 2022.06"), "SK")

    def test_us_bodies(self):
        for kategorie in ("CGA - Compressed Gas Association", "ASTM International"):
            self.assertEqual(classify_jurisdikce("SOME-CODE", kategorie), "US", msg=kategorie)

    def test_unrecognized_us_body_is_neurceno_not_a_guess(self):
        # "US Air Force" isn't in the marker list — a deliberate residual,
        # not every conceivable issuing body is worth chasing (see
        # doc/PLAN.md Step 1 follow-up #8).
        self.assertEqual(classify_jurisdikce("A-A-59874", "US Air Force (Air Force Life Cycle Management Center)"),
                          "neurčeno")

    def test_unrecognized_body_is_neurceno_not_a_guess(self):
        self.assertEqual(classify_jurisdikce("SEP 1970", "SEP – Stahl-Eisen-Prüfblätter"), "neurčeno")
        self.assertEqual(classify_jurisdikce("bez označenia", ""), "neurčeno")


class PdfRowToRecordTestCase(unittest.TestCase):
    def test_adopted_stn_gets_stn_kategorie_and_platnost_from_date(self):
        row = {
            "designation": "STN EN 17124/ - 2022.06",
            "title": "Vodíkové palivo - Špecifikácia výrobku",
            "url": "https://normy.normoff.gov.sk/",
            "note": "Prijatá v sústave STN",
        }
        record = _pdf_row_to_record(row)
        self.assertEqual(record["Kategorie"], "STN (prijatá v sústave)")
        self.assertEqual(record["Platnost"], "od 06/2022")
        self.assertEqual(record["Jurisdikce"], "SK")
        self.assertEqual(record["Link"], "https://normy.normoff.gov.sk/")

    def test_foreign_body_note_becomes_kategorie(self):
        row = {
            "designation": "CGA H-10",
            "title": "Combustion safety for steam reformer",
            "url": "https://www.cganet.com/",
            "note": "CGA - Compressed Gas Association; US",
        }
        record = _pdf_row_to_record(row)
        self.assertEqual(record["Kategorie"], "CGA - Compressed Gas Association; US")
        self.assertEqual(record["Jurisdikce"], "US")

    def test_url_with_embedded_wrap_space_is_stripped(self):
        row = {"designation": "ISO 21011", "title": "Cryogenic vessels",
               "url": "https://www.iso.org/standards.h tml", "note": ""}
        record = _pdf_row_to_record(row)
        self.assertEqual(record["Link"], "https://www.iso.org/standards.html")


if __name__ == "__main__":
    unittest.main()
