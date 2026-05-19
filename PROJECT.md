# Popis projektu: Databáze regulačních předpisů a předrealizačních procesů (Vodíkový technologický inkubátor)

Tento projekt implementuje strukturované úložiště (databázi) a webové rozhraní pro evidenci, verzování, kategorizaci a efektivní vyhledávání regulatorních dokumentů týkajících se vodíkových technologií. Jedná se o klíčovou výzkumnou a infrastrukturní komponentu v rámci projektu Národního centra vodíkové mobility (TN02000007), konkrétně dílčího projektu DP004 "Nástroje a znalostní systém pro inkubaci vodíkových technologií".

**Goal**: Host a Python web interface to a public database of hydrogen fuel related norms, laws, and other regulating documents.

## Project Summary (Czech)
"Výsledek představuje databázi předpisů a procesů, jež bude strukturovaným a přístupným zdrojem informací pro všechny zainteresované subjekty. Bude zahrnovat klíčové národní i mezinárodní regulační předpisy a normy související s výstavbou, instalací a provozem vodíkových technologií. Databáze bude průběžně aktualizována na základě legislativních změn a nově schválených regulací. Část konsolidovaných dat (typicky normy) budou přístupné přes služby (obvykle placené) třetích stran."

## Struktura projektu

| Adresář | Popis obsahu |
|---------|--------------|
| `/app` | Zdrojové kódy a webové rozhraní Flask aplikace pro prohlížení databáze. |
| `/data` | Surová a předzpracovaná data pro plnění databáze, rozdělená podle zdrojů (Prokop, Sinay, Haltuf). |
| `/db` | Inicializační skripty, UML návrhy a samotný soubor SQLite databáze. |
| `/documents` | Projektová technická dokumentace (např. k webové aplikaci). |
| `/text` | Oficiální textové výstupy, analýzy a kompletní zprávy k projektu (Word, PDF, Markdown). |
| `/tools` | Pomocné a analytické Python skripty pro zpracování podkladů. |

**Důležitá pravidla pro vývojáře:**
- Všechny pomocné skripty vytvářej v adresáři `tools/`, nepatří do kořene projektu.
- Pokud někde vytvoříš nový soubor, zapiš informaci o tomto souboru do příslušného `0README.md` v daném adresáři.

## Cíl projektu
Hlavním cílem je sjednotit roztříštěné právní a regulatorní prostředí týkající se vodíkových technologií v ČR (výroba, distribuce, skladování, využití) a převést jej do formalizované datové podoby. Databáze snižuje regulatorní nejistotu a transakční náročnost pro investory, provozovatele infrastruktury a orgány státní správy tím, že propojuje právní rovinu s konkrétními technologickými (use-case) scénáři.

## Architektura a technické řešení
Aplikace je navržena jako lehká, s oddělenou částí pro přípravu dat a prezentační vrstvou:
- **Backend:** Python + Flask (soubor `app/app.py`).
- **Databáze:** Relační databáze na bázi SQLite (soubor `db/regulatory_documents.db`), jenž se dynamicky plní skriptem `db/init_db.py`.
- **Frontend:** HTML5, CSS3 a šablony Jinja2 (`app/templates/`). Využívá responzivní design, Phosphor Icons a Google Fonts bez nutnosti masivních JavaScriptových knihoven (využívá Vanilla JS pro základní interaktivitu).
- **Zpracování dat:** Surová strukturovaná metadata z právních analýz se nachází ve složce `data` (CSV formáty). Různé pomocné Python skripty ve složce `tools/` pak pomáhají s analýzou a zpracováním (např. Excel tabulek, scrapováním zákonů atd.).

## Datová struktura a logika
Základní logickou jednotkou v databázi je **dokument**. Logika aplikace je postavená na následujících vrstvách:
- **Identita dokumentu:** Unikátní identifikátor, název, popis.
- **Kategorizace:** Vazba na definovaný typ (legislativa, metodika, norma atd.) a orgán / instituci původu.
- **Tematické indexování (štítky):** Vazby přes klíčová slova umožňující filtrování např. podle aplikované technologie (elektrolyzér, plnicí stanice, apod.).
- **Verzování:** Mechanismus zachycující časovou dimenzi dokumentů a jejich vývoj.

## Používání
Aplikace se provozuje spuštěním webového serveru (Flask engine pomocí `python app.py` ve složce `app`) a je pro uživatele k dispozici lokálně přes port 5000. 
Hlavní stránka (`/`) poskytuje vyhledávací panel, v němž lze parametricky nebo fulltextově filtrovat dokumenty podle potřeby. Výsledky obsahují shrnutí dokumentu a hypertextové odkazy na původní zdroje, pokud je to licenčně a autorsky přípustné.

## Výzkumný přínos a autoři
Databáze neslouží pouze jako repozitář textů, ale transformuje roztříštěné, víceúrovňové předpisy do analyticky využitelné struktury. Na realizaci a údržbě dat se podílí konsorcium RICE FEL Západočeské univerzity (ZČU), Centra dopravního výzkumu (CDV), VŠB-TUO a platformy HYTEP. ZČU je hlavním garantem technické infrastruktury a pravidelných automatizovaných i expertních aktualizací.
