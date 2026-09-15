import json
import pathlib
import re

BASE_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent
SITE_METADATA_CACHE_PATH = REPO_ROOT / "data" / "site_metadata_cache.json"

def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


# A designation that IS the bare international ISO/IEC number itself — no
# ČSN prefix at all (e.g. "ISO 22734:2019", "ISO 11114-4") — is the
# international standard, not a ČSN adoption, even though it came in via
# the Prokop source (a curated hydrogen-standards reading list, not
# exclusively a ČSN catalog — some entries just cite the international
# standard directly, not yet/never separately ČSN-numbered). Mirrors
# parse_sinay_norms.py's own `_BARE_ISO_IEC_DESIGNATION_RE` (duplicated,
# not imported — this module has no other dependency on that one and the
# two already duplicate other jurisdikce-adjacent logic independently).
_BARE_ISO_IEC_DESIGNATION_RE = re.compile(r"^(?:ISO|IEC)(?:/[A-Z]+)?\s+\d", re.IGNORECASE)

# A bare "EN ISO"/"EN IEC" combination (the European, CEN/CENELEC-level
# adoption, no ČSN prefix) is likewise not a ČSN adoption — see
# parse_sinay_norms.py's own `_BARE_EN_ISO_DESIGNATION_RE` (duplicated for
# the same independent-module reason as above; Step 1 follow-up #16).
_BARE_EN_ISO_DESIGNATION_RE = re.compile(
    r"^(?:pr|F\s*pr)?EN\s+(?:ISO|IEC)(?:/[A-Z]+)?\s+\d", re.IGNORECASE)

# A bare "EN <number>" with NO following ISO/IEC (e.g. "EN 17127") is
# itself a genuine CEN/CENELEC standard, not a re-badging of an ISO/IEC
# one — it IS the European original (doc/PLAN.md §9, 2026-09-13, found
# via live agentura-cas.cz lookups: "ČSN EN 17127" is a real national
# adoption of bare "EN 17127", which must not be marked CZ either).
_BARE_EN_DESIGNATION_RE = re.compile(r"^(?:pr|F\s*pr)?EN\s+\d", re.IGNORECASE)


def resolve_prokop_jurisdikce(znacka):
    """Prokop is a curated ČSN-adjacent hydrogen-standards list — almost
    all entries are real ČSN adoptions, unambiguously CZ-valid, but a bare
    international ISO/IEC designation (see `_BARE_ISO_IEC_DESIGNATION_RE`)
    is the international standard itself, a bare "EN ISO"/"EN IEC"
    combination (see `_BARE_EN_ISO_DESIGNATION_RE`) is its European
    adoption, and a bare "EN <number>" with no ISO/IEC after it (see
    `_BARE_EN_DESIGNATION_RE`) is itself a genuine CEN/CENELEC original —
    none of these is a ČSN adoption, and must never be marked CZ just
    because of which source file it came from (see doc/PLAN.md Step 1
    follow-up #14/#16, and §9 for the bare-EN case)."""
    znacka = znacka.strip()
    if _BARE_ISO_IEC_DESIGNATION_RE.match(znacka):
        return "mezinárodní"
    if _BARE_EN_ISO_DESIGNATION_RE.match(znacka) or _BARE_EN_DESIGNATION_RE.match(znacka):
        return "EU"
    return "CZ"


