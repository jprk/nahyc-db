import json
import os
import pathlib
import re

import pymysql
from dotenv import load_dotenv

from language import detect_language, normalize_raw_language
from norm_title import format_norm_title
from puvodce import load_eu_gestor_cache, resolve_gestor, resolve_puvodce

BASE_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent
JSON_PATH = REPO_ROOT / "data" / "database_merged_deduplicated.json"
FULLTEXT_MANIFEST_PATH = REPO_ROOT / "data" / "fulltext_manifest.json"
INCOMPLETE_RECORDS_QUEUE_PATH = REPO_ROOT / "data" / "incomplete_records_review_queue.json"

# Truncation order respects FK dependencies (children before parents).
TRUNCATE_ORDER = ["DocumentKeyword", "DocumentVersion", "Document", "Keyword",
                  "DocumentSource", "DocumentType"]

# A purely-numeric (or blank) typ_dokumentu is leaked category-id junk —
# 44 records, all from Haltuf_Dokumenty (e.g. "1", "2", "9") — that must
# not become its own DocumentType row. See doc/PLAN.md Step 2.
_NUMERIC_TYPE_RE = re.compile(r"^\d+$")
FALLBACK_DOCUMENT_TYPE = "Nezařazeno"

# jurisdikce values that mean "we don't have a real jurisdiction to
# attribute to this gestor" — never used to seed DocumentSource.jurisdiction.
_UNKNOWN_JURISDIKCE = {"", "neurčeno"}

# Document.identifier is VARCHAR(100) — a znacka longer than this can't be
# stored as-is. Found in practice: one Sinay-parsed record bundles several
# distinct STN designations (newline-joined) into a single znacka field, a
# PDF-parsing artifact, not a real single identifier — see doc/PLAN.md Step 2.
IDENTIFIER_MAX_LENGTH = 100

# doc/REQUIREMENTS.md R4.1, 2026-09-11: DocumentType names whose full text
# is copyrighted/paywalled — file_path should hold nothing for these, only
# a metadata `url` pointing at the (paid) publisher/registry. Kept as an
# explicit, structural flag on DocumentType (not inferred at render time
# from whether file_path happens to be empty), because relying on that
# alone is NOT actually safe: found in practice (2026-09-11) that
# fetch_fulltext.py's own source-based exclusion missed a handful of norm
# citations that happened to live inside a law source (Haltuf_Dokumenty),
# giving 2 "Norma"-typed Documents a file_path anyway (harmless in this
# instance — the cached pages turned out to be public catalog/anti-bot
# pages, not paid full text, but the wrong content shape regardless — see
# fetch_fulltext.py's own is_norm_designation() fix). This flag is the
# actual enforcement layer app/app.py relies on — it must say "no" even
# when file_path says otherwise.
RESTRICTED_DOCUMENT_TYPES = {"Norma"}


def get_connection():
    load_dotenv(REPO_ROOT / ".env")
    return pymysql.connect(
        host=os.environ["DB_HOST"], port=int(os.environ["DB_PORT"]),
        user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"], autocommit=False,
    )


def reset_tables(cursor):
    print("Clearing existing rows from V01 tables...")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    for table in TRUNCATE_ORDER:
        cursor.execute(f"TRUNCATE TABLE {table}")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")


def get_or_create(cursor, table, val_dict, extra_insert_cols=None, return_col="id"):
    """Helper to get a record ID or insert it if it doesn't exist.
    `extra_insert_cols` are only ever written on first INSERT (not part of
    the WHERE match) — used for DocumentSource.institution_type/jurisdiction,
    which key on `name` alone but carry extra derived columns."""
    where_clause = " AND ".join([f"{k} = %s" for k in val_dict.keys()])
    values = tuple(val_dict.values())

    cursor.execute(f"SELECT {return_col} FROM {table} WHERE {where_clause}", values)
    result = cursor.fetchone()
    if result:
        return result[0]

    insert_dict = dict(val_dict)
    if extra_insert_cols:
        insert_dict.update(extra_insert_cols)
    cols = ", ".join(insert_dict.keys())
    placeholders = ", ".join(["%s"] * len(insert_dict))
    cursor.execute(f"INSERT INTO {table} ({cols}) VALUES ({placeholders})", tuple(insert_dict.values()))
    return cursor.lastrowid


