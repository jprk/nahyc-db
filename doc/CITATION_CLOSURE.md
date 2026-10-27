# Uzávěr citací — první měření úplnosti

> Historie dokumentu:  
> 2026-10-27 první měření nad živou databází `h2regdocs`  
> 2026-10-27 rozlišení platnosti (odstavec 6)

Dokument popisuje první z kontrol úplnosti, které stanovuje odstavec 7 dokumentu
`doc/DATABASE_SCOPE.md`: **uzávěr citací**. Zjišťujeme, které předpisy, akty EU
a normy citují texty uložené v databázi, a kolik z nich databáze sama obsahuje.
Měření provádí skript `src/tools/citation_closure.py`; jeho úplný výstup je
v souboru `data/citation_closure.json` (není součástí repozitáře, lze jej kdykoli
znovu vytvořit) a kandidáti k posouzení v `data/citation_closure_candidates.csv`.

## 1. Postup

1. Ze všech čistých plných textů (`data/fulltext_clean/`) dokumentů v databázi
   vybíráme citace českých předpisů (`N/RRRR Sb.`), mezinárodních smluv
   (`N/RRRR Sb. m. s.`), slovenských předpisů (`N/RRRR Z. z.`), aktů EU
   (`(EU) 2019/943`, `(ES) č. 1907/2006`, `2012/18/EU` aj.) a norem
   (`ČSN EN ISO 19880-1`, `IEC 60079-10-1`).
2. Každou citaci převádíme na klíč nezávislý na způsobu zápisu: akt EU na rok
   a pořadové číslo (bez ohledu na to, zda je zapsán číslovacím systémem před
   rokem 2015, nebo po něm), normu na mezinárodní označení bez národní předpony
   (ČSN EN 17124 a EN 17124 tedy mají týž klíč).
3. Stejným postupem získáváme klíče dokumentů v databázi (z jejich označení,
   u dokumentů bez označení z prvního citovaného aktu v názvu) a citace s nimi
   porovnáváme. Dokument a jeho jazyková varianta (`… [EN]`) se počítají jako
   jeden citující dokument; citace dokumentu sebe sama se nepočítá.
4. Citace, jež stojí v seznamu novelizujících předpisů („ve znění zákona
   č. …“, „Přechodná ustanovení zavedena zákonem č. …“ a navazující výčty),
   označujeme jako **novelizační**: takový předpis je citován kvůli historii
   znění, ne kvůli obsahu.

Samotná citace o věcné příslušnosti mnoho neříká: konsolidované znění českého
zákona cituje desítky obecných předpisů (správní řád, zákon o obcích). Výsledkem
proto není verdikt, ale **pořadí kandidátů podle počtu citujících dokumentů**;
předpis citovaný mnoha dokumenty databáze do ní s větší pravděpodobností patří.

## 2. Výsledky (27. 10. 2026)

Databáze obsahuje 1488 dokumentů, z nichž 257 má čistý plný text (normy plný
text nemají, viz požadavek R4.1). Tyto texty citují celkem 4039 různých dokumentů.

Tabulka uvádí, kolik z citovaných dokumentů databáze obsahuje, a to pro skupiny
dokumentů citovaných alespoň *k* citujícími dokumenty; novelizační citace jsou
vyloučeny.

| Skupina | k ≥ 1 | k ≥ 2 | k ≥ 3 | k ≥ 5 |
|---|---|---|---|---|
| české předpisy | 20 / 406 | 18 / 124 | 17 / 81 | 15 / 46 |
| akty EU | 127 / 1094 | 90 / 548 | 68 / 360 | 40 / 192 |
| normy | 80 / 493 | 61 / 246 | 11 / 36 | 3 / 7 |
| slovenské předpisy | 3 / 221 | 2 / 120 | 0 / 89 | 0 / 12 |
| mezinárodní smlouvy (Sb. m. s.) | 0 / 12 | — | — | — |

Bez vyloučení novelizačních citací by české předpisy vycházely 35 / 1584 (k ≥ 1)
a 22 / 151 (k ≥ 5); více než polovina chybějících českých předpisů citovaných
alespoň třikrát (271 z 335) je citována převážně jako novela.

Nejčastěji citované dokumenty, které databáze neobsahuje (bez novelizačních citací):

* **České předpisy:** správní řád (500/2004 Sb., 12 citujících dokumentů),
  zákon o obcích (128/2000 Sb., 11), dřívější stavební zákon (50/1976 Sb., 11),
  zákon o cenách (526/1990 Sb., 9), dřívější zákon o odpadech (185/2001 Sb., 8),
  **zákon o metrologii** (505/1990 Sb., 8), autorizace architektů a inženýrů
  (360/1992 Sb., 7), **zákon o silničním provozu** (361/2000 Sb., 7).
