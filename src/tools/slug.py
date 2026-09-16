"""Stable, rebuild-safe public identifier for a `Document`.

doc/PLAN.md §16 (2026-09-16). `Document.id` is an autoincrement assigned
by insertion order, and `init_db.py` TRUNCATEs and reloads the whole
corpus on every run — so ids are reassigned on each rebuild. §14 caught
this in practice: an id the user had cited (147) had already drifted to
an unrelated record. That was tolerable while ids only ever appeared as
a label in the detail accordion (§12), but a per-document page exists to
be linked, bookmarked and quoted, so it needs a key derived from the
record's own content instead.

`assign_slugs()` is therefore a PURE function over the whole corpus, not
a per-record one: collision suffixes ("-2", "-3") are handed out in a
content-derived sort order, never in input order. That distinction is
the whole point — two records whose designations slugify identically
would otherwise swap slugs from one rebuild to the next and reintroduce
exactly the instability this module exists to remove.
"""
import hashlib
import pathlib
import re
import sys
import unicodedata

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from norm_title import designation_core, is_real_designation

# Room for a "-NN" collision suffix inside the column's VARCHAR(160).
MAX_BASE_LENGTH = 120

_NON_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text):
    """Lowercase ASCII slug: strips diacritics (so "ČSN" -> "csn"),
    collapses every other run of characters to a single "-". Returns ""
    for input that has no alphanumerics at all."""
    decomposed = unicodedata.normalize("NFKD", text or "")
    ascii_text = "".join(c for c in decomposed if not unicodedata.combining(c))
    ascii_text = ascii_text.encode("ascii", "ignore").decode("ascii")
    return _NON_SLUG_RE.sub("-", ascii_text.lower()).strip("-")[:MAX_BASE_LENGTH]


def base_slug(identifier, title):
    """The slug a record wants, before collision handling.

    Prefers the designation — it is the record's own stable, meaningful
    name ("ČSN EN 17124" -> "csn-en-17124", "(EU) 2022/869" ->
    "eu-2022-869"). Falls back to a hash of the title for the records
    that have no real designation: `identifier` is NULL for 56 of them
    (the R1.1 gap), and for a handful more it holds a copy or fragment of
    the title rather than a designation, which `is_real_designation()`
    already knows how to reject. The hash is over the title alone, so it
    is reproducible from content and nothing else."""
    identifier = (identifier or "").strip()
    if is_real_designation(identifier):
        slug = slugify(designation_core(identifier) or identifier)
        if slug:
            return slug
    digest = hashlib.sha1((title or "").encode("utf-8")).hexdigest()[:8]
    return f"doc-{digest}"


def assign_slugs(records):
    """Maps each record to a unique slug. `records` is an iterable of
    (key, identifier, title); returns {key: slug}.

    Records are processed in a content-derived order — (base slug,
    identifier, title) — so the same corpus always produces the same
    assignment no matter what order it arrives in. Duplicates of a base
    slug get "-2", "-3", … in that order; the first record in the sort
    keeps the bare slug."""
    prepared = [
        (base_slug(identifier, title), (identifier or ""), (title or ""), key)
        for key, identifier, title in records
    ]
    prepared.sort(key=lambda r: (r[0], r[1], r[2], str(r[3])))

    assigned = {}
    seen_counts = {}
    for base, _identifier, _title, key in prepared:
        seen_counts[base] = seen_counts.get(base, 0) + 1
        n = seen_counts[base]
        assigned[key] = base if n == 1 else f"{base}-{n}"
    return assigned
