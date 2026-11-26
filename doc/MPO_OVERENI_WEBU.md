# Ověření veřejného webu proti připomínkám MPO (interní)

> Historie dokumentu:  
> 2026-11-21 jprk Ověření https://nahyc.fd.cvut.cz/h2db/ po nasazení 20. 11. 2026  
> 2026-11-26 jprk Opakované ověření po nasazení 26. 11. 2026 (odstavec 4): závady Z1–Z5 opraveny

Interní záznam. Veřejnou verzi aplikace (https://nahyc.fd.cvut.cz/h2db/,
databáze aktualizována 2026-11-20 19:21) jsme 21. 11. 2026 prošli
v prohlížeči Chromium (Playwright) jen čtením (GET, bez přihlášení), jako
návštěvník. Snímky: `data/test_screenshots/20261121_125428_mpo_overeni/`
(`result.json` obsahuje zaznamenané texty stránek). Odstavce 1 až 3
zachycují stav 21. 11. 2026; opakované ověření po nasazení 26. 11. 2026
popisuje odstavec 4.

## 1. Výsledky po připomínkách

| # | Co jsme ověřili | Výsledek |
|---|---|---|
| — | Úvodní stránka | 1038 předpisů a norem, „z toho 857 aktuálně platných a 181 historických“ (viz závada Z1). |
| 1 | Jeden řádek na předpis, štítky jazyků | Splněno. Pod výsledky věta o jazykových verzích; RED III má štítky CS a EN. Dotaz `2018/546` (rozhodnutí ECB) vrací 0. |
| 2 | Dotaz „RFNBO“ | Splněno, ale jinak, než uváděl text z 19. 11.: 7 dokumentů, každý jednou — (EU) 2023/2413, 2023/1184, 2023/1185, 2018/2001 a tři strategie (COM(2021) 550, COM(2026) 370, Vnitrostátní plán). Poznámka o synonymu RFNBO se zobrazuje. Vypořádání opraveno. |
| 3 | Filtr podtypu aktů EU | Splněno. „Akt v přenesené pravomoci (EU)“: 5 (2023/1184, 2018/674, 2019/1745, 2023/1185, 2025/656); „Prováděcí akt (EU)“: 9, nikoli 11 (vypořádání opraveno). (EU) 2023/1185 má český název. |
| 4 | „MD“ × „Ministerstvo dopravy“ | Splněno; v nabídce institucí nejsou holé zkratky. |
| 5 | Zákon o dráhách, filtr institucí a jurisdikce | Splněno. 266/1994 Sb. i 426/2021 Sb.: gestor Ministerstvo dopravy. Nabídka institucí ve 4 skupinách (Česká republika, Evropská unie, Mezinárodní organizace, Normalizační a odborné organizace) — skupiny „Slovensko“ a „zahraniční státní orgány“, jež text z 19. 11. uváděl, se návštěvníkovi nezobrazují (vypořádání opraveno). Filtr jurisdikce: ČR 104, EU 217, mezinárodní 312, ostatní a neurčené 405. Výběr jurisdikce nabídku institucí nezužuje (text to netvrdí). |
| 6 | Energetický zákon bez zastaralé hlášky | Splněno; stránky 458/2000 Sb. a RED III hlášku neobsahují, hledání „Stav ke dni 30.6.2025“ vrací 0. |
| 7 | Připravované dokumenty | Splněno pro zobrazení: stav „připravovaný“ na stránce dokumentu (ISO 19885-2, návrh Politiky ochrany klimatu 2025–2050 s vazbou „má nahradit“). Návrhy předpisů z prvního sběru zatím jen ve frontě (nepřijaty). |
| 8 | Předpisy z tabulek MPO | Odpovídá stavu: např. 349/2015 Sb. ani další části ČSN EN 60079 v katalogu nejsou (kandidáti čekají na potvrzení editorem). |
| 9 | Strategie | Splněno: filtr „Strategie“ vrací 31 řádků (32 dokumentů; slovenské znění COM(2020) 301 jen jako jazyková verze). |
| 10 | Datum kontroly na stránce dokumentu | Splněno: „Poslední kontrola stavu 27. 10. 2026 (e-Sbírka)“ u 266/1994 Sb. a 458/2000 Sb., „5. 11. 2026 (Věstník ÚNMZ)“ u ČSN EN 1717+A1, „dosud neověřeno“ u návrhů. |
| SK | Slovenské dokumenty pro návštěvníka | Splněno: přepínač se nezobrazuje, `?jurisdikce=SK` se ignoruje, hledání „STN“ nevrací žádný dokument STN; stránka STN dostupná jen přímým odkazem s poznámkou „Slovenský dokument…“. |
| — | Opravy označení | ČSN ISO 19880-1 a ČSN EN 1717+A1 (s verzí 12/2026 „vyhlášený, dosud neúčinný“) správně. CLP zobrazuje konsolidované znění k 1. 7. 2026 a znění k 1. 1. 2027 jako vyhlášené, dosud neúčinné. |
| — | Telefon (390 px) | Bez vodorovného posuvníku na úvodní stránce, výsledcích i stránce dokumentu. |

