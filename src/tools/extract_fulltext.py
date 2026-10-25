"""Extracts the clean legal text out of the whole-page HTML downloads that
`fetch_fulltext.py` stores under `data/fulltext/` — GitHub issue #2.

The stored files are complete pages of the source sites (navigation,
scripts, trackers, root-relative links that lead nowhere on our domain; the
Slov-Lex ones are an empty Angular shell). Serving them as they are looks
broken and runs foreign scripts on our origin. This module keeps only the
text of the act and rebuilds it as a small, closed vocabulary of HTML —
headings, paragraphs with a nesting level, tables, a few inline marks —
that the application can restyle and render without trusting anything the
source page contained. The original download is never touched.

Supported sources (anything else is reported as unsupported, never
guessed at):
- zakonyprolidi.cz — the `div.Frags` inside `article#idBody_idCtn`.
- eur-lex.europa.eu — `div#text` (Official Journal markup, `oj-*` classes).
- slov-lex.sk — `div.predpis` of the page as a browser rendered it.
PDFs are NOT handled here (issue #2 open question).

Output vocabulary (everything else is dropped or unwrapped): `h3`, `h4`,
`p` (class `l1`..`l5`, `para`, `note`, `title`, `center`, `item` + `d0`..`d4`), `hr`, `table`
(class `data` or `layout`) with `tr`/`th`/`td`, and inline `em`,
`strong`, `sub`, `sup`, `br`, `span.num`. Links, images, scripts, styles
and every attribute not listed here are removed.

Usage:
    .venv/bin/python src/tools/extract_fulltext.py            # dry run, report only
    .venv/bin/python src/tools/extract_fulltext.py --apply    # write data/fulltext_clean/
"""
import argparse
import collections
import html
import json
import pathlib
import re
import sys
from urllib.parse import urlparse

from bs4 import BeautifulSoup, NavigableString, Tag

BASE_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent
MANIFEST_PATH = REPO_ROOT / "data" / "fulltext_manifest.json"
OUTPUT_DIR = REPO_ROOT / "data" / "fulltext_clean"


class ExtractionError(Exception):
    """The page is not a document we can extract text from."""


class Unsupported(ExtractionError):
    """The page comes from a source this module does not handle."""


_WS = re.compile(r"\s+")

# Tags whose content is never part of the text.
_DROP = {"script", "style", "noscript", "img", "figure", "svg", "iframe",
         "form", "button", "input", "select", "head", "nav", "footer"}

# Source-neutral inline mapping: tag -> output tag.
_INLINE_TAGS = {"i": "em", "em": "em", "b": "strong", "strong": "strong",
                "sub": "sub", "sup": "sup"}
# EUR-Lex marks emphasis with classed spans.
_INLINE_CLASSES = {"oj-italic": "em", "oj-bold": "strong",
                   "oj-sub": "sub", "oj-super": "sup",
                   # the consolidated-text dialect of EUR-Lex
                   "italics": "em", "boldface": "strong",
                   "subscript": "sub", "superscript": "sup"}

_NON_TEXT_STRINGS = ("Comment", "Doctype", "CData", "ProcessingInstruction", "Declaration")

_BLOCK_WRAPPERS = {"div", "section", "article", "main", "body", "html",
                   "tbody", "thead", "tfoot", "center", "blockquote", "span"}


def _classes(tag):
    return tag.get("class") or []


def _inline(node):
    """HTML for the inline content of `node` (children only)."""
    out = []
    for child in node.children:
        if isinstance(child, NavigableString):
            if type(child).__name__ in _NON_TEXT_STRINGS:
                continue
            out.append(html.escape(_WS.sub(" ", str(child)), quote=False))
        elif isinstance(child, Tag):
            out.append(_inline_tag(child))
    return "".join(out)


def _inline_tag(tag):
    name = tag.name
    if name in _DROP:
        return ""
    if name == "br":
        return "<br>"
    if name == "var":
        return f'<span class="num">{_inline(tag)}</span>'
    mapped = _INLINE_TAGS.get(name)
    if mapped is None and name == "span":
        for cls in _classes(tag):
            if cls in _INLINE_CLASSES:
                mapped = _INLINE_CLASSES[cls]
                break
    inner = _inline(tag)
    if mapped and inner.strip():
        return f"<{mapped}>{inner}</{mapped}>"
    return inner  # unwrap: links, unknown spans, anchors


