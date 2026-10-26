"""Tests for src/tools/extract_fulltext.py (GitHub issue #2): clean text out
of whole-page downloads. Synthetic pages only — the real downloads under
data/fulltext/ are gitignored, so nothing here depends on them."""
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))

import extract_fulltext as ef

ZPL_PAGE = """<!DOCTYPE html><html><head><title>116/2016 Sb.</title>
<script src="/js/lib/jquery.min.js"></script></head><body>
<nav>Menu <a href="/cs/hledani">Hledání</a></nav>
<article class="doc-ctn" id="idBody_idCtn">
<div class="doc-sum Exp"><h4>Obsah</h4><div class="Tree"><div class="Node">
<a class="Name" href="#p1">§ 1 - Předmět úpravy</a></div></div></div>
<div class="Frags">
<p class="L1"><a id="f1"></a>NAŘÍZENÍ VLÁDY</p>
<div class="L0"><a id="f2"></a><hr/></div>
<p class="PARA L1"><a id="f3"><i id="p1"></i></a>§ 1</p>
<h3 class="NADPIS L2"><a id="f4"></a>Předmět úpravy</h3>
<p class="L2" onclick="evil()"><var>(1)</var> Text<a class="linknote" href="#f9"><sup>1)</sup></a> s <i>kurzívou</i>.</p>
<p class="L3"><var>a)</var> písmeno <a href="javascript:alert(1)">odkaz</a></p>
<div class="AT L1"><a id="f5"></a></div>
<script>alert(1)</script>
</div></article></body></html>"""

EURLEX_PAGE = """<html><body><div class="panel-body" id="text"><div id="textTabContent">
<table width="100%"><col width="10%"/><tbody><tr>
<td><p class="oj-hd-date">6.4.2021</p></td><td><p class="oj-hd-ti">Official Journal of the European Union</p></td>
</tr></tbody></table>
<hr class="oj-separator"/>
<div class="eli-container">
<div class="eli-main-title"><p class="oj-doc-ti">COMMISSION REGULATION (EU) 2021/535</p></div>
<div class="eli-subdivision"><p class="oj-normal">THE COMMISSION,</p>
<p class="oj-normal">Having regard to the Treaty<a href="#ntr1"><span class="oj-super oj-note-tag">1</span></a>, see <span class="oj-italic">ibid.</span></p></div>
<p class="oj-ti-grseq-1">CHAPTER I</p>
<p class="oj-ti-art">Article 1</p><p class="oj-sti-art">Subject matter</p>
<table border="0"><tbody><tr><td><p class="oj-normal">(a)</p></td><td><p class="oj-normal">first item</p></td></tr></tbody></table>
<table class="oj-table"><tbody><tr class="oj-table"><th class="oj-table"><p class="oj-tbl-hdr">Name</p></th><td colspan="2" class="oj-table"><p class="oj-tbl-txt">Value</p></td></tr></tbody></table>
<p class="oj-image"><img class="oj-img" src="x.png"/></p>
<figure><img src="y.png"/></figure>
</div></div></div></body></html>"""


class ZakonyprolidiTestCase(unittest.TestCase):
    def setUp(self):
        self.result = ef.extract(ZPL_PAGE, "https://www.zakonyprolidi.cz/cs/2016-116")

    def test_source_detected_from_url(self):
        self.assertEqual(self.result.source, "zakonyprolidi")

    def test_levels_headings_and_numbers_are_kept(self):
        h = self.result.html
        self.assertIn('<p class="para">§ 1</p>', h)
        self.assertIn("<h3>Předmět úpravy</h3>", h)
        self.assertIn('<p class="l2"><span class="num">(1)</span> Text<sup>1)</sup> s <em>kurzívou</em>.</p>', h)
        self.assertIn('<p class="l3"><span class="num">a)</span> písmeno odkaz</p>', h)
        self.assertIn("<hr>", h)

    def test_table_of_contents_and_site_chrome_are_not_included(self):
        self.assertNotIn("Obsah", self.result.html)
        self.assertNotIn("Menu", self.result.html)
        self.assertNotIn("Hledání", self.result.html)

    def test_nothing_executable_or_linked_survives(self):
        h = self.result.html
        for forbidden in ("<script", "alert", "onclick", "href", "javascript:", "<a ", "<img", "id="):
            self.assertNotIn(forbidden, h)

    def test_plain_text_has_one_block_per_line(self):
        lines = self.result.text.splitlines()
        self.assertIn("§ 1", lines)
        self.assertIn("(1) Text1) s kurzívou.", lines)


