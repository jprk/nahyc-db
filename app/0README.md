# Adresář /app

Tento adresář obsahuje zdrojové kódy a webové rozhraní Flask aplikace pro prohlížení databáze regulačních předpisů. 

## Struktura aplikace
* `app.py` – Hlavní vstupní bod spouštění aplikace. Obsahuje logiku routování, načítání z databáze a aplikační logiku.
* `static/` – Adresář pro statické soubory, jako jsou kaskádové styly (CSS), klientské skripty (JavaScript) a obrázky či loga, které se uživateli přímo načítají v prohlížeči.
* `templates/` – Adresář pro HTML šablony využívající Jinja2. Zde se definuje vzhled webových stránek, do kterých se dynamicky vkládají data z databáze.
* `tests/` – Sada automatizovaných testů (např. pomocí pytest) pro ověření funkčnosti a stability aplikace.
