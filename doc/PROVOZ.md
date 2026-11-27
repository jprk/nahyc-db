# Provoz a udržování aktuálnosti databáze regulačních předpisů

> Historie dokumentu:  
> 2026-11-19 jprk Návrh první verze (podklad k vypořádání připomínek MPO k výsledku V01)  
> 2026-11-19 jprk Doplněn stav po krocích 1 až 3, editorský přístup pro MPO, termíny nasazení  
> 2026-11-20 jprk Konsolidovaná znění CLP a REACH, termín instalace plánovače a nouzový postup  
> 2026-11-21 jprk Stav po nasazení 20. 11. 2026, první běh sběru a automatické předtřídění fronty kandidátů; plánovač dosud nenainstalován, kontroly se spouštějí ručně  
> 2026-11-26 jprk Stav po nasazení 26. 11. 2026: kontrola záznamů (zásada 7, odstavec 4.7), klíčová slova a oblasti katalogu, čísla ověřená nad provozní databází

> **Plánovač je třeba nainstalovat do konce prosince 2026.** Dne 1. 1. 2027
> se automaticky přepínají normy ČSN EN 13445 a ČSN EN 1717+A1 na vydání
> 12/2026 a nařízení CLP na konsolidované znění k 1. 1. 2027; bez plánovače
> se nic z toho nestane. Nebude-li plánovač do té doby nainstalován, provede
> správce 2. 1. 2027 nouzový postup podle odstavce 5.4.

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

Stav popisujeme k 26. 11. 2026. Popsané úpravy jsme nasadili do veřejné
verze aplikace a zapsali do provozní databáze 20. 11. 2026 (kontrola
platnosti, sběr zdrojů, fronta kandidátů) a 23. a 26. 11. 2026 (kontrola
záznamů, klíčová slova a oblasti katalogu); čísla jsme ověřili dotazem nad
provozní databází 26. 11. 2026. Od toho odlišujeme, co teprve
zavádíme, především pravidelné automatické spouštění kontrol (plánovač),
jež dosud nainstalováno není. Plánované stavy popisujeme budoucím časem.

## 1. Zásady

1. **Nic se do databáze nedostane automaticky.** Automatizované nástroje
   zdroje jen čtou a nálezy předkládají editorům. Nový dokument vznikne až
   rozhodnutím dvou editorů (odstavec 4); automatizovaně zachycená změna není
   právním posouzením. Automatický navrhovatel (odstavec 4.4) smí být prvním
   navrhovatelem přijetí, potvrzuje však vždy člověk.
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
7. **Jazykový model nesmí dodávat název ani popis bez podkladu.** Název
   dokumentu přebíráme z úředního registru (Cellar, e-Sbírka, katalog ČAS,
   otevřená data ISO, vydavatel dokumentu), popis z anotace zdroje nebo
   z textu dokumentu. Cokoli, co model odvodí (shrnutí, klíčová slova,
   doporučení), označujeme jako neověřené a nikdy tím nenahrazujeme údaj
   z registru. Pravidlo zavádíme po kontrole záznamů z 23. 11. 2026
   (`doc/KONTROLA_ZAZNAMU.md`): model k holému číslu předpisu doplnil název
   jiného předpisu a popisy, které dokumentu neodpovídaly.

## 2. Role

| Role | Kdo | Odpovědnost |
|---|---|---|
| Garant databáze | Mgr. Vladimír Kremlík (RICE) | Odpovídá za obsah a rozsah databáze; rozhoduje sporné případy; jednou za čtvrtletí vyhodnocuje úplnost (odstavec 8) a podává zprávu aplikačnímu garantovi. |
| Editoři řešitele (nejméně dva) | Dr. Bronislav Vahalík (CDV), Ing. Jan Sochor (HYTEP) | Posuzují frontu kandidátů, připravované dokumenty a navržené opravy; navrhují a potvrzují přijetí dokumentů a změny stavu; provádějí ruční kontroly zdrojů, jež automatizovat nelze. |
| Editoři MPO (volitelně) | pracovníci MPO určení aplikačním garantem (po dohodě s MPO) | Stejná oprávnění jako editoři řešitele (odstavec 2.1); mohou zejména navrhovat nové dokumenty a opravy údajů a potvrzovat návrhy ostatních editorů. |
| Správce | Dr. Jan Přikryl (RICE) | Spouští nebo nastavuje pravidelné kontroly, pořizuje zálohy, sleduje chyby a dostupnost zdrojů, zakládá uživatelské účty editorů. |
| Aplikační garant (MPO) | Ing. Petr Mervart | Uplatňuje připomínky a požadavky na rozsah; určuje, kteří pracovníci MPO dostanou editorský účet; dostává čtvrtletní zprávu o úplnosti. |

K 26. 11. 2026 jsou v provozní databázi založeny dva aktivní uživatelské
účty (správce a jeden editor řešitele) a neaktivní technický účet
automatického navrhovatele (odstavec 4.4), jenž se nepřihlašuje a nic
nepotvrzuje. <!-- OTEVŘENO bod 3: editorské účty --> Přijetí kandidáta vyžaduje dva různé editory; dva
účty pravidlu postačují, s jediným aktivním editorem by však fronta
kandidátů nemohla být vyřizována. Proto doporučujeme udržovat nejméně tři
aktivní editory.

### 2.1 Editorský přístup pro pracovníky MPO

Pracovníkům MPO nabízíme editorský přístup k databázi. Editor MPO se
přihlašuje v editorské části webové aplikace stejně jako editoři řešitele
a má stejná oprávnění: posuzuje kandidáty, navrhuje nové dokumenty
a opravy údajů, zaznamenává vyhlášení připravovaných předpisů a potvrzuje
návrhy jiných editorů. Pro editory MPO platí tytéž zásady jako pro ostatní
(odstavec 1): každou změnu jeden editor navrhne a druhý, odlišný editor ji
potvrdí, a každé rozhodnutí se zaznamenává. Návrh editora MPO tak potvrdí
editor řešitele, nebo jiný editor MPO, a naopak.

