#!/usr/bin/env python3
"""Převod formálního dokumentu v Markdownu (doc/*.md) na DOCX a PDF podle
TEXT_STYLE.md.

Použití:
    .venv/bin/python src/tools/md_to_office.py doc/MPO_VYPORADANI.md \
        --out doc/mpo_odeslani --subtitle "…" [--pdf]

Podporovaná podmnožina Markdownu: nadpis dokumentu (#), kapitoly (##
„N. Text“ nebo „Příloha X: Text“), podkapitoly (### „N.M Text“), odstavce,
odrážky (* / -), číslované seznamy (1.), tabulky s hlavičkou, bloky kódu
(```), citace (>), tučné písmo, `kód`, <adresa> a [text](adresa).
Vynechává se blok „Historie dokumentu“ a HTML komentáře (např. značky
<!-- OTEVŘENO … -->), takže se do výstupu nedostanou interní poznámky.

DOCX (python-docx) dodržuje TEXT_STYLE.md, odstavec 3: vestavěné styly,
motiv Aptos, nadpisy navy 17365D, Název v Aptos ExtraBold, viditelná čísla
kapitol přes pole SEQ Kapitola se záložkou, podkapitoly „N.M“, tabulky
s popiskem „Tabulka N — …“ (pole SEQ Tabulka) nad tabulkou, odkazy
„odstavec N“ jako pole REF … \\# 0 \\h, A4 s okraji 2,5 cm, číslo strany
v zápatí, jazyk cs-CZ na každém běhu, updateFields v settings.xml.

PDF se vykresluje z HTML téhož obsahu prohlížečem Chromium (Playwright),
protože LibreOffice na serveru není; čísla kapitol a tabulek jsou v HTML
dopočtená stejně jako cache hodnoty polí v DOCX.
"""
import argparse
import html
import os
import re
import zipfile

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

MONO = "Aptos Mono"
NAVY = RGBColor(0x17, 0x36, 0x5D)

# ─────────────────────────────── parsování ───────────────────────────────


def parse(md):
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S)
    lines = md.split("\n")
    blocks, i = [], 0
    chapter, sub = None, 0

    def para_until(i):
        buf = []
        while i < len(lines) and lines[i].strip() and not re.match(r"(#{1,4} |```|\||> )", lines[i]):
            buf.append(lines[i].strip())
            i += 1
        return " ".join(buf), i

    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith("# "):
            blocks.append(("title", line[2:].strip()))
            i += 1
            continue
        if line.startswith("> "):
            buf = []
            while i < len(lines) and lines[i].startswith(">"):
                buf.append(lines[i][1:].strip())
                i += 1
            if buf and buf[0].startswith("Historie dokumentu"):
                continue
            blocks.append(("quote", " ".join(buf)))
            continue
        m = re.match(r"## (?:(\d+)\. )?(.*)", line)
        if m and line.startswith("## "):
            if m.group(1):
                chapter, sub = int(m.group(1)), 0
                blocks.append(("h1", chapter, m.group(2).strip()))
            else:
                chapter, sub = m.group(2).split(":")[0].replace("Příloha ", ""), 0
                blocks.append(("h1", None, m.group(2).strip()))
            i += 1
            continue
        if line.startswith("### "):
            t = line[4:].strip()
            m2 = re.match(r"(\d+)\.(\d+) (.*)", t)
            if m2:
                sub += 1
                assert int(m2.group(1)) == chapter and int(m2.group(2)) == sub, ("číslování podkapitol", t)
                blocks.append(("h2", "%s.%s" % (chapter, sub), m2.group(3)))
            else:
                m3 = re.match(r"([A-Z]\.\d+) (.*)", t)
                blocks.append(("h2", m3.group(1), m3.group(2)) if m3 else ("h2", None, t))
            i += 1
            continue
        if line.startswith("```"):
            buf = []
            i += 1
            while not lines[i].startswith("```"):
                buf.append(lines[i])
                i += 1
            blocks.append(("code", "\n".join(buf)))
            i += 1
            continue
        if line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split(" | ")]
                if not re.match(r"^\|[-| :]+\|$", lines[i].strip()):
                    rows.append(cells)
                i += 1
            blocks.append(("table", rows[0], rows[1:]))
            continue
        for kind, pat in (("ul", r"[*-] "), ("ol", r"\d+\. ")):
            if re.match(pat, line):
                items = []
                while i < len(lines) and (re.match(pat, lines[i]) or (lines[i].startswith("  ") and lines[i].strip() and items)):
                    if re.match(pat, lines[i]):
                        items.append(re.sub("^" + pat, "", lines[i]).strip())
                    else:
                        items[-1] += " " + lines[i].strip()
                    i += 1
                blocks.append((kind, items))
                break
        else:
            text, i = para_until(i)
            blocks.append(("p", text))
    return blocks


