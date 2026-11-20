"""Automatic triage of the candidate queue: the approved rules of
data/triage_rules.json, then the language model for the rest (triage.py,
doc/FRONTA_AUTOMAT.md). The automat proposes acceptances (a human editor confirms
them), and rejects or defers by the rules; every action is reversible and written
to the AuditLog under the technical account `automat`.

Dry run unless --apply: prints what the rules and the model would do (the model is
called, unless --rules-only; its answers are cached in data/triage_model_cache.json).
--apply refuses a database whose name does not end with `_test` until the rules are
approved (`approval` in the rules file).

Usage:
  .venv/bin/python src/tools/triage_candidates.py [--rules-only] [--limit N] [--sample N [--seed S]]
      [--ids 1,2,3] [--rule R9-model] [--model NAME] [--report FILE] [--max-usd X] [--apply] [--env-file FILE]
"""
import argparse
import collections
import json
import random
import sys

import pymysql
from dotenv import dotenv_values

import candidates as cd
import testdb
import triage


def connect(env_file):
    env = dotenv_values(env_file or str(testdb.find_env_file(".env")))
    conn = pymysql.connect(host=env["DB_HOST"], port=int(env.get("DB_PORT") or 3306), user=env["DB_USER"],
                           password=env["DB_PASSWORD"], database=env["DB_NAME"],
                           cursorclass=pymysql.cursors.DictCursor)
    return conn, env["DB_NAME"]


def document_types(cur):
    cur.execute("SELECT name FROM DocumentType ORDER BY name")
    return [r["name"] for r in cur.fetchall()]


def select(queue, limit=None, sample=None, seed=None):
    if sample:
        queue = random.Random(seed).sample(queue, min(sample, len(queue)))
    if limit:
        queue = queue[:limit]
    return queue


def run(conn, database, args, config, assessor_factory=None, out=print):
    """Triage of the queue on `conn`; returns [(candidate, Decision, action taken or None)]."""
    with conn.cursor() as cur:
        if args.apply:
            cd.ensure_schema(cur)
        types = document_types(cur)
        index = triage.document_index(triage.load_documents(cur))
        queue = triage.load_queue(cur, args.ids)
        if args.rule:
            queue = [c for c in queue if triage.match_rule(c, config, index)["id"] in args.rule]
        queue = select(queue, args.limit, args.sample, args.seed)
        linked = triage.linked_documents(cur, queue)
        sources = cd.source_labels()
        assessor = None
        if not args.rules_only:
            assessor = (assessor_factory or triage.ModelAssessor)(config, types, model=args.model,
                                                                  composition=triage.database_composition(cur))
            to_model = [c for c in queue
                        if triage.decide(c, config, index, types, rules_only=True).action == "model"]
            payloads = [triage.build_payload(c, linked, sources) for c in to_model]
            calls, tokens_in, tokens_out, usd = assessor.estimate(payloads)
            out(f"model {assessor.model}: at most {calls} new calls, ~{tokens_in} input + ~{tokens_out} output tokens"
                + (f", ~{usd:.3f} USD" if usd is not None else ", price unknown (add it to the rules file)"))
            budget = args.max_usd if args.max_usd is not None else config["model"].get("budget_usd")
            if calls and (usd is None or (budget is not None and usd > budget)):
                out(f"refused: the estimate exceeds the budget {budget} USD (or the price is unknown); "
                    "use --max-usd or --rules-only")
                return []
        automat = cd.automat_id(cur, create=args.apply)
        results = []
        for candidate in queue:
            decision = triage.decide(candidate, config, index, types, cur=cur, assessor=assessor, linked=linked,
                                     sources=sources, rules_only=args.rules_only)
            taken = None
            if args.apply:
                taken = triage.store(cur, candidate, decision, automat)
                conn.commit()
            results.append((candidate, decision, taken))
    return results


def report(results, out=print):
    rules = collections.Counter((d.rule, d.action) for _, d, _ in results)
    out("rule / action / count:")
    for (rule, action), n in sorted(rules.items()):
        out(f"  {rule:16} {triage.ACTION_LABELS.get(action, action):24} {n}")
    taken = collections.Counter(t for _, _, t in results if t)
    if taken:
        out("written: " + ", ".join(f"{triage.ACTION_LABELS.get(k, k)} {v}" for k, v in sorted(taken.items())))
    for candidate, decision, _ in results:
        model = decision.model
        extra = f" [{model['recommendation']} {triage.confidence(model):.2f} {model['category']}]" if model else ""
        errors = f" (chyby: {'; '.join(decision.errors)})" if decision.errors else ""
        out(f"#{candidate['id']:<5} {candidate['source']:18} {decision.rule:16} {decision.action:9}{extra} "
            f"{(candidate.get('designation') or candidate.get('candidate_key') or '')[:30]} — "
            f"{(candidate.get('title') or '')[:70]}{errors}")


def as_json(results):
    return [{"id": c["id"], "source": c["source"], "signal": c.get("signal"), "tier": c.get("tier"),
             "designation": c.get("designation"), "title": c.get("title"), "url": c.get("url"),
             "rule": d.rule, "action": d.action, "taken": t, "note": d.note, "model": d.model,
             "areas": d.areas, "errors": d.errors,
             "metadata": d.metadata} for c, d, t in results]


def main(argv=None, assessor_factory=None, out=print):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--apply", action="store_true", help="write the decisions (dry run without it)")
    parser.add_argument("--rules-only", action="store_true", help="only the rules, no model calls")
    parser.add_argument("--limit", type=int, default=None, help="the first N candidates of the queue")
    parser.add_argument("--sample", type=int, default=None, help="a random sample of N candidates")
    parser.add_argument("--seed", type=int, default=20261120, help="the seed of --sample")
    parser.add_argument("--ids", type=lambda s: [int(x) for x in s.split(",") if x.strip()], default=None)
    parser.add_argument("--rule", type=lambda s: s.split(","), default=None,
                        help="only the candidates matched by these rules (e.g. R9-model)")
    parser.add_argument("--model", default=None, help="the model (default: model.name of the rules file)")
    parser.add_argument("--max-usd", type=float, default=None, help="refuse when the estimate exceeds this")
    parser.add_argument("--report", default=None, help="write the decisions as JSON to this file")
    parser.add_argument("--rules", default=None, help="the rules file (default: data/triage_rules.json)")
    parser.add_argument("--env-file", default=None)
    args = parser.parse_args(argv)
    config = triage.load_config(args.rules)
    conn, database = connect(args.env_file)
    try:
        if args.apply and not database.endswith("_test") and not triage.is_approved(config):
            out(f"refused: the rules are not approved yet (approval in {args.rules or triage.RULES_PATH}); "
                f"{database} stays untouched")
            return 2
        out(f"{database}: triage {'(writing)' if args.apply else '(dry run)'}"
            f"{', rules only' if args.rules_only else ''}")
        results = run(conn, database, args, config, assessor_factory, out)
    finally:
        conn.close()
    report(results, out)
    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            json.dump(as_json(results), f, ensure_ascii=False, indent=1, default=str)
    return 0


if __name__ == "__main__":
    sys.exit(main())
