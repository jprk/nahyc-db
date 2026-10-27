"""Citation closure: which documents that the texts in the database cite are
not in the database themselves (doc/DATABASE_SCOPE.md, odstavec 7, krok 1).

Every clean full text (`data/fulltext_clean/`) is searched for citations of
Czech acts (`N/RRRR Sb.`), international treaties (`N/RRRR Sb. m. s.`), Slovak
acts (`N/RRRR Z. z.`), EU acts (`(EU) 2019/943`, `(ES) č. 1907/2006`,
`2012/18/EU`, ...) and standards (`ČSN EN ISO 19880-1`, `IEC 60079-10-1`). Each
citation is reduced to a key that does not depend on how it is written (an EU act
to its year and number, a standard to its international designation without the
national prefix), and the keys are compared with the keys of the documents in
the database (their `identifier`; the title when there is none).

What a citation says about relevance is weak: a consolidated Czech act cites
every act that ever amended it. The result is therefore a ranked list, not a
verdict — a document cited by many documents of the database is more likely to
belong in it than one cited once — and the closure is reported for every
threshold of "cited by at least k documents". A document and its language
variant (`… [EN]`) count as one citing document.

Read-only: it reads the database and the clean texts and writes
data/citation_closure.json (everything) and data/citation_closure_candidates.csv
(the candidates for a person to decide on, see write_candidates).

Usage: .venv/bin/python src/tools/citation_closure.py [--env-file FILE] [--top N]
"""
import argparse
import collections
import datetime
import json
import pathlib
import re

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
CLEAN_DIR = REPO_ROOT / "data" / "fulltext_clean"
OUTPUT_PATH = REPO_ROOT / "data" / "citation_closure.json"
CANDIDATES_PATH = REPO_ROOT / "data" / "citation_closure_candidates.csv"

YEAR_MIN, YEAR_MAX = 1950, 2035

_CZ = re.compile(r"(?<![\d/])(\d{1,4})\s*/\s*(\d{4})\s*Sb\.(\s*m\.\s*s\.)?")
_SK = re.compile(r"(?<![\d/])(\d{1,4})\s*/\s*(\d{4})\s*Z\.\s*z\.")
_EU_BODY = r"EU|ES|EC|EÚ|EHS|EEC|ESUO|ECSC|Euratom"
_EU_BRACKET = re.compile(r"\((?:" + _EU_BODY + r")\)\s*(č\.|No\.?|n\.)?\s*(\d{1,4})\s*/\s*(\d{1,4})(?![\d/])", re.I)
_EU_SUFFIX = re.compile(r"(?<![\d/])(\d{2,4})/(\d{1,4})/(?:" + _EU_BODY + r")\b", re.I)
_EU_KIND = re.compile(r"(nařízení|nariadenie|nariadenia|regulation|směrnice|směrnic|smernice|smernica|directive"
                      r"|rozhodnutí|rozhodnutie|decision)", re.I)
_NORM = re.compile(r"\b(?:(?:ČSN|CSN|STN|DIN|BS|NF)\s+)?((?:EN|ISO|IEC)(?:\s*/\s*(?:ISO|IEC))?(?:\s+(?:ISO|IEC))?)"
                   r"\s+(\d{3,5}(?:-\d{1,3}){0,3})\b")
_KINDS = {"nař": "regulation", "nari": "regulation", "regu": "regulation", "smě": "directive", "sme": "directive",
          "dire": "directive", "rozh": "decision", "deci": "decision"}

Citation = collections.namedtuple("Citation", "key family display kind position")


def _year(text):
    year = int(text)
    if len(text) == 2:  # "98/34/ES", "(EHS) č. 1408/71": the EU numbering before 2000
        year += 1900
    return year


def _plausible(text):
    return len(text) in (2, 4) and (len(text) == 2 or YEAR_MIN <= int(text) <= YEAR_MAX)


def _eu_kind(text, position):
    before = text[max(0, position - 120):position]
    found = list(_EU_KIND.finditer(before))
    if not found:
        return None
    word = found[-1].group(1).lower()
    return next((kind for prefix, kind in _KINDS.items() if word.startswith(prefix)), None)