Účet zakládá správce na vyžádání aplikačního garanta (jméno a e-mailová
adresa pracovníka); úvodní heslo předá editorovi správce. Účet, jenž se již nepoužívá, správce deaktivuje; záznam
rozhodnutí editora zůstává zachován.

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

### 3.2 Stav k 26. 11. 2026

* **Kontrola platnosti** předpisů ČR a EU je v provozu a naposledy proběhla
  27. 10. 2026 (747 předpisů ČR a EU — dokumenty databáze i kandidáti na
  doplnění, odstavec 5).
* **Sběr ze sledovaných zdrojů** (34 zdrojů čtených pravidelně, 5 k dohledání
  na vyžádání, 16 ručně kontrolovaných) je v provozu. První běh nad
  provozní databází proběhl 20. 11. 2026: zapsal do fronty 242 nových
  kandidátů, mezi nimi 35 sněmovních tisků, 9 legislativních postupů EU,
  74 předpisů z otevřených dat e-Sbírky, 69 technických pravidel TPG
  a 22 norem a návrhů norem z Věstníku ÚNMZ; u čtyř norem zaznamenal změnu
  stavu. Souhrnné seznamy harmonizovaných norem Evropské komise se stáhnout
  nepodařilo (server odmítl dotaz pro přílišnou četnost požadavků,
  HTTP 429); zdroj se zkontroluje při dalším běhu. Kanál novinek VeKLEPu
  žádný nový návrh nepřinesl.
* **Kandidáti z tabulek MPO a CDV** (34 kandidátů s úředním názvem, adresou,
  platností a navrženou odpovědnou institucí) a kandidáti na další části
  řad ČSN EN 60079 a ČSN EN 13445 a na novely LEX OZE jsou od 20. 11. 2026
  ve frontě kandidátů.
* **Fronta kandidátů** je v provozu a obsahuje 597 kandidátů. Automatický
  navrhovatel 20. 11. 2026 předtřídil 592 z nich (odstavec 4.4): 242 navrhl
  k přijetí, 163 zamítl, 46 odložil a u 140 ponechal editorům doporučení
  jazykového modelu; jeden další kandidát byl navržen k přijetí již dříve.
  Dne 26. 11. 2026 přibylo pět neposouzených kandidátů z porovnání pokrytí
  tématu RFNBO s referenčním seznamem (odstavec 8). Přijetí žádného kandidáta dosud editor nepotvrdil;
  nálezy s přímým vztahem k databázi posoudí editoři do 18. 12. 2026,
  kandidáty z tabulek MPO a CDV do 11. 12. 2026 a ostatní do 15. 1. 2027.
  <!-- OTEVŘENO bod 3: editorské účty -->
* **Kontrola záznamů** proti úředním rejstříkům a mezi sebou (odstavec 4.7)
  proběhla nad celou databází 23. 11. 2026. Po opravách ověřených ve zdroji,
  sloučení duplicit a vyřazení 28 aktů EU mimo rozsah vede provozní databáze
  1432 záznamů (dříve 1506); zbylé nálezy u 36 dokumentů čekají na editory.
* **Klíčová slova a oblasti** má od 23. a 26. 11. 2026 všech 1432 dokumentů
  (odstavec 4.8). Oblast dosud nelze určit u 39 dokumentů; ty vedeme
  v pracovní oblasti, jež se veřejně nezobrazuje.
* **Pravidelné automatické spouštění** kontrol na serveru (plánovač)
  zavedeno není; kontroly, sběr i třídění fronty spouští správce ručně
  (příloha A.4). Konfigurace plánovače (denní, týdenní, měsíční
  a čtvrtletní běh se zálohou databáze před každým zápisem) je připravena,
  nainstalována však není (odstavec 9.2). Dokud plánovač nebude zaveden,
  odpovídá za dodržení četnosti podle odstavce 3.1 správce. Plánovač je
  třeba nainstalovat do konce prosince 2026; jinak správce 2. 1. 2027
  provede ruční běh podle odstavce 5.4.

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
| odložen | rozhodnutí vyžaduje další podklady | jeden editor, nebo automat podle odsouhlaseného pravidla; lze znovu otevřít |

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

### 4.4 Automatické třídění fronty

Nové kandidáty předtřídí technický účet „Automatický navrhovatel“ (přihlašovací
jméno `automat`; podrobný popis pravidel je v interním dokumentu
`doc/FRONTA_AUTOMAT.md`). Účet se nepřihlásí a nic nepotvrzuje. Podle
pravidel, jež řešitel předem schválil (`data/triage_rules.json`), smí navrhnout přijetí (například technických
pravidel TPG, dokumentů z tabulek MPO a CDV, jiné jazykové verze předpisu,
jejž databáze má, a zrušeného předpisu se stavem „zrušený“ a vazbou na předpis,
který jej zrušil), zamítnout duplicitu ve stejném jazyce a odložit novinku, jež
sama dokumentem není; ostatní kandidáty posoudí
jazykový model a jeho doporučení s jistotou a zdůvodněním se zobrazí editorům.
Každé rozhodnutí automatu nese poznámku s pravidlem a důvodem, v seznamu
i v auditním logu je označeno štítkem „automat“ a lze je vrátit
(**Vrátit návrh**, **Znovu otevřít**). Kandidáta, jejž editor znovu otevřel,
automat již nemění.

Návrhy automatu potvrzuje editor: ve filtru „návrhy automatu k potvrzení“
zaškrtne kandidáty, jež zkontroloval, a zvolí **Potvrdit přijetí vybraných**;
hromadně lze stejně odložit nebo (s důvodem) zamítnout. Každý kandidát se
zpracuje a do auditu zapíše zvlášť.

