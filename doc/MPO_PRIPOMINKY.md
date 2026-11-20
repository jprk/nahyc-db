# Připomínky MPO k výsledku V01 a jejich vypořádání

Stav k 19. 11. 2026 (doplněno o harmonogram a rozhodnutí z téhož dne). Dokument porovnává připomínky Ing. Petra Mervarta
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
  U zákona č. 250/2012 Z. z. (#73) jsme jako původce zvolili ÚRSO; podle
  uživatele je jím Ministerstvo hospodárstva SR (opraveno v kroku 1 –
  opravy dat).
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

**Stav k 19. 11. 2026 (větev `feature/mpo-data-opravy`, krok 1 – opravy dat
a strategie podle rozhodnutí uživatele; živá DB zatím nezapsána):** Opravy
jsou v `data/manual_corrections.json`, nové strategie v
`data/strategy_documents.json` (čte je `build_unified_db.py`). Commitnuté
výstupy pipeline odpovídají přestavbě; porovnali jsme je s úplnou
přestavbou, která se od commitnutého stavu liší i nesouvisejícími změnami
deduplikace jazykovým modelem, ty jsme nepřevzali. Do živé databáze je
promítnou `apply_manual_corrections.py` (sloupce dokumentů) a nový
`src/tools/backfill_strategies.py` (přejmenování typu, nové dokumenty,
vazby, stavy).

* *Slovenská znění aktů EU.* Slovenská znění mají označení
  `<značka> [SK]` po vzoru `[EN]` a vazbu `TRANSLATION_OF` na české znění:
  `(EU) 2022/2427 [SK]` (#57 → #58), `COM(2020) 301 [SK]` (#78 → #79),
  `(EU) 2018/858 [SK]` (#88, dříve `2018/858/ES` → #89) a
  `(EU) 2024/1788 [SK]` (#84 → #104). Vazby počítá
  `language_variants.translation_relations()`, zapisuje je
  `split_language_variants.py` do `data/document_relations_variants.json`.
  #57 a #88 mají úřední slovenský název z Cellaru. Katalog je zobrazuje
  jako jazykovou verzi českého řádku, stránka dokumentu jako „slovenskou
  verzi dokumentu“. Úřední české znění Vodíkové strategie EU (#79) má nově
  označení `COM(2020) 301`, adresu českého znění a typ Strategie. Jiná
  slovenská znění aktů EU databáze nemá; #62 (označení `2010/75/EU`) je
  slovenské oznámení, nikoli akt EU.
* *Kolace a klíče.* Označení nekolidují ani pod `utf8mb4_czech_ci` (test).
  Klíče manifestu plných textů a `data/fulltext_url_overrides.json` jsou
  přejmenované na nová označení, texty stažené znovu z Cellaru.
  `load_document_relations.py` sleduje přejmenování z korekcí ve všech
  souborech vazeb (např. `2018/858/ES` v `document_relations_auto.json`)
  a dokument bez označení najde podle `url-<hash>` jeho adresy.
* *Původce 250/2012 Z. z.* (#73) je Ministerstvo hospodárstva Slovenskej
  republiky (dosud ÚRSO).
* *#110 (2012/18/EU).* Chybná byla česká varianta: označení, popis
  i anglická varianta (#1485) patří směrnici Seveso III, název a adresa
  směrnici ATEX 2014/34/EU (#108). Opraveno na úřední název a adresu
  2012/18/EU (CELEX 32012L0018), plný text stažen znovu. Odpovědným
  útvarem obou variant je podle Cellaru GŘ pro životní prostředí (dosud
  převzato od ATEX: GŘ pro vnitřní trh; opraveno v `data/eu_gestor_cache.json`).
* *#3.* Označení `ČSN ISO 19880-1` (katalog ČAS: vydání 8/2025, katalogové
  číslo 522022, účinnost 1. 9. 2025, nahradilo vydání 9/2020), platnost
  „od 9/2025“.
* *#140.* Záznam ze zdroje Haltuf_Dokumenty je předpis EHK OSN č. 100
  (revize 2, elektrické hnací ústrojí vozidel; adresa UNECE). Název a popis
  publikace EIGA Doc 100/20 o vodíkových lahvích dostal chybou
  `build_unified_db.py`: klíč `eiga:<číslo>` se hledal pro každé označení
  s číslem, takže „Regulation No. 100“ i pravidlo DVGW `G 100 (A)` (#744)
  dostaly titul EIGA Doc 100, a deduplikace pak záznam sloučila s publikací
  EIGA ze zdroje Sinay_Normy. Klíč `eiga:` se nyní hledá jen u označení
  EIGA/IGC. #140 má anglický název předpisu, úřední název a adresu
  zveřejnění revize 2 v Úředním věstníku EU (CELEX 42015X0331(01), plný
  text z Cellaru), původce EHK OSN, typ Nezařazeno (jako ostatní předpisy
  EHK OSN) a jurisdikci „mezinárodní“. `EIGA IGC Doc 100/20` je opět
  samostatný dokument (v živé DB nový); #744 převzatý název a popis ztratil.
* *Typ „Strategie“.* Typ „Strategický dokument“ je přejmenován na
  „Strategie“ v pipeline, testech a datech; v živé DB přejmenuje řádek
  `DocumentType` (i u kandidátů) `backfill_strategies.py`. Úřední české
  znění Vodíkové strategie EU (#79) je Strategie.
* *13 strategií s prioritou A a B* (příloha A `doc/MPO_VYPORADANI.md`, 4
  národní a 9 evropských; dřívější text uváděl 11) jsou dokumenty, nikoli
  kandidáti: Vnitrostátní plán ČR v oblasti energetiky a klimatu (2024),
  2. aktualizace NAP čisté mobility (2024), Státní energetická koncepce
  (2015), Politika ochrany klimatu (2017) a sdělení Komise COM(2019) 640,
  COM(2020) 299, COM(2020) 789, COM(2021) 550, COM(2022) 230, COM(2023) 62,
  COM(2023) 156, COM(2025) 85 a COM(2026) 370. Úřední názvy sdělení jsou
  z Cellaru (u COM(2023) 62 opraven překlep Cellaru „VBORU“), popis je
  věcný, původ záznamu je v `provenance`. Kategorie Strategie bude mít
  25 dokumentů. Plné texty jsou stažené všechny; 2. aktualizace NAP čisté
  mobility je jen ve formátu .docx, jejž `extract_fulltext.py` dosud nečte.
  Deduplikace jazykovým modelem sloučila 2. aktualizaci NAP čisté mobility
  s aktualizací z roku 2019; ručně ověřené záznamy (`Strategy_Research`)
  proto `deduplicate_db.py` slučuje jen podle shodného označení nebo
  adresy, nikoli podle podobnosti názvu.
* *Nahrazený NAP čisté mobility.* Aktualizace z roku 2019 (#1246) a její
  příloha (#1247) zůstávají v databázi ve stavu „nahrazený“
  (`stav_dokumentu: superseded` v korekcích) s vazbou `REPEALS` od
  2. aktualizace (`data/document_relations.json`, konce `url-<hash>`).
  Stránka dokumentu u strategií vazbu popisuje „nahrazuje / je nahrazen
  dokumentem“, u ostatních typů „ruší“.
* *Plné texty z EUR-Lexu* stahuje `fetch_fulltext.py` u adres s číslem
  CELEX z Cellaru Úřadu pro publikace (`sites/eurlex.py`), bez prohlížeče.
  Nové soubory (21) jsou ve worktree v `data/fulltext_mpo_data_opravy/`;
  po mergi je zkopírovat `cp -n` do `data/fulltext/` hlavního stromu.
* *Strategie s prioritou C* (rozhodnutí z 20. 11. 2026, větev
  `feature/mpo-strategie-c`) jsou dokumenty stejně jako priority A a B:
  COM(2023) 634 (revize plánu SET), COM(2024) 63 (klimatický cíl 2040),
  COM(2025) 79 (Akční plán pro cenově dostupnou energii), COM(2025) 95
  (Průmyslový akční plán pro automobilový průmysl) a COM(2025) 1005 (Balíček
  opatření pro elektrizační soustavy). Úřední názvy jsou z Cellaru, plné texty
  z Cellaru přes `fetch_fulltext.py --only`. Příloha A uvádí s prioritou C
  pět sdělení, nikoli šest, jak tvrdil dřívější text.
* *Neschválené aktualizace strategií* jsou připravované dokumenty
  (`stav_dokumentu: draft` v `data/strategy_documents.json`, typ Strategie):
  „Politika ochrany klimatu v České republice. Aktualizace pro období 2025
  až 2050“ (MŽP, verze z července 2025 zveřejněná 6. 11. 2025, plný text
  PDF) a „Aktualizace Státní energetické koncepce České republiky (návrh)“
  (MPO, meziresortní připomínkové řízení od 7. 2. 2024; text návrhu není
  zveřejněn, adresou je stránka MPO s Východisky aktualizace). Obě mají vazbu
  `REPEALS` na platnou strategii, již mají nahradit (Politika ochrany klimatu
  2017, Státní energetická koncepce 2015); stránka dokumentu ji u
  připravovaného dokumentu popisuje „má nahradit / má být nahrazen
  připravovaným dokumentem“. Stav projednávání (z médií, usnesení vlády
  nedohledáno): vláda projednání obou aktualizací v červenci 2024 odložila
  a podle zpráv z prosince 2024 při schválení Vnitrostátního plánu od jejich
  aktualizace upustila; MŽP poté zveřejnilo novou verzi Politiky ochrany
  klimatu. Schválí-li vláda aktualizaci, editor ji na stránce připravovaných
  dokumentů převede na účinnou (`self`, `active`); aplikace pak nahrazovanou
  strategii převede do stavu „nahrazený“ (`app/drafts_admin.py`). Kategorie
  Strategie má 32 dokumentů (30 platných, 2 připravované).
* *Nové plné texty* (6) jsou ve worktree v `data/fulltext_mpo_strategie_c/`
  (COM_2023_634, COM_2024_63, COM_2025_79, COM_2025_95, COM_2025_1005
  a `url-760e34c6` – návrh Politiky ochrany klimatu); po mergi je zkopírovat
  `cp -n` do `data/fulltext/` hlavního stromu.

Příkazy pro živou databázi (po sloučení větve, `git pull` a zkopírování
plných textů; `title-3ef76674` a další korekce kroku 0-zbytek musí být
promítnuty dřív nebo spolu s nimi, jinak #84 nemá označení `[SK]`):

```
.venv/bin/python src/tools/backup_db.py --reason before_mpo_data_opravy
.venv/bin/python src/tools/apply_manual_corrections.py --only url-e18c5e80 --only url-86dc0d38 \
    --only url-fd143b87 --only 2018/858/ES --only "250/2012 Z. z." --only 2012/18/EU \
    --only "2012/18/EU [EN]" --only "ČSN EN ISO 19880-1" --only "UNECE Regulation No. 100 (Revision 2)" \
    --only "G 100 (A)" --only title-3ef76674          # dry run, pak totéž s --apply
.venv/bin/python src/tools/backfill_strategies.py   # dry run, pak --apply
~/.cache/lit-tools/bin/python src/tools/extract_fulltext.py --apply
```

`backfill_strategies.py` vloží i strategie s prioritou C a obě připravované
aktualizace s vazbami (suchý běh nad živou DB 20. 11. 2026: 22 nových
dokumentů, z toho 7 této větve, 4 vazby, 2 stavy; vazby slovenských znění
se vyřeší až po korekcích kroku 0-zbytek). Pro větev `feature/mpo-strategie-c`
je před ním třeba zkopírovat plné texty z `data/fulltext_mpo_strategie_c/`.

`apply_manual_corrections.py` založí pro opravené dokumenty typ „Strategie“
jako nový řádek; `backfill_strategies.py` jej sloučí s přejmenovaným
typem.

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
  ČSN ISO 19880-1 pod neexistujícím označením ČSN EN ISO 19880-1 (#3;
  opraveno v kroku 1 – opravy dat).
* *Fronta kandidátů.* Pro zdroj „MPO/CDV 30. 4. 2026“ je připraveno 57
  kandidátů s úředním názvem, adresou a platností (zakonyprolidi.cz, e-Sbírka,
  EUR-Lex, katalog ČAS): 31 českých předpisů, 2 akty EU, 21 norem ČSN
  a 3 kandidáti z uzávěru citací, jimž se jen doplní řádky tabulky do podkladů.
  Zápis do živé databáze provede `src/tools/mpo_tables.py import --apply`;
  na `h2regdocs_test` je vyzkoušen, včetně opakovaného běhu, který nic nezmění.
* *ERÚ a ČBÚ.* Kandidáti nesou navrženého původce (nový sloupec
  `DocumentCandidate.puvodce`), mezi nimi Energetický regulační úřad
  (6 kandidátů) a Český báňský úřad (6 kandidátů). Do `DocumentSource` se
  instituce zapíše s prvním přijatým dokumentem, aby veřejný filtr nenabízel
  instituci bez dokumentů.
* *Zlatý test.* `tests/test_mpo_golden.py` (součást `run_tests.py`) ověřuje
  nad `h2regdocs_test`, že každý řádek obou tabulek je dokumentem, kandidátem,
  nebo má uveden důvod, a že žádný dokument z tabulek z databáze nezmizel.

**Doplnění k 19. 11. 2026 (větev `feature/mpo-kandidati-doplnit`, živá DB
dosud nezapsána):** Podle rozhodnutí z téhož dne jsme frontu rozšířili
(podrobně `doc/MPO_TABULKY.md`, odstavec 3.1):

* *Původce nařízení vlády č. 191/2022 Sb.* je Ministerstvo práce a sociálních
  věcí, nikoli MPO uvedené v tabulce.
* *Novely LEX OZE.* Kandidáty jsou zákony č. 19/2023 Sb. (LEX OZE I),
  č. 469/2023 Sb. (LEX OZE II) a č. 87/2025 Sb. (LEX OZE III); zkratky podle
  prezentace MPO z roku 2025, čísla a obsah ověřené na zakonyprolidi.cz
  a v e-Sbírce. Všechny tři novelizují energetický zákon i zákon
  o podporovaných zdrojích energie; přijetí kandidáta k nim založí vazby AMENDS.
  Slovník synonym je obsahuje již nyní (obecná položka „LEX OZE“ a položky
  „LEX OZE I“, „II“, „III“): označení, jež v databázi dosud není, nic nenajde,
  a jakmile editoři kandidáta přijmou, vyhledávání novelu najde bez další změny.
  Test `MpoCatalogTestCase` proto připouští v synonymech i označení kandidáta
  z `mpo_candidates.json`, jenž nebyl ve frontě zamítnut. Doplnit synonyma až
  po přijetí by vyžadovalo další změnu kódu, na niž by bylo snadné zapomenout.
* *Řady ČSN EN 60079 a ČSN EN 13445.* Kandidáty je 13 dalších platných částí
  řady ČSN EN 60079 (1, 2, 7, 10-1, 11, 14, 17, 19, 25, 29-0, 29-1, 29-2)
  a 8 částí řady ČSN EN 13445 (1, 2, 3, 4, 6, 8, 10, 11), jež databáze
  v českém převzetí nemá; ČSN EN ISO/IEC 80079-20-1, náhradu zrušené
  ČSN EN 60079-20-1, databáze již obsahuje. Jsou zdrojem `mpo` s řádky MPO-48
  a MPO-49 v podkladech, takže je hlídá i zlatý test.
* *Vydání ČSN EN 13445* (rozhodnutí z 20. 11. 2026): kandidáti nesou vydání
  platné a účinné dnes: části 1, 6, 8 a 10 vydání 11/2021, část 11 vydání
  2/2025, části 2, 3 a 4 konsolidované vydání se změnou A1 (označení
  `ČSN EN 13445-2+A1` 1/2024, `-3+A1` 9/2026, `-4+A1` 7/2026; vydání 2021
  bez změny je u nich již zrušené). Nové vydání všech částí s datem vydání
  1. 12. 2026 (Věstník 12/26) nabývá podle katalogu ČAS účinnosti
  **1. 1. 2027** (pole „Datum účinnosti“ na stránce normy), nikoli v prosinci
  2026; kandidát je nese v podkladech jako `upcoming_edition`. Totéž nové
  vydání má i ČSN EN 13445-5 (v databázi `ČSN EN 13445-5+A1`, #37) a nové
  vydání ČSN EN 1717+A1 z 12/2026 (#1456, označení opraveno z `ČSN EN 1717`,
  odstavec 5.1), obojí s účinností 1. 1. 2027.
  Z ostatních kandidátských norem má budoucí účinnost jen ČSN EN IEC
  60079-29-0 (nová norma, vydána 11/2026, účinná od 1. 12. 2026): kandidát
  je „dosud neúčinný“ a po přijetí bude dokument ve stavu „vyhlášený, dosud
  neúčinný“. Ostatní části ČSN EN 60079 a ČSN EN ISO 11114-4 novější vydání
  nemají (kontrola 20. 11. 2026, `check_csn_validity.py --editions`).
* *Přepnutí na nové vydání* (`src/tools/norm_editions.py`): nové vydání je
  další, neaktuální verzí dokumentu ve stavu `promulgated` s datem účinnosti
  a označením vydání. Kontrola stavu ČSN (`harvest_adapters.csn_state`,
  měsíčně) je zapisuje do `data/norm_validity_cache.json` jako `upcoming`;
  `backfill_document_states.py` z něj verzi doplní a v den účinnosti ji
  učiní aktuální (`active`) a dosavadní vydání `superseded`. Přijetí
  kandidáta normy založí obě verze hned (`app/candidates_admin.py`);
  přestavba databáze (`init_db.py`) postupuje stejně. ČSN nabývají účinnosti
  1. dnem měsíce, proto plánovač spouští promítnutí stavů 1. den v měsíci
  (`deploy/scheduler/h2db-states-monthly.timer`, `scheduled_harvest.sh
  states`; zatím neinstalováno, `doc/PROVOZ.md`, odstavec 5.2). Liší-li se
  označení nového vydání od označení dokumentu, změní se v den účinnosti
  i označení dokumentu; trvalá adresa (slug) zůstává (rozhodnutí
  z 20. 11. 2026, odstavec 5.1).
  Kandidáty v živé DB obnoví `mpo_tables.py import --apply` (nerozhodnutý
  kandidát zdroje `mpo` dostane nové podklady); `mpo_tables.py lookup
  --refresh-norms` je znovu zjistí z katalogu.
* *Opakovaný import.* `mpo_tables.py import` lze spouštět opakovaně: obnoví
  podklady nerozhodnutých kandidátů zdroje `mpo` a ostatní nemění.

Zbývá z kroku 1: zápis kandidátů do živé databáze, jejich posouzení editory
(potvrzení přijetí vyžaduje dva různé editory) a vysvětlení technických
komisí MPO.

### 4.3 Krok 2: Úpravy rozhraní

* jeden řádek na předpis, jazykové verze jen jako štítky CS/EN v tomto řádku;
* filtr původců rozdělit podle jurisdikce (ČR / EU / mezinárodní /
  normalizační orgány) a slovenské dokumenty ve výchozím zobrazení skrýt
  (rozhodnuto, viz „Slovenské dokumenty“ níže);
* zavést podtyp „akt v přenesené pravomoci / prováděcí akt“;
* ve vyhledávání využít klíčová slova a synonyma (RFNBO, AFIR, RED III,
  LEX OZE apod.).

**Stav k 19. 11. 2026 (větev `feature/mpo-krok2`, živá DB zatím beze změny):**

* *Jeden řádek na předpis.* Katalog zobrazuje jazykové varianty jednoho aktu
  (vazba `TRANSLATION_OF`, anglická varianta s označením `<značka> [EN]`)
  jako jeden řádek s českým názvem a štítky CS/EN, které vedou na stránky
  jednotlivých verzí. Dotaz i filtry se vyhodnocují nad všemi variantami,
  takže řádek se najde i tehdy, když dotazu odpovídá jen anglický název.
  Počet nalezených dokumentů je počet řádků; úvodní věta („Prohledejte …“)
  počítá rovněž předpisy, nikoli jazykové varianty (1461 místo 1486).
  Export (CSV, JSON, XML) ponechává jeden záznam na jazykovou verzi, protože
  každá má vlastní název a adresu.
* *Původci a jurisdikce.* Nabídka „Odpovědný orgán / DG“ je rozdělena do
  skupin Česká republika, Slovensko, Evropská unie, Mezinárodní organizace,
  Normalizační a odborné organizace a Zahraniční státní orgány podle
  datového souboru `data/source_groups.json`; nabízí jen původce, kteří mají
  aspoň jeden dokument (zmizela tak prázdná „Evropská centrální banka“).
  Nový filtr „Jurisdikce“ nabízí všechny jurisdikce, ČR, EU, mezinárodní
  a ostatní státy; volbu „Slovensko“ jen přihlášenému editorovi se
  zapnutým přepínačem slovenské legislativy (viz níže). Výchozí stav určuje
  konstanta `DEFAULT_JURISDICTION` v `app/catalog_filters.py` („vše“, tj.
  vše, co smí uživatel vidět); dřívější volbu „vše kromě Slovenska“ jsme
  zrušili, protože ji nahrazuje přepínač.
* *Slovenské dokumenty (rozhodnutí uživatele, větev `feature/mpo-sk-filtr`).*
  Slovenské dokumenty nejsou součástí veřejného katalogu. Za slovenský
  považujeme dokument s jurisdikcí `SK` nebo s označením končícím příponou
  `[SK]`, jíž značíme slovenské znění aktu EU (#84, `(EU) 2024/1788 [SK]`),
  ať by mu později byla přiřazena jakákoli jurisdikce. V živé databázi jde
  o 444 dokumentů typů norma (416, normy STN, TNI a TPP, z toho 411
  s původcem ÚNMS SR), zákon (12), vyhláška (9), nařízení vlády (1),
  rozhodnutí EU (2), nařízení EU (1), strategický dokument (1) a nezařazeno
  (2); patří mezi ně i slovenská znění aktů EU #57, #78, #84 a #88, která
  mají jurisdikci `SK`, takže je pravidlo zachytí i bez přípony `[SK]`.
  Jazyk sám o sobě nerozhoduje: 14 dokumentů se slovenským názvem
  a jinou jurisdikcí (normy DIN a DVGW, návrhy evropských norem prEN/FprEN,
  normy ISO, převzaté z tabulky Sinay se slovenským překladem názvu) nejsou
  slovenskou legislativou a zůstávají veřejné. Nepřihlášený uživatel
  slovenské dokumenty nevidí v seznamu, ve vyhledávání, v exportech CSV,
  JSON a XML, v nabídce jurisdikcí (volba „Slovensko“), v nabídce původců
  (skupina „Slovensko“ a ÚNMS SR mezi normalizačními orgány zmizí, protože
  nabídka uvádí jen původce s alespoň jedním viditelným dokumentem),
  v nabídce klíčových slov (např. „STN (prijatá v sústave)“) ani v počtech
  na úvodní stránce: místo 1461 předpisů, z toho 1276 platných, vidí 1017,
  z toho 840 platných. Přihlášenému editorovi (relace z `app/admin.py`)
  nabízí formulář katalogu přepínač „Zahrnout i slovenskou legislativu“
  (parametr adresy `sk=1`, přenáší se do stránkování i exportu); bez
  přihlášení se parametr `sk=1` i `jurisdikce=sk` ignoruje.
  *Přímý odkaz* na stránku slovenského dokumentu (`/dokument/<slug>`)
  i na jeho text funguje i nepřihlášenému: dokument není tajný, odkazy
  na něj mohou existovat a jeho skrytí by rozbilo trvalé adresy. Stránka
  nese upozornění „Slovenský dokument. Ve veřejném katalogu se nezobrazuje,
  stránka je dostupná jen přímým odkazem.“ *Vazby* na slovenské dokumenty
  se nepřihlášenému ve výpisech nezobrazují, a to na stránkách dokumentů
  (v živé databázi 156 vazeb mezi slovenským a jiným dokumentem: 110 `ADOPTS`
  norem STN k normám EN, 31 `IMPLEMENTS` slovenských předpisů ke směrnicím EU,
  14 `NATIONAL_EQUIVALENT`, 1 `REPEALS`; stejně se skryjí slovenská znění aktů
  EU, propojí-li je souběžná větev vazbou `TRANSLATION_OF`, a to i ze štítků
  jazykových verzí v řádku katalogu) i na stránkách procesů (12 odkazů na
  slovenské normy ve 4 procesních uzlech). Přihlášený editor vidí vazby
  vždy. Rozhodnutí o tom, co je slovenský dokument, je v `is_slovak()`
  a `public_condition()` v `app/catalog_filters.py`.
* *Podtyp aktů EU.* Nový sloupec `Document.eu_act_subtype`
  (`delegated` / `implementing`) určuje `src/tools/eu_act_subtype.py` podle
  ELI v adrese (`eli/reg_del/…`), jinak podle úředního názvu („v přenesené
  pravomoci“, „Delegované nařízení“, „Prováděcí nařízení“, „Commission
  Implementing Regulation“, slovensky „vykonávacie“); rozhoduje první
  zmínka v názvu, aby se prováděcí nařízení, které mění akt v přenesené
  pravomoci, nezařadilo chybně. CELEX oba podtypy nerozlišuje. Podtyp se
  určuje v pipeline (`init_db.py` při každé přestavbě) a pro existující
  databázi migrací `src/tools/backfill_eu_act_subtype.py`; katalog jej jen
  čte, a dokud sloupec v databázi chybí, nabídku podtypů nezobrazí.
  V nabídce typů přibyla skupina „Podtyp aktu EU“ s položkami „Akt
  v přenesené pravomoci (EU)“ (5 předpisů: 2023/1184, 2023/1185, 2018/674,
  2019/1745, 2025/656) a „Prováděcí akt (EU)“ (11 řádků, 17 dokumentů
  včetně anglických variant); řádek takového aktu nese štítek podtypu.
* *Synonyma.* Slovník `data/search_synonyms.json` přiřazuje zkratkám
  a ustáleným názvům hledané výrazy a označení dokumentů: RFNBO
  (2023/1184, 2023/1185, 2018/2001, 2023/2413 a výraz „nebiologického
  původu“), AFIR (2023/1804), AFID, RED II, RED III (2023/2413), LEX OZE
  (165/2012 Sb. a 458/2000 Sb., od 19. 11. 2026 i novely LEX OZE I–III,
  odstavec 4.2), TEN-E, plynárenský balíček, ReFuelEU, ATEX a PED. Zkratka se hledá jako celé slovo („RED II“ nenajde RED III).
  Pod výsledky se zobrazí, která synonyma byla použita. Vyhledávání nově
  prochází i označení dokumentu. Dotaz „RFNBO“ tak vrací 4 řádky (oba akty
  v přenesené pravomoci, RED II a RED III), každý předpis jednou.

Ke spuštění na živé databázi (po sloučení větve, před `git pull`
v hlavním stromu nebo hned po něm; katalog bez sloupce funguje, jen nenabízí
podtypy):

```
.venv/bin/python src/tools/backfill_eu_act_subtype.py            # dry run: 22 dokumentů
.venv/bin/python src/tools/backfill_eu_act_subtype.py --apply    # po záloze DB
```

Zjištěno při práci: dokument #110 má označení `2012/18/EU` (Seveso III), ale
název směrnice 2014/34/EU (ATEX), obdobně jako #130 v odstavci 4.1; do slovníku
synonym proto Seveso zatím nezařazujeme. (Opraveno v kroku 1 – opravy dat,
odstavec 4.1.)

### 4.4 Krok 3: Průběžná aktualizace

* sloučit větev `feature/h2db-sources` do `master` (PR), provést první běh
  sběru nad živou databází (odhadem 247 kandidátů, z toho 111 v první
  úrovni) a nastavit plánovač podle `doc/DATABASE_SCOPE.md`, odstavec 6
  (týdně e-Sbírka, EUR-Lex a VeKLEP, měsíčně normy);
* u každého dokumentu zobrazovat datum poslední kontroly;
* doplnit editorské rozhraní pro převod návrhu na vyhlášený předpis;
* sepsat pro garanta krátký provozní dokument: kdo frontu kandidátů
  posuzuje, jak často a podle jakých zdrojů.

**Stav k 19. 11. 2026 (větev `feature/mpo-krok3`, živá DB jen čtena):**
větev obsahuje sběr zdrojů (`feature/h2db-sources`) i krok 0 a je připravena
k žádosti o sloučení do `master`. Přibyla stránka *Připravované dokumenty*
(`/admin/drafts`) pro převod návrhu na vyhlášený předpis se schválením dvěma
editory a na stránce každého dokumentu údaj „Poslední kontrola stavu“ (datum
a zdroj kontroly). Postup prvního ostrého běhu, odhad nanečisto nad živou
databází (252 kandidátů, z toho 112 v pásmu přímého vztahu) a návrh plánovače
(`deploy/scheduler/`, neinstalováno) popisuje `doc/DATA_SOURCES.md`,
odstavec 8.17. Provozní dokument pro garanta a rozhodnutí o plánovači zůstávají
otevřené.

### 4.5 Krok 4: Před opětovným předáním

* převést všechny scénáře z připomínek MPO do prohlížečových testů
  (`tests/e2e/`) se snímky obrazovky;
* nechat aplikaci před předáním projít někým mimo vývojový tým (interní
  akceptace);
* připravit pro MPO přehled vypořádání jednotlivých připomínek
  (tento dokument v upravené podobě) jako podklad k telekonferenci.

**Stav k 19. 11. 2026 (větev `feature/mpo-krok2`):** scénáře připomínek 1–6
jsou v `tests/e2e/test_mpo_comments.py` a běží v rámci
`src/tools/run_tests.py` nad kopií živé databáze (s opravami kroku 0):

| Připomínka | Scénář | Snímek |
|---|---|---|
| 1 (ECB) | filtr původce „Evropská centrální banka“ nevrací duplicity; původce bez dokumentů se nenabízí | `MpoCommentsTestCase-ecb-originator.png` |
| 2, 3 (RFNBO) | „RFNBO“ vrací jeden řádek na předpis, mezi nimi 2023/1184 a 2023/1185; RED III se štítky CS/EN, štítek EN vede na anglickou verzi | `…-rfnbo.png`, `…-rfnbo-red3-row.png`, `…-rfnbo-red3-english.png` |
| 3 | v nabídce typů lze vybrat „Akt v přenesené pravomoci (EU)“ | `…-filter-delegated.png` |
| 4 (MD) | nabídka původců je seskupená, bez holé zkratky („MD“ apod.), Ministerstvo dopravy je mezi českými orgány | `…-filters.png` |
| 5 (dráhy) | zákony 266/1994 Sb. a 426/2021 Sb. mají původce Ministerstvo dopravy, v řádku i na stránce dokumentu | `…-railway-act.png`, `…-railway-act-page.png` |
| 6 (hláška) | stránky energetického zákona a RED III (obě jazykové verze) neobsahují „Stav ke dni 30.6.2025“ | `…-stale-note-*.png` |
| 6 (obecně) | žádný popis, název ani export neobsahuje „doc/PLAN.md“; stránky vodíkových strategií | `…-strategy-*.png` |
| — | filtr jurisdikce; telefon 390 px bez vodorovného posuvníku | `…-jurisdiction-cz.png`, `…-rfnbo-phone.png` |

Snímky ukládá `run_tests.py` do `data/test_screenshots/<datum_čas>/`.
Připomínky 7–10 (připravované předpisy, chybějící předpisy z tabulek MPO
a CDV, kategorie „Strategie“, aktuálnost) jsou obsahové a patří do kroků 1
a 3; scénáře k nim přibudou s nimi. Zbývá interní akceptace a přehled
vypořádání pro MPO.

### 4.6 Harmonogram

Kroky 0 až 3 jsou hotové na větvích sloučených do integrační větve
`feature/mpo-integrace` (testy prošly), krok 0 je v živé databázi zapsán
jen zčásti (odstavec 4.1). Zbývá sloučení do `master`, zápis do živé
databáze, posouzení kandidátů editory, doplnění strategií a interní
akceptace. Harmonogram jsme proto zkrátili na nejkratší realistický;
v podobě pro MPO (bez interních údajů) je v `doc/MPO_VYPORADANI.md`,
odstavec 6.

| Termín | Krok | Obsah | Podmínka |
|---|---|---|---|
| 19. 11. 2026 (provedeno) | krok 0, první část | opravy v živé DB (záloha `before_mpo_krok0`) | — |
| do 25. 11. 2026 (st) | sloučení a nasazení | PR integrační větve (kroky 0-zbytek, 1, 2, 3 a souběžné větve: skrytí SK, strategie, opravy dat) do `master`; `git pull` v hlavním stromu; záloha; `apply_manual_corrections.py --apply`; `backfill_eu_act_subtype.py --apply`; schéma a stavy podle `doc/DATA_SOURCES.md`, odst. 8.17, kroky 2–3; `mpo_tables.py import --apply`; první ostrý běh sběru (kroky 5–8) | `run_tests.py` zelený nad sloučenou verzí; záloha živé DB před každým zápisem; oba editorské účty se přihlásí |
| do 27. 11. 2026 (pá) | odeslání vypořádání | `MPO_VYPORADANI.md` a `PROVOZ.md` (případně převedené do DOCX podle `TEXT_STYLE.md`) s průvodním e-mailem (`doc/MPO_EMAIL_NAVRH.md`) | nasazení podle předchozího řádku; jména garanta a editorů doplněna |
| 1.–4. 12. 2026 | jednání s MPO | vypořádání, otázky z odst. 7 vypořádání, dohoda o postupu opětovného schválení V01, editorské účty pro MPO; navrženo út 1. 12., st 2. 12. nebo čt 3. 12. | časové možnosti MPO (posun jednání posouvá i předání) |
| do 11. 12. 2026 (pá) | krok 1 dokončení | posouzení 34 kandidátů MPO/CDV dvěma editory; přejmenování typu na „Strategie“ a 13 strategií A a B (připraveno); části ČSN EN 60079 a 13445; novely LEX OZE; oprava #110 a #140; vysvětlení jazykových verzí v aplikaci | dva editoři s kapacitou; posouzení nečeká na výklad MPO-27 a MPO-42 (odloženo) |
| do 18. 12. 2026 (pá) | krok 4 | posouzení 112 nálezů sběru v pásmu 1; e2e scénáře připomínek 7–10; interní akceptace osobou mimo vývojový tým; zapracování závěrů jednání | osoba pro akceptaci k dispozici 14.–18. 12.; závěry jednání bez rozsáhlých úprav |
| 22. 12. 2026 (út) | opětovné předání V01 | předání MPO postupem dohodnutým na jednání, s výsledky akceptace | akceptace bez závažných nálezů; dohoda o postupu schválení |
| do 15. 1. 2027 (pá) | provoz | posouzení zbylých nálezů sběru (pásmo 2, odhadem 140) | předání na něm nezávisí |

## 5. Rozhodnutí a otevřené otázky

Stav k 19. 11. 2026. Rozhodnutí uživatele z tohoto dne; jejich provedení
běží souběžně na samostatných větvích, a kde text na výsledku závisí, je
psán jako plán.

### 5.1 Rozhodnuto

* **Telekonference z června 2026 neproběhla.** Vypořádání je ve skluzu;
  jednání s MPO navrhujeme jako první krok po odeslání vypořádání, v prvním
  prosincovém týdnu (odstavec 4.6). Dokumenty pro MPO nepředpokládají, že
  jednání proběhlo.
* **Postup opětovného schválení V01** stanovíme až po vypořádání
  připomínek: po odeslání vypořádání požádáme MPO o dohodu na postupu
  a podkladech schválení (včetně potvrzení pro TAČR, o něž žádal e-mail
  z 26. 2. 2026).
* **Editorská práva pro MPO.** Pracovníci MPO mohou na vyžádání
  aplikačního garanta dostat editorský účet se stejnými oprávněními jako
  editoři řešitele, při zachování potvrzování každé změny druhým editorem
  (`doc/PROVOZ.md`, odstavec 2.1; `doc/MPO_VYPORADANI.md`, odstavec 4.5).
* **Slovenské dokumenty** jsou ve výchozím zobrazení katalogu skryté;
  přepínač „Zahrnout i slovenskou legislativu“ je jen pro přihlášené
  editory (provedeno, odstavec 4.3, „Slovenské dokumenty“).
* **Slovenská znění aktů EU** (#57, #78, #84, #88) mají označení
  `<značka> [SK]` a vazbu `TRANSLATION_OF` na české znění (provedeno,
  odstavec 4.1).
* **Původce zákona č. 250/2012 Z. z.** (#73) je Ministerstvo
  hospodárstva Slovenskej republiky (provedeno; v kroku 0 ÚRSO).
* **Původce nařízení vlády č. 191/2022 Sb.** je u kandidáta MPSV, shodně
  se zákonem č. 250/2021 Sb., který provádí (provedeno).
* **Novely LEX OZE** (19/2023 Sb., 469/2023 Sb., 87/2025 Sb.) a **další
  části řad ČSN EN 60079 (13) a ČSN EN 13445 (8)** jsou připraveny jako
  kandidáti (odstavec 4.2).
* **Typ „Strategie“:** typ „Strategický dokument“ je přejmenován na
  „Strategie“ a doplněno 13 strategií s prioritou A a B (příloha A
  `doc/MPO_VYPORADANI.md` jich uvádí 13, nikoli 11); kategorie má
  25 dokumentů (provedeno, odstavec 4.1).
* **Strategie s prioritou C** (20. 11. 2026): zařadit; doplněno pět sdělení
  Komise (příloha A jich s prioritou C uvádí pět, nikoli šest), kategorie má
  32 dokumentů (provedeno, odstavec 4.1).
* **Neschválené aktualizace strategií** (20. 11. 2026): Politika ochrany
  klimatu 2025–2050 a aktualizace Státní energetické koncepce jsou vedeny
  jako připravované dokumenty s vazbou na strategii, již mají nahradit
  (provedeno, odstavec 4.1).
* **Vydání ČSN EN 13445** (20. 11. 2026): kandidáti nesou platné vydání
  (2021, u částí 2–4 se změnou A1; část 11 vydání 2025), nové vydání 12/2026
  je v podkladech a databáze se na ně sama přepne dnem jeho účinnosti
  1. 1. 2027 (provedeno, odstavec 4.2; plánovač zatím neinstalován).
* **Termíny etap** podle odstavce 4.6.
* **Označení normy po přepnutí na nové vydání** (20. 11. 2026): mění se
  automaticky. Liší-li se označení vydání, jež nabývá účinnosti, od označení
  dokumentu (`ČSN EN 13445-2+A1` → `ČSN EN 13445-2`, nebo přibude `+A1`),
  `norm_editions.py` v den účinnosti změní `Document.identifier` i označení
  na začátku názvu; slug a tím trvalá adresa zůstávají, dosavadní vydání si
  ponechá své označení u nahrazené verze (`DocumentVersion.edition_label`),
  odkaz na stránku dosavadního vydání v katalogu ČSN online se přesměruje
  na nové vydání. Shoda s označením jiného dokumentu (podle kolace
  `utf8mb4_czech_ci`) přejmenování zabrání a běh ji vypíše. Aby změna
  přežila přestavbu databáze, zapíše se do `data/manual_corrections.json`
  (`znacka`, `slug`, `zdroj_autoritativni_url`), klíče dokumentu
  v `data/fulltext_manifest.json` se přejmenují a záznam
  v `data/norm_validity_cache.json` se přesune pod nové označení
  (provedeno; `doc/PROVOZ.md`, odstavec 5.2). Zkouška na testovací
  databázi s datem 1. 1. 2027: #37 `ČSN EN 13445-5+A1` → `ČSN EN 13445-5`
  (slug `csn-en-13445-5-a1`), #1456 bez změny označení.
* **Označení #1456** (20. 11. 2026): `ČSN EN 1717` opraveno na platné
  `ČSN EN 1717+A1` (katalog ČSN online: vydání 9/2026, účinné od
  1. 10. 2026; vydání ČSN EN 1717 z 11/2025, na něž vedl odkaz, bylo
  zrušeno 1. 10. 2026). Oprava je v `data/manual_corrections.json` (označení,
  odkaz na stránku vydání 9/2026, slug `csn-en-1717` zůstává). Nové vydání
  12/2026 má stejné označení `ČSN EN 1717+A1`; 1. 1. 2027 se na ně dokument
  přepne bez další změny označení (ověřeno na testovací databázi).
* **Nařízení CLP (ES) č. 1272/2008** (20. 11. 2026): doplněno české XHTML
  z Cellaru (23 MB); čitelný text dokumentu (stránka „text“ a vyhledávání)
  se nově tvoří z něj, PDF zůstává staženým originálem dokumentu
  (`Document.file_path`), stejně jako u ostatních aktů EU s PDF a HTML.
  Zdůvodnění a ověření úplnosti v `doc/CELLAR_FULLTEXT.md`, odstavec 5.
  Ukládáme původní znění z roku 2008, nikoli konsolidované (otázka
  v odstavci 5.3).

* **Plné texty z EUR-Lexu jen z Cellaru** (20. 11. 2026, `doc/CELLAR_FULLTEXT.md`):
  `fetch_fulltext.py` už EUR-Lex neotevírá v prohlížeči ani se na něj
  neobrací; adresy ELI a adresy Úředního věstníku (`?uri=OJ:L_…`) se
  dotazem SPARQL přeloží na číslo CELEX a text se stáhne z Cellaru. Úplnost
  textu z Cellaru byla ověřena porovnáním se všemi 288 uloženými soubory
  (jazyk, délka textu, přílohy, název): 68 shodných, 218 úplných, žádný
  kratší; tři uložené stránky byly neúplné. Celé číslo Úředního věstníku
  u 2014/34/EU nahradilo PDF směrnice. Manifest je přepnut na Cellar u všech
  505 stažených položek. Současně opravena chyba extraktoru, jenž
  u 33 souborů (21 aktů) vynechával přílohy (podrobně
  v `doc/CELLAR_FULLTEXT.md`).
* **Stránky slovenských dokumentů a vyhledávače** (20. 11. 2026): stránka
  slovenského dokumentu, jeho čitelný text i stažený soubor nesou pro
  nepřihlášeného návštěvníka `<meta name="robots" content="noindex">`
  a hlavičku `X-Robots-Tag: noindex`. Aplikace nemá mapu webu, `robots.txt`
  serveru vše povoluje; z veřejných stránek, exportů ani procesů na slovenské
  dokumenty odkazy nevedou (vazby a dokumenty procesů jsou skryté), takže
  vyhledávač je může najít jen přes odkaz zvenčí, nebo z doby před jejich
  skrytím — na webu `nahyc.fd.cvut.cz/h2db` (větev `master`) jsou v katalogu
  veřejně uvedené až do nasazení kroku 2. Pojistka `noindex` pokryje i tento
  případ (již zaindexovaná stránka vypadne při příštím průchodu robota).

* **Rozhodnutí z 20. 11. 2026:**
  * e-mail MPO půjde v kopii Ing. M. Revíkové, L. Svobodové (titul neznáme,
    neuvádíme) a P. Polanskému a T. Matochové z CDV (`doc/MPO_EMAIL_NAVRH.md`);
  * skripty pro ISO (`add_missing_iso_parents.py`), IEC, EIGA a DVGW zůstávají,
    jak jsou (rozhodnutí uživatele; servery nepřetěžovat). Asistent je
    nespouští ani nerozšiřuje — spouští je řešitel;
  * Slov-Lex (vykreslení v prohlížeči) a zakonyprolidi.cz (User-Agent
    prohlížeče) zůstávají, ochranu neobcházejí a fungují;
  * #3 `ČSN ISO 19880-1` si ponechá trvalou adresu `csn-en-iso-19880-1`
    (připnutý slug v korekci), stejně jako přejmenované normy.

### 5.2 Odloženo, vyřešíme později

* **Výklad řádků MPO-27 a MPO-42 tabulky MPO** (227/2015 Sb. místo
  277/2015 Sb.; 192/2022 Sb., případně i 191/2022 Sb.; `doc/MPO_TABULKY.md`,
  odstavec 2.1). Kandidáti jsou zařazeni podle názvu i čísla.
* **Označení předpisu EHK OSN č. 134:** přežívající dokument má označení
  `[2019/795]`; přejmenování na `EHK OSN č. 134` by změnilo i anglickou
  variantu a klíče plných textů.
* **Provozní otázky** (`doc/DATA_SOURCES.md`, odstavec 8.17;
  `doc/PROVOZ.md`, odstavec 9.3):
  * plánovač (časovač systemd, nebo crontab; na kterém serveru);
  * zapisování datových souborů měněných běhy v hlavním stromu do
    repozitáře, nebo jejich přesun mimo správu verzí;
  * zdroje IEC, EIGA a DVGW, jejichž skripty obcházejí ochranu proti
    robotům — navrženo je vypnout;
  * registrace k REST API e-Sbírky a e-Legislativy a žádost o přístup
    k TRIS;
  * četnost kontroly stavu ČSN a STN (v registru „na vyžádání“, návrh
    plánovače měsíčně).

### 5.3 Otevřeno

* **Neúřední překlad Vodíkové strategie EU (HYTEP, #1245)** zůstává
  samostatným dokumentem bez vazby na úřední české znění (#79): vazba
  `TRANSLATION_OF` by jej v katalogu skryla jako „českou verzi“ českého
  dokumentu a vhodnější typ vazby (neúřední překlad) číselník nemá.
* **Znění nařízení CLP:** Ukládáme původní znění z roku 2008 (CELEX
  `32008R1272`), nikoli konsolidované. Cellar vede konsolidovaná znění
  `02008R1272-<datum>`; ke 20. 11. 2026 je účinné znění ze 1. 7. 2026
  a připraveno znění k 1. 1. 2027. Přejít na konsolidované znění (a pak je
  při každé změně obnovovat), nebo ponechat původní znění s odkazem na
  konsolidované znění v EUR-Lexu? Totéž se týká i dalších často měněných
  aktů (REACH).
* **Usnesení vlády k aktualizacím SEK a Politiky ochrany klimatu:** číslo
  usnesení z prosince 2024, jímž vláda od aktualizací upustila, ani pozdější
  rozhodnutí jsme nedohledali; ověřit u MPO a MŽP. Text návrhu SEK není
  zveřejněn.
* **Text .docx:** 2. aktualizace NAP čisté mobility je zveřejněna jen ve
  formátu .docx, jejž `extract_fulltext.py` nečte.
* **Jména garanta, editorů a správce** doplní uživatel (značky
  `[DOPLNIT: jméno]` v `doc/PROVOZ.md`, odstavec 2).
* **Otázky pro jednání s MPO** (`doc/MPO_VYPORADANI.md`, odstavec 7):
  postup schválení V01, editorské účty pro MPO, převzetí tabulek jako
  referenčního souboru a jejich průběžné doplňování, lhůty posouzení
  kandidátů, normy podle technických komisí.
* **Zařazení původců do skupin** (`data/source_groups.json`): ÚNMS SR je
  mezi normalizačními orgány, nikoli ve skupině Slovensko (veřejnost jej
  od rozhodnutí o slovenských dokumentech nevidí, týká se jen editorů); DGUV, BAuA, PTB,
  OSHA, NIST, NASA a Sandia jsou „zahraniční státní orgány“. Ověřit.
* **Seveso III ve slovníku synonym:** záznam #110 je opraven (odstavec 4.1),
  synonymum „Seveso III“ lze doplnit.
