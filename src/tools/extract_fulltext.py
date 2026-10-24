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
Slov-Lex and PDFs are NOT handled here (doc/PLAN.md, issue #2 open
questions).

Output vocabulary (everything else is dropped or unwrapped): `h3`, `h4`,
`p` (class `l1`..`l5`, `para`, `note`, `title`, `center`), `hr`, `table`
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
                   "oj-sub": "sub", "oj-super": "sup"}

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


def _table(tag, source):
    cls = "data" if "oj-table" in _classes(tag) or source == "zakonyprolidi" else "layout"
    rows = []
    for tr in tag.find_all("tr"):
        # Nested tables are flattened by their own row; only direct cells here.
        cells = []
        for cell in tr.find_all(["td", "th"], recursive=False):
            span = "".join(f' {a}="{int(cell[a])}"' for a in ("colspan", "rowspan")
                           if str(cell.get(a, "")).isdigit() and int(cell[a]) > 1)
            body = "".join(_blocks(cell, source)) or _inline(cell).strip()
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
}
# Document-header furniture (date, language, "Official Journal ...", page).
_EURLEX_SKIP = {"oj-hd-date", "oj-hd-lg", "oj-hd-ti", "oj-hd-oj", "oj-hd-coll",
                "oj-hd-uniq", "oj-separator"}


def _eurlex_block(tag):
    if tag.name != "p":
        return {"h1": ("h3", None), "h2": ("h3", None), "h3": ("h3", None),
                "h4": ("h4", None)}.get(tag.name)
    cls = _classes(tag)
    for c in cls:
        if c in _EURLEX_CLASSES:
            return _EURLEX_CLASSES[c]
    return "p", None


_BLOCK_RULES = {"zakonyprolidi": _zakonyprolidi_block, "eurlex": _eurlex_block}


def _blocks(node, source):
    """Yields the HTML of the block-level content of `node`, in order."""
    rule = _BLOCK_RULES[source]
    pending = []  # loose inline content between blocks

    def flush():
        if pending:
            text = "".join(pending)
            pending.clear()
            piece = _emit("p", None, text)
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
        if child.name == "hr":
            yield from flush()
            yield "<hr>"
        elif child.name == "table":
            yield from flush()
            if source == "eurlex" and child.find(class_="oj-hd-ti"):
                continue  # the Official Journal page header table
            piece = _table(child, source)
            if piece:
                yield piece
        elif (mapped := rule(child)) is not None:
            yield from flush()
            piece = _emit(mapped[0], mapped[1], _inline(child))
            if piece:
                yield piece
        elif child.name in _BLOCK_WRAPPERS and not _is_inline_span(child):
            yield from flush()
            if source == "zakonyprolidi" and "L0" in _classes(child) and child.find("hr"):
                yield "<hr>"
            else:
                yield from _blocks(child, source)
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


def _extract_eurlex(soup):
    # The text container also exists on search-result and error pages, so
    # require the Official Journal markup that only real acts carry.
    root = soup.find("div", id="text")
    if root is None or not (root.find(class_="eli-container") or root.find(class_="oj-normal")):
        raise ExtractionError("eur-lex: no Official Journal text (search/error page?)")
    return "\n".join(_blocks(root, "eurlex"))


_EXTRACTORS = {"zakonyprolidi": _extract_zakonyprolidi, "eurlex": _extract_eurlex}


def detect_source(url=None, soup=None):
    host = (urlparse(url).hostname or "").lower() if url else ""
    if host.endswith("zakonyprolidi.cz"):
        return "zakonyprolidi"
    if host.endswith("eur-lex.europa.eu"):
        return "eurlex"
    if host:
        raise Unsupported(f"unsupported source: {host}")
    if soup is not None:
        if soup.find("article", id="idBody_idCtn"):
            return "zakonyprolidi"
        if soup.find("div", id="text") and soup.find(class_=re.compile(r"^(oj-|eli-)")):
            return "eurlex"
    raise Unsupported("unsupported source: cannot tell the site from the page")


def extract(page_html, url=None):
    """Clean `Extracted(html, text, source)` for a downloaded page."""
    soup = BeautifulSoup(page_html, "html.parser")
    source = detect_source(url, soup)
    fragment = _EXTRACTORS[source](soup)
    if not _has_text(fragment):
        raise ExtractionError(f"{source}: the text container is empty")
    return Extracted(fragment, html_to_text(fragment), source)


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
            target = pathlib.Path(output_dir) / pathlib.Path(local).relative_to("data/fulltext")
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
