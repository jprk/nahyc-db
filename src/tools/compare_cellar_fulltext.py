"""Checks, for every EUR-Lex full text in `data/fulltext_manifest.json`, that the
same document downloaded from Cellar (the Publications Office's repository,
`src/sites/eurlex.py: fetch_cellar`) is as complete as the stored file —
doc/CELLAR_FULLTEXT.md, 2026-11-20.

The stored files were partly downloaded through a headless browser that passed
EUR-Lex's protection against robots; that path is gone from fetch_fulltext.py,
and an address may be switched to Cellar only where Cellar demonstrably gives
the full text. For each stored file (one row per file, not per manifest key)
the script downloads the Cellar version into `--out` (default
`data/fulltext_mpo_cellar/`) and compares:

- language of the extracted text (langdetect on its beginning);
- length of the extracted text (`extract_fulltext.py`; a PDF through
  `pdf_text.py`, which needs PyMuPDF — run in a subprocess by `--pdf-python`,
  by default `~/.cache/lit-tools/bin/python`);
- number of annexes (lines that are only "PŘÍLOHA …"/"ANNEX …"/"PRÍLOHA …");
- the title (the beginning of both texts, and the act's number in Cellar's).

The result goes to `data/cellar_fulltext_comparison.json` (`--report`), one
record per file with a verdict: `identical` (same bytes), `complete`, or a
reason why not. Already downloaded Cellar files are reused (rerun is cheap).

Usage:
    .venv/bin/python src/tools/compare_cellar_fulltext.py [--limit N] [--old-root DIR ...]
"""
import argparse
import collections
import datetime
import difflib
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))  # src/, for sites/
from sites.eurlex import fetch_cellar  # noqa: E402
import extract_fulltext  # noqa: E402
import fetch_fulltext  # noqa: E402

BASE_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent
MAIN_TREE = pathlib.Path("/home/laborator/DEVEL/nahyc-h2db")
DEFAULT_OUT = REPO_ROOT / "data" / "fulltext_mpo_cellar"
DEFAULT_REPORT = REPO_ROOT / "data" / "cellar_fulltext_comparison.json"
DEFAULT_PDF_PYTHON = pathlib.Path.home() / ".cache" / "lit-tools" / "bin" / "python"

# A line that is only an annex heading: "PŘÍLOHA", "PŘÍLOHA I", "ANNEX II", "Príloha 3".
_ANNEX_LINE = re.compile(r"^\s*(PŘÍLOHA|PRÍLOHA|ANNEX|ANHANG|ANNEXE)(\s+[IVXLC\d]+[a-z]?)?\s*\.?\s*$",
                         re.IGNORECASE | re.MULTILINE)
LENGTH_TOLERANCE = 0.97  # Cellar's text must have at least this share of the stored one's length


def eurlex_groups(manifest):
    """{local_path: [(key, entry), ...]} of the fetched EUR-Lex files, plus
    {key: entry} of the failed EUR-Lex entries (no file to compare)."""
    groups, failed = collections.defaultdict(list), {}
    for key, entry in sorted(manifest.items()):
        if not fetch_fulltext.is_eurlex(entry.get("url")):
            continue
        if entry.get("status") == "fetched" and entry.get("local_path"):
            groups[entry["local_path"]].append((key, entry))
        else:
            failed[key] = entry
    return groups, failed


def find_old_file(local_path, roots):
    """The stored file: `<root>/<local_path>` for the first root that has it,
    else a file of the same name anywhere under `<root>/.claude/worktrees/*/data/`."""
    name = pathlib.PurePath(local_path).name
    for root in roots:
        if (root / local_path).is_file():
            return root / local_path
    for root in roots:
        for found in sorted((root / ".claude" / "worktrees").glob(f"*/data/*/{name}")):
            if found.is_file() and not found.is_symlink():
                return found
    return None


def pdf_text(path, python):
    """Clean text of a PDF, via pdf_text.py in an interpreter that has PyMuPDF."""
    code = ("import sys; sys.path.insert(0, sys.argv[1]); import pdf_text; "
            "sys.stdout.write(pdf_text.extract_pdf(sys.argv[2]).text)")
    done = subprocess.run([str(python), "-c", code, str(BASE_DIR), str(path)],
                          capture_output=True, text=True, timeout=600)
    if done.returncode:
        raise extract_fulltext.ExtractionError(done.stderr.strip().splitlines()[-1] if done.stderr else "failed")
    return done.stdout