* **Akty EU:** komitologie (rozhodnutí 1999/468/ES, 31; nařízení (EU)
  č. 182/2011, 27), **jakost benzinu a nafty** (směrnice 98/70/ES, 28),
  informační procedura pro technické předpisy (směrnice 98/34/ES, 26),
  **přístup k plynárenským přepravním soustavám** (nařízení (ES) č. 715/2009, 25),
  **rámcová směrnice BOZP** (89/391/EHS, 22) a skupina dřívějších směrnic
  nového přístupu (94/9/ES ATEX, 97/23/ES tlaková zařízení, 89/686/EHS osobní
  ochranné prostředky), dnes nahrazených.
* **Normy:** ISO/IEC 17025 (11), EN 590 a EN 228 (jakost paliv, 7 a 6),
  EN 62196-2 a -3 (dobíjecí konektory, 7 a 4), EN ISO 20519, ISO 7225
  (výstražné značky na plynových lahvích).

## 3. Co z výsledků vyplývá

1. **Uzávěr je nízký, ale to samo o sobě úplnost nevyvrací.** Velkou část
   chybějících dokumentů tvoří předpisy zjevně mimo rozsah (správní řád,
   ozbrojené síly, lesní zákon) a dokumenty **již zrušené nebo nahrazené**
   (185/2001 Sb. nahrazený zákonem 541/2020 Sb., směrnice 94/9/ES nahrazená
   směrnicí 2014/34/EU, 96/61/ES nahrazená směrnicí 2010/75/EU). Citace v textech
   zachycují stav v době jejich přijetí.
2. **Mezi kandidáty jsou dokumenty, které do rozsahu patrně patří.** Zákon
   o metrologii a silničním provozu (okruhy 4 a 5), směrnice o jakosti paliv,
   nařízení o přístupu k plynárenským soustavám (okruh 9), rámcová směrnice BOZP
   (okruh 7) a normy o jakosti paliv a o tlakových lahvích.
3. **Slovenské předpisy** vycházejí velmi nízko, ale jejich úplnost dokument
   rozsahu negarantuje (úroveň B).

## 4. Omezení měření

* Citující základ tvoří jen dokumenty s plným textem (257 z 1488), převážně
  zákony a akty EU; normy a dokumenty bez textu citace nepřinášejí.
* Rozpoznání novelizačních citací je heuristické; dlouhé výčty bez úvodní
  fráze mohou zůstat neoznačené.
* Klíč aktu EU nerozlišuje druh aktu (nařízení, směrnice, rozhodnutí); shoda
  roku a čísla u různých druhů je vzácná, ale možná.
* Normy jsou rozpoznávány jen podle označení EN, ISO a IEC; normy DIN, ASME
  a podobné zachyceny nejsou.

## 5. Další kroky

1. **Rozlišení platnosti.** Pro akty EU zjistit z Cellaru, zda jsou v platnosti
   a čím byly nahrazeny; pro české předpisy totéž z e-Sbírky. Tím se od
   kandidátů oddělí zrušené dokumenty a databáze získá vazbu na jejich
   nástupce (stavy podle odstavce 5 dokumentu rozsahu).
2. **Posouzení kandidátů.** Soubor `data/citation_closure_candidates.csv`
   obsahuje 867 chybějících dokumentů citovaných alespoň dvěma dokumenty
   (bez novelizačních citací) s kontextem první citace a prázdným sloupcem
   `rozhodnuti` (v rozsahu / mimo rozsah / zrušený). Po kroku 1 se seznam
   patrně výrazně zkrátí.
3. **Opakování měření** po doplnění dokumentů; poměry v tabulce odstavce 2
   slouží jako výchozí stav pro srovnání.

## 6. Platnost citovaných a uložených předpisů

Platnost zjišťuje skript `src/tools/check_validity.py`; výsledky ukládá do
`data/validity_cache.json` (s datem kontroly, aby se při dalším běhu ověřovalo
jen to, co je starší než zvolená lhůta) a doplňuje je jako sloupce `platnost`,
`konec` a `zruseno_predpisem` do souboru kandidátů.

* **Akty EU:** veřejný SPARQL koncový bod Cellar — příznak „v platnosti“, datum
  konce platnosti a akty, které daný akt zrušily. Akt se dohledává podle čísla
  CELEX; není-li druh aktu znám (nařízení, směrnice, rozhodnutí), zkoušíme
  všechny tři a výsledek přijímáme jen tehdy, existuje-li právě jeden.
* **České předpisy:** otevřená data e-Sbírky — konec účinnosti posledního
  konsolidovaného znění a počátek účinnosti prvního. Předpis, který daný předpis
  zrušil, otevřená data e-Sbírky neobsahují; přebíráme jej ze stránky předpisu na
  zakonyprolidi.cz („Zrušeno k … (N/RRRR Sb.)“).

Kontrolovali jsme 747 předpisů: kandidáty z odstavce 5 (české předpisy a akty EU)
a všechny české předpisy a akty EU v databázi. Normy zatím nekontrolujeme;
veřejný strojově čitelný zdroj jejich platnosti nemáme.