def _has_text(fragment):
    return bool(_WS.sub("", re.sub(r"<[^>]+>", "", fragment)))


def _emit(tag_name, cls, inner):
    inner = inner.strip()
    if not _has_text(inner):
        return ""
    attr = f' class="{cls}"' if cls else ""
    return f"<{tag_name}{attr}>{inner}</{tag_name}>"


_PLAIN_P = re.compile(r'^<p(?: class="d\d")?>(.*)</p>$', re.S)
_MARKER_MAX = 8  # "(10)", "(iii)", "a)", "1." — longer first cells are real content


def _own_rows(table):
    """The rows of `table` itself — find_all("tr") would also return the rows
    of any table nested inside one of its cells, which are handled there."""
    return [tr for tr in table.find_all("tr") if tr.find_parent("table") is table]


def _enumeration_items(tag, source, depth):
    """A layout table that is only an enumeration — rows of a short marker
    ("(1)", "(a)") next to the text, as the Official Journal sets every
    numbered recital and list — becomes one hanging-indent paragraph per
    row, nested ones one level deeper. Rendered as separate tables these
    never lined up (each table sized its own marker column). None when the
    table is anything else."""
    items = []
    for tr in _own_rows(tag):
        cells = tr.find_all(["td", "th"], recursive=False)
        # Leading empty cells are indentation spacers: one level deeper each.
        spacers = 0
        while len(cells) > 2 and not cells[0].get_text().strip():
            cells = cells[1:]
            spacers += 1
        if len(cells) != 2:
            return None
        marker = _WS.sub(" ", cells[0].get_text()).strip()
        if not marker or len(marker) > _MARKER_MAX:
            return None
        level = depth + spacers
        items.extend(_item(marker, list(_blocks(cells[1], source, level + 1)), level))
    return items or None


def _item(marker, body, level):
    """A hanging-indent item paragraph: the marker, then the first plain
    paragraph of `body` (the blocks of the item's content) joined to it, then
    the rest of `body` (continuations, nested items)."""
    lead = ""
    if body and (m := _PLAIN_P.match(body[0])):
        lead, body = m.group(1), body[1:]
    return [f'<p class="item d{level}"><span class="num">{html.escape(marker, quote=False)}</span>{lead}</p>', *body]


def _eurlex_special(child, depth):
    """The two list shapes of consolidated EUR-Lex texts: a `grid-list` (marker
    column + text column) and a numbered paragraph (`div.norm` that starts with
    `span.no-parag`). A list of the blocks, or None when `child` is neither."""
    classes = _classes(child)
    if child.name != "div":
        return None
    if "grid-list" in classes:
        marker_cell = child.find("div", class_="list")
        text_cell = child.find("div", class_="grid-list-column-2")
        if marker_cell is None or text_cell is None:
            return None
        marker = _WS.sub(" ", marker_cell.get_text()).strip()
        return _item(marker, list(_blocks(text_cell, "eurlex", depth + 1)), depth)
    number = child.find("span", class_="no-parag", recursive=False) if "norm" in classes else None
    if number is not None:
        marker = _WS.sub(" ", number.get_text()).strip()
        number.extract()
        return _item(marker, list(_blocks(child, "eurlex", depth + 1)), depth)
    return None


def _table(tag, source, depth=0):
    cls = "data" if {"oj-table", "borderOj"} & set(_classes(tag)) or source in ("zakonyprolidi", "slovlex") else "layout"
    if cls == "layout":
        items = _enumeration_items(tag, source, depth)
        if items:
            return "\n".join(items)
    rows = []
    for tr in _own_rows(tag):
        cells = []
        for cell in tr.find_all(["td", "th"], recursive=False):
            span = "".join(f' {a}="{int(cell[a])}"' for a in ("colspan", "rowspan")
                           if str(cell.get(a, "")).isdigit() and int(cell[a]) > 1)
            body = "".join(_blocks(cell, source, depth)) or _inline(cell).strip()
            cells.append(f"<{cell.name}{span}>{body}</{cell.name}>")
        if cells and _has_text("".join(cells)):
            rows.append("<tr>" + "".join(cells) + "</tr>")
    if not rows:
        return ""
    return f'<table class="{cls}">' + "".join(rows) + "</table>"