def text_of(path, pdf_python):
    """(text, error) of a stored or downloaded file."""
    try:
        if path.suffix.lower() == ".pdf":
            return pdf_text(path, pdf_python), None
        return extract_fulltext.extract(path.read_text(encoding="utf-8", errors="replace"),
                                        "https://eur-lex.europa.eu/").text, None
    except Exception as error:  # noqa: BLE001 - every failure is a finding of the comparison
        return "", f"{type(error).__name__}: {error}"


def text_language(text):
    """ISO code of the text's language (langdetect on its first 5000 characters
    after the Official Journal's header), or None."""
    from language import _detect_text
    code, _ = _detect_text(text[200:5200] or text)
    return code.upper() if code else None


def annex_count(text):
    return len(_ANNEX_LINE.findall(text))


def _norm(text):
    return re.sub(r"\s+", " ", text).strip().lower()


def title_similarity(old, new, chars=400):
    return round(difflib.SequenceMatcher(None, _norm(old)[:chars], _norm(new)[:chars]).ratio(), 2)


def number_in_title(celex, text, chars=1500):
    """True when the number of the act (from its CELEX: 32001L0042 -> 2001/42 or
    42/2001) appears at the beginning of the text, i.e. in its title. Only for
    legislation (sector 3); for other sectors (a COM document, a UNECE regulation)
    the number has no fixed written form, and True is returned."""
    m = re.match(r"^3(\d{4})[A-Z]+0*(\d+)", celex or "")
    if not m:
        return True
    year, number = m.groups()
    head = re.sub(r"\s+", " ", text[:chars])
    return f"{year}/{number}" in head or f"{number}/{year}" in head or f"{year[2:]}/{number}" in head \
        or f"{number}/{year[2:]}" in head


def verdict(row):
    """`identical`, `complete`, or a short reason the Cellar text is not a
    replacement for the stored one."""
    if row.get("cellar_error"):
        return "no Cellar file"
    if row["old_sha256"] and row["old_sha256"] == row["cellar_sha256"]:
        return "identical"
    if row.get("cellar_text_error"):
        return "Cellar text not extractable"
    problems = []
    if row["old_language"] and row["cellar_language"] and row["old_language"] != row["cellar_language"]:
        problems.append(f"language {row['cellar_language']} instead of {row['old_language']}")
    if row["old_length"] and row["cellar_length"] < LENGTH_TOLERANCE * row["old_length"]:
        problems.append(f"shorter ({row['cellar_length']} of {row['old_length']} characters)")
    if row["cellar_annexes"] < row["old_annexes"]:
        problems.append(f"annexes {row['cellar_annexes']} of {row['old_annexes']}")
    if not row["cellar_title_has_number"]:
        problems.append("the act's number not in the title")
    if row["title_similarity"] is not None and row["title_similarity"] < 0.8:
        problems.append(f"different beginning (similarity {row['title_similarity']})")
    if not row["old_length"] and not row.get("old_text_error"):
        problems.append("no stored file to compare")
    return "; ".join(problems) or "complete"


def measure(row, old_text, new_text):
    """Fills the text measurements and the verdict of a row."""
    row.update({
        "old_length": len(old_text), "cellar_length": len(new_text),
        "old_language": text_language(old_text) if old_text else None,
        "cellar_language": text_language(new_text) if new_text else None,
        "old_annexes": annex_count(old_text), "cellar_annexes": annex_count(new_text),
        "title_similarity": title_similarity(old_text, new_text) if old_text else None,
        "cellar_title_has_number": number_in_title(row["celex"], new_text),
    })
    row["verdict"] = verdict(row)
    return row


def reextract(report, pdf_python, html_only=True):
    """Measures the rows of `report` again from the files already stored (after a
    change of the extractor), without downloading anything."""
    for row in report["files"]:
        if not row.get("cellar_file") or (html_only and not row["local_path"].endswith(".html")):
            continue
        old = pathlib.Path(row["old_file"]) if row.get("old_file") else None
        old_text, row["old_text_error"] = text_of(old, pdf_python) if old else ("", None)
        new_text, row["cellar_text_error"] = text_of(REPO_ROOT / row["cellar_file"], pdf_python)
        measure(row, old_text, new_text)
    return report


