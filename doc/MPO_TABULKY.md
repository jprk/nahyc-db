# Tabulky předpisů MPO a CDV jako zlatá sada

Stav k 19. 11. 2026 (větev `feature/mpo-krok1`). Dokument popisuje, jak jsme
porovnali obě tabulky předpisů, jež Ministerstvo průmyslu a obchodu (MPO) zaslalo
22. 5. 2026, s živou databází `h2regdocs`, jak chybějící předpisy vkládáme do
fronty kandidátů a jak pokrytí tabulek hlídá automatický test. Navazuje na
odstavce 2.1 a 4.2 dokumentu `doc/MPO_PRIPOMINKY.md`.

## 1. Podklady a jejich strojový tvar

Obě tabulky jsou uloženy beze změny v adresáři `data/20260430_MPO/raw/`:

* `Předpisy CZ - vodík_MPO.xlsx` (dále „tabulka MPO“) — 50 řádků, z toho
  43 řádků s českými právními předpisy a 7 řádků s normami ČSN;
* `CDV - evropské právní předpisy_v01.xlsx` (dále „tabulka CDV“) — 40 řádků
  s předpisy EU, mezinárodními úmluvami, normami a technickými komisemi.

Skript `src/tools/mpo_tables.py` je převádí do souboru
`data/20260430_MPO/mpo_tables.json`. Každý řádek má identifikátor složený
z tabulky a čísla řádku v listu (`MPO-03`, `CDV-21`), obsah buněk, příznak
žlutého označení („databáze předpis již obsahuje“) a klíče předpisů, jež
řádek uvádí. Klíče jsou tytéž, jaké používá kontrola úplnosti uzávěrem citací
(`doc/CITATION_CLOSURE.md`) a fronta kandidátů: `CZ:349/2015` pro český
předpis, `EU:2024/1679` pro akt EU bez ohledu na pořadí roku a čísla
v zápisu, `NORM:EN ISO 11114` pro normu bez národní předpony.

Řádky, u nichž klíč z čísla předpisu odvodit nelze, rozhoduje ručně
udržovaný soubor `data/20260430_MPO/mpo_decisions.json`: řádky bez čísla
(AFIR, TEN-T, balíček pro trh s plynem), dokumenty bez označení (ADR, RID,
pokyny IMO), zjevné překlepy v čísle předpisu a technické komise, jež
dokumenty nejsou. U každého rozhodnutí je uveden důvod.

## 2. Porovnání s databází

Výsledek porovnání s živou databází je v souboru
`data/20260430_MPO/mpo_coverage.json`. Normy párujeme jen se stejným národním
převzetím (ČSN ISO 14687 s dokumentem ČSN ISO 14687, nikoli s ISO 14687 nebo
STN ISO 14687); řádek, jenž uvádí celou řadu norem (ČSN EN 60079), pokrývá
kterákoli její část.

| Tabulka | Řádků | V databázi | Ve frontě kandidátů | S důvodem, proč chybí |
|---|---|---|---|---|
| MPO | 50 | 21 | 29 | 0 |
| CDV | 40 | 30 | 2 | 8 |
| celkem | 90 | 51 | 31 | 8 |

### 2.1 Tabulka MPO

* **V databázi je 21 řádků:** 13 řádků s 12 právními předpisy (zákon
  č. 250/2021 Sb. je uveden dvakrát, v řádcích MPO-28 a MPO-39), řádek MPO-42
  (viz níže) a všech 7 řádků s normami ČSN.
* **Ve frontě kandidátů je 29 řádků.** Tři předpisy již ve frontě byly
  z uzávěru citací (108/2011 Sb., 345/2002 Sb., 586/1992 Sb.); řádky MPO
  jsme jim doplnili do podkladů, zdroj kandidáta se nemění. Zbylých 26 řádků
  a dva další předpisy (viz níže) vkládáme do fronty nově.
* Žlutě označilo MPO jen 6 řádků (458/2000 Sb., 133/1985 Sb., 250/2021 Sb.,
  ČSN ISO 14687, ČSN ISO 19880-1, ČSN EN 17127); databáze však obsahuje
  i dalších 9 předpisů a 4 normy z tabulky, jež žlutě označeny nejsou,
  a nařízení vlády č. 192/2022 Sb. z řádku MPO-42.

Při dohledávání autoritativních názvů jsme narazili na čtyři nesrovnalosti
mezi číslem a názvem předpisu v tabulce MPO:

1. **MPO-27, „277/2015 Sb.“:** Pod tímto číslem je vyhlášena vyhláška
   o náhradě za bolest příslušníků bezpečnostních sborů. Název v tabulce
   („o náležitostech bezpečnostní dokumentace a rozsahu informací poskytovaných
   zpracovateli posudku“) doslova odpovídá vyhlášce č. 227/2015 Sb.,
   prováděcímu předpisu zákona o prevenci závažných havárií. Kandidátem je
   proto vyhláška č. 227/2015 Sb.
2. **MPO-42, „191/2022 Sb.“:** Číslo patří nařízení vlády o vyhrazených
   technických plynových zařízeních, název v tabulce („o vyhrazených tlakových
   zařízeních“) nařízení vlády č. 192/2022 Sb. To databáze již obsahuje
   (#1214); nařízení č. 191/2022 Sb. se vodíkových zařízení týká také,
   a je proto kandidátem.
3. **MPO-06, 513/2021 Sb.:** Vyhláška jen novelizovala vyhlášku č. 262/2015 Sb.
   o regulačním výkaznictví, kterou k 1. 1. 2026 zrušila vyhláška
   č. 508/2025 Sb. Podle zakonyprolidi.cz je vyhláška č. 513/2021 Sb. zrušená.
   Kandidáty jsou obě, editor patrně přijme jen platnou vyhlášku č. 508/2025 Sb.
4. **MPO-43, 146/2024 Sb.:** Vyhláška o požadavcích na výstavbu je podle
   zakonyprolidi.cz zrušena k 1. 1. 2027 předpisem č. 215/2026 Sb. Kandidátem
   zůstává, editor by měl zvážit i nový předpis.

K normám ČSN:

* **MPO-47, ČSN ISO 19880-1:** Databáze vede normu pod označením
  ČSN EN ISO 19880-1 (#3). Katalog České agentury pro standardizaci (ČAS)
  takové označení nezná; platné české převzetí je ČSN ISO 19880-1 (vydáno
  v srpnu 2025). Označení dokumentu je třeba opravit.
* **MPO-48 a MPO-49, řady ČSN EN 60079 a ČSN EN 13445:** Z řad jsou v databázi
  jen ČSN EN IEC 60079-0 a ČSN EN 13445-5+A1. V jiném národním převzetí
  (STN, DIN) má databáze desítky dalších částí obou řad.
* **MPO-50, ČSN EN ISO 11114:** V databázi je část 1. Kompatibilitu materiálů
  s vodíkem, jak řádek popisuje, řeší část 4, která je v databázi jen jako
  ISO 11114-4 a STN EN ISO 11114-4. Kandidátem je proto ČSN EN ISO 11114-4.

### 2.2 Tabulka CDV

* **V databázi je 30 řádků**, z toho 25 žlutě označených a 5 neoznačených:
  nařízení (ES) č. 79/2009 (#1228, zrušené), AFIR (EU) 2023/1804, akt
  v přenesené pravomoci (EU) 2023/1184, balíček pro dekarbonizaci trhu s plynem
  (směrnice (EU) 2024/1788 a nařízení (EU) 2024/1789, vedené jednotlivě)
  a norma ISO 19880-3:2018.
* **Ve frontě kandidátů jsou 2 řádky:** nařízení TEN-T, ověřené v EUR-Lexu jako
  nařízení (EU) 2024/1679 o hlavních směrech Unie pro rozvoj transevropské
  dopravní sítě, a akt v přenesené pravomoci (EU) 2025/2359 o metodice pro
  nízkouhlíková paliva.
* **S důvodem je 8 řádků:** sedm technických komisí (ISO/TC 22, ISO/TC 193,
  ISO/TC 268, IEC/TC 105, CEN/TC 234, CEN/TC 235, CEN/TC 268) a souhrnná
  položka „UNECE předpisy (WP.29)“. Tyto řádky nejsou dokumenty; u komisí
  uvádíme, které jejich normy databáze obsahuje.

Porovnání potvrdilo i nesrovnalosti, jež tabulka CDV sdílí s databází:
řádek CDV-13 spojuje označení (EU) č. 1302/2014 s názvem prováděcího nařízení
(EU) 2019/776 (stejně jako dokument #130), řádek CDV-26 uvádí u směrnice
Seveso III 2012/18/EU název směrnice ATEX 2014/34/EU a záznam #140, jenž
odpovídá řádku CDV-05 („UNECE Regulation No. 100“), má název publikace EIGA
o vodíkových lahvích.

## 3. Kandidáti ze zdroje „MPO/CDV 30. 4. 2026“

Chybějící předpisy vkládá do fronty kandidátů (`/admin/candidates`) příkaz
`src/tools/mpo_tables.py import --apply` jako zdroj `mpo` s popisem
„MPO/CDV 30. 4. 2026“. Jde o 34 kandidátů: 31 nových (28 českých předpisů,
2 akty EU a norma ČSN EN ISO 11114-4) a 3 kandidáti z uzávěru citací, jimž
doplňujeme řádky tabulky do podkladů.

Autoritativní údaje dohledává příkaz `src/tools/mpo_tables.py lookup` a ukládá
je do `data/20260430_MPO/mpo_candidates.json`, takže samotný import síť
nepotřebuje:

* české předpisy — úřední název ze zakonyprolidi.cz (`src/sites/zakonyprolidi.py`),
  ověření citace a adresa v e-Sbírce (`src/sites/esbirka.py`), platnost
  z otevřených dat e-Sbírky (`src/tools/check_validity.py`); adresou kandidáta
  je stránka na zakonyprolidi.cz, odkud se stahuje plný text;
* akty EU — český název a platnost z Cellaru (`src/sites/eurlex.py`,
  `check_validity.py`), adresa v EUR-Lexu;
* norma ČSN — název, platnost a stránka normy z katalogu ČAS
  (`src/tools/check_csn_validity.py`).

Kandidát nese navrženého původce podle sloupce „Nositel“ tabulky MPO
(nový sloupec `DocumentCandidate.puvodce`) a návrh věcného okruhu podle
poznámky (zásobníky plynu a těžba → skladování, bezpečnost → bezpečnost,
ERÚ a energetika → energetika). Editor oba údaje při návrhu přijetí potvrdí
nebo změní. Nově se tak objevují původci Energetický regulační úřad
(6 kandidátů) a Český báňský úřad (6 kandidátů). Do tabulky `DocumentSource`
je zapisuje až přijetí prvního takového kandidáta, aby veřejný filtr původců
nenabízel instituci, k níž není žádný dokument. Akty EU původce nemají;
doplní jej po přijetí `src/tools/backfill_eu_gestor.py`.

## 4. Automatický test zlaté sady

Test `tests/test_mpo_golden.py` běží nad testovací databází `h2regdocs_test`
v rámci `src/tools/run_tests.py` a ověřuje, že každý z 90 řádků je:

1. dokumentem databáze — u řádků, jež `mpo_coverage.json` vede jako
   „v databázi“; nenalezený dokument znamená, že se z databáze ztratil;
2. kandidátem ve frontě nebo dokumentem, jenž z přijatého kandidáta vznikl;
3. nebo má v `mpo_decisions.json` uveden důvod.

Protože se testovací databáze obnovuje kopií živé, test si kandidáty
z `mpo_candidates.json` nejdřív sám vloží (bez sítě) a na konci je odebere;
po importu do živé databáze už nic nevkládá. Soulad commitnutých souborů
s tabulkami a s pravidly párování ověřují unit testy `tests/test_mpo_tables.py`.

## 5. Otevřené otázky

* **Řady norem ČSN EN 60079 a ČSN EN 13445:** Které další části doplnit?
  Navrhujeme ty, jež databáze již má v jiném národním převzetí, u řady 60079
  přednostně části 10-1 (určování prostorů s plynnou výbušnou atmosférou),
  14 a 17.
* **MPO-27 a MPO-42:** Potvrdit u MPO, že řádky míní vyhlášku č. 227/2015 Sb.
  a nařízení vlády č. 192/2022 Sb., případně i č. 191/2022 Sb.
* **Původce nařízení vlády č. 191/2022 Sb.:** Tabulka MPO uvádí MPO; nařízení
  provádí zákon č. 250/2021 Sb., u něhož jsme původce v kroku 0 opravili na
  MPSV. Původce je vhodné ověřit při posouzení kandidáta.
* **Technické komise:** Vysvětlit MPO, že ISO/TC, IEC/TC a CEN/TC nejsou
  dokumenty, a nabídnout přehled norem, jež tyto komise vydaly a jež databáze
  obsahuje.
* **Označení ČSN EN ISO 19880-1 (#3):** Opravit na ČSN ISO 19880-1
  (pokračování kroku 0).
