# Tabulky předpisů MPO a CDV jako zlatá sada

Stav k 19.11.2026 (větve `feature/mpo-krok1` a `feature/mpo-kandidati-doplnit`). Dokument popisuje, jak jsme
porovnali obě tabulky předpisů, jež Ministerstvo průmyslu a obchodu (MPO) zaslalo
22.05.2026, s živou databází `h2regdocs`, jak chybějící předpisy vkládáme do
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
dokumenty nejsou. U každého rozhodnutí je uveden důvod. Oddíl `_candidates`
téhož souboru nese údaje ke kandidátům, jež z řádku tabulky převzít nelze:
navrženého původce tam, kde sloupec „Nositel“ neodpovídá (nařízení vlády
č. 191/2022 Sb.), příznak novely s klíči novelizovaných předpisů a zkratku,
pod níž se předpis běžně uvádí (LEX OZE I–III).

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
   a je proto kandidátem. Jeho původcem je podle rozhodnutí z 19.11.2026
   Ministerstvo práce a sociálních věcí (nařízení provádí zákon č. 250/2021 Sb.),
   nikoli MPO ze sloupce „Nositel“.
3. **MPO-06, 513/2021 Sb.:** Vyhláška jen novelizovala vyhlášku č. 262/2015 Sb.
   o regulačním výkaznictví, kterou k 01.01.2026 zrušila vyhláška
   č. 508/2025 Sb. Podle zakonyprolidi.cz je vyhláška č. 513/2021 Sb. zrušená.
   Kandidáty jsou obě, editor patrně přijme jen platnou vyhlášku č. 508/2025 Sb.
4. **MPO-43, 146/2024 Sb.:** Vyhláška o požadavcích na výstavbu je podle
   zakonyprolidi.cz zrušena k 01.01.2027 předpisem č. 215/2026 Sb. Kandidátem
   zůstává, editor by měl zvážit i nový předpis.

K normám ČSN:

* **MPO-47, ČSN ISO 19880-1:** Databáze vede normu pod označením
  ČSN EN ISO 19880-1 (#3). Katalog České agentury pro standardizaci (ČAS)
  takové označení nezná; platné české převzetí je ČSN ISO 19880-1 (vydáno
  v srpnu 2025). Označení dokumentu je třeba opravit.
* **MPO-48 a MPO-49, řady ČSN EN 60079 a ČSN EN 13445:** Z řad jsou v databázi
  jen ČSN EN IEC 60079-0 a ČSN EN 13445-5+A1. V jiném národním převzetí
  (STN, DIN) má databáze desítky dalších částí obou řad. Další české části
  jsou od 19.11.2026 kandidáty (odstavec 3.1).
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

## 3. Kandidáti ze zdroje „MPO/CDV 30.04.2026“

Chybějící předpisy vkládá do fronty kandidátů (`/admin/candidates`) příkaz
`src/tools/mpo_tables.py import --apply` jako zdroj `mpo` s popisem
„MPO/CDV 30.04.2026“. Jde o 57 kandidátů: 54 nových a 3 kandidáti z uzávěru
citací, jimž doplňujeme řádky tabulky do podkladů. Nové kandidáty tvoří
31 českých předpisů (28 z řádků tabulky a tři novely LEX OZE, odstavec 3.1),
2 akty EU a 21 norem ČSN (ČSN EN ISO 11114-4 a 20 částí řad ČSN EN 60079
a ČSN EN 13445, odstavec 3.1).

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
(nový sloupec `DocumentCandidate.puvodce`), není-li v `_candidates` uveden jiný, a návrh věcného okruhu podle
poznámky (zásobníky plynu a těžba → skladování, bezpečnost → bezpečnost,
ERÚ a energetika → energetika). Editor oba údaje při návrhu přijetí potvrdí
nebo změní. Nově se tak objevují původci Energetický regulační úřad
(6 kandidátů) a Český báňský úřad (6 kandidátů). Do tabulky `DocumentSource`
je zapisuje až přijetí prvního takového kandidáta, aby veřejný filtr původců
nenabízel instituci, k níž není žádný dokument. Akty EU původce nemají;
doplní jej po přijetí `src/tools/backfill_eu_gestor.py`.

### 3.1 Kandidáti doplnění 19.11.2026

Na základě rozhodnutí z 19.11.2026 jsme frontu rozšířili o kandidáty, které
tabulky výslovně neuvádějí, ale které z jejich řádků vyplývají. Všichni jsou
zdrojem `mpo` a v podkladech nesou řádek, z něhož vyplývají; zvláštní zdroj
jsme nezakládali, protože by pouze rozdělil jeden podklad (tabulky MPO a jejich
vypořádání) do dvou položek filtru a zlatý test by je nehlídal.

**Novely LEX OZE.** Zkratky LEX OZE I–III uvádí MPO ve své prezentaci na
Konferenci energetiky a odpadového hospodářství 2025
(<https://www.smocr.cz/shared/clanky/15677/1_1_Rene_Nedela_MPO.pdf>).
Čísla, úřední názvy a části zákonů jsme ověřili na zakonyprolidi.cz, adresy
a platnost v e-Sbírce:

| Zkratka | Předpis | Účinnost od | Hlavní obsah | Novelizuje mimo jiné |
|---|---|---|---|---|
| LEX OZE I | zákon č. 19/2023 Sb. | 23.01.2023 | zjednodušení povolování obnovitelných zdrojů | 458/2000 Sb., 165/2012 Sb., 406/2000 Sb. |
| LEX OZE II | zákon č. 469/2023 Sb. | 31.12.2023 | komunitní energetika a sdílení elektřiny | 458/2000 Sb., 165/2012 Sb., 406/2000 Sb. |
| LEX OZE III | zákon č. 87/2025 Sb. | 31.03.2025 | akumulace, agregace a flexibilita | 458/2000 Sb., 165/2012 Sb., 406/2000 Sb., 586/1992 Sb. |

Všechny tři zákony mají shodný úřední název „Zákon, kterým se mění zákon
č. 458/2000 Sb., … (energetický zákon), ve znění pozdějších předpisů, a další
související zákony“; od sebe je odlišuje označení a zkratka v podkladech
(`evidence.alias`). Zkratka „LEX OZE IV“ se ve veřejných zdrojích nevyskytuje,
a proto ji nedoplňujeme. Kandidáti jsou řazeni k řádkům MPO-02 (energetický
zákon) a MPO-29 (zákon o podporovaných zdrojích energie), mají příznak novely
(`signal = amendment`), navrženého původce MPO a věcný okruh Energetika.

Vazbu AMENDS vytváří až přijetí kandidáta, a to z identifikátorů novelizovaných
dokumentů v `evidence.amends_ids` (stejně jako u novel, jež nalézají sledované
zdroje). Protože identifikátory dokumentů se mezi databázemi liší, ukládá
`mpo_candidates.json` jen klíče novelizovaných předpisů (`evidence.amends`)
a import je převádí na identifikátory dokumentů té databáze, do níž zapisuje.
V živé databázi jsou to energetický zákon (#72) a zákon o podporovaných zdrojích
energie (#66); zákony č. 406/2000 Sb. a 586/1992 Sb. jsou zatím jen kandidáty,
a vazba na ně proto zatím nevznikne.

**Další části řad ČSN EN 60079 a ČSN EN 13445.** Platné části jsme vyhledali
v katalogu ČAS (`src/tools/check_csn_validity.py`) a porovnali s živou
databází včetně různých zápisů označení (ČSN EN, ČSN EN IEC, ČSN EN ISO/IEC;
převzetí STN a DIN se za českou normu nepočítají). Označení kandidáta je bez
čísla vydání, aby odpovídalo zápisu v databázi; vydání a datum vydání uvádí
`evidence.edition` a `evidence.issued`. Je-li stejné označení v katalogu
vícekrát, vybíráme nejnovější platné vydání.

* Řada ČSN EN 60079 (13 kandidátů): části 1 (pevný závěr), 2 (přetlak),
  7 (zajištěné provedení), 10-1 (určování nebezpečných prostorů s plynnou
  atmosférou), 11 a 25 (jiskrová bezpečnost), 14 (návrh elektrické instalace),
  17 (prohlídky a údržba), 19 (opravy) a 29-0, 29-1, 29-2 (detektory plynů;
  část 29-0 vyšla v listopadu 2026 jako nová obecná norma pro detekci plynů).
  Části 10-1, 11, 14, 17, 19, 25 a 29-0 mají české označení ČSN EN IEC.
  Zrušenou ČSN EN 60079-20-1 nahradila ČSN EN ISO/IEC 80079-20-1, kterou
  databáze již má (#28).
* Řada ČSN EN 13445 (8 kandidátů): části 1, 2, 3, 4, 6, 8, 10 a 11; část 5
  již v databázi je. Části 7 a 9 jako ČSN nevyšly (část 9 je technická zpráva
  CEN/TR), část 12 je zatím návrh prEN. Katalog ČAS vede u všech částí nové
  vydání s datem vydání 01.12.2026 a datem účinnosti 01.01.2027. Kandidát
  nese vydání účinné v den kontroly (části 1, 6, 8, 10: 11/2021; část 11:
  2/2025; části 2, 3, 4: konsolidované vydání se změnou A1, označení
  `ČSN EN 13445-2+A1` atd.), nové vydání je v podkladech jako
  `upcoming_edition`. Po přijetí kandidáta má dokument obě vydání jako verze
  a 01.01.2027 se sám přepne na nové (`src/tools/norm_editions.py`,
  rozhodnutí z 20.11.2026). Z řady ČSN EN 60079 má budoucí účinnost jen
  nová ČSN EN IEC 60079-29-0 (účinná od 01.12.2026; kandidát „dosud
  neúčinný“).

## 4. Automatický test zlaté sady

Test `tests/test_mpo_golden.py` běží nad testovací databází `h2regdocs_test`
v rámci `src/tools/run_tests.py` a ověřuje, že každý z 90 řádků je:

1. dokumentem databáze — u řádků, jež `mpo_coverage.json` vede jako
   „v databázi“; nenalezený dokument znamená, že se z databáze ztratil;
2. kandidátem ve frontě nebo dokumentem, jenž z přijatého kandidáta vznikl;
3. nebo má v `mpo_decisions.json` uveden důvod.

Protože se testovací databáze obnovuje kopií živé, test si kandidáty
z `mpo_candidates.json` nejdřív sám vloží (bez sítě) a na konci je odebere;
po importu do živé databáze už nic nevkládá. Test dále ověřuje, že opakovaný
import nic nezmění, že novely LEX OZE nesou identifikátory novelizovaných
dokumentů a že původcem nařízení vlády č. 191/2022 Sb. je MPSV.

Import lze spouštět opakovaně. Kandidát zdroje `mpo`, o němž dosud nebylo
rozhodnuto (stav nový nebo odložený), dostane obnovené podklady, platnost
a navrženého původce; původce, jehož editor změnil, zůstává. Kandidát jiného
zdroje dostane jen řádky tabulky do podkladů. Kandidáta navrženého k přijetí,
přijatého nebo zamítnutého import nemění. Příkaz `lookup` se ptá sítě jen na
kandidáty, kteří v `mpo_candidates.json` dosud nejsou (`--refresh` znovu na
všechny). Soulad commitnutých souborů
s tabulkami a s pravidly párování ověřují unit testy `tests/test_mpo_tables.py`.

## 5. Otevřené otázky

* **MPO-27 a MPO-42 (odloženo, vyřešíme později):** Potvrdit u MPO, že řádky
  míní vyhlášku č. 227/2015 Sb. (nikoli č. 277/2015 Sb.) a nařízení vlády
  č. 192/2022 Sb., případně i č. 191/2022 Sb.
* **Technické komise:** Vysvětlit MPO, že ISO/TC, IEC/TC a CEN/TC nejsou
  dokumenty, a nabídnout přehled norem, jež tyto komise vydaly a jež databáze
  obsahuje.
* **Označení ČSN EN ISO 19880-1 (#3):** Opravit na ČSN ISO 19880-1
  (pokračování kroku 0).
* **Vazby novel LEX OZE na zákony č. 406/2000 Sb. a 586/1992 Sb.:** Vzniknou
  jen tehdy, budou-li tyto zákony přijaty jako dokumenty dříve než novely
  (import pak doplní jejich identifikátory); jinak je třeba vazbu doplnit ručně.
* **Vydání norem ČSN EN 13445 z 12/2026** (rozhodnuto 20.11.2026):
  kandidáti nesou dosavadní účinné vydání, na nové se databáze přepne dnem
  jeho účinnosti 01.01.2027 (odstavec 3.1).