def compare_group(local_path, members, out_dir, roots, pdf_python, session=None):
    key, entry = members[0]
    url = entry["url"]
    designation = fetch_fulltext.designation_of(key)
    row = {"local_path": local_path, "keys": [k for k, _ in members], "url": url, "designation": designation}
    old = find_old_file(local_path, roots)
    row["old_file"] = str(old) if old else None
    old_bytes = old.read_bytes() if old else b""
    row["old_sha256"] = hashlib.sha256(old_bytes).hexdigest() if old else None
    old_text, row["old_text_error"] = text_of(old, pdf_python) if old else ("", None)

    info = _cache_info(out_dir).get(url)
    cached = bool(info and (out_dir / info["file"]).is_file())
    if cached:
        cellar_path = out_dir / info["file"]
    else:
        found = fetch_cellar(url, session=session)
        if not found:
            row["cellar_error"] = "fetch_cellar returned nothing"
            row["verdict"] = verdict(row)
            return row, True
        content = found["content"]
        ok, reason = fetch_fulltext.is_document_page(url, content, found["content_type"], designation)
        if not ok:
            row["cellar_error"] = reason
            row["verdict"] = verdict(row)
            return row, True
        ext = fetch_fulltext.extension_from_url(url, found["content_type"])
        if ext == "bin" or (ext == "html" and "pdf" in found["content_type"]):
            ext = "pdf" if "pdf" in found["content_type"] else "html"
        sha = hashlib.sha256(content).hexdigest()
        cellar_path = out_dir / fetch_fulltext.flat_name(designation, sha, ext)
        cellar_path.write_bytes(content)
        info = {"file": cellar_path.name, "celex": found["celex"], "items": found["items"],
                "content_type": found["content_type"]}
        _remember(out_dir, url, info)
    cellar_bytes = cellar_path.read_bytes()
    row.update({"cellar_file": str(cellar_path.relative_to(REPO_ROOT)), "celex": info["celex"],
                "cellar_items": info["items"], "cellar_sha256": hashlib.sha256(cellar_bytes).hexdigest()})
    new_text, row["cellar_text_error"] = text_of(cellar_path, pdf_python)
    measure(row, old_text, new_text)
    return row, not cached


_CACHE = "_cellar_downloads.json"