Předtřídění se spouští po každém sběru zdrojů a importu kandidátů; do
zavedení plánovače je spouští správce ručně (příloha A.4). První běh nad
provozní databází proběhl 20. 11. 2026 nad 592 kandidáty: podle pravidel
navrhl automat k přijetí 126 kandidátů (69 technických pravidel TPG,
53 kandidátů z tabulek MPO a CDV a souvisejících norem a novel LEX OZE,
3 návrhy předpisů a norem výslovně o vodíku a 1 zrušený předpis, vyhlášku
č. 513/2021 Sb. z tabulky MPO), 6 novinek
odložil; ze 459 kandidátů posouzených jazykovým modelem navrhl k přijetí
116, zamítl 163, odložil 40 a u 140 ponechal doporučení editorům. Vše je
vratné a přijetí každého kandidáta musí potvrdit editor.

### 4.5 Lhůty

Navrhujeme, aby editoři kandidáty z týdenních zdrojů posoudili do dvou
týdnů od zachycení a ostatní do konce kalendářního čtvrtletí. Lhůty jsou
návrhem k projednání s aplikačním garantem na jednání, jež navrhujeme na
první prosincový týden 2026; po dohodě je zde upřesníme.

### 4.6 Opravy údajů

Opravy údajů existujících dokumentů (název, popis, odpovědná instituce,
typ, jazyk aj.) se schvalují stejně: jeden editor opravu navrhne, druhý ji
potvrdí. Dokumenty s pravděpodobnou vadou údajů nesou příznak ke kontrole
s důvodem; k 26. 11. 2026 jich je 524, převážně jde o chybějící popis (491).
Dalších 36 navržených oprav předala editorům kontrola záznamů (odstavec 4.7).

Přihlášený editor najde tyto dokumenty v katalogu filtrem „Ke kontrole“
(parametr `kontrola`), který nabízí volby podle druhu důvodu, u každé
s počtem dokumentů (stav k 26. 11. 2026, celá databáze včetně slovenských
dokumentů):

| Volba | Hodnota parametru | Důvod obsahuje | Dokumentů |
|---|---|---|---|
| Vše ke kontrole | `vse` | jakýkoli důvod | 524 |
| Vyžaduje opravu (vady) | `oprava` | useknutý název, neplatná značka, nedohledaný gestor aktu EU | 5 |
| Nálezy kontroly záznamů | `kontrola-zaznamu` | „Kontrola záznamů: …“ | 36 |
| Odhadnutý jazyk | `jazyk` | „jazyk dokumentu byl automaticky odhadnut“ | 52 |
| Chybí popis | `popis` | „chybí popis/anotace dokumentu“ | 491 |

Dokument s více důvody spadá do více voleb. Filtr kombinujeme s typem,
jurisdikcí, oblastí i hledáním; export CSV, JSON nebo XML zúženého seznamu
slouží editorovi jako pracovní seznam, protože pro přihlášeného navíc
obsahuje označení, adresu záznamu a důvody kontroly. Katalog počítá řádky
předpisů (jazykové verze v jednom řádku), export jednotlivé dokumenty.
Návštěvníkovi se volba nezobrazí a parametr pro něj nic nemění.

### 4.7 Kontrola záznamů

Údaje dokumentů (označení, název, popis) kontrolujeme ve dvou vrstvách:

1. **Porovnání s úředními rejstříky a vnitřní kontroly** — Akty EU
   porovnáváme s databází Úřadu pro publikace EU (Cellar), normy ISO
   s otevřenými daty ISO a ostatní dokumenty s autoritativním názvem ze
   zdrojového webu; dále hledáme duplicity, useknuté názvy a úlomky řádků
   podkladových tabulek a návrhy norem, jež ISO mezitím vydala nebo zrušila.
2. **Posouzení jazykovým modelem** — Model dostane záznam s dostupnými
   podklady (úřední název, anotace, začátek textu) a posoudí, zda název
   a popis odpovídají dokumentu a jak dokument souvisí s vodíkovými
   technologiemi. Jeho posouzení je jen podnětem pro editora.

První kontrola nad celou databází proběhla 23. 11. 2026: nález mělo
151 dokumentů, z toho 47 chyb (název nebo popis jiného dokumentu). Každou
opravu jsme ověřili ve zdroji a zapsali do podkladů, z nichž lze databázi
znovu sestavit; popis bez doloženého zdroje jsme odstranili. Zbylé nálezy
jsme předali editorům jako navržené opravy údajů (odstavec 4.6). První
vrstvu budeme spouštět po každém přijetí kandidátů a spolu s týdenní
kontrolou platnosti, druhou po každé změně záznamů; do zavedení plánovače
je spouští správce ručně (příloha A.4).

### 4.8 Klíčová slova a oblasti

Každý dokument nese klíčová slova se zřetelným původem: deskriptory tezauru
EuroVoc, jež aktům EU přiděluje Úřad pro publikace EU (146 dokumentů),
třídník ICS a deskriptory ČSN z katalogu České agentury pro standardizaci,
u norem ISO bez českého převzetí třídník ICS z otevřených dat ISO
(705 dokumentů s třídníkem ICS, 31 s deskriptory ČSN), a česká klíčová
slova, jež jazykový model odvodí z názvu, anotace a textu dokumentu
(1287 dokumentů). Stránka dokumentu slova odvozená modelem označuje jako
neověřená (zásada 7). Klíčová slova prohledává i vyhledávání.

Filtr „Oblast“ a štítky dokumentů ukazují 29 veřejných oblastí katalogu
navázaných na věcné okruhy (odstavec 4.3, bod 2). Oblast určují pravidla
podle názvu a označení dokumentu, třídy ČSN, technické komise, typu
dokumentu a okruhů, jež editor zvolil při přijetí kandidáta. Dokument, jemuž
pravidla oblast nepřiřadí, je v pracovní oblasti „Oblast dosud neurčena“,
jež se veřejně nezobrazuje; k 26. 11. 2026 jich je 39.

Přijatý kandidát dostane oblast ihned. Klíčová slova novým dokumentům
doplní správce během, jenž stáhne deskriptory a třídy a odvodí klíčová
slova modelem (příloha A.2).

## 5. Kontrola platnosti a stavy dokumentů

