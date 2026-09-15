import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))

from build_unified_db import (
    extract_znacka_from_title, resolve_prokop_jurisdikce,
    record_url, apply_authoritative_metadata, synthesize_csn_adoption_records,
    classify_law_document_typ, split_sinay_zakony_row,
)


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

    def test_bare_en_designation_with_no_iso_iec_is_eu_not_cz(self):
        # doc/PLAN.md §9: a bare "EN 17127" (no ISO/IEC after it) is
        # itself the CEN/CENELEC original, not a ČSN adoption — real case
        # found live: "ČSN EN 17127" adopts bare "EN 17127".
        self.assertEqual(resolve_prokop_jurisdikce("EN 17127"), "EU")
        self.assertEqual(resolve_prokop_jurisdikce("EN 17339"), "EU")


class ClassifyLawDocumentTypTestCase(unittest.TestCase):
    """doc/PLAN.md §11/§14, 2026-09-14/15: Sinay_Zakony used to hardcode
    every record as "Zákon"; Haltuf_Dokumenty's own typ_dokumentu is just
    a raw, uninterpreted numeric category id. Real corpus check found EU
    regulations/directives/decisions and Czech/Slovak Vyhlášky/Nařízení
    vlády mixed in under one label (Sinay), and effectively no
    classification at all for Haltuf's 179 records. Every case here is a
    real title found in the actual corpus
    (data/database_merged_raw.json), not invented."""

    def test_real_czech_zakon(self):
        self.assertEqual(
            classify_law_document_typ("Zákon č. 458/2000 Sb., o podmínkách podnikání..."), "Zákon")
        self.assertEqual(
            classify_law_document_typ("zákon č. 201/2012 Sb., o ochraně ovzduší"), "Zákon")

    def test_zakonik_is_also_zakon(self):
        self.assertEqual(classify_law_document_typ("Zákon č. 262/2006 Sb., zákoník práce"), "Zákon")

    def test_czech_and_slovak_vyhlaska(self):
        self.assertEqual(
            classify_law_document_typ("Vyhláška č. 133/2010 Sb., o jakosti a evidenci pohonných hmot"),
            "Vyhláška")
        self.assertEqual(classify_law_document_typ("Vyhláška MV SR č.699/2004 Z. z"), "Vyhláška")
        self.assertEqual(classify_law_document_typ("vyhlášky  č. 94/2004 Z .z."), "Vyhláška")

    def test_narizeni_vlady(self):
        self.assertEqual(
            classify_law_document_typ(
                "Nařízení vlády č. 378/2001 Sb., kterým se stanoví bližší požadavky..."),
            "Nařízení vlády")

    def test_eu_regulation_variants(self):
        self.assertEqual(
            classify_law_document_typ("Nařízení Evropského parlamentu a Rady (EU) 2019/2144"),
            "Nařízení EU")
        self.assertEqual(
            classify_law_document_typ("Delegované nařízení Komise (EU) 2023/1184"), "Nařízení EU")
        self.assertEqual(
            classify_law_document_typ("Nařízení Komise v přenesené pravomoci (EU) 2023/1185"),
            "Nařízení EU")

    def test_own_type_wins_over_a_later_reference_to_a_different_act_type(self):
        # doc/PLAN.md §14: real corpus regression — this act states its
        # own type ("Nařízení") up front and only later cites an
        # unrelated directive/decision it amends or repeals; the earliest
        # type-keyword position must win, not a fixed check order (which
        # would have misread it as the type of the act it repeals).
        self.assertEqual(
            classify_law_document_typ(
                "Nařízení Evropského parlamentu a Rady (EU) 2023/1804 ze dne 13. září 2023 "
                "o zavádění infrastruktury pro alternativní paliva a o zrušení směrnice 2014/94/EU"),
            "Nařízení EU")
        self.assertEqual(
            classify_law_document_typ(
                "(EU) 2024/1789 - Nařízení Evropského parlamentu a Rady (EU) 2024/1789 ze dne "
                "13. června 2024 o vnitřním trhu s plynem ..., o změně nařízení (EU) č. 1227/2011 "
                "... a rozhodnutí (EU) 2017/684 a o zrušení nařízení (ES) č. 715/2009"),
            "Nařízení EU")

    def test_eu_directive_even_with_a_leading_project_label(self):
        # Real case: the EU marker isn't at the very start of the title.
        self.assertEqual(
            classify_law_document_typ(
                "REDIII - Smernica Európskeho parlamentu a Rady (EÚ) 2023/2413 z 18. októbra 2023..."),
            "Směrnice EU")

    def test_eu_commission_decision_without_bracket_marker(self):
        # Real case: no "(EU)" bracket at all, but "komisie" (Commission)
        # plus "rozhodnutie" is unambiguous.
        self.assertEqual(
            classify_law_document_typ(
                "Vykonávacie rozhodnutie komisie 2022/2427 sa stanovujú závery..."),
            "Rozhodnutí EU")

    def test_genuinely_unclear_falls_back_to_empty_string(self):
        # A policy strategy paper and a UN/ECE vehicle regulation are
        # neither — never force-guessed into the wrong bucket.
        self.assertEqual(classify_law_document_typ("Vodíková stratégia pre klimaticky neutrálnu Európu"), "")
        self.assertEqual(classify_law_document_typ("(EHK OSN) č. 134"), "")

    def test_blank_is_empty_string(self):
        self.assertEqual(classify_law_document_typ(""), "")
        self.assertEqual(classify_law_document_typ(None), "")

    def test_haltuf_compound_noun_zakon_not_anchored_at_start(self):
        # doc/PLAN.md §14: Haltuf often names a well-known Act as
        # "<Adjective> zákon", not "Zákon č. ...".
        self.assertEqual(classify_law_document_typ("Energetický zákon (č. 458/2000 Sb.)"), "Zákon")
        self.assertEqual(classify_law_document_typ("Stavební zákon (č. 283/2021 Sb.)"), "Zákon")
        self.assertEqual(classify_law_document_typ("Zákon o ochraně ovzduší (č. 201/2012 Sb.)"), "Zákon")
        self.assertEqual(classify_law_document_typ("426/2021 Sb. - novela Zákona o drahách"), "Zákon")

    def test_haltuf_english_eu_act_titles(self):
        # doc/PLAN.md §14: Haltuf carries an English-language duplicate
        # row for most EU acts, alongside the Czech one.
        self.assertEqual(
            classify_law_document_typ(
                "2014/34/EU \nDIRECTIVE  OF THE EUROPEAN PARLIAMENT AND OF THE COUNCIL\nof 26 February 2014"),
            "Směrnice EU")
        self.assertEqual(
            classify_law_document_typ(
                "(EU) 1300/2014 - TSI PRM - Commission Regulation of 18 November 2014 on the technical..."),
            "Nařízení EU")
        self.assertEqual(
            classify_law_document_typ(
                "(EU) 2018/546 - DECISION  OF THE EUROPEAN CENTRAL BANK\nof 15 March 2018 on delegation..."),
            "Rozhodnutí EU")

    def test_haltuf_european_central_bank_in_czech(self):
        self.assertEqual(
            classify_law_document_typ(
                "Rozhodnutí Evropské centrální banky (EU) 2018/546 ze dne 15. března 2018..."),
            "Rozhodnutí EU")

    def test_haltuf_bare_norm_designation_is_norma(self):
        # doc/PLAN.md §14: Haltuf mixes bare norm citations in among its
        # law records (same designation shapes as fetch_fulltext.py's own
        # is_norm_designation()).
        self.assertEqual(classify_law_document_typ("ČSN EN 17127"), "Norma")
        self.assertEqual(classify_law_document_typ("EN 17339"), "Norma")
        self.assertEqual(classify_law_document_typ("DIN EN ISO 22734"), "Norma")
        self.assertEqual(classify_law_document_typ("ISO 16111"), "Norma")

    def test_haltuf_truncated_czech_title_with_no_type_word_falls_back(self):
        # Real case: this specific Czech-language row never states its
        # own type (the source data itself omits the "Nařízení Komise"
        # lead-in) — correctly unclassified here; its English sibling row
        # (see test_haltuf_english_eu_act_titles above) resolves it, and
        # programmatic_merge()'s existing backfill picks that up post-merge.
        self.assertEqual(
            classify_law_document_typ(
                "(EU) 1300/2014 - TSI PRM - \nze dne 18. listopadu 2014,\no technických specifikacích..."),
            "")

    def test_non_eu_international_instruments_stay_unclassified(self):
        # doc/PLAN.md §14: ADR/RID/UN-ECE regulations cite "Regulation"/
        # "Agreement" too, but without an EU/CZ/SK institution attached —
        # never guessed into an EU or national bucket.
        self.assertEqual(
            classify_law_document_typ(
                "ADR 2025 - Agreement concerning the International Carriage of Dangerous Goods by Road"),
            "")
        self.assertEqual(
            classify_law_document_typ(
                "RID -  Appendix C – Regulation concerning the International Carriage of Dangerous Goods by Rail"),
            "")
        self.assertEqual(classify_law_document_typ("UNECE Regulation No. 100 (Revision 2)"), "")


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


