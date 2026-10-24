"""Tests for src/tools/extract_fulltext.py (GitHub issue #2): clean text out
of whole-page downloads. Synthetic pages only — the real downloads under
data/fulltext/ are gitignored, so nothing here depends on them."""
import json
import pathlib
import sys
import tempfile
import unittest

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

    def test_enumeration_table_is_layout_and_data_table_keeps_spans(self):
        h = self.result.html
        self.assertIn('<table class="layout">', h)
        self.assertIn('<table class="data">', h)
        self.assertIn('<td colspan="2">', h)
        self.assertIn("<th><p>Name</p></th>", h.replace(' class="oj-tbl-hdr"', ""))

    def test_layout_table_text_reads_as_one_line_data_table_uses_bars(self):
        lines = self.result.text.splitlines()
        self.assertIn("(a) first item", lines)
        self.assertIn("Name | Value", lines)

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
            ef.extract(ZPL_PAGE, "https://www.slov-lex.sk/pravne-predpisy/SK/ZZ/2006/124/")

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
            "k|d": {"status": "fetched", "local_path": "data/fulltext/S/d.html", "url": "https://www.slov-lex.sk/x"},
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
            stats, problems = ef.run(apply=False, manifest_path=manifest_path, output_dir=out, repo_root=root)
            self.assertEqual(stats["extracted: zakonyprolidi"], 1)
            self.assertEqual(stats["extracted: eurlex"], 1)
            self.assertEqual(stats["failed"], 1)
            self.assertEqual(stats["skipped: unsupported source: www.slov-lex.sk"], 1)
            self.assertEqual(stats["skipped: not a fetched HTML file"], 2)
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


if __name__ == "__main__":
    unittest.main()
