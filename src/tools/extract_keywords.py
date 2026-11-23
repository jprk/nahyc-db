"""Czech keywords of the documents drawn by a language model (doc/KLICOVA_SLOVA.md).

The documents that have no official keywords — every document except the EU acts,
which have their EuroVoc descriptors (fetch_eurovoc.py) — get 5 to 10 Czech
keywords from the model (OpenAI, gpt-5.5 by default). The model gets only
public data: the designation, the title, the annotation of the catalogue and the
beginning of the full text we have (data/fulltext_clean/ of the main working
tree). The keywords are in Czech whatever the language of the document, so that
a Slovak, German or English standard is found by the same word as a Czech law.

The answers go to data/keyword_model_cache.json, keyed by document_terms.doc_key(),
with the hash of the input: a document is sent again only when its input or the
prompt (PROMPT_VERSION) changes.

    .venv/bin/python src/tools/extract_keywords.py              # estimate only, nothing sent
    .venv/bin/python src/tools/extract_keywords.py --run --limit 20
    .venv/bin/python src/tools/extract_keywords.py --run        # all not in the cache

Reads the database and never writes it; document_terms.py --apply loads the cache.
"""
import argparse
import collections
import concurrent.futures
import datetime
import hashlib
import json
import pathlib
import sys
import threading
import time

import document_terms as dterms
import testdb

MODEL = "gpt-5.5"  # chosen over gpt-4.1 and the mini models by a comparison on 20 standards (2026-11-23)
PRICES = {"gpt-4o-mini": {"input": 0.15, "output": 0.60}, "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
          "gpt-4.1": {"input": 2.00, "output": 8.00}, "gpt-5.4-mini": {"input": 0.75, "output": 4.50},
          "gpt-5.5": {"input": 5.00, "output": 30.00}}  # USD per million tokens
PROMPT_VERSION = 2
ANNOTATION_LIMIT = 2000
TEXT_LIMIT = 5000
API_KEY_PATH = dterms.REPO_ROOT / ".openapi_key"

SYSTEM = """Jsi knihovník odborné databáze regulačních předpisů a technických norem pro vodíkové
technologie (výroba, skladování, přeprava, plnění a použití vodíku, plynárenství, tlaková zařízení,
výbušná prostředí, životní prostředí, doprava). Ke každému dokumentu vrátíš 5 až 10 klíčových slov,
podle kterých ho uživatel databáze vyhledá.

Pravidla:
- Klíčová slova piš česky, i když je dokument slovensky, německy nebo anglicky. Použij ustálené
  české odborné termíny (např. „tlaková láhev“, „výbušná atmosféra“, „čerpací stanice vodíku“).
- Jedno klíčové slovo je podstatné jméno nebo krátká jmenná fráze (1 až 4 slova) v 1. pádě,
  malými písmeny kromě vlastních jmen a zkratek (ATEX, LNG, CNG).
- Pojmenuj předmět dokumentu: látky, zařízení, materiály, procesy, rizika, zkoušky, oblast regulace.
- Nepiš obecná slova („norma“, „předpis“, „požadavky“, „dokument“, „technické údaje“), označení
  dokumentu ani čísla.
- Piš spisovnou češtinou se správným pravopisem a diakritikou. Nenech v klíčovém slově anglické
  ani slovenské slovo („vodíková křehkost“, ne „vodíkové embrittlement“; „litina s kuličkovým
  grafitem“, ne „spheroidalní litina“). Když český termín neznáš, klíčové slovo vynech.
- Vycházej jen z předaných údajů. Když je k dispozici jen název, vrať méně klíčových slov (i jen 3).
- Seřaď je od nejdůležitějšího."""

SCHEMA = {"name": "keywords", "strict": True, "schema": {
    "type": "object", "additionalProperties": False, "required": ["keywords"],
    "properties": {"keywords": {"type": "array", "items": {"type": "string"}}}}}


def clean_dir():
    """data/fulltext_clean/ of this tree, else of the main working tree (only it has the texts)."""
    for root in (dterms.REPO_ROOT, testdb.main_worktree_root(dterms.REPO_ROOT)):
        path = pathlib.Path(root) / "data" / "fulltext_clean"
        if path.is_dir() and any(path.iterdir()):
            return path
    return None


def _clip(text, limit):
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + " …"


def payload(row, texts_dir):
    """The input the model gets for a document row of document_terms.fetch_documents()."""
    doc_id, identifier, url, type_name, title, language, description, file_path = row
    item = {"označení": identifier or "", "typ": type_name or "", "jazyk": language or "",
            "název": _clip(title, 500)}
    if description:
        item["anotace"] = _clip(description, ANNOTATION_LIMIT)
    if file_path and texts_dir:
        clean = texts_dir / (pathlib.Path(file_path).stem + ".txt")
        if clean.is_file():
            item["začátek textu"] = _clip(clean.read_text(encoding="utf-8", errors="replace"), TEXT_LIMIT)
    return item