# (tag, class) for the block-level elements of each source.
def _zakonyprolidi_block(tag):
    cls = _classes(tag)
    if tag.name == "h3":
        return "h3", None
    if tag.name == "h4":
        return "h4", None
    if tag.name == "p":
        if "PARA" in cls:
            return "p", "para"
        for c in cls:
            if re.fullmatch(r"L[1-5]", c):
                return "p", c.lower()
        return "p", None
    return None


_EURLEX_CLASSES = {
    "oj-doc-ti": ("p", "title"), "oj-ti-tbl": ("h4", None),
    "oj-ti-grseq-1": ("h3", None), "oj-ti-section-1": ("h3", None),
    "oj-ti-section-2": ("h3", None), "oj-ti-art": ("h4", None),
    "oj-sti-art": ("h4", None), "oj-note": ("p", "note"),
    "oj-signatory": ("p", "center"), "oj-center": ("p", "center"),
    "oj-ti-annotation": ("p", "note"),
    # consolidated texts ("TXT/HTML/?uri=CELEX:0..."): another set of class names
    "title-doc-first": ("p", "title"), "title-doc-last": ("p", "title"),
    "title-division-1": ("h3", None), "title-division-2": ("h3", None),
    "title-gr-seq-level-1": ("h4", None), "title-gr-seq-level-2": ("h4", None),
    "title-gr-seq-level-3": ("h4", None), "title-article-norm": ("h4", None),
    "stitle-article-norm": ("h4", None), "title-annex-1": ("h3", None),
    "title-annex-2": ("h3", None), "footnote": ("p", "note"),
}
# Document-header furniture (date, language, "Official Journal ...", page).
_EURLEX_SKIP = {"oj-hd-date", "oj-hd-lg", "oj-hd-ti", "oj-hd-oj", "oj-hd-coll",
                "oj-hd-uniq", "oj-separator",
                # amendment markers ("▼B" and the link to the next one) in consolidated texts
                "arrow", "modref"}


def _eurlex_block(tag):
    if tag.name != "p":
        return {"h1": ("h3", None), "h2": ("h3", None), "h3": ("h3", None),
                "h4": ("h4", None)}.get(tag.name)
    cls = _classes(tag)
    for c in cls:
        if c in _EURLEX_CLASSES:
            return _EURLEX_CLASSES[c]
    return "p", None


def _slovlex_block(tag):
    """Only reached for the cells of a table inside an act's text."""
    return {"p": ("p", None), "h3": ("h3", None), "h4": ("h4", None)}.get(tag.name)


_BLOCK_RULES = {"zakonyprolidi": _zakonyprolidi_block, "eurlex": _eurlex_block, "slovlex": _slovlex_block}


def _blocks(node, source, depth=0):
    """Yields the HTML of the block-level content of `node`, in order.
    `depth` is how many enumeration levels (see _enumeration_items) enclose it."""
    rule = _BLOCK_RULES[source]
    pending = []  # loose inline content between blocks

    def flush():
        if pending:
            text = "".join(pending)
            pending.clear()
            piece = _emit("p", f"d{depth}" if depth else None, text)
            if piece:
                yield piece

    for child in node.children:
        if isinstance(child, NavigableString):
            if type(child).__name__ not in _NON_TEXT_STRINGS:
                pending.append(html.escape(_WS.sub(" ", str(child)), quote=False))
            continue
        if not isinstance(child, Tag) or child.name in _DROP:
            continue
        if source == "eurlex" and any(c in _EURLEX_SKIP for c in _classes(child)):
            continue
        if source == "eurlex" and (special := _eurlex_special(child, depth)) is not None:
            yield from flush()
            yield from special
        elif child.name == "hr":
            yield from flush()
            yield "<hr>"
        elif child.name == "table":
            yield from flush()
            if source == "eurlex" and child.find(class_="oj-hd-ti"):
                continue  # the Official Journal page header table
            piece = _table(child, source, depth)
            if piece:
                yield piece
        elif (mapped := rule(child)) is not None:
            yield from flush()
            tag_name, cls = mapped
            if depth and tag_name == "p" and cls is None:
                cls = f"d{depth}"  # body text continuing under an enumeration item
            piece = _emit(tag_name, cls, _inline(child))
            if piece:
                yield piece
        elif child.name in _BLOCK_WRAPPERS and not _is_inline_span(child):
            yield from flush()
            if source == "zakonyprolidi" and "L0" in _classes(child) and child.find("hr"):
                yield "<hr>"
            else:
                yield from _blocks(child, source, depth)
        else:
            pending.append(_inline_tag(child))
    yield from flush()


