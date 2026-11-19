# Připomínky MPO k výsledku V01 a jejich vypořádání

Stav k 19. 11. 2026. Dokument porovnává připomínky Ing. Petra Mervarta
(Ministerstvo průmyslu a obchodu, aplikační garant dílčího projektu DP004)
k výsledku V01 „Databáze regulačních předpisů a předrealizačních procesů“
se současným stavem databáze a webové aplikace a navrhuje postup jejich
vypořádání.

## 1. Podklady

Připomínky jsou uloženy jako e-maily v adresáři `doc/mail/`:

* e-mail ze 17. 4. 2026 (soubor `… 01.eml`) — šest konkrétních výhrad
  doložených snímky obrazovky a obecné hodnocení („v této podobě to rozhodně
  nemůžeme schválit“, „aplikační garant a Ministerstvo průmyslu a obchodu
  nejsou beta-testeři aplikací“);
* e-mail z 22. 5. 2026 (soubor `… 00.eml`) — dvě tabulky předpisů, jež by
  podle MPO měly být v databázi, návrh nové kategorie „Strategie“, dotaz na
  způsob udržování aktuálnosti a návrh telekonference začátkem června 2026:
  * `Předpisy CZ - vodík_MPO.xlsx` (list „Předpisy (30.4.2026)“, 50 řádků;
    zdroje VS = vodíková strategie, ZPL = Zákony pro lidi, AI = dotaz přes AI;
    žlutě označené položky byly podle MPO v databázi již v dubnu 2026),
  * `CDV - evropské právní předpisy_v01.xlsx` (list „Databáze EU (30.4.2026)“,
    40 řádků; zdroje „Databáze CDV“ a „AI – Copilot“).

