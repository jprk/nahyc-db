"""Clean text out of a text-layer PDF, in the closed HTML vocabulary of
extract_fulltext.py (headings, paragraphs, list items, tables).

Used for the documents whose only full text is a PDF without an HTML twin:
strategies, studies, methodologies, and the Official Journal regulations whose
page EUR-Lex does not render (REACH, CLP). The PDF itself is never touched and
stays the download; this builds the readable view of it.

PDF has no paragraphs, only positioned lines, so the structure is rebuilt from
geometry and fonts and is therefore a best effort, never a claim about the
document: running headers and footers (a line that repeats, digits aside, in the
top or bottom margin of many pages) and bare page numbers are dropped; the most
common font size is the body text and a clearly larger (or short bold) line is a
heading; a line starts a new paragraph after a vertical gap, after a short
(justified-text) line that ended a sentence, or when it begins with a list marker;
a hyphenated word at a line end is joined; a paragraph that breaks across a page
is joined; tables found by PyMuPDF become `table.data`, and the lines inside them
are not repeated as text. A PDF without a text layer (a scan) is refused, not
OCR'd or guessed at.

Needs PyMuPDF (`pymupdf`, AGPL), imported only when a PDF is opened: the
functions that rebuild the structure from `Line`s work without it. The project
venv does not have it; run the extraction with an interpreter that has it, e.g.
`~/.cache/lit-tools/bin/python src/tools/extract_fulltext.py --apply`.
"""
import collections
import html
import re

from extract_fulltext import Extracted, ExtractionError, html_to_text

Line = collections.namedtuple("Line", "text size bold x0 y0 x1 y1 page vertical", defaults=(False,))

MARGIN = 62               # points from the top/bottom edge of a page where running lines live
RUNNING_SHARE = 0.25      # a margin line on this share of the pages (and at least 3) is a running one
HEADING_RATIO = 1.12      # a line this much larger than the body is a heading ...
BIG_HEADING_RATIO = 1.5   # ... a level-3 one from this
SHORT_BOLD = 110          # a bold line up to this long, alone in its paragraph, is a heading
PITCH_FACTOR = 1.35       # a line this many normal line pitches below the previous one starts a paragraph
SHORT_LINE = 0.82         # a line shorter than this part of the text width may end a paragraph
INDENT_STEP = 18.0        # points of indentation per list level
MIN_TEXT_PAGES = 0.5      # a text layer on at least this share of the sampled pages, else it is a scan

_PAGE_NUMBER = re.compile(r"^\W*(?:strana|page|s\.|str\.)?\s*\d{1,5}\s*(?:/|z|of)?\s*\d{0,5}\W*$", re.I)
_MARKER = re.compile(r"^(\(\d{1,3}\)|\d{1,3}(?:\.\d{1,3})+\.?|\d{1,3}[.)]|\([a-z]{1,2}\)|[a-z]{1,2}\)|\([ivxlc]{1,6}\)|[•●▪■◦\-–—·])\s+")
_ARTICLE = re.compile(r"^(Článek|Čl\.|Článok|Article|Příloha|PŘÍLOHA|Príloha|PRÍLOHA|Annex|ANNEX|§)\s*[\dIVXLC]+\w*\b", re.I)
_SENTENCE_END = re.compile(r"[.;:!?)\]»”\"]\s*$")
_DIGITS = re.compile(r"\d+")


def _norm(text):
    return _DIGITS.sub("#", " ".join(text.split())).lower()


def _esc(text):
    return html.escape(text, quote=False)


def _span_text(spans, size):
    """The text of a line's spans; some PDFs set every word as a span of its own
    and leave the space out, so a visible gap between two spans is a space."""
    text = spans[0]["text"]
    for before, span in zip(spans, spans[1:]):
        gap = span["bbox"][0] - before["bbox"][2]
        if gap > 0.12 * size and not text.endswith(" ") and not span["text"].startswith(" "):
            text += " "
        text += span["text"]
    return text.strip()


def lines_of_page(page, number):
    """The positioned lines of a PyMuPDF page (blocks in the file's own order)."""
    lines = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block["lines"]:
            spans = [s for s in line["spans"] if s["text"].strip()]
            if not spans:
                continue
            chars = sum(len(s["text"]) for s in spans)
            size = max(s["size"] for s in spans)
            bold = sum(len(s["text"]) for s in spans if s["flags"] & 16 or "bold" in s["font"].lower()) > chars / 2
            x0, y0, x1, y1 = line["bbox"]
            vertical = abs(line["dir"][1]) > 0.5  # text turned sideways (an annex printed landscape)
            lines.append(Line(_span_text(spans, size), round(size, 1), bold, x0, y0, x1, y1, number, vertical))
    return lines