## 2. Zjištěné závady (21. 11. 2026; opraveny 26. 11. 2026, odstavec 4)

1. **Z1 – úvodní stránka, „historických“:** Údaj „181 historických“ je
   rozdíl celku a platných, zahrnuje tedy i 145 připravovaných dokumentů
   (vedle 34 zrušených a 2 nahrazených). Připravované dokumenty nejsou
   historické; text by měl rozlišovat stavy (`app/app.py`,
   `inactive_document_count`; `app/templates/index.html`).
2. **Z2 – telefon, vyhledávací pole:** Ikona lupy je na šířce 390 px
   vykreslena pod textem pole, nikoli v něm (`07_telefon_rfnbo.png`).
   Kosmetické.
3. **Z3 – údaje připravovaných norem (data):** Stránka ISO 19885-2 má
   německý popis („noch nocht vorhanden“), slovenský štítek „Stav k 02/2025:
   v príprave“ a v poli „Platnost od“ text „Arbeitsdokument (Work
   Item)-Pracovný dokument…“. Totéž patrně u dalších návrhů ISO z rešerše.
4. **Z4 – název RED III (data):** Název (EU) 2023/2413 končí „Známá jako RED
   III Direktiva“ (slovensky „Direktiva“).
5. **Z5 – datum kontroly CLP:** U CLP je „Poslední kontrola stavu
   27. 10. 2026“, ačkoli konsolidovaná znění byla z Cellaru obnovena
   20. 11. 2026; obnova konsolidací datum kontroly neposouvá.

## 3. Rozpor zjištěný v databázi

V tabulce `User` jsou kromě účtu `automat` dva aktivní účty z 27. 10. 2026
(`prikryl`, `vahalik`); jediný záznam auditu s lidským uživatelem je návrh
kandidáta `1998/70/ES` z 27. 10. 2026. Vypořádání proto netvrdí, že účty
chybí, jen že žádný návrh dosud nepotvrdil editor (komentáře `OTEVŘENO bod 3`).
Zákon č. 586/1992 Sb. z tabulky MPO automat podle doporučení modelu
zamítl — přezkoumat.

## 4. Opakované ověření 26. 11. 2026

Veřejnou verzi aplikace (databáze aktualizována 2026-11-26 09:40) jsme
26. 11. 2026 znovu prošli jen čtením (GET, bez přihlášení): stránky jsme
stáhli a vyhodnotili skriptem a rozložení na telefonu (390 px) a počítači
(1280 px) ověřili v prohlížeči Chromium (Playwright). Snímky:
`data/test_screenshots/20261126_mpo_overeni/` (`result.json` obsahuje šířky
stránek a polohu ikony lupy). Čísla jsme porovnali s dotazem nad provozní
databází.

