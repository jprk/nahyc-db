"""Descriptions of the legal acts from their own text (issue #37, doc/ANOTACE_PREDPISU.md).

Most acts had as their description only their full title (the source surveys put it in
the annotation column; e-Sbírka and zakonyprolidi.cz publish no annotation), EU acts
often none or a text a language model wrote earlier. Principle 7 of doc/PROVOZ.md: a
description comes from the source or from the text of the document; what a model
derives is marked unverified.

For every act (law, decree, government regulation, EU directive, regulation, decision)
with a clean full text (data/fulltext_clean/):

1. **The opening provision, word for word** (act_provisions.opening_provision()):
   "§ 1 Předmět úpravy", "Článek 1 Předmět" … — the description, with its source
   (`popis_zdroj`: "§ 1 Předmět úpravy, doslova z textu předpisu").
2. **Located by a model** (`--locate`), when the first provision does not describe the
   act (an amending act, definitions, transposition list): the model gets the beginning
   of the text and returns, word for word, the provision that says what the act does,
   or none. The quote is kept only when it occurs in the text as it stands.
3. **An approximate summary** (`--summarize`), when no provision serves: a model writes
   2–4 Czech sentences from the text, a second, different model checks them against
   the text and corrects spelling; a summary the checker rejects is dropped. The summary
   goes to `popis_priblizny` (shown as "Přibližné shrnutí, neověřeno"), the record is
   flagged "popis je třeba doplnit ručně".

A description that only restates the title (`restates_title()`) is dropped; a
description an editor set (data/manual_corrections.json) is never touched. The results
are cached in data/act_descriptions.json (keyed like document_terms.document_keys());
build_unified_db.py applies them on every rebuild, `--apply` writes them to a database.

    .venv/bin/python src/tools/annotate_acts.py                         # the provisions, report only
    .venv/bin/python src/tools/annotate_acts.py --locate --summarize    # + estimate of the model steps
    .venv/bin/python src/tools/annotate_acts.py --locate --summarize --run
    .venv/bin/python src/tools/annotate_acts.py --apply --env-file .env.test
"""
import argparse
import collections
import concurrent.futures
import datetime
import hashlib
import json
import pathlib
import re
import sys
import threading
import time

import act_provisions as ap
import document_terms as dterms
import extract_keywords as ek
import state_paths

CACHE_PATH = state_paths.data_file("act_descriptions.json")
LEGAL_TYPES = ap.LEGAL_TYPES
LOCATE_MODEL = "gpt-5.5"
SUMMARY_MODEL = "gpt-5.5"
CHECK_MODEL = "gpt-5.4"  # a different model checks the summary (issue #37)
PROMPT_VERSION = 2
EXCERPT = 25000
MANUAL_REASON = ap.MANUAL_REASON
restates_title = ap.restates_title
outcome = ap.description_of


def text_sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def normalize_space(text):
    return " ".join((text or "").split())


# --- the model steps --------------------------------------------------------

LOCATE_SYSTEM = """Dostaneš začátek textu právního předpisu (český, slovenský nebo předpis EU).
Najdi v něm jednu pasáž, která celým větami říká, co předpis upravuje, stanoví, na co se vztahuje
nebo jaký má účel – typicky „Tento zákon upravuje …“, „Tato směrnice stanoví …“, „Účelem tohoto
nařízení je …“, „Toto nařízení se vztahuje na …“. U novely, která takovou větu nemá, smíš vybrat bod
odůvodnění, který jednou až třemi větami říká, co a proč novela mění („Tato směrnice mění …, aby …“).
NEVYBÍREJ: výčet změn („… se mění takto:“, „… se nahrazuje …“), definice pojmů, úvodní větu typu
„Ministerstvo … stanoví podle § …:“, název předpisu, výjimky z působnosti, poznámky pod čarou.
Pasáž vrať DOSLOVA, beze změny jediného znaku, jako souvislý úsek textu (nejvýše 1500 znaků), a její
označení (např. „§ 2“, „čl. 3 odst. 1“, „bod odůvodnění 17“). Když taková pasáž v textu není,
vrať found=false. Nic nevymýšlej a nepiš vlastní text."""
LOCATE_SCHEMA = {"name": "provision", "strict": True, "schema": {
    "type": "object", "additionalProperties": False, "required": ["found", "quote", "label"],
    "properties": {"found": {"type": "boolean"}, "quote": {"type": "string"}, "label": {"type": "string"}}}}