def resolve_identifier(znacka, seen_identifiers):
    """Returns the `Document.identifier` value for this record, or None.
    Blank znacka -> None (MariaDB allows multiple NULLs under the UNIQUE
    constraint on `identifier`, so this is free). A znacka that collides
    with one already assigned earlier this run also -> None, with a
    printed warning, instead of crashing the load — a known, disclosed
    residual (e.g. "ASTM F1624-12" exists once as CZ and once as US; same
    reference number, legitimately different national instruments — see
    doc/PLAN.md Step 1 follow-up #9). Mutates `seen_identifiers`."""
    z = (znacka or "").strip()
    if not z:
        return None
    if len(z) > IDENTIFIER_MAX_LENGTH:
        print(f"WARNING: znacka too long for identifier ({len(z)} > "
              f"{IDENTIFIER_MAX_LENGTH} chars) — leaving identifier NULL: {z[:80]!r}...")
        return None
    if z in seen_identifiers:
        print(f"WARNING: duplicate znacka {z!r} across final records — "
              f"leaving identifier NULL for this one (see doc/PLAN.md Step 1 "
              f"follow-up #9 for the known cross-jurisdiction residual).")
        return None
    seen_identifiers.add(z)
    return z


def resolve_document_type(typ_dokumentu):
    """Returns the DocumentType.name to use for this record — the stripped
    value, or FALLBACK_DOCUMENT_TYPE when it's blank or purely numeric
    (leaked category-id junk, see module docstring)."""
    t = (typ_dokumentu or "").strip()
    if not t or _NUMERIC_TYPE_RE.match(t):
        return FALLBACK_DOCUMENT_TYPE
    return t


def is_restricted_document_type(doc_type):
    """R4.1: True when this DocumentType's full text is copyrighted/
    paywalled (see RESTRICTED_DOCUMENT_TYPES)."""
    return doc_type in RESTRICTED_DOCUMENT_TYPES