### 5.1 Stavy

| Stav | Význam |
|---|---|
| připravovaný | návrh v legislativním procesu (návrh zákona, návrh Komise, návrh normy prEN) |
| vyhlášený, dosud neúčinný | platný předpis s odloženou účinností |
| účinný | předpis, jenž se použije |
| nahrazený | dokument nahrazený novějším vydáním (u norem a strategií) |
| zrušený | předpis, jenž se již nepoužije |

Úvodní stránka aplikace uvádí zvlášť počet aktuálně platných, připravovaných
a historických (zrušených nebo nahrazených) dokumentů; stránka dokumentu
uvádí stav každé jeho verze a u zrušeného předpisu vazbu „je zrušen
předpisem“. K 26. 11. 2026 má aktuální verze 1281 dokumentů stav účinný,
124 připravovaný (122 návrhů norem a dvě připravované aktualizace
strategií), 25 zrušený a 2 nahrazený (počty zahrnují jazykové verze
a slovenské dokumenty; veřejný katalog bez nich uvádí 825 platných,
116 připravovaných a 26 historických).

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

Kontrola dosud nepokrývá strategie, technická pravidla a slovenské
předpisy. U norem zaznamenáváme výsledek kontroly v katalozích
norem (ČSN online, Normoff, Věstník ÚNMZ, souhrnné seznamy harmonizovaných
norem) a datum této kontroly se zobrazuje u dokumentu (odstavec 7).
Zrušení normy se do stavu dokumentu automaticky nepromítá a provádí je
editor.

**Nové vydání ČSN s pozdější účinností** se promítá automaticky. Katalog
ČSN online vede nové vydání jako platné ode dne vydání, dosavadní vydání
však zůstává účinné až do dne účinnosti nového (zpravidla 1. den měsíce
po vydání; údaj „Datum účinnosti“ na stránce normy). Měsíční kontrola stavu
ČSN zjistí obě vydání a nové zapíše do mezipaměti kontrol; databáze je pak
vede u dokumentu jako další verzi ve stavu „vyhlášený, dosud neúčinný“
s datem účinnosti. V den účinnosti se nové vydání stane aktuální verzí
a dosavadní vydání „nahrazeným“. Proto se promítnutí stavů spouští
1. den každého měsíce (plánovač, odstavec 9.2; do jeho zavedení ručně,
příloha A.4). Nová norma, jež dosud nenabyla účinnosti, je do dne účinnosti
ve stavu „vyhlášený, dosud neúčinný“. Příklad: řada ČSN EN 13445 vydaná 1. 12. 2026 nabývá účinnosti 1. 1. 2027, ČSN EN IEC 60079-29-0 vydaná
v listopadu 2026 nabývá účinnosti 1. 12. 2026.

**Označení dokumentu se při přepnutí řídí účinným vydáním** (rozhodnutí
z 20. 11. 2026). Liší-li se označení nového vydání od dosavadního označení
dokumentu, například `ČSN EN 13445-5+A1` → `ČSN EN 13445-5` (změna A1 je
v novém vydání zapracována), nebo naopak přibude `+A1`, změní se v den
účinnosti automaticky i označení dokumentu a označení na začátku jeho názvu.
Má-li nové vydání stejné označení (ČSN EN 1717+A1 z 9/2026 a z 12/2026),
označení se nemění. Dále platí:

* **Trvalá adresa** stránky dokumentu (`/dokument/<slug>`) se nemění; slug
  odvozený z dosavadního označení zůstává (například
  `csn-en-13445-5-a1`), aby odkazy na dokument nepřestaly fungovat.
* **Dosavadní vydání** zůstává u dokumentu jako nahrazená verze se svým
  označením a měsícem vydání (například „ČSN EN 13445-5+A1 (vydání 4.2025)“).
* **Odkaz na zdroj**, vedl-li na stránku dosavadního vydání v katalogu ČSN
  online, vede nově na stránku účinného vydání.
* **Shoda označení s jiným dokumentem** (porovnává databáze, tedy bez
  ohledu na velikost písmen) přejmenování zabrání; vydání se přepne,
  označení zůstane a běh to vypíše. O označení pak rozhodne editor.
* **Přestavba databáze** změnu zachová: Běh promítnutí stavů ji zapíše
  do `data/manual_corrections.json` (nové označení, zachovaný slug, nový
  odkaz), přejmenuje klíče dokumentu v `data/fulltext_manifest.json`
  a přesune jeho záznam v `data/norm_validity_cache.json` pod nové
  označení. Vazby uložené podle označení se při přestavbě přejmenují
  podle `data/manual_corrections.json`. Změněné soubory je třeba zapsat do
  repozitáře (odstavec 9.2, bod 2).

Zkouška na testovací databázi s datem 1. 1. 2027 (20. 11. 2026): Dokument
#37 přešel na vydání 12/2026 s označením `ČSN EN 13445-5` a slugem
`csn-en-13445-5-a1`, dokument #1456 na vydání 12/2026 se stejným označením
`ČSN EN 1717+A1`.

### 5.3 Konsolidovaná znění aktů EU

U nařízení CLP (ES) č. 1272/2008 a REACH (ES) č. 1907/2006 zobrazujeme
od 20. 11. 2026 aktuální konsolidované znění, nikoli původní znění
vyhlášené v Úředním věstníku (rozhodnutí řešitele z 20. 11. 2026).
Konsolidované znění je neúřední úplné znění aktu se všemi změnami; vydává
je Úřad pro publikace EU, jenž je v databázi Cellar vede s datem, od něhož
se použije. Databáze vede každé znění jako verzi dokumentu:

* **Aktuální konsolidované znění** (k 26. 11. 2026 u CLP znění k 1. 7. 2026,
  u REACH k 22. 6. 2026) je aktuální verzí ve stavu „účinný“ a jeho text se
  zobrazuje na stránce dokumentu.
* **Původní znění** a **starší konsolidovaná znění** jsou verze ve stavu
  „nahrazený“; původní znění si ponechává svůj uložený text.
