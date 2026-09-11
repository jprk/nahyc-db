import os
import json
import logging
import datetime
import pathlib
import math
import re
import time
from openai import OpenAI

# Nastavení logování
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = f"deduplication_{timestamp}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Inicializace OpenAI klienta
BASE_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent
API_KEY_PATH = REPO_ROOT / ".openapi_key"

try:
    with open(API_KEY_PATH, 'r', encoding='utf-8') as f:
        api_key = f.read().strip()
    os.environ['OPENAI_API_KEY'] = api_key
    client = OpenAI()
    logging.info("OpenAI API klíč úspěšně načten.")
except FileNotFoundError:
    logging.error(f"Soubor s API klíčem nebyl nalezen: {API_KEY_PATH}")
    exit(1)

MAX_LLM_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2

def cosine_similarity(v1, v2):
    dot_product = sum(a * b for a, b in zip(v1, v2))
    magnitude1 = math.sqrt(sum(a * a for a in v1))
    magnitude2 = math.sqrt(sum(b * b for b in v2))
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    return dot_product / (magnitude1 * magnitude2)

_DASH_VARIANTS_RE = re.compile(r"[‐-―−]")  # en/em/figure/horizontal-bar dashes, minus sign

# A trailing "/ - YYYY.MM" (or "/ – YYYY.MM") is a Sinay-parser edition-date
# suffix, not part of the standard's identity — e.g. "ISO 16111" and
# "ISO 16111/ - 2018.08" are the same standard. Requires the ".MM" month
# component (not just a bare trailing year) so a real identifier that
# happens to end in a year, e.g. "ADR 2025", is never touched. Deliberately
# does NOT strip an amendment marker before the date (e.g. "/A1 - 2024.02"
# or "-2+A1/ - 2024.02" keep their "+A1"/"/A1") — a base standard and its
# amendment are a separate, not-yet-resolved question (see doc/PLAN.md).
_EDITION_DATE_SUFFIX_RE = re.compile(r"/\s*-\s*\d{4}\.\d{2}\s*$")

# A second, rarer edition-year suffix style: "ISO 11413 :2019" (bare
# colon-year, no month) instead of the "/ - YYYY.MM" form above — same
# standard as "ISO 11413/ - 2019.03" once both are normalized. Requires a
# bare 4-digit year right after the colon so real part:edition citations
# like "CHMC 2:19" or "CSA HPIT 1:15" (2-digit year, a different Sinay
# citation convention) are never touched.
_COLON_YEAR_SUFFIX_RE = re.compile(r"\s*:\s*\d{4}\s*$")

# Two known document-series names appear in the corpus with an
# inconsistent "/" vs. " " (vs. no separator at all) between their parts —
# e.g. "CSA/ANSI HGV 2" vs. "CSA ANSI HGV 2", "IGEM/TD/1" vs. "IGEM TD1" —
# purely a citation-formatting difference, not a different document.
# Deliberately a short, explicit allowlist (not a blanket "fold every
# slash" rule): a generic transformation risks silently merging genuinely
# different designations elsewhere in the corpus (e.g. "STN CLC/TR
# 60079-32-1", where the "/" is meaningful). Each regex collapses all
# separators between the series' own tokens to nothing, so both spellings
# land on the same normalized form; everything after the series name
# (edition/part number, title fragment, ...) is left untouched.
_KNOWN_SERIES_SEPARATOR_RES = [
    re.compile(r"\bCSA\s*/?\s*ANSI\b", re.IGNORECASE),
    re.compile(r"\bIGEM\s*/?\s*TD\s*/?\s*1\b", re.IGNORECASE),
]


def _fold_known_series_separators(znacka):
    for pattern in _KNOWN_SERIES_SEPARATOR_RES:
        znacka = pattern.sub(lambda m: re.sub(r"[\s/]", "", m.group(0)), znacka)
    return znacka


