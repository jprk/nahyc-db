# Adresář /data

Tento adresář slouží pro ukládání surových a předzpracovaných dat pro plnění databáze. Najdete zde podsložky, ve kterých jsou roztříděny datové sady podle jednotlivých řešitelů/témat. (Poznámka: Pomocné skripty, např. pro extrakci tabulek, byly přesunuty do adresáře `/tools`).

## Získávání plných textů (od 2026-09-09, viz `doc/PLAN.md` §4)

* `fulltext/` — stažené plné texty zákonů (PDF/HTML), git-ignorováno (velký objem, viz `.gitignore`). Plní `src/tools/fetch_fulltext.py`.
* `fulltext_manifest.json` — malý, verzovaný manifest (bez obsahu dokumentů) evidující, co bylo staženo, odkud a s jakým výsledkem — umožňuje idempotentní opakované běhy `fetch_fulltext.py` a bude vstupem pro budoucí Step 2 (`Document.file_path`).
* `fulltext_screening_candidates.json` — report kandidátů z `src/tools/screen_eurlex.py` / `screen_esbirka.py` / `screen_slovlex.py` (nové dokumenty k vodíku, resp. nefunkční odkazy). **Pouze report** — nikdy se nezapisuje zpět do `database_merged_raw.json` bez lidské kontroly.

## Procesní vrstva B (od 2026-09-10, viz `doc/PLAN.md` Krok 3a)

* `v02_processes_parsed.json` — strukturovaný výstup `src/tools/parse_v02_processes.py` (rozpad `doc/NAHYC DP004 V02 - Popis procesů.docx` na uzly U1–U7 + bibliografii), vstup pro `src/tools/load_process_layer.py`.
* `process_layer_review_queue.json` — nenapárované citace předpisů/norem a bibliografické položky vyžadující lidskou kontrolu (generuje `load_process_layer.py`, stejný princip jako `dedup_review_queue.json`).

## Chybějící dokumenty z bibliografie V02 (od 2026-09-11, viz `doc/PLAN.md` Krok 1 follow-up #17)

* `v02_bibliography_documents.json` — ručně kurátorovaný seznam 12 zákonů/nařízení/norem citovaných dokumentem V02 (uzly U2/U4/U5/U6/U7 i vlastní bibliografie), které se křížovou kontrolou proti `process_layer_review_queue.json` ukázaly být v korpusu zcela chybějící (ne chyba párování citací). Vstup pro `src/tools/build_unified_db.py` jako pátý zdroj `V02_Bibliografie` — už ve finálním tvaru záznamu, žádné zdrojové tabulky k parsování neexistují.

## Verzní historie dokumentů (od 2026-09-11, viz `doc/PLAN.md` Krok 1 follow-up #16)

* `document_relations.json` — ručně kurátorovaný seznam vztahů mezi dvěma samostatně číslovanými dokumenty (zákon novelizovaný jiným zákonem, viz `Konsolidace-DB-popis.md` §4.4) — vstup pro `src/tools/load_document_relations.py`. Detekce napříč celým korpusem vyžaduje lidský úsudek, proto malý a ručně udržovaný, stejný princip jako `v03_layer_d_draft.json` (viz `doc/PLAN.md` Krok 3b).
* `document_relations_review_queue.json` — nenapárované položky ze `document_relations.json` (neznámý `identifier` nebo `relation_type`) vyžadující lidskou kontrolu (generuje `load_document_relations.py`).