* **Připravené znění s budoucí účinností** (u CLP znění k 1. 1. 2027) je
  verze ve stavu „vyhlášený, dosud neúčinný“.

Stránka dokumentu uvádí, které znění se zobrazuje, a u každé verze odkaz
do EUR-Lexu, u verzí s uloženým textem i odkaz na náš text. Denní kontrola
(plánovač, odstavec 5.4) zjistí v Cellaru nové znění, v den jeho účinnosti
je učiní aktuální verzí, stáhne jeho text z Cellaru a vytvoří čitelný text.
Dokud se text nového znění nepodaří stáhnout, stránka zobrazuje text
předchozího znění a uvádí to. Další akty EU lze do mechanismu zařadit
seznamem v datovém souboru (příloha A.2); návrh je v `doc/CELLAR_FULLTEXT.md`,
odstavec 7.

### 5.4 Plánovač a nouzový postup

**Plánovač je třeba nainstalovat do konce prosince 2026.** Konfigurace je
připravena v `deploy/scheduler/` (časovače systemd nebo crontab, příloha
A.2), dosud není nainstalována (odstavec 9.2). Na plánovači závisí:

* přepnutí norem na vydání s pozdější účinností 1. den v měsíci (1. 1. 2027
  řada ČSN EN 13445 a ČSN EN 1717+A1, odstavec 5.2);
* přechod nařízení CLP na konsolidované znění k 1. 1. 2027 a každé další
  nové konsolidované znění CLP a REACH (odstavec 5.3);
* týdenní, měsíční a čtvrtletní sběr sledovaných zdrojů (odstavec 3).

Nebude-li plánovač 1. 1. 2027 v provozu, provede správce **2. 1. 2027**
v adresáři provozované aplikace (`/home/laborator/DEVEL/nahyc-h2db`) nouzový postup:

```
.venv/bin/python src/tools/backup_db.py --reason before_states_20270102
.venv/bin/python src/tools/backfill_document_states.py            # suchý běh
.venv/bin/python src/tools/backfill_document_states.py --apply    # normy a verze CLP
.venv/bin/python src/tools/refresh_eu_consolidations.py           # suchý běh
.venv/bin/python src/tools/refresh_eu_consolidations.py --apply   # Cellar, text CLP k 1. 1. 2027
```

Výsledek správce ověří na stránkách dokumentů CLP (`/dokument/es-1272-2008`,
zobrazený text „konsolidované znění ke dni 1. 1. 2027“) a ČSN EN 13445-5
(označení `ČSN EN 13445-5`). Totéž platí pro každý další 1. den v měsíci
(normy) a pro den účinnosti dalšího konsolidovaného znění, dokud plánovač
nebude nainstalován.

## 6. Co se stane s novým, novelizovaným a zrušeným předpisem

| Událost | Kde ji zachytíme | Co se stane v databázi |
|---|---|---|
| Návrh předpisu se objeví ve VeKLEPu nebo jako sněmovní tisk | týdenní sběr návrhů | Kandidát s označením „návrh“; po přijetí dokument ve stavu „připravovaný“ s vazbou na předpisy, jež mění. |
| Návrh je schválen a vyhlášen ve Sbírce | e-Sbírka (týdně); otevřená data Sněmovny vážou vyhlášený předpis k tisku | Vyhlášený předpis se stane kandidátem. Po nasazení editor na stránce připravovaných dokumentů zaznamená, jak návrh skončil: buď převede týž dokument na vyhlášený (stav „vyhlášený, dosud neúčinný“ nebo „účinný“, případně nové označení, název a datum účinnosti), nebo jej propojí s vyhlášeným předpisem, jenž je v databázi jiným dokumentem, vazbou „návrh vyhlášen jako“; návrh pak bude veden jako nahrazený. Změnu navrhuje jeden editor a potvrzuje druhý. Automatické propojení návrhu s vyhlášeným předpisem zatím neplánujeme. |
| Nový předpis EU (nařízení, směrnice, akt v přenesené pravomoci) | EUR-Lex a rejstříky Komise (týdně) | Kandidát; po přijetí dokument ve stavu „účinný“ nebo „vyhlášený, dosud neúčinný“. U směrnice editor sleduje transpozici do českého práva. |
| Novela předpisu, jejž databáze má | e-Sbírka, EUR-Lex | Novela, jež se týká vodíku nebo věcných okruhů, se stane kandidátem a po přijetí je propojena vazbou „mění“; konsolidované znění odkazuje do autoritativního zdroje. U aktů EU ze seznamu konsolidovaných znění (CLP, REACH) se nové konsolidované znění stane v den účinnosti aktuální verzí dokumentu a zobrazí se jeho text (odstavec 5.3). |
| Předpis nabude účinnosti | kontrola platnosti | Stav „vyhlášený, dosud neúčinný“ se změní na „účinný“. |
| Předpis je zrušen | kontrola platnosti | Stav „zrušený“, vazba na zrušující předpis; dokument zůstává v databázi. |
| Norma je nahrazena novým vydáním | Věstník ÚNMZ a katalog ČSN online (měsíčně) | Nové vydání ČSN, jež databáze má, se uloží jako další verze dokumentu ve stavu „vyhlášený, dosud neúčinný“ a v den účinnosti se automaticky stane aktuální verzí; dosavadní vydání bude „nahrazené“ (odstavec 5.2). Norma, jež v databázi není, je kandidátem. Návrh normy (prEN) po vydání převede editor na vydanou normu stejně jako návrh předpisu. |
| Vláda nebo Komise přijme novou strategii | čtvrtletní kontrola, kanály novinek | Kandidát (ruční návrh editora); předchozí verze strategie bude vedena jako nahrazená. Zveřejněný, dosud neschválený návrh aktualizace strategie vedeme jako připravovaný dokument s vazbou na strategii, již má nahradit (dnes Politika ochrany klimatu 2025–2050 a aktualizace Státní energetické koncepce). Po schválení jej editor na stránce připravovaných dokumentů převede na účinný; nahrazovaná strategie se tím převede do stavu „nahrazený“. |