class EurLexTestCase(unittest.TestCase):
    def setUp(self):
        self.result = ef.extract(EURLEX_PAGE, "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32021R0535")

    def test_page_header_table_and_separator_are_dropped(self):
        self.assertNotIn("Official Journal", self.result.html)
        self.assertNotIn("6.4.2021", self.result.html)
        self.assertNotIn("<hr>", self.result.html)

    def test_titles_headings_and_inline_marks(self):
        h = self.result.html
        self.assertIn('<p class="title">COMMISSION REGULATION (EU) 2021/535</p>', h)
        self.assertIn("<h3>CHAPTER I</h3>", h)
        self.assertIn("<h4>Article 1</h4>", h)
        self.assertIn("<h4>Subject matter</h4>", h)
        self.assertIn("Treaty<sup>1</sup>, see <em>ibid.</em>", h)

    def test_enumeration_table_becomes_an_item_paragraph_and_data_table_keeps_spans(self):
        h = self.result.html
        self.assertIn('<p class="item d0"><span class="num">(a)</span>first item</p>', h)
        self.assertNotIn('<table class="layout">', h)
        self.assertIn('<table class="data">', h)
        self.assertIn('<td colspan="2">', h)
        self.assertIn("<th><p>Name</p></th>", h.replace(' class="oj-tbl-hdr"', ""))

    def test_item_text_reads_as_one_line_data_table_uses_bars(self):
        lines = self.result.text.splitlines()
        self.assertIn("(a) first item", lines)
        self.assertIn("Name | Value", lines)

    def test_nested_enumerations_are_one_level_deeper_with_continuation_text(self):
        page = ('<div id="text"><div class="eli-container">'
                '<table><tr><td><p class="oj-normal">(1)</p></td><td>'
                '<p class="oj-normal">Main point:</p>'
                '<table><tr><td><p class="oj-normal">(a)</p></td><td><p class="oj-normal">sub point</p></td></tr></table>'
                '<p class="oj-normal">closing words</p>'
                '</td></tr></table></div></div>')
        r = ef.extract(page, "https://eur-lex.europa.eu/x")
        self.assertEqual(r.html.split("\n"), [
            '<p class="item d0"><span class="num">(1)</span>Main point:</p>',
            '<p class="item d1"><span class="num">(a)</span>sub point</p>',
            '<p class="d1">closing words</p>'])
        self.assertEqual(r.text.splitlines(), ["(1) Main point:", "(a) sub point", "closing words"])

    def test_leading_empty_cell_is_an_indentation_spacer(self):
        page = ('<div id="text"><div class="eli-container"><table><tr><td></td>'
                '<td><p class="oj-normal">(1)</p></td><td><p class="oj-normal">indented item</p></td>'
                '</tr></table></div></div>')
        r = ef.extract(page, "https://eur-lex.europa.eu/x")
        self.assertEqual(r.html, '<p class="item d1"><span class="num">(1)</span>indented item</p>')

    def test_layout_table_that_is_not_an_enumeration_stays_a_table(self):
        page = ('<div id="text"><div class="eli-container"><table><tr>'
                '<td><p class="oj-normal">A long first column that is real content</p></td>'
                '<td><p class="oj-normal">second</p></td></tr></table></div></div>')
        r = ef.extract(page, "https://eur-lex.europa.eu/x")
        self.assertIn('<table class="layout">', r.html)
        self.assertNotIn("item", r.html)

    def test_images_are_dropped(self):
        self.assertNotIn("img", self.result.html)
        self.assertNotIn("<p></p>", self.result.html)

    def test_search_results_page_is_rejected_not_extracted(self):
        page = '<html><body><div id="text"><p>Search results - EUR-Lex</p></div></body></html>'
        with self.assertRaises(ef.ExtractionError):
            ef.extract(page, "https://eur-lex.europa.eu/search.html")


