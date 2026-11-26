"""The second layer of the record checks (doc/KONTROLA_ZAZNAMU.md): a language model reads
each record with the evidence we have and says whether it holds together.

check_records.py compares a record with an official register, which exists for the EU
acts, the ISO standards and the documents with an authoritative title. A strategy, a
German or Slovak standard and above all a description written by a model have none.
The model gets the record (identifier, type, language, title, description) and the
evidence (the official title from Cellar or ISO, the ISO abstract, the beginning of the
full text) and answers:

- `title_ok`: does the title name the document the identifier (and the evidence) stand for?
- `description_ok`: does the description describe that document?
- `relevance`: how the document relates to hydrogen technologies (doc/DATABASE_SCOPE.md);
- `problems`: what is wrong, in Czech.

A `no` gives an `error`, relevance `none` a `warning`. Answers are cached in
data/record_check_model_cache.json by the hash of the model, the prompt and the input,
so a rerun sends only the records that changed.

    .venv/bin/python src/tools/check_records_model.py                  # estimate only
    .venv/bin/python src/tools/check_records_model.py --run --sample 40
    .venv/bin/python src/tools/check_records_model.py --run            # all documents

Reads the database and never writes it; the findings go to data/record_checks_model.json.
"""
import argparse
import collections
import concurrent.futures
import datetime
import hashlib
import json
import pathlib
import random
import sys
import threading
import time

import check_records as cr
import document_terms as dterms
import extract_keywords as ek
import fetch_eurovoc
import fetch_ics
import iso_open_data
import state_paths

CACHE_PATH = state_paths.data_file("record_check_model_cache.json")
REPORT_PATH = state_paths.data_file("record_checks_model.json")
MODEL = "gpt-5.5"
PROMPT_VERSION = 1
TEXT_LIMIT = 3000

SYSTEM = """Jsi revizor databáze regulačních předpisů a technických norem pro vodíkové technologie.
Dostaneš jeden záznam databáze (označení, typ, jazyk, název, popis) a podklady, které k němu máme
(úřední název z registru, anotaci normy, začátek plného textu). Část názvů a popisů v databázi
doplnil jazykový model a může být vymyšlená: k číslu předpisu přiřadil název jiného předpisu,
nebo popis neodpovídá dokumentu.

Posuď:
- title_ok: odpovídá název dokumentu, který označuje označení a podklady? "yes", "no", nebo
  "unknown", když podklady nestačí. Odlišná formulace, jazyk nebo zkrácení názvu chybou nejsou;
  chybou je jiný předmět, jiný předpis nebo jiná norma.
- description_ok: popisuje popis tentýž dokument? "yes", "no", "unknown", nebo "none", když popis chybí.
  Obecnost nebo neúplnost chybou není; chybou je jiný předmět nebo tvrzení, které podkladům odporuje.
- relevance: vztah dokumentu k vodíkovým technologiím (výroba, skladování, přeprava, plnění, použití
  vodíku a navazující plynárenství, tlaková zařízení, výbušná prostředí, povolování, životní prostředí):
  "high" (týká se přímo vodíku), "medium" (obecný předpis nebo norma, kterou vodíkový projekt
  použije), "low" (okrajový vztah), "none" (nesouvisí).
- problems: konkrétní problémy česky, každý jednou větou (prázdný seznam, když žádné nejsou).
Odpovídej věcně a jen z předaných údajů."""

SCHEMA = {"name": "record_check", "strict": True, "schema": {
    "type": "object", "additionalProperties": False,
    "required": ["title_ok", "description_ok", "relevance", "problems"],
    "properties": {
        "title_ok": {"type": "string", "enum": ["yes", "no", "unknown"]},
        "description_ok": {"type": "string", "enum": ["yes", "no", "unknown", "none"]},
        "relevance": {"type": "string", "enum": ["high", "medium", "low", "none"]},
        "problems": {"type": "array", "items": {"type": "string"}}}}}


def evidence(doc, acts, keys, cellar, iso_index, texts_dir):
    """The evidence about a document: official title, ISO abstract, beginning of the text."""
    out = {}
    key = keys[doc["id"]]
    celexes = [c for c in acts.get(key, []) if cellar.get(c, {}).get("exists")]
    if len(celexes) == 1:
        titles = cellar[celexes[0]]["titles"]
        out["úřední název (Cellar)"] = titles.get(cr.LANGUAGES.get(doc["language"] or "CS", "CES")) or titles.get("CES") \
            or titles.get("ENG")
    if doc["type"] == "Norma":
        international = fetch_ics.international_part(doc["identifier"])
        record = iso_open_data.lookup(iso_index, international) if international else None
        if record:
            out["název v ISO"] = (record.get("title") or {}).get("en")
            scope = ((record.get("scope") or {}).get("en") or "")
            if scope:
                out["anotace ISO"] = ek._clip(cr.re.sub(r"<[^>]+>", " ", scope), 1500)
    if doc.get("nazev_autoritativni"):
        out["autoritativní název"] = doc["nazev_autoritativni"]
    if doc.get("file_path") and texts_dir:
        clean = texts_dir / (pathlib.Path(doc["file_path"]).stem + ".txt")
        if clean.is_file():
            out["začátek textu"] = ek._clip(clean.read_text(encoding="utf-8", errors="replace"), TEXT_LIMIT)
    return out


def payload(doc, proof):
    return {"označení": doc["identifier"] or "", "typ": doc["type"] or "", "jazyk": doc["language"] or "",
            "název": ek._clip(doc["title"], 600), "popis": ek._clip(doc.get("description") or "", 1500),
            "podklady": proof}


