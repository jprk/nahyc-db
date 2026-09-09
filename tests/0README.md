# Adresář /tests

Tento adresář obsahuje automatizované testy (unittest, stdlib — bez závislosti na pytestu). Spuštění celé sady: `.venv/bin/python -m unittest discover -s tests -p "test_*.py"` z kořene repozitáře.

## Obsah
* `test_search.py` - Testovací skript ověřující správnost fungování vyhledávání a deduplikace záznamů podle názvu ve Flask aplikaci (`app/app.py`), např. že zákon 458/2000 Sb. se po deduplikaci zobrazí v katalogu právě jednou. Vyžaduje běžící MariaDB (`h2regdocs`) a `.env` — jde o integrační test proti reálné databázi, ne izolovaný unit test.
* `test_build_unified_db.py` - Unit testy pro `extract_znacka_from_title()` (`src/tools/build_unified_db.py`) — pokrývají všechny vzory nalezené v reálných datech Haltuf/Sinay (viz `doc/PLAN.md` Step 1, follow-upy #3/#4/#6) i obě zde opravené regrese. Čisté, bez síťových volání.
* `test_deduplicate_db.py` - Unit testy pro klíčovou logiku `src/tools/deduplicate_db.py`: normalizaci značky, `validate_merge`, `is_pure_znacka_cluster`, `programmatic_merge`, `match_type_for_group`, `build_clusters` (na syntetických embeddingech, bez OpenAI), ověření proti registru ČSN online (`resolve_iso_csn_ambiguity`, s mockovaným vyhledáváním) a `deduplicate_cluster_with_llm` (s mockovaným OpenAI klientem — žádné reálné API volání).
