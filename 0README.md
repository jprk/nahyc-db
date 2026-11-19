# Adresář /app

Tento adresář obsahuje zdrojové kódy a webové rozhraní Flask aplikace pro prohlížení databáze regulačních předpisů. 

## Struktura aplikace
* `app.py` – Hlavní vstupní bod spouštění aplikace. Obsahuje logiku routování, načítání z databáze a aplikační logiku.
* `admin.py` – Přihlášení editorů, revize dokumentů s principem dvou osob a auditní log.
* `candidates_admin.py` – Kandidáti na nové dokumenty (`/admin/candidates`): seznam s filtry, detail s podklady, návrh přijetí a potvrzení druhým editorem (dokument se založí ihned), zamítnutí a odložení jedním editorem, ruční návrh dokumentu (2026-10-27).
* `catalog_filters.py` – Filtry katalogu podle připomínek MPO (`doc/MPO_PRIPOMINKY.md`, krok 2, 2026-11-19): filtr jurisdikce (výchozí stav v konstantě `DEFAULT_JURISDICTION`), podtypy aktů EU v nabídce typů (`podtyp-delegated`, `podtyp-implementing`), synonyma vyhledávání z `data/search_synonyms.json` a skupiny původců z `data/source_groups.json`. Katalog (`app.py`) zobrazuje jeden řádek na předpis; jazykové varianty (`TRANSLATION_OF`) jsou v něm odkazy CS/EN.
* `drafts_admin.py` – Připravované dokumenty (`/admin/drafts`): převod návrhu na vyhlášený předpis — dokument se stal vyhlášeným předpisem (nové označení, stav „vyhlášený, dosud neúčinný“ nebo „účinný“), nebo je vyhlášený předpis v databázi jako jiný dokument (vazba `ENACTED_AS`, návrh „nahrazený“); návrh jedním editorem, potvrzení druhým, auditní log (2026-11-19, `doc/MPO_PRIPOMINKY.md` krok 3).
* `static/` – Adresář pro statické soubory, jako jsou kaskádové styly (CSS), klientské skripty (JavaScript) a obrázky či loga, které se uživateli přímo načítají v prohlížeči.
* `templates/` – Adresář pro HTML šablony využívající Jinja2. Zde se definuje vzhled webových stránek, do kterých se dynamicky vkládají data z databáze.
* `tests/` – Sada automatizovaných testů (např. pomocí pytest) pro ověření funkčnosti a stability aplikace.
