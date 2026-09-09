import csv
import glob
import json
import os
import pathlib

BASE_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent

def process_haltuf_csvs():
    input_dir = REPO_ROOT / "data" / "20250915_Haltuf"
    output_path = input_dir / "haltuf_combined.json"
    
    # 1. Fetch all *_processed.csv files
    target_files = glob.glob(str(input_dir / "*_processed.csv"))
    print(f"Found {len(target_files)} target files.")
    
    if not target_files:
        print("No files to process.")
        return

    # 2. Extract global column headers
    global_headers = set()
    for fp in target_files:
        with open(fp, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter=';')
            try:
                headers = next(reader)
                # Clean up BOM or surrounding whitespaces which might be present
                headers = [h.strip().replace('\ufeff', '') for h in headers if h.strip()]
                global_headers.update(headers)
            except StopIteration:
                 # Empty file
                 continue
    
    # Discard 'Typ dokumentu' from global_headers as we rename it to 'Typ_ID'
    if 'Typ dokumentu' in global_headers:
        global_headers.remove('Typ dokumentu')

    print(f"Extracted {len(global_headers)} unique global headers.")
    
    # 3 & 4. Parse files, extract metadata, format entries
    combined_data = []

    for fp in target_files:
        filename = os.path.basename(fp)
        
        # Expected pattern: A - výroba_EU_processed.csv -> section: "A - výroba", doc_type: "EU"
        base_name = filename.replace("_processed.csv", "")
        if "_" in base_name:
             parts = base_name.rsplit("_", 1)
             section = parts[0].strip()
             document_group = parts[1].strip()
        else:
             section = base_name.strip()
             document_group = "Unknown"
             
        with open(fp, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter=';')
            try:
                 headers = next(reader)
                 headers = [h.strip().replace('\ufeff', '') for h in headers]
            except StopIteration:
                 continue
                 
            dict_reader = csv.DictReader(f, fieldnames=headers, delimiter=';')
            
            for row in dict_reader:
                 if not any(row.values()):
                      continue
                 
                 entry = {}
                 # (a) Sekce
                 entry["Sekce"] = section
                 # (b) Třída
                 entry["Třída"] = document_group
                 # (c) Typ_ID from 'Typ dokumentu'
                 typ_id_val = row.get("Typ dokumentu", "")
                 if typ_id_val is None:
                     typ_id_val = ""
                 entry["Typ_ID"] = typ_id_val.strip()
                 
                 # (d) Copy the rest of the columns
                 for header in global_headers:
                      val = row.get(header, "")
                      if val is None:
                           val = ""
                      entry[header] = val.strip()
                      
                 combined_data.append(entry)
                 
    # 5. Output compilation to JSON
    with open(output_path, "w", encoding="utf-8") as f:
         json.dump(combined_data, f, ensure_ascii=False, indent=4)
         
    print(f"Finished processing. Extracted {len(combined_data)} total entries.")
    print(f"File saved to {output_path}")

if __name__ == "__main__":
    process_haltuf_csvs()