SUMMARY_SYSTEM = """Jsi právník. Dostaneš označení, název a začátek textu právního předpisu. Napiš česky
2 až 4 věty, co předpis upravuje: předmět, koho se týká, hlavní povinnosti nebo nástroje. U novely
napiš, který předpis mění a v čem. Piš věcně, spisovnou češtinou, bez hodnocení. Uváděj jen to, co
z předaného textu plyne; nevymýšlej čísla, lhůty ani výjimky. Nepiš úvod typu „Tento dokument“ –
začni přímo podmětem („Zákon upravuje …“, „Směrnice stanoví …“)."""
SUMMARY_SCHEMA = {"name": "summary", "strict": True, "schema": {
    "type": "object", "additionalProperties": False, "required": ["summary"],
    "properties": {"summary": {"type": "string"}}}}

CHECK_SYSTEM = """Jsi kontrolor. Dostaneš začátek textu právního předpisu a jeho krátké shrnutí, které
napsal jiný jazykový model. Posuď, zda každé tvrzení shrnutí plyne z předaného textu, a oprav
pravopis, gramatiku a terminologii (spisovná čeština). Vrať:
- verdict: "ok" (shrnutí sedí, jen případně opravený pravopis), "reject" (shrnutí obsahuje tvrzení,
  které z textu neplyne nebo mu odporuje, nebo popisuje jiný předpis);
- corrected: shrnutí s opraveným pravopisem (při "reject" prázdné);
- problems: zjištěné nedostatky, každý jednou větou česky (prázdný seznam, když nejsou)."""
CHECK_SCHEMA = {"name": "check", "strict": True, "schema": {
    "type": "object", "additionalProperties": False, "required": ["verdict", "corrected", "problems"],
    "properties": {"verdict": {"type": "string", "enum": ["ok", "reject"]}, "corrected": {"type": "string"},
                   "problems": {"type": "array", "items": {"type": "string"}}}}}


class Models(ek.Extractor):
    """Model calls with the client, retries and usage of extract_keywords.Extractor."""

    def ask(self, model, system, schema, payload, attempts=3):
        last = None
        for attempt in range(1, attempts + 1):
            try:
                arguments = {"model": model, "response_format": {"type": "json_schema", "json_schema": schema},
                             "messages": [{"role": "system", "content": system},
                                          {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}]}
                if model.startswith(("gpt-4", "gpt-3")):
                    arguments["temperature"] = 0
                else:
                    arguments["reasoning_effort"] = self.reasoning
                completion = self._client().chat.completions.create(**arguments)
                usage = completion.usage
                with self.lock:
                    self.usage[model + ":in"] += usage.prompt_tokens
                    self.usage[model + ":out"] += usage.completion_tokens
                return json.loads(completion.choices[0].message.content)
            except Exception as error:  # noqa: BLE001 — a failed act stays without the step
                last = error
                time.sleep(2 * attempt)
        print(f"[warn] {model} failed: {last}")
        return None

    def spent(self):
        total = 0.0
        for key, tokens in self.usage.items():
            model, kind = key.rsplit(":", 1)
            prices = ek.PRICES.get(model)
            if prices:
                total += tokens * prices["input" if kind == "in" else "output"] / 1_000_000
        return total


def locate(models, doc, text):
    """The provision a model points to, verified to occur in `text`, or {"found": False}."""
    result = models.ask(LOCATE_MODEL, LOCATE_SYSTEM, LOCATE_SCHEMA,
                        {"označení": doc["identifier"] or "", "název": doc["title"], "text": text[:EXCERPT]})
    if not result:
        return None
    quote = (result.get("quote") or "").strip()
    if not result.get("found") or not quote:
        return {"found": False}
    if normalize_space(quote) not in normalize_space(text):
        return {"found": False, "rejected": "citace se v textu nevyskytuje doslova", "quote": quote[:300]}
    quote = ap.shorten(ap.clean_provision(quote))
    problem = ap.describes(quote, result.get("label", ""))
    if problem:
        return {"found": False, "rejected": problem, "quote": quote[:300], "label": result.get("label", "").strip()}
    return {"found": True, "label": result.get("label", "").strip(), "text": quote}


def summarize(models, doc, text):
    """{"summary", "check"} — the checked summary, or one with "rejected"."""
    payload = {"označení": doc["identifier"] or "", "název": doc["title"], "text": text[:EXCERPT]}
    written = models.ask(SUMMARY_MODEL, SUMMARY_SYSTEM, SUMMARY_SCHEMA, payload)
    if not written or not written.get("summary", "").strip():
        return None
    check = models.ask(CHECK_MODEL, CHECK_SYSTEM, CHECK_SCHEMA, {"text": text[:EXCERPT], "shrnutí": written["summary"]})
    if not check:
        return None
    out = {"model": SUMMARY_MODEL, "checked_by": CHECK_MODEL, "draft": written["summary"].strip(),
           "verdict": check["verdict"], "problems": check.get("problems", [])}
    if check["verdict"] == "ok" and check.get("corrected", "").strip():
        out["summary"] = check["corrected"].strip()
    return out


