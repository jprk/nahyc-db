"""Hands the findings of the record checks to the editors (doc/KONTROLA_ZAZNAMU.md).

The editors' queue (/admin/review, app/admin.py) lists the documents flagged
`needs_review` with their `review_reason`; a `ReviewItem` holds the open review of
one document. For every document with a finding in data/record_checks.json and
data/record_checks_model.json (except the ones in `VERIFIED`, checked by hand and
found correct) this script

- adds an open `ReviewItem` (status `needs_review`) whose reason starts with
  `PREFIX` and names the checks, unless the document has one from this script;
- sets `needs_review` and appends the reason to `review_reason` (500 characters).

Idempotent: a document that already carries the reason is left alone. A rebuild
(init_db.py) recomputes `needs_review`; rerun the checks and this script after it.

    .venv/bin/python src/tools/review_findings.py                     # dry run, live DB
    .venv/bin/python src/tools/review_findings.py --apply --env-file .env.test
"""
import argparse
import collections
import json
import sys

import check_records as cr
import check_records_model as crm
import document_terms as dterms

PREFIX = "Kontrola záznamů:"
REASON_LIMIT = 500
# findings checked by hand and found to be wrong (doc/KONTROLA_ZAZNAMU.md, odstavec 7)
VERIFIED = {("STN EN IEC 62282-8-301/ - 2023.11", "model_description"):
            "IEC 62282-8-301 se skutečně týká systémů power-to-methane, popis odpovídá"}
LABELS = {"eu_title": "název jiného aktu EU", "eu_not_found": "číslo aktu v Cellaru neexistuje",
          "eu_ambiguous": "číslu odpovídá více aktů", "eu_type": "typ neodpovídá druhu aktu",
          "eu_date": "datum v názvu nesouhlasí", "iso_not_found": "ISO normu neuvádí",
          "iso_title": "název se liší od ISO", "iso_draft_published": "návrh ISO už vydala",
          "iso_withdrawn": "ISO poslední vydání zrušila", "auth_title": "název se liší od autoritativního",
          "number_not_in_title": "číslo z označení chybí v názvu", "bad_identifier": "označení je úlomek",
          "title_fragment": "useknutý název nebo poznámka místo názvu", "type_vs_title": "typ neodpovídá názvu",
          "duplicate_title": "možná duplicita", "model_title": "model: název neodpovídá dokumentu",
          "model_description": "model: popis neodpovídá dokumentu", "model_relevance": "model: nesouvisí s vodíkem"}


def reasons(findings):
    """{document id: (identifier, reason)} — one reason per document listing its checks."""
    by_doc = collections.OrderedDict()
    for f in findings:
        if (f["identifier"], f["check"]) in VERIFIED:
            continue
        by_doc.setdefault(f["id"], (f["identifier"], []))
        labels = by_doc[f["id"]][1]
        if LABELS.get(f["check"], f["check"]) not in labels:
            labels.append(LABELS.get(f["check"], f["check"]))
    return {doc_id: (ident, f"{PREFIX} {', '.join(labels)}") for doc_id, (ident, labels) in by_doc.items()}


def detail(findings, doc_id):
    return " ".join(dict.fromkeys(f["detail"] for f in findings if f["id"] == doc_id))


def plan(cursor, findings):
    """[(document id, reason, new review_reason or None, add ReviewItem)] for the findings."""
    cursor.execute("SELECT id, review_reason FROM Document")
    current = dict(cursor.fetchall())
    cursor.execute("SELECT document_id FROM ReviewItem WHERE status IN ('needs_review', 'proposed') "
                   "AND review_reason LIKE %s", (PREFIX + "%",))
    open_items = {r[0] for r in cursor.fetchall()}
    out = []
    for doc_id, (_ident, reason) in reasons(findings).items():
        if doc_id not in current:
            continue  # the document has gone (merged, excluded) since the check
        old = current[doc_id] or ""
        new = None if PREFIX in old else ("; ".join(p for p in (old, reason) if p))[:REASON_LIMIT]
        out.append((doc_id, reason, new, doc_id not in open_items))
    return out


def apply(cursor, rows, findings):
    for doc_id, reason, new, add_item in rows:
        if new is not None:
            cursor.execute("UPDATE Document SET needs_review = 1, review_reason = %s WHERE id = %s", (new, doc_id))
        if add_item:
            cursor.execute("INSERT INTO ReviewItem (document_id, review_reason, status) VALUES (%s, %s, 'needs_review')",
                           (doc_id, (reason + " — " + detail(findings, doc_id))[:REASON_LIMIT]))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--apply", action="store_true", help="write to the database (dry run without it)")
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--report", action="append", default=None,
                        help="report(s) to read (default: data/record_checks.json and data/record_checks_model.json)")
    args = parser.parse_args(argv)
    paths = args.report or [str(cr.REPORT_PATH), str(crm.REPORT_PATH)]
    findings = [f for path in paths for f in json.loads(open(path, encoding="utf-8").read())["findings"]]
    conn = dterms.connect(args.env_file)
    try:
        cur = conn.cursor()
        rows = plan(cur, findings)
        for doc_id, reason, new, add_item in rows:
            print(f"#{doc_id}: {reason}" + ("" if new is not None or add_item else " (already in the queue)"))
        print(f"{len(rows)} documents; {sum(1 for r in rows if r[3])} review items to add, "
              f"{sum(1 for r in rows if r[2] is not None)} flags to set")
        if args.apply:
            apply(cur, rows, findings)
            conn.commit()
            print("written")
        else:
            print("dry run, nothing written (--apply)")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