class DispatchTestCase(unittest.TestCase):
    def test_unsupported_domain_is_reported_not_guessed(self):
        with self.assertRaises(ef.Unsupported):
            ef.extract(ZPL_PAGE, "https://www.technicke-normy-csn.cz/csn-en-17127")

    def test_empty_slovlex_style_shell_is_unsupported_without_url(self):
        with self.assertRaises(ef.Unsupported):
            ef.extract("<html><body><app-root></app-root></body></html>")

    def test_source_is_sniffed_from_the_page_when_there_is_no_url(self):
        self.assertEqual(ef.extract(ZPL_PAGE).source, "zakonyprolidi")
        self.assertEqual(ef.extract(EURLEX_PAGE).source, "eurlex")

    def test_empty_text_container_is_an_error(self):
        page = '<article id="idBody_idCtn"><div class="Frags"></div></article>'
        with self.assertRaises(ef.ExtractionError):
            ef.extract(page, "https://www.zakonyprolidi.cz/cs/2016-116")


class RunTestCase(unittest.TestCase):
    def _repo(self, tmp):
        root = pathlib.Path(tmp)
        (root / "data" / "fulltext" / "S").mkdir(parents=True)
        files = {"a.html": ZPL_PAGE, "b.html": EURLEX_PAGE,
                 "c.html": "<html><div id='text'>Search results</div></html>",
                 "d.html": "<html><app-root></app-root></html>"}
        for name, body in files.items():
            (root / "data" / "fulltext" / "S" / name).write_text(body, encoding="utf-8")
        manifest = {
            "k|a": {"status": "fetched", "local_path": "data/fulltext/S/a.html", "url": "https://www.zakonyprolidi.cz/cs/x"},
            "k|b": {"status": "fetched", "local_path": "data/fulltext/S/b.html", "url": "https://eur-lex.europa.eu/x"},
            "k|c": {"status": "fetched", "local_path": "data/fulltext/S/c.html", "url": "https://eur-lex.europa.eu/search"},
            "k|d": {"status": "fetched", "local_path": "data/fulltext/S/d.html", "url": "https://www.technicke-normy-csn.cz/x"},
            "k|e": {"status": "fetched", "local_path": "data/fulltext/S/e.pdf", "url": "https://eur-lex.europa.eu/pdf"},
            "k|f": {"status": "failed", "local_path": "", "url": "https://eur-lex.europa.eu/y"},
        }
        manifest_path = root / "data" / "fulltext_manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        return root, manifest_path

    def test_dry_run_counts_everything_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, manifest_path = self._repo(tmp)
            out = root / "data" / "fulltext_clean"
            with mock.patch.dict(sys.modules, {"pymupdf": None}):  # as in the project venv
                stats, problems = ef.run(apply=False, manifest_path=manifest_path, output_dir=out, repo_root=root)
            self.assertEqual(stats["extracted: zakonyprolidi"], 1)
            self.assertEqual(stats["extracted: eurlex"], 1)
            self.assertEqual(stats["failed"], 1)
            self.assertEqual(stats["skipped: unsupported source: www.technicke-normy-csn.cz"], 1)
            self.assertEqual(stats["skipped: not a fetched HTML or PDF file"], 1)
            self.assertEqual(stats["skipped: PDF without an HTML twin, PyMuPDF is not installed"], 1)
            self.assertEqual([k for k, _ in problems], ["k|c"])
            self.assertFalse(out.exists())

    def test_apply_writes_html_and_txt_mirroring_the_download_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, manifest_path = self._repo(tmp)
            out = root / "data" / "fulltext_clean"
            ef.run(apply=True, manifest_path=manifest_path, output_dir=out, repo_root=root)
            self.assertIn("§ 1", (out / "S" / "a.txt").read_text(encoding="utf-8"))
            self.assertIn("<h3>Předmět úpravy</h3>", (out / "S" / "a.html").read_text(encoding="utf-8"))
            self.assertTrue((out / "S" / "b.html").exists())
            self.assertFalse((out / "S" / "c.html").exists())


