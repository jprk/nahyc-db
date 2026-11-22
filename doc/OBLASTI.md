# Oblasti katalogu

Stav k 22. 11. 2026. Filtr „Oblast“ v katalogu a štítky u dokumentů v seznamu a na stránce dokumentu
nově ukazují **oblasti**: 29 českých hodnot navázaných na věcné okruhy `doc/DATABASE_SCOPE.md`
(odstavec 3). Dosud v nich byla klíčová slova převzatá ze zdrojových rešerší.

## 1. Proč

Pole „Oblast (klíčové slovo)“ mělo v živé databázi 238 hodnot (3294 vazeb, 343 dokumentů bez hodnoty):

* **jazyky:** většina hodnot je německá (tabulka Sinay: „Explosionsschutz“ 247 dokumentů,
  „Schienenfahrzeuge“ 169, „Produktzertifizierung“ 124 …), část slovenská („STN (prijatá v sústave)“ 375,
  „Stav k 02/2025: v príprave“ 34) a anglická („Controls“);
* **nejde o oblasti:** vydavatelé („DIN - Deutsches Institut für Normung e.V.“, „ASTM …“, „EIGA …“,
  přes 40 hodnot), technické komise („Norm (ISO/TC 58/SC 3/WG 27)“, přes 100 hodnot, většinou s 1–5
  dokumenty), stavy normy („STN (zrušená bez náhrady)“), obecné hodnoty („EU“, „Norm“, „-“, „Information“);
* **duplicity a překlepy:** „Norm (IEC/TC 31)“ / „Norm (IEC/TC31)“, „Norm (ISO TC58 SC3)“ / „Norm (ISO/TC 58/SC 3)“,
  „DIN - Deutsches“ / „DIN - Deutsches Institut …“, „NACE - National“ / „NACE - National Association …“,
  „Palivové články“ / „3360 - Technologie palivových článků“ / „Brennstoffzelle“;
* **příliš podrobné:** třídy ČSN („4202 - Ingoty z ocelí. Tvářené výrobky z ocelí …“), pracovní skupiny komisí.

## 2. Nová sada oblastí

| Oblast | Kód | Okruh | Dokumentů |
|---|---|---|---|
| Výroba vodíku | `vyroba` | 1 | 80 |
| Obnovitelný a nízkouhlíkový vodík, certifikace | `rfnbo` | 1 | 30 |
| Tlakové nádoby a lahve | `tlakove-nadoby` | 2 | 186 |
| Zkapalněný vodík a kryogenní technika | `kryogenika` | 2 | 172 |
| Podzemní zásobníky | `podzemni-zasobniky` | 2 | 114 |
| Plynovody a plynárenské sítě | `site` | 3 | 179 |
| Přeprava nebezpečných věcí | `preprava-nv` | 3 | 17 |
| Plnicí stanice a infrastruktura paliv | `plnici-stanice` | 4 | 94 |
| Kvalita vodíku, měření a metrologie | `kvalita-mereni` | 4 | 153 |
| Silniční a speciální vozidla | `silnicni-vozidla` | 5 | 256 |
| Železnice a kolejová vozidla | `kolejova-vozidla` | 5 | 220 |
| Lodní a letecká doprava | `lode-letadla` | 5 | 55 |
| Palivové články | `palivove-clanky` | 6 | 75 |
| Průmyslové využití a Power-to-X | `prumysl` | 6 | 130 |
| Elektrárny, turbíny a tepelná zařízení | `energeticka-zarizeni` | 6 | 73 |
| Plynové spotřebiče v domácnostech a provozovnách | `spotrebice` | 6 | 48 |
| Ochrana před výbuchem | `vybuch` | 7 | 273 |
| Bezpečnost a prevence havárií | `bezpecnost` | 7 | 240 |
| Chemické látky a směsi | `chemicke-latky` | 7 | 22 |
| BOZP a odborná způsobilost | `bozp` | 7 | 73 |
| Materiály a jejich zkoušení | `materialy` | 7 | 317 |
| Komponenty, armatury a potrubí | `komponenty` | 7 | 281 |
| Řídicí systémy a kybernetická bezpečnost | `rizeni-kyber` | 7 | 94 |
| Posuzování shody a certifikace výrobků | `shoda-vyrobku` | 7 | 134 |
| Stavby, územní plánování a umístění | `stavby` | 8 | 17 |
| Energetika a trh s plynem a vodíkem | `energetika` | 9 | 76 |
| Životní prostředí, emise a klima | `zivotni-prostredi` | 10 | 139 |
| Strategie, koncepce a studie | `strategie` | — | 38 |
| Obecné a průřezové předpisy | `obecne` | — | 40 |

