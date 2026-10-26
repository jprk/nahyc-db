import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src" / "tools"))
import pdf_text as pt
from extract_fulltext import ExtractionError

try:
    import pymupdf
except ImportError:
    pymupdf = None

PITCH = 20.0


def line(text, y, x0=60.0, size=12.0, bold=False, x1=500.0, page=0):
    return pt.Line(text, size, bold, x0, y, x1, y + 13.0, page)


def body(pages):
    return pt.build_blocks(pages, 12.0, PITCH)


class RunningLinesTestCase(unittest.TestCase):
    def pages(self):
        return [[line("30.12.2006 CS Úřední věstník L 396/%d" % n, 20), line(str(n + 1), 800), line("text %d" % n, 300)]
                for n in range(6)]

    def test_a_repeated_margin_line_and_page_numbers_are_dropped_the_body_stays(self):
        kept = pt.drop_running_lines(self.pages(), [842.0] * 6)
        self.assertEqual([[l.text for l in lines] for lines in kept], [["text %d" % n] for n in range(6)])

    def test_a_margin_line_that_appears_once_is_kept(self):
        pages = self.pages()
        pages[2].append(line("Unique footnote", 790))
        kept = pt.drop_running_lines(pages, [842.0] * 6)
        self.assertIn("Unique footnote", [l.text for l in kept[2]])

    def test_the_margin_is_measured_in_points_so_a_landscape_page_works_too(self):
        pages = [[line("Header", 50), line("body", 300)] for _ in range(4)]
        kept = pt.drop_running_lines(pages, [595.0] * 4)
        self.assertEqual([[l.text for l in lines] for lines in kept], [["body"]] * 4)


class MarkerLinesTestCase(unittest.TestCase):
    def test_a_marker_on_the_baseline_of_the_text_becomes_one_line(self):
        merged = pt.merge_marker_lines([line("(48)", 100, x0=57, x1=80), line("Tímto nařízením", 100, x0=99)])
        self.assertEqual([(l.text, l.x0) for l in merged], [("(48) Tímto nařízením", 57)])

    def test_a_marker_without_text_next_to_it_stays(self):
        merged = pt.merge_marker_lines([line("(48)", 100, x1=80), line("Další odstavec", 140, x0=99)])
        self.assertEqual(len(merged), 2)


