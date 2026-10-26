"""One act, two language variants, two documents.

The Haltuf spreadsheet lists every EU act twice: a row with `jazyk` CZ (the
Czech text) and a row with `jazyk` EN (the English one), both with the same
`znacka`. deduplicate_db.py merges them into ONE record that keeps only one of
the languages, so the document's title, address, language label and full text
used to disagree with each other. Following the rule that a document is a
specific text in a specific language (see the `ADOPTS`/`NATIONAL_EQUIVALENT`
precedent), the two variants are separate Documents joined by a
`TRANSLATION_OF` relation (English variant -> Czech original).

The Czech variant keeps the designation (so every existing relation and link
to it stays valid); the English one gets `EN_SUFFIX` appended, because
`Document.identifier` is UNIQUE. This module holds what the pipeline stages
share: which (source, designation) pairs have both variants, the designation of
a raw row's variant, and the split of a deduplicated record into its variants.
"""
import copy
import re

from language import normalize_raw_language

EN_SUFFIX = " [EN]"
RELATION_TYPE = "TRANSLATION_OF"

# What differs between the two spreadsheet rows of one act; everything else
# (type, validity, jurisdiction, ...) is shared and stays as deduplicated.
VARIANT_FIELDS = ("nazev_cz", "odkaz_hlavni", "odkaz_eu", "gestor", "jazyk", "anotace_poznamka")
# Czech-only overlays: the authoritative title/description come from EUR-Lex in Czech.
CZECH_ONLY_FIELDS = ("nazev_autoritativni", "popis_autoritativni", "zdroj_autoritativni_url")


_LEGAL_CONTENT_LANGUAGE = re.compile(r"eur-lex\.europa\.eu/legal-content/([A-Z]{2})/")


def row_language(record):
    """The language of a spreadsheet row: the language segment of its EUR-Lex
    address when it has one (the spreadsheet's `jazyk` column is wrong for some
    rows, e.g. both rows of (EU) 2019/773 say "angličtina"), else `jazyk`."""
    match = _LEGAL_CONTENT_LANGUAGE.search(record.get("odkaz_hlavni") or "")
    if match and match.group(1) in ("CS", "EN"):
        return match.group(1)
    return normalize_raw_language(record.get("jazyk", ""))


def variant_pairs(raw_records):
    """{(zdroj_dat, znacka): {"CS": first Czech row, "EN": first English row}}
    for every designation of one source that has both an English and a Czech
    row. Raw order decides which row is `first`."""
    rows = {}
    for record in raw_records:
        znacka = (record.get("znacka") or "").strip()
        language = row_language(record)
        if znacka and language in ("CS", "EN"):
            rows.setdefault((record.get("zdroj_dat"), znacka), {}).setdefault(language, record)
    return {key: value for key, value in rows.items() if len(value) == 2}


def variant_designation(record, pairs):
    """The designation a raw row is filed under: the English row of a pair gets
    `EN_SUFFIX`, every other row keeps its own `znacka`."""
    znacka = (record.get("znacka") or "").strip()
    if (record.get("zdroj_dat"), znacka) in pairs and row_language(record) == "EN":
        return znacka + EN_SUFFIX
    return znacka


def english_designation(znacka):
    return (znacka or "").strip() + EN_SUFFIX


def _pair_for(record, pairs):
    """The pair a deduplicated record belongs to: its znacka under any of the
    sources that contributed to it (`zdroj_dat` may list several, comma-joined)."""
    znacka = (record.get("znacka") or "").strip()
    for source in (s.strip() for s in (record.get("zdroj_dat") or "").split(",")):
        if (source, znacka) in pairs:
            return source, pairs[(source, znacka)]
    return None, None


def split_record(record, pairs):
    """[czech, english] variants of a deduplicated record that belongs to a
    pair, else None. The Czech variant keeps every contributing source, the
    English one only the spreadsheet that lists it; the English variant has no
    Czech authoritative overlay and no Sinay-only fields."""
    source, rows = _pair_for(record, pairs)
    if rows is None:
        return None
    czech, english = copy.deepcopy(record), copy.deepcopy(record)
    for variant, row in ((czech, rows["CS"]), (english, rows["EN"])):
        for field in VARIANT_FIELDS:
            if field in row:
                variant[field] = copy.deepcopy(row[field])
    czech["jazyk"], english["jazyk"] = "CZ", "EN"  # the spreadsheet's own value can be wrong
    english["zdroj_dat"] = source
    english["znacka"] = english_designation(record["znacka"])
    for field in CZECH_ONLY_FIELDS:
        english.pop(field, None)
    for field in ("nazev_eu", "nazev_sk", "odkaz_sk"):
        english[field] = ""
    return [czech, english]


def expand_variants(deduplicated, pairs):
    """The corpus with every pair's deduplicated record replaced by its two
    variants (Czech first). Idempotent: a pair whose English designation is
    already present is left as it is."""
    present = {(record.get("znacka") or "").strip() for record in deduplicated}
    records = []
    for record in deduplicated:
        znacka = (record.get("znacka") or "").strip()
        variants = None if znacka.endswith(EN_SUFFIX) or english_designation(znacka) in present \
            else split_record(record, pairs)
        records.extend(variants if variants else [record])
    return records


def translation_relations(records):
    """The `TRANSLATION_OF` relations (English variant -> Czech original, the
    shape load_document_relations.py reads) of a corpus that holds the variants."""
    designations = {(record.get("znacka") or "").strip() for record in records}
    relations = []
    for designation in sorted(designations):
        original = designation[:-len(EN_SUFFIX)]
        if designation.endswith(EN_SUFFIX) and original in designations:
            relations.append({"from_identifier": designation, "to_identifier": original,
                              "relation_type": RELATION_TYPE,
                              "note": "Anglická a česká jazyková verze téhož aktu (jazykové varianty rozdělené z jednoho záznamu)."})
    return relations


def gestor_cache_additions(records, cache):
    """{url: gestor} for the variants whose address (init_db.resolve_url) has no
    entry in data/eu_gestor_cache.json yet while the other variant's has: the
    responsible EU body of an act is the same in both languages, so the entry is
    copied. Without it the variant would be flagged `gestor not found`."""
    from init_db import resolve_url
    by_designation = {(record.get("znacka") or "").strip(): record for record in records}
    additions = {}
    for designation, english in by_designation.items():
        czech = by_designation.get(designation[:-len(EN_SUFFIX)]) if designation.endswith(EN_SUFFIX) else None
        if czech is None:
            continue
        urls = [resolve_url(czech), resolve_url(english)]
        for url, other in (urls, urls[::-1]):
            if url and url not in cache and other in cache:
                additions[url] = cache[other]
    return additions
