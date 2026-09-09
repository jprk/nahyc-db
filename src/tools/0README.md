# Adresář /tools

Tento adresář sdružuje rozličné pomocné a analytické Python skripty určené například pro analýzu Excel tabulek, parsování dat, obohacování a celkovou přípravu podkladů pro databázi.

## Přehled skriptů
* `analyze_*.py` (`headers`, `legenda`, `sheets`, `xlsx`, `xlsx2`) - Sada průzkumných skriptů pro čtení a analýzu struktury původních Excelových tabulek dodaných partnery.
* `build_unified_db.py` - Slouží k sestavení jedné sjednocené databáze (`data/database_merged_raw.json`) z různých dílčích zdrojů dat (Prokop, Sinay, Haltuf), bez deduplikace. Pro zdroje Haltuf a Sinay (které nikdy nevyplňují `znacka`) extrahuje referenční číslo přímo z názvu dokumentu — `extract_znacka_from_title()` (Haltuf 166/179, Sinay 46/48 pokryto; nepokryty zůstávají RID přílohy a pár záznamů bez referenčního čísla v názvu). Při opakovaném spuštění zachovává již vygenerované anotace (`anotace_poznamka`) z předchozího běhu, pokud je aktuální zdroj sám neposkytuje.
* `deduplicate_db.py` - Shlukuje záznamy `database_merged_raw.json` podle shodné značky (`znacka`, deterministicky) i podobnosti titulních embeddingů (práh 0.85, sémanticky) a pomocí GPT-4o-mini slučuje duplicity do `data/database_merged_deduplicated.json`. Neslučitelné/sporné shluky zapisuje do `data/dedup_review_queue.json` místo tichého průchodu; každé rozhodnutí loguje do `data/dedup_audit_log.jsonl`.
* `analyze_similarities.py` - Diagnostický skript, který vypisuje páry záznamů v "šedé zóně" podobnosti (0.75–0.85) do `doc/similarity_analysis.md` k ručnímu přezkoumání před finalizací deduplikace. Páry s prokazatelně odlišnou značkou (`znacka`) vylučuje jako falešně pozitivní.
* `enrich_eu_laws.py`, `process_laws.py` - Skripty využívající OpenAI API pro obohacení legislativních dat, mapování vazeb mezi EU a CZ zákony a doplňování metadat.
* `enrich_annotations.py` - Skript využívající OpenAI API k hromadnému dogenerování chybějících odborných anotací ke všem záznamům v `data/database_merged_deduplicated.json` (dřívější cíl `databaze_komplet.json` už v repozitáři neexistuje, nahrazen touto sjednocenou/deduplikovanou databází).
* `parse_norms.py` - Skript pro vyparsování a extrakci technických norem z Markdown souborů do strukturovaného formátu JSON.
* `process_haltuf.py` - Skript, který zpracovává jednotlivé CSV soubory (z analýz pana Haltufa) a konsoliduje je do JSON formátu.
* `search_agent.py` - Pomocný skript napojený na vyhledávač DuckDuckGo a LLM k automatizovanému vyhledávání informací na webu.
* `provision_db.py` - Jednorázově založí MariaDB databázi `h2regdocs` a aplikuje na ni `doc/konsolidace/V01-baseline-schema.sql` + `Konsolidace-DB-schema.sql`. Přihlašovací údaje bere z kořenového `.env`.
* `init_db.py` - Nahraje data z `data/database_merged_deduplicated.json` do MariaDB databáze `h2regdocs` (tabulky `Document`, `DocumentType`, `DocumentSource`, `Keyword`, `DocumentKeyword`) — před spuštěním vyžaduje již provedené `provision_db.py`. Před importem vyprázdní tyto tabulky.
* `check_db.py` - Jednoduchý diagnostický skript k dotazování a ověření obsahu MariaDB databáze `h2regdocs`.
* `create_xmi.py` - Vytváří XMI soubor pro import struktury databáze do nástroje Enterprise Architect (ukládá do `/db`).
* `plantuml_draw.py` - Skript pro vygenerování diagramu z PlantUML definice struktury databáze.
* `read_docx.py` - Pomocný skript pro extrakci textu z .docx souborů.
* `extract_tables.py` - Skript pro extrakci jednotlivých tabulek z komplexních vícestránkových XLSX souborů do samostatných CSV.