def normalize_znacka(znacka):
    """Normalizes a znacka (reference number) for exact-match comparison.
    Also folds en-dash/em-dash/minus-sign variants to a plain hyphen — the
    Sinay PDF source uses "–" (en dash) and "-" (hyphen) interchangeably
    for the same date separator (e.g. "STN EN ISO 11114-1/ – 2020.12" vs
    "STN EN ISO 11114-1/ - 2020.12"), which otherwise silently defeats
    exact-match deduplication. Also strips a trailing edition-date suffix —
    either the "/ - YYYY.MM" form (`_EDITION_DATE_SUFFIX_RE`) or the rarer
    bare colon-year form, e.g. "ISO 11413 :2019" (`_COLON_YEAR_SUFFIX_RE`)
    — and folds a couple of known document-series "/" vs. " " spelling
    inconsistencies (see `_KNOWN_SERIES_SEPARATOR_RES`) for the same
    reason."""
    if not znacka:
        return ""
    znacka = _fold_known_series_separators(str(znacka))
    znacka = _DASH_VARIANTS_RE.sub("-", znacka)
    znacka = " ".join(znacka.split()).strip()
    znacka = _EDITION_DATE_SUFFIX_RE.sub("", znacka)
    znacka = _COLON_YEAR_SUFFIX_RE.sub("", znacka)
    return znacka.strip().lower()

def core_znacka(znacka):
    """Strips the optional Czech national-adoption prefix ('ČSN') so that
    'ČSN EN 17127' and 'EN 17127' compare as the same underlying standard —
    used for clustering, NOT for validate_merge's exact-membership check."""
    zn = normalize_znacka(znacka)
    if zn.startswith("čsn "):
        zn = zn[len("čsn "):]
    return zn

def validate_merge(cluster_records, merged_records):
    """Rejects a merge that (a) invents a znacka not present in the input
    cluster, or (b) still leaves two output records sharing the same
    znacka — the LLM sometimes fails to actually merge a cross-language
    (EN/CZ) pair or very sparse (title-only) records even when the
    deterministic znacka pre-pass already proved they're the same
    document. These are the two checks we can make without a source
    document to verify against."""
    input_znacka = {normalize_znacka(r.get("znacka", "")) for r in cluster_records}
    input_znacka.discard("")
    seen_output_znacka = set()
    for r in merged_records:
        zn = normalize_znacka(r.get("znacka", ""))
        if not zn:
            continue
        if zn not in input_znacka:
            return False, f"invented znacka '{zn}'"
        if zn in seen_output_znacka:
            return False, f"left {zn!r} split across multiple output records instead of merging them"
        seen_output_znacka.add(zn)
    return True, None

