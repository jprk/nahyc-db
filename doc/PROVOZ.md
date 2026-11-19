# Provoz a udržování aktuálnosti databáze regulačních předpisů

> Historie dokumentu:  
> 2026-11-19 jprk Návrh první verze (podklad k vypořádání připomínek MPO k výsledku V01)

Dokument popisuje, jak se databáze regulačních předpisů a předrealizačních
procesů (výsledek V01 dílčího projektu DP004 centra NAHYC) udržuje aktuální:
z jakých zdrojů a jak často zjišťujeme nové dokumenty a změny stavu
dokumentů, kdo o zařazení dokumentu rozhoduje, jak se v databázi projeví
nový, novelizovaný nebo zrušený předpis a jak lze zjistit, kdy byl dokument
naposledy ověřen. Je určen garantovi databáze a editorům; slouží zároveň jako
odpověď na dotaz Ministerstva průmyslu a obchodu, jak bude zajištěna
aktuálnost předpisů.

Odstavce 1 až 9 popisují postup bez technických podrobností. Technické
údaje (nástroje, příkazy, datové soubory a tabulky) jsou v příloze A na
konci dokumentu.

U každého postupu odlišujeme, co platí k 19. 11. 2026, od toho, co teprve
zavádíme. Plánované stavy popisujeme budoucím časem; místa, jež doplníme po
dokončení rozpracovaných úprav, jsou označena `[DOPLNIT po kroku N]`.

## 1. Zásady

1. **Nic se do databáze nedostane automaticky.** Automatizované nástroje
   zdroje jen čtou a nálezy předkládají editorům. Nový dokument vznikne až
   rozhodnutím dvou editorů (odstavec 4); automatizovaně zachycená změna není
   právním posouzením.
2. **Každá změna má dva podpisy.** Přijetí nového dokumentu i oprava údajů
   existujícího dokumentu vyžadují návrh jednoho editora a potvrzení druhým,
   odlišným editorem. Databáze tuto podmínku sama vynucuje.
3. **Každé rozhodnutí se zaznamenává.** Kdo, kdy a co navrhl, potvrdil,
   zamítl nebo odložil, se ukládá do záznamu změn (auditního protokolu).
4. **Zaznamenává se i kontrola bez nálezu.** Doložený negativní výsledek
   („zdroj X jsme dne D prošli a nic nového nenašli“) je součástí tvrzení
   o úplnosti databáze.
5. **Zrušené dokumenty nemažeme.** Zrušený nebo nahrazený dokument zůstává
   v databázi se svým stavem a s vazbou na dokument, jenž jej zrušil nebo
   nahradil (odstavec 6).
6. **Před každým hromadným zápisem pořizujeme zálohu** databáze.

## 2. Role

| Role | Kdo | Odpovědnost |
|---|---|---|
| Garant databáze | [DOPLNIT: jméno, pracoviště řešitele] | Odpovídá za obsah a rozsah databáze; rozhoduje sporné případy; jednou za čtvrtletí vyhodnocuje úplnost (odstavec 8) a podává zprávu aplikačnímu garantovi. |
| Editoři (nejméně dva) | [DOPLNIT: jména] | Posuzují frontu kandidátů a navržené opravy; navrhují a potvrzují přijetí dokumentů; provádějí ruční kontroly zdrojů, jež automatizovat nelze. |
| Správce | [DOPLNIT: jméno] | Spouští nebo nastavuje pravidelné kontroly, pořizuje zálohy, sleduje chyby a dostupnost zdrojů, zakládá uživatelské účty editorů. |
| Aplikační garant (MPO) | Ing. Petr Mervart | Uplatňuje připomínky a požadavky na rozsah; navrhujeme, aby alespoň jeden z editorů byl z jeho okruhu (otevřená otázka, odstavec 9). |

K 19. 11. 2026 jsou v provozní databázi založeny dva uživatelské účty
editorů. Přijetí kandidáta vyžaduje dva různé editory; s jediným aktivním
editorem by tedy fronta kandidátů nemohla být vyřizována.

## 3. Sledované zdroje a četnost kontrol

Zdroje, z nichž zjišťujeme nové dokumenty a změny stavu, vede registr
sledovaných zdrojů (78 položek). U každého zdroje uvádí adresu, způsob
dotazování, co zdroj přináší, četnost kontroly a případné překážky
(například že provozovatel automatizovaný přístup zakazuje). Ochranu webů
proti robotům neobcházíme; takové zdroje kontrolují editoři ručně.

### 3.1 Co a jak často kontrolujeme

