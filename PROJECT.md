# Popis projektu: Databáze regulačních předpisů a předrealizačních procesů (Vodíkový technologický inkubátor)

Tento projekt implementuje strukturované úložiště (databázi) a webové rozhraní pro evidenci, verzování, kategorizaci a efektivní vyhledávání regulatorních dokumentů týkajících se vodíkových technologií. Jedná se o klíčovou výzkumnou a infrastrukturní komponentu v rámci projektu Národního centra vodíkové mobility (TN02000007), konkrétně dílčího projektu DP004 "Nástroje a znalostní systém pro inkubaci vodíkových technologií".

**Goal**: Host a Python web interface to a public database of hydrogen fuel related norms, laws, and other regulating documents.

## Project Summary (Czech)
"Výsledek představuje databázi předpisů a procesů, jež bude strukturovaným a přístupným zdrojem informací pro všechny zainteresované subjekty. Bude zahrnovat klíčové národní i mezinárodní regulační předpisy a normy související s výstavbou, instalací a provozem vodíkových technologií. Databáze bude průběžně aktualizována na základě legislativních změn a nově schválených regulací. Část konsolidovaných dat (typicky normy) budou přístupné přes služby (obvykle placené) třetích stran."

## Struktura projektu

Pozn.: repozitář je aktuálně v procesu reorganizace — podrobnosti a
aktuální stav viz `CLAUDE.md`.

| Adresář | Popis obsahu |
|---------|--------------|
| `/app` | Zdrojové kódy Flask aplikace pro prohlížení databáze — kanonické umístění, spouští se odsud (`app/app.py`, vstupní bod `wsgi.py` importuje `app.app`). |
| `/src/tools` | Pomocné a analytické Python skripty pro sestavení, obohacení a zpracování podkladů — přehled v `src/tools/0README.md`. |
| `/src/sites` | Dedikované parsery pro autoritativní zdrojové weby dokumentů (EUR-Lex, zakonyprolidi.cz, slov-lex.sk, normy.normoff.gov.sk, e-sbírka) — přehled v `src/sites/0README.md`. |
| `/data` | Surová a předzpracovaná data pro plnění databáze, rozdělená podle zdrojů (Prokop, Sinay, Haltuf) + sloučené JSON výstupy pipeline — přehled v `data/0README.md`. |
| `/tests` | Automatizované testy (stdlib `unittest`) — spuštění `.venv/bin/python -m unittest discover -s tests -p "test_*.py"`; přehled v `tests/0README.md`. |
| `/doc` | Dokumentace projektu: `PLAN.md` (živý deník konsolidace databáze), `REQUIREMENTS.md`, `konsolidace/` (konsolidované DB schéma) a zdrojové podklady V01–V03. |
| `wsgi.py` | WSGI vstupní bod aplikace (importuje `app.app`). |
| `requirements.txt`, `.env.example` | Závislosti a šablona konfigurace — viz „Používání" níže. |
| `/zip/v01` | Archivní záloha staršího stavu repozitáře (needituj). |

`Databaze/` a `Web/` v kořeni jsou dočasné pracovní adresáře mimo tuto
strukturu — viz `CLAUDE.md`.

**Důležitá pravidla pro vývojáře:**
- Všechny pomocné skripty vytvářej v adresáři `src/tools/`, nepatří do kořene projektu.
- Pokud někde vytvoříš nový soubor, zapiš informaci o tomto souboru do příslušného `0README.md` v daném adresáři.

## Cíl projektu
Hlavním cílem je sjednotit roztříštěné právní a regulatorní prostředí týkající se vodíkových technologií v ČR (výroba, distribuce, skladování, využití) a převést jej do formalizované datové podoby. Databáze snižuje regulatorní nejistotu a transakční náročnost pro investory, provozovatele infrastruktury a orgány státní správy tím, že propojuje právní rovinu s konkrétními technologickými (use-case) scénáři.

## Architektura a technické řešení
Aplikace je navržena jako lehká, s oddělenou částí pro přípravu dat a prezentační vrstvou:
- **Backend:** Python + Flask (soubor `app/app.py`).
- **Databáze:** Relační databáze MariaDB (schéma `h2regdocs`, `doc/konsolidace/`), kterou dynamicky plní skript `src/tools/init_db.py` z výstupu datové pipeline.
- **Frontend:** HTML5, CSS3 a šablony Jinja2 (`app/templates/`). Využívá responzivní design, Phosphor Icons a Google Fonts bez nutnosti masivních JavaScriptových knihoven (využívá Vanilla JS pro základní interaktivitu).
- **Zpracování dat:** Surová strukturovaná metadata z právních analýz (Excel/PDF/DOCX podklady partnerů) se nachází ve složce `data`, rozdělená podle zdrojů. Pipeline ve `src/tools/` je slučuje, deduplikuje, obohacuje o autoritativní metadata z `src/sites/` a nahrává do databáze — dokumentovaný postup a pořadí kroků viz `doc/PLAN.md`.