Současný stav jsme ověřovali v živé databázi `h2regdocs` (pouze čtení)
a ve vyhledávání aplikace na větvi `master` (`fc29be8`, PR #25). Čísla
dokumentů v textu (#83 apod.) jsou hodnoty `Document.id`.

## 2. Stav jednotlivých připomínek

| # | Připomínka | Stav | Zjištění |
|---|---|---|---|
| 1 | Rozhodnutí ECB (EU) 2018/546 se ve výsledcích zobrazí dvakrát česky a dvakrát anglicky. | duplicita vyřešena, relevance trvá | V databázi je již jen #128 (CS) a #1472 (EN). Jde však o vnitřní rozhodnutí ECB o kapitálových rozhodnutích, jež s vodíkovými technologiemi patrně nesouvisí. V seznamu výsledků jsou obě jazykové verze stále dvěma samostatnými řádky, takže uživatel je i nadále může vnímat jako duplicitu. |
| 2 | Dotaz „RFNBO“ vrací čtyřikrát stejný dokument; někde je jen česká verze, jinde česká i anglická. | duplicita vyřešena, výsledek neúplný | Dotaz nyní vrací jediný dokument, směrnici RED III (#83). Nenajde však akty v přenesené pravomoci (EU) 2023/1184 a 2023/1185, jež pojem RFNBO přímo vymezují, protože vyhledávání prochází jen text názvu a popisu. Anglické verze existují jen u 26 dvojic z podkladu Haltuf (`doc/PLAN.md` §47); tato zásada není uživateli nikde vysvětlena. |
| 3 | V databázi chybějí akty v přenesené pravomoci. | částečně vyřešeno | Databáze obsahuje (EU) 2023/1184, 2023/1185 (jen s anglickým názvem), 2018/674, 2019/1745 a 2025/656. Chybí (EU) 2025/2359 (metodika nízkouhlíkového vodíku). Filtr typu dokumentu nemá kategorii „akt v přenesené pravomoci / prováděcí akt“; tyto akty jsou zařazeny pod „Nařízení EU“ a dotaz „delegovan“ najde jen jeden z nich. |
| 4 | V nabídce původců je současně „MD“ i „Ministerstvo dopravy“. | vyřešeno | Zkratky byly nahrazeny plnými názvy institucí. S připomínkou však souvisí systémová chyba přiřazení původců popsaná v odstavci 3. |
| 5 | MPO je uvedeno jako odpovědné za zákon o dráhách. | trvá | #144 (266/1994 Sb.) i #145 (426/2021 Sb.) mají jako původce stále MPO; věcně příslušné je Ministerstvo dopravy. Podle tabulky MPO je chybně přiřazen i zákon č. 250/2021 Sb. (v databázi MPO, v tabulce MPSV). |
| 6 | U energetického zákona se zobrazuje zastaralá hláška („Stav ke dni 30.6.2025 – čeká se na podpis presidenta“). | trvá | Text je v popisu směrnice RED III (#83), na niž se uživatel patrně dostal z vazeb energetického zákona; popis energetického zákona (#72) je již v pořádku. Obdobný problém je rozsáhlejší: 231 popisů dokumentů obsahuje veřejně viditelné interní poznámky z vývoje (např. „Nalezeno screeningem EUR-Lex Cellar (klíčové slovo 'hydrogen', doc/PLAN.md §28) …“), mimo jiné i oba záznamy Vodíkové strategie ČR (#1240, #1241). |
| 7 | Databáze neobsahuje připravované předpisy (např. připravovanou aktualizaci LEX vodík). | na `master` trvá | Sběr návrhů předpisů (VeKLEP, Poslanecká sněmovna, Senát, návrhy Komise, návrhy norem prEN) je hotov na větvi `feature/h2db-sources` (etapa E2, `src/tools/harvest_drafts.py`). Byl však vyzkoušen jen na testovací databázi `h2regdocs_test`, do `master` zatím nebyl sloučen a nad živou databází dosud neběžel. Chybí rovněž editorské rozhraní pro převod návrhu na vyhlášený předpis. |
| 8 | „Nejsou tam ani ty existující“ předpisy; tabulky MPO a CDV s předpisy, jež by v databázi měly být. | trvá, patrně nejzávažnější | Podrobně v odstavci 2.1. |
| 9 | Nová kategorie „Strategie“. | převážně vyřešeno | Typ „Strategický dokument“ obsahuje 10 dokumentů, mimo jiné Vodíkovou strategii ČR (2021), její aktualizaci (2024) a Vodíkovou strategii EU (2020). Zbývá zvážit přejmenování typu na „Strategie“ podle návrhu MPO, vyčistit popisy (bod 6) a doplnit další národní a evropské strategie (Vnitrostátní plán ČR v oblasti energetiky a klimatu, Státní energetická koncepce, REPowerEU). |
| 10 | Jak bude zajištěna aktuálnost předpisů. | částečně vyřešeno | Na `master` je kontrola platnosti (`src/tools/check_validity.py`), stavy dokumentů `promulgated` a `repealed` a fronta kandidátů s potvrzováním dvěma editory (`/admin/candidates`). Pravidelné automatické spouštění kontrol neexistuje (otevřené rozhodnutí R1.9) a provozní postup pro garanta není sepsán. |

### 2.1 Pokrytí tabulek MPO a CDV

**Česká legislativa (tabulka MPO).** Tabulka obsahuje 43 řádků s právními
předpisy (42 různých předpisů, zákon č. 250/2021 Sb. je uveden dvakrát)
a 7 řádků s normami ČSN. Z právních předpisů je v databázi 12, další 3 jsou
jen ve frontě kandidátů (108/2011 Sb., 345/2002 Sb., 586/1992 Sb.)
a **27 předpisů v databázi zcela chybí**:

* vyhlášky ERÚ: 349/2015 Sb., 488/2021 Sb., 401/2010 Sb., 513/2021 Sb.,
  8/2016 Sb., 489/2021 Sb.;
* vyhlášky MPO: 344/2012 Sb., 110/2022 Sb., 166/2022 Sb., 328/2022 Sb.,
  264/2020 Sb.;
* předpisy týkající se zásobníků plynu, těžby a báňské bezpečnosti:
  44/1988 Sb., 61/1988 Sb., 62/1988 Sb., 71/2002 Sb., 72/2002 Sb.,
  104/1988 Sb., 239/1998 Sb., 392/2003 Sb., 85/2012 Sb.;
* předpisy k prevenci závažných havárií: 226/2015 Sb., 277/2015 Sb.;
* zákony: 249/2025 Sb. (ZOZE), 406/2000 Sb. (o hospodaření energií);
* nařízení vlády 191/2022 Sb. a 219/2016 Sb.; vyhláška 146/2024 Sb.
  (o požadavcích na výstavbu).

Normy ČSN z tabulky jsou v databázi zastoupeny (ČSN ISO 14687, ČSN EN 17124,
ČSN EN ISO 19880-1, ČSN EN 13445, ČSN EN ISO 11114, ČSN EN 17127), z řady
ČSN EN 60079 jen část 0.

Kontrola úplnosti uzávěrem citací (`doc/CITATION_CLOSURE.md`) těchto 27
předpisů nezachytila. Samo toto zjištění ukazuje, že dosavadní měření
úplnosti nepostačuje a že zlatá sada sestavená odborníky
(`doc/DATABASE_SCOPE.md`, odstavec 7, bod 1) je nezbytná.

**Evropská a mezinárodní legislativa (tabulka CDV).** Žlutě označené
položky jsou v databázi. Chybí akt v přenesené pravomoci (EU) 2025/2359
a patrně nařízení TEN-T (EU) 2024/1679 (ověřit). Položky AFIR (2023/1804)
a balíček dekarbonizace trhu s plynem (2024/1788 a 2024/1789) v databázi jsou,
balíček však není veden jako celek. Položky „ISO/TC 22“, „ISO/TC 193“,
„ISO/TC 268“, „IEC/TC 105“ a „CEN/TC 234, 235, 268“ označují technické
komise, nikoli dokumenty; navrhujeme je MPO vysvětlit a místo nich nabídnout
přehled norem, jež tyto komise vydaly a jež databáze obsahuje. Obecná položka
„IMO pravidla pro přepravu vodíku“ odpovídá v databázi dokumentu
IMO CCC8/WP.3 Annex 2 (#770).

## 3. Další zjištění, jež MPO patrně uvidí

* **Slovenské předpisy jsou přiřazeny českým ministerstvům.** Například
  slovenský zákon o podpoře ekologických vozidel (#70) má původce
  Ministerstvo dopravy, slovenské předpisy #67, #73 a #97 MPO, #47 a #48
  MMR, slovenské předpisy z oblasti životního prostředí MŽP. Obdobně je
  směrnice 2018/858 (#88) přiřazena MD, RID (#120) MPO a sdělení Komise (#79)
  MPO. Připomínka k zákonu o dráhách je jen jedním projevem této chyby.
* Filtr „Odpovědný orgán / DG“ míchá česká ministerstva, generální
  ředitelství Komise a normalizační orgány; 411 dokumentů pochází od
  slovenského ÚNMS SR (normy STN), což může českého uživatele mást.
* Dokumenty s chybnými údaji: #57 a #78 mají název „Slov-Lex“ a #78 navíc
  popis Vodíkové strategie EU; #130 má označení `(EU) 2014/1302`, ale název
  prováděcího nařízení 2019/776, takže působí jako duplicita #129; předpis
  EHK OSN č. 134 je v databázi dvakrát (#92 a #139).
* Příznak `needs_review` má 339 dokumentů.

## 4. Navrhovaný postup

### 4.1 Krok 0: Opravy dat (1–2 dny, živá databáze, předem záloha)

* opravit původce: #144 a #145 na Ministerstvo dopravy, 250/2021 Sb.
  na MPSV; slovenským předpisům přiřadit slovenské instituce nebo zdroj
  „Slovenská republika“; prověřit původce všech českých předpisů proti
  sloupci „Nositel“ tabulky MPO;
* odstranit zastaralou hlášku z popisu #83;
* interní poznámky o původu záznamu přesunout z popisů do samostatného,
  veřejně nezobrazovaného pole (provenance, `doc/DATABASE_SCOPE.md`,
  odstavec 7, bod 2);
* opravit #57, #78 a #130, sloučit #92 a #139, doplnit český název
  u (EU) 2023/1185, vyřadit rozhodnutí ECB 2018/546 jako dokument mimo rozsah;
* opravy zapsat i do `manual_corrections.json`, aby přežily přestavbu
  databáze z JSON; u dokumentů bez označení to dosud nejde (stejný problém
  jako u štítků jazyka), a bude proto potřeba korekce klíčovat jinak.

**Stav k 19. 11. 2026 (větev `feature/mpo-krok0`, živá DB zapsána):**
Před zápisem jsme pořídili zálohu
`backups/h2regdocs_20261119_170137_before_mpo_krok0.sql.gz`.

* *Původ záznamu.* Poznámky o původu záznamu („Nalezeno screeningem …,
  doc/PLAN.md §28“) jsou v novém sloupci `Document.provenance`, který veřejné
  stránky nezobrazují (`src/tools/backfill_provenance.py`; 231 dokumentů).
  Generátory je nadále zapisují jen tam. Z 231 dokumentů jich 229 nemělo jiný
  popis než tuto poznámku; nyní jsou bez popisu a nesou důvod kontroly
  „chybí popis/anotace dokumentu“, takže počet dokumentů s příznakem
  `needs_review` vzrostl z 339 na 558. Obě vodíkové strategie mají popis
  bez interní poznámky.
* *Ruční korekce.* `data/manual_corrections.json` nově přijímá klíč
  `url-<hash>` pro záznamy bez označení, vyřazení záznamu (`"exclude": true`)
  a omezení na jazyk řádku; do živé DB je promítá
  `src/tools/apply_manual_corrections.py` (34 opravených dokumentů,
  2 smazané).
* *Původci.* #144, #145 a nařízení vlády 133/2005 Sb. (#148) mají původce
  Ministerstvo dopravy, zákon č. 250/2021 Sb. (#147) MPSV. Slovenské předpisy
  (23 dokumentů) mají slovenské orgány: Ministerstvo životného prostredia,
  dopravy, hospodárstva, financií, vnútra a práce, sociálnych vecí a rodiny
  Slovenskej republiky, Úrad pre územné plánovanie a výstavbu SR a Úrad pre
  reguláciu sieťových odvetví. ADR (#119) má EHK OSN, RID (#120) OTIF,
  sdělení Komise COM(2020) 301 (#79 a slovenské znění #78) Evropskou komisi,
  slovenský záznam aktu (EU) 2018/858 (#88) Evropský parlament a Radu EU.
  U zákona č. 250/2012 Z. z. (#73) jsme jako původce zvolili ÚRSO; vhodné
  ověřit.
* *Zastaralá hláška.* Popis RED III (#83) je nahrazen popisem bez údajů,
  které stárnou; anglická varianta (#1479) zůstává beze změny.
* *Názvy.* #57 a #78 již nemají název „Slov-Lex“ a odkazují na slovenské
  znění v EUR-Lexu; parser Slov-Lexu název webu za název předpisu
  nepovažuje. (EU) 2023/1185 (#77) má úřední český název a štítek jazyka CS
  (plný text byl již český).
* *Rozhodnutí ECB 2018/546* (#128 a anglická varianta #1472) je vyřazeno
  jako dokument mimo rozsah. Bylo chybně navázáno jako právní základ uzlu U5;
  tato vazba zanikla s ním. Celkem 1486 dokumentů.

Zbývá z kroku 0:

* prověření původců ostatních českých předpisů proti sloupci „Nositel“
  tabulky MPO: z předpisů, které tabulka i databáze obsahují, se liší jen
  zákon č. 250/2021 Sb. (opraveno).

**Stav k 19. 11. 2026 (větev `feature/mpo-krok0-zbytek`, živá DB zatím
nezapsána):** Zbylé opravy kroku 0 jsou v `data/manual_corrections.json`
a v commitnutých výstupech pipeline, plné texty jsou stažené a zkouška
proběhla na `h2regdocs_test`. Do živé databáze je promítne
`src/tools/apply_manual_corrections.py` po sloučení větve; do té doby živá
databáze tyto opravy nemá.

* *Mechanismus korekcí.* Korekce s klíčem `<značka> [EN]` (označení
  anglické varianty, které zapisuje i editorské rozhraní) mění jen anglický
  řádek jazykové dvojice. Záznam bez označení i adresy má klíč
  `title-<hash>` podle názvu. Položka `"merged_into": "<značka>"` vyřadí
  duplicitní záznam; v živé databázi skript přesune jeho vazby
  (`document_relation`, `node_document`, `scenario_document`, klíčová slova,
  pravidla aktivace, kontrolní položky a kandidáty) na přežívající dokument
  a duplicitní smaže. Při změně označení skript nastaví i adresu plného
  textu a slug, jaký by dokument dostal při přestavbě.
* *#130 a #1466.* Obě jazykové varianty `(EU) 2014/1302` nesou úřední
  název nařízení Komise (EU) č. 1302/2014 o TSI LOC&PAS (CELEX 32014R1302,
  český a anglický název z Cellaru), jeho adresu v EUR-Lexu, datum účinnosti
  1. 1. 2015 a nový popis; plné texty jsme stáhli znovu. Prováděcí nařízení
  (EU) 2019/776 zůstává samostatně jako #129.
* *#92 a #139.* Předpis EHK OSN č. 134 je jeden dokument: záznam
  `(EHK OSN) č. 134` (zdroj Sinay_Zakony, s adresou nesouvisejícího
  slovenského předpisu 134/2006 Z. z.) je sloučen do `[2019/795]` (#139),
  jenž má české i anglické znění (#1488, vazba `TRANSLATION_OF`
  zůstává). #92 neměl vazby ani klíčová slova; #139 nově odkazuje na české
  znění místo anglického.
* *#84.* Slovenské znění směrnice (EU) 2024/1788 má označení
  `(EU) 2024/1788 [SK]`, úřední slovenský název, adresu slovenského znění
  v EUR-Lexu, typ „Směrnice EU“ a plný text. Původcem je podle pravidla pro
  akty EU odpovědné generální ředitelství (DG ENER), stejně jako u českého
  znění #104. Zápis `(EÚ) 2024/1788` použít nelze, protože porovnání
  v databázi diakritiku nerozlišuje a označení by kolidovalo s #104.
* *#75.* Novela slovenského zákona o spotřební dani z minerálních olejů má
  označení `492/2010 Z. z.`; vazba `NATIONAL_EQUIVALENT` na zákon
  č. 353/2003 Sb. a plný text následují nové označení.
* *Vedlejší účinek.* U #57 a #78 skript nově srovná i sloupce
  `nazev_autoritativni` a `zdroj_autoritativni_url` (v živé databázi
  zůstal název „Slov-Lex“ a adresa Slov-Lexu), tedy na stav, který dá
  přestavba.

### 4.2 Krok 1: Doplnění obsahu podle tabulek MPO a CDV (1–2 týdny)

* obě tabulky naimportovat jako zdroj „MPO/CDV 30. 4. 2026“ do fronty
  kandidátů a nechat je posoudit editory;
* doplnit chybějící instituce (ERÚ, ČBÚ);
* obě tabulky převzít jako zlatou sadu a jejich pokrytí hlídat automatickým
  testem, aby se případná ztráta dokumentu projevila hned.

**Stav k 19. 11. 2026 (větev `feature/mpo-krok1`, živá DB dosud nezapsána):**
Podrobnosti uvádíme v dokumentu `doc/MPO_TABULKY.md`.

* *Strojový tvar.* Obě tabulky jsou v `data/20260430_MPO/raw/`; skript
  `src/tools/mpo_tables.py` je převádí do `mpo_tables.json` (90 řádků)
  a každý řádek porovnává s databází (`mpo_coverage.json`). Řádky, jež nelze
  rozhodnout pravidlem, rozhoduje s uvedením důvodu `mpo_decisions.json`.
* *Pokrytí.* Z 90 řádků je 51 v databázi (MPO 21, CDV 30), 31 ve frontě
  kandidátů nebo do ní patří (MPO 29, CDV 2: nařízení TEN-T (EU) 2024/1679,
  jež jsme v EUR-Lexu ověřili, a (EU) 2025/2359) a 8 řádků CDV nejsou dokumenty
  (sedm technických komisí a souhrnná položka „UNECE předpisy (WP.29)“).
  Čísla v odstavci 2.1 se potvrdila s jednou výjimkou: řádek MPO-42 uvádí číslo
  191/2022 Sb., ale název nařízení vlády č. 192/2022 Sb., jež databáze má.
* *Nesrovnalosti v tabulce MPO.* Řádek „277/2015 Sb.“ míní podle názvu
  vyhlášku č. 227/2015 Sb.; vyhláška č. 513/2021 Sb. je zrušená novela, platná
  je vyhláška č. 508/2025 Sb. o regulačním výkaznictví; databáze vede
  ČSN ISO 19880-1 pod neexistujícím označením ČSN EN ISO 19880-1 (#3).
* *Fronta kandidátů.* Pro zdroj „MPO/CDV 30. 4. 2026“ je připraveno 34
  kandidátů s úředním názvem, adresou a platností (zakonyprolidi.cz, e-Sbírka,
  EUR-Lex, katalog ČAS): 28 českých předpisů, 2 akty EU, norma
  ČSN EN ISO 11114-4 a 3 kandidáti z uzávěru citací, jimž se jen doplní řádky
  tabulky do podkladů. Zápis do živé databáze provede
  `src/tools/mpo_tables.py import --apply`; na `h2regdocs_test` je vyzkoušen.
* *ERÚ a ČBÚ.* Kandidáti nesou navrženého původce (nový sloupec
  `DocumentCandidate.puvodce`), mezi nimi Energetický regulační úřad
  (6 kandidátů) a Český báňský úřad (6 kandidátů). Do `DocumentSource` se
  instituce zapíše s prvním přijatým dokumentem, aby veřejný filtr nenabízel
  instituci bez dokumentů.
* *Zlatý test.* `tests/test_mpo_golden.py` (součást `run_tests.py`) ověřuje
  nad `h2regdocs_test`, že každý řádek obou tabulek je dokumentem, kandidátem,
  nebo má uveden důvod, a že žádný dokument z tabulek z databáze nezmizel.

Zbývá z kroku 1: zápis kandidátů do živé databáze, jejich posouzení editory
(potvrzení přijetí vyžaduje dva různé editory), rozhodnutí o dalších
částech řad ČSN EN 60079 a ČSN EN 13445 a vysvětlení technických komisí MPO.

### 4.3 Krok 2: Úpravy rozhraní

* jeden řádek na předpis, jazykové verze jen jako štítky CS/EN v tomto řádku;
* filtr původců rozdělit podle jurisdikce (ČR / EU / mezinárodní /
  normalizační orgány) a slovenské dokumenty ve výchozím zobrazení skrýt
  (viz otevřenou otázku v odstavci 5);
* zavést podtyp „akt v přenesené pravomoci / prováděcí akt“;
* ve vyhledávání využít klíčová slova a synonyma (RFNBO, AFIR, RED III,
  LEX OZE apod.).

### 4.4 Krok 3: Průběžná aktualizace

* sloučit větev `feature/h2db-sources` do `master` (PR), provést první běh
  sběru nad živou databází (odhadem 247 kandidátů, z toho 111 v první
  úrovni) a nastavit plánovač podle `doc/DATABASE_SCOPE.md`, odstavec 6
  (týdně e-Sbírka, EUR-Lex a VeKLEP, měsíčně normy);
* u každého dokumentu zobrazovat datum poslední kontroly;
* doplnit editorské rozhraní pro převod návrhu na vyhlášený předpis;
* sepsat pro garanta krátký provozní dokument: kdo frontu kandidátů
  posuzuje, jak často a podle jakých zdrojů.

### 4.5 Krok 4: Před opětovným předáním

* převést všechny scénáře z připomínek MPO do prohlížečových testů
  (`tests/e2e/`) se snímky obrazovky;
* nechat aplikaci před předáním projít někým mimo vývojový tým (interní
  akceptace);
* připravit pro MPO přehled vypořádání jednotlivých připomínek
  (tento dokument v upravené podobě) jako podklad k telekonferenci.

## 5. Otevřené otázky

* **Slovenské předpisy a normy STN:** ponechat je ve veřejném katalogu,
  nebo je skrýt či oddělit?
* **Telekonference z června 2026:** e-mail z 22. 5. 2026 navrhoval schůzku
  začátkem června. Je třeba doplnit, zda proběhla a co se na ní dohodlo.
* **Přejmenování typu „Strategický dokument“ na „Strategie“** podle návrhu
  MPO.
* **Označení předpisu EHK OSN č. 134:** přežívající dokument má označení
  `[2019/795]` (číslo zveřejnění v Úředním věstníku). Patrně vhodnější by
  bylo `EHK OSN č. 134`; změna by ale přejmenovala i anglickou variantu
  a klíče plných textů, proto ji necháváme k rozhodnutí.
* **Slovenské znění aktů EU:** #84 jsme označili `(EU) 2024/1788 [SK]`
  podle vzoru `[EN]`, ale vazbou na české znění jsme jej nepropojili
  (`TRANSLATION_OF` vede jen z anglické varianty). Je třeba rozhodnout,
  zda slovenská znění aktů EU (#57, #78, #84, #88) propojovat stejně.