# doc/PLAN.md §11/§14, 2026-09-14/15: Sinay_Zakony used to hardcode every
# record as "Zákon" (Act) and Haltuf_Dokumenty's own typ_dokumentu is just
# a raw, uninterpreted numeric category id (e.g. "9", "10") from its own
# spreadsheet — both sources mix real Acts with Vyhlášky (decrees),
# Nařízení vlády (government regulations), EU regulations/directives/
# decisions, bare norm designations, and the occasional genuine UN/ECE or
# multilateral-treaty citation that's none of the above. Classified from
# the record's own resolved title text (the same field
# extract_znacka_from_title() already runs on) by the same leading-word
# legal-drafting convention Czech/Slovak legislation already follows,
# extended with the English equivalents Haltuf's own English-language
# title rows use ("Directive"/"Regulation"/"Decision"/"Commission") —
# never guessed: an EU institutional act is recognized by an explicit
# "(EU)"/"(EÚ)" marker or a named EU institution (European Parliament/
# Council/Commission/European Central Bank, in Czech, Slovak, or
# English), verified against the real corpus (both sources, ~230 records)
# not to trigger on any genuine national Zákon/Vyhláška/Nařízení vlády
# title, nor on a genuine non-EU international instrument (ADR, RID,
# UN/ECE regulations — these correctly stay unclassified: they cite
# "Regulation"/"Agreement" too, but without any EU/CZ/SK institution or
# body attached, so the EU-institution gate never opens for them and the
# national-prefix checks below don't match them either).
_EU_INSTITUTION_RE = re.compile(
    r"\((?:EU|EÚ)\)|evropsk[ée]ho parlamentu|evropskej? rady|\bkomis[ei]|"
    r"evropsk[ée] centráln[íí] banky|european parliament|european central bank|"
    r"\bof the council\b|\bcommission\b", re.IGNORECASE)
# Not anchored at the start (unlike Vyhláška/Nařízení vlády below) — Haltuf
# often uses a compound-noun form ("Energetický zákon", "Stavební zákon",
# "novela Zákona o drahách") where "zákon" isn't the title's first word.
_ZAKON_RE = re.compile(r"^\s*zákon(?:í?k)?\b|\bzákon(?:a|ík)?\b", re.IGNORECASE)
_VYHLASKA_RE = re.compile(r"^\s*vyhlá[šs]", re.IGNORECASE)
_NARIZENI_VLADY_RE = re.compile(r"^\s*(?:nařízení|nariadenie)\s+vlády", re.IGNORECASE)
_SMERNICE_RE = re.compile(r"směrnice|smernica|\bdirective\b", re.IGNORECASE)
_NARIZENI_RE = re.compile(r"nařízení|nariadenie|\bregulation\b", re.IGNORECASE)
_ROZHODNUTI_RE = re.compile(r"rozhodnutí|rozhodnutie|\bdecision\b", re.IGNORECASE)
# Same designation-prefix shape as fetch_fulltext.py's own
# is_norm_designation() (duplicated, not imported — see this module's
# established convention of keeping each construction branch
# independent) — Haltuf mixes bare norm citations in among its laws.
_NORM_DESIGNATION_PREFIX_RE = re.compile(
    r"^(?:ČSN|CSN|STN|TNI|DIN|VDE|NF|BS|NEN|ISO|IEC|EN)\b", re.IGNORECASE)


def classify_law_document_typ(nazev):
    """Returns the real DocumentType name for a Sinay_Zakony/
    Haltuf_Dokumenty record from its own title text, or "" when genuinely
    unclear (e.g. a policy strategy paper, or a UN/ECE/multilateral-treaty
    regulation — neither is any of the types below; "" falls back to
    init_db.py's own FALLBACK_DOCUMENT_TYPE, same as a blank/numeric
    typ_dokumentu elsewhere in this pipeline — never force-guessed into
    the wrong bucket). Safe to call per-raw-record before deduplication:
    when one language variant of a multi-row record doesn't state its own
    type clearly (a real corpus case — a truncated Czech TSI title that
    omits its own "Nařízení Komise" lead-in) and a same-znacka sibling row
    does, programmatic_merge()'s existing backfill-from-any-member logic
    already resolves it post-merge without any change needed there.

    Within a confirmed EU act, the type keyword is matched by EARLIEST
    position in the text, not a fixed priority order — a real corpus case
    (`"Nařízení ... (EU) 2023/1804 ... o zrušení směrnice 2014/94/EU"`)
    states its own type ("Nařízení") up front and only later cites an
    unrelated directive it repeals; checking `"směrnice"` before
    `"nařízení"` unconditionally would misclassify it as the repealed
    act's type instead of its own."""
    n = (nazev or "").strip()
    if not n:
        return ""
    if _NORM_DESIGNATION_PREFIX_RE.match(n):
        return "Norma"
    if _EU_INSTITUTION_RE.search(n):
        earliest = None
        for label, pattern in (("Směrnice EU", _SMERNICE_RE),
                                ("Rozhodnutí EU", _ROZHODNUTI_RE),
                                ("Nařízení EU", _NARIZENI_RE)):
            m = pattern.search(n)
            if m and (earliest is None or m.start() < earliest[0]):
                earliest = (m.start(), label)
        return earliest[1] if earliest else ""
    if _ZAKON_RE.search(n):
        return "Zákon"
    if _VYHLASKA_RE.match(n):
        return "Vyhláška"
    if _NARIZENI_VLADY_RE.match(n):
        return "Nařízení vlády"
    return ""


