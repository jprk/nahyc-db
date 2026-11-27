# Nasazení databáze na produkční server

Stav k 26. 11. 2026, větev `feature/nasazeni`; produkce je v `/home/prikryl/DEVEL/nahyc-h2db`.

## 1. Rozhodnutí

Vývojová verze běží na stroji `labauto.fd.cvut.cz` (web `https://nahyc.fd.cvut.cz/h2db/`). Produkce
poběží na `vm-nahyc.fel.zcu.cz` (web `https://nahyc.fel.zcu.cz/h2db/`). Uživatel rozhodl
(26. 11. 2026):

1. Na produkci se dostane jen uživatel, a to jen ze sítě ZČU. Vývojový stroj produkci nevidí
   (port 22 neodpovídá), produkce naopak vývojový stroj ze sítě ČVUT vidí. **Spojení proto vždy
   navazuje produkce:** data si stáhne a kopii pro testovací web sama odešle.
2. Editorské účty přenášíme z vývoje.
3. `nahyc.fd.cvut.cz/h2db` po přepnutí zůstává jako **testovací web s kopií produkční databáze**.
4. Soubory, které se mění za provozu (opravy a rozhodnutí editorů, mezipaměti plánovače), ukládáme
   **mimo pracovní strom gitu** do adresáře z `.env` (`H2DB_STATE_DIR`).

Po přepnutí je zdrojem pravdy produkce. Databázi ani stavové soubory z vývoje na produkci už
nikdy nepřenášíme; opačným směrem (produkce → testovací web) ano.

```
            první nasazení (jednou)                  každý týden
vývoj (ČVUT) ───────────────────────► produkce (ZČU) ───────────────────► testovací web (ČVUT)
  balík: DB + stavové soubory           zdroj pravdy                       kopie produkce
  rsync: plné texty                     editoři, plánovač                  h2regdocs na labauto
            (stahuje produkce)                       (posílá produkce)
```

## 2. Co přenášíme

| Část | Velikost | Jak |
|---|---|---|
| Kód | — | git (stejný commit na obou strojích) |
| Databáze `h2regdocs` (43 tabulek vč. 3 editorských účtů) | asi 15 MB, výpis 1 MB | balík `transfer_bundle.py` (výpis `mariadb-dump --single-transaction`) |
| Stavové soubory (18 souborů, příloha A) | asi 3 MB | balík `transfer_bundle.py` |
| Plné texty `data/fulltext/` | 451 MB | `rsync` (jen změny) |
| Vyčištěné texty `data/fulltext_clean/` | 136 MB | `rsync`; lze je i vytvořit znovu (`extract_fulltext.py --apply`) |
| `.env`, `.openapi_key` | — | nevytváříme kopií: na produkci nové heslo k DB a nový `SECRET_KEY` |

Balík (`src/tools/transfer_bundle.py`) obsahuje výpis databáze, stavové soubory a `meta.json`
s počty řádků všech tabulek, commitem a kontrolními součty SHA-256. Instalace ověří součty, odmítne
přepsat databázi s tabulkami bez `--replace-db`, s ním ji nejdřív zálohuje, po importu porovná
počty řádků a stavové soubory uloží do `H2DB_STATE_DIR` (nahrazené soubory si ponechá v `backups/`).

## 3. Příprava produkce (jednou, správce serveru)

Cesty odpovídají dnešnímu stavu produkce; jiné stačí promítnout do `.env`, do konfigurace Apache
a do jednotek systemd ve `deploy/production/`.

### 3.1 Systém

- Debian 13 (nebo shodný se strojem labauto), Python 3.13, `python3-venv`, git, rsync.
- MariaDB alespoň 11 (řazení `utf8mb4_czech_ci`, generovaný sloupec `jurisdikce_uroven`; vývoj
  běží na 11.8).
- Apache 2.4 s `libapache2-mod-wsgi-py3` pro stejnou verzi Pythonu, HTTPS pro `nahyc.fel.zcu.cz`.

### 3.2 Účet a adresáře

Na produkci je dnes vše v pracovním stromu `/home/prikryl/DEVEL/nahyc-h2db` účtu `prikryl`
(26. 11. 2026). Postup s tím počítá:

- Aplikace, plánovač i kopie na testovací web běží pod účtem `prikryl` (démon mod_wsgi
  s `user=prikryl`, jednotky systemd s `User=prikryl`).