### 6.1 Kandidáti

Z 564 kandidátů (české předpisy a akty EU citované alespoň dvěma dokumenty, ne
převážně jako novela) je:

| Stav | České předpisy | Akty EU | Celkem |
|---|---|---|---|
| účinný | 69 | 216 | 285 |
| zrušený | 37 | 239 | 276 |
| nezjištěno | 0 | 3 | 3 |

U 110 zrušených kandidátů databáze již obsahuje předpis, který je zrušil
(například směrnice 94/9/ES → 2014/34/EU, nařízení (ES) č. 715/2009 →
(EU) 2024/1789, zákon 50/1976 Sb. → 183/2006 Sb.). Nezjištěny zůstaly tři akty,
které nejsou nařízením, směrnicí ani rozhodnutím (například doporučení Komise
2003/361/ES o definici malých a středních podniků).

Uzávěr citací omezený na **účinné** předpisy (bez novelizačních citací):

| Skupina | k ≥ 2 | k ≥ 3 | k ≥ 5 |
|---|---|---|---|
| české předpisy | 15 / 84 | 14 / 57 | 13 / 35 |
| akty EU | 72 / 288 | 54 / 186 | 26 / 91 |

K ručnímu posouzení tak zbývá 285 účinných kandidátů, z toho 87 citovaných
alespoň pěti dokumenty. Nejčastěji citované účinné akty, které databáze nemá:
směrnice 98/70/ES o jakosti paliv (28 citujících dokumentů), nařízení (EU)
č. 182/2011 o komitologii (27), rámcová směrnice BOZP 89/391/EHS (22), nařízení
(EU) č. 1025/2012 o evropské normalizaci (16), směrnice 2003/87/ES o obchodování
s povolenkami (15), nařízení (ES) č. 715/2007 o schvalování typu vozidel z hlediska
emisí (13), směrnice 2013/30/EU o bezpečnosti těžby ropy a zemního plynu
v moři (13), dále směrnice o elektřině (EU) 2019/944 a nařízení (EU) 2019/943,
evropský klimatický zákon (EU) 2021/1119 a z českých předpisů správní řád,
zákon o obcích a zákon o cenách.

### 6.2 Předpisy v databázi

Z 183 českých předpisů a aktů EU, které databáze obsahuje, je **34 zrušených**
(146 účinných, 3 nezjištěné). Databáze je dnes vede bez rozlišení stavu.

* U 18 z nich databáze obsahuje i předpis, který je zrušil (například stavební
  zákon 183/2006 Sb. → 283/2021 Sb., směrnice 2009/73/ES a (EU) 2019/692 →
  (EU) 2024/1788, směrnice 2014/94/EU → nařízení (EU) 2023/1804 AFIR,
  nařízení vlády 133/2005 Sb. → 426/2021 Sb.).
* U 8 z nich nástupce v databázi chybí: zákon 133/2010 Sb. → 516/2020 Sb.,
  směrnice 2012/27/EU → (EU) 2023/1791 (energetická účinnost), rozhodnutí
  2000/96/ES a 2002/253/ES → prováděcí rozhodnutí (EU) 2018/945, rozhodnutí
  2009/177/ES → (EU) 2021/620, rozhodnutí 1998/2119/ES → 1082/2013/EU,
  nařízení (EU) č. 559/2014 → (EU) 2021/2085 a nařízení (EU) č. 1305/2014 →
  (EU) 2026/253.
* U 8 z nich Cellar nástupce neuvádí (rozhodnutí 2007/875/ES, 2008/426/ES,
  2009/312/ES, 2009/539/ES, 2009/540/ES, 2009/547/ES, směrnice 2014/106/EU,
  nařízení (EU) č. 630/2012); jde o akty, jejichž platnost uplynula nebo byla
  ukončena bez přímé náhrady.

### 6.3 Doporučení

1. **Stavy dokumentů v databázi.** Označit 34 zrušených předpisů jako zrušené
   s vazbou na nástupce (vazba `REPEALS`); stavy jsou rozšířeny
   (`src/tools/backfill_document_states.py`, 27. 10. 2026): 35 aktuálních verzí
   (34 předpisů a jedna jazyková varianta) a 20 vazeb `REPEALS`.
2. **Chybějící nástupci.** Doplnit 8 předpisů, které zrušily předpisy
   v databázi, pokud do rozsahu patří.
3. **Účinní kandidáti.** Ručně posoudit 285 účinných kandidátů v souboru
   kandidátů (sloupec `rozhodnuti`), nejdříve 87 citovaných alespoň pěti
   dokumenty; zrušené kandidáty lze při posuzování přeskočit.
4. **Pravidelná kontrola.** `check_validity.py` spouštět s četností podle
   odstavce 6 dokumentu rozsahu (registry předpisů týdně); mezipaměť zajistí,
   že se dotazy opakují jen pro starší záznamy.