def citations(text):
    """[Citation] of the acts and standards cited in `text`, in order."""
    found = []
    for m in _CZ.finditer(text):
        family = "CZ-MS" if m.group(3) else "CZ"
        number, year = int(m.group(1)), int(m.group(2))
        suffix = "Sb. m. s." if m.group(3) else "Sb."
        found.append(Citation(f"{family}:{number}/{year}", family, f"{number}/{year} {suffix}", None, m.start()))
    for m in _SK.finditer(text):
        number, year = int(m.group(1)), int(m.group(2))
        found.append(Citation(f"SK:{number}/{year}", "SK", f"{number}/{year} Z. z.", None, m.start()))
    for m in _EU_BRACKET.finditer(text):
        first, second = m.group(2), m.group(3)
        if m.group(1) or not _plausible(first) or (len(first) == 4 and not YEAR_MIN <= int(first) <= YEAR_MAX):
            number, year = first, second  # "(ES) č. 1907/2006", "(ES) 1907/2006": number first
        else:
            year, number = first, second  # "(EU) 2019/943": since 2015 the year comes first
        if not _plausible(year):
            continue
        year = _year(year)
        found.append(Citation(f"EU:{year}/{int(number)}", "EU", f"{year}/{int(number)}", _eu_kind(text, m.start()), m.start()))
    for m in _EU_SUFFIX.finditer(text):
        if not _plausible(m.group(1)):
            continue
        year = _year(m.group(1))
        found.append(Citation(f"EU:{year}/{int(m.group(2))}", "EU", f"{year}/{int(m.group(2))}",
                              _eu_kind(text, m.start()), m.start()))
    for m in _NORM.finditer(text):
        organisation = re.sub(r"\s+", " ", m.group(1).replace(" /", "/").replace("/ ", "/"))
        display = f"{organisation} {m.group(2)}"
        found.append(Citation(f"NORM:{display}", "NORM", display, None, m.start()))
    return sorted(found, key=lambda c: c.position)


def own_keys(identifier, title):
    """The keys a document of the database is known by: those in its identifier; a
    bare `N/RRRR` (e.g. "Nařízení vlády 133/2005") is a Czech act; without an
    identifier, the first key of its title."""
    keys = {c.key for c in citations(identifier or "")}
    if identifier and not keys:
        m = re.search(r"(?<![\d/])(\d{1,4})/(\d{4})(?![\d/])", identifier)
        if m:
            keys.add(f"CZ:{int(m.group(1))}/{int(m.group(2))}")
    if not keys and not identifier and title:
        first = citations(title[:300])
        if first:
            keys.add(first[0].key)
    return keys


_AMENDMENT = re.compile(r"(?:ve znění|ve zneni|v znení|as amended by|změněn[ýé]?|změna:|novel|zavedeno zákonem"
                        r"|zavedena zákonem|zavedeny zákonem)[^;§]{0,200}$", re.I)


def is_amendment(text, citation):
    """True when the citation follows a phrase that introduces amending acts ("ve
    znění zákona č. …", "v znení", "as amended by", "Přechodná ustanovení zavedena
    zákonem č. …"): such an act is cited for its history, not for its content, and is
    a weak candidate. A long list continues beyond the phrase; see `closure`."""
    return bool(_AMENDMENT.search(text[max(0, citation.position - 220):citation.position]))


def title_hint(text, citation):
    """A few words around the first citation, to recognise the act in the report."""
    start = max(0, citation.position - 60)
    return re.sub(r"\s+", " ", text[start:citation.position + 140]).strip()


def closure(documents, texts):
    """The report for `documents` — [(id, identifier, title)] — and `texts` —
    {id: clean text} of those that have one."""
    known = collections.defaultdict(set)  # key -> ids of documents with that key
    unit = {}  # id -> the citing unit (a document and its language variant are one)
    for doc_id, identifier, title in documents:
        keys = own_keys(identifier, title)
        for key in keys:
            known[key].add(doc_id)
        unit[doc_id] = min(keys) if keys else f"doc:{doc_id}"
    cited = collections.defaultdict(lambda: {"units": set(), "documents": set(), "hint": None, "kind": None,
                                             "citations": 0, "as_amendment": 0})
    for doc_id, text in texts.items():
        own = own_keys(*next((i, t) for d, i, t in documents if d == doc_id))
        previous, previous_amendment = None, False
        for citation in citations(text):
            # a citation right after an amending one ("…, zákona č. 124/2000 Sb., zákona č. …") is in the same list
            amendment = is_amendment(text, citation) or (
                previous_amendment and citation.position - previous.position < 45
                and not re.search(r"[;§]", text[previous.position:citation.position]))
            previous, previous_amendment = citation, amendment
            if citation.key in own:
                continue
            entry = cited[citation.key]
            entry["units"].add(unit.get(doc_id, f"doc:{doc_id}"))
            entry["documents"].add(doc_id)
            entry["kind"] = entry["kind"] or citation.kind
            entry["citations"] += 1
            entry["as_amendment"] += amendment
            if entry["hint"] is None:
                entry["hint"] = title_hint(text, citation)
            entry.setdefault("family", citation.family)
            entry.setdefault("display", citation.display)
    rows = []
    for key, entry in cited.items():
        rows.append({"key": key, "family": entry["family"], "designation": entry["display"], "kind": entry["kind"],
                     "in_database": key in known, "database_ids": sorted(known.get(key, ())),
                     "cited_by": len(entry["units"]), "citing_ids": sorted(entry["documents"]),
                     "amendment_share": round(entry["as_amendment"] / entry["citations"], 2), "context": entry["hint"]})
    rows.sort(key=lambda r: (-r["cited_by"], r["family"], r["key"]))
    return rows