def _is_inline_span(tag):
    return tag.name == "span" and not tag.find(["p", "div", "table", "h3", "h4"])


def html_to_text(fragment):
    """Plain text of a cleaned fragment: one block per line, table rows as
    `cell | cell`."""
    soup = BeautifulSoup(fragment, "html.parser")
    for br in soup.find_all("br"):
        br.replace_with("\n")
    # An item's marker hangs in a fixed-width column in the page, so the
    # markup has no space after it; the plain text needs one.
    for marker in soup.select("p.item > span.num"):
        marker.insert_after(" ")
    lines = []
    for block in soup.find_all(recursive=False):
        if block.name == "hr":
            lines.append("")
        elif block.name == "table":
            # A layout table only aligns "(a)" markers with their text.
            sep = " " if "layout" in (block.get("class") or []) else " | "
            for tr in block.find_all("tr"):
                cells = [_WS.sub(" ", c.get_text()).strip() for c in tr.find_all(["td", "th"])]
                lines.append(sep.join(c for c in cells if c))
        else:
            lines.append("\n".join(_WS.sub(" ", part).strip() for part in block.get_text().split("\n")))
    return "\n".join(lines).strip() + "\n"


class Extracted(collections.namedtuple("Extracted", "html text source")):
    __slots__ = ()


def _extract_zakonyprolidi(soup):
    article = soup.find("article", id="idBody_idCtn")
    frags = article.find("div", class_="Frags") if article else None
    if frags is None:
        raise ExtractionError("zakonyprolidi.cz: no article/div.Frags in the page")
    return "\n".join(_blocks(frags, "zakonyprolidi"))


_LEGACY_TITLE = re.compile(r"^EUR-Lex\s*-\s*\w+\s*-\s*[A-Z]{2}\b")


def _extract_eurlex_legacy(soup):
    """Acts from before 2004 have a third kind of page ("Avis juridique
    important"): no classes at all, the text is a plain run of `<p>` under the
    site's own header and language bar. Returns the HTML or None when the page
    is not of that kind."""
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    body = soup.body
    if body is None or not _LEGACY_TITLE.match(title) or len(body.find_all("p")) < 20:
        return None
    for chrome in body.select("div.bglang, div.bgtool, p.bglang, h1, script, style"):
        chrome.decompose()
    return "\n".join(_blocks(body, "eurlex"))


def _extract_eurlex(soup):
    # Search-result and error pages carry the same page chrome, so require the
    # markup that only real acts have: the Official Journal's `oj-*` classes, or
    # the `eli-container` of the consolidated-text page, which has no `div#text`
    # — or, for an act from before 2004, the legacy page (see above).
    root = soup.find("div", id="text") or soup.select_one(".eli-container") or soup.body
    if root is None or not (root.find(class_="eli-container") or root.find(class_="oj-normal")
                            or "eli-container" in _classes(root) or root.find(class_="oj-doc-ti")):
        legacy = _extract_eurlex_legacy(soup)
        if legacy is None:
            raise ExtractionError("eur-lex: no Official Journal text (search/error page?)")
        return legacy
    return "\n".join(_blocks(root, "eurlex"))