## 7. Jak zjistit, kdy byl dokument naposledy ověřen

Od 20. 11. 2026:

* zápatí každé stránky aplikace uvádí datum a čas poslední změny databáze
  jako celku;
* stránka dokumentu uvádí stav každé jeho verze a údaj „Poslední kontrola
  stavu“ s datem a zdrojem kontroly, například „27. 10. 2026 (e-Sbírka)“
  nebo „5. 11. 2026 (Věstník ÚNMZ)“, u změny potvrzené editorem jméno
  editora; dokument, jenž dosud ověřen nebyl, nese text „dosud neověřeno“.

Údaj se zapisuje při každém promítnutí výsledků kontrol do databáze, i když
se stav dokumentu nezměnil, a datum se nikdy neposouvá zpět; od 26. 11. 2026
jej posouvá i obnova konsolidovaného znění aktu EU (odstavec 5.3). K 26. 11.
2026 je datum kontroly uvedeno u 205 dokumentů (databáze Úřadu pro publikace
EU 141, e-Sbírka 37, Věstník ÚNMZ 24, katalogy norem a seznamy
harmonizovaných norem 3; 20. 11. 2026 to bylo 233 dokumentů, úbytek připadá
převážně na vyřazené akty EU); ostatní, mezi nimi většina norem STN, nesou „dosud neověřeno“,
dokud je některá kontrola neověří. Aplikační garant tak může u každého
dokumentu ověřit, kdy a podle čeho byl naposledy zkontrolován.

Veřejný přehled kontrol jednotlivých zdrojů včetně kontrol bez nálezu
plánujeme; dosud jej vede jen záznam běhů dostupný správci (příloha A.2).

## 8. Měření úplnosti

Jednou za čtvrtletí garant vyhodnotí úplnost databáze kombinací nezávislých
kontrol:

1. **Referenční soubor** — Tabulky předpisů zpracované MPO a Centrem
   dopravního výzkumu (květen 2026) převezmeme jako referenční soubor;
   automatický test, jenž je součástí testů spouštěných před každou změnou
   aplikace, ověřuje, že každý z 90 řádků obou tabulek je dokumentem
   databáze, kandidátem ve frontě, nebo má uveden důvod, proč dokumentem
   není (například technické komise normalizačních organizací), a že žádný
   dokument z tabulek z databáze nezmizel. K 26. 11. 2026 je beze změny
   51 řádků v databázi, 31 ve frontě kandidátů a 8 řádků nejsou dokumenty.
   Obdobně hlídá automatický test referenční seznam předpisů k obnovitelným
   palivům nebiologického původu (RFNBO), jejichž existenci a číslo jsme
   ověřili v databázi Úřadu pro publikace EU; pět chybějících aktů jsme
   26. 11. 2026 zapsali do fronty kandidátů.
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

### 9.1 K projednání s aplikačním garantem

1. **Editoři MPO** — Zda a kterým pracovníkům MPO založit editorský účet
   (odstavec 2.1).
2. **Lhůty posouzení kandidátů** podle odstavce 4.5.

### 9.2 Odloženo, vyřešíme později

Následující provozní otázky jsme odložili; do jejich vyřešení platí postup
popsaný v odstavci 3.2 (kontroly spouští ručně správce).

1. **Plánovač kontrol** — Na kterém serveru a jakým mechanismem (časovač
   systemd, nebo crontab) jej provozovat; kde bude databáze provozována po
   skončení projektu. **Nainstalovat jej je třeba do konce prosince 2026**
   (odstavec 5.4), jinak se 1. 1. 2027 nepřepnou normy ani znění CLP.
2. **Datové soubory měněné běhy kontrol** — Běhy v adresáři provozované aplikace mění
   soubory pod správou verzí (záznam běhů, mezipaměti kontrol, přijaté
   kandidáty, při přejmenování normy na nové vydání i `data/manual_corrections.json`
   a `data/fulltext_manifest.json`); zda je pravidelně zapisovat do repozitáře, nebo je přesunout
   mimo správu verzí. Do rozhodnutí je nutné změněné soubory před každým
   nasazením nové verze (`git pull` v adresáři provozované aplikace) ošetřit ručně.
3. **Zdroje IEC, EIGA a DVGW** — Stávající způsob jejich čtení obchází
   ochranu proti robotům; navrhujeme je vypnout a kontrolovat je ručně.
4. **Registrace** k rozhraní e-Sbírky a e-Legislativy (podání Ministerstvu
   vnitra datovou schránkou; e-Legislativa postupně nahrazuje VeKLEP)
   a **přístup k databázi TRIS** (oznamování technických předpisů).
5. **Četnost kontroly stavu norem ČSN a STN** — V registru zdrojů je
   vedena „na vyžádání“, připravený plánovač ji spouští měsíčně. Pro
   přepnutí norem na nové vydání v den účinnosti je navíc připraveno
   promítnutí stavů 1. den každého měsíce (`h2db-states-monthly.timer`);
   bez plánovače je spouští správce ručně (příloha A.4).
6. **Ostatní zdroje za ochranou proti robotům** (EHK OSN, registr Rady EU,
   Slov-Lex) — Ponechat ruční kontrolu, nebo požádat provozovatele
   o přístup.

## Příloha A: Technické údaje

Údaje v této příloze slouží správci a vývojářům. Nástroje jsou v adresáři
`src/tools/` adresáře provozované aplikace a spouštějí se jejím interpretem
(`.venv/bin/python`); bez volby `--apply` provádějí jen suchý běh. Účet
k databázi se čte ze souboru `.env` (pro testovací databázi `.env.test`,
volba `--env-file`).

### A.1 Databáze