INLINE = re.compile(r"\*\*(.+?)\*\*|`([^`]+)`|<(https?://[^>]+)>|\[([^\]]+)\]\((https?://[^)]+)\)"
                    r"|(?<![“`] )(?<![“`], )(odstav(?:ec|ce|ci|cem|ců|cích))[  ]+(\d+)((?:\.\d+)?)")


def inline(text, chapters, subs):
    """Rozloží řádek na segmenty (druh, text[, extra])."""
    out, pos = [], 0
    for m in INLINE.finditer(text):
        if m.start() > pos:
            out.append(("t", text[pos:m.start()]))
        if m.group(1) is not None:
            for seg in inline(m.group(1), chapters, subs):
                out.append(("b" if seg[0] == "t" else seg[0],) + seg[1:])
        elif m.group(2) is not None:
            out.append(("mono", m.group(2)))
        elif m.group(3) is not None:
            out.append(("link", m.group(3), m.group(3)))
        elif m.group(4) is not None:
            out.append(("link", m.group(4), m.group(5)))
        else:
            word, num, tail = m.group(6), int(m.group(7)), m.group(8)
            before = text[max(0, m.start() - 3):m.start()]
            full = "%d%s" % (num, tail)
            if num in chapters and (not tail or full in subs) and "md" not in before:
                out.append(("t", word + " "))
                out.append(("ref", num))
                if tail:
                    out.append(("t", tail))
            else:
                out.append(("t", m.group(0)))
        pos = m.end()
    if pos < len(text):
        out.append(("t", text[pos:]))
    return out


# ─────────────────────────────── DOCX ───────────────────────────────


