import os
import json
import pathlib
import math
from openai import OpenAI

BASE_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent
API_KEY_PATH = ".openapi_key"

try:
    with open(REPO_ROOT / API_KEY_PATH, 'r', encoding='utf-8') as f:
        api_key = f.read().strip()
    os.environ['OPENAI_API_KEY'] = api_key
    client = OpenAI()
except FileNotFoundError:
    print(f"Soubor s API klíčem nebyl nalezen: {API_KEY_PATH}")
    exit(1)

def cosine_similarity(v1, v2):
    dot_product = sum(a * b for a, b in zip(v1, v2))
    magnitude1 = math.sqrt(sum(a * a for a in v1))
    magnitude2 = math.sqrt(sum(b * b for b in v2))
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    return dot_product / (magnitude1 * magnitude2)

def core_znacka(znacka):
    """Mirrors deduplicate_db.py's core_znacka (duplicated, not imported,
    to avoid triggering that module's own API-key/logging setup on
    import): normalizes a znacka and strips the optional Czech
    national-adoption 'ČSN' prefix, so 'ČSN EN 17127' and 'EN 17127'
    compare as the same underlying standard."""
    if not znacka:
        return ""
    zn = " ".join(str(znacka).split()).strip().lower()
    if zn.startswith("čsn "):
        zn = zn[len("čsn "):]
    return zn

def main():
    input_file = REPO_ROOT / "data" / "database_merged_raw.json"
    output_md = REPO_ROOT / "doc" / "similarity_analysis.md"

    if not input_file.exists():
        print(f"Vstupní soubor neexistuje: {input_file}")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    print(f"Načteno {len(data)} záznamů z {input_file}")

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

    print(f"Příprava na vektorizaci {len(valid_data)} záznamů...")

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

    print("Vektorizace dokončena. Počítám podobnosti...")

    znacka_of = [core_znacka(item.get("znacka", "")) for item in valid_data]

    results = []
    excluded_diff_znacka = 0
    # Avoid calculating duplicates (i, j) and (j, i)
    for i in range(len(valid_data)):
        for j in range(i + 1, len(valid_data)):
            sim = cosine_similarity(valid_data[i]["_embedding"], valid_data[j]["_embedding"])
            # The user asked for similarity between 0.75 and 0.85
            if 0.75 <= sim < 0.85:
                # Two different, non-empty reference numbers mean two
                # different documents regardless of title similarity (same
                # rule as deduplicate_db.py's merge veto) — excluding these
                # keeps this report to genuine candidates instead of norms
                # that just happen to share domain vocabulary.
                if znacka_of[i] and znacka_of[j] and znacka_of[i] != znacka_of[j]:
                    excluded_diff_znacka += 1
                    continue
                # Store titles and the source for clarity
                title1 = valid_data[i]["_search_text"].replace('\n', ' ')
                source1 = valid_data[i].get("zdroj_dat", "")
                title2 = valid_data[j]["_search_text"].replace('\n', ' ')
                source2 = valid_data[j].get("zdroj_dat", "")
                results.append((sim, f"{title1} ({source1})", f"{title2} ({source2})"))

    print(f"Nalezeno {len(results)} párů v požadovaném rozsahu "
          f"({excluded_diff_znacka} dalších vyloučeno pro prokazatelně odlišnou značku).")

    # Seřadit sestupně podle podobnosti
    results.sort(key=lambda x: x[0], reverse=True)

    # Vygenerovat Markdown
    with open(output_md, 'w', encoding='utf-8') as f:
        f.write("# Přehled dokumentů s podobností 0.75 až 0.85\n\n")
        f.write("Následující tabulka obsahuje páry dokumentů, které mají sémantickou podobnost (Cosine Similarity) v rozmezí 0.75 až 0.85. Jsou seřazeny sestupně.\n\n")
        f.write(f"Páry, kde oba záznamy mají vyplněnou, ale vzájemně odlišnou značku "
                f"(tedy prokazatelně odlišné dokumenty), jsou z tohoto přehledu vyloučeny "
                f"({excluded_diff_znacka} vyloučeno).\n\n")
        f.write("| Podobnost | Dokument 1 | Dokument 2 |\n")
        f.write("| :---: | :--- | :--- |\n")
        for sim, doc1, doc2 in results:
            f.write(f"| {sim:.4f} | {doc1} | {doc2} |\n")

    print(f"Hotovo. Výsledek uložen do {output_md}")

if __name__ == "__main__":
    main()