SLOVLEX_PAGE = """<html><head><title>124/2000 Z. z. Vyhláška</title></head><body><div class="menu">Prihlásenie</div>
<div class="predpis Skupina">
<div class="predpisOznacenie">124</div><div class="predpisTyp">VYHLÁŠKA</div>
<div class="predpisPodnadpis">Ministerstva vnútra</div><div class="predpisDatum">z 20. marca 2000,</div>
<div class="predpisNadpis NADPIS">ktorou sa ustanovujú zásady</div>
<div class="predpisText">Ministerstvo ustanovuje:<a class="citacnyOdkazJednoduchy" href="#x">odkaz</a></div>
<div class="utilities-addition"><div class="cast Skupina">
  <div class="castOznacenie">PRVÁ ČASŤ</div><div class="castNadpis NADPIS">ZÁKLADNÉ USTANOVENIA</div>
  <div class="utilities-addition"><div class="paragraf Skupina">
    <div class="paragrafOznacenie">§ 1</div><div class="paragrafNadpis NADPIS">Predmet úpravy</div>
    <div class="utilities-addition"><div class="odsek Skupina">
      <div class="odsekOznacenie">(1)</div><div class="text">Táto vyhláška upravuje<sup>1</sup>) pri</div>
      <div class="pismeno Skupina"><div class="pismenoOznacenie">a)</div><div class="text">výstavbe <img class="tooltip-fragment" src="x.svg"></div>
        <div class="bod Skupina"><div class="bodOznacenie">1.</div><div class="text">podbod</div></div></div>
    </div></div>
  </div></div>
  <div class="paragraf Skupina"><div class="paragrafOznacenie">§ 2</div><div class="text">Táto vyhláška nadobúda účinnosť.</div></div>
</div></div>
<div class="text2">Ladislav Pittner v. r.</div>
</div></body></html>"""


class SlovLexTestCase(unittest.TestCase):
    def setUp(self):
        self.result = ef.extract(SLOVLEX_PAGE, "https://www.slov-lex.sk/pravne-predpisy/SK/ZZ/2000/124/")

    def test_source_is_detected_from_the_host_and_from_the_page(self):
        self.assertEqual(self.result.source, "slovlex")
        self.assertEqual(ef.extract(SLOVLEX_PAGE).source, "slovlex")

    def test_header_formula_and_signature_are_kept_without_the_site_chrome(self):
        h = self.result.html
        self.assertIn('<p class="title">VYHLÁŠKA</p>', h)
        self.assertIn('<p class="title">ktorou sa ustanovujú zásady</p>', h)
        self.assertIn("<p>Ministerstvo ustanovuje:odkaz</p>", h)
        self.assertIn('<p class="center">Ladislav Pittner v. r.</p>', h)
        self.assertNotIn("Prihlásenie", h)

    def test_parts_found_through_wrapper_divs_are_not_lost(self):
        h = self.result.html
        self.assertIn("<h3>PRVÁ ČASŤ</h3>", h)
        self.assertIn("<h3>ZÁKLADNÉ USTANOVENIA</h3>", h)
        self.assertIn('<p class="para">§ 1</p>', h)
        self.assertIn("<h4>Predmet úpravy</h4>", h)

    def test_items_nest_one_level_deeper_each(self):
        h = self.result.html
        self.assertIn('<p class="item d0"><span class="num">(1)</span>Táto vyhláška upravuje<sup>1</sup>) pri</p>', h)
        self.assertIn('<p class="item d1"><span class="num">a)</span>výstavbe</p>', h)
        self.assertIn('<p class="item d2"><span class="num">1.</span>podbod</p>', h)

    def test_a_section_with_no_subsections_keeps_its_text(self):
        self.assertIn("<p>Táto vyhláška nadobúda účinnosť.</p>", self.result.html)

    def test_nothing_executable_or_linked_survives(self):
        for forbidden in ("<script", "<a ", "href", "<img", "tooltip", "class=\"predpis"):
            self.assertNotIn(forbidden, self.result.html)

    def test_plain_text_reads_marker_then_text(self):
        lines = self.result.text.splitlines()
        self.assertIn("(1) Táto vyhláška upravuje1) pri", lines)
        self.assertIn("a) výstavbe", lines)

    def test_the_empty_angular_shell_is_an_error_not_an_empty_text(self):
        with self.assertRaises(ef.ExtractionError):
            ef.extract("<html><body><app-root></app-root></body></html>", "https://www.slov-lex.sk/pravne-predpisy/SK/ZZ/2000/124/")

    def test_a_history_page_is_an_error(self):
        page = "<html><body><table><tr class='effectivenessHistoryItem'><td>1.</td></tr></table></body></html>"
        with self.assertRaises(ef.ExtractionError):
            ef.extract(page, "https://www.slov-lex.sk/pravne-predpisy/SK/ZZ/2004/96/")


