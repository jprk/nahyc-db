import json
import os
import pathlib
import time

from openai import OpenAI

def get_api_key():
    key_path = pathlib.Path(".openapi_key")
    if not key_path.exists():
        raise FileNotFoundError("API key file .openapi_key not found.")
    with open(key_path, "r", encoding="utf-8") as f:
        return f.read().strip()

def process_eu_laws():
    # 1. Initialize OpenAI client
    api_key = get_api_key()
    client = OpenAI(api_key=api_key)

    # 2. Load the previously generated JSON File
    file_path = pathlib.Path("Data/20250712_Sinay/sinay_zakony_processed.json")
    if not file_path.exists():
        raise FileNotFoundError(f"Input file {file_path} not found.")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"Loaded {len(data)} records from {file_path}.")
    
    # System prompt specifically engineered to reduce hallucinations and target EU docs
    system_prompt = """
Jsi právní datový analytik. Tvým úkolem je analyzovat legislativní název (obvykle slovenský text odkazující na EU dokument) a:
1. Identifikovat přesný oficiální název příslušné Směrnice nebo Nařízení EU (z EUR-Lexu) a vrátit jej jako `Dokument EU`.
2. Poskytnout spolehlivé URL na EUR-Lex (např. https://eur-lex.europa.eu/eli/...) a vrátit jej jako `URL EU`.
3. Pokud se jedná o směrnici, najdi její aktuální a validní transpozici do českého práva (oficiální název zákona ve Sbírce zákonů) a ulož do `Dokument CZ`.
4. Pokud je `Dokument CZ` nalezen, vlož jeho platné URL na zakonyprolidi.cz do `URL CZ`. Pokud jde o přímo použitelné nařízení EU (nařízení Komise/EP a Rady atd.), uveď jako `Dokument CZ` oficiální český název daného evropského nařízení a do `URL CZ` dej stejný odkaz z nařízení na EUR-Lex (v češtině, lang=CS).
5. Pokus se odvodit českého gestora pro tuto oblast (seznam řetězců jako ["Ministerstvo životního prostředí"]) do `Gestor CZ`.

PŘÍSNÁ PRAVIDLA:
- NEHALUCINUJ. Vracej URL adresy pouze, pokud odpovídají standardnímu formátu a jsi si naprosto jistý dokumentem. 
- Pokud nevíš, nenech se zmást a vrať prázdný řetězec "" pro daný klíč.

Očekávaný validní JSON formát:
{
  "Dokument EU": "string",
  "URL EU": "string",
  "Dokument CZ": "string",
  "URL CZ": "string",
  "Gestor CZ": ["string"]
}
"""

    modified_count = 0

    for index, record in enumerate(data):
        slovak_law = record.get("Dokument SK", "").strip()
        cz_law = record.get("Dokument CZ", "").strip()
        
        # We only want to process records that failed to map to a CZ law previously
        if not cz_law and slovak_law:
            print(f"[{index+1}/{len(data)}] Analyzing for EU missing element: '{slovak_law}'")
            
            user_prompt = f"Analyzuj následující záznam a doplň EU a CZ informace: '{slovak_law}'"
            
            try:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.0,
                    response_format={ "type": "json_object" }
                )
                
                result_json_str = response.choices[0].message.content
                parsed_result = json.loads(result_json_str)
                
                # Update the record object in memory
                record["Dokument EU"] = parsed_result.get("Dokument EU", "")
                record["URL EU"] = parsed_result.get("URL EU", "")
                
                # If we found a previously missing Czech rep equivalent through the EU routing, inject it
                new_cz = parsed_result.get("Dokument CZ", "")
                if new_cz:
                     record["Dokument CZ"] = new_cz
                     
                new_cz_url = parsed_result.get("URL CZ", "")
                if new_cz_url:
                     record["URL CZ"] = new_cz_url
                     
                new_gestor = parsed_result.get("Gestor CZ", [])
                if new_gestor and not record.get("Gestor CZ"):
                     record["Gestor CZ"] = new_gestor
                     
                modified_count += 1
                time.sleep(1) # Be polite to the API
                
            except Exception as e:
                print(f"Error processing '{slovak_law}': {e}")
                record["Dokument EU"] = ""
                record["URL EU"] = ""

    # Ensure empty fields exist even for properties that didn't go through the parser
    for record in data:
       if "Dokument EU" not in record:
           record["Dokument EU"] = ""
       if "URL EU" not in record:
           record["URL EU"] = ""

    # 4. Save results to JSON
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
    print(f"Done! Modified {modified_count} records and saved to {file_path}")

if __name__ == "__main__":
    process_eu_laws()
