# Adresář /data/20250712_Sinay

Tento adresář obsahuje zdrojová data a podklady týkající se zákonů a legislativních předpisů ve zpracované i nezpracované podobě.

## Zpracování zákonů (Pipeline)
1. **Příprava vstupních dat:** Ve složce `raw/` se nacházejí původní surové tabulky. Z nich byl (pravděpodobně ručně či dřívější kompilací) vytvořen zčištěný vstupní soubor `20250927_sinay_zakony.xlsx`, který obsahuje čistý seznam slovenských dokumentů (sloupec "Dokument SK").
2. **AI Obohacení (Enrichment):** Následně se na tento XLSX soubor aplikuje skript `tools/process_laws.py`. Tento skript pomocí OpenAI API (LLM) automaticky dohledá ke každému slovenskému zákonu jeho český ekvivalent, příslušné odkazy na právní portály (slov-lex.sk, zakonyprolidi.cz) a české gestory. Výsledek tohoto AI obohacení se uloží do výstupního pracovního souboru `sinay_zakony_processed.json`.