CONSOLIDATED_PAGE = """<html><head><title>TEXT v úplném znění</title></head><body><div class="Wrapper"><div class="eli-container">
<p><br/></p><p class="arrow">▼B <a class="anchorarrow" href="#B-2"><i class="fa"></i></a></p>
<div class="eli-main-title"><p class="title-doc-first">NAŘÍZENÍ (EU) 2022/869</p><p class="title-doc-last">kterým se stanoví hlavní směry</p></div>
<div class="eli-subdivision"><div id="cpt_I">
  <p class="title-division-1"><span class="italics">KAPITOLA I</span></p>
  <p class="title-division-2"><span class="boldface">Obecná ustanovení</span></p>
  <div class="eli-subdivision"><p class="title-article-norm">Článek 1</p>
    <div class="eli-title"><p class="stitle-article-norm">Předmět</p></div>
    <div class="norm"><span class="no-parag">1. </span><div class="norm inline-element">Toto nařízení stanoví<a href="#E1"><span class="superscript">1</span></a> hlavní směry.</div></div>
    <div class="norm"><span class="no-parag">2. </span><div class="norm inline-element">Toto nařízení zejména:</div></div>
    <div class="grid-container grid-list"><div class="list grid-list-column-1"><span>a) </span></div>
      <div class="grid-list-column-2"><p class="norm">určuje projekty,</p></div></div>
  </div>
  <div class="eli-subdivision"><p class="title-article-norm">Článek 2</p>
    <p class="norm">Pro účely tohoto nařízení se rozumí:</p>
    <div class="grid-container grid-list"><div class="list grid-list-column-1"><span>1) </span></div>
      <div class="grid-list-column-2"><p class="norm">„projektem“ jedno vedení;</p></div></div>
    <table class="borderOj"><tbody><tr><td><p class="tbl-norm">A</p></td><td><p class="tbl-norm">B</p></td></tr></tbody></table>
    <p class="footnote">(1) Nařízení (EU) 2018/1999.</p>
  </div>
</div></div>
<div id="anx_I"><hr class="separator-annex"/><p class="title-annex-1">PŘÍLOHA I</p><p class="title-annex-2"><span class="norm">PRIORITNÍ KORIDORY</span></p>
  <p class="norm">Toto nařízení se vztahuje na tyto koridory:</p></div>
<p class="modref">next</p>
</div></div></body></html>"""