| Tabulka | Účel |
|---|---|
| `Document`, `DocumentVersion` | dokumenty a jejich verze; stav v `DocumentVersion.lifecycle_state` (`active`, `promulgated`, `draft`, `superseded`, `repealed`) |
| `document_relation` | vazby `AMENDS`, `REPEALS`, `IMPLEMENTS`, `TRANSLATION_OF` aj. |
| `DocumentCandidate` | fronta kandidátů (stavy `new`, `proposed`, `accepted`, `rejected`, `deferred`; podmínka `chk_dc_distinct_reviewers`) |
| `ReviewItem` | navržené opravy údajů (podmínka `chk_ri_distinct_reviewers`) |
| `User`, `AuditLog` | účty editorů a záznam rozhodnutí |
| `DocumentStateChange` | navržené změny stavu připravovaných dokumentů (podmínka `chk_dsc_distinct_reviewers`) |
| `Term`, `DocumentTerm` | klíčová slova (původ `eurovoc`, `ics`, `cas`, `model`) a jejich vazby na dokumenty (od 26. 11. 2026) |
| `Area`, `DocumentArea` | oblasti katalogu (`Area.public = 0` u pracovní oblasti) a jejich vazby na dokumenty (od 26. 11. 2026) |
| `SourceCategory`, `DocumentSourceCategory` | kategorie převzaté ze zdrojových rešerší (do 26. 11. 2026 `Keyword`, `DocumentKeyword`); prohledávají se, ve filtru je nahradily oblasti |

Sloupec `Document.provenance` nese původ záznamu a veřejně se nezobrazuje.
Od 20. 11. 2026 jsou v provozu sloupce `Document.eu_act_subtype`
(`delegated`, `implementing`), `Document.status_checked_at`
a `status_checked_by` (datum a zdroj poslední kontroly stavu),
`DocumentCandidate.puvodce` (navržená odpovědná instituce) a typ vazby
`ENACTED_AS` („návrh vyhlášen jako“).
Zálohy: `backups/h2regdocs_<datum>_<čas>_<důvod>.sql.gz` (mimo git).

### A.2 Nástroje