class RecordUrlTestCase(unittest.TestCase):
    def test_prefers_odkaz_hlavni(self):
        item = {"odkaz_hlavni": "https://a", "odkaz_eu": "https://b", "odkaz_sk": "https://c"}
        self.assertEqual(record_url(item), "https://a")

    def test_falls_back_in_order(self):
        self.assertEqual(record_url({"odkaz_eu": "https://b", "odkaz_sk": "https://c"}), "https://b")
        self.assertEqual(record_url({"odkaz_sk": "https://c"}), "https://c")

    def test_no_url_is_empty_string(self):
        self.assertEqual(record_url({}), "")


class ApplyAuthoritativeMetadataTestCase(unittest.TestCase):
    """doc/PLAN.md §8, 2026-09-11: the build_unified_db.py-side half of
    the authoritative per-site title/description overlay."""

    def test_fetched_entry_attaches_new_fields_without_touching_originals(self):
        record = {"znacka": "458/2000 Sb.", "nazev_cz": "Původní název",
                  "odkaz_hlavni": "https://www.zakonyprolidi.cz/cs/2000-458",
                  "anotace_poznamka": ""}
        cache = {
            "https://www.zakonyprolidi.cz/cs/2000-458": {
                "status": "fetched", "title": "458/2000 Sb. Energetický zákon",
                "description": "Zákon o podmínkách podnikání...",
                "zdroj_esbirka_url": "https://e-sbirka.gov.cz/sb/2000/458",
            }
        }
        apply_authoritative_metadata(record, cache)
        self.assertEqual(record["nazev_autoritativni"], "458/2000 Sb. Energetický zákon")
        self.assertEqual(record["popis_autoritativni"], "Zákon o podmínkách podnikání...")
        self.assertEqual(record["zdroj_autoritativni_url"], "https://e-sbirka.gov.cz/sb/2000/458")
        # Original fields are untouched.
        self.assertEqual(record["nazev_cz"], "Původní název")
        self.assertEqual(record["anotace_poznamka"], "")

    def test_falls_back_to_fetched_url_when_no_esbirka_reference(self):
        record = {"znacka": "ISO 14687", "odkaz_hlavni": "https://eur-lex.europa.eu/x"}
        cache = {"https://eur-lex.europa.eu/x": {
            "status": "fetched", "title": "T", "description": None, "zdroj_esbirka_url": None}}
        apply_authoritative_metadata(record, cache)
        self.assertEqual(record["zdroj_autoritativni_url"], "https://eur-lex.europa.eu/x")

    def test_csn_key_used_when_no_url_present(self):
        record = {"znacka": "ČSN ISO 14687"}
        cache = {"csn:ČSN ISO 14687": {"status": "fetched", "title": "T", "description": None,
                                        "zdroj_esbirka_url": None}}
        apply_authoritative_metadata(record, cache)
        self.assertEqual(record["nazev_autoritativni"], "T")

    def test_failed_status_does_not_attach_anything(self):
        record = {"znacka": "X", "odkaz_hlavni": "https://a"}
        cache = {"https://a": {"status": "failed", "title": None, "description": None,
                                "zdroj_esbirka_url": None}}
        apply_authoritative_metadata(record, cache)
        self.assertNotIn("nazev_autoritativni", record)

    def test_no_cache_hit_does_not_attach_anything(self):
        record = {"znacka": "X", "odkaz_hlavni": "https://unrelated"}
        apply_authoritative_metadata(record, {})
        self.assertNotIn("nazev_autoritativni", record)

    def test_csn_detail_url_preferred_over_records_own_url(self):
        # doc/PLAN.md §9: a ČSN match's real provenance is the
        # Detailnormy.aspx page, not the record's own (often third-party)
        # odkaz_hlavni.
        record = {"znacka": "ČSN EN 17127", "odkaz_hlavni": "https://www.technicke-normy-csn.cz/x.html"}
        cache = {"csn:ČSN EN 17127": {
            "status": "fetched", "title": "T", "description": None, "zdroj_esbirka_url": None,
            "zdroj_autoritativni_url": "https://csnonline.agentura-cas.cz/Detailnormy.aspx?k=1",
        }}
        apply_authoritative_metadata(record, cache)
        self.assertEqual(record["zdroj_autoritativni_url"],
                         "https://csnonline.agentura-cas.cz/Detailnormy.aspx?k=1")

    def test_jurisdikce_autoritativni_corrects_jurisdikce_and_keeps_original(self):
        record = {"znacka": "EN 17127", "jurisdikce": "CZ"}
        cache = {"csn:EN 17127": {
            "status": "fetched", "title": "English title", "description": None,
            "zdroj_esbirka_url": None, "jurisdikce_autoritativni": "EU",
        }}
        apply_authoritative_metadata(record, cache)
        self.assertEqual(record["jurisdikce"], "EU")
        self.assertEqual(record["jurisdikce_puvodni"], "CZ")

    def test_jurisdikce_unchanged_when_already_correct(self):
        record = {"znacka": "ISO 14687", "jurisdikce": "mezinárodní"}
        cache = {"csn:ISO 14687": {
            "status": "fetched", "title": "T", "description": None,
            "zdroj_esbirka_url": None, "jurisdikce_autoritativni": "mezinárodní",
        }}
        apply_authoritative_metadata(record, cache)
        self.assertEqual(record["jurisdikce"], "mezinárodní")
        self.assertNotIn("jurisdikce_puvodni", record)