def drop_running_lines(pages, heights):
    """`pages` without the running headers/footers and the page numbers. A line
    is running when its normalised text stands in the top or bottom margin of at
    least RUNNING_SHARE of the pages (and 3 pages)."""
    seen = collections.defaultdict(set)
    for number, lines in enumerate(pages):
        for line in lines:
            if _in_margin(line, heights[number]):
                seen[_norm(line.text)].add(number)
    limit = max(3, RUNNING_SHARE * len(pages))
    running = {text for text, where in seen.items() if len(where) >= limit}
    kept = []
    for number, lines in enumerate(pages):
        kept.append([line for line in lines if not (
            _in_margin(line, heights[number]) and (_norm(line.text) in running or _PAGE_NUMBER.match(line.text)))])
    return kept


def _in_margin(line, height):
    return line.vertical or line.y0 < MARGIN or line.y1 > height - MARGIN


def body_size(pages):
    """The most common font size, weighted by characters."""
    weight = collections.Counter()
    for lines in pages:
        for line in lines:
            weight[round(line.size * 2) / 2] += len(line.text)
    return weight.most_common(1)[0][0] if weight else 0


_BARE_MARKER = re.compile(_MARKER.pattern[:-3] + "$")  # the marker alone on a line


def merge_marker_lines(lines):
    """A list marker set in its own text run on the same baseline as the text of
    the item (OJ: "(48)" at the margin, the text indented) becomes one line."""
    merged, skip = [], False
    for index, line in enumerate(lines):
        if skip:
            skip = False
            continue
        following = lines[index + 1] if index + 1 < len(lines) else None
        if (type(line) is Line and type(following) is Line and _BARE_MARKER.match(line.text)
                and abs(following.y0 - line.y0) < line.size / 2 and following.x0 >= line.x1 - 1):
            merged.append(Line(line.text + " " + following.text, following.size, line.bold and following.bold,
                               line.x0, min(line.y0, following.y0), following.x1, max(line.y1, following.y1), line.page,
                               line.vertical))
            skip = True
        else:
            merged.append(line)
    return merged


def line_pitch(pages):
    """The usual distance between the tops of two consecutive lines (the most
    common one; OJ regulations are set at 1.7 times the font size, a report at 1.2)."""
    distances = collections.Counter()
    for lines in pages:
        for before, after in zip(lines, lines[1:]):
            if type(before) is Line and type(after) is Line and 0 < after.y0 - before.y0 < 3 * after.size:
                distances[round((after.y0 - before.y0) * 2) / 2] += 1
    return distances.most_common(1)[0][0] if distances else 0


def _text_box(pages):
    """(left edge, width) of the body text."""
    lefts, rights = collections.Counter(), []
    for lines in pages:
        for line in lines:
            if type(line) is tuple:
                continue
            lefts[round(line.x0)] += len(line.text)
            rights.append(line.x1)
    left = lefts.most_common(1)[0][0] if lefts else 0
    rights.sort()
    right = rights[int(len(rights) * 0.9)] if rights else left + 1
    return left, max(right - left, 1)


def _join(previous, current):
    """`previous` + `current` as one run of text: a hyphen at the line end and a
    lowercase start of the next line make one word."""
    if re.search(r"[^\W\d_]-$", previous) and current[:1].islower():
        return previous[:-1] + current
    return previous + " " + current


def build_blocks(pages, size, pitch=None):
    """[("h3"|"h4"|"p"|"item"|"table", ...)] from the lines of the pages (running
    lines already dropped; a table is a plain `("table", rows)` tuple among the
    lines): the structure rebuilt from font and geometry."""
    left, width = _text_box(pages)
    pitch = line_pitch(pages) if pitch is None else pitch
    blocks = []
    previous = None
    for lines in pages:
        new_page = True
        for index, line in enumerate(lines):
            if type(line) is tuple:
                blocks.append(line)
                previous, new_page = None, False
                continue
            kind = _kind(line, size, pitch, _neighbour(lines, index - 1), _neighbour(lines, index + 1))
            marker = _MARKER.match(line.text) if kind == "p" else None
            if new_page:  # a paragraph goes on over a page break when it was not finished
                gap = not (blocks and blocks[-1][0] == "p" and not _SENTENCE_END.search(blocks[-1][1])
                           and line.text[:1].islower() and kind == "p")
            else:
                gap = previous is not None and line.y0 - previous.y0 > PITCH_FACTOR * pitch
            short = previous is not None and (previous.x1 - left) < SHORT_LINE * width \
                and _SENTENCE_END.search(previous.text)
            if (kind == "p" and not marker and not gap and blocks and blocks[-1][0] == "h4"
                    and _ARTICLE.match(blocks[-1][1]) and len(line.text) <= 100 and not _SENTENCE_END.search(line.text)):
                kind = "h4"  # the title line under "Článek 3"
            same = blocks and (blocks[-1][0] == kind or (kind == "p" and blocks[-1][0] == "item"))
            continues = (same and previous is not None and not gap and not marker
                         and not (short and line.text[:1].isupper()))
            if continues:
                blocks[-1] = (blocks[-1][0], _join(blocks[-1][1], line.text)) + blocks[-1][2:]
            elif marker:
                depth = max(0, min(4, round((line.x0 - left) / INDENT_STEP)))
                blocks.append(("item", line.text[marker.end():].strip(), marker.group(1), depth))
            else:
                blocks.append((kind, line.text))
            previous, new_page = line, False
    return blocks