| Četnost | Zdroje | Co přinášejí |
|---|---|---|
| týdně | e-Sbírka, EUR-Lex (databáze Úřadu pro publikace EU), VeKLEP, otevřená data Poslanecké sněmovny a Senátu, Legislativní observatoř Evropského parlamentu, rejstříky Evropské komise (akty v přenesené pravomoci, komitologie, dokumenty Komise), kanály novinek s krátkou historií | nové předpisy, návrhy předpisů, změny stavu předpisů |
| měsíčně | Věstník ÚNMZ a novinky ÚNMZ, souhrnné seznamy harmonizovaných norem, katalog ČSN, katalog technických pravidel TPG, kanály novinek ministerstev a úřadů (MPO, MMR, MŽP, ERÚ, SÚIP, ČIŽP, ČOI, Drážní úřad, OTIF, ACER, Agentura EU pro železnice), stránky TIČR, HZS ČR, ČMI, MD (ADR); kontrola dostupnosti všech zdrojů | nové a nahrazené normy, technická pravidla, metodiky, změny dohod ADR a RID |
| čtvrtletně | zdroje kontrolované ručně (např. EHK OSN — předpisy WP.29 a ADR, registr Rady EU, IMO), strategie a koncepce (MPO, MŽP, MD, Evropská komise), měření úplnosti | strategie, mezinárodní předpisy na webech bez strojového přístupu, vyhodnocení úplnosti |

Četnost vychází z vymezení rozsahu pokrytí databáze (dokument „Rozsah
pokrytí databáze regulačních dokumentů“, odstavec 6) a z povahy zdrojů: kanál
novinek VeKLEPu například pokrývá jen zhruba dva týdny, a musí se proto
číst nejméně týdně.

### 3.2 Stav k 19. 11. 2026

* **Kontrola platnosti** předpisů ČR a EU je v provozu a naposledy proběhla
  27. 10. 2026 (747 předpisů ČR a EU — dokumenty databáze i kandidáti na
  doplnění, odstavec 5).
* **Fronta kandidátů** je v provozu; obsahuje 296 kandidátů, z nichž 295
  čeká na posouzení a 1 je navržen k přijetí. Pocházejí z kontroly úplnosti
  (288) a z kontroly platnosti (8).
* **Sběr ze sledovaných zdrojů** (34 zdrojů čtených pravidelně, 5 k dohledání
  na vyžádání, 16 ručně kontrolovaných) je vyvinut a vyzkoušen na testovací
  kopii databáze, do provozu však dosud uveden nebyl. Uvedeme jej do provozu
  v rámci vypořádání připomínek MPO [DOPLNIT po kroku 3: datum prvního
  ostrého běhu a počet nálezů].
* **Pravidelné automatické spouštění** kontrol na serveru zavedeno není;
  kontroly spouští správce ručně. O plánovači a jeho provozovateli zbývá
  rozhodnout (odstavec 9). Dokud plánovač nebude zaveden, odpovídá za
  dodržení četnosti podle odstavce 3.1 správce.

## 4. Fronta kandidátů

Fronta kandidátů je jedinou cestou, jíž do databáze vstupují nové dokumenty.
Je přístupná přihlášeným editorům v editorské části aplikace.

### 4.1 Odkud kandidáti pocházejí

1. **Sledované zdroje** — Nález ze zdroje podle odstavce 3 (nový předpis,
   návrh předpisu, nová norma).
2. **Kontrola úplnosti** — Předpis, jejž citují texty dokumentů v databázi
   (nejméně dva dokumenty, nikoli jen jako novelu), ale databáze jej neobsahuje.
3. **Kontrola platnosti** — Předpis, jenž zrušil dokument databáze, ale sám
   v databázi chybí.
4. **Ruční návrh editora** — Například dokument z referenčního souboru MPO
   a CDV nebo strategie z rešerše.

Týž dokument nalezený více zdroji je jedním kandidátem; u kandidáta se
připisují doklady ze všech zdrojů (zdroj, datum, adresa, doslovný úryvek).
Kandidát, o němž editoři již rozhodli, se při dalším nálezu znovu neotevře.

### 4.2 Stavy kandidáta

| Stav | Význam | Kdo jej mění |
|---|---|---|
| nový | čeká na posouzení | — |
| navržen k přijetí | jeden editor navrhl přijetí a vyplnil údaje budoucího dokumentu | editor |
| přijat | druhý, jiný editor návrh potvrdil; dokument vznikl | druhý editor |
| zamítnut | dokument do databáze nepatří (s odůvodněním) | jeden editor; lze znovu otevřít |
| odložen | rozhodnutí vyžaduje další podklady | jeden editor; lze znovu otevřít |

