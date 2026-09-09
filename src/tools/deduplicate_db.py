import os
import json
import logging
import datetime
import pathlib
import math
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

def normalize_znacka(znacka):
    """Normalizes a znacka (reference number) for exact-match comparison."""
    if not znacka:
        return ""
    return " ".join(str(znacka).split()).strip().lower()

def core_znacka(znacka):
    """Strips the optional Czech national-adoption prefix ('ČSN') so that
    'ČSN EN 17127' and 'EN 17127' compare as the same underlying standard —
    used for clustering, NOT for validate_merge's exact-membership check."""
    zn = normalize_znacka(znacka)
    if zn.startswith("čsn "):
        zn = zn[len("čsn "):]
    return zn

def validate_merge(cluster_records, merged_records):
    """Rejects a merge that invents a znacka not present in the input cluster
    (the one deterministic signal we can check without a source document)."""
    input_znacka = {normalize_znacka(r.get("znacka", "")) for r in cluster_records}
    input_znacka.discard("")
    for r in merged_records:
        zn = normalize_znacka(r.get("znacka", ""))
        if zn and zn not in input_znacka:
            return False, zn
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
'''

    last_error = None
    for attempt in range(1, MAX_LLM_ATTEMPTS + 1):
        try:
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                response_format={ "type": "json_object" },
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps({"records": cluster_records}, ensure_ascii=False)}
                ],
                temperature=0.0
            )

            result_content = completion.choices[0].message.content
            result_json = json.loads(result_content)

            # Očekáváme JSON ve formátu {"records": [ ... ]} nebo jen pole
            merged_records = result_json.get("records", [])
            if not merged_records and isinstance(result_json, list):
                merged_records = result_json

            valid, bad_znacka = validate_merge(cluster_records, merged_records)
            if not valid:
                last_error = f"LLM vrátilo neexistující značku '{bad_znacka}', která není v žádném vstupním záznamu."
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
    # embeddingů, přes společnou Union-Find strukturu — shoda ZNACKY
    # spojí záznamy do shluku bez ohledu na to, co říká cosine similarity.
    n = len(valid_data)
    uf = UnionFind(n)
    similarity_threshold = 0.85

    logging.info("Zahajuji deterministický průchod podle značky (znacka)...")
    znacka_index = {}
    for i, item in enumerate(valid_data):
        zn = core_znacka(item.get("znacka", ""))
        if zn:
            if zn in znacka_index:
                uf.union(i, znacka_index[zn])
            else:
                znacka_index[zn] = i

    logging.info(f"Zahajuji sémantické shlukování s prahem podobnosti {similarity_threshold}...")
    znacka_normalized = [core_znacka(item.get("znacka", "")) for item in valid_data]
    for i in range(n):
        for j in range(i + 1, n):
            if uf.find(i) == uf.find(j):
                continue
            # Two different, non-empty reference numbers mean two different
            # documents, full stop — no title similarity can override that
            # (e.g. multi-part standards like "ČSN EN 62282-3-300" vs
            # "...-3-200" score above the semantic threshold on title alone).
            if znacka_normalized[i] and znacka_normalized[j] and znacka_normalized[i] != znacka_normalized[j]:
                continue
            sim = cosine_similarity(valid_data[i]["_embedding"], valid_data[j]["_embedding"])
            if sim > similarity_threshold:
                uf.union(i, j)

    groups = {}
    for i in range(n):
        root = uf.find(i)
        groups.setdefault(root, []).append(i)
    clusters = list(groups.values())

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
                    "action": "merged", "timestamp": datetime.datetime.now().isoformat()
                })

    # 4. Uložení
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
