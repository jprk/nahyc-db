import json
import pathlib

def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def build_unified_db():
    base_dir = pathlib.Path("Data")
    
    file_prokop = base_dir / "20250303_Prokop" / "normy_vodik.json"
    file_sinay = base_dir / "20250712_Sinay" / "sinay_zakony_processed.json"
    file_haltuf = base_dir / "20250915_Haltuf" / "haltuf_combined.json"
    
    output_file = base_dir / "databaze_komplet.json"

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

            record = {
                "zdroj_dat": "Prokop_Normy",
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
                "anotace_poznamka": item.get("Anotace", "").strip()
            }
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
                "znacka": "",
                "typ_dokumentu": "Zákon",
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
                "anotace_poznamka": ""
            }
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

            record = {
                "zdroj_dat": "Haltuf_Dokumenty",
                "nazev_cz": item.get("Název dokumentu", "").strip(),
                "znacka": "",
                "typ_dokumentu": item.get("Typ_ID", "").strip(),
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
                "anotace_poznamka": item.get("Poznámka", "").strip()
            }
            # Attempt to map EUR-lex links to odkaz_eu heuristically
            if "eur-lex.europa.eu" in record["odkaz_hlavni"]:
                 record["odkaz_eu"] = record["odkaz_hlavni"]
                 
            unified_db.append(record)
        print(f"Loaded {len(data_haltuf)} records from Haltuf.")
    except Exception as e:
        print(f"Error loading Haltuf data: {e}")

    # 4. Save combined to JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(unified_db, f, ensure_ascii=False, indent=4)
        
    print(f"Done. Unified database created with {len(unified_db)} total records at {output_file}")

if __name__ == "__main__":
    build_unified_db()