def input_hash(item, model):
    blob = json.dumps([model, PROMPT_VERSION, SYSTEM, item], ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def findings_of(doc, result):
    out = []
    problems = "; ".join(result.get("problems") or [])
    if result["title_ok"] == "no":
        out.append(cr.finding(doc, "model_title", "error", "Model: název neodpovídá dokumentu. " + problems))
    if result["description_ok"] == "no":
        out.append(cr.finding(doc, "model_description", "error", "Model: popis neodpovídá dokumentu. " + problems))
    if result["relevance"] == "none":
        out.append(cr.finding(doc, "model_relevance", "warning", "Model: dokument nesouvisí s vodíkem. " + problems))
    return out


class Checker(ek.Extractor):
    def check(self, item, attempts=3):
        last = None
        for attempt in range(1, attempts + 1):
            try:
                arguments = {"model": self.model, "response_format": {"type": "json_schema", "json_schema": SCHEMA},
                             "messages": [{"role": "system", "content": SYSTEM},
                                          {"role": "user", "content": json.dumps(item, ensure_ascii=False)}]}
                if self.model.startswith(("gpt-4", "gpt-3")):
                    arguments["temperature"] = 0
                else:
                    arguments["reasoning_effort"] = self.reasoning
                completion = self._client().chat.completions.create(**arguments)
                result = json.loads(completion.choices[0].message.content)
                usage = {"prompt_tokens": completion.usage.prompt_tokens,
                         "completion_tokens": completion.usage.completion_tokens}
                with self.lock:
                    self.usage.update(usage)
                return result, usage
            except Exception as error:  # noqa: BLE001 — a failed record stays unchecked
                last = error
                time.sleep(2 * attempt)
        print(f"[warn] model failed: {last}")
        return None, None


def load(cursor):
    documents, linked = cr.load(cursor)
    cursor.execute("SELECT id, COALESCE(NULLIF(popis_autoritativni, ''), NULLIF(description, '')), file_path "
                   "FROM Document")
    extra = {r[0]: (r[1], r[2]) for r in cursor.fetchall()}
    for doc in documents:
        doc["description"], doc["file_path"] = extra[doc["id"]]
    return documents


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--run", action="store_true", help="call the model (only an estimate without it)")
    parser.add_argument("--sample", type=int, default=None, help="a random sample of this many documents")
    parser.add_argument("--ids", default=None, help="only these document ids, comma separated")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--budget", type=float, default=15.0)
    parser.add_argument("--report", default=str(REPORT_PATH))
    args = parser.parse_args(argv)
    conn = dterms.connect(args.env_file)
    try:
        documents = load(conn.cursor())
    finally:
        conn.close()
    rows = [(d["id"], d["identifier"], d["url"], d["type"], d["title"], d["language"], None, None) for d in documents]
    acts, keys = fetch_eurovoc.eu_acts(rows), dterms.document_keys(rows)
    cellar = dterms.load_cache(cr.TITLES_CACHE)
    iso_index = iso_open_data.load_index()
    texts_dir = ek.clean_dir()
    if args.ids:
        wanted = {int(i) for i in args.ids.split(",")}
        documents = [d for d in documents if d["id"] in wanted]
    if args.sample:
        documents = random.Random(args.seed).sample(documents, min(args.sample, len(documents)))
    cache = dterms.load_cache(CACHE_PATH)
    jobs = []
    for doc in documents:
        item = payload(doc, evidence(doc, acts, keys, cellar, iso_index, texts_dir))
        jobs.append((doc, item, input_hash(item, args.model)))
    todo = [j for j in jobs if j[2] not in cache]
    tokens_in = sum(ek.estimate_tokens(SYSTEM) + ek.estimate_tokens(json.dumps(i, ensure_ascii=False)) for _, i, _ in todo)
    tokens_out = 150 * len(todo)
    prices = ek.PRICES.get(args.model)
    usd = ek.cost(tokens_in, tokens_out, args.model) if prices else None
    print(f"documents: {len(jobs)}, to send: {len(todo)}; estimate {tokens_in} + {tokens_out} tokens"
          + (f", about {usd:.2f} USD ({args.model})" if usd is not None else ""))
    if args.run and todo:
        checker = Checker(model=args.model)
        checker._client()
        lock = threading.Lock()
        today = datetime.date.today().isoformat()

        def work(job):
            doc, item, digest = job
            with lock:
                spent = ek.cost(checker.usage["prompt_tokens"], checker.usage["completion_tokens"], args.model)
            if spent >= args.budget:
                return
            result, usage = checker.check(item)
            if result is not None:
                with lock:
                    cache[digest] = {"id": doc["id"], "identifier": doc["identifier"], "model": args.model,
                                     "at": today, "usage": usage, "result": result}
                    if len(cache) % 20 == 0:
                        dterms.save_cache(CACHE_PATH, cache)

        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            list(pool.map(work, todo))
        dterms.save_cache(CACHE_PATH, cache)
        print(f"spent: {ek.cost(checker.usage['prompt_tokens'], checker.usage['completion_tokens'], args.model):.3f} USD")
    findings, answered = [], collections.Counter()
    for doc, item, digest in jobs:
        entry = cache.get(digest)
        if entry:
            answered[entry["result"]["relevance"]] += 1
            findings += findings_of(doc, entry["result"])
    report = {"checked_at": datetime.date.today().isoformat(), "documents": len(jobs),
              "answered": sum(answered.values()), "relevance": dict(answered),
              "counts": dict(collections.Counter(f"{f['severity']}:{f['check']}" for f in findings)),
              "findings": findings}
    pathlib.Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("answered", "relevance", "counts")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