Počty jsou z dry runu `assign_areas.py` nad živou databází (1506 dokumentů, z toho 1466 s věcnou oblastí;
dokument může mít více oblastí). Rozpad podle původu: jen z původních klíčových slov 469 dokumentů, jen z názvu
407, z obojího 577, z typu (strategie, studie) 13, náhradní oblast 40.

## 3. Pravidla přiřazení (`data/areas.json`)

1. **Původní klíčová slova** — `keywords`: přesná hodnota → oblasti (všech 238 hodnot je buď zmapováno, nebo
   výslovně ignorováno; neznámou hodnotu vypíše `assign_areas.py` a hlídá `tests/test_areas.py`);
   `committee_rules`: označení technické komise v hodnotě (např. ISO/TC 58 a CEN/TC 23 → tlakové nádoby,
   IEC/TC 31 → ochrana před výbuchem, ISO/TC 22 → silniční vozidla); `ignore`: vydavatelé, stavy STN, obecné hodnoty.
   Názvy okruhů, které přidává přijetí kandidáta (`app/candidates_admin.py`), jsou zmapované také.
2. **Typ dokumentu** — `type_rules`: strategie a studie → „Strategie, koncepce a studie“.
3. **Název a označení** — `title_rules`: regulární výrazy v češtině, slovenštině, angličtině a němčině.
4. **Náhradní oblast** `obecne` dostane dokument, kterému žádné pravidlo nic nepřiřadilo; tyto dokumenty vypisuje
   `assign_areas.py --uncertain` jako nejisté. LLM se nepoužívá.

## 4. Co se stalo s klíčovými slovy

Původní klíčová slova se **nemažou**: zůstávají v tabulkách `Keyword` a `DocumentKeyword`, prohledává je
vyhledávání v katalogu (dotaz „Befüllungsanlagen“ dál najde příslušné normy) a obsahují je exporty CSV/JSON/XML.
Nejsou jen nabízena ve filtru ani zobrazena ve štítcích. Důvod: nesou informaci ze zdrojových rešerší (vydavatel,
technická komise, stav STN), kterou oblasti nenahrazují, a mapování se z nich dá kdykoli přepočítat. Starý odkaz
`?keyword_id=…` dál funguje.

Oblasti jsou v tabulkách `Area` (kód, název, okruh, pořadí) a `DocumentArea` (dokument, oblast, původ:
`keyword`, `type`, `title`, `fallback`). Dokud v databázi nejsou, aplikace ukazuje původní klíčová slova.

## 5. Údržba

* `src/tools/assign_areas.py` — dry run s rozpadem; `--apply` zapíše; `--uncertain` vypíše nejisté.
  Idempotentní; spustit po přestavbě databáze (`init_db.py`) a po změně `data/areas.json`.
* Přijetí kandidáta oblasti novému dokumentu přiřadí hned (`areas.assign_document()`).
* Test: `tests/test_areas.py` (soubor, pravidla, zápis), `tests/e2e/test_areas.py` (filtr, stránka dokumentu,
  hledání ve skrytých klíčových slovech). `run_tests.py` oblasti do testovací databáze zapisuje
  (`TEST_DB_MIGRATIONS`).

## 6. Nejisté přiřazení (40 dokumentů s náhradní oblastí)

Většinou předpisy mimo rozsah databáze, které do ní přišly ze seznamů EU předpisů (pracovní právo, rovné zacházení,
přenosné nemoci: 1999/70/ES, 2000/43/ES, 2000/78/ES, 2002/253/ES a jeho změny, 2003/88/ES, 2004/113/ES, 2006/54/ES,
2008/104/ES, 2010/32/EU, 2014/66/EU, 2018/957/EU, 2019/1152/EU, 2019/1158/EU, 2000/96/ES, 1998/2119/ES …), dále obecné
vodíkové dokumenty EIGA/CGA bez věcného zaměření (CGA G-5, EIGA DOC 15, DOC 247), záznamy s poškozeným názvem
(#385, #1077) a zákon o spotřebních daních, živnostenský zákon, ISO 17526 (lasery). Úplný seznam:
`assign_areas.py --uncertain`. Doporučení: předpisy mimo rozsah posoudit k vyřazení (`data/manual_corrections.json`,
`"exclude": true`), ostatním doplnit pravidlo nebo oblast ručně.