def load_fulltext_manifest():
    """Reads data/fulltext_manifest.json (built by fetch_fulltext.py) —
    empty dict if it doesn't exist yet (e.g. a fresh checkout that hasn't
    run that script)."""
    if FULLTEXT_MANIFEST_PATH.exists():
        with open(FULLTEXT_MANIFEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def resolve_file_path(item, manifest):
    """R1.7: returns the locally-cached full-text path for this record, or
    None. The manifest is keyed by the RAW per-source "zdroj_dat|znacka|
    url_field" triple (see fetch_fulltext.py) — a merged record's own
    zdroj_dat can be a comma-joined list of contributing sources (see
    deduplicate_db.py's "', '.join(sources)"), so every component source
    is tried against every URL field. Never guessed: a record with no
    manifest hit simply gets no file_path, whether because it's a
    copyrighted norm (fetch_fulltext.py deliberately excludes those, see
    its own is_norm_designation()), the fetch failed, or it hasn't run
    yet — but note this alone is not the access-control mechanism (see
    RESTRICTED_DOCUMENT_TYPES above), only a best-effort input to it."""
    znacka = (item.get("znacka") or "").strip()
    if not znacka:
        return None
    sources = [s for s in (item.get("zdroj_dat") or "").split(", ") if s]
    for source in sources:
        for url_field in ("odkaz_hlavni", "odkaz_eu", "odkaz_sk"):
            entry = manifest.get(f"{source}|{znacka}|{url_field}")
            if entry and entry.get("status") == "fetched" and entry.get("local_path"):
                return entry["local_path"]
    return None


# 2026-09-11, user-reported: some Sinay_Normy records export/display with a
# meaningless title or missing description (e.g. znacka "CEN/TC 326 Natural
# Gas Vehicles" + nazev_cz "- Fuelling and Operation" — a single wrapped
# line from parse_sinay_norms.py's coordinate-based PDF-table reconstruction
# split across the wrong columns). Rather than silently displaying these,
# every such record is flagged (Document.needs_review/review_reason below)
# so a human can find and fix the source data — never guessed/repaired
# automatically, same review-queue philosophy as everywhere else in this
# pipeline.
_EDITION_ONLY_ZNACKA_RE = re.compile(r"^[-–—]\s*\d{4}(\.\d{2}|-\d{2})?$")
_COMMITTEE_ONLY_ZNACKA_RE = re.compile(r"\b(CEN|CENELEC|ISO|IEC)/TC\b", re.IGNORECASE)
_FRAGMENT_TITLE_START_RE = re.compile(r"^([-–—:]|\d+(-\d+)*\s*:)")
# Real Czech/Slovak legal-document titles conventionally start lowercase
# ("zákon č. ... Sb., o ...") — excluded so they're never mistaken for a
# fragment just for not starting with a capital letter.
_LEGITIMATE_LOWERCASE_TITLE_RE = re.compile(
    r"^(zákon|vyhlášk|nařízení|nariaden|smernic|směrnic|usnesení|sdělení|"
    r"vykonávacie|opatrenie)\w*\b", re.IGNORECASE)


def is_garbled_znacka(znacka):
    """True when znacka is not a real document designation: just an
    edition-date suffix with nothing before it ("- 2024.09"), or a bare
    technical-committee reference ("CEN/TC 326 Natural Gas Vehicles") —
    both real parsing-artifact shapes found in this corpus."""
    zn = (znacka or "").strip()
    return bool(_EDITION_ONLY_ZNACKA_RE.match(zn)) or bool(_COMMITTEE_ONLY_ZNACKA_RE.search(zn))


def is_fragment_title(title):
    """True when a title looks like a wrapped continuation line rather
    than a real title: starts with a stray dash/colon, a "N-N:" part
    fragment, or lowercase text that isn't one of the legitimate
    lowercase-starting Czech/Slovak legal-document title conventions."""
    t = (title or "").strip()
    if not t:
        return False
    if _FRAGMENT_TITLE_START_RE.match(t):
        return True
    if re.match(r"^[a-záčďéěíňóřšťúůýž]", t) and not _LEGITIMATE_LOWERCASE_TITLE_RE.match(t):
        return True
    return False


def resolve_title(item):
    """doc/PLAN.md §8, 2026-09-11: prefers the verified authoritative
    title (nazev_autoritativni — attached by build_unified_db.py from
    data/site_metadata_cache.json, itself built by src/tools/
    fetch_authoritative_metadata.py querying each document's own
    "single point of authority" website) over the spreadsheet-derived
    nazev_cz/nazev_sk/nazev_eu fallback chain. A record with no
    authoritative hit (the large majority — see that script's own
    docstring for the honestly-bounded scope) falls back to today's
    resolution unchanged."""
    title = (item.get("nazev_autoritativni") or "").strip()
    if title:
        return title
    title = (item.get("nazev_cz") or "").strip()
    if not title:
        title = (item.get("nazev_sk") or "").strip()
        if not title:
            title = (item.get("nazev_eu") or "").strip()
    return title


def resolve_description(item):
    """doc/PLAN.md §8: prefers the verified authoritative description
    (popis_autoritativni) over the spreadsheet-derived anotace_poznamka —
    same reasoning as resolve_title() above."""
    description = (item.get("popis_autoritativni") or "").strip()
    if description:
        return description
    return (item.get("anotace_poznamka") or "").strip()


def resolve_url(item):
    """doc/PLAN.md §9, 2026-09-13: prefers the confirmed
    zdroj_autoritativni_url (the real "single point of authority" —
    e.g. agentura-cas.cz's own Detailnormy.aspx page, or e-Sbírka's
    government reference for a Czech law) over the spreadsheet-derived
    odkaz_hlavni/odkaz_eu/odkaz_sk — this is the link app/templates/
    index.html actually renders as "go to source", so a record whose
    title we've already verified against a better source should also
    send the user there, not to whatever third-party mirror
    (technicke-normy-csn.cz, or similar) the raw spreadsheet happened to
    cite. Falls back to today's resolution unchanged when no
    authoritative URL was found."""
    url = (item.get("zdroj_autoritativni_url") or "").strip()
    if url:
        return url
    url = (item.get("odkaz_hlavni") or "").strip()
    if not url:
        url = (item.get("odkaz_eu") or "").strip()
        if not url:
            url = (item.get("odkaz_sk") or "").strip()
    return url


def detect_data_quality_issues(item):
    """Returns a list of Czech-language reasons this record should be
    flagged for manual review, or [] if none apply. Checked: a garbled
    znacka (see is_garbled_znacka), a fragment-looking title (see
    is_fragment_title — checked against the resolved title, i.e. an
    authoritative title fixes this even if the underlying nazev_cz is
    still garbled), and a missing description (same — an authoritative
    description fixes this too). Never guesses a fix — only flags what's
    left over after resolve_title()/resolve_description() have already
    applied whatever authoritative data is available."""
    reasons = []
    if is_garbled_znacka(item.get("znacka")):
        reasons.append("značka není platné označení dokumentu")
    if is_fragment_title(resolve_title(item)):
        reasons.append("název vypadá jako useknutý fragment textu")
    if not resolve_description(item):
        reasons.append("chybí popis/anotace dokumentu")
    return reasons


def normalize_jurisdikce(jurisdikce):
    """Returns the `Document.jurisdikce` value — blank -> None, else the
    stripped value verbatim (including "neurčeno", which is a real,
    meaningful classification outcome — "we tried and couldn't tell" is
    different from "we never had this field at all")."""
    j = (jurisdikce or "").strip()
    return j or None


def build_gestor_jurisdiction_map(records):
    """Pre-scans all records once to determine each non-blank gestor's
    jurisdiction up front. Needed because DocumentSource rows are
    get_or_create'd — whichever record for a given gestor is processed
    FIRST decides what gets inserted, so the correct value must be known
    before that first insert, not discovered from a later record. Verified
    empirically (doc/PLAN.md Step 2): zero real per-gestor jurisdikce
    conflicts exist in the current corpus, so "first non-blank, non-
    unknown value found" is safe, not an arbitrary pick. Keyed by
    `resolve_puvodce()` (src/tools/puvodce.py, 2026-09-15) — the same
    single-institution resolution used for `Document.source_id` below —
    so lookups by the caller (`resolve_source_jurisdiction()`) actually
    hit; keying by the old raw joined-gestor string would silently never
    match once `source` itself stopped being that joined string."""
    mapping = {}
    for item in records:
        gestor = resolve_puvodce(item) or ""
        if not gestor or gestor in mapping:
            continue
        jurisdikce = (item.get("jurisdikce") or "").strip()
        if jurisdikce not in _UNKNOWN_JURISDIKCE:
            mapping[gestor] = jurisdikce
    return mapping


def resolve_source_jurisdiction(gestor_name, gestor_jurisdiction_map):
    """Returns (institution_type, jurisdiction) for this DocumentSource.
    `institution_type` is never populated this pass — no reliable source
    data to derive it from (not guessed). `jurisdiction` is looked up from
    the pre-built map for a non-blank gestor; a blank gestor (95% of
    records, nearly all norms) gets (None, None) — DocumentSource can't
    carry per-document jurisdikce for those, see doc/PLAN.md Step 2 (that's
    what the new Document.jurisdikce column is for)."""
    gestor_name = (gestor_name or "").strip()
    if not gestor_name:
        return None, None
    return None, gestor_jurisdiction_map.get(gestor_name)


# doc/REQUIREMENTS.md R1.5, 2026-09-11: platnost (in this corpus, a
# free-text field mixing "od MM/RRRR"-style effective dates, publication
# stamps like "Veröffentlicht-Publikovaný", and genuine pre-publication
# work-item markers) is the only place a version's real lifecycle stage
# ever shows up — never a structured value. These are the actual marker
# strings found in the corpus (German/Czech/Slovak, standards-body
# terminology): "Entwurf"/"Návrh" (draft), "Arbeitsdokument"/"pracovný
# dokument" (work item), "PWI" (ISO/IEC Preliminary Work Item stage).
_DRAFT_MARKER_RE = re.compile(
    r"entwurf|návrh|navrh|arbeitsdokument|pracovn[ýy] dokument|\bpwi\b|work item",
    re.IGNORECASE,
)


def classify_lifecycle_state(platnost, is_current):
    """Maps a version to one of R1.5's three explicit lifecycle states —
    never guessed beyond what's actually evidenced: a non-current version
    (superseded by a later one in its own DocumentVersion history) is
    always "superseded" regardless of its own platnost text (that text
    describes its state AT THE TIME, not its current standing relative to
    a newer edition); a current version whose platnost carries a real
    draft/work-item marker (see _DRAFT_MARKER_RE) is "draft"; every other
    current version — including one with empty/unrecognized platnost — is
    "active", the same default a plain, unversioned, currently-valid
    document already gets today."""
    if not is_current:
        return "superseded"
    if _DRAFT_MARKER_RE.search(platnost or ""):
        return "draft"
    return "active"


def resolve_document_versions(item):
    """Returns the DocumentVersion rows to insert for this record, in
    order, numbered 1..N: one per entry in its "versions" list (built by
    link_document_versions.py for a norm base+amendment group — Step 1
    follow-up #16), each carrying its own real designation/edition-date
    as edition_label/effective_date; or, when "versions" is absent (the
    common, unversioned case), the historical single-row behavior
    (version=1, is_current=True, no edition_label/effective_date). Every
    row also gets `lifecycle_state` (R1.5) via classify_lifecycle_state()
    — for the versioned case, from that member's own platnost (already
    carried as its effective_date, see link_document_versions.py); for the
    unversioned case, from the record's own top-level platnost (not itself
    stored as this row's effective_date, to avoid changing that column's
    existing "only a real per-edition date, never generic platnost text"
    meaning for the common case)."""
    versions = item.get("versions")
    if not versions:
        platnost = item.get("platnost", "")
        return [{"version": 1, "edition_label": None, "effective_date": None,
                  "is_current": True,
                  "lifecycle_state": classify_lifecycle_state(platnost, True)}]
    return [
        {"version": i,
         "edition_label": v.get("edition_label") or None,
         "effective_date": v.get("effective_date") or None,
         "is_current": bool(v.get("is_current")),
         "lifecycle_state": classify_lifecycle_state(
             v.get("effective_date") or "", bool(v.get("is_current")))}
        for i, v in enumerate(versions, start=1)
    ]


def import_json_data(db_conn):
    print(f"Reading from {JSON_PATH}")

    if not JSON_PATH.exists():
        print(f"Error: {JSON_PATH} does not exist. Run build_unified_db.py first.")
        return

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"Found {len(data)} records to import.")

    cursor = db_conn.cursor()
    seen_identifiers = set()
    gestor_jurisdiction_map = build_gestor_jurisdiction_map(data)
    eu_gestor_cache = load_eu_gestor_cache(REPO_ROOT)
    fulltext_manifest = load_fulltext_manifest()
    incomplete_records = []

    for item in data:
        title = resolve_title(item)
        if not title:
            continue

        doc_type = resolve_document_type(item.get("typ_dokumentu", ""))
        effective_date = item.get("platnost", "").strip()
        url = resolve_url(item)

        # src/tools/puvodce.py, 2026-09-15/16: "Gestor" is a single
        # institution — the primary CZ ministry for a national act, or
        # (2026-09-16 follow-up) the responsible EU body (from
        # data/eu_gestor_cache.json, see backfill_eu_gestor.py) for an EU
        # act itself — never the whole raw `gestor` list joined verbatim
        # (what `init_db.py` used to do). Same one-time fixes as
        # backfill_puvodce.py/backfill_eu_gestor.py applied directly to
        # the already-imported DB, kept here too so a future rebuild from
        # JSON reproduces the same result.
        gestor, gestor_unresolved_eu_act = resolve_gestor(item, doc_type, url, eu_gestor_cache)
        source = gestor or ""

        description = resolve_description(item)

        # src/tools/language.py, 2026-09-15: a raw `jazyk` value (when
        # present) is normalized to EN/CS/SK/DE spelling; otherwise the
        # language is detected from title/description — see that module
        # for why title takes priority over description (many records'
        # description is scope/abstract text in a different language than
        # the document itself).
        language = normalize_raw_language(item.get("jazyk", ""))
        language_confident = language is not None
        if language is None:
            language, language_confident = detect_language(title, description)

        identifier = resolve_identifier(item.get("znacka", ""), seen_identifiers)

        # src/tools/norm_title.py, 2026-09-15: Norma titles never carried
        # their own designation (e.g. "ČSN EN 17124") — prefix it, same
        # one-time fix as backfill_norm_designation.py applied directly
        # to the already-imported DB, kept here too so a future rebuild
        # from JSON reproduces the same result.
        if doc_type == "Norma":
            title, _ = format_norm_title(title, identifier)

        jurisdikce = normalize_jurisdikce(item.get("jurisdikce", ""))
        file_path = resolve_file_path(item, fulltext_manifest)
        review_reasons = detect_data_quality_issues(item)
        if not language_confident:
            review_reasons.append(f"jazyk dokumentu byl automaticky odhadnut, ověřte ({language})")
        if gestor_unresolved_eu_act:
            review_reasons.append(
                "EU akt: autoritativní gestor (DG/instituce) se v EUR-Lex/Cellar nepodařilo dohledat")
        needs_review = bool(review_reasons)
        review_reason = "; ".join(review_reasons) or None

        type_id = get_or_create(
            cursor, "DocumentType", {"name": doc_type},
            extra_insert_cols={"restricted_fulltext": is_restricted_document_type(doc_type)})

        source_id = None
        if source:
            institution_type, source_jurisdiction = resolve_source_jurisdiction(
                source, gestor_jurisdiction_map)
            source_id = get_or_create(
                cursor, "DocumentSource", {"name": source},
                extra_insert_cols={"institution_type": institution_type,
                                    "jurisdiction": source_jurisdiction})

        # doc/PLAN.md §15, 2026-09-15: zdroj_dat/nazev_autoritativni/
        # popis_autoritativni/zdroj_autoritativni_url/jurisdikce_puvodni
        # are direct, literal pass-through — audit/provenance companions
        # to the already-resolved title/description/url/jurisdikce above,
        # never themselves resolved further. zdroj_dat is pure
        # provenance (which spreadsheet(s) contributed this record) —
        # nothing may branch behavior on it (see fetch_authoritative_
        # metadata.py/fetch_fulltext.py, switched to typ_dokumentu-based
        # checks instead).
        cursor.execute("""
            INSERT INTO Document
            (title, description, type_id, source_id, language, url,
             effective_date, identifier, jurisdikce, file_path,
             needs_review, review_reason,
             zdroj_dat, nazev_autoritativni, popis_autoritativni,
             zdroj_autoritativni_url, jurisdikce_puvodni)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (title, description, type_id, source_id, language, url,
              effective_date, identifier, jurisdikce, file_path,
              needs_review, review_reason,
              item.get("zdroj_dat") or None, item.get("nazev_autoritativni") or None,
              item.get("popis_autoritativni") or None, item.get("zdroj_autoritativni_url") or None,
              item.get("jurisdikce_puvodni") or None))

        doc_id = cursor.lastrowid

        if needs_review:
            incomplete_records.append({
                "document_id": doc_id, "znacka": item.get("znacka", ""),
                "title": title, "reasons": review_reasons,
            })

        for v in resolve_document_versions(item):
            cursor.execute("""
                INSERT INTO DocumentVersion
                (document_id, version, edition_label, effective_date, is_current, lifecycle_state)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (doc_id, v["version"], v["edition_label"], v["effective_date"], v["is_current"],
                  v["lifecycle_state"]))

        klicova_slova = item.get("klicova_slova", [])
        if not isinstance(klicova_slova, list):
            klicova_slova = [klicova_slova]

        sekce = item.get("sekce", "").strip()
        kategorie = item.get("kategorie_trida", "").strip()

        if sekce and sekce not in klicova_slova:
            klicova_slova.append(sekce)
        if kategorie and kategorie not in klicova_slova:
            klicova_slova.append(kategorie)

        for kw in klicova_slova:
            if isinstance(kw, str) and kw.strip():
                kw_id = get_or_create(cursor, "Keyword", {"keyword": kw.strip()})
                try:
                    cursor.execute(
                        "INSERT INTO DocumentKeyword (document_id, keyword_id) VALUES (%s, %s)",
                        (doc_id, kw_id))
                except pymysql.err.IntegrityError:
                    pass

    db_conn.commit()

    with open(INCOMPLETE_RECORDS_QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump(incomplete_records, f, ensure_ascii=False, indent=2)

    print("Import complete.")
    print(f"{len(incomplete_records)} documents flagged for manual review -> "
          f"{INCOMPLETE_RECORDS_QUEUE_PATH}")


if __name__ == "__main__":
    conn = get_connection()

    reset_tables(conn.cursor())
    conn.commit()

    import_json_data(conn)

    c = conn.cursor()
    print("\n--- Database Stats ---")
    c.execute("SELECT COUNT(*) FROM Document")
    print(f"Total Documents: {c.fetchone()[0]}")
    c.execute("SELECT COUNT(*) FROM DocumentSource")
    print(f"Unique Sources: {c.fetchone()[0]}")
    c.execute("SELECT COUNT(*) FROM Keyword")
    print(f"Unique Keywords extracted from filenames: {c.fetchone()[0]}")
    c.execute("SELECT COUNT(*) FROM DocumentVersion")
    print(f"Document versions: {c.fetchone()[0]}")
    c.execute("SELECT COUNT(*) FROM Document WHERE identifier IS NOT NULL")
    print(f"Documents with a resolved identifier: {c.fetchone()[0]}")
    c.execute("SELECT COUNT(*) FROM Document WHERE file_path IS NOT NULL")
    print(f"Documents with a locally-cached full text (file_path): {c.fetchone()[0]}")
    c.execute("SELECT COUNT(*) FROM Document WHERE needs_review = TRUE")
    print(f"Documents flagged needs_review: {c.fetchone()[0]}")

    conn.close()