class ConsolidatedEurLexTestCase(unittest.TestCase):
    def setUp(self):
        self.result = ef.extract(CONSOLIDATED_PAGE, "https://eur-lex.europa.eu/legal-content/CS/TXT/HTML/?uri=CELEX:02022R0869-20250205")

    def test_page_without_div_text_is_read_from_the_eli_container(self):
        self.assertEqual(self.result.source, "eurlex")
        self.assertIn('<p class="title">NAŘÍZENÍ (EU) 2022/869</p>', self.result.html)

    def test_amendment_markers_are_dropped(self):
        for marker in ("▼B", "next", "arrow", "modref"):
            self.assertNotIn(marker, self.result.html)

    def test_chapters_articles_and_annexes_become_headings(self):
        h = self.result.html
        self.assertIn("<h3><em>KAPITOLA I</em></h3>", h)
        self.assertIn("<h4>Článek 1</h4>", h)
        self.assertIn("<h4>Předmět</h4>", h)
        self.assertIn("<h3>PŘÍLOHA I</h3>", h)
        self.assertIn("<hr>", h)

    def test_numbered_paragraphs_and_grid_lists_are_items(self):
        h = self.result.html
        self.assertIn('<p class="item d0"><span class="num">1.</span>Toto nařízení stanoví<sup>1</sup> hlavní směry.</p>', h)
        self.assertIn('<p class="item d0"><span class="num">2.</span>Toto nařízení zejména:</p>', h)
        self.assertIn('<p class="item d0"><span class="num">a)</span>určuje projekty,</p>', h)
        self.assertIn('<p class="item d0"><span class="num">1)</span>„projektem“ jedno vedení;</p>', h)

    def test_plain_paragraph_note_and_data_table(self):
        h = self.result.html
        self.assertIn("<p>Pro účely tohoto nařízení se rozumí:</p>", h)
        self.assertIn('<p class="note">(1) Nařízení (EU) 2018/1999.</p>', h)
        self.assertIn('<table class="data">', h)

    def test_nothing_executable_or_linked_survives(self):
        for forbidden in ("<script", "<a ", "href", "<i ", "anchorarrow"):
            self.assertNotIn(forbidden, self.result.html)

    def test_a_search_page_without_any_act_markup_is_still_rejected(self):
        page = "<html><head><title>Search results - EUR-Lex</title></head><body><div class='Wrapper'><p>0 results</p></div></body></html>"
        with self.assertRaises(ef.ExtractionError):
            ef.extract(page, "https://eur-lex.europa.eu/legal-content/CS/TXT/HTML/?uri=CELEX:1")


class PdfTwinNamingTestCase(unittest.TestCase):
    MANIFEST = {
        "S|A 1|odkaz_hlavni": {"status": "fetched", "local_path": "data/fulltext/A_1__11111111.pdf"},
        "S|A 1|odkaz_hlavni_html": {"status": "fetched", "local_path": "data/fulltext/A_1__22222222.html"},
        "S|B 2|odkaz_hlavni_html": {"status": "fetched", "local_path": "data/fulltext/B_2__33333333.html"},
        "S|C 3|odkaz_hlavni": {"status": "failed"},
        "S|C 3|odkaz_hlavni_html": {"status": "fetched", "local_path": "data/fulltext/C_3__44444444.html"},
    }

    def name(self, key):
        return ef.clean_name_source(key, self.MANIFEST[key], self.MANIFEST)

    def test_the_html_twin_of_a_pdf_takes_the_pdfs_name(self):
        self.assertEqual(self.name("S|A 1|odkaz_hlavni_html"), "data/fulltext/A_1__11111111.pdf")

    def test_a_plain_download_keeps_its_own_name(self):
        manifest = {"S|D 4|odkaz_hlavni": {"status": "fetched", "local_path": "data/fulltext/D_4__55555555.html"}}
        self.assertEqual(ef.clean_name_source("S|D 4|odkaz_hlavni", manifest["S|D 4|odkaz_hlavni"], manifest),
                         "data/fulltext/D_4__55555555.html")

    def test_a_twin_without_a_fetched_pdf_keeps_its_own_name(self):
        self.assertEqual(self.name("S|B 2|odkaz_hlavni_html"), "data/fulltext/B_2__33333333.html")
        self.assertEqual(self.name("S|C 3|odkaz_hlavni_html"), "data/fulltext/C_3__44444444.html")

    def test_run_writes_the_text_under_the_pdfs_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "data" / "fulltext").mkdir(parents=True)
            (root / "data/fulltext/A_1__11111111.pdf").write_bytes(b"%PDF-1.4 x")
            (root / "data/fulltext/A_1__22222222.html").write_text(CONSOLIDATED_PAGE, encoding="utf-8")
            manifest = {
                "S|A 1|odkaz_hlavni": {"status": "fetched", "local_path": "data/fulltext/A_1__11111111.pdf",
                                       "url": "https://eur-lex.europa.eu/legal-content/CS/TXT/PDF/?uri=CELEX:1"},
                "S|A 1|odkaz_hlavni_html": {"status": "fetched", "local_path": "data/fulltext/A_1__22222222.html",
                                            "url": "https://eur-lex.europa.eu/legal-content/CS/TXT/HTML/?uri=CELEX:1"}}
            manifest_path = root / "data" / "fulltext_manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            out = root / "data" / "fulltext_clean"
            stats, problems = ef.run(apply=True, manifest_path=manifest_path, output_dir=out, repo_root=root)
            self.assertEqual(problems, [])
            self.assertEqual(stats["extracted: eurlex"], 1)
            self.assertIn("Článek 1", (out / "A_1__11111111.txt").read_text(encoding="utf-8"))
            self.assertTrue((out / "A_1__11111111.html").exists())
            self.assertFalse((out / "A_1__22222222.html").exists())