### 4.3 Postup posouzení

1. Editor ověří dokument v autoritativním zdroji (e-Sbírka, EUR-Lex, katalog
   norem, stránky vydavatele) a porovná označení, název a stav.
2. Posoudí věcnou příslušnost podle deseti věcných okruhů a typů dokumentů
   vymezených v dokumentu „Rozsah pokrytí databáze regulačních dokumentů“
   (výroba, skladování, přeprava,
   plnění do vozidel, provoz vozidel, využití mimo vozidla, bezpečnost,
   stavební řízení a umístění, energetika, životní prostředí). Obecný předpis,
   jenž se na vodíková zařízení vztahuje, do databáze patří, i když vodík
   výslovně nezmiňuje; jeho novela, jež se vodíku netýká, patrně nikoli.
3. Ověří, zda dokument v databázi již není pod jiným označením nebo v jiném
   jazyce.
4. Navrhne přijetí s úplnými údaji (označení, úřední český název, typ,
   odpovědná instituce, jazyk, adresa, věcný okruh) nebo kandidáta zamítne či
   odloží s odůvodněním.
5. Druhý editor návrh zkontroluje a potvrdí, nebo jej vrátí.

Po potvrzení dokument vznikne v databázi ihned, je veřejně viditelný
a zapíše se i do podkladů, z nichž lze databázi znovu sestavit, takže jej
případné nové sestavení neodstraní. Jeho plný text se stáhne při nejbližším
stahování plných textů (u norem se plný text neuchovává).

### 4.4 Lhůty

Navrhujeme, aby editoři kandidáty z týdenních zdrojů posoudili do dvou
týdnů od zachycení a ostatní do konce kalendářního čtvrtletí. Lhůty jsou
návrhem k projednání s aplikačním garantem [DOPLNIT po dohodě s MPO].

### 4.5 Opravy údajů

Opravy údajů existujících dokumentů (název, popis, odpovědná instituce,
typ, jazyk aj.) se schvalují stejně: jeden editor opravu navrhne, druhý ji
potvrdí. Dokumenty s pravděpodobnou vadou údajů nesou příznak ke kontrole
s důvodem; k 19. 11. 2026 jich je 558, převážně jde o chybějící popis.

## 5. Kontrola platnosti a stavy dokumentů

### 5.1 Stavy

| Stav | Význam |
|---|---|
| připravovaný | návrh v legislativním procesu (návrh zákona, návrh Komise, návrh normy prEN) |
| vyhlášený, dosud neúčinný | platný předpis s odloženou účinností |
| účinný | předpis, jenž se použije |
| nahrazený | dokument nahrazený novějším vydáním (u norem a strategií) |
| zrušený | předpis, jenž se již nepoužije |

Úvodní stránka aplikace počítá jen účinné dokumenty; stránka dokumentu
uvádí stav každé jeho verze a u zrušeného předpisu vazbu „je zrušen
předpisem“. K 19. 11. 2026 má aktuální verze 1300 dokumentů stav účinný,
151 připravovaný (vesměs návrhy norem) a 35 zrušený; 20 zrušených předpisů
je propojeno s předpisem, jenž je zrušil.

### 5.2 Jak kontrola probíhá

1. U předpisů EU zjišťujeme v databázi Úřadu pro publikace EU, zda je akt
   v platnosti, kdy platnost skončila a kterým aktem byl zrušen.
2. U českých předpisů zjišťujeme v otevřených datech e-Sbírky, od kdy a do
   kdy je předpis účinný; předpis, jenž jej zrušil, doplňujeme ze stránek
   Zákony pro lidi.
3. Výsledek se ukládá s datem kontroly; předpis se znovu ověřuje, je-li
   výsledek starší než 30 dní.
4. Ze změn se odvodí stavy dokumentů: zrušený předpis dostane stav
   „zrušený“ a vazbu na zrušující předpis, je-li v databázi; chybí-li
   zrušující předpis, stane se kandidátem ve frontě (odstavec 4.1, bod 3).

Kontrola dosud nepokrývá normy (změny stavu norem z Věstníku ÚNMZ se
zatím jen ukládají a do stavů dokumentů se nepromítají), strategie
a technická pravidla a slovenské předpisy. Rozšíření kontroly na normy
a strategie [DOPLNIT po kroku 3].

## 6. Co se stane s novým, novelizovaným a zrušeným předpisem