# --- the plan ---------------------------------------------------------------

def load_documents(cursor):
    """Rows of the legal acts: dicts with id, identifier, url, type, title, language,
    description, popis_autoritativni, file_path, nazev_autoritativni."""
    marks = ", ".join(["%s"] * len(LEGAL_TYPES))
    cursor.execute("SELECT d.id, d.identifier, d.url, dt.name, d.title, d.language, d.description, "
                   "d.popis_autoritativni, d.file_path, d.nazev_autoritativni FROM Document d "
                   f"JOIN DocumentType dt ON dt.id = d.type_id WHERE dt.name IN ({marks}) ORDER BY d.id", LEGAL_TYPES)
    names = ("id", "identifier", "url", "type", "title", "language", "description", "popis_autoritativni",
             "file_path", "nazev_autoritativni")
    return [dict(zip(names, row)) for row in cursor.fetchall()]


def editor_keys(corrections):
    """Keys whose description an editor wrote (data/manual_corrections.json). A correction
    that only removed a description without a source (the record check of 2026-11-23) does
    not protect it: the act's own provision may then fill it."""
    return {key for key, entry in corrections.items()
            if any((entry.get("changes") or {}).get(field, "").strip() for field in ("anotace_poznamka", "popis_autoritativni"))}


def clean_text(doc, texts_dir):
    if not doc.get("file_path") or texts_dir is None:
        return None
    path = texts_dir / (pathlib.Path(doc["file_path"]).stem + ".txt")
    return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else None


def scan(documents, cache, texts_dir, today):
    """Updates `cache` with the opening provision of every act whose text changed; returns
    {key: (doc, text)} of the acts with a text."""
    keys = dterms.document_keys([(d["id"], d["identifier"], d["url"], d["type"], d["title"]) for d in documents])
    found = {}
    for doc in documents:
        key, text = keys[doc["id"]], clean_text(doc, texts_dir)
        if not key or text is None:
            continue
        found[key] = (doc, text)
        sha = text_sha(text)
        entry = cache.get(key)
        if entry and entry.get("text_sha") == sha:
            continue
        provision = ap.opening_provision(text, doc["language"])
        entry = {"text_sha": sha, "file": pathlib.Path(doc["file_path"]).stem, "scanned": today}
        if provision and provision["usable"]:
            entry["provision"] = {"label": ap.label_of(provision), "text": provision["text"], "method": "pattern"}
        else:
            entry["pattern_reason"] = provision["reason"] if provision else "první ustanovení nenalezeno"
        cache[key] = entry
    return found


def plan(documents, cache, protected, keys=None):
    """[(doc, change)] — change: {"description", "popis_autoritativni", "popis_zdroj",
    "popis_priblizny", "manual"} — for the acts whose stored description should change."""
    keys = keys or dterms.document_keys([(d["id"], d["identifier"], d["url"], d["type"], d["title"]) for d in documents])
    out = []
    for doc in documents:
        key = keys[doc["id"]]
        entry = cache.get(key)
        if not entry or key in protected:
            continue
        description, source, approximate = outcome(entry)
        current = (doc.get("description") or "").strip()
        if description:
            change = {"description": description, "popis_autoritativni": description, "popis_zdroj": source,
                      "popis_priblizny": None, "manual": False}
        elif not current or restates_title(current, doc["title"], doc.get("nazev_autoritativni")):
            change = {"description": None, "popis_autoritativni": None, "popis_zdroj": None,
                      "popis_priblizny": approximate, "manual": True}
        else:
            continue  # a real annotation or a note of the survey stays
        out.append((doc, change))
    return out


# --- the database -----------------------------------------------------------

def ensure_schema(cursor):
    cursor.execute("ALTER TABLE Document ADD COLUMN IF NOT EXISTS popis_zdroj VARCHAR(255) NULL AFTER popis_autoritativni")


def review_reason(old, manual):
    """The review reason after the change: "chybí popis…" goes when a description comes,
    MANUAL_REASON comes when the description must be written by hand."""
    parts = [p.strip() for p in (old or "").split(";") if p.strip()]
    parts = [p for p in parts if p != MANUAL_REASON and not (not manual and p == "chybí popis/anotace dokumentu")]
    if manual:
        parts.append(MANUAL_REASON)
    return "; ".join(parts)[:500] or None


