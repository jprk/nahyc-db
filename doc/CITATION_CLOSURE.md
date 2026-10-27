# Uzávěr citací — první měření úplnosti

> Historie dokumentu:  
> 2026-10-27 první měření nad živou databází `h2regdocs`

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