def summary(rows, thresholds=(1, 2, 3, 5)):
    """{family: {k: {cited, in_database, share}}}: the closure among the documents cited
    by at least k citing documents."""
    result = {}
    for family in sorted({r["family"] for r in rows}) + ["all"]:
        result[family] = {}
        for k in thresholds:
            group = [r for r in rows if r["cited_by"] >= k and (family == "all" or r["family"] == family)]
            present = sum(1 for r in group if r["in_database"])
            result[family][k] = {"cited": len(group), "in_database": present,
                                 "share": round(present / len(group), 3) if group else None}
    return result


def write_candidates(rows, path=CANDIDATES_PATH, minimum=2):
    """A sheet for a person to decide on: the documents not in the database, cited by at
    least `minimum` documents and not mostly as amending acts, with an empty
    `rozhodnuti` column (v rozsahu / mimo rozsah / zrušený)."""
    import csv
    chosen = [r for r in rows if not r["in_database"] and r["cited_by"] >= minimum and r["amendment_share"] < 0.5]
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["family", "designation", "kind", "cited_by", "amendment_share", "context", "citing_ids", "rozhodnuti"])
        for r in chosen:
            writer.writerow([r["family"], r["designation"], r["kind"] or "", r["cited_by"], r["amendment_share"],
                             r["context"], " ".join(map(str, r["citing_ids"])), ""])
    return len(chosen)


def load_from_database(env_file=None, clean_dir=CLEAN_DIR):
    import pymysql
    from dotenv import dotenv_values
    import testdb
    env = dotenv_values(env_file or str(testdb.find_env_file(".env")))
    conn = pymysql.connect(host=env["DB_HOST"], port=int(env.get("DB_PORT") or 3306), user=env["DB_USER"],
                           password=env["DB_PASSWORD"], database=env["DB_NAME"])
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, identifier, title, file_path FROM Document")
            rows = cur.fetchall()
    finally:
        conn.close()
    documents = [(doc_id, identifier, title) for doc_id, identifier, title, _ in rows]
    texts = {}
    for doc_id, _identifier, _title, file_path in rows:
        if file_path:
            clean = pathlib.Path(clean_dir) / (pathlib.Path(file_path).stem + ".txt")
            if clean.is_file():
                texts[doc_id] = clean.read_text(encoding="utf-8")
    return documents, texts, env["DB_NAME"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--env-file", default=None, help="database account (default: .env)")
    parser.add_argument("--top", type=int, default=30, help="how many missing documents to print")
    args = parser.parse_args(argv)
    documents, texts, database = load_from_database(args.env_file)
    rows = closure(documents, texts)
    stats = summary(rows)
    OUTPUT_PATH.write_text(json.dumps({
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"), "database": database,
        "documents": len(documents), "documents_with_text": len(texts), "summary": stats, "cited": rows,
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(texts)} texts of {len(documents)} documents; {len(rows)} distinct documents cited")
    for family, by_k in stats.items():
        print(f"  {family:6} " + "  ".join(f"≥{k}: {v['in_database']}/{v['cited']}" for k, v in by_k.items()))
    print(f"most cited documents not in the database (top {args.top}):")
    for row in [r for r in rows if not r["in_database"]][:args.top]:
        print(f"  {row['cited_by']:3}  {row['family']:5} {row['designation']:22} {row['kind'] or '':10} "
              f"{'amend.' if row['amendment_share'] >= 0.5 else '':6} {row['context'][:80]}")
    count = write_candidates(rows)
    print(f"written: {OUTPUT_PATH.relative_to(REPO_ROOT)}, {CANDIDATES_PATH.relative_to(REPO_ROOT)} ({count} candidates)")


if __name__ == "__main__":
    main()