def deduplicate_cluster_with_llm(cluster_records):
    """
    Pomocí GPT-4o-mini sloučí nalezené podobné záznamy, pokud usoudí, že jde o tytéž dokumenty.
    Retries up to MAX_LLM_ATTEMPTS times on a call error or a failed sanity check;
    returns (merged_records, None) on success or (None, last_error) if every attempt failed.
    """
    logging.info(f"Odesílám {len(cluster_records)} kandidátů do GPT pro deduplikaci.")
    for i, r in enumerate(cluster_records):
        logging.info(f"  Kandidát {i+1}: {r.get('nazev_cz', '')} (Zdroj: {r.get('zdroj_dat', '')})")

    system_prompt = '''You are an expert data deduplication assistant for Czech regulatory documents.
You will be given a JSON array of records. Some or all of them might refer to the exact same law, norm, or document.
Your task is to merge the records that represent the same document into a single comprehensive record.
If some records actually represent distinct, different documents, keep them separate.
Output a JSON array of the resulting (merged or separate) records.

Merging Rules:
1. "nazev_cz": Use the most complete/official name.
2. "klicova_slova": Combine all unique keywords from the merged records into a single list.
3. "gestor": Combine all unique gestors into a single list.
4. "odkaz_hlavni", "odkaz_eu", "odkaz_sk": Keep the most functional/complete URL.
5. "zdroj_dat": Combine the sources into a comma-separated string (e.g. "Sinay_Zakony, Haltuf_Dokumenty").
6. Keep other metadata like "typ_dokumentu", "sekce", "kategorie_trida", "platnost" by picking the most descriptive/accurate one.
7. "znacka": Never invent a reference number. Only use a value that already appears on one of the input records.
8. CRITICAL: if two or more input records share the exact same non-empty "znacka", they are GUARANTEED to be the same document (verified by exact reference-number match before you ever saw them) — you MUST merge every one of them into a single output record, even if their titles look different (e.g. one is a Czech translation and the other is the English original). Never leave two output records with the same "znacka".
'''

    user_content = json.dumps({"records": cluster_records}, ensure_ascii=False)
    last_error = None
    for attempt in range(1, MAX_LLM_ATTEMPTS + 1):
        try:
            # On a retry, tell the model exactly what was wrong with its
            # last attempt — at temperature=0.0, resending an identical
            # prompt after a validation failure would likely just
            # reproduce the same wrong output.
            user_message = user_content
            if last_error:
                user_message = (
                    f"{user_content}\n\nYour previous attempt was rejected: {last_error} "
                    "Fix this and try again — pay special attention to rule 8: any input "
                    "records sharing the same non-empty znacka MUST end up as one output record."
                )

            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                response_format={ "type": "json_object" },
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.0
            )

            result_content = completion.choices[0].message.content
            result_json = json.loads(result_content)

            # Očekáváme JSON ve formátu {"records": [ ... ]} nebo jen pole
            merged_records = result_json.get("records", [])
            if not merged_records and isinstance(result_json, list):
                merged_records = result_json

            valid, reason = validate_merge(cluster_records, merged_records)
            if not valid:
                last_error = f"Neplatné sloučení: {reason}."
                logging.warning(f"Pokus {attempt}/{MAX_LLM_ATTEMPTS} zamítnut: {last_error}")
                if attempt < MAX_LLM_ATTEMPTS:
                    time.sleep(RETRY_BACKOFF_SECONDS * attempt)
                continue

            logging.info(f"Výsledek LLM: vytvořeno {len(merged_records)} záznamů z původních {len(cluster_records)}.")
            for i, r in enumerate(merged_records):
                logging.info(f"  Výsledek {i+1}: {r.get('nazev_cz', '')} (Sloučené zdroje: {r.get('zdroj_dat', '')})")

            return merged_records, None

        except Exception as e:
            last_error = str(e)
            logging.error(f"Chyba při volání LLM (pokus {attempt}/{MAX_LLM_ATTEMPTS}): {e}")
            if attempt < MAX_LLM_ATTEMPTS:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)

    logging.error(f"Shluk se nepodařilo sloučit po {MAX_LLM_ATTEMPTS} pokusech: {last_error}")
    return None, last_error

def is_pure_znacka_cluster(records):
    """True if every record in the cluster has a non-empty znacka and they
    all share the same core value — i.e. every member is certainly the
    same document, with zero probabilistic (semantic-similarity) judgment
    involved. For these, no LLM call is needed at all: which document this
    is isn't in question, only which field values to keep — and it turns
    out gpt-4o-mini isn't reliably able to actually collapse a large or
    very sparse (title-only) pure cluster into one record even when told
    to, so skip that failure mode entirely rather than retry around it.

    Also requires no known jurisdiction conflict among members — belt and
    suspenders alongside build_clusters' own veto: programmatic_merge does
    no identity judgment at all, so a cluster that slipped through with,
    say, a Czech and a Slovak record in it would get silently flattened
    into one record with no safety net otherwise."""
    cores = [core_znacka(r.get("znacka", "")) for r in records]
    if not (all(cores) and len(set(cores)) == 1):
        return False
    known_jurisdikce = {r.get("jurisdikce", "") for r in records if _jurisdikce_known(r.get("jurisdikce", ""))}
    return len(known_jurisdikce) <= 1

def programmatic_merge(cluster_records):
    """Deterministic merge for a pure znacka cluster (see
    is_pure_znacka_cluster): start from the most complete title, union
    list fields, backfill blank scalar fields from any member that has a
    value. No LLM involved — there's no identity judgment left to make."""
    best = max(cluster_records, key=lambda r: len(r.get("nazev_cz", "")))
    merged = dict(best)

    keywords, gestors, sources = [], [], []
    for r in cluster_records:
        for kw in r.get("klicova_slova", []):
            if kw not in keywords:
                keywords.append(kw)
        for g in r.get("gestor", []):
            if g not in gestors:
                gestors.append(g)
        # Split on ', ' first — a record here may itself already be the
        # (comma-joined) result of an earlier programmatic_merge, e.g. when
        # resolve_iso_csn_ambiguity merges across already-merged clusters.
        for src in r.get("zdroj_dat", "").split(", "):
            src = src.strip()
            if src and src not in sources:
                sources.append(src)
        for field in ("odkaz_hlavni", "odkaz_eu", "odkaz_sk", "nazev_eu", "nazev_sk",
                      "platnost", "ratifikovan", "jazyk", "typ_dokumentu", "sekce",
                      "kategorie_trida", "anotace_poznamka"):
            if not merged.get(field) and r.get(field):
                merged[field] = r.get(field)

    merged["klicova_slova"] = keywords
    merged["gestor"] = gestors
    merged["zdroj_dat"] = ", ".join(sources)

    # Prefer a "ČSN"-prefixed znacka (the more formal/complete citation) if
    # any member has one, else whatever's there — all members share the
    # same core already, this is purely cosmetic.
    znackas = [r.get("znacka", "").strip() for r in cluster_records if r.get("znacka", "").strip()]
    csn_variant = next((z for z in znackas if z.lower().startswith("čsn ")), None)
    merged["znacka"] = csn_variant or znackas[0]

    merged.pop("_search_text", None)
    merged.pop("_embedding", None)
    return merged