class DocxWriter:
    def __init__(self):
        self.doc = Document()
        self.bid = 0
        self.tables = 0
        self.num_id_seq = None
        d = self.doc
        sec = d.sections[0]
        sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
        sec.left_margin = sec.right_margin = sec.top_margin = sec.bottom_margin = Cm(2.5)
        for sid, pt in (("Title", 26), ("Heading 1", 16), ("Heading 2", 14)):
            d.styles[sid].font.color.rgb = NAVY
            d.styles[sid].font.size = Pt(pt)
        d.styles["Normal"].font.size = Pt(11)
        title = d.styles["Title"]
        title.font.name = "Aptos ExtraBold"
        ppr = title.element.get_or_add_pPr()
        bdr = ppr.find(qn("w:pBdr"))
        if bdr is not None:
            ppr.remove(bdr)
        title.paragraph_format.space_after = Pt(6)
        par = sec.footer.paragraphs[0]
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        par.add_run("Strana ")
        fld = OxmlElement("w:fldSimple")
        fld.set(qn("w:instr"), "PAGE")
        r = OxmlElement("w:r")
        t = OxmlElement("w:t")
        t.text = "1"
        r.append(t)
        fld.append(r)
        par._p.append(fld)

    # pole a záložky
    def _run(self, italic=False, sz=None, bold=False):
        r = OxmlElement("w:r")
        rpr = OxmlElement("w:rPr")
        if bold:
            rpr.append(OxmlElement("w:b"))
        if italic:
            rpr.append(OxmlElement("w:i"))
        if sz:
            e = OxmlElement("w:sz")
            e.set(qn("w:val"), str(sz))
            rpr.append(e)
        r.append(rpr)
        return r

    def _field(self, instr, cached, **kw):
        runs = []
        for kind in ("begin", "instr", "separate", "text", "end"):
            r = self._run(**kw)
            if kind == "instr":
                e = OxmlElement("w:instrText")
                e.set(qn("xml:space"), "preserve")
                e.text = instr
            elif kind == "text":
                e = OxmlElement("w:t")
                e.set(qn("xml:space"), "preserve")
                e.text = cached
            else:
                e = OxmlElement("w:fldChar")
                e.set(qn("w:fldCharType"), kind)
            r.append(e)
            runs.append(r)
        return runs

    def _bookmarked(self, name, instr, cached, **kw):
        self.bid += 1
        bs = OxmlElement("w:bookmarkStart")
        bs.set(qn("w:id"), str(self.bid))
        bs.set(qn("w:name"), name)
        be = OxmlElement("w:bookmarkEnd")
        be.set(qn("w:id"), str(self.bid))
        return [bs] + self._field(instr, cached, **kw) + [be]

    def runs(self, par, segs, bold=False):
        for seg in segs:
            kind, text = seg[0], seg[1]
            if kind == "ref":
                for el in self._field(" REF _RefKap%d \\# 0 \\h " % text, str(text), bold=bold):
                    par._p.append(el)
                continue
            r = par.add_run(text)
            if kind == "b" or bold:
                r.bold = True
            if kind == "mono":
                r.font.name = MONO
                r.font.size = Pt(10)
            if kind == "link":
                r.font.color.rgb = RGBColor(0x0F, 0x4C, 0x81)
                r.underline = True

    def title(self, text, subtitle):
        self.doc.add_paragraph(text, style="Title")
        if subtitle:
            self.doc.add_paragraph(subtitle, style="Subtitle")

    def h1(self, num, text):
        par = self.doc.add_heading(level=1)
        if num is not None:
            for el in self._bookmarked("_RefKap%d" % num, " SEQ Kapitola \\* ARABIC ", str(num)):
                par._p.append(el)
            par.add_run(" " + text)
        else:
            par.add_run(text)

    def h2(self, num, text):
        self.doc.add_heading(("%s " % num if num else "") + text, level=2)

    def para(self, segs, style=None):
        par = self.doc.add_paragraph(style=style)
        self.runs(par, segs)
        return par

    def quote(self, segs):
        par = self.para(segs, style="Intense Quote")
        return par

    def _restart_numbering(self, par):
        """Každý číslovaný seznam začíná od 1: nová instance w:num nad abstraktním
        číslováním stylu List Number s startOverride."""
        numbering = self.doc.part.numbering_part.element
        style = self.doc.styles["List Number"]
        num_pr = style.element.pPr.find(qn("w:numPr"))
        base_num_id = num_pr.find(qn("w:numId")).get(qn("w:val"))
        abstract = None
        for n in numbering.findall(qn("w:num")):
            if n.get(qn("w:numId")) == base_num_id:
                abstract = n.find(qn("w:abstractNumId")).get(qn("w:val"))
        new_id = str(max(int(n.get(qn("w:numId"))) for n in numbering.findall(qn("w:num"))) + 1)
        num = OxmlElement("w:num")
        num.set(qn("w:numId"), new_id)
        a = OxmlElement("w:abstractNumId")
        a.set(qn("w:val"), abstract)
        num.append(a)
        lo = OxmlElement("w:lvlOverride")
        lo.set(qn("w:ilvl"), "0")
        so = OxmlElement("w:startOverride")
        so.set(qn("w:val"), "1")
        lo.append(so)
        num.append(lo)
        numbering.append(num)
        return new_id

    def items(self, kind, items_segs):
        style = "List Bullet" if kind == "ul" else "List Number"
        num_id = None
        for k, segs in enumerate(items_segs):
            par = self.para(segs, style=style)
            par.paragraph_format.space_after = Pt(3)
            if kind == "ol":
                if num_id is None:
                    num_id = self._restart_numbering(par)
                ppr = par._p.get_or_add_pPr()
                npr = OxmlElement("w:numPr")
                il = OxmlElement("w:ilvl")
                il.set(qn("w:val"), "0")
                ni = OxmlElement("w:numId")
                ni.set(qn("w:val"), num_id)
                npr.append(il)
                npr.append(ni)
                ppr.find(qn("w:pStyle")).addnext(npr)  # pořadí CT_PPrBase: pStyle, …, numPr, …, spacing

    def code(self, text):
        for line in text.split("\n"):
            par = self.doc.add_paragraph()
            par.paragraph_format.space_after = Pt(0)
            par.paragraph_format.left_indent = Cm(0.5)
            r = par.add_run(line)
            r.font.name = MONO
            r.font.size = Pt(8.5)
        self.doc.add_paragraph().paragraph_format.space_after = Pt(2)

    def table(self, caption, header, rows, widths):
        self.tables += 1
        cap = self.doc.add_paragraph()
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap.paragraph_format.space_before = Pt(6)
        cap.paragraph_format.space_after = Pt(4)
        cap.paragraph_format.keep_with_next = True
        r = cap.add_run("Tabulka ")
        r.italic = True
        r.font.size = Pt(9.5)
        for el in self._bookmarked("_RefTab%d" % self.tables, " SEQ Tabulka \\* ARABIC ", str(self.tables),
                                   italic=True, sz=19):
            cap._p.append(el)
        r = cap.add_run(" — " + caption)
        r.italic = True
        r.font.size = Pt(9.5)
        t = self.doc.add_table(rows=1 + len(rows), cols=len(header))
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        for i, row in enumerate([header] + rows):
            for j, segs in enumerate(row):
                c = t.rows[i].cells[j]
                c.width = Cm(widths[j])
                par = c.paragraphs[0]
                par.paragraph_format.space_after = Pt(2)
                self.runs(par, segs, bold=(i == 0))
                for r in par.runs:
                    r.font.size = Pt(9.5)
                if i == 0:
                    tcpr = c._tc.get_or_add_tcPr()
                    shd = OxmlElement("w:shd")
                    shd.set(qn("w:val"), "clear")
                    shd.set(qn("w:fill"), "DEEAF6")
                    tcpr.append(shd)
            if i == 0:
                trpr = t.rows[0]._tr.get_or_add_trPr()
                th = OxmlElement("w:tblHeader")
                trpr.append(th)
        self.doc.add_paragraph().paragraph_format.space_after = Pt(2)

    def save(self, path):
        def process(root):
            for r in root.iter(qn("w:r")):
                rpr = r.find(qn("w:rPr"))
                if rpr is None:
                    rpr = OxmlElement("w:rPr")
                    r.insert(0, rpr)
                if rpr.find(qn("w:lang")) is None:
                    lang = OxmlElement("w:lang")
                    lang.set(qn("w:val"), "cs-CZ")
                    lang.set(qn("w:eastAsia"), "cs-CZ")
                    lang.set(qn("w:bidi"), "ar-SA")
                    rpr.append(lang)
        process(self.doc.element.body)
        for s in self.doc.sections:
            process(s.footer.part.element)
        self.doc.save(path)
        tmp = path + ".tmp"
        with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == "word/theme/theme1.xml":
                    t = data.decode("utf-8")
                    t = re.sub(r'(<a:majorFont>\s*<a:latin typeface=")[^"]*(")', r"\g<1>Aptos Display\g<2>", t)
                    t = re.sub(r'(<a:minorFont>\s*<a:latin typeface=")[^"]*(")', r"\g<1>Aptos\g<2>", t)
                    data = t.encode("utf-8")
                elif item.filename == "word/settings.xml":
                    s = data.decode("utf-8")
                    s = re.sub(r"<w:zoom\s*/>", '<w:zoom w:percent="100"/>', s)
                    s = re.sub(r"(<w:zoom(?![^>]*w:percent)[^>]*?)/>", r'\g<1> w:percent="100"/>', s)
                    if "<w:updateFields" not in s:
                        s = re.sub(r"(<w:compat>)", r'<w:updateFields w:val="true"/>\1', s, count=1)
                    data = s.encode("utf-8")
                elif item.filename == "word/styles.xml":
                    s = data.decode("utf-8")
                    s = s.replace('<w:lang w:val="en-US" w:eastAsia="en-US" w:bidi="ar-SA"/>',
                                  '<w:lang w:val="cs-CZ" w:eastAsia="cs-CZ" w:bidi="ar-SA"/>')
                    data = s.encode("utf-8")
                zout.writestr(item, data)
        os.replace(tmp, path)


