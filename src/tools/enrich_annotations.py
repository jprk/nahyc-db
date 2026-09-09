import json
import os
import pathlib
import time
import sys
sys.stdout.reconfigure(encoding='utf-8')

from openai import OpenAI

BASE_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent

def get_api_key():
    key_path = REPO_ROOT / ".openapi_key"
    if not key_path.exists():
        raise FileNotFoundError("API key file .openapi_key not found.")
    with open(key_path, "r", encoding="utf-8") as f:
        return f.read().strip()

def enrich_annotations():
    # 1. Initialize OpenAI client
    api_key = get_api_key()
    client = OpenAI(api_key=api_key)

    # 2. Load the deduplicated database (supersedes the old, now-gone
    # databaze_komplet.json from the pre-reorg single-file pipeline)
    file_path = REPO_ROOT / "data" / "database_merged_deduplicated.json"
    if not file_path.exists():
        raise FileNotFoundError(f"Input file {file_path} not found.")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"Loaded {len(data)} records from {file_path}.")
    
    # Count how many we need to process
    to_process = [r for r in data if not r.get("anotace_poznamka", "").strip()]
    print(f"Found {len(to_process)} records missing an annotation.")

    # System prompt specifically engineered to generate concise professional descriptions
    system_prompt = """
Jsi právní a technologický expert v oblasti vodíkových technologií. Tvým úkolem je na základě názvu, typu dokumentu a případných dalších poskytnutých metadat sepsat krátkou, profesionální anotaci (1 až 3 věty) popisující, čeho se daný zákon, norma či směrnice týká v kontextu energetiky, techniky nebo dopravy (primárně s potenciálním vztahem k vodíku, plynárenství a obnovitelným zdrojům, pokud je to relevantní).

Pravidla:
- Pokud je to běžný zákon (např. zákon o odpadech, stavební zákon), popiš stručně jeho účel.
- Pokud je to technická norma (ČSN, EN, ISO), popiš stručně, jakou oblast obvykle reguluje.
- Zkus být neutrální, přesný a informativní. Není nutné si domýšlet složité detaily, pokud název napoví jen obecně.
- NEPIŠ zbytečné úvody jako "Tento zákon..." apod.
- NEHALUCINUJ nesmysly – drž se obecných a ověřených faktů o daném typu zákona nebo normy.

Očekávaný výstup je POUZE validní strukturovaný JSON:
{
  "anotace_poznamka": "zde bude vygenerovaný text anotace"
}
"""

    modified_count = 0

    for index, record in enumerate(data):
        current_annotation = record.get("anotace_poznamka", "").strip()
        
        if not current_annotation:
            title_cz = record.get("nazev_cz", "")
            title_sk = record.get("nazev_sk", "")
            title_eu = record.get("nazev_eu", "")
            doc_type = record.get("typ_dokumentu", "Neznámý typ")
            
            # Vybereme aspoň nějaký dostupný název pro LLM
            title = title_cz if title_cz else (title_eu if title_eu else title_sk)
            
            if not title:
                continue

            print(f"[{modified_count+1}/{len(to_process)}] Generuji anotaci pro: '{title}' ({doc_type})")
            
            user_prompt = f"Vygeneruj anotaci pro tento dokument:\nNázev: '{title}'\nTyp: '{doc_type}'"
            
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini", # Using mini to be faster and cheaper for simpler summarization tasks
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.3,
                    response_format={ "type": "json_object" },
                    timeout=10
                )
                
                result_json_str = response.choices[0].message.content
                parsed_result = json.loads(result_json_str)
                
                # Update the record object in memory
                new_annotation = parsed_result.get("anotace_poznamka", "").strip()
                if new_annotation:
                     record["anotace_poznamka"] = new_annotation
                     
                modified_count += 1
                
                # Simple rate limiting/saving progress every 20 records
                if modified_count % 20 == 0:
                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=4)
                    print(f"--- Průběžně uloženo {modified_count} anotací ---")
                
                time.sleep(0.5)
                
            except Exception as e:
                print(f"Error processing '{title}': {e}")

    # 4. Save final results to JSON
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
    print(f"Hotovo! Vygenerováno {modified_count} anotací a soubor {file_path} byl úspěšně aktualizován.")

if __name__ == "__main__":
    enrich_annotations()