LEGACY_PAGE = ("<html><head><title>EUR-Lex - 31999L0092 - EN</title></head><body><div class='bgtool'>tools</div><h1>menu</h1>"
               "<p class='bglang'><a href='x'><b>Avis juridique important</b></a></p><p> <txt_te> </txt_te></p>"
               "<p>DIRECTIVE 1999/92/EC OF THE EUROPEAN PARLIAMENT AND OF THE COUNCIL</p><p>of 16 December 1999</p>"
               + "".join(f"<p>1.{i} Paragraph number {i} of the directive text.</p>" for i in range(30))
               + "</body></html>")


class LegacyEurLexTestCase(unittest.TestCase):
    def test_a_pre_2004_page_is_read_as_plain_paragraphs_without_the_site_chrome(self):
        r = ef.extract(LEGACY_PAGE, "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:31999L0092")
        self.assertEqual(r.source, "eurlex")
        self.assertIn("<p>DIRECTIVE 1999/92/EC OF THE EUROPEAN PARLIAMENT AND OF THE COUNCIL</p>", r.html)
        self.assertIn("<p>1.7 Paragraph number 7 of the directive text.</p>", r.html)
        for chrome in ("Avis juridique", "tools", "menu", "txt_te"):
            self.assertNotIn(chrome, r.html)

    def test_the_same_plain_text_inside_the_current_page_chrome_is_read_too(self):
        page = ("<html><head><title>Directive - 1999/31 - EN - EUR-Lex</title></head><body><div class='ecl-site-header'>nav</div>"
                "<div id='text'><div class='tabContent'><p class='bglang'><b>Avis juridique important</b></p>"
                "<p>COUNCIL DIRECTIVE 1999/31/EC</p>"
                + "".join(f"<p>Article {i}. Text of the article number {i}.</p>" for i in range(30))
                + "</div></div><div class='ecl-site-footer'>footer</div></body></html>")
        r = ef.extract(page, "https://eur-lex.europa.eu/eli/dir/1999/31/oj")
        self.assertIn("<p>Article 7. Text of the article number 7.</p>", r.html)
        for chrome in ("Avis juridique", "nav", "footer"):
            self.assertNotIn(chrome, r.html)

    def test_a_short_page_with_the_same_title_shape_is_not_taken_for_an_act(self):
        page = "<html><head><title>EUR-Lex - 31999L0092 - EN</title></head><body><p>not found</p></body></html>"
        with self.assertRaises(ef.ExtractionError):
            ef.extract(page, "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:31999L0092")