# ─────────────────────────────── HTML (pro PDF) ───────────────────────────────

CSS = """
@page { size: A4; margin: 2.5cm 2.5cm 2.5cm 2.5cm; }
body { font-family: Aptos, Carlito, Calibri, "Liberation Sans", "DejaVu Sans", sans-serif; font-size: 11pt;
       line-height: 1.35; color: #000; }
h1.title { font-size: 26pt; color: #17365D; font-weight: 800; margin: 0 0 4pt 0; line-height: 1.1; }
p.subtitle { font-size: 13pt; color: #4f6179; margin: 0 0 18pt 0; }
h2 { font-size: 16pt; color: #17365D; font-weight: 600; margin: 18pt 0 6pt 0; break-after: avoid; }
h3 { font-size: 14pt; color: #17365D; font-weight: 600; margin: 12pt 0 4pt 0; break-after: avoid; }
p { margin: 0 0 6pt 0; text-align: left; }
ul, ol { margin: 0 0 6pt 0; padding-left: 1.4em; } li { margin-bottom: 3pt; }
code { font-family: "Liberation Mono", "DejaVu Sans Mono", monospace; font-size: 9.5pt; }
pre { font-family: "Liberation Mono", "DejaVu Sans Mono", monospace; font-size: 8.5pt; margin: 0 0 8pt 0.5cm;
      white-space: pre-wrap; }
.caption { text-align: center; font-style: italic; font-size: 9.5pt; margin: 8pt 0 4pt 0; break-after: avoid; }
table { border-collapse: collapse; width: 100%; table-layout: fixed; font-size: 9.5pt; margin-bottom: 10pt; }
th, td { overflow-wrap: anywhere; border: 0.5pt solid #000; padding: 2pt 4pt; vertical-align: top; text-align: left; }
th { background: #DEEAF6; font-weight: bold; } thead { display: table-header-group; } tr { break-inside: avoid; }
blockquote { border-top: 1pt solid #17365D; border-bottom: 1pt solid #17365D; color: #17365D; font-style: italic;
             margin: 8pt 1cm; padding: 6pt 0; }
a { color: #0F4C81; overflow-wrap: anywhere; }
"""


