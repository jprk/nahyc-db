# Zpracování dat a životní cyklus databáze (Processing Pipeline)

Tento dokument popisuje proces vzniku a zpracování dat pro Katalog regulačních dokumentů H2, od získání surových dat až po jejich publikaci ve webové aplikaci.

Proces je plně automatizovaný a sestává z několika fází:

## 1. Příjem a primární zpracování zdrojových dat
Surová data jsou obvykle dodávána od partnerů projektu (např. v Excelu nebo CSV). Tato data se ukládají v podsložkách adresáře `data/` a zpracovávají se jednoúčelovými skripty.

* **Sinay:** Původní slovenský seznam (např. `20250927_sinay_zakony.xlsx`) se zpracovává pomocí AI skriptů.
* **Haltuf:** Skript `tools/process_haltuf.py` konsoliduje rozsáhlé tabulky ve formátu CSV.
* **Prokop:** Detailní popis dvoufázového zpracování norem z původního DOCX dokumentu (využití skriptů `tools/read_docx.py` a `tools/parse_norms.py`) naleznete v [0README.md adresáře Prokop](../data/20250303_Prokop/0README.md).

## 2. Obohacení dat (AI Enrichment)
Syrová data jsou často nekompletní. Pomocí skriptů využívajících model GPT (OpenAI) se automaticky dohledávají chybějící prvky:
* `tools/process_laws.py` - Hledá k dodaným slovenským nebo mezinárodním zákonům české ekvivalenty (zákony účinné v ČR), odvozuje gestory (např. MŽP) a nachází URL na systémy typu zakonyprolidi.cz.
* `tools/enrich_eu_laws.py` - Identifikuje nadřazené evropské směrnice a dohledává k nim korektní odkazy do systému EUR-Lex.

## 3. Sloučení do jednotného formátu
Ve chvíli, kdy jsou partneři a jejich datové sady lokálně předzpracované, je nutné je sloučit do jednoho souboru.
* Nástroj: `tools/build_unified_db.py`
* Zpracuje jednotlivé (i různorodé) výstupy od partnerů a vygeneruje jeden obří, formátově standardizovaný seznam v souboru **`data/databaze_komplet.json`**. Tento soubor se stává hlavním referenčním bodem (SSOT - Single Source of Truth) pro další operace.

## 4. Obohacení anotací (Summarization)
Záznamy sloučené do `databaze_komplet.json` velmi často postrádají smysluplnou anotaci nebo zkrácený popis (Poznámku).
* Nástroj: `tools/enrich_annotations.py`
* Tento nástroj prochází `databaze_komplet.json` a u každého záznamu, který postrádá anotaci, využije LLM (OpenAI) k sepsání profesionálního, krátkého (1–3 věty) vysvětlení účelu daného předpisu nebo normy a upravený výsledek opět uloží.

## 5. Naplnění relační databáze (SQLite)
Ačkoliv je `databaze_komplet.json` sjednocený soubor, webová aplikace (Flask) vyžaduje pro efektivní vyhledávání, filtrování a vztahy relační databázi (SQLite).
* Nástroj: `db/init_db.py`
* **Jak se volá:** Jednorázově (nebo při aktualizaci jsonu) se v kořenovém adresáři spustí `python db/init_db.py`.
* **Proč:** Skript vymaže starou databázi, vytvoří strukturu tabulek podle UML návrhu (oddělené tabulky pro typy, zdroje, dokumenty a klíčová slova) a iteruje celým JSON souborem. Výsledkem je lehká plnohodnotná lokální databáze `db/regulatory_documents.db`.

## 6. Provoz aplikace (Backend & Frontend)
Ve finální fázi aplikace tyto data pouze čte.
* `app/app.py` servíruje data z `db/regulatory_documents.db` na endpoint `http://127.0.0.1:5000/`. K žádnému dalšímu zápisu či změnám ze strany uživatelů webu zde nedochází (databáze funguje v aplikaci primárně v read-only režimu).
