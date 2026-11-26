# Adresář /tests/e2e

Prohlížečové scénáře (Playwright + Chromium z `.venv`), které spouští
`src/tools/run_tests.py`: ten nastartuje Flask debug server nad testovací
databází, nastaví `H2DB_BASE_URL` a `H2DB_SHOT_DIR` a spustí `unittest discover`
v tomto adresáři. Samostatně (bez `H2DB_BASE_URL`) se scénáře přeskočí.

Každý scénář ukládá screenshoty do `data/test_screenshots/<datum_čas>/`
(mimo git, uchovává se posledních 5 běhů) a selže, když stránka vyhodí chybu
JavaScriptu nebo když požadavek na naši aplikaci selže / vrátí ≥ 400 bez
`expect_status()`. Cizí servery (písma, CDN ikon) se nehodnotí.

* `browser_case.py` — základní třída `BrowserTestCase` (životní cyklus prohlížeče, `new_page`, `goto`, `shot`, `shot_element`, kontrola chyb), `database_connection()` (jen `*_test` databáze) a velikosti zobrazení `DESKTOP`/`PHONE`.
* `test_catalog.py` — katalog: seznam a součty, hledání (i bez shody), filtr typu, rozbalení řádku, další strana, telefonní rozložení.
* `test_document_page.py` — stránka dokumentu: shoda s řádkem seznamu, nařízení EU 2022/869 (záznam 80), stažená kopie, placená norma (bez stažení, `/fulltext/<id>` = 403), neznámý slug = 404.
* `test_processes.py` — procesní pohled: sedm uzlů a matice, detail uzlu, telefonní rozložení.
* `test_fulltext_page.py` — čtení textu v aplikaci (issue #2): nařízení EU 2022/869 (očíslované body jako odstavce `p.item`, žádné `script`/`a`/`img`/`iframe`, telefon bez přetékání), český zákon (nadpisy a úrovně), placená norma = 403, surové stažení jako příloha se sandbox CSP. `run_tests.py` před startem serveru znovu vygeneruje `data/fulltext_clean/` (`extract_clean_texts`), takže scénáře nečtou texty po starší verzi extraktoru.
* `test_readability.py` — čitelnost odkazů: všechny textové odkazy na hlavních stránkách (katalog s rozbaleným řádkem, procesy, detail uzlu, přihlášení, dokument se vztahy) mají kontrast vůči tmavému pozadí aspoň 3.
* `test_editor_workflow.py` — celý editorský workflow přes skutečné stránky: přesměrování na přihlášení, špatné heslo, návrh opravy, zákaz potvrzení vlastního návrhu (403), potvrzení druhým editorem s rozdílem, auditní log. Fixtury (dva editoři a dokument) vytváří a maže v testovací DB.
* `test_candidates.py` (2026-11-05) — navíc hlavička fronty kandidátů: tři tlačítka v jedné řadě a stejně vysoká (40 px), nápověda „Jak s frontou pracovat“ (postup přijetí, pásma), na telefonu bez vodorovného posunu (dlouhé názvy zdrojů ve filtru).
* `test_harvest_queue.py` — řetěz sledovaných zdrojů (DATA_SOURCES.md, odstavec 8.16): zaznamenané nálezy zapsané `harvest.write_findings()` (bez sítě), filtry fronty kandidátů podle pásma, zdroje a skupiny, detail návrhu zákona se dvěma nálezy a dokumentem, který mění, přijetí dvěma editory a stránka vzniklého dokumentu („připravovaný“, „novelizuje“). Fixtury (klíče v `KEYS`, editoři `e2e_harv_*`) vytváří a maže v testovací DB.

**Vady nalezené scénáři a opravené** (2026-10-25): hlavička na telefonu 390 px
se nezalamovala (stránka široká 616 px, R2.2), na `/procesy` navíc široká
tabulka roztahovala panel v mřížce, a odkazy bez vlastní barvy (např. „Trvalý
odkaz“) měly výchozí modrou `#0000EE` na tmavém pozadí (kontrast 1,9).
Screenshoty se pořizují s `animations="disabled"`, aby nezachytily rozpracovaný
náběh (fade-in) úvodních textů.
* `test_fulltext_page.py` — navíc slovenský předpis ze Slov-Lexu (`124/2000 Z. z.`): odstavce `p.item d0`, písmena o úroveň hlouběji, značky § a nadpisy, žádný `script`/`a`/`img`/`iframe`.
* `test_mpo_comments.py` — připomínky MPO (`doc/MPO_PRIPOMINKY.md`, odstavec 2) jako scénáře: filtr původce „Evropská centrální banka“ bez duplicit, „RFNBO“ jeden řádek na předpis se štítky CS/EN a akty v přenesené pravomoci, podtyp v nabídce typů, nabídka původců seskupená bez zkratky „MD“, filtr jurisdikce (bez volby „Slovensko“ pro nepřihlášené), zákon o dráhách s původcem Ministerstvo dopravy, stránky energetického zákona a RED III bez hlášky „Stav ke dni 30.6.2025“, žádný veřejný popis ani export s „doc/PLAN.md“, telefon bez vodorovného posuvníku.
* `test_slovak_documents.py` — slovenské dokumenty mimo veřejný katalog (`doc/MPO_PRIPOMINKY.md`, odstavec 4.3): nepřihlášený je nevidí v seznamu, ve vyhledávání („STN“), v nabídkách jurisdikce a původců, v počtech na úvodní stránce, v exportech ani ve vazbách na stránkách dokumentů a procesů; stránka slovenského dokumentu se otevře z adresy s upozorněním; přihlášený editor je přepínačem „Zahrnout i slovenskou legislativu“ zahrne (počty, skupina Slovensko, filtr jurisdikce, export); telefon. Editora `e2e_sk_editor` vytváří a maže v testovací DB.
* `test_drafts.py` (2026-11-19, `doc/MPO_PRIPOMINKY.md` krok 3) — připravované dokumenty: z revizí na seznam návrhů, editor A navrhne, že se návrh stal vyhlášeným předpisem (nové označení, účinnost), čeká na druhého editora, editor B potvrdí; stránka dokumentu pak ukazuje nové označení, stav „vyhlášený, dosud neúčinný“ a poslední kontrolu stavu (editor). Druhý případ: návrh normy vyhlášený jako jiný dokument databáze (vazba „návrh vyhlášen jako“, návrh „nahrazený“, norma „účinný“), odkaz na převod ze stránky dokumentu; šířka telefonu. Obnovuje `data/manual_corrections.json` a `data/document_relations_editor.json`, které server ve stromu zapisuje.
* `test_triage_queue.py` (2026-11-20, `doc/FRONTA_AUTOMAT.md`) — automat ve frontě kandidátů: filtr návrhů automatu se štítkem „automat“, doporučení modelu v detailu a formulář předvyplněný podle něj, hromadné potvrzení zaškrtnutých návrhů, seznam a detail na telefonu bez vodorovného posunu.
* `test_mpo_vady.py` (2026-11-22, `doc/MPO_OVERENI_WEBU.md`) — Z1: úvodní stránka uvádí platné, připravované a historické (zrušené nebo nahrazené) zvlášť a jejich součet je celkový počet; Z2: ikona lupy leží uvnitř vyhledávacího pole na telefonu i na počítači.
* `test_review_filter.py` (2026-11-26) — filtr „Ke kontrole“ jen pro přihlášené editory: návštěvník volbu nevidí a parametr `kontrola` nemění seznam ani exporty; editor filtruje podle druhu důvodu (počty u voleb odpovídají SQL), kombinuje filtr s typem, exportuje pracovní seznam s důvody (JSON, CSV, XML), stránkování filtr drží; telefon bez vodorovného posuvníku. Editora `e2e_review_editor` vytváří a maže v testovací DB.