def _neighbour(lines, index):
    return lines[index] if 0 <= index < len(lines) and type(lines[index]) is not tuple else None


def _kind(line, size, pitch, before, after):
    """What a line is: a larger font is a heading; a short bold line is one only
    when it stands apart (a bold phrase inside a paragraph is not a heading). A line
    that starts like a list item or reads as a sentence is never a heading."""
    if _ARTICLE.match(line.text) and len(line.text) <= 40:
        return "h4"
    text = line.text
    if (_MARKER.match(text) or text[:1].islower() or text[:1] in "(„\"'‚" or text[-1:] in ".;,:"
            or (_SENTENCE_END.search(text) and len(text) > 40)):
        return "p"  # a heading neither starts like an item or in mid-sentence nor ends like a sentence
    if size and line.size >= BIG_HEADING_RATIO * size and len(line.text) < 200:
        return "h3"
    if size and line.size >= HEADING_RATIO * size and len(line.text) < 200:
        return "h4"
    if line.bold and len(line.text) <= SHORT_BOLD and line.size >= size - 0.5:
        apart_before = before is None or line.y0 - before.y0 > PITCH_FACTOR * pitch or before.size > line.size
        apart_after = after is None or after.y0 - line.y0 > PITCH_FACTOR * pitch or not after.bold
        if apart_before and apart_after:
            return "h4"
    return "p"


def render(blocks):
    """(html fragment) of the blocks."""
    out = []
    for block in blocks:
        kind = block[0]
        if kind in ("h3", "h4"):
            out.append(f"<{kind}>{_esc(block[1])}</{kind}>")
        elif kind == "p":
            out.append(f'<p class="para">{_esc(block[1])}</p>')
        elif kind == "item":
            out.append(f'<p class="item d{block[3]}"><span class="num">{_esc(block[2])}</span>{_esc(block[1])}</p>')
        elif kind == "table":
            rows = "".join("<tr>" + "".join(f"<td>{_esc(cell)}</td>" for cell in row) + "</tr>" for row in block[1])
            out.append(f'<table class="data">{rows}</table>')
    return "\n".join(out)


def _tables_of_page(page):
    """[(bbox, rows)] of the tables PyMuPDF finds, rows as lists of strings; tables
    of fewer than two rows or columns (a framed paragraph) are not tables."""
    found = []
    for table in page.find_tables().tables:
        rows = [[" ".join((cell or "").split()) for cell in row] for row in table.extract()]
        rows = [row for row in rows if any(row)]
        used = [i for i in range(max((len(row) for row in rows), default=0)) if any(i < len(row) and row[i] for row in rows)]
        rows = [[row[i] if i < len(row) else "" for i in used] for row in rows]
        if len(rows) >= 2 and max(len(row) for row in rows) >= 2:
            found.append((table.bbox, rows))
    return found


def _inside(line, bbox):
    x, y = (line.x0 + line.x1) / 2, (line.y0 + line.y1) / 2
    return bbox[0] <= x <= bbox[2] and bbox[1] <= y <= bbox[3]


def extract_pdf(path, tables=True):
    """`Extracted(html, text, "pdf")` of the PDF at `path`; ExtractionError for a
    PDF without a text layer."""
    try:
        import pymupdf
    except ImportError as error:
        raise ExtractionError("PyMuPDF is not installed (use an interpreter that has it, "
                              "e.g. ~/.cache/lit-tools/bin/python)") from error
    try:
        document = pymupdf.open(path)
    except Exception as error:  # pymupdf has its own exception types for a damaged file
        raise ExtractionError(f"cannot open the PDF: {error}") from error
    if not document.page_count:
        raise ExtractionError("the PDF has no pages")
    step = max(1, document.page_count // 20)
    sample = [document[i] for i in range(0, document.page_count, step)]
    with_text = sum(1 for page in sample if len(page.get_text().strip()) > 40)
    if with_text < MIN_TEXT_PAGES * len(sample):
        raise ExtractionError("no text layer (a scan; OCR would be needed)")
    pages, heights, page_tables = [], [], []
    for number, page in enumerate(document):
        lines = lines_of_page(page, number)
        found = _tables_of_page(page) if tables else []
        page_tables.append(found)
        pages.append([line for line in lines if not any(_inside(line, bbox) for bbox, _ in found)])
        heights.append(page.rect.height)
    pages = [merge_marker_lines(lines) for lines in drop_running_lines(pages, heights)]
    for number, found in enumerate(page_tables):
        for bbox, rows in found:  # a table is placed by its top edge among the lines of its page
            at = next((i for i, line in enumerate(pages[number]) if type(line) is Line and line.y0 > bbox[1]),
                      len(pages[number]))
            pages[number].insert(at, ("table", rows))
    flat = [[line for line in lines if isinstance(line, Line)] for lines in pages]
    blocks = build_blocks(pages, body_size(flat))
    if not blocks:
        raise ExtractionError("no text found in the PDF")
    fragment = render(blocks)
    return Extracted(fragment, html_to_text(fragment), "pdf")