def extract_znacka_from_title(title):
    """Haltuf and Sinay never fill in 'znacka' — the reference number (EU
    act number, EN/ISO/ČSN standard code, Czech "Sb." or Slovak "Z. z." law
    citation, ...) instead lives inside the title text itself, e.g.
    "(EU) 2019/773 - TSI OPE - ...", a bare "EN 17339", or "Zákon č.
    201/2012 Sb., o ochraně ovzduší" (Haltuf's titles put it as a leading
    token; Sinay's put it mid-sentence in prose). Extracts it so records
    citing the same instrument — across sources and languages — get a
    real, comparable znacka instead of relying purely on (weak,
    cross-lingual) title similarity. Conservative on purpose: returns ""
    rather than guess when unsure — an empty znacka just falls back to
    today's title-only behavior, never worse than before this function
    existed.
    """
    if not title:
        return ""
    t = title.strip()

    # Case A: a trailing bracketed OJ-style reference, e.g. "... [2019/795]"
    # — appears identically regardless of the title's language, so it's a
    # stronger cross-lingual signal than the leading token when present.
    m = re.search(r'\[(\d{3,4}/\d+)\]\s*$', t)
    if m:
        return f"[{m.group(1)}]"

    # Case B: a leading EU/ES act number with NO dash separator following it
    # (e.g. "2014/34/EU \nDIRECTIVE ..." — its Czech counterpart has a dash
    # and is already caught by case C, but this variant isn't).
    m = re.match(r'^\(?\s*(?:EU|EÚ|ES)\s*\)?\s*\d{3,5}/\d+', t)
    if m:
        return ' '.join(m.group(0).split())
    m = re.match(r'^\d{3,5}/\d+/(?:EU|ES|EÚ)', t)
    if m:
        return ' '.join(m.group(0).split())

    # Case C: a leading code followed by a ' - ' separator, e.g.
    # "(EU) 2024/1788 - SMĚRNICE ..." / "2014/68/EU - DIRECTIVE ...". Requires
    # whitespace on BOTH sides of the dash — a bare part-numbered code like
    # "ČSN EN ISO 19880-1" has a hyphen with no surrounding spaces, which
    # must fall through to case E instead (this used to wrongly truncate
    # to "ČSN EN ISO 19880", dropping the "-1").
    m = re.match(r'^(.{1,60}?)\s+-\s+\S', t, re.DOTALL)
    if m:
        candidate = ' '.join(m.group(1).split())
        if re.search(r'\d', candidate):
            return candidate

    # Case D: a Czech "č. NNN/YYYY Sb." or Slovak "č. NNN/YYYY Z. z." law
    # citation anywhere in the title (e.g. "Zákon o ochraně ovzduší (č.
    # 201/2012 Sb.)", "Nařízení vlády č. 116/2016 Sb., o ...", "Vyhláška
    # č. 94/2004 Z. z"). CZ and SK are separate legal systems — the suffix
    # is kept in the extracted value so a Czech and Slovak law sharing the
    # same number never collide as the same znacka.
    m = re.search(r'č\.?\s*(\d{1,4}\s*/\s*\d{4})\s*Sb\.', t, re.IGNORECASE)
    if m:
        number = re.sub(r'\s+', '', m.group(1))
        return f"{number} Sb."
    m = re.search(r'č\.?\s*(\d{1,4}\s*/\s*\d{4})\s*Z\s*\.?\s*z\s*\.?', t, re.IGNORECASE)
    if m:
        number = re.sub(r'\s+', '', m.group(1))
        return f"{number} Z. z."

    # Case F: an EU/ES/EÚ act number anywhere in the text, not just leading
    # — needed for Sinay's prose titles, e.g. "Nařízení Evropského
    # parlamentu a Rady (EU) 2022/869 ze dne ...". EÚ (Slovak) and ES (the
    # pre-Lisbon designation) are normalized to EU so the same act cited
    # under any of the three still compares equal.
    m = re.search(r'\(\s*(?:EU|EÚ|ES)\s*\)\s*\d{3,5}/\d+', t)
    if m:
        return ' '.join(m.group(0).split()).replace('EÚ', 'EU').replace('ES', 'EU')
    m = re.search(r'\d{3,5}/\d+\s*/\s*(?:EU|ES|EÚ)\b', t)
    if m:
        return ' '.join(m.group(0).split())

    # Case E: the whole title IS just a bare code, no separator (e.g.
    # "EN 17339", "ČSN EN ISO 19880-1", "ISO 14687").
    whole = ' '.join(t.split())
    if len(whole) <= 40 and re.search(r'\d', whole):
        return whole

    return ""