# --- Slov-Lex -------------------------------------------------------------
# The page is an Angular app; what is stored is the DOM after a browser ran it
# (fetch_fulltext.py). The act is `div.predpis`: a header (number, type, issuer,
# date, title, enacting formula) followed by nested groups — cast > hlava >
# oddiel > skupinaParagrafov > paragraf > odsek > pismeno > bod — each with an
# `...Oznacenie` (its number/marker), an optional `...Nadpis` (its title) and, for
# the leaves, a `div.text`.
_SLOVLEX_HEADER = ("predpisOznacenie", "predpisTyp", "predpisPodnadpis", "predpisDatum", "predpisNadpis")
_SLOVLEX_HEADINGS = {"cast": "h3", "hlava": "h4", "oddiel": "h4", "skupinaParagrafov": "h4"}
_SLOVLEX_ITEMS = ("odsek", "pismeno", "bod")


def _slovlex_kind(tag):
    classes = _classes(tag)
    return next((k for k in (*_SLOVLEX_HEADINGS, "paragraf", *_SLOVLEX_ITEMS) if k in classes), None)


def _slovlex_child(tag, cls):
    return next((c for c in tag.find_all("div", recursive=False) if cls in _classes(c)), None)


def _slovlex_own(tag, cls):
    """The `cls` element that belongs to this group: found through the
    wrapper divs Slov-Lex puts around parts, but never inside a nested group
    (that one's marker or text is its own)."""
    for child in tag.find_all("div", recursive=False):
        if cls in _classes(child):
            return child
        if _slovlex_kind(child) is None:
            found = _slovlex_own(child, cls)
            if found is not None:
                return found
    return None


def _slovlex_walk(tag, level, out):
    """Appends the HTML blocks of one group (and its sub-groups) to `out`.
    `level` is the depth of items (odsek 0, pismeno 1, bod 2, ...)."""
    kind = _slovlex_kind(tag)
    if kind in _SLOVLEX_HEADINGS:
        label = _slovlex_own(tag, f"{kind}Oznacenie")
        title = _slovlex_own(tag, f"{kind}Nadpis")
        for part in (label, title):
            if part is not None:
                piece = _emit(_SLOVLEX_HEADINGS[kind], None, _inline(part))
                if piece:
                    out.append(piece)
    elif kind == "paragraf":
        label = _slovlex_own(tag, "paragrafOznacenie")
        title = _slovlex_own(tag, "paragrafNadpis")
        if label is not None:
            out.append(_emit("p", "para", _inline(label)))
        if title is not None:
            piece = _emit("h4", None, _inline(title))
            if piece:
                out.append(piece)
        text = _slovlex_own(tag, "text")  # a § that has no (1), (2): its text sits directly in it
        if text is not None:
            piece = _emit("p", None, _inline(text))
            if piece:
                out.append(piece)
    elif kind in _SLOVLEX_ITEMS:
        marker = _slovlex_own(tag, f"{kind}Oznacenie")
        text = _slovlex_own(tag, "text")
        body = _inline(text) if text is not None else ""
        if marker is not None and body.strip():
            num = html.escape(_WS.sub(" ", marker.get_text()).strip(), quote=False)
            out.append(f'<p class="item d{level}"><span class="num">{num}</span>{body.strip()}</p>')
        elif body.strip():
            out.append(_emit("p", f"d{level}" if level else None, body))
        level += 1  # whatever is nested under this item is one level deeper
    for child in tag.find_all(True, recursive=False):
        classes = _classes(child)
        if child.name == "table":
            piece = _table(child, "slovlex", level)
            if piece:
                out.append(piece)
        elif child.name != "div" or any(c.endswith(("Oznacenie", "Nadpis")) or c == "text" for c in classes):
            continue  # already used above (or inline content)
        elif "text2" in classes:
            piece = _emit("p", "center", _inline(child))
            if piece:
                out.append(piece)
        else:
            _slovlex_walk(child, level, out)