- `/home/prikryl/DEVEL/nahyc-h2db` — pracovní strom gitu; `/home/prikryl/DEVEL/nahyc-h2db-state` —
  stavové soubory (`H2DB_STATE_DIR`), mimo pracovní strom gitu. Do tohoto adresáře musí smět zapisovat
  účet, pod nímž běží démon mod_wsgi (na vývojovém stroji právě chybějící právo zápisu způsobilo chybu
  opravenou v PR #34).
- SSH klíč účtu `prikryl` na produkci přidáme na vývojovém stroji do `~laborator/.ssh/authorized_keys`
  (s omezením `from="147.228.82.118"`): přes něj produkce stahuje balík a posílá kopii.

### 3.3 Kód a prostředí

```
git clone git@github.com:jprk/nahyc-db.git /home/prikryl/DEVEL/nahyc-h2db
#  (bez přístupu na GitHub: git clone laborator@nahyc.fd.cvut.cz:/home/laborator/DEVEL/nahyc-h2db /home/prikryl/DEVEL/nahyc-h2db)
cd /home/prikryl/DEVEL/nahyc-h2db && git checkout <commit vývojového stroje>
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp deploy/production/env.example .env && chmod 600 .env    # doplnit heslo k DB a SECRET_KEY
```

### 3.4 Databáze a Apache

```
CREATE DATABASE h2regdocs CHARACTER SET utf8mb4 COLLATE utf8mb4_czech_ci;
CREATE USER 'h2regdocs'@'localhost' IDENTIFIED BY '<heslo z .env>';
GRANT ALL PRIVILEGES ON h2regdocs.* TO 'h2regdocs'@'localhost';
```

Konfiguraci Apache převezmeme ze vzoru `deploy/production/apache-h2db.conf` (démon mod_wsgi pod
účtem `prikryl`, `WSGIScriptAlias /h2db`).

## 4. První nasazení

### 4.1 Zmrazení vývoje

Editory upozorníme, že od tohoto okamžiku do přepnutí na vývojovém webu nic neměníme (fronta
kandidátů, opravy, rozhodnutí); jinak by změna zůstala jen ve vývojové databázi.

### 4.2 Export na vývojovém stroji

```
cd /home/laborator/DEVEL/nahyc-h2db && git pull        # hlavní strom na commitu, který nasazujeme
.venv/bin/python src/tools/transfer_bundle.py export --dir ~/h2db-export
```

Vznikne `~/h2db-export/<datum_čas>/` a odkaz `~/h2db-export/latest`.

### 4.3 Stažení a instalace na produkci

```
/home/prikryl/DEVEL/nahyc-h2db/deploy/production/pull_from_development.sh
```

Skript stáhne balík a plné texty, zkontroluje, že produkce běží na stejném commitu jako vývoj,
a nainstaluje databázi i stavové soubory. Opakované nasazení do databáze s tabulkami vyžaduje
`--replace-db` (databázi nejdřív zálohuje).

### 4.4 Plánovač

Časovače sběru zdrojů (`deploy/scheduler/`) zapneme **jen na produkci**, s účtem a cestami podle
odstavce 3 (`User=prikryl`, `WorkingDirectory=/home/prikryl/DEVEL/nahyc-h2db`). Na vývojovém stroji plánovač neběží
a po přepnutí ho tam nezapínáme: dva sběry by zapisovaly do dvou různých databází.

### 4.5 Přepnutí testovacího webu

Na vývojovém stroji nastavíme v `.env` hlavního stromu `H2DB_STATE_DIR=/home/laborator/h2db-test-state`.
Kopie produkce pak ukládá stavové soubory tam a nepřepisuje soubory v `data/` pracovního stromu
gitu, se kterými pracuje vývoj. Testovací web zůstává na `nahyc.fd.cvut.cz/h2db`. Do téhož `.env` přidáme `H2DB_INSTANCE=test`:
úvodní stránka pak nad nadpisem a každá stránka v patičce ukazují upozornění „Testovací verze“
s odkazem na produkční web. Produkce proměnnou nenastavuje. `H2DB_INSTANCE=test` platí na testovacím webu
už od 26. 11. 2026.

**Po každé změně `.env` aplikaci znovu načteme:**

```
touch /home/laborator/DEVEL/nahyc-h2db/wsgi.py      # na produkci /home/prikryl/DEVEL/nahyc-h2db/wsgi.py
```

Aplikace čte `.env` jen při startu procesu. Démon mod_wsgi při dalším požadavku zjistí změnu času
`wsgi.py` a aplikaci načte znovu. Bez toho běžící web novou hodnotu nevidí (26. 11. 2026 se tak
upozornění „Testovací verze“ neobjevilo, dokud jsme `wsgi.py` neaktualizovali). Plánovač a skripty
z příkazové řádky čtou `.env` při každém spuštění, ty se znovu načítat nemusí.

Patička na obou strojích uvádí „Verze webu (git)“: popis commitu (`git describe`), a když proces
webového serveru git spustit nesmí (repozitář patří jinému uživateli), commit a větev přečtené
přímo ze souborů `.git`.

### 4.6 Kontrola po nasazení

- `https://nahyc.fel.zcu.cz/h2db/`: katalog ukazuje 1432 dokumentů (stav k 26. 11. 2026), filtry
  a vyhledávání fungují (např. „svazek lahví“ najde ISO 11114-2 přes klíčová slova).
- Stránka dokumentu (`/dokument/eu-2021-535`): popis, klíčová slova, verze, odkaz „Číst text“.
- Přihlášení editora, fronta kandidátů a fronta oprav (36 položek „Kontrola záznamů“).
- Zápis: zkušební oprava v editorském rozhraní se objeví v `/home/prikryl/DEVEL/nahyc-h2db-state/manual_corrections.json`,
  ne v `/home/prikryl/DEVEL/nahyc-h2db/data/`. Zkušební opravu potom zamítneme.
- `.venv/bin/python src/tools/check_records.py` doběhne bez chyby.
- V patičce je „Verze webu (git)“ se stejným commitem jako na vývojovém stroji a žádné upozornění
  „Testovací verze“ (produkce `H2DB_INSTANCE` nenastavuje).

## 5. Aktualizace kódu na produkci

```
cd /home/prikryl/DEVEL/nahyc-h2db
.venv/bin/python src/tools/backup_db.py --reason before_update
git pull && .venv/bin/pip install -r requirements.txt
# migrace, které nová verze uvádí v popisu PR (stejné jako TEST_DB_MIGRATIONS v run_tests.py)
touch wsgi.py
```

Změny dat (opravy záznamů) děláme na produkci: editorským rozhraním, nebo souborem oprav a
`apply_manual_corrections.py --apply` se zálohou. Výpis databáze z vývoje na produkci už nepřenášíme.
Stavové soubory v `data/` gitu po přepnutí slouží jen jako výchozí stav pro vývoj a testy.

## 6. Kopie produkce na testovací web

Produkce každou neděli ve 3:30 (`deploy/production/h2db-copy-to-test.timer`) spustí
`push_copy_to_test.sh`: vytvoří balík, pošle ho s novými plnými texty na vývojový stroj a tam ho
nainstaluje do `h2regdocs` (s `--replace-db`, tedy se zálohou). Testovací web pak ukazuje stav
produkce z neděle; testy (`run_tests.py`) dál kopírují `h2regdocs` do `h2regdocs_test`.

## 7. Návrat k předchozímu stavu

- Kód: `git checkout <předchozí commit>` a `touch wsgi.py`.
- Databáze: záloha z `backups/` (`gunzip -c <záloha> | mariadb h2regdocs`); každá instalace balíku
  i aktualizace podle odstavce 5 zálohu vytváří.
- Stavové soubory: kopie nahrazených souborů v `backups/state_before_bundle_<datum_čas>/`.

## 8. K potvrzení se správcem produkce

1. Verze systému, Pythonu a MariaDB na `vm-nahyc.fel.zcu.cz`; zda Apache smí spouštět démona
   mod_wsgi pod účtem `prikryl` a číst jeho domovský adresář.
2. Zda produkce smí přes SSH na `nahyc.fd.cvut.cz` (port 22) a na GitHub.
3. Kdo spravuje Apache a certifikát `nahyc.fel.zcu.cz` (dnes na všech cestách WSGI vrací 500).

## Příloha A: stavové soubory

Seznam vede `src/tools/state_paths.py` (`STATE_FILES`); všechny skripty a webová aplikace k nim
přistupují přes `state_paths.data_file()` a test `tests/test_state_paths.py` hlídá, aby žádný
nevedl přímo do `data/`.

| Soubor | Kdo zapisuje |
|---|---|
| `manual_corrections.json` | editoři (opravy), kontrola záznamů |
| `accepted_candidates.json`, `document_relations_editor.json` | editoři (fronta kandidátů) |
| `validity_cache.json`, `norm_validity_cache.json` | kontrola platnosti, sběr, editoři |
| `harvest_not_imported.json`, `source_checks.jsonl` | sběr zdrojů |
| `document_relations_validity.json` | promítnutí stavů dokumentů |
| `eu_consolidation_cache.json` | konsolidovaná znění aktů EU |
| `fulltext_manifest.json` | stahování plných textů |
| `triage_model_cache.json` | automatické třídění fronty |
| `eurovoc_cache.json`, `ics_cache.json`, `keyword_model_cache.json` | klíčová slova nových dokumentů |
| `official_titles_cache.json`, `record_check_model_cache.json`, `record_checks.json`, `record_checks_model.json` | kontrola záznamů |
