# Adresář /data/20250915_Haltuf

Tento adresář obsahuje konsolidovaná data a kombinované exporty pro databázi předpisů z různých zdrojů.

## Zpracování dat (Pipeline)
Složitá víceúrovňová data ze zdrojového XLS se zpracovávají do finálního JSON souboru následujícím způsobem:

1. **Příprava vstupních dat:** V adresáři `raw/` je uložen původní dodaný Excel `2025-07-10_Databáze dokumentů H2.xlsx`. Ten byl kvůli složité vizuální struktuře upraven a přeuložen jako čistší verze `20250915_haltuf_legislativa.xlsx` přímo zde v kořeni tohoto adresáře.
2. **Extrakce do CSV (Dočasné adresáře):** Na pracovní `.xlsx` je zavolán skript `tools/extract_tables.py`, který z něj vytáhne a rozdělí jednotlivé datové bloky do mnoha drobných CSV souborů (`*_processed.csv`). Tyto exporty se typicky zkoušely a ukládaly do dočasných ladicích adresářů (např. `v1/`, `v2/`, atd.), které jsou verzovacím systémem Git záměrně ignorovány.
3. **Sloučení do JSON:** Na hotové sady CSV souborů (extrahované do hlavního adresáře) se zavolá skript `tools/process_haltuf.py`. Tento skript projde všechny platné `*_processed.csv` soubory, sjednotí jejich hlavičky a vygeneruje finální zkonsolidovaný soubor `haltuf_combined.json`, který se dál používá jako primární vstupní surovina pro celkovou databázi.