def _extract_slovlex(soup):
    root = soup.select_one("div.predpis")
    if root is None or _slovlex_child(root, "predpisOznacenie") is None:
        raise ExtractionError("slov-lex: no act text in the page (an empty shell or a history page)")
    out = []
    for cls in _SLOVLEX_HEADER:
        part = _slovlex_child(root, cls)
        if part is not None:
            piece = _emit("p", "title", _inline(part))
            if piece:
                out.append(piece)
    preamble = _slovlex_child(root, "predpisText")
    if preamble is not None:
        piece = _emit("p", None, _inline(preamble))
        if piece:
            out.append(piece)
    for child in root.find_all("div", recursive=False):
        classes = _classes(child)
        if any(c in _SLOVLEX_HEADER or c == "predpisText" for c in classes):
            continue
        if "text2" in classes:  # the signature after the last section
            piece = _emit("p", "center", _inline(child))
            if piece:
                out.append(piece)
        else:
            _slovlex_walk(child, 0, out)
    return "\n".join(out)


_EXTRACTORS = {"zakonyprolidi": _extract_zakonyprolidi, "eurlex": _extract_eurlex, "slovlex": _extract_slovlex}


def detect_source(url=None, soup=None):
    host = (urlparse(url).hostname or "").lower() if url else ""
    if host.endswith("zakonyprolidi.cz"):
        return "zakonyprolidi"
    if host.endswith("eur-lex.europa.eu"):
        return "eurlex"
    if host.endswith("slov-lex.sk"):
        return "slovlex"
    if host:
        raise Unsupported(f"unsupported source: {host}")
    if soup is not None:
        if soup.find("article", id="idBody_idCtn"):
            return "zakonyprolidi"
        if soup.find("div", id="text") and soup.find(class_=re.compile(r"^(oj-|eli-)")):
            return "eurlex"
        if soup.select_one("div.predpis > div.predpisOznacenie"):
            return "slovlex"
    raise Unsupported("unsupported source: cannot tell the site from the page")


def extract(page_html, url=None):
    """Clean `Extracted(html, text, source)` for a downloaded page."""
    soup = BeautifulSoup(page_html, "html.parser")
    source = detect_source(url, soup)
    fragment = _EXTRACTORS[source](soup)
    if not _has_text(fragment):
        raise ExtractionError(f"{source}: the text container is empty")
    return Extracted(fragment, html_to_text(fragment), source)


def clean_name_source(key, entry, manifest):
    """The download whose file name the clean text takes. Normally the file
    itself; for the HTML alternative of a PDF (field `<field>_html`, see
    fetch_fulltext.html_alternative) it is the PDF — the file a Document points
    at — so that the application finds the text from `file_path` alone."""
    if key.endswith("_html"):
        twin = manifest.get(key[:-len("_html")], {})
        if twin.get("status") == "fetched" and (twin.get("local_path") or "").lower().endswith(".pdf"):
            return twin["local_path"]
    return entry["local_path"]


def run(apply=False, manifest_path=MANIFEST_PATH, output_dir=OUTPUT_DIR, repo_root=REPO_ROOT):
    manifest = json.loads(pathlib.Path(manifest_path).read_text(encoding="utf-8"))
    stats = collections.Counter()
    problems = []
    for key, entry in sorted(manifest.items()):
        local = entry.get("local_path", "")
        if entry.get("status") != "fetched" or not local.lower().endswith(".html"):
            stats["skipped: not a fetched HTML file"] += 1
            continue
        path = repo_root / local
        try:
            result = extract(path.read_text(encoding="utf-8", errors="replace"), entry.get("url"))
        except Unsupported as e:
            stats[f"skipped: {e}"] += 1
            continue
        except (ExtractionError, OSError) as e:
            stats["failed"] += 1
            problems.append((key, str(e)))
            continue
        stats[f"extracted: {result.source}"] += 1
        if apply:
            target = pathlib.Path(output_dir) / pathlib.Path(clean_name_source(key, entry, manifest)).relative_to("data/fulltext")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.with_suffix(".html").write_text(result.html + "\n", encoding="utf-8")
            target.with_suffix(".txt").write_text(result.text, encoding="utf-8")
    return stats, problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--apply", action="store_true",
                        help=f"write the extracted files under {OUTPUT_DIR.relative_to(REPO_ROOT)}/")
    args = parser.parse_args(argv)
    stats, problems = run(apply=args.apply)
    for label, count in sorted(stats.items()):
        print(f"{count:4d}  {label}")
    for key, message in problems:
        print(f"FAILED {key}: {message}")
    if not args.apply:
        print("(dry run — pass --apply to write files)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