| # | Co jsme ověřili | Výsledek 26. 11. 2026 |
|---|---|---|
| — | Úvodní stránka | 967 předpisů a norem, „z toho 825 aktuálně platných, 116 připravovaných a 26 historických (zrušených nebo nahrazených)“; odpovídá databázi (bez jazykových verzí a slovenských dokumentů: 825 účinných, 116 připravovaných, 24 zrušených, 2 nahrazené). Z1 opravena. |
| 1 | Jeden řádek na předpis, štítky jazyků | Splněno, beze změny. Dotaz `2018/546` vrací 0. |
| 2 | Dotaz „RFNBO“ | Splněno: 12 dokumentů, každý jednou (21. 11. jich bylo 7) — (EU) 2024/1788, 165/2012 Sb., 201/2012 Sb., 458/2000 Sb., (EU) 2023/1184, (EU) 2023/2405, (EU) 2023/1185, COM(2021) 550, COM(2026) 370, (EU) 2018/2001, (EU) 2023/2413 a Vnitrostátní plán. Poznámka o synonymu RFNBO se zobrazuje. Pět chybějících aktů z porovnání pokrytí (C/2025/2983, (EU) 2024/3176, 2024/3180, 2024/3194, 2026/2316) je ve frontě kandidátů jako nové. Vypořádání aktualizováno. |
| 3 | Filtr podtypu aktů EU | Beze změny: „Akt v přenesené pravomoci (EU)“ 5 (2023/1184, 2018/674, 2019/1745, 2023/1185, 2025/656), „Prováděcí akt (EU)“ 9. |
| 4 | „MD“ × „Ministerstvo dopravy“ | Splněno; v nabídce institucí nejsou holé zkratky (jedinou zkratkou je název společnosti DNV). |
| 5 | Zákon o dráhách, filtr institucí a jurisdikce | Splněno. 266/1994 Sb. i 426/2021 Sb.: gestor Ministerstvo dopravy. Nabídka institucí má nově 5 skupin: kromě 4 skupin z 21. 11. přibyla „Zahraniční státní orgány“ (7 institucí: BAuA, DGUV, NASA, NIST, OSHA, PTB, Sandia National Laboratories). Vypořádání aktualizováno. Filtr jurisdikce: ČR 104, EU 187, mezinárodní 278, ostatní a neurčené 398 (součet 967; úbytek proti 21. 11. odpovídá sloučeným a vyřazeným záznamům). |
| 6 | Energetický zákon bez zastaralé hlášky | Splněno; hledání „Stav ke dni 30.6.2025“ vrací 0. |
| 7 | Připravované dokumenty | Katalog uvádí 116 připravovaných (21. 11.: 145). ISO 19885-2 má nově označení ISO/DIS 19885-2, anglický název z otevřených dat ISO, „Platnost od: Neuvedeno“, bez německého zástupného popisu; hledání „Arbeitsdokument“, „noch nocht“ a „v príprave“ vrací 0. Z3 opravena. |
| 8 | Předpisy z tabulek MPO | Beze změny: porovnání tabulek s provozní databází dává 51 řádků v databázi, 31 ve frontě, 8 bez dokumentu; žádný návrh přijetí nepotvrdil editor. |
| 9 | Strategie | Splněno: filtr „Strategie“ vrací 31 řádků (32 dokumentů). |
| 10 | Datum kontroly na stránce dokumentu | Splněno: „27. 10. 2026 (e-Sbírka)“ u 266/1994 Sb., 426/2021 Sb. a 458/2000 Sb., „27. 10. 2026 (EUR-Lex (Cellar))“ u RED II, RED III, ATEX, PED a (EU) 2023/1185, „5. 11. 2026 (Věstník ÚNMZ)“ u ČSN EN 1717+A1, „dosud neověřeno“ u ISO/DIS 19885-2 a ČSN ISO 19880-1. CLP a REACH nově „20. 11. 2026 (EUR-Lex (Cellar))“, CLP zobrazuje konsolidované znění ke dni 1. 7. 2026. Z5 opravena. Datum kontroly nese v databázi 205 dokumentů (21. 11.: 233). |
| SK | Slovenské dokumenty pro návštěvníka | Splněno: `?jurisdikce=SK` se ignoruje (vrací všech 967), hledání „STN“ vrací 164 řádků a žádný z nich není dokumentem STN (shoda jen v textu českých a dalších dokumentů). |
| — | Úřední názvy | RED II, RED III, ATEX (2014/34/EU) a PED (2014/68/EU) mají úřední název z EUR-Lexu bez přezdívky; hledání „Známá jako“ a „Direktiva“ vrací 0. Z4 opravena. |
| — | Klíčová slova | Stránka dokumentu má oddíl „Klíčová slova“ s původem: „Deskriptory EuroVoc … Úřední indexace Úřadu pro publikace EU (Cellar)“ u aktů EU, „Třídník ICS … podle českého převzetí v katalogu ČAS“ u norem, „Odvozená klíčová slova … Odvodil jazykový model …; neověřeno“ u ostatních. Vyhledávání je prochází: dotaz „tržní zvyklosti“ (deskriptor EuroVoc, jenž v názvech není) vrací 5 aktů EU. |
| — | Oblasti | Filtr „Oblast“ nabízí 29 oblastí (Elektrolýza … Dokumenty obecné povahy); pracovní „Oblast dosud neurčena“ v nabídce není. |
| — | Telefon (390 px) a počítač (1280 px) | Bez vodorovného posuvníku na úvodní stránce, výsledcích „RFNBO“, stránce RED III a ISO/DIS 19885-2. Ikona lupy leží uvnitř vyhledávacího pole na obou šířkách. Z2 opravena. |

Nové závady jsme nezjistili. Rozpor z odstavce 3 trvá: v tabulce `User` jsou
dva aktivní účty (`prikryl`, `vahalik`) a neaktivní `automat`; v záznamu
změn není žádné potvrzení přijetí editorem.