def match_type_for_group(records):
    """Whether a cluster's members were joined by an exact znacka match
    (deterministic) or only by title-embedding similarity (semantic)."""
    znacka_counts = {}
    for r in records:
        zn = core_znacka(r.get("znacka", ""))
        if zn:
            znacka_counts[zn] = znacka_counts.get(zn, 0) + 1
    if any(count > 1 for count in znacka_counts.values()):
        return "deterministic"
    if len(records) > 1:
        return "semantic"
    return "none"

class UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, x, y):
        rx, ry = self.find(x), self.find(y)
        if rx != ry:
            self.parent[rx] = ry

def _jurisdikce_known(jurisdikce):
    """"" and "neurčeno" both mean "we don't actually know" — neither
    should ever veto a match; only two DIFFERENT known jurisdictions
    should."""
    return bool(jurisdikce) and jurisdikce != "neurčeno"


def _jurisdikce_conflict(a, b):
    """True only when both sides have a known jurisdiction and it
    differs — e.g. a Slovak STN vs a Czech ČSN adoption of the same EN/ISO
    standard are legally distinct documents no matter how identical their
    reference number or title look (see doc/PLAN.md Step 1 follow-up #8).
    An unknown/unset jurisdiction on either side never blocks a match —
    it just means this source doesn't carry that information, not that
    there's a genuine conflict."""
    return _jurisdikce_known(a) and _jurisdikce_known(b) and a != b


def build_clusters(valid_data, similarity_threshold=0.85):
    """Groups records (each already carrying a pre-computed '_embedding')
    into clusters: a deterministic pass unions any records sharing a core
    znacka regardless of title similarity, then a semantic pass unions
    remaining pairs above similarity_threshold — vetoed when both records
    have different non-empty core znacka (two different reference numbers
    means two different documents, full stop, no matter how similar their
    titles score) OR a known jurisdiction conflict (see
    _jurisdikce_conflict). Returns a list of index-groups (each a list of
    indices into valid_data), not the records themselves — kept
    pure/deterministic and independent of the OpenAI/network calls that
    produce embeddings, so it's unit-testable with synthetic vectors.
    """
    n = len(valid_data)
    uf = UnionFind(n)

    znacka_of = [core_znacka(item.get("znacka", "")) for item in valid_data]
    jurisdikce_of = [item.get("jurisdikce", "") for item in valid_data]

    # Deterministic pass. A shared core znacka can span more than one
    # jurisdiction "island" (e.g. 3 Czech ČSN records + 2 Slovak STN
    # records, all citing the same EN number) — union each new record
    # with any EXISTING same-core record it doesn't conflict with
    # (Union-Find transitivity extends that to the whole compatible
    # island), never with one it does.
    core_to_indices = {}
    for i, core in enumerate(znacka_of):
        if not core:
            continue
        bucket = core_to_indices.setdefault(core, [])
        compatible = next((j for j in bucket if not _jurisdikce_conflict(jurisdikce_of[i], jurisdikce_of[j])), None)
        if compatible is not None:
            uf.union(i, compatible)
        bucket.append(i)

    for i in range(n):
        for j in range(i + 1, n):
            if uf.find(i) == uf.find(j):
                continue
            if znacka_of[i] and znacka_of[j] and znacka_of[i] != znacka_of[j]:
                continue
            if _jurisdikce_conflict(jurisdikce_of[i], jurisdikce_of[j]):
                continue
            sim = cosine_similarity(valid_data[i]["_embedding"], valid_data[j]["_embedding"])
            if sim > similarity_threshold:
                uf.union(i, j)

    groups = {}
    for i in range(n):
        root = uf.find(i)
        groups.setdefault(root, []).append(i)
    return list(groups.values())