def load_previous_annotations(output_file):
    """Returns a {(zdroj_dat, nazev_cz): anotace_poznamka} lookup from the
    currently-existing output file, so re-running this script never
    silently discards annotation text some other (often untracked, manual,
    or historical) enrichment pass previously added — see doc/PLAN.md
    Step 1 for the incident this fixes."""
    if not output_file.exists():
        return {}
    try:
        previous = load_json(output_file)
    except (json.JSONDecodeError, OSError):
        return {}
    lookup = {}
    for r in previous:
        note = r.get("anotace_poznamka", "").strip()
        if note:
            lookup[(r.get("zdroj_dat", ""), r.get("nazev_cz", ""))] = note
    return lookup


def load_site_metadata_cache():
    """doc/REQUIREMENTS.md-adjacent, doc/PLAN.md §8, 2026-09-11: reads
    data/site_metadata_cache.json (built by src/tools/
    fetch_authoritative_metadata.py) — empty dict if it doesn't exist yet
    (e.g. a fresh checkout that hasn't run that script)."""
    if SITE_METADATA_CACHE_PATH.exists():
        return load_json(SITE_METADATA_CACHE_PATH)
    return {}


def record_url(item):
    """Same precedence as init_db.py's own `url` field resolution:
    odkaz_hlavni -> odkaz_eu -> odkaz_sk, first non-empty wins."""
    for field in ("odkaz_hlavni", "odkaz_eu", "odkaz_sk"):
        url = (item.get(field) or "").strip()
        if url:
            return url
    return ""


def apply_authoritative_metadata(record, cache):
    """Attaches nazev_autoritativni/popis_autoritativni/
    zdroj_autoritativni_url from the site-metadata cache when a
    successfully-fetched entry exists for this record's URL (or, for
    ČSN records with no per-document URL of their own, its
    "csn:<znacka>" key) — mutates `record` in place, returns nothing.
    Deliberately NEVER overwrites nazev_cz/anotace_poznamka: the
    authoritative title can be in a different language, or simply differ
    from the spreadsheet-derived one, so it's kept as its own, clearly-
    provenanced field rather than silently replacing what's already
    there — downstream consumers that want the verified value use the
    new field explicitly (see src/tools/init_db.py).

    doc/PLAN.md §9, 2026-09-13: for a bare EN/ISO/IEC record confirmed by
    agentura-cas.cz to be the international original of a Czech ČSN
    adoption, the cache also carries `jurisdikce_autoritativni` — this
    field IS applied directly to `record["jurisdikce"]` (unlike title/
    description, jurisdikce is read as-is by deduplicate_db.py/
    link_document_relations_auto.py, so a stale/blank value there isn't
    just cosmetic — it silently breaks the ADOPTS auto-linking). The
    original raw value is kept under `jurisdikce_puvodni` for audit."""
    znacka = (record.get("znacka") or "").strip()
    url = record_url(record)
    entry = cache.get(url) if url else None
    if entry is None and znacka:
        entry = cache.get(f"csn:{znacka}")
    if entry is None or entry.get("status") != "fetched":
        return
    if entry.get("title"):
        record["nazev_autoritativni"] = entry["title"]
    if entry.get("description"):
        record["popis_autoritativni"] = entry["description"]
    record["zdroj_autoritativni_url"] = (
        entry.get("zdroj_esbirka_url") or entry.get("zdroj_autoritativni_url") or url or None)
    if entry.get("jurisdikce_autoritativni") and entry["jurisdikce_autoritativni"] != record.get("jurisdikce"):
        record["jurisdikce_puvodni"] = record.get("jurisdikce", "")
        record["jurisdikce"] = entry["jurisdikce_autoritativni"]


