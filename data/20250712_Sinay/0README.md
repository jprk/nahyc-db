# Adresář /data/20250712_Sinay

Tento adresář obsahuje zdrojová data a podklady týkající se zákonů a legislativních předpisů ve zpracované i nezpracované podobě.

## Zpracování zákonů (Pipeline)
1. **Příprava vstupních dat:** Ve složce `raw/` se nacházejí původní surové tabulky. Z nich byl (pravděpodobně ručně či dřívější kompilací) vytvořen zčištěný vstupní soubor `20250927_sinay_zakony.xlsx`, který obsahuje čistý seznam slovenských dokumentů (sloupec "Dokument SK").
2. **AI Obohacení (Enrichment):** Následně se na tento XLSX soubor aplikuje skript `tools/process_laws.py`. Tento skript pomocí OpenAI API (LLM) automaticky dohledá ke každému slovenskému zákonu jeho český ekvivalent, příslušné odkazy na právní portály (slov-lex.sk, zakonyprolidi.cz) a české gestory. Výsledek tohoto AI obohacení se uloží do výstupního pracovního souboru `sinay_zakony_processed.json`.

## Zpracování norem (samostatná větev, 2026-09-09)
`raw/Zoznam_noriem_vodik-11_02_2025.pdf` (statický seznam technických noriem, PDF) a `raw/Zoznam_noriem_Vodik_Road_map_Nemecko_Priradenie_STN_VERZIA_2024_06_27b.xlsx` (německá vodíková roadmapa s návrhem přiřazení k STN) byly dosud nezpracované. Skript `src/tools/parse_sinay_norms.py` je parsuje a slučuje do `sinay_normy_processed.json` (1949 záznamů), se schématem shodným s `data/20250303_Prokop/normy_vodik.json` (Sekce/Značka/Název/Kategorie/Platnost/Anotace/Klíčová slova/Link) plus pole `Jurisdikce` — obsahově jde o normy, ne zákony, proto se drží Prokopova schématu. Od 2026-09-09 zapojeno do `build_unified_db.py` jako zdroj `Sinay_Normy` (viz `doc/PLAN.md` Step 1, follow-up #9) — `jurisdikce` zajišťuje, že se slovenská/německá norma nikdy neslije s českou ČSN adopcí téže EN/ISO normy.

`sinay_normy_csn_equivalents.json` (generuje `src/tools/check_foreign_norm_csn_equivalents.py`) je samostatný, needitovaný report: pro slovenské/německé normy s ISO/EN číslem ověřuje proti registru ČSN online, zda existuje odpovídající aktuálně platná ČSN — nikdy je ale neslučuje (zahraniční norma zůstává i s potvrzeným ekvivalentem samostatným záznamem).
