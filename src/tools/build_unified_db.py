import json
import pathlib
import re

BASE_DIR = pathlib.Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent.parent

def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

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

def build_unified_db():
    base_dir = REPO_ROOT / "data"

    file_prokop = base_dir / "20250303_Prokop" / "normy_vodik.json"
    file_sinay = base_dir / "20250712_Sinay" / "sinay_zakony_processed.json"
    file_haltuf = base_dir / "20250915_Haltuf" / "haltuf_combined.json"

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

            if not record["anotace_poznamka"]:
                prev = previous_annotations.get((record["zdroj_dat"], record["nazev_cz"]))
                if prev:
                    record["anotace_poznamka"] = prev
                    restored_count += 1

            unified_db.append(record)
        print(f"Loaded {len(data_haltuf)} records from Haltuf.")
    except Exception as e:
        print(f"Error loading Haltuf data: {e}")

    # 4. Save combined to JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(unified_db, f, ensure_ascii=False, indent=4)

    if previous_annotations:
        print(f"Restored {restored_count} annotation(s) from the previous {output_file.name} "
              f"(matched by zdroj_dat+nazev_cz) that this run's sources don't themselves provide.")
    print(f"Done. Unified database created with {len(unified_db)} total records at {output_file}")

if __name__ == "__main__":
    build_unified_db()