def synthesize_csn_adoption_records(unified_db, cache):
    """doc/PLAN.md §9, 2026-09-13: for every cache entry carrying a
    `synthesize` block (written by fetch_authoritative_metadata.py when
    agentura-cas.cz confirms a Czech ČSN adoption of a bare EN/ISO/IEC
    record that has no record of its own anywhere in the corpus yet —
    e.g. "ČSN EN 17339" for bare "EN 17339"), appends a new minimal
    record for it. Idempotent by construction: skipped if a record with
    that exact znacka already exists in `unified_db` (a rerun after the
    record has since appeared some other way is a no-op, never a
    duplicate)."""
    existing = {(r.get("znacka") or "").strip().lower() for r in unified_db}
    added = 0
    for entry in cache.values():
        block = entry.get("synthesize")
        if not block:
            continue
        key = (block.get("znacka") or "").strip().lower()
        if not key or key in existing:
            continue
        record = {
            "zdroj_dat": block["zdroj_dat"],
            "nazev_cz": block.get("nazev_cz", ""),
            "znacka": block["znacka"],
            "typ_dokumentu": block.get("typ_dokumentu", "Norma"),
            "sekce": "",
            "kategorie_trida": "",
            "klicova_slova": [],
            "odkaz_hlavni": block.get("odkaz_hlavni", ""),
            "nazev_eu": "",
            "odkaz_eu": "",
            "nazev_sk": "",
            "odkaz_sk": "",
            "platnost": "",
            "ratifikovan": "",
            "gestor": [],
            "jazyk": "",
            "anotace_poznamka": "",
            "jurisdikce": block.get("jurisdikce", ""),
        }
        if block.get("nazev_autoritativni"):
            record["nazev_autoritativni"] = block["nazev_autoritativni"]
        if block.get("zdroj_autoritativni_url"):
            record["zdroj_autoritativni_url"] = block["zdroj_autoritativni_url"]
        unified_db.append(record)
        existing.add(key)
        added += 1
    return added