class SynthesizeCsnAdoptionRecordsTestCase(unittest.TestCase):
    """doc/PLAN.md §9: builds a brand-new record for a Czech ČSN adoption
    confirmed by agentura-cas.cz that has no record of its own anywhere
    in the corpus yet (real case: "ČSN EN 17339", bare "EN 17339" exists
    but no ČSN-prefixed sibling did)."""

    def test_adds_new_record_when_no_existing_sibling(self):
        unified_db = [{"znacka": "EN 17339", "jurisdikce": "EU"}]
        cache = {"csn:EN 17339": {
            "status": "fetched",
            "synthesize": {
                "zdroj_dat": "CSN_Adoption_AgenturaCAS",
                "znacka": "ČSN EN 17339",
                "typ_dokumentu": "Norma",
                "nazev_cz": "Český název",
                "jurisdikce": "CZ",
                "odkaz_hlavni": "https://csnonline.agentura-cas.cz/Detailnormy.aspx?k=1",
                "nazev_autoritativni": "Český název",
                "zdroj_autoritativni_url": "https://csnonline.agentura-cas.cz/Detailnormy.aspx?k=1",
            },
        }}
        added = synthesize_csn_adoption_records(unified_db, cache)
        self.assertEqual(added, 1)
        self.assertEqual(len(unified_db), 2)
        new_record = unified_db[1]
        self.assertEqual(new_record["znacka"], "ČSN EN 17339")
        self.assertEqual(new_record["jurisdikce"], "CZ")
        self.assertEqual(new_record["zdroj_dat"], "CSN_Adoption_AgenturaCAS")
        self.assertEqual(new_record["nazev_autoritativni"], "Český název")

    def test_skips_when_sibling_already_exists(self):
        unified_db = [{"znacka": "ČSN EN 17339", "jurisdikce": "CZ"}]
        cache = {"csn:EN 17339": {
            "status": "fetched",
            "synthesize": {
                "zdroj_dat": "CSN_Adoption_AgenturaCAS",
                "znacka": "ČSN EN 17339",
                "typ_dokumentu": "Norma",
                "nazev_cz": "Český název",
                "jurisdikce": "CZ",
            },
        }}
        added = synthesize_csn_adoption_records(unified_db, cache)
        self.assertEqual(added, 0)
        self.assertEqual(len(unified_db), 1)

    def test_no_synthesize_block_is_a_no_op(self):
        unified_db = [{"znacka": "EN 17127"}]
        cache = {"csn:EN 17127": {"status": "fetched", "title": "T"}}
        added = synthesize_csn_adoption_records(unified_db, cache)
        self.assertEqual(added, 0)
        self.assertEqual(len(unified_db), 1)

    def test_idempotent_across_two_matching_synthesize_entries(self):
        # Two different bare records could, in principle, resolve to the
        # same ČSN designation — never add it twice.
        unified_db = []
        block = {
            "zdroj_dat": "CSN_Adoption_AgenturaCAS", "znacka": "ČSN EN 17339",
            "typ_dokumentu": "Norma", "nazev_cz": "X", "jurisdikce": "CZ",
        }
        cache = {
            "csn:EN 17339": {"status": "fetched", "synthesize": block},
            "csn:Haltuf-duplicate": {"status": "fetched", "synthesize": dict(block)},
        }
        added = synthesize_csn_adoption_records(unified_db, cache)
        self.assertEqual(added, 1)
        self.assertEqual(len(unified_db), 1)


