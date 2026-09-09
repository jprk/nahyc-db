import json
import os
import pathlib
import time

import pandas as pd
from openai import OpenAI

BASE_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent

def get_api_key():
    key_path = REPO_ROOT / ".openapi_key"
    if not key_path.exists():
        raise FileNotFoundError("API key file .openapi_key not found.")
    with open(key_path, "r", encoding="utf-8") as f:
        return f.read().strip()

def process_laws():
    # 1. Initialize OpenAI client
    api_key = get_api_key()
    client = OpenAI(api_key=api_key)

    # 2. Load the Excel File
    file_path = REPO_ROOT / "data" / "20250712_Sinay" / "20250927_sinay_zakony.xlsx"
    if not file_path.exists():
        raise FileNotFoundError(f"Input file {file_path} not found.")

    print(f"Loading data from {file_path}...")
    # Header is at row index 1 (0-indexed)
    df = pd.read_excel(file_path, header=1)
    
    # 3. Prepare the Output Array
    results = []

    total_rows = len(df)
    
    # System prompt specifically engineered to reduce hallucinations
    system_prompt = """
Jsi právní datový asistent. Tvým úkolem je najít k zadanému slovenskému zákonu jeho odpovídající, reálně existující ekvivalent platný v České republice (např. ze Sbírky zákonů ČR).
Dále musíš vyhledat příslušné URL odkazy směřující na veřejné právní systémy (slov-lex.sk pro SR a zakonyprolidi.cz nebo e-sbirka.cz pro ČR).
Nakonec identifikuj českého gestora nebo skupinu gestorů (např. ministerstev), kteří mají danou legislativu v gesci.

PRAVIDLA PRO ZABRÁNĚNÍ HALUCINACÍM (VELMI DŮLEŽITÉ):
1. Vracené české zákony MUSÍ SKUTEČNĚ EXISTOVAT ve Sbírce zákonů ČR. Nevymýšlej si čísla zákonů. Pokud neexistuje přímý ekvivalent v jednom zákoně, uveď ten nejrelevantnější nebo prázdný string.
2. Vracené URL odkazy MUSÍ BÝT FUNKČNÍ A PLATNÉ. Nekonstruuj URL adresy odhadem. Ve většině případů na zakonyprolidi.cz vypadá odkaz jako `https://www.zakonyprolidi.cz/cs/[rok]-[číslo]`. Nehádej formáty, pokud si nejsi absolutně jistý jejich konstrukcí.
3. Pokud pro dané pole skutečně nedokážeš s vysokou jistotou najít přesnou hodnotu nebo existuje pochybnost o validitě odkazu, VRAŤ PRÁZDNÝ ŘETĚZEC "" (nebo prázdné pole pro Gestor CZ).

Očekávaný výstup je STRICTNĚ korektní strukturovaný JSON (bez markdownu, bez dalšího textu) s následujícími klíči:
{
  "URL SK": "string",
  "Dokument CZ": "string",
  "URL CZ": "string",
  "Gestor CZ": ["string", "string"]
}
"""

    for index, row in df.iterrows():
        slovak_law = str(row.get('Dokument SK', '')).strip()
        if pd.isna(slovak_law) or not slovak_law or slovak_law.lower() == 'nan':
            continue
            
        print(f"Processing ({index+1}/{total_rows}): {slovak_law}")
        
        user_prompt = f"Zpracuj následující slovenský zákon a najdi jeho český ekvivalent: '{slovak_law}'"
        
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0, # Lowest temperature to reduce randomness and hallucinations
                response_format={ "type": "json_object" }
            )
            
            result_json_str = response.choices[0].message.content
            parsed_result = json.loads(result_json_str)
            
            record = {
                "Dokument SK": slovak_law,
                "URL SK": parsed_result.get("URL SK", ""),
                "Dokument CZ": parsed_result.get("Dokument CZ", ""),
                "URL CZ": parsed_result.get("URL CZ", ""),
                "Gestor CZ": parsed_result.get("Gestor CZ", [])
            }
            results.append(record)
            
            # Rate limiting / politeness
            time.sleep(1)
            
        except Exception as e:
            print(f"Error processing '{slovak_law}': {e}")
            # Still append an empty structure so we don't lose the Slovak law from the list
            results.append({
                "Dokument SK": slovak_law,
                "URL SK": "",
                "Dokument CZ": "",
                "URL CZ": "",
                "Gestor CZ": [],
                "Error": str(e)
            })

    # 4. Save results to JSON
    output_path = REPO_ROOT / "data" / "20250712_Sinay" / "sinay_zakony_processed.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
        
    print(f"Done! Processed {len(results)} laws and saved to {output_path}")

if __name__ == "__main__":
    process_laws()
