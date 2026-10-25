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
* `test_editor_workflow.py` — celý editorský workflow přes skutečné stránky: přesměrování na přihlášení, špatné heslo, návrh opravy, zákaz potvrzení vlastního návrhu (403), potvrzení druhým editorem s rozdílem, auditní log. Fixtury (dva editoři a dokument) vytváří a maže v testovací DB.

**Známé vady nalezené scénáři** (označeno `@unittest.expectedFailure`, po opravě
běh ohlásí „unexpected success“): na telefonu 390 px se hlavička (logo, čtyři
odkazy, logo TAČR) nezalamuje, stránka je široká 616 px a posouvá se do stran
(R2.2).