def write(cursor, changes):
    ensure_schema(cursor)
    for doc, change in changes:
        cursor.execute("SELECT review_reason FROM Document WHERE id = %s", (doc["id"],))
        reason = review_reason(cursor.fetchone()[0], change["manual"])
        cursor.execute("UPDATE Document SET description = %s, popis_autoritativni = %s, popis_zdroj = %s, "
                       "popis_priblizny = %s, review_reason = %s, needs_review = %s WHERE id = %s",
                       (change["description"], change["popis_autoritativni"], change["popis_zdroj"],
                        change["popis_priblizny"], reason, 1 if reason else 0, doc["id"]))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--locate", action="store_true", help="let a model find the provision where the pattern failed")
    parser.add_argument("--summarize", action="store_true", help="approximate summaries where no provision serves")
    parser.add_argument("--run", action="store_true", help="call the models (only an estimate without it)")
    parser.add_argument("--apply", action="store_true", help="write the descriptions to the database")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--report", default=None, help="write the plan as JSON here")
    args = parser.parse_args(argv)
    from build_unified_db import load_manual_corrections
    conn = dterms.connect(args.env_file)
    try:
        cur = conn.cursor()
        documents = load_documents(cur)
        cache = dterms.load_cache(CACHE_PATH)
        today = datetime.date.today().isoformat()
        acts = scan(documents, cache, ek.clean_dir(), today)
        protected = editor_keys(load_manual_corrections())
        # a provision located before is checked again (act_provisions.describes()); a rejected one is asked again
        # once with the current instructions
        for key, entry in cache.items():
            located = entry.get("located") or {}
            if located.get("found") and ap.describes(located.get("text"), located.get("label", "")):
                entry["located"] = {"found": False, "rejected": ap.describes(located["text"], located.get("label", "")),
                                    "quote": located["text"][:300], "label": located.get("label", ""),
                                    "prompt_version": located.get("prompt_version", 1)}
        need_locate = [k for k, e in cache.items() if k in acts and not e.get("provision")
                       and ("located" not in e or ((e["located"].get("prompt_version", 1) < PROMPT_VERSION)
                                                   and not e["located"].get("found")))]
        if args.locate and args.run and need_locate:
            models = Models(model=LOCATE_MODEL)
            models._client()

            def do_locate(key):
                doc, text = acts[key]
                result = locate(models, doc, text)
                if result is not None:
                    cache[key]["located"] = {**result, "model": LOCATE_MODEL, "at": today, "prompt_version": PROMPT_VERSION}
            with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
                list(pool.map(do_locate, need_locate))
            print(f"locate: {len(need_locate)} acts, {models.spent():.3f} USD")
            dterms.save_cache(CACHE_PATH, cache)
        need_summary = [k for k, e in cache.items() if k in acts and k not in protected and not outcome(e)[0]
                        and "summary" not in e]
        if args.summarize and args.run and need_summary:
            models = Models(model=SUMMARY_MODEL)
            models._client()

            def do_summary(key):
                doc, text = acts[key]
                result = summarize(models, doc, text)
                if result is not None:
                    cache[key]["summary"] = {**result, "at": today}
            with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
                list(pool.map(do_summary, need_summary))
            print(f"summaries: {len(need_summary)} acts, {models.spent():.3f} USD")
        dterms.save_cache(CACHE_PATH, cache)
        if not args.run and (args.locate or args.summarize):
            tokens = sum(min(len(acts[k][1]), EXCERPT) // 3 for k in (need_locate if args.locate else []))
            tokens += sum(2 * min(len(acts[k][1]), EXCERPT) // 3 for k in (need_summary if args.summarize else []))
            print(f"model steps: locate {len(need_locate)}, summaries {len(need_summary)}, about {tokens} input tokens, "
                  f"about {tokens * 5 / 1_000_000 + 0.5:.2f} USD (gpt-5.5); nothing sent (--run)")
        changes = plan(documents, cache, protected)
        counts = collections.Counter("provision" if c["description"] else ("summary" if c["popis_priblizny"] else "manual")
                                     for _, c in changes)
        print(f"acts: {len(documents)}, with text: {len(acts)}, editor-protected: {len(protected & set(acts))}; "
              f"changes: {dict(counts)}")
        if args.report:
            pathlib.Path(args.report).write_text(json.dumps(
                [{"id": d["id"], "identifier": d["identifier"], **c} for d, c in changes], ensure_ascii=False, indent=1),
                encoding="utf-8")
        if args.apply:
            write(cur, changes)
            conn.commit()
            print(f"written to {dterms.connect.__module__ and 'the database'}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
