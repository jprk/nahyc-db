"""How a document is named in data/fulltext_manifest.json.

The manifest is keyed `<source>|<designation>|<url field>` (fetch_fulltext.py).
The designation is the document's `znacka`, so a document with none — a
strategy, a study, a Slovak act listed by its address only — could not be
fetched and had no full text. It is now filed under a designation made of its
address, `url-<8 hex of the SHA-256 of the address>`, stable as long as the
address in the source is. fetch_fulltext.py writes the manifest with it and
init_db.resolve_file_path() reads it back with the same function.
"""
import hashlib

URL_FIELDS = ("odkaz_hlavni", "odkaz_eu", "odkaz_sk")
URL_DESIGNATION_PREFIX = "url-"


def first_url(raw_value):
    """Some Haltuf odkaz_* cells hold two URLs joined by an embedded
    newline (an Excel line-break artifact, e.g. the EUR-Lex PDF link
    followed by an unrelated informational page) — only the first is a
    real, fetchable document link; sending the whole blob 404s. Splits
    on any whitespace and returns the first token, or "" for blank/None."""
    parts = (raw_value or "").split()
    return parts[0] if parts else ""


def url_designation(url):
    """The designation of a document that has none, from its address."""
    return URL_DESIGNATION_PREFIX + hashlib.sha256(url.encode("utf-8")).hexdigest()[:8]


def designation(record, url_field):
    """The designation `record` is filed under for `url_field`: its `znacka`, else the
    one made of that field's address ("" when it has neither)."""
    znacka = (record.get("znacka") or "").strip()
    if znacka:
        return znacka
    url = first_url(record.get(url_field))
    return url_designation(url) if url else ""