def build_unified_db():
    base_dir = REPO_ROOT / "data"

    file_prokop = base_dir / "20250303_Prokop" / "normy_vodik.json"
    file_sinay = base_dir / "20250712_Sinay" / "sinay_zakony_processed.json"
    file_haltuf = base_dir / "20250915_Haltuf" / "haltuf_combined.json"
    file_sinay_normy = base_dir / "20250712_Sinay" / "sinay_normy_processed.json"

    output_file = base_dir / "database_merged_raw.json"

    previous_annotations = load_previous_annotations(output_file)
    restored_count = 0

    unified_db = []

    # 1. Process Prokop Norms
    try:
        data_prokop = load_json(file_prokop)
        for item in data_prokop:
            klicova_slova = item.get("Klíčová slova", "")
            if klicova_slova and klicova_slova != "-":
                klicova_slova = [x.strip() for x in klicova_slova.split(",") if x.strip()]
            else:
                klicova_slova = []

            znacka = item.get("Značka", "").strip()
            record = {
                "zdroj_dat": "Prokop_Normy",
                "nazev_cz": item.get("Název", "").strip(),
                "znacka": znacka,
                "typ_dokumentu": "Norma",
                "sekce": item.get("Sekce", "").strip(),
                "kategorie_trida": item.get("Kategorie", "").strip(),
                "klicova_slova": klicova_slova,
                "odkaz_hlavni": item.get("Link", "").strip(),
                "nazev_eu": "",
                "odkaz_eu": "",
                "nazev_sk": "",
                "odkaz_sk": "",
                "platnost": item.get("Platnost", "").strip(),
                "ratifikovan": "",
                "gestor": [],
                "jazyk": "",
                "anotace_poznamka": item.get("Anotace", "").strip(),
                # Prokop = mostly real ČSN norms, unambiguously CZ-valid —
                # except a bare international ISO/IEC designation, never a
                # ČSN adoption regardless of source file. See
                # resolve_prokop_jurisdikce() and the jurisdikce note on
                # the Sinay_Normy branch below for why this field exists.
                "jurisdikce": resolve_prokop_jurisdikce(znacka),
            }
            if not record["anotace_poznamka"]:
                prev = previous_annotations.get((record["zdroj_dat"], record["nazev_cz"]))
                if prev:
                    record["anotace_poznamka"] = prev
                    restored_count += 1
            unified_db.append(record)
        print(f"Loaded {len(data_prokop)} records from Prokop.")
    except Exception as e:
        print(f"Error loading Prokop data: {e}")

    # 2. Process Sinay Zákony
    try:
        data_sinay = load_json(file_sinay)
        for item in data_sinay:
            # For Sinay, primarily a Czech law mapping, else falling back to original SK equivalent
            nazev_cz = item.get("Dokument CZ", "").strip()
            if not nazev_cz:
                nazev_cz = item.get("Dokument SK", "").strip()

            gestor = item.get("Gestor CZ", [])
            if isinstance(gestor, str):
                gestor = [gestor]

            record = {
                "zdroj_dat": "Sinay_Zakony",
                "nazev_cz": nazev_cz,
                "znacka": extract_znacka_from_title(nazev_cz),
                "typ_dokumentu": classify_law_document_typ(nazev_cz),
                "sekce": "",
                "kategorie_trida": "",
                "klicova_slova": [],
                "odkaz_hlavni": item.get("URL CZ", "").strip(),
                "nazev_eu": item.get("Dokument EU", "").strip(),
                "odkaz_eu": item.get("URL EU", "").strip(),
                "nazev_sk": item.get("Dokument SK", "").strip(),
                "odkaz_sk": item.get("URL SK", "").strip(),
                "platnost": "",
                "ratifikovan": "",
                "gestor": gestor,
                "jazyk": "",
                "anotace_poznamka": "",
                # Left unset (not "CZ"): this source mixes Czech law
                # equivalents with the original Slovak text under
                # nazev_sk — not confidently one single jurisdiction per
                # record without deeper work than was asked for here.
                "jurisdikce": "",
            }
            prev = previous_annotations.get((record["zdroj_dat"], record["nazev_cz"]))
            if prev:
                record["anotace_poznamka"] = prev
                restored_count += 1
            unified_db.append(record)
        print(f"Loaded {len(data_sinay)} records from Sinay.")
    except Exception as e:
        print(f"Error loading Sinay data: {e}")

    # 3. Process Haltuf Dokumenty
    try:
        data_haltuf = load_json(file_haltuf)
        for item in data_haltuf:
            
            # Extract combined gestor logic
            resort = item.get("Odpovědný resort", "").strip()
            organ = item.get("Odpovědný orgán", "").strip()
            dg = item.get("Odpovědné DG", "").strip()
            
            gestor = []
            for g in [resort, organ, dg]:
                if g:
                    gestor.append(g)

            nazev_cz = item.get("Název dokumentu", "").strip()
            record = {
                "zdroj_dat": "Haltuf_Dokumenty",
                "nazev_cz": nazev_cz,
                "znacka": extract_znacka_from_title(nazev_cz),
                "typ_dokumentu": classify_law_document_typ(nazev_cz),
                "sekce": item.get("Sekce", "").strip(),
                "kategorie_trida": item.get("Třída", "").strip(),
                "klicova_slova": [],
                "odkaz_hlavni": item.get("Odkaz na zdroj", "").strip(),
                "nazev_eu": "",
                "odkaz_eu": "", 
                "nazev_sk": "",
                "odkaz_sk": "",
                "platnost": item.get("Platnost", "").strip(),
                "ratifikovan": item.get("Ratifikován", "").strip(),
                "gestor": gestor,
                "jazyk": item.get("Jazyková verze", "").strip(),
                "anotace_poznamka": item.get("Poznámka", "").strip(),
                # Left unset: Haltuf mixes EU regulations, Czech laws, and
                # bare EN/ISO standard codes with no per-record
                # jurisdiction marker of its own — not confidently
                # classified without deeper work than was asked for here.
                "jurisdikce": "",
            }
            # Attempt to map EUR-lex links to odkaz_eu heuristically
            if "eur-lex.europa.eu" in record["odkaz_hlavni"]:
                 record["odkaz_eu"] = record["odkaz_hlavni"]

            if not record["anotace_poznamka"]:
                prev = previous_annotations.get((record["zdroj_dat"], record["nazev_cz"]))
                if prev:
                    record["anotace_poznamka"] = prev
                    restored_count += 1

            unified_db.append(record)
        print(f"Loaded {len(data_haltuf)} records from Haltuf.")
    except Exception as e:
        print(f"Error loading Haltuf data: {e}")

    # 4. Process Sinay Norms (STN/German standards — see
    # src/tools/parse_sinay_norms.py). Unlike the other three sources,
    # this one is majority NOT Czech: an STN (Slovak) or German (DIN/VDI/
    # DVGW/...) norm is not automatically valid in Czechia just because it
    # shares an EN/ISO ancestor with a ČSN — "jurisdikce" (populated
    # per-record by the parser) exists specifically so this pipeline can
    # tell them apart and never conflate a foreign adoption with a Czech
    # one, however similar their reference numbers or titles look. See
    # doc/PLAN.md Step 1 follow-up #8 and deduplicate_db.py's jurisdiction
    # veto in build_clusters().
    try:
        data_sinay_normy = load_json(file_sinay_normy)
        for item in data_sinay_normy:
            klicova_slova = item.get("Klíčová slova", "")
            if klicova_slova and klicova_slova != "-":
                klicova_slova = [x.strip() for x in klicova_slova.split(",") if x.strip()]
            else:
                klicova_slova = []

            record = {
                "zdroj_dat": "Sinay_Normy",
                "nazev_cz": item.get("Název", "").strip(),
                "znacka": item.get("Značka", "").strip(),
                "typ_dokumentu": "Norma",
                "sekce": item.get("Sekce", "").strip(),
                "kategorie_trida": item.get("Kategorie", "").strip(),
                "klicova_slova": klicova_slova,
                "odkaz_hlavni": item.get("Link", "").strip(),
                "nazev_eu": "",
                "odkaz_eu": "",
                "nazev_sk": "",
                "odkaz_sk": "",
                "platnost": item.get("Platnost", "").strip(),
                "ratifikovan": "",
                "gestor": [],
                "jazyk": "",
                "anotace_poznamka": item.get("Anotace", "").strip(),
                "jurisdikce": item.get("Jurisdikce", "").strip(),
            }
            if not record["anotace_poznamka"]:
                prev = previous_annotations.get((record["zdroj_dat"], record["nazev_cz"]))
                if prev:
                    record["anotace_poznamka"] = prev
                    restored_count += 1
            unified_db.append(record)
        print(f"Loaded {len(data_sinay_normy)} records from Sinay Normy.")
    except Exception as e:
        print(f"Error loading Sinay Normy data: {e}")

    # 5. V02 Bibliography — a small, hand-curated set of laws/regulations/
    # norms cited by doc/NAHYC DP004 V02 - Popis procesů.docx (nodes
    # U2/U4/U5/U6/U7 and its own bibliography) that turned out to be
    # missing from the corpus entirely (Step 1 follow-up #17) — confirmed
    # genuinely absent, not a citation-matching bug, by cross-checking
    # every unmatched load_process_layer.py review-queue entry against
    # this file before adding it. Already in final record shape (no raw
    # source spreadsheet exists to parse — verified directly from the V02
    # bibliography text plus well-established ministry assignments), so
    # this block just appends it as-is, unlike the four parsed sources
    # above.
    file_v02_bibliography = base_dir / "v02_bibliography_documents.json"
    try:
        data_v02_bibliography = load_json(file_v02_bibliography)
        unified_db.extend(data_v02_bibliography)
        print(f"Loaded {len(data_v02_bibliography)} records from V02 Bibliography.")
    except Exception as e:
        print(f"Error loading V02 Bibliography data: {e}")

    # 6. EU Transposition Targets — doc/REQUIREMENTS.md R1.3, 2026-09-11: a
    # small, hand-curated set of the EU acts (directives/regulations/an
    # implementing decision) that real national-law records in this corpus
    # (201/2012 Sb., 56/2001 Sb., 458/2000 Sb.) cite in their own nazev_eu/
    # odkaz_eu but that were, until now, missing from the corpus entirely —
    # found by src/tools/link_document_relations_auto.py and written to
    # data/eu_transposition_missing_targets.json, then verified one by one
    # directly against eur-lex.europa.eu (title/date/type/CELEX number, and
    # the official Czech-language title + Official Journal reference) before
    # being added here — never guessed. Already in final record shape (no
    # raw spreadsheet exists behind these), so this block just appends it
    # as-is, same as V02 Bibliography above. Adding these lets
    # link_document_relations_auto.py's find_eu_transposition_pairs()
    # produce real `IMPLEMENTS` edges instead of only missing-target
    # candidates (see doc/PLAN.md §6).
    file_eu_transposition_targets = base_dir / "eu_transposition_targets.json"
    try:
        data_eu_transposition_targets = load_json(file_eu_transposition_targets)
        unified_db.extend(data_eu_transposition_targets)
        print(f"Loaded {len(data_eu_transposition_targets)} records from EU Transposition Targets.")
    except Exception as e:
        print(f"Error loading EU Transposition Targets data: {e}")

    # 7. Authoritative per-site title/description overlay — doc/PLAN.md §8,
    # 2026-09-11: attaches nazev_autoritativni/popis_autoritativni (and,
    # for records src/sites/esbirka.py could verify, the confirmed
    # government zdroj_autoritativni_url) from data/site_metadata_cache.json
    # (built by src/tools/fetch_authoritative_metadata.py) onto every
    # record with a cached, successfully-fetched entry. Applied here, at
    # the end of every build, so it survives every rebuild automatically —
    # this is exactly the trap this session found and worked around for
    # enrich_annotations.py's edits (see fetch_authoritative_metadata.py's
    # own docstring): a downstream patch to
    # database_merged_deduplicated.json is silently discarded by the next
    # raw rebuild, but reading a persistent, git-tracked cache HERE is not.
    site_metadata_cache = load_site_metadata_cache()
    authoritative_count = 0
    for record in unified_db:
        apply_authoritative_metadata(record, site_metadata_cache)
        if "nazev_autoritativni" in record:
            authoritative_count += 1
    if authoritative_count:
        print(f"Applied authoritative title/description to {authoritative_count} record(s) "
              f"from {SITE_METADATA_CACHE_PATH.relative_to(REPO_ROOT)}.")

    synthesized_count = synthesize_csn_adoption_records(unified_db, site_metadata_cache)
    if synthesized_count:
        print(f"Added {synthesized_count} new ČSN-adoption record(s) confirmed by "
              f"agentura-cas.cz with no prior record of their own (doc/PLAN.md §9).")

    # 8. Save combined to JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(unified_db, f, ensure_ascii=False, indent=4)

    if previous_annotations:
        print(f"Restored {restored_count} annotation(s) from the previous {output_file.name} "
              f"(matched by zdroj_dat+nazev_cz) that this run's sources don't themselves provide.")
    print(f"Done. Unified database created with {len(unified_db)} total records at {output_file}")

if __name__ == "__main__":
    build_unified_db()