## Datová struktura a logika
Základní logickou jednotkou v databázi je **dokument**. Logika aplikace je postavená na následujících vrstvách:
- **Identita dokumentu:** Unikátní identifikátor, název, popis.
- **Kategorizace:** Vazba na definovaný typ (legislativa, metodika, norma atd.) a orgán / instituci původu.
- **Tematické indexování (štítky):** Vazby přes klíčová slova umožňující filtrování např. podle aplikované technologie (elektrolyzér, plnicí stanice, apod.).
- **Verzování:** Mechanismus zachycující časovou dimenzi dokumentů a jejich vývoj.

## Používání

### Instalace a spuštění (od začátku)

```bash
# 1. Python prostředí
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. Konfigurace — zkopíruj a vyplň skutečné údaje k MariaDB
cp .env.example .env

# 3. Databáze — jednorázově založí databázi h2regdocs, aplikačního
#    uživatele (přesně účet z .env výše) a schéma. Vyžaduje SAMOSTATNÝ,
#    oprávněnější MariaDB účet (admin/root — jen pro tento krok, nikdy
#    z .env) — bez zadání --admin-user/--admin-password se na něj
#    interaktivně zeptá. Vyžaduje nainstalovaný klient `mariadb`
#    (systémový balíček, ne Python knihovnu). Bez spuštění, jen ukázat,
#    co by se provedlo: přidej --dry-run.
.venv/bin/python src/tools/provision_db.py

# 4. Naplnění dat — již sloučený a deduplikovaný korpus
#    (data/database_merged_deduplicated.json) je součástí repozitáře,
#    takže stačí ho nahrát do databáze a připojit relace/procesní vrstvu:
.venv/bin/python src/tools/init_db.py
.venv/bin/python src/tools/load_document_relations.py
.venv/bin/python src/tools/load_process_layer.py

# 5. Spuštění aplikace — naslouchá na http://localhost:5050
.venv/bin/python app/app.py
```

Produkční nasazení používá `wsgi.py` (importuje `app.app`) jako vstupní
bod pro WSGI server (např. gunicorn), ne přímé spuštění `app/app.py`.

Výše je minimální cesta k běžící aplikaci nad již připraveným korpusem.
Přesestavení korpusu z původních zdrojových podkladů partnerů (Excel/PDF
tabulky ve `/data`) — sloučení, deduplikace, obohacení o autoritativní
metadata z `src/sites/` — je samostatný, delší proces zdokumentovaný v
`doc/PLAN.md`; začíná skriptem `src/tools/build_unified_db.py`.

### Funkce webového rozhraní

Hlavní stránka (`/`) poskytuje vyhledávací panel, v němž lze parametricky
(typ dokumentu, gestor/vydávající orgán, klíčové slovo) nebo fulltextově
filtrovat dokumenty podle potřeby, s výsledky stránkovanými po 50
záznamech. Každý dokument má vlastní trvalou stránku (`/dokument/<slug>`,
klíčovanou stabilním identifikátorem odvozeným z označení dokumentu, ne z
databázového `id`, které se při přesestavení dat mění) se shrnutím,
metadaty, historií verzí, souvisejícími dokumenty a hypertextovým odkazem
na původní zdroj, pokud je to licenčně a autorsky přípustné. Výsledky lze
exportovat jako CSV, JSON nebo XML (`/export/<formát>`), export vždy
obsahuje celou filtrovanou množinu, ne jen aktuální stránku.

## Výzkumný přínos a autoři
Databáze neslouží pouze jako repozitář textů, ale transformuje roztříštěné, víceúrovňové předpisy do analyticky využitelné struktury. Na realizaci a údržbě dat se podílí konsorcium RICE FEL Západočeské univerzity (ZČU), Centra dopravního výzkumu (CDV), VŠB-TUO a platformy HYTEP. ZČU je hlavním garantem technické infrastruktury a pravidelných automatizovaných i expertních aktualizací.
