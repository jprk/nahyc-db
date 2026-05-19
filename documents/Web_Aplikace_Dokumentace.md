# Dokumentace k webové aplikaci: Katalog regulačních dokumentů H2

Tento dokument popisuje fungování a vnitřní logiku webové aplikace pro vyhledávání a filtrování v databázi regulačních dokumentů a norem týkajících se vodíkových technologií.

## 1. Architektura a použité technologie

Aplikace je postavena na odlehčeném frameworku a nevyžaduje složitou infrastrukturu:
- **Backend:** Python + Flask
- **Databáze:** SQLite (lokální soubor `regulatory_documents.db`)
- **Frontend:** HTML5, CSS3, šablony Jinja2
- **Ikony a fonty:** Phosphor Icons, Google Fonts (Inter, Outfit)

Celý systém se dělí na dvě hlavní části:
1. Skript pro inicializaci a naplnění databáze (`Databaze/init_db.py`).
2. Samotná webová aplikace pro zobrazení rozhraní uživatelům (`Web/app.py` a příslušné šablony).

---

## 2. Příprava databáze (`init_db.py`)

Skript `init_db.py` slouží k prvotnímu vytvoření databáze z raw dat (ve formátu CSV).
- **Vytvoření schématu:** Skript založí tabulky pro dokumenty (`documents`), typy dokumentů (`document_types`), zdroje/orgány (`document_sources`), klíčová slova (`keywords`) a vazební tabulky pro spojení typu M:N (např. `document_keywords`).
- **Import dat:** Skript prohledává adresář `../Data` a hledá zpracované soubory `*_processed.csv`. Z nich iterativně načítá záznamy o jednotlivých dokumentech (název, typ, platnost, jazyk atd.).
- **Dynamické tagování:** Na základě samotných názvů CSV souborů (např. `A - výroba_Česká republika_processed.csv`) skript dokáže vyštípnout (parsovat) příslušná klíčová slova a přiřadit je vkládaným dokumentům.

Výsledkem spuštění tohoto skriptu je hotový soubor `regulatory_documents.db`, nad kterým webový backend následně provádí jen operaci čtení.

---

## 3. Backend webové aplikace (`app.py`)

Základním řídícím centrem webu je soubor `app.py` postavený nad mikrorámcem Flask.

### Připojení k databázi
Aplikace využívá přístup sdílené mezipaměti `get_db()`. Ta pomocí objektu `g` udržuje spojení pro každý aktuální HTTP požadavek (využívá se zde abstrakce `sqlite3.Row` pro snadnější přístup ke sloupcům pomocí jména složek na místo číselných indexů). Po obsloužení požadavku se spojení automaticky a bezpečně uzavře v injektovaném callbacku `@app.teardown_appcontext`.

### Interakce a filtry (`/` hlavní endpoint)
Tradiční flow práce uživatele využívá jednu cestu pro zobrazení tabulky. Při zadání parametrů uživatelem přes formulář dojde k sérii kroků:
1. **Načtení možností pro číselníky:** Podkapitola zavolá sdílenou funkci `get_filters()`, která načte existující typy dokumentů, orgány původu a štítky. Tím inicializuje možnosti pro `<select>` drop-down filtry.
2. **Zpracování vstupů:** Získají se parametry z URL adresy pomocí volání přes objekt `request.args`.
3. **Dynamické skládání SQL dotazu:**
   Načtené vyhledávací vstupy (fulltextový dotaz nebo konkrétní unikátní identifikátory v roletových filtrech) postupně dynamicky formují výsledný SQL string. Díky skládání pomocí parametrů (Prepared Statements ve stylizaci `?`) je systém bráněn vůči SQL Injection zranitelnosti.
4. **Omezení výsledků:** Vygenerovaný databázový dotaz je natvrdo usměrněn klauzulí `LIMIT 100`, zabraňující přehlcení frontendové tabulky při vrácení stovky až tisíce záznamů, když ještě uživatel zpočátku nezadal žádnou preferenci do filtru.
5. **Anotování dokumentů o štítky:** Po načtení základních entit z databáze se shromáždí jejich interní identifikátory (`id`), přes `IN` klausuli se seskupí příslušící klíčová slova k těmto dokumentům a na míru se připraví asociační slovník/tagy k zobrazení. 

Vyformovaná tabulka se potom skrze proměnné injektuje do šablony skrze standardizované volání pro instancování kontextu (`render_template`).

---

## 4. Frontend a uživatelské rozhraní (`templates/`)

Šablony zajišťují konečný vzhled uživateli a jsou funkčně rozděleny na vrchní kontejner vizualizačního DOM v `base.html` (kostra) a `index.html` (obsah).

### `base.html`
- Obsahuje inicializační `head` část (vložka aplikačního moderního CSS na míru, volání CDN ke knihovně fosforových ikon a moderních fontů od Google).
- Dodaný interaktivní JavaScript zajišťuje čistou Vanilla-JS implementaci naslouchače na elementech pro harmonikový list (Akordeon design vzor). Akce myši manipuluje stylové CSS třídy a rotuje ikonami na obalujícím kontajneru bez potřeby natahovat klientské masivní knihovny typu např. jQuery nebo React. 

### `index.html`
- **Sekce Hero:** Úvodní marketingová hlavička upoutávající pohonnou energii řešení ("sklovitý text", nadpisy atp.) 
- **Vyhledávací panelový formulář:** Propojuje odesílatelný formulář z input boxu s textem, a trojící filtrů k omezení listu zobrazených možností. Modifikace na kteréhokoliv filtru napřímo provede event `onchange="this.form.submit()"` vyžadující ihned nová data pro uživatele ke čtení, díky tomu pocitově nahrazuje moderní stavové reaktivní architektury jednoduchým způsobem. 
- **Zobrazovací komponenta Databázová tabulka:** Využitím iterace `{% for doc in documents %}` generuje opakovaným cyklením strukturu UI z Flasku o zaslané iterativní proměnné.
  - Vždy pro iteraci vypočítá horní sumarizační vrstvu v listu (Typ entity, Titulek, barevná metadata klíčových slov a vlaječky jazyka). 
  - V nižší, rozbalitelné části vizuálu zobrazuje po prokliku čtečky přesný popisek pro studium detailů z připomínek dokumentu, nebo odkaz (`doc.url`), který funguje jako přímý hyper odkaz na podklad z ministerstva/úřadovny. V případě nevyplnění je vizuálně diskrétně utlumen ("Zdroj nedostupný").

---

## Provoz aplikace 📈

1. **Obnova obsahu listu z dat:** Je nutné zajistit generované soubory např. `*_processed.csv` v relativně umístěné složce `../Data`. Následným voláním `python init_db.py` v adresáři `/Databaze` skript starý stav databáze smaže a provede čistou resynchronizaci na aktuální stav bez vzniku duplicitních odkazů.
2. **Přístup pro čtenáře k prohlížení:** Výsledná vizualizace se po provedení startu webového enginu pomocí příkazu `python app.py` nachází plnohodnotně a standardně k interakci uživatelů na doménové lokální lince `http://127.0.0.1:5000`. 