| Nástroj | Účel | Četnost |
|---|---|---|
| `check_validity.py [--max-age 30]` | kontrola platnosti (Cellar, e-Sbírka, zakonyprolidi.cz) → `data/validity_cache.json` | týdně |
| `backfill_document_states.py --apply [--today RRRR-MM-DD]` | promítnutí výsledků do `lifecycle_state` a vazeb `REPEALS` (`data/document_relations_validity.json`); vydání norem s pozdější účinností (`norm_editions.py`): doplnění verze a přepnutí v den účinnosti, případně se změnou označení dokumentu (zápis do `data/manual_corrections.json`, `data/fulltext_manifest.json` a `data/norm_validity_cache.json`, odstavec 5.2); `--today` (bez `--apply`) ukáže, co se stane k danému dni | po kontrole platnosti a 1. den v měsíci |
| `check_csn_validity.py --editions "<označení>"` | platné vydání ČSN a vydání s pozdější účinností z katalogu ČSN online (datum vydání a účinnosti) | podle potřeby |
| `citation_closure.py` | uzávěr citací → `data/citation_closure.json`, `data/citation_closure_candidates.csv` | čtvrtletně |
| `import_candidates.py --apply` | kandidáti z uzávěru citací a kontroly platnosti do `DocumentCandidate` | po předchozích dvou |
| `apply_manual_corrections.py --apply` | promítnutí ručních korekcí `data/manual_corrections.json` do živé databáze | při změně souboru |
| `src/db/dbuser_add.py <login> "<jméno>" <email> --apply` | založení účtu editora | podle potřeby |
| `harvest_sources.py --cadence <četnost> --apply` | sběr ze sledovaných zdrojů do fronty kandidátů; při prvním běhu po etapách `--stage E1` až `E6` | podle `cadence` |
| `scheduled_harvest.sh <četnost> [--dry-run]` | plánovaný běh: záloha, sběr dané četnosti, promítnutí stavů; četnost `states` jen záloha, promítnutí stavů a konsolidovaná znění; `daily` jen konsolidovaná znění; konfigurace plánovače v `deploy/scheduler/` (nenainstalována, **instalovat do konce prosince 2026**, odstavec 5.4) | týdně, měsíčně, čtvrtletně; `states` 1. den v měsíci; `daily` denně |
| `refresh_act_versions.py --apply [--today RRRR-MM-DD] [--backup]` | verze ostatních českých předpisů a aktů EU (issue #38, `doc/VERZE_PREDPISU.md`): znění z otevřených dat e-Sbírky a z Cellaru → `data/act_versions_cache.json`, výchozí verze doplněná o vydání, účinnost a odkaz, nová znění po vložení dokumentu jako nové verze s textem (zakonyprolidi.cz, Cellar), prázdné „Platnost od“ | denně |
| `refresh_eu_consolidations.py --apply [--today RRRR-MM-DD] [--backup]` | konsolidovaná znění aktů EU ze seznamu `data/eu_consolidated_acts.json` (CLP, REACH): dotaz do Cellaru → `data/eu_consolidation_cache.json`, stažení textu účinného znění z Cellaru (`fetch_fulltext.py`, položka manifestu `konsolidace_<RRRRMMDD>`), čitelný text, verze dokumentu (`eu_consolidations.py`); `--today` bez `--apply` ukáže stav k danému dni (odstavec 5.3) | denně |
| `backup_db.py --reason <důvod>` | záloha databáze do `backups/` | před každým hromadným zápisem |
| `triage_candidates.py [--rules-only] [--sample N] [--apply]` | automatické třídění fronty kandidátů: pravidla `data/triage_rules.json`, pak jazykový model (mezipaměť `data/triage_model_cache.json`, odhad ceny a limit před během); bez `--apply` suchý běh; ostrý běh nad provozní databází jen s odsouhlasenými pravidly (`approval`), postup v `doc/FRONTA_AUTOMAT.md`, odstavec 7 | po každém sběru a importu kandidátů |
| `mpo_tables.py import --apply` | kandidáti z tabulek MPO a CDV (`data/20260430_MPO/`) do fronty kandidátů | jednorázově (provedeno 20. 11. 2026) |
| `backfill_eu_act_subtype.py --apply` | podtyp aktů EU (`Document.eu_act_subtype`) v existující databázi | jednorázově (provedeno 20. 11. 2026) |
| `harvest_sources.py --checklist`, `--record <zdroj> --note … --found N` | seznam ručně kontrolovaných zdrojů a záznam ruční kontroly | čtvrtletně |
| `check_sources.py --apply` | kontrola dostupnosti adres registru | měsíčně |
| `check_records.py` | kontrola záznamů, vrstva 1: Cellar, otevřená data ISO, vnitřní kontroly → `data/record_checks.json` (jen čte) | po přijetí kandidátů a týdně |
| `check_records_model.py [--run]` | kontrola záznamů, vrstva 2: posouzení modelem (bez `--run` jen odhad ceny, mezipaměť podle obsahu záznamu) → `data/record_checks_model.json` | po změně záznamů |
| `review_findings.py --apply` | nálezy kontroly záznamů jako navržené opravy (`ReviewItem`) pro editory | po kontrole záznamů |
| `fetch_eurovoc.py`, `fetch_ics.py`, `extract_keywords.py --run` | deskriptory EuroVoc z Cellaru, třídy ICS a deskriptory ČSN z katalogu ČAS a otevřených dat ISO, klíčová slova modelem → `data/eurovoc_cache.json`, `data/ics_cache.json`, `data/keyword_model_cache.json` | po přijetí nových dokumentů |
| `document_terms.py --apply` | klíčová slova z mezipamětí do `Term` a `DocumentTerm` | po předchozím řádku a po přestavbě databáze |
| `assign_areas.py --apply [--uncertain]` | oblasti katalogu podle `data/areas.json` do `DocumentArea`; `--uncertain` vypíše dokumenty bez oblasti | po změně pravidel a po přestavbě databáze |
| `import_listed_candidates.py <soubor> --apply` | kandidáti ze seznamu (například `data/rfnbo_candidates.json`) do fronty kandidátů | jednorázově (provedeno 26. 11. 2026) |

Registr zdrojů: `data/monitored_sources.json` (popis v `doc/DATA_SOURCES.md`);
záznam běhů a ručních kontrol
`data/source_checks.jsonl` (jen připisování). Přijaté kandidáty zapisuje
editorská aplikace do `data/accepted_candidates.json`, potvrzené opravy do
`data/manual_corrections.json`, potvrzené změny stavu připravovaných
dokumentů do `data/manual_corrections.json` a
`data/document_relations_editor.json`; tyto soubory čte sestavení databáze
(`build_unified_db.py`). Mezipaměti kontrol: `data/validity_cache.json`
(předpisy) a `data/norm_validity_cache.json` (normy). Konsolidovaná znění:
seznam aktů `data/eu_consolidated_acts.json` (další akt se zapne přidáním
položky), mezipaměť znění z Cellaru `data/eu_consolidation_cache.json`;
odkaz verze do EUR-Lexu je ve sloupci `DocumentVersion.url` (založí jej
první zápis verzí).

### A.3 Editorská aplikace

| Adresa | Účel |
|---|---|
| `/admin/login` | přihlášení editora |
| `/admin/candidates` | fronta kandidátů (filtr podle stavu a zdroje), detail s doklady, `/admin/candidates/new` ruční návrh |
| `/admin/review` | dokumenty s příznakem ke kontrole a návrhy oprav |
| `/admin/drafts` | připravované dokumenty a převod návrhu na vyhlášený předpis |
| `/admin/audit-log` | záznam rozhodnutí |

### A.4 Doporučený týdenní běh (do zavedení plánovače)

```
cd /home/laborator/DEVEL/nahyc-h2db
.venv/bin/python src/tools/check_validity.py
.venv/bin/python src/tools/backup_db.py --reason before_weekly_run
.venv/bin/python src/tools/backfill_document_states.py --apply
.venv/bin/python src/tools/import_candidates.py --apply
.venv/bin/python src/tools/harvest_sources.py --cadence weekly --apply
.venv/bin/python src/tools/triage_candidates.py --apply
.venv/bin/python src/tools/backfill_document_states.py --apply  # stavy a data kontrol
.venv/bin/python src/tools/check_records.py                 # kontrola záznamů, jen čte
```

První den každého měsíce (do zavedení plánovače) navíc promítnutí stavů,
aby se normy přepnuly na nové vydání v den jeho účinnosti (nejbližší 1. 12. 2026 a 1. 1. 2027):

```
.venv/bin/python src/tools/backup_db.py --reason before_monthly_states
.venv/bin/python src/tools/backfill_document_states.py --apply
.venv/bin/python src/tools/refresh_eu_consolidations.py --apply
```

Konsolidovaná znění CLP a REACH (odstavec 5.3) mohou nabýt účinnosti
kterýkoli den; do zavedení plánovače spouští správce
`refresh_eu_consolidations.py --apply` alespoň týdně a vždy v den účinnosti
znění, jež suchý běh hlásí jako připravené (nejbližší CLP 1. 1. 2027,
nouzový postup v odstavci 5.4).

Související dokumenty: `doc/DATABASE_SCOPE.md` (rozsah, stavy, četnost),
`doc/CITATION_CLOSURE.md` (uzávěr citací), `doc/DATA_SOURCES.md` (registr
zdrojů a plán vytěžování; postup prvního ostrého běhu a návrh plánovače
v odstavci 8.17), `doc/MPO_TABULKY.md` (tabulky MPO a CDV jako zlatá sada),
`doc/MPO_VYPORADANI.md` (vypořádání připomínek MPO), `doc/KONTROLA_ZAZNAMU.md`
(kontrola záznamů), `doc/KLICOVA_SLOVA.md` (klíčová slova), `doc/OBLASTI.md`
(oblasti katalogu), `doc/RFNBO_POKRYTI.md` (pokrytí tématu RFNBO).