class SplitSinayZakonyRowTestCase(unittest.TestCase):
    """doc/PLAN.md §15, 2026-09-15: the EU version of a law is the legally
    binding original, CZ/SK versions are national implementations derived
    from it -- these become separate, interlinked records instead of
    extra fields bundled onto one (rejected first draft)."""

    def test_cz_only_row_yields_a_single_primary_record(self):
        item = {"Dokument CZ": "Zákon č. 458/2000 Sb., energetický zákon",
                "URL CZ": "https://www.zakonyprolidi.cz/cs/2000-458"}
        records, relations = split_sinay_zakony_row(item)
        self.assertEqual(len(records), 1)
        self.assertEqual(relations, [])
        primary = records[0]
        self.assertEqual(primary["jurisdikce"], "CZ")
        self.assertEqual(primary["odkaz_hlavni"], "https://www.zakonyprolidi.cz/cs/2000-458")
        self.assertEqual(primary["zdroj_dat"], "Sinay_Zakony")

    def test_sk_only_fallback_yields_a_single_record_with_sk_jurisdikce(self):
        # doc/PLAN.md §15: also the fix for the pre-existing odkaz_hlavni
        # bug -- the URL must follow whichever language's text actually
        # became the title, not always "URL CZ".
        item = {"Dokument SK": "Vyhláška č. 124/2000 Z. z.",
                "URL SK": "https://www.slov-lex.sk/pravne-predpisy/SK/ZZ/2000/124/"}
        records, relations = split_sinay_zakony_row(item)
        self.assertEqual(len(records), 1)
        self.assertEqual(relations, [])
        primary = records[0]
        self.assertEqual(primary["jurisdikce"], "SK")
        self.assertEqual(primary["nazev_cz"], "Vyhláška č. 124/2000 Z. z.")
        self.assertEqual(primary["odkaz_hlavni"], "https://www.slov-lex.sk/pravne-predpisy/SK/ZZ/2000/124/")

    def test_identical_cz_and_sk_text_does_not_spuriously_split(self):
        # The SK sibling must only appear for genuine dual content, not
        # when "Dokument SK" merely repeats the same text as "Dokument CZ".
        item = {"Dokument CZ": "Zákon č. 458/2000 Sb.", "URL CZ": "https://a",
                "Dokument SK": "Zákon č. 458/2000 Sb.", "URL SK": "https://a"}
        records, relations = split_sinay_zakony_row(item)
        self.assertEqual(len(records), 1)
        self.assertEqual(relations, [])

    def test_genuinely_distinct_cz_and_sk_text_splits_and_links(self):
        item = {"Dokument CZ": "Zákon č. 458/2000 Sb., energetický zákon",
                "URL CZ": "https://www.zakonyprolidi.cz/cs/2000-458",
                "Dokument SK": "Vyhláška č. 124/2000 Z. z.",
                "URL SK": "https://www.slov-lex.sk/pravne-predpisy/SK/ZZ/2000/124/"}
        records, relations = split_sinay_zakony_row(item)
        self.assertEqual(len(records), 2)
        cz, sk = records
        self.assertEqual(cz["jurisdikce"], "CZ")
        self.assertEqual(sk["jurisdikce"], "SK")
        self.assertEqual(sk["odkaz_hlavni"], "https://www.slov-lex.sk/pravne-predpisy/SK/ZZ/2000/124/")
        self.assertEqual(len(relations), 1)
        self.assertEqual(relations[0]["relation_type"], "NATIONAL_EQUIVALENT")
        self.assertEqual(relations[0]["from_identifier"], cz["znacka"])
        self.assertEqual(relations[0]["to_identifier"], sk["znacka"])

    def test_sk_column_holding_only_the_bare_eu_citation_does_not_split(self):
        # doc/PLAN.md §15 follow-up: real corpus bug — "Dokument SK" was a
        # bare EU-act citation ("(EÚ) ...", not real Slovak text) on a row
        # whose CZ text is a genuine national implementing act (distinct
        # own znacka, not itself equal to the EU original's — see
        # test_eu_regulation_with_direct_effect_collapses_to_a_single_eu_record
        # for that separate scenario). Splitting the SK citation out would
        # create a content-free duplicate of the EU original under
        # jurisdikce SK; also used to crash init_db.py via a MariaDB
        # accent-insensitive unique-identifier collation clash with the
        # correctly-spelled "(EU) ..." elsewhere.
        item = {"Dokument CZ": "Zákon č. 458/2000 Sb., energetický zákon",
                "URL CZ": "https://cz",
                "Dokument SK": "(EÚ) 2019/2144", "URL SK": "https://sk",
                "Dokument EU": "Nařízení Evropského parlamentu a Rady (EU) 2019/2144 ze dne 27. listopadu 2019",
                "URL EU": "https://eu"}
        records, relations = split_sinay_zakony_row(item)
        jurisdikce = [r["jurisdikce"] for r in records]
        self.assertEqual(jurisdikce, ["CZ", "EU"])
        self.assertEqual(relations, [])

    def test_eu_marker_normalized_even_via_leading_match(self):
        # doc/PLAN.md §15 follow-up: case B's leading-EU-number match used
        # to skip the EÚ/ES -> EU normalization that case F already did,
        # so a Slovak-spelled leading citation ("(EÚ) 2021/535 ...")
        # produced a znacka distinct (in Python) from the correctly-spelled
        # "(EU) 2021/535" — but MariaDB's accent-insensitive collation
        # treats them as the same identifier, crashing the import.
        item = {"Dokument CZ": "Nařízení Komise (EU) 2021/535 ze dne 31. března 2021",
                "URL CZ": "https://cz",
                "Dokument SK": "(EÚ) 2021/535 nariadenie", "URL SK": "https://sk"}
        records, relations = split_sinay_zakony_row(item)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[1]["znacka"], "(EU) 2021/535")

    def test_eu_regulation_with_direct_effect_collapses_to_a_single_eu_record(self):
        # doc/PLAN.md §15 follow-up: real corpus bug — an EU REGULATION
        # (unlike a directive) applies directly, so Sinay's "Dokument CZ"/
        # "Dokument SK" columns just repeat the same regulation's own
        # title rather than naming a genuinely separate national act.
        # Splitting these produced records whose own znacka literally
        # equalled the EU record's — link_document_relations_auto.py's
        # R1.4 then created a self-referencing "X ADOPTS X" edge, which
        # crashed load_document_relations.py's unique-constraint insert.
        item = {"Dokument CZ": "Delegované nařízení Komise (EU) 2023/1184",
                "URL CZ": "https://cz",
                "Dokument SK": "Delegované nariadenie EK (EÚ) 2023/1184 z 10. februára 2023",
                "URL SK": "https://sk",
                "Dokument EU": ("Delegované nařízení Komise (EU) 2023/1184 ze dne 10. února 2023, "
                                "kterým se doplňuje směrnice ..."),
                "URL EU": "https://eu"}
        records, relations = split_sinay_zakony_row(item)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["jurisdikce"], "EU")
        self.assertEqual(records[0]["odkaz_hlavni"], "https://eu")
        self.assertEqual(relations, [])

    def test_eu_original_is_split_out_as_its_own_record(self):
        item = {"Dokument CZ": "Zákon č. 458/2000 Sb.", "URL CZ": "https://cz",
                "Dokument EU": "Směrnice (EU) 2019/692", "URL EU": "https://eu"}
        records, relations = split_sinay_zakony_row(item)
        self.assertEqual(len(records), 2)
        primary, eu = records
        self.assertEqual(primary["jurisdikce"], "CZ")
        self.assertEqual(eu["jurisdikce"], "EU")
        self.assertEqual(eu["nazev_cz"], "Směrnice (EU) 2019/692")
        self.assertEqual(eu["odkaz_hlavni"], "https://eu")
        # No CZ<->SK relation, since no SK sibling was emitted.
        self.assertEqual(relations, [])

    def test_nazev_eu_and_odkaz_eu_stay_on_primary_for_r1_3_matching(self):
        # link_document_relations_auto.py's existing R1.3 IMPLEMENTS
        # detection reads nazev_eu/odkaz_eu straight off the primary
        # record -- must survive the split unchanged, even though they're
        # never mapped into a Document column downstream.
        item = {"Dokument CZ": "Zákon č. 458/2000 Sb.", "URL CZ": "https://cz",
                "Dokument EU": "Směrnice (EU) 2019/692", "URL EU": "https://eu"}
        records, _ = split_sinay_zakony_row(item)
        primary = records[0]
        self.assertEqual(primary["nazev_eu"], "Směrnice (EU) 2019/692")
        self.assertEqual(primary["odkaz_eu"], "https://eu")

    def test_full_triple_yields_three_records_and_one_relation(self):
        item = {"Dokument CZ": "Zákon č. 458/2000 Sb., energetický zákon", "URL CZ": "https://cz",
                "Dokument SK": "Vyhláška č. 124/2000 Z. z.", "URL SK": "https://sk",
                "Dokument EU": "Směrnice (EU) 2019/692", "URL EU": "https://eu"}
        records, relations = split_sinay_zakony_row(item)
        jurisdikce = [r["jurisdikce"] for r in records]
        self.assertEqual(jurisdikce, ["CZ", "SK", "EU"])
        self.assertEqual(len(relations), 1)
        self.assertEqual(relations[0]["relation_type"], "NATIONAL_EQUIVALENT")

    def test_gestor_string_is_normalized_to_a_list_on_every_split_record(self):
        item = {"Dokument CZ": "Zákon č. 458/2000 Sb.", "URL CZ": "https://cz",
                "Dokument SK": "Vyhláška č. 124/2000 Z. z.", "URL SK": "https://sk",
                "Gestor CZ": "MPO"}
        records, _ = split_sinay_zakony_row(item)
        for record in records:
            self.assertEqual(record["gestor"], ["MPO"])


if __name__ == "__main__":
    unittest.main()