def input_hash(item, model=MODEL):
    blob = json.dumps([model, PROMPT_VERSION, SYSTEM, item], ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def wanted(documents, eurovoc):
    """The rows to give keywords to: all but the EU acts that have EuroVoc descriptors."""
    out = []
    for row in documents:
        key = dterms.doc_key(row[1], row[2])
        if key and key not in eurovoc:
            out.append((key, row))
    return out


def estimate_tokens(text):
    return len(text) // 3 + 1  # Czech and German run at about three characters per token


def tidy(keywords):
    """Drops empty, duplicate and overlong keywords; at most ten."""
    out, seen = [], set()
    for word in keywords:
        word = " ".join(str(word).split()).strip(" .,;")
        if not word or len(word) > 80 or word.lower() in seen:
            continue
        seen.add(word.lower())
        out.append(word)
    return out[:10]


class Extractor:
    def __init__(self, client=None, model=MODEL, reasoning="low"):
        self.client = client
        self.reasoning = reasoning
        self.lock = threading.Lock()
        self.model = model
        self.usage = collections.Counter()

    def _client(self):
        if self.client is None:
            from openai import OpenAI
            key_path = API_KEY_PATH if API_KEY_PATH.exists() else (
                pathlib.Path(testdb.main_worktree_root(dterms.REPO_ROOT)) / ".openapi_key")
            self.client = OpenAI(api_key=key_path.read_text(encoding="utf-8").strip())
        return self.client

    def keywords(self, item, attempts=3):
        last = None
        for attempt in range(1, attempts + 1):
            try:
                arguments = {"model": self.model, "response_format": {"type": "json_schema", "json_schema": SCHEMA},
                             "messages": [{"role": "system", "content": SYSTEM},
                                          {"role": "user", "content": json.dumps(item, ensure_ascii=False)}]}
                if self.model.startswith(("gpt-4", "gpt-3")):
                    arguments["temperature"] = 0
                else:  # the reasoning models take only their default temperature
                    arguments["reasoning_effort"] = self.reasoning
                completion = self._client().chat.completions.create(**arguments)
                result = json.loads(completion.choices[0].message.content)
                usage = completion.usage
                with self.lock:
                    self.usage.update({"prompt_tokens": usage.prompt_tokens, "completion_tokens": usage.completion_tokens})
                return {"keywords": tidy(result.get("keywords", []))}, {
                    "prompt_tokens": usage.prompt_tokens, "completion_tokens": usage.completion_tokens}
            except Exception as error:  # noqa: BLE001 — a failed document stays without keywords
                last = error
                time.sleep(2 * attempt)
        print(f"[warn] model failed: {last}")
        return None, None


def cost(prompt_tokens, completion_tokens, model=MODEL):
    p = PRICES[model]
    return (prompt_tokens * p["input"] + completion_tokens * p["output"]) / 1_000_000


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--run", action="store_true", help="call the model (only an estimate without it)")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--workers", type=int, default=6, help="requests in parallel")
    parser.add_argument("--budget", type=float, default=15.0, help="stop when the spent USD reach this")
    args = parser.parse_args(argv)
    conn = dterms.connect(args.env_file)
    try:
        documents = dterms.fetch_documents(conn.cursor())
    finally:
        conn.close()
    texts_dir = clean_dir()
    path = dterms.CACHES["model"]
    cache = dterms.load_cache(path)
    eurovoc = dterms.load_cache(dterms.CACHES["eurovoc"])
    todo = []
    for key, row in wanted(documents, eurovoc):
        item = payload(row, texts_dir)
        digest = input_hash(item, args.model)
        if cache.get(key, {}).get("input") != digest:
            todo.append((key, item, digest))
    if args.limit is not None:
        todo = todo[:args.limit]
    tokens_in = sum(estimate_tokens(SYSTEM) + estimate_tokens(json.dumps(i, ensure_ascii=False)) for _, i, _ in todo)
    tokens_out = 60 * len(todo)
    print(f"documents: {len(documents)}, EU acts with EuroVoc: {len(eurovoc)}, to send: {len(todo)} "
          f"(with full text: {sum(1 for _, i, _ in todo if 'začátek textu' in i)}, "
          f"with annotation: {sum(1 for _, i, _ in todo if 'anotace' in i)})")
    print(f"estimate: {tokens_in} input + {tokens_out} output tokens, about "
          f"{cost(tokens_in, tokens_out, args.model):.2f} USD ({args.model}); texts from {texts_dir}")
    if not args.run:
        print("estimate only, nothing sent (--run)")
        return 0
    extractor = Extractor(model=args.model)
    extractor._client()  # once, before the threads
    today = datetime.date.today().isoformat()
    lock = threading.Lock()
    stop = threading.Event()

    def work(n, key, item, digest):
        if stop.is_set():
            return
        with lock:
            spent = cost(extractor.usage["prompt_tokens"], extractor.usage["completion_tokens"], args.model)
        if spent >= args.budget:
            stop.set()
            print(f"budget of {args.budget} USD reached, stopping")
            return
        result, usage = extractor.keywords(item)
        if result is None:
            return
        with lock:
            cache[key] = {"input": digest, "model": args.model, "prompt_version": PROMPT_VERSION, "at": today,
                          "usage": usage, "result": result}
            if n % 20 == 0:
                dterms.save_cache(path, cache)
            print(f"{n}/{len(todo)} {key}: {', '.join(result['keywords'])}", flush=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(lambda job: work(*job), [(n, *t) for n, t in enumerate(todo, 1)]))
    dterms.save_cache(path, cache)
    print(f"spent: {cost(extractor.usage['prompt_tokens'], extractor.usage['completion_tokens'], args.model):.3f} USD "
          f"({extractor.usage['prompt_tokens']} + {extractor.usage['completion_tokens']} tokens)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
