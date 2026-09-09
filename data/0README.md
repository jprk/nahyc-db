# Adresář /data

Tento adresář slouží pro ukládání surových a předzpracovaných dat pro plnění databáze. Najdete zde podsložky, ve kterých jsou roztříděny datové sady podle jednotlivých řešitelů/témat. (Poznámka: Pomocné skripty, např. pro extrakci tabulek, byly přesunuty do adresáře `/tools`).

## Získávání plných textů (od 2026-09-09, viz `doc/PLAN.md` §4)

* `fulltext/` — stažené plné texty zákonů (PDF/HTML), git-ignorováno (velký objem, viz `.gitignore`). Plní `src/tools/fetch_fulltext.py`.
* `fulltext_manifest.json` — malý, verzovaný manifest (bez obsahu dokumentů) evidující, co bylo staženo, odkud a s jakým výsledkem — umožňuje idempotentní opakované běhy `fetch_fulltext.py` a bude vstupem pro budoucí Step 2 (`Document.file_path`).
* `fulltext_screening_candidates.json` — report kandidátů z `src/tools/screen_eurlex.py` / `screen_esbirka.py` / `screen_slovlex.py` (nové dokumenty k vodíku, resp. nefunkční odkazy). **Pouze report** — nikdy se nezapisuje zpět do `database_merged_raw.json` bez lidské kontroly.