class PdfRunTestCase(unittest.TestCase):
    def _manifest(self, root, entries):
        (root / "data" / "fulltext").mkdir(parents=True)
        manifest_path = root / "data" / "fulltext_manifest.json"
        manifest_path.write_text(json.dumps(entries), encoding="utf-8")
        return manifest_path

    def test_a_pdf_without_a_twin_is_extracted_once_under_its_own_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            entry = {"status": "fetched", "local_path": "data/fulltext/url-1__ab.pdf", "url": "https://x/a.pdf"}
            path = self._manifest(root, {"s|url-1|odkaz_hlavni": entry, "s|url-1|odkaz_eu": dict(entry)})
            result = ef.Extracted('<p class="para">Text</p>', "Text\n", "pdf")
            with mock.patch.object(ef, "_extract_pdf", return_value=result) as extract:
                stats, problems = ef.run(apply=True, manifest_path=path, output_dir=root / "out", repo_root=root)
            self.assertEqual(extract.call_count, 1)
            self.assertEqual((stats["extracted: pdf"], stats["skipped: the same PDF under another field"]), (1, 1))
            self.assertEqual((root / "out" / "url-1__ab.txt").read_text(encoding="utf-8"), "Text\n")
            self.assertEqual(problems, [])

    def test_a_pdf_whose_html_twin_was_fetched_is_left_to_the_twin(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            pdf = {"status": "fetched", "local_path": "data/fulltext/A__ab.pdf", "url": "https://eur-lex.europa.eu/pdf"}
            twin = {"status": "fetched", "local_path": "data/fulltext/A__cd.html", "url": "https://eur-lex.europa.eu/h"}
            path = self._manifest(root, {"s|A|odkaz_hlavni": pdf, "s|A|odkaz_hlavni_html": twin})
            (root / "data" / "fulltext" / "A__cd.html").write_text(EURLEX_PAGE, encoding="utf-8")
            with mock.patch.object(ef, "_extract_pdf") as extract:
                stats, _ = ef.run(apply=True, manifest_path=path, output_dir=root / "out", repo_root=root)
            extract.assert_not_called()
            self.assertEqual((stats["skipped: PDF with an HTML twin"], stats["extracted: eurlex"]), (1, 1))
            self.assertTrue((root / "out" / "A__ab.html").exists())  # the twin's text carries the PDF's name

    def test_a_pdf_that_cannot_be_read_is_a_problem_not_a_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            entry = {"status": "fetched", "local_path": "data/fulltext/scan.pdf", "url": "https://x/scan.pdf"}
            path = self._manifest(root, {"s|url-2|odkaz_hlavni": entry})
            with mock.patch.object(ef, "_extract_pdf", side_effect=ef.ExtractionError("no text layer")):
                stats, problems = ef.run(apply=False, manifest_path=path, output_dir=root / "out", repo_root=root)
            self.assertEqual((stats["failed"], problems), (1, [("s|url-2|odkaz_hlavni", "no text layer")]))


WORD_PAGE = """<html><head><title>IMMC.COM.docx</title></head><body><div class="contentWrapper">
<div class="content"><p class="Logo"><img src="data:image/png;base64,AAAA"/>
EVROPSKÁ KOMISE</p></div>
<div class="content"><p class="Emission">V Bruselu dne 8.7.2020</p><p class="Typedudocument_cp">SDĚLENÍ KOMISE</p>
<p class="Titreobjet_cp">Vodíková strategie</p></div>
<div class="content"><p class="li Heading1"><span class="num">1.</span><span class="tab"> </span>Úvod</p>
<p class="Normal">Vodík se těší pozornosti<a class="footnoteRef" href="#f1">1</a>.</p><p class="Normal"> </p>
<p class="li ListParagraph"><span class="list-symbol">-</span>první bod</p>
<p class="Heading2">Podkapitola</p>
<table><tr><td><p class="Normal">buňka A</p></td><td><p class="Normal">buňka B</p></td></tr></table>
<p class="FootnoteText"><a class="footnote" href="#r1"></a>Poznámka pod čarou.</p></div></div></body></html>"""


class WordDocumentTestCase(unittest.TestCase):
    def test_a_converted_word_file_gives_the_text_in_the_closed_vocabulary(self):
        result = ef.extract(WORD_PAGE, "https://eur-lex.europa.eu/legal-content/CS/TXT/HTML/?uri=CELEX:52020DC0301")
        self.assertEqual(result.source, "eurlex")
        lines = result.html.split("\n")
        self.assertEqual(lines[0], '<p class="center">EVROPSKÁ KOMISE</p>')
        self.assertIn('<p class="title">SDĚLENÍ KOMISE</p>', lines)
        self.assertIn("<h3>1. Úvod</h3>", lines)
        self.assertIn('<p class="para">Vodík se těší pozornosti<sup>1</sup>.</p>', lines)
        self.assertIn('<p class="item d0"><span class="num">-</span>první bod</p>', lines)
        self.assertIn("<h4>Podkapitola</h4>", lines)
        self.assertIn('<p class="note"><span class="num">1</span> Poznámka pod čarou.</p>', lines)
        self.assertEqual(result.html.count("<table"), 1)
        self.assertNotIn("img", result.html)
        self.assertNotIn("data:", result.text)

    def test_the_source_is_recognised_without_an_address_too(self):
        self.assertEqual(ef.extract(WORD_PAGE).source, "eurlex")


if __name__ == "__main__":
    unittest.main()