def digit_core(znacka):
    """The bare numeric/part-number core of a znacka, e.g. '14687' or
    '19880-1' from 'ČSN EN ISO 19880-1' — used only to group candidate
    ISO/ČSN designation variants for the registry check below, never for
    merge decisions elsewhere (it's deliberately looser than core_znacka)."""
    return " ".join(re.findall(r"\d[\d./-]*\d|\d+", znacka or ""))

def find_iso_csn_ambiguous_groups(final_dataset):
    """Finds groups of final records that share a digit_core but differ in
    core_znacka and mention 'ISO' — the exact shape of the 'ISO X' /
    'ČSN ISO X' / 'ČSN EN ISO X' ambiguity that only the ČSN registry (not
    our own title text) can resolve: which national-adoption form is
    actually currently valid. Returns {digit_core: [indices into
    final_dataset]}.

    CRITICAL: only ever groups records with a CZ or unknown jurisdikce
    ("", "CZ", "neurčeno") — this function's whole point is finding the
    Czech ČSN designation for what's presumed-CZ ambiguity (e.g. Prokop's
    own bare "ISO X" vs "ČSN EN ISO X" rows). A record with a KNOWN
    non-CZ jurisdikce (SK, DE, US, EU, mezinárodní, ...) is EXCLUDED
    entirely, never a candidate to merge here — a Slovak STN or German
    norm is a legally distinct document from a Czech ČSN even when the
    registry confirms a matching CZ standard exists (see
    check_foreign_norm_csn_equivalents.py, which handles that case
    correctly, as a cross-reference *report*, never a merge). Silently
    merging a foreign record in here and relabelling it with a "ČSN ..."
    znacka would be exactly the conflation this whole field exists to
    prevent — this was a real bug, found and fixed 2026-09-09 (see
    doc/PLAN.md Step 1 follow-up #9)."""
    by_core = {}
    for idx, r in enumerate(final_dataset):
        zn = r.get("znacka", "").strip()
        if not zn or "iso" not in zn.lower():
            continue
        if _jurisdikce_known(r.get("jurisdikce", "")) and r.get("jurisdikce") != "CZ":
            continue
        core = digit_core(zn)
        if core:
            by_core.setdefault(core, []).append(idx)

    return {
        core: idxs for core, idxs in by_core.items()
        if len(idxs) > 1
        and len({core_znacka(final_dataset[i]["znacka"]) for i in idxs}) > 1
    }

def resolve_iso_csn_ambiguity(final_dataset, csn_search=None):
    """Best-effort: for each ambiguous ISO/ČSN group, asks the ČSN online
    registry (see check_csn_validity.py) which national-adoption form is
    actually currently valid, and merges the group under that confirmed
    designation. Never blocks or fails the pipeline: a lookup error, no
    match, or more than one currently-valid designation (contradicting the
    assumption that only one can be valid at a time) just leaves the group
    untouched with a logged note for a human to look at — no blind merge
    without a clear, single, confirmed answer.

    csn_search is injectable as `query -> [{"designation", "is_valid", ...}]`
    for testing; defaults to a real (rate-limited, single-session) lookup
    against csnonline.agentura-cas.cz.

    Returns (final_dataset, log_entries) — does not mutate its argument.
    """
    if csn_search is None:
        import requests
        from check_csn_validity import search as _search, USER_AGENT

        session = requests.Session()
        session.headers.update({"User-Agent": USER_AGENT})
        csn_search = lambda query: _search(session, query)

    ambiguous = find_iso_csn_ambiguous_groups(final_dataset)
    log_entries = []
    if not ambiguous:
        return final_dataset, log_entries

    indices_to_remove = set()
    additions = []

    for core, idxs in ambiguous.items():
        records = [final_dataset[i] for i in idxs]
        summary = [{"znacka": r.get("znacka", ""), "nazev_cz": r.get("nazev_cz", "")} for r in records]
        query = f"ISO {core}"

        try:
            results = csn_search(query)
        except Exception as e:
            log_entries.append({
                "digit_core": core, "query": query, "action": "csn_lookup_failed",
                "error": str(e), "records": summary,
            })
            continue

        valid_designations = {r["designation"].strip() for r in results if r.get("is_valid") and r.get("designation")}
        if len(valid_designations) != 1:
            log_entries.append({
                "digit_core": core, "query": query, "action": "csn_lookup_inconclusive",
                "valid_designations_found": sorted(valid_designations), "records": summary,
            })
            continue

        canonical = next(iter(valid_designations))
        merged = programmatic_merge(records)
        merged["znacka"] = canonical
        additions.append(merged)
        indices_to_remove.update(idxs)
        log_entries.append({
            "digit_core": core, "query": query, "action": "merged_by_csn_registry",
            "canonical_znacka": canonical, "records": summary,
        })

    if indices_to_remove:
        final_dataset = [r for i, r in enumerate(final_dataset) if i not in indices_to_remove] + additions

    return final_dataset, log_entries

