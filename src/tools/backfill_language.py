"""One-time backfill of `Document.language` across the whole corpus
(language-indicator request, 2026-09-15): normalizes the records that
already carried a raw `jazyk` value (mixed 'CZ'/'čeština'/'angličtina'/
'EN' spellings) and detects a best-guess language for the records that
never had one (mostly Norma-type standards), restricted to EN/CS/SK/DE —
see `language.py` for why `jurisdikce` can't be used as a shortcut.
Low-confidence guesses are flagged via the existing needs_review/
review_reason mechanism (doc/PLAN.md data-quality flagging, shipped
2026-09-11) instead of being silently asserted, so they surface for
manual check like any other data-quality issue.

Usage: `.venv/bin/python src/tools/backfill_language.py [--apply]`
(dry-run report only by default; --apply writes to the database)
"""
import argparse
import os
import pathlib
import sys

import pymysql
from dotenv import load_dotenv

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from language import detect_language, normalize_raw_language, resolve_domain_language_override

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
load_dotenv(REPO_ROOT / ".env")

REVIEW_REASON_PREFIX = "jazyk dokumentu byl automaticky odhadnut, ověřte"


def get_connection():
    return pymysql.connect(
        host=os.environ["DB_HOST"], port=int(os.environ["DB_PORT"]),
        user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"], cursorclass=pymysql.cursors.DictCursor,
    )


def append_review_reason(existing, reason):
    existing = (existing or "").strip()
    if not existing:
        return reason
    if reason in existing:
        return existing
    return f"{existing}; {reason}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true",
                         help="write changes to the database (default: dry-run report only)")
    args = parser.parse_args()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, title, description, language, url, needs_review, review_reason FROM Document")
    documents = cur.fetchall()

    updates = []  # (id, new_language, needs_review, review_reason)
    stats = {"domain_override": 0, "normalized": 0, "already_normalized": 0,
             "detected_confident": 0, "detected_flagged": 0}

    for doc in documents:
        # doc/PLAN.md §23, 2026-09-17: checked first and unconditionally
        # — a domain override must be able to CORRECT an already
        # "valid-looking" but wrong stored value (e.g. a confidently
        # wrong SK detection for an e-sbirka.gov.cz record), which the
        # normalize_raw_language() short-circuit below would otherwise
        # never revisit.
        override = resolve_domain_language_override(doc["url"])
        if override:
            if override == doc["language"]:
                stats["already_normalized"] += 1
            else:
                stats["domain_override"] += 1
                updates.append((doc["id"], override, doc["needs_review"], doc["review_reason"]))
            continue

        normalized = normalize_raw_language(doc["language"])
        if normalized:
            if normalized == doc["language"]:
                stats["already_normalized"] += 1
                continue
            stats["normalized"] += 1
            updates.append((doc["id"], normalized, doc["needs_review"], doc["review_reason"]))
            continue

        code, confident = detect_language(doc["title"], doc["description"])
        if confident:
            stats["detected_confident"] += 1
            updates.append((doc["id"], code, doc["needs_review"], doc["review_reason"]))
        else:
            stats["detected_flagged"] += 1
            new_reason = append_review_reason(
                doc["review_reason"], f"{REVIEW_REASON_PREFIX} ({code})")
            updates.append((doc["id"], code, True, new_reason))

    print(f"{len(documents)} documents total")
    print(f"  corrected by domain override (e.g. e-sbirka.gov.cz -> CS): {stats['domain_override']}")
    print(f"  raw value normalized to EN/CS/SK/DE spelling: {stats['normalized']}")
    print(f"  already in normalized form (no-op): {stats['already_normalized']}")
    print(f"  detected with high confidence: {stats['detected_confident']}")
    print(f"  detected low-confidence, flagged for review: {stats['detected_flagged']}")
    print(f"{len(updates)} rows to update")

    if not args.apply:
        print("\nDry run — pass --apply to write changes.")
        conn.close()
        return

    for doc_id, language, needs_review, review_reason in updates:
        cur.execute(
            "UPDATE Document SET language=%s, needs_review=%s, review_reason=%s WHERE id=%s",
            (language, needs_review, review_reason, doc_id))
    conn.commit()
    print(f"\nApplied {len(updates)} updates.")
    conn.close()


if __name__ == "__main__":
    main()