| Událost | Kde ji zachytíme | Co se stane v databázi |
|---|---|---|
| Návrh předpisu se objeví ve VeKLEPu nebo jako sněmovní tisk | týdenní sběr návrhů | Kandidát s označením „návrh“; po přijetí dokument ve stavu „připravovaný“ s vazbou na předpisy, jež mění. |
| Návrh je schválen a vyhlášen ve Sbírce | e-Sbírka (týdně); otevřená data Sněmovny vážou vyhlášený předpis k tisku | Dnes nový kandidát; připravovaný dokument převede editor na vyhlášený. Automatické propojení návrhu s vyhlášeným předpisem plánujeme [DOPLNIT po kroku 3]. |
| Nový předpis EU (nařízení, směrnice, akt v přenesené pravomoci) | EUR-Lex a rejstříky Komise (týdně) | Kandidát; po přijetí dokument ve stavu „účinný“ nebo „vyhlášený, dosud neúčinný“. U směrnice editor sleduje transpozici do českého práva. |
| Novela předpisu, jejž databáze má | e-Sbírka, EUR-Lex | Novela, jež se týká vodíku nebo věcných okruhů, se stane kandidátem a po přijetí je propojena vazbou „mění“; konsolidované znění odkazuje do autoritativního zdroje. |
| Předpis nabude účinnosti | kontrola platnosti | Stav „vyhlášený, dosud neúčinný“ se změní na „účinný“. |
| Předpis je zrušen | kontrola platnosti | Stav „zrušený“, vazba na zrušující předpis; dokument zůstává v databázi. |
| Norma je nahrazena novým vydáním | Věstník ÚNMZ (měsíčně) | Nové vydání jako kandidát; starší vydání bude vedeno jako nahrazené [DOPLNIT po kroku 3]. |
| Vláda nebo Komise přijme novou strategii | čtvrtletní kontrola, kanály novinek | Kandidát (ruční návrh editora); předchozí verze strategie bude vedena jako nahrazená. |

## 7. Jak zjistit, kdy byl dokument naposledy ověřen

K 19. 11. 2026:

* zápatí každé stránky aplikace uvádí datum a čas poslední změny databáze
  jako celku;
* stránka dokumentu uvádí stav jeho verzí, nikoli však datum, kdy byl stav
  naposledy ověřen;
* datum kontroly platnosti je evidováno u každého předpisu interně
  (poslední kontrola 27. 10. 2026), veřejně se však nezobrazuje.

Plánujeme, že stránka dokumentu bude uvádět datum poslední kontroly a zdroj,
v němž kontrola proběhla, a že bude zveřejněn přehled kontrol jednotlivých
zdrojů včetně kontrol bez nálezu [DOPLNIT po kroku 3]. Aplikační garant tak
bude moci u každého dokumentu ověřit, kdy a podle čeho byl naposledy
zkontrolován.

## 8. Měření úplnosti

Jednou za čtvrtletí garant vyhodnotí úplnost databáze kombinací nezávislých
kontrol:

1. **Referenční soubor** — Tabulky předpisů zpracované MPO a Centrem
   dopravního výzkumu (květen 2026) převezmeme jako referenční soubor;
   automatický test bude hlídat, že všechny jeho dokumenty databáze obsahuje
   [DOPLNIT po kroku 1].
2. **Uzávěr citací** — Předpisy citované v textech dokumentů databáze, jež
   databáze neobsahuje; nejčastěji citované se stávají kandidáty.
3. **Porovnání s registry** — U směrnic EU seznam českých prováděcích
   předpisů z EUR-Lexu, u českých předpisů vazby novelizací z e-Sbírky.
4. **Procesní vrstva** — Procesní uzel nebo technologie bez jediného
   regulačního dokumentu ukazuje na mezeru.

Výsledkem je přehled pokrytí po věcných okruzích a typech dokumentů
s datem kontroly. Úplnost netvrdíme absolutně; první porovnání s tabulkou
MPO ukázalo, že uzávěr citací sám o sobě nepostačuje (z 42 českých předpisů
tabulky jich v databázi chybělo 27).

## 9. Otevřené otázky

1. **Plánovač kontrol** — Kdo bude provozovat pravidelné spouštění kontrol
   na serveru a kde bude databáze provozována po skončení projektu?
2. **Editoři** — Jména garanta a editorů; účast editora z okruhu
   aplikačního garanta.
3. **Lhůty posouzení kandidátů** podle odstavce 4.4.
4. **Registrace** k rozhraní e-Sbírky a e-Legislativy (podání Ministerstvu
   vnitra datovou schránkou); e-Legislativa postupně nahrazuje VeKLEP.
5. **Zdroje za ochranou proti robotům** (EHK OSN, registr Rady EU, Slov-Lex,
   IEC) — Ponechat ruční kontrolu, nebo požádat provozovatele o přístup?