def main():
    input_file = REPO_ROOT / "data" / "database_merged_raw.json"
    output_file = REPO_ROOT / "data" / "database_merged_deduplicated.json"
    audit_log_file = REPO_ROOT / "data" / "dedup_audit_log.jsonl"
    review_queue_file = REPO_ROOT / "data" / "dedup_review_queue.json"
    similarity_report_file = REPO_ROOT / "doc" / "similarity_analysis.md"

    if not input_file.exists():
        logging.error(f"Vstupní soubor neexistuje: {input_file}")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    logging.info(f"Načteno {len(data)} záznamů z {input_file}")

    # 1. Získání textů k vektorizaci (použijeme název)
    # Vyfiltrujeme záznamy bez názvu
    valid_data = []
    for item in data:
        nazev = item.get("nazev_cz", "").strip()
        if not nazev:
            nazev = item.get("nazev_sk", "").strip()
            if not nazev:
                nazev = item.get("nazev_eu", "").strip()

        item["_search_text"] = nazev
        if nazev:
            valid_data.append(item)
        else:
            # Záznamy bez jakéhokoliv jména si necháme jen tak stranou (nepravděpodobné)
            logging.warning(f"Záznam bez názvu vynechán z deduplikace: {item}")

    logging.info(f"Příprava na vektorizaci {len(valid_data)} záznamů...")

    # Získání vektorů v dávkách
    batch_size = 100
    for i in range(0, len(valid_data), batch_size):
        batch = valid_data[i:i+batch_size]
        texts = [x["_search_text"] for x in batch]

        response = client.embeddings.create(
            input=texts,
            model="text-embedding-3-small"
        )

        for j, embedding_data in enumerate(response.data):
            batch[j]["_embedding"] = embedding_data.embedding

    logging.info("Vektorizace (Embeddings) dokončena.")

    # 2. Shlukování (Clustering): deterministický průchod přes shodnou
    # znacku, sloučený se sémantickým shlukováním podle podobnosti
    # embeddingů — shoda ZNACKY spojí záznamy do shluku bez ohledu na to,
    # co říká cosine similarity; různá ZNACKA naopak sloučení vetuje bez
    # ohledu na podobnost názvu (viz build_clusters).
    clusters = build_clusters(valid_data, similarity_threshold=0.85)

    logging.info(f"Vytvořeno {len(clusters)} shluků unikátních dokumentů.")

    # 3. Odstranění pomocných klíčů a deduplikace pomocí LLM
    final_dataset = []
    audit_log = []
    review_queue = []

    for idx, index_group in enumerate(clusters):
        cluster = [valid_data[i] for i in index_group]

        # Odstranit '_search_text' a '_embedding' před odesláním do LLM / uložením
        clean_cluster = []
        for item in cluster:
            item_copy = dict(item)
            item_copy.pop("_search_text", None)
            item_copy.pop("_embedding", None)
            clean_cluster.append(item_copy)

        match_type = match_type_for_group(clean_cluster)
        cluster_summary = [{"nazev_cz": r.get("nazev_cz", ""), "znacka": r.get("znacka", "")} for r in clean_cluster]

        if len(clean_cluster) == 1:
            # Žádná duplicita
            final_dataset.append(clean_cluster[0])
            audit_log.append({
                "cluster_id": idx, "records": cluster_summary, "match_type": match_type,
                "action": "kept_separate", "timestamp": datetime.datetime.now().isoformat()
            })
        elif is_pure_znacka_cluster(clean_cluster):
            # Každý záznam ve shluku má stejnou (jádrovou) značku — jde
            # nepochybně o týž dokument, žádné rozhodování o identitě není
            # potřeba, sloučíme deterministicky bez volání LLM.
            logging.info(f"--- Shluk {idx+1} ({len(clean_cluster)} prvků, match_type={match_type}) — programové sloučení (čistá shoda značky) ---")
            final_dataset.append(programmatic_merge(clean_cluster))
            audit_log.append({
                "cluster_id": idx, "records": cluster_summary, "match_type": match_type,
                "action": "merged", "merge_method": "programmatic",
                "timestamp": datetime.datetime.now().isoformat()
            })
        else:
            # Potenciální duplicita -> vyřeší LLM
            logging.info(f"--- Zpracovávám shluk {idx+1} ({len(clean_cluster)} prvků, match_type={match_type}) ---")
            merged, error = deduplicate_cluster_with_llm(clean_cluster)

            if merged is None:
                # Nikdy nezahazovat data beze stopy — ponecháme nesloučené,
                # ale označíme k ručnímu přezkoumání.
                for r in clean_cluster:
                    r["_dedup_status"] = "flagged_for_review"
                final_dataset.extend(clean_cluster)
                review_queue.append({
                    "cluster_id": idx, "records": clean_cluster, "error": error
                })
                audit_log.append({
                    "cluster_id": idx, "records": cluster_summary, "match_type": match_type,
                    "action": "flagged_for_review", "error": error,
                    "timestamp": datetime.datetime.now().isoformat()
                })
            else:
                final_dataset.extend(merged)
                audit_log.append({
                    "cluster_id": idx, "records": cluster_summary, "match_type": match_type,
                    "action": "merged", "merge_method": "llm",
                    "timestamp": datetime.datetime.now().isoformat()
                })

    # 4. Vyřešení nejednoznačných ISO/ČSN variant proti registru ČSN online
    # (best-effort — chyba sítě nebo nejednoznačný výsledek nikdy nezastaví
    # zbytek pipeline, jen se zaloguje k ručnímu přezkoumání).
    logging.info("Ověřuji nejednoznačné ISO/ČSN varianty proti registru ČSN online...")
    try:
        final_dataset, csn_log_entries = resolve_iso_csn_ambiguity(final_dataset)
        for entry in csn_log_entries:
            entry["timestamp"] = datetime.datetime.now().isoformat()
            audit_log.append(entry)
        n_merged = sum(1 for e in csn_log_entries if e["action"] == "merged_by_csn_registry")
        n_other = len(csn_log_entries) - n_merged
        if csn_log_entries:
            logging.info(f"Registr ČSN online: {n_merged} skupin(a) sloučeno, {n_other} ponecháno k přezkoumání.")
    except Exception as e:
        logging.warning(f"Ověření proti registru ČSN online selhalo, pokračuji bez něj: {e}")

    # 5. Uložení
    logging.info(f"Ukládám {len(final_dataset)} záznamů do {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final_dataset, f, ensure_ascii=False, indent=4)

    with open(audit_log_file, 'w', encoding='utf-8') as f:
        for entry in audit_log:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    with open(review_queue_file, 'w', encoding='utf-8') as f:
        json.dump(review_queue, f, ensure_ascii=False, indent=4)

    logging.info("Proces deduplikace úspěšně dokončen.")

    print("\n" + "=" * 70)
    print("Než budete výstup považovat za finální, zkontrolujte:")
    print(f"  - 'šedou zónu' (0.75-0.85) sémantické podobnosti: {similarity_report_file}")
    print(f"    (spusťte analyze_similarities.py, pokud soubor chybí nebo je zastaralý)")
    if review_queue:
        print(f"  - {len(review_queue)} shluk(y) označené k ručnímu přezkoumání: {review_queue_file}")
    print(f"  - kompletní audit log rozhodnutí: {audit_log_file}")
    print("=" * 70)

if __name__ == "__main__":
    main()
