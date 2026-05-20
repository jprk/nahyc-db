# Adresář /tools

Tento adresář sdružuje rozličné pomocné a analytické Python skripty určené například pro analýzu Excel tabulek, parsování dat, obohacování a celkovou přípravu podkladů pro databázi.

## Přehled skriptů
* `analyze_*.py` (`headers`, `legenda`, `sheets`, `xlsx`, `xlsx2`) - Sada průzkumných skriptů pro čtení a analýzu struktury původních Excelových tabulek dodaných partnery.
* `build_unified_db.py` - Slouží k sestavení jedné sjednocené databáze (`databaze_komplet.json`) z různých dílčích zdrojů dat (Prokop, Sinay, Haltuf).
* `enrich_eu_laws.py`, `process_laws.py` - Skripty využívající OpenAI API pro obohacení legislativních dat, mapování vazeb mezi EU a CZ zákony a doplňování metadat.
* `enrich_annotations.py` - Skript využívající OpenAI API k hromadnému dogenerování chybějících odborných anotací ke všem záznamům ve sjednocené databázi (`databaze_komplet.json`).
* `parse_norms.py` - Skript pro vyparsování a extrakci technických norem z Markdown souborů do strukturovaného formátu JSON.
* `process_haltuf.py` - Skript, který zpracovává jednotlivé CSV soubory (z analýz pana Haltufa) a konsoliduje je do JSON formátu.
* `search_agent.py` - Pomocný skript napojený na vyhledávač DuckDuckGo a LLM k automatizovanému vyhledávání informací na webu.
* `check_db.py` - Jednoduchý diagnostický skript k lokálnímu dotazování a ověření obsahu aktuální SQLite databáze.
* `init_db.py` - Slouží k inicializaci a nahrání dat do SQLite databáze `regulatory_documents.db` uložené v adresáři `/db`.
* `create_xmi.py` - Vytváří XMI soubor pro import struktury databáze do nástroje Enterprise Architect (ukládá do `/db`).
* `plantuml_draw.py` - Skript pro vygenerování diagramu z PlantUML definice struktury databáze.
* `read_docx.py` - Pomocný skript pro extrakci textu z .docx souborů.
* `extract_tables.py` - Skript pro extrakci jednotlivých tabulek z komplexních vícestránkových XLSX souborů do samostatných CSV.