class BlocksTestCase(unittest.TestCase):
    def test_lines_at_the_normal_pitch_make_one_paragraph_with_a_hyphenated_word_joined(self):
        blocks = body([[line("Toto je první řádek odstavce roz-", 100), line("dělený na dva řádky.", 100 + PITCH)]])
        self.assertEqual(blocks, [("p", "Toto je první řádek odstavce rozdělený na dva řádky.")])

    def test_a_larger_gap_starts_a_new_paragraph(self):
        blocks = body([[line("První odstavec", 100), line("Druhý odstavec", 100 + 2 * PITCH)]])
        self.assertEqual([b[1] for b in blocks], ["První odstavec", "Druhý odstavec"])

    def test_a_short_line_that_ended_a_sentence_ends_the_paragraph(self):
        blocks = body([[line("Konec odstavce.", 100, x1=200), line("Nový odstavec začíná.", 100 + PITCH, x1=500),
                        line("a pokračuje dál", 100 + 2 * PITCH, x1=500)]])
        self.assertEqual([b[1] for b in blocks], ["Konec odstavce.", "Nový odstavec začíná. a pokračuje dál"])

    def test_a_list_item_has_its_marker_depth_and_continuation_lines(self):
        blocks = body([[line("(1) První bod", 100), line("pokračuje", 100 + PITCH),
                        line("a) vnořený bod", 100 + 2 * PITCH, x0=96)]])
        self.assertEqual(blocks, [("item", "První bod pokračuje", "(1)", 0), ("item", "vnořený bod", "a)", 2)])

    def test_a_larger_font_is_a_heading_and_a_bold_phrase_inside_a_paragraph_is_not(self):
        blocks = body([[line("KAPITOLA 1", 100, size=18.0), line("Text odstavce", 100 + 2 * PITCH),
                        line("tučná fráze uvnitř", 100 + 3 * PITCH, bold=True), line("odstavce dál.", 100 + 4 * PITCH)]])
        self.assertEqual(blocks[0], ("h3", "KAPITOLA 1"))
        self.assertEqual(blocks[1][0], "p")
        self.assertEqual(len(blocks), 2)

    def test_a_short_bold_line_standing_apart_is_a_heading(self):
        blocks = body([[line("Text před", 100), line("Úvod", 100 + 2 * PITCH, bold=True),
                        line("Text za", 100 + 4 * PITCH)]])
        self.assertEqual([b[0] for b in blocks], ["p", "h4", "p"])

    def test_an_article_number_and_the_title_line_below_it_are_one_heading(self):
        blocks = body([[line("Článek 3", 100, x0=250), line("Definice", 100 + PITCH, x0=270),
                        line("Pro účely tohoto nařízení se rozumí:", 100 + 3 * PITCH)]])
        self.assertEqual([b[:2] for b in blocks], [("h4", "Článek 3 Definice"), ("p", "Pro účely tohoto nařízení se rozumí:")])

    def test_an_unfinished_paragraph_goes_on_over_a_page_break(self):
        blocks = body([[line("Odstavec, který pokračuje", 700)], [line("na další stránce.", 80, page=1)]])
        self.assertEqual(blocks, [("p", "Odstavec, který pokračuje na další stránce.")])

    def test_a_finished_paragraph_does_not_continue_on_the_next_page(self):
        blocks = body([[line("Hotový odstavec.", 700)], [line("na další stránce.", 80, page=1)]])
        self.assertEqual(len(blocks), 2)

    def test_a_table_stays_a_block_between_the_text(self):
        blocks = body([[line("Před", 100), ("table", [["a", "b"], ["c", "d"]]), line("Za", 300)]])
        self.assertEqual([b[0] for b in blocks], ["p", "table", "p"])


class RenderTestCase(unittest.TestCase):
    def test_the_vocabulary_is_the_closed_one_and_the_text_is_escaped(self):
        fragment = pt.render([("h3", "A & B"), ("h4", "<x>"), ("p", "a < b"), ("item", "text", "(1)", 1),
                              ("table", [["1", "<2>"]])])
        self.assertEqual(fragment.split("\n"), [
            "<h3>A &amp; B</h3>", "<h4>&lt;x&gt;</h4>", '<p class="para">a &lt; b</p>',
            '<p class="item d1"><span class="num">(1)</span>text</p>',
            '<table class="data"><tr><td>1</td><td>&lt;2&gt;</td></tr></table>'])


@unittest.skipIf(pymupdf is None, "PyMuPDF is not installed")
class ExtractPdfTestCase(unittest.TestCase):
    def make_pdf(self, path, pages):
        document = pymupdf.open()
        for texts in pages:
            page = document.new_page()
            y = 90
            for size, text in texts:
                page.insert_text((60, y), text, fontsize=size)
                y += size * 1.8
        document.save(path)

    def test_a_pdf_with_a_text_layer_gives_headings_and_paragraphs(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "a.pdf"
            self.make_pdf(path, [[(20, "Vodikova strategie"), (11, "Prvni radek odstavce"), (11, "druhy radek odstavce.")]] * 2)
            result = pt.extract_pdf(path, tables=False)
        self.assertEqual(result.source, "pdf")
        self.assertIn("<h3>Vodikova strategie</h3>", result.html)
        self.assertIn("Prvni radek odstavce druhy radek odstavce.", result.text)

    def test_a_pdf_without_text_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "scan.pdf"
            document = pymupdf.open()
            document.new_page()
            document.save(path)
            with self.assertRaises(ExtractionError):
                pt.extract_pdf(path)

    def test_a_damaged_file_is_an_extraction_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "broken.pdf"
            path.write_bytes(b"not a pdf")
            with self.assertRaises(ExtractionError):
                pt.extract_pdf(path)


if __name__ == "__main__":
    unittest.main()