def html_segs(segs):
    out = []
    for seg in segs:
        kind, text = seg[0], seg[1]
        if kind == "ref":
            out.append(str(text))
        elif kind == "b":
            out.append("<b>%s</b>" % html.escape(text))
        elif kind == "mono":
            out.append("<code>%s</code>" % html.escape(text))
        elif kind == "link":
            out.append('<a href="%s">%s</a>' % (html.escape(seg[2]), html.escape(text)))
        else:
            out.append(html.escape(text))
    return "".join(out)


# ─────────────────────────────── hlavní běh ───────────────────────────────


def col_widths(header, rows, total=16.0):
    lens = []
    for j in range(len(header)):
        col = [len(header[j])] + [len(r[j]) if j < len(r) else 0 for r in rows]
        lens.append(max(9, min(60, sum(col) / len(col))))
    s = sum(lens)
    return [total * x / s for x in lens]


def convert(src, out_dir, subtitle, pdf):
    md = open(src, encoding="utf-8").read()
    blocks = parse(md)
    chapters = {b[1] for b in blocks if b[0] == "h1" and b[1] is not None}
    subs = {b[1] for b in blocks if b[0] == "h2" and b[1]}
    seg = lambda t: inline(t, chapters, subs)
    base = os.path.splitext(os.path.basename(src))[0]
    w = DocxWriter()
    h = ['<!doctype html><html lang="cs"><head><meta charset="utf-8"><style>%s</style></head><body>' % CSS]
    heading_ctx, tabs_in_ctx = "", 0
    for b in blocks:
        kind = b[0]
        if kind == "title":
            w.title(b[1], subtitle)
            h.append('<h1 class="title">%s</h1>' % html.escape(b[1]))
            if subtitle:
                h.append('<p class="subtitle">%s</p>' % html.escape(subtitle))
        elif kind == "h1":
            w.h1(b[1], b[2])
            h.append("<h2>%s%s</h2>" % ("%d&nbsp;&nbsp;" % b[1] if b[1] else "", html.escape(b[2])))
            heading_ctx, tabs_in_ctx = b[2], 0
        elif kind == "h2":
            w.h2(b[1], b[2])
            h.append("<h3>%s%s</h3>" % (html.escape(b[1]) + "&nbsp;" if b[1] else "", html.escape(b[2])))
            heading_ctx, tabs_in_ctx = b[2], 0
        elif kind == "p":
            w.para(seg(b[1]))
            h.append("<p>%s</p>" % html_segs(seg(b[1])))
        elif kind == "quote":
            w.quote(seg(b[1]))
            h.append("<blockquote>%s</blockquote>" % html_segs(seg(b[1])))
        elif kind in ("ul", "ol"):
            w.items(kind, [seg(x) for x in b[1]])
            h.append("<%s>%s</%s>" % (kind, "".join("<li>%s</li>" % html_segs(seg(x)) for x in b[1]), kind))
        elif kind == "code":
            w.code(b[1])
            h.append("<pre>%s</pre>" % html.escape(b[1]))
        elif kind == "table":
            tabs_in_ctx += 1
            caption = heading_ctx + (" (%d)" % tabs_in_ctx if tabs_in_ctx > 1 else "")
            header, rows = b[1], b[2]
            widths = col_widths(header, rows)
            w.table(caption, [seg(c) for c in header], [[seg(c) for c in r] for r in rows], widths)
            h.append('<p class="caption">Tabulka %d — %s</p><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table>' % (
                w.tables, html.escape(caption),
                "".join('<th style="width:%.0f%%">%s</th>' % (100 * x / 16.0, html_segs(seg(c))) for c, x in zip(header, widths)),
                "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % html_segs(seg(c)) for c in r) for r in rows)))
    h.append("</body></html>")
    os.makedirs(out_dir, exist_ok=True)
    docx_path = os.path.join(out_dir, base + ".docx")
    w.save(docx_path)
    print("DOCX:", docx_path)
    if pdf:
        from playwright.sync_api import sync_playwright
        html_path = os.path.join(out_dir, "." + base + ".html")
        open(html_path, "w", encoding="utf-8").write("".join(h))
        pdf_path = os.path.join(out_dir, base + ".pdf")
        with sync_playwright() as p:
            b = p.chromium.launch()
            page = b.new_page()
            page.goto("file://" + os.path.abspath(html_path))
            page.pdf(path=pdf_path, format="A4", print_background=True, display_header_footer=True,
                     header_template="<span></span>",
                     footer_template='<div style="font-size:9pt;width:100%;text-align:center;font-family:sans-serif">'
                                     'Strana <span class="pageNumber"></span></div>',
                     margin={"top": "2.5cm", "bottom": "2.5cm", "left": "2.5cm", "right": "2.5cm"})
            b.close()
        os.remove(html_path)
        print("PDF:", pdf_path)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("src")
    ap.add_argument("--out", required=True)
    ap.add_argument("--subtitle", default="")
    ap.add_argument("--pdf", action="store_true")
    a = ap.parse_args()
    convert(a.src, a.out, a.subtitle, a.pdf)