## Příloha A: Technické údaje

Údaje v této příloze slouží správci a vývojářům. Nástroje jsou v adresáři
`src/tools/` hlavního stromu a spouštějí se jeho interpretem
(`.venv/bin/python`); bez volby `--apply` provádějí jen suchý běh. Účet
k databázi se čte ze souboru `.env` (pro testovací databázi `.env.test`,
volba `--env-file`).

### A.1 Databáze

| Tabulka | Účel |
|---|---|
| `Document`, `DocumentVersion` | dokumenty a jejich verze; stav v `DocumentVersion.lifecycle_state` (`active`, `promulgated`, `draft`, `superseded`, `repealed`) |
| `document_relation` | vazby `AMENDS`, `REPEALS`, `IMPLEMENTS`, `TRANSLATION_OF` aj. |
| `DocumentCandidate` | fronta kandidátů (stavy `new`, `proposed`, `accepted`, `rejected`, `deferred`; podmínka `chk_dc_distinct_reviewers`) |
| `ReviewItem` | navržené opravy údajů (podmínka `chk_ri_distinct_reviewers`) |
| `User`, `AuditLog` | účty editorů a záznam rozhodnutí |

Sloupec `Document.provenance` nese původ záznamu a veřejně se nezobrazuje.
Zálohy: `backups/h2regdocs_<datum>_<čas>_<důvod>.sql.gz` (mimo git).

### A.2 Nástroje

| Nástroj | Účel | Četnost |
|---|---|---|
| `check_validity.py [--max-age 30]` | kontrola platnosti (Cellar, e-Sbírka, zakonyprolidi.cz) → `data/validity_cache.json` | týdně |
| `backfill_document_states.py --apply` | promítnutí výsledků do `lifecycle_state` a vazeb `REPEALS` (`data/document_relations_validity.json`) | po kontrole platnosti |
| `citation_closure.py` | uzávěr citací → `data/citation_closure.json`, `data/citation_closure_candidates.csv` | čtvrtletně |
| `import_candidates.py --apply` | kandidáti z uzávěru citací a kontroly platnosti do `DocumentCandidate` | po předchozích dvou |
| `apply_manual_corrections.py --apply` | promítnutí ručních korekcí `data/manual_corrections.json` do živé databáze | při změně souboru |
| `src/db/dbuser_add.py <login> "<jméno>" <email> --apply` | založení účtu editora | podle potřeby |
| `harvest_sources.py --cadence <četnost> --apply` | sběr ze sledovaných zdrojů do fronty kandidátů (větev `feature/h2db-sources`, do `master` v kroku 3) | podle `cadence` |
| `harvest_sources.py --checklist`, `--record <zdroj> --note … --found N` | seznam ručně kontrolovaných zdrojů a záznam ruční kontroly | čtvrtletně |
| `check_sources.py --apply` | kontrola dostupnosti adres registru | měsíčně |

Registr zdrojů: `data/monitored_sources.json` (popis v `doc/DATA_SOURCES.md`
na větvi `feature/h2db-sources`); záznam běhů a ručních kontrol
`data/source_checks.jsonl` (jen připisování). Přijaté kandidáty zapisuje
editorská aplikace do `data/accepted_candidates.json`, potvrzené opravy do
`data/manual_corrections.json`; oba soubory čte sestavení databáze
(`build_unified_db.py`).

### A.3 Editorská aplikace

| Adresa | Účel |
|---|---|
| `/admin/login` | přihlášení editora |
| `/admin/candidates` | fronta kandidátů (filtr podle stavu a zdroje), detail s doklady, `/admin/candidates/new` ruční návrh |
| `/admin/review` | dokumenty s příznakem ke kontrole a návrhy oprav |
| `/admin/audit-log` | záznam rozhodnutí |

### A.4 Doporučený týdenní běh (do zavedení plánovače)

```
cd /home/laborator/DEVEL/nahyc-h2db
.venv/bin/python src/tools/check_validity.py
# záloha databáze do backups/ (mysqldump … | gzip)
.venv/bin/python src/tools/backfill_document_states.py --apply
.venv/bin/python src/tools/import_candidates.py --apply
.venv/bin/python src/tools/harvest_sources.py --cadence weekly --apply   # po kroku 3
```

Související dokumenty: `doc/DATABASE_SCOPE.md` (rozsah, stavy, četnost),
`doc/CITATION_CLOSURE.md` (uzávěr citací), `doc/DATA_SOURCES.md` (registr
zdrojů a plán vytěžování, větev `feature/h2db-sources`),
`doc/MPO_VYPORADANI.md` (vypořádání připomínek MPO).
