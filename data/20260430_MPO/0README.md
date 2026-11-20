# Adresář /data/20260430_MPO

Tabulky předpisů, které Ministerstvo průmyslu a obchodu (MPO) zaslalo e-mailem
22. 5. 2026 jako přílohu připomínek k výsledku V01 (`doc/MPO_PRIPOMINKY.md`,
odstavec 2.1). Obě tabulky jsou datovány 30. 4. 2026 a slouží jako první zlatá
sada databáze (`doc/MPO_TABULKY.md`).

## Soubory

* `raw/` — původní tabulky tak, jak přišly (viz `raw/0README.md`).
* `mpo_tables.json` — řádky obou tabulek ve strojovém tvaru: buňky řádku, žluté
  označení („v databázi již je“) a klíče předpisů nebo norem, jež řádek uvádí.
  Vytváří `src/tools/mpo_tables.py convert`.
* `mpo_decisions.json` — ruční rozhodnutí k řádkům, která nelze odvodit pravidlem:
  klíče řádků bez čísla předpisu (AFIR, TEN-T, balíček pro trh s plynem), dokumenty
  bez klíče (ADR, RID, IMO), opravy zjevných překlepů v čísle (277/2015 Sb. →
  227/2015 Sb.), důvody, proč řádek není dokumentem (technické komise), další
  kandidáty, jež z řádku vyplývají (novely LEX OZE, části řad norem), a poznámky.
  Oddíl `_candidates` nese údaje ke kandidátům, jež z řádku převzít nelze
  (původce, příznak novely a klíče novelizovaných předpisů, zkratka).
* `mpo_coverage.json` — výsledek porovnání každého řádku s živou databází
  (`src/tools/mpo_tables.py compare`): v databázi, ve frontě kandidátů, nebo
  s důvodem. Je to zároveň očekávaný stav, který hlídá test
  `tests/test_mpo_golden.py`.
* `mpo_candidates.json` — kandidáti ze zdroje „MPO/CDV 30. 4. 2026“ s autoritativním
  názvem, adresou, platností a navrženým původcem (`src/tools/mpo_tables.py lookup`);
  do fronty je vkládá `src/tools/mpo_tables.py import --apply`.