def _cache_info(out_dir):
    path = out_dir / _CACHE
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _remember(out_dir, url, info):
    cache = _cache_info(out_dir)
    cache[url] = info
    (out_dir / _CACHE).write_text(json.dumps(cache, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")


SWITCHED = ("identical", "complete")


def switch_manifest(manifest, report, now=None):
    """Points every manifest entry of a file whose Cellar version is verified
    (`identical` or `complete`) at the Cellar file, as `data/fulltext/<name>`
    (the file is copied there after the merge), and marks it `"via": "cellar"`
    with its CELEX. The other entries keep their stored file and get
    `"cellar_check"` with the reason. Returns (switched keys, kept keys)."""
    now = now or datetime.datetime.now().isoformat(timespec="seconds")
    switched, kept = [], []
    for row in report["files"]:
        for key in row["keys"]:
            entry = manifest.get(key)
            if not entry or entry.get("status") != "fetched" or entry.get("local_path") != row["local_path"]:
                continue
            if row["verdict"] in SWITCHED:
                name = pathlib.PurePath(row["cellar_file"]).name
                entry.update({"local_path": f"data/fulltext/{name}", "sha256": row["cellar_sha256"],
                              "via": "cellar", "celex": row["celex"], "http_status": 200, "fetched_at": now})
                entry.pop("cellar_check", None)
                switched.append(key)
            else:
                entry["cellar_check"] = row["verdict"]
                kept.append(key)
    return switched, kept


VERDICT_CS = {"identical": "shodné", "complete": "úplné", "no Cellar file": "Cellar nedal soubor",
              "Cellar text not extractable": "text z Cellaru nečitelný"}


def _verdict_cs(verdict):
    if verdict in VERDICT_CS:
        return VERDICT_CS[verdict]
    out = verdict
    for en, cs in (("language", "jazyk"), ("instead of", "místo"), ("shorter", "kratší"), ("of", "z"),
                   ("characters", "znaků"), ("annexes", "přílohy"), ("the act's number not in the title",
                   "číslo aktu není v názvu"), ("different beginning (similarity", "jiný začátek (podobnost"),
                   ("no stored file to compare", "chybí uložený soubor")):
        out = re.sub(rf"\b{re.escape(en)}\b" if en.isalpha() else re.escape(en), cs, out)
    return out


def _old_source(row):
    url = row["url"]
    if "CELEX" in url.upper():
        how = "CELEX"
    elif "/eli/" in url:
        how = "ELI"
    elif "uri=OJ:" in url:
        how = "Úř. věstník"
    else:
        how = "jiná"
    return f"{how}, {row['local_path'].rsplit('.', 1)[-1].upper()}"


def markdown_table(report):
    """The table of doc/CELLAR_FULLTEXT.md: one row per stored file."""
    lines = ["| Dokument | Starý zdroj | Cellar (CELEX) | Jazyk | Délka stará | Délka Cellar | Přílohy | Verdikt |",
             "|---|---|---|---|--:|--:|--:|---|"]
    for row in sorted(report["files"], key=lambda r: (r["designation"], r["local_path"])):
        language = row.get("old_language") or "–"
        if row.get("cellar_language") and row.get("cellar_language") != row.get("old_language"):
            language += f" → {row['cellar_language']}"
        annexes = (f"{row.get('old_annexes', 0)} / {row.get('cellar_annexes', 0)}"
                   if "cellar_annexes" in row else "–")
        verdict_cs = _verdict_cs(row["verdict"])
        if row["verdict"] == "complete" and row.get("old_length") \
                and row["cellar_length"] > 1.03 * row["old_length"]:
            verdict_cs += "; uložený soubor neúplný"
        lines.append(f"| {row['designation']} | {_old_source(row)} | {row.get('celex') or '–'} | {language} | "
                     f"{row.get('old_length', '–')} | {row.get('cellar_length', '–')} | {annexes} | "
                     f"{verdict_cs} |")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    parser.add_argument("--report", type=pathlib.Path, default=DEFAULT_REPORT)
    parser.add_argument("--old-root", type=pathlib.Path, action="append", default=[],
                        help="where the stored files are (default: this tree and the main tree)")
    parser.add_argument("--pdf-python", type=pathlib.Path, default=DEFAULT_PDF_PYTHON)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--redo-missing", action="store_true",
                        help="reuse the rows of an existing --report and compare only those without a Cellar file")
    parser.add_argument("--reextract", action="store_true",
                        help="measure the HTML rows of an existing --report again from the stored files")
    parser.add_argument("--switch", action="store_true",
                        help="point the verified manifest entries of an existing --report at the Cellar files")
    parser.add_argument("--table", action="store_true",
                        help="only print the Markdown table of an existing --report and exit")
    args = parser.parse_args(argv)
    if args.reextract:
        report = reextract(json.loads(args.report.read_text(encoding="utf-8")), args.pdf_python)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
        print(collections.Counter(r["verdict"].split(" (")[0] for r in report["files"]))
        return
    if args.switch:
        report = json.loads(args.report.read_text(encoding="utf-8"))
        manifest = json.loads(fetch_fulltext.MANIFEST_PATH.read_text(encoding="utf-8"))
        switched, kept = switch_manifest(manifest, report)
        fetch_fulltext.save_manifest(manifest)
        print(f"{len(switched)} manifest entries switched to Cellar, {len(kept)} kept with cellar_check")
        return
    if args.table:
        print(markdown_table(json.loads(args.report.read_text(encoding="utf-8"))))
        return
    roots = args.old_root or [REPO_ROOT, MAIN_TREE]
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(fetch_fulltext.MANIFEST_PATH.read_text(encoding="utf-8"))
    groups, failed = eurlex_groups(manifest)
    import requests
    session = requests.Session()
    previous = {}
    if args.redo_missing and args.report.exists():  # keep the rows that have a Cellar file
        previous = {r["local_path"]: r for r in json.loads(args.report.read_text(encoding="utf-8"))["files"]
                    if r["verdict"] != "no Cellar file"}
    rows = []
    for number, (local_path, members) in enumerate(sorted(groups.items())):
        if args.limit is not None and number >= args.limit:
            break
        if local_path in previous:
            rows.append(previous[local_path])
            continue
        row, fetched = compare_group(local_path, members, args.out, roots, args.pdf_python, session)
        rows.append(row)
        print(f"{row['designation']:<40} {local_path.rsplit('.', 1)[-1]:<4} {row.get('old_length', '-')!s:>8} "
              f"{row.get('cellar_length', '-')!s:>8}  {row['verdict']}", flush=True)
        if fetched:
            time.sleep(fetch_fulltext.SLEEP_SECONDS)
    failed_rows = []
    for key, entry in failed.items():
        found = fetch_cellar(entry.get("url", ""), session=session)
        failed_rows.append({"key": key, "url": entry.get("url"), "error": entry.get("error"),
                            "cellar": bool(found), "celex": found and found["celex"],
                            "content_type": found and found["content_type"]})
        time.sleep(fetch_fulltext.SLEEP_SECONDS)
    report = {"generated": datetime.datetime.now().isoformat(timespec="seconds"),
              "files": rows, "failed_entries": failed_rows}
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    print(collections.Counter(r["verdict"].split(" (")[0] for r in rows))


if __name__ == "__main__":
    main()
