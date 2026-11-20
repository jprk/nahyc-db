# Provoz a udržování aktuálnosti databáze regulačních předpisů

> Historie dokumentu:  
> 2026-11-19 jprk Návrh první verze (podklad k vypořádání připomínek MPO k výsledku V01)  
> 2026-11-19 jprk Doplněn stav po krocích 1 až 3, editorský přístup pro MPO, termíny nasazení

Dokument popisuje, jak se databáze regulačních předpisů a předrealizačních
procesů (výsledek V01 dílčího projektu DP004 centra NAHYC) udržuje aktuální:
z jakých zdrojů a jak často zjišťujeme nové dokumenty a změny stavu
dokumentů, kdo o zařazení dokumentu rozhoduje, jak se v databázi projeví
nový, novelizovaný nebo zrušený předpis a jak lze zjistit, kdy byl dokument
naposledy ověřen. Je určen garantovi databáze a editorům; slouží zároveň jako
odpověď na dotaz Ministerstva průmyslu a obchodu, jak bude zajištěna
aktuálnost předpisů.

Odstavce 1 až 9 popisují postup bez technických podrobností. Technické
údaje (nástroje, příkazy, datové soubory a tabulky) jsou v příloze A na
konci dokumentu.

U každého postupu odlišujeme, co platí k 19. 11. 2026 v provozní databázi,
od toho, co je připraveno a ověřeno na kopii databáze a co nasadíme do 25. 11. 2026 (dále „po nasazení“), a od toho, co teprve zavádíme. Plánované
stavy popisujeme budoucím časem. Místa, jež doplní řešitel, jsou označena
`[DOPLNIT: …]`.

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
| Garant databáze | Mgr. Vladimír Kremlík (RICE) | Odpovídá za obsah a rozsah databáze; rozhoduje sporné případy; jednou za čtvrtletí vyhodnocuje úplnost (odstavec 8) a podává zprávu aplikačnímu garantovi. |
| Editoři řešitele (nejméně dva) | Dr. Bronislav Vahalík (CDV), Ing. Jan Sochor (HYTEP) | Posuzují frontu kandidátů, připravované dokumenty a navržené opravy; navrhují a potvrzují přijetí dokumentů a změny stavu; provádějí ruční kontroly zdrojů, jež automatizovat nelze. |
| Editoři MPO (volitelně) | pracovníci MPO určení aplikačním garantem [DOPLNIT po dohodě s MPO: jméno] | Stejná oprávnění jako editoři řešitele (odstavec 2.1); mohou zejména navrhovat nové dokumenty a opravy údajů a potvrzovat návrhy ostatních editorů. |
| Správce | Dr. Jan Přikryl (RICE) | Spouští nebo nastavuje pravidelné kontroly, pořizuje zálohy, sleduje chyby a dostupnost zdrojů, zakládá uživatelské účty editorů. |
| Aplikační garant (MPO) | Ing. Petr Mervart | Uplatňuje připomínky a požadavky na rozsah; určuje, kteří pracovníci MPO dostanou editorský účet; dostává čtvrtletní zprávu o úplnosti. |

K 19. 11. 2026 jsou v provozní databázi založeny dva aktivní uživatelské
účty editorů řešitele. Přijetí kandidáta vyžaduje dva různé editory; dva
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

### 3.2 Stav k 19. 11. 2026

* **Kontrola platnosti** předpisů ČR a EU je v provozu a naposledy proběhla
  27. 10. 2026 (747 předpisů ČR a EU — dokumenty databáze i kandidáti na
  doplnění, odstavec 5).
* **Fronta kandidátů** je v provozu; obsahuje 296 kandidátů, z nichž 295
  čeká na posouzení a 1 je navržen k přijetí. Pocházejí z kontroly úplnosti
  (288) a z kontroly platnosti (8).
* **Sběr ze sledovaných zdrojů** (34 zdrojů čtených pravidelně, 5 k dohledání
  na vyžádání, 16 ručně kontrolovaných) je vyvinut a vyzkoušen na testovací
  kopii databáze, do provozu však dosud uveden nebyl. Zkouška nanečisto nad
  provozní databází 19. 11. 2026, při níž se nic nezapsalo, odhadla 252
  nových kandidátů, z toho 112 s přímým vztahem k databázi (mění dokument
  databáze nebo se týká vodíku). Do provozu jej uvedeme prvním ostrým
  během do 25. 11. 2026; skutečný počet nálezů bude záviset na stavu zdrojů
  v den běhu. Nálezy s přímým vztahem posoudí editoři do 18. 12. 2026,
  ostatní do 15. 1. 2027.
* **Kandidáti z tabulek MPO a CDV** (34 kandidátů s úředním názvem, adresou,
  platností a navrženou odpovědnou institucí) jsou připraveni a do fronty
  kandidátů je zapíšeme do 25. 11. 2026; posoudí je editoři do
  11. 12. 2026.
* **Pravidelné automatické spouštění** kontrol na serveru zavedeno není;
  kontroly spouští správce ručně. Konfigurace plánovače (týdenní, měsíční
  a čtvrtletní běh se zálohou databáze před každým zápisem) je připravena,
  nainstalována však není; rozhodnutí o jejím zavedení jsme odložili
  (odstavec 9). Dokud plánovač nebude zaveden, odpovídá za dodržení
  četnosti podle odstavce 3.1 správce.

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
návrhem k projednání s aplikačním garantem na jednání, jež navrhujeme na
první prosincový týden 2026; po dohodě je zde upřesníme.

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

Kontrola dosud nepokrývá strategie, technická pravidla a slovenské
předpisy. U norem po nasazení zaznamenáváme výsledek kontroly v katalozích
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
1. den každého měsíce (plánovač, odstavec 9.3; do jeho zavedení ručně,
příloha A.4). Nová norma, jež dosud nenabyla účinnosti, je do dne účinnosti
ve stavu „vyhlášený, dosud neúčinný“. Příklad: řada ČSN EN 13445 vydaná
1. 12. 2026 nabývá účinnosti 1. 1. 2027, ČSN EN IEC 60079-29-0 vydaná
v listopadu 2026 nabývá účinnosti 1. 12. 2026. Označení dokumentu se při
přepnutí nemění; nové označení vydání je uvedeno u verze.

## 6. Co se stane s novým, novelizovaným a zrušeným předpisem

| Událost | Kde ji zachytíme | Co se stane v databázi |
|---|---|---|
| Návrh předpisu se objeví ve VeKLEPu nebo jako sněmovní tisk | týdenní sběr návrhů | Kandidát s označením „návrh“; po přijetí dokument ve stavu „připravovaný“ s vazbou na předpisy, jež mění. |
| Návrh je schválen a vyhlášen ve Sbírce | e-Sbírka (týdně); otevřená data Sněmovny vážou vyhlášený předpis k tisku | Vyhlášený předpis se stane kandidátem. Po nasazení editor na stránce připravovaných dokumentů zaznamená, jak návrh skončil: buď převede týž dokument na vyhlášený (stav „vyhlášený, dosud neúčinný“ nebo „účinný“, případně nové označení, název a datum účinnosti), nebo jej propojí s vyhlášeným předpisem, jenž je v databázi jiným dokumentem, vazbou „návrh vyhlášen jako“; návrh pak bude veden jako nahrazený. Změnu navrhuje jeden editor a potvrzuje druhý. Automatické propojení návrhu s vyhlášeným předpisem zatím neplánujeme. |
| Nový předpis EU (nařízení, směrnice, akt v přenesené pravomoci) | EUR-Lex a rejstříky Komise (týdně) | Kandidát; po přijetí dokument ve stavu „účinný“ nebo „vyhlášený, dosud neúčinný“. U směrnice editor sleduje transpozici do českého práva. |
| Novela předpisu, jejž databáze má | e-Sbírka, EUR-Lex | Novela, jež se týká vodíku nebo věcných okruhů, se stane kandidátem a po přijetí je propojena vazbou „mění“; konsolidované znění odkazuje do autoritativního zdroje. |
| Předpis nabude účinnosti | kontrola platnosti | Stav „vyhlášený, dosud neúčinný“ se změní na „účinný“. |
| Předpis je zrušen | kontrola platnosti | Stav „zrušený“, vazba na zrušující předpis; dokument zůstává v databázi. |
| Norma je nahrazena novým vydáním | Věstník ÚNMZ a katalog ČSN online (měsíčně) | Nové vydání ČSN, jež databáze má, se uloží jako další verze dokumentu ve stavu „vyhlášený, dosud neúčinný“ a v den účinnosti se automaticky stane aktuální verzí; dosavadní vydání bude „nahrazené“ (odstavec 5.2). Norma, jež v databázi není, je kandidátem. Návrh normy (prEN) po vydání převede editor na vydanou normu stejně jako návrh předpisu. |
| Vláda nebo Komise přijme novou strategii | čtvrtletní kontrola, kanály novinek | Kandidát (ruční návrh editora); předchozí verze strategie bude vedena jako nahrazená. Zveřejněný, dosud neschválený návrh aktualizace strategie vedeme jako připravovaný dokument s vazbou na strategii, již má nahradit (dnes Politika ochrany klimatu 2025–2050 a aktualizace Státní energetické koncepce). Po schválení jej editor na stránce připravovaných dokumentů převede na účinný; nahrazovaná strategie se tím převede do stavu „nahrazený“. |

## 7. Jak zjistit, kdy byl dokument naposledy ověřen

K 19. 11. 2026:

* zápatí každé stránky aplikace uvádí datum a čas poslední změny databáze
  jako celku;
* stránka dokumentu uvádí stav jeho verzí, nikoli však datum, kdy byl stav
  naposledy ověřen;
* datum kontroly platnosti je evidováno u každého předpisu interně
  (poslední kontrola 27. 10. 2026), veřejně se však nezobrazuje.

Po nasazení (do 25. 11. 2026) bude stránka dokumentu uvádět údaj „Poslední
kontrola stavu“ s datem a zdrojem kontroly, například „27. 10. 2026
(e-Sbírka)“, „5. 11. 2026 (ČSN online)“ nebo u změny potvrzené editorem
„19. 11. 2026 (editor …)“; dokument, jenž dosud ověřen nebyl, ponese text
„dosud neověřeno“. Údaj se zapisuje při každém promítnutí výsledků kontrol
do databáze, i když se stav dokumentu nezměnil, a datum se nikdy neposouvá
zpět. Podle zkoušky nanečisto nad provozní databází bude datum kontroly
po nasazení uvedeno u 226 dokumentů (databáze Úřadu pro publikace EU 167,
e-Sbírka 37, Věstník ÚNMZ 13, seznamy harmonizovaných norem 7, katalogy
norem 2); ostatní, mezi nimi většina norem STN, ponesou „dosud neověřeno“,
dokud je některá kontrola neověří. Aplikační garant tak bude moci u každého
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
   dokument z tabulek z databáze nezmizel. Ke 19. 11. 2026 je 51 řádků
   v databázi, 31 ve frontě kandidátů (po zápisu kandidátů do provozní
   databáze) a 8 řádků nejsou dokumenty.
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

### 9.1 K projednání s aplikačním garantem

1. **Editoři MPO** — Zda a kterým pracovníkům MPO založit editorský účet
   (odstavec 2.1).
2. **Lhůty posouzení kandidátů** podle odstavce 4.4.

### 9.2 Doplní řešitel

1. **Jména** garanta databáze, editorů řešitele a správce (odstavec 2).

### 9.3 Odloženo, vyřešíme později

Následující provozní otázky jsme odložili; do jejich vyřešení platí postup
popsaný v odstavci 3.2 (kontroly spouští ručně správce).

1. **Plánovač kontrol** — Zda zavést pravidelné automatické spouštění
   kontrol, na kterém serveru a jakým mechanismem (časovač systemd, nebo
   crontab); kde bude databáze provozována po skončení projektu.
2. **Datové soubory měněné běhy kontrol** — Běhy v hlavním stromu mění
   soubory pod správou verzí (záznam běhů, mezipaměti kontrol, přijaté
   kandidáty); zda je pravidelně zapisovat do repozitáře, nebo je přesunout
   mimo správu verzí. Do rozhodnutí je nutné změněné soubory před každým
   nasazením nové verze (`git pull` v hlavním stromu) ošetřit ručně.
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
| `DocumentStateChange` | navržené změny stavu připravovaných dokumentů (podmínka `chk_dsc_distinct_reviewers`; po nasazení kroku 3) |

Sloupec `Document.provenance` nese původ záznamu a veřejně se nezobrazuje.
Po nasazení kroků 1 až 3 přibudou sloupce `Document.eu_act_subtype`
(`delegated`, `implementing`), `Document.status_checked_at`
a `status_checked_by` (datum a zdroj poslední kontroly stavu),
`DocumentCandidate.puvodce` (navržená odpovědná instituce) a typ vazby
`ENACTED_AS` („návrh vyhlášen jako“).
Zálohy: `backups/h2regdocs_<datum>_<čas>_<důvod>.sql.gz` (mimo git).

### A.2 Nástroje

| Nástroj | Účel | Četnost |
|---|---|---|
| `check_validity.py [--max-age 30]` | kontrola platnosti (Cellar, e-Sbírka, zakonyprolidi.cz) → `data/validity_cache.json` | týdně |
| `backfill_document_states.py --apply [--today RRRR-MM-DD]` | promítnutí výsledků do `lifecycle_state` a vazeb `REPEALS` (`data/document_relations_validity.json`); vydání norem s pozdější účinností (`norm_editions.py`): doplnění verze a přepnutí v den účinnosti; `--today` (bez `--apply`) ukáže, co se stane k danému dni | po kontrole platnosti a 1. den v měsíci |
| `check_csn_validity.py --editions "<označení>"` | platné vydání ČSN a vydání s pozdější účinností z katalogu ČSN online (datum vydání a účinnosti) | podle potřeby |
| `citation_closure.py` | uzávěr citací → `data/citation_closure.json`, `data/citation_closure_candidates.csv` | čtvrtletně |
| `import_candidates.py --apply` | kandidáti z uzávěru citací a kontroly platnosti do `DocumentCandidate` | po předchozích dvou |
| `apply_manual_corrections.py --apply` | promítnutí ručních korekcí `data/manual_corrections.json` do živé databáze | při změně souboru |
| `src/db/dbuser_add.py <login> "<jméno>" <email> --apply` | založení účtu editora | podle potřeby |
| `harvest_sources.py --cadence <četnost> --apply` | sběr ze sledovaných zdrojů do fronty kandidátů (do `master` sloučením kroku 3); při prvním běhu po etapách `--stage E1` až `E6` | podle `cadence` |
| `scheduled_harvest.sh <četnost> [--dry-run]` | plánovaný běh: záloha, sběr dané četnosti, promítnutí stavů; četnost `states` jen záloha a promítnutí stavů; konfigurace plánovače v `deploy/scheduler/` (nenainstalována, odstavec 9.3) | týdně, měsíčně, čtvrtletně; `states` 1. den v měsíci |
| `backup_db.py --reason <důvod>` | záloha databáze do `backups/` | před každým hromadným zápisem |
| `mpo_tables.py import --apply` | kandidáti z tabulek MPO a CDV (`data/20260430_MPO/`) do fronty kandidátů | jednorázově (do 25. 11. 2026) |
| `backfill_eu_act_subtype.py --apply` | podtyp aktů EU (`Document.eu_act_subtype`) v existující databázi | jednorázově po nasazení kroku 2 |
| `harvest_sources.py --checklist`, `--record <zdroj> --note … --found N` | seznam ručně kontrolovaných zdrojů a záznam ruční kontroly | čtvrtletně |
| `check_sources.py --apply` | kontrola dostupnosti adres registru | měsíčně |

Registr zdrojů: `data/monitored_sources.json` (popis v `doc/DATA_SOURCES.md`);
záznam běhů a ručních kontrol
`data/source_checks.jsonl` (jen připisování). Přijaté kandidáty zapisuje
editorská aplikace do `data/accepted_candidates.json`, potvrzené opravy do
`data/manual_corrections.json`, potvrzené změny stavu připravovaných
dokumentů do `data/manual_corrections.json` a
`data/document_relations_editor.json`; tyto soubory čte sestavení databáze
(`build_unified_db.py`). Mezipaměti kontrol: `data/validity_cache.json`
(předpisy) a `data/norm_validity_cache.json` (normy).

### A.3 Editorská aplikace

| Adresa | Účel |
|---|---|
| `/admin/login` | přihlášení editora |
| `/admin/candidates` | fronta kandidátů (filtr podle stavu a zdroje), detail s doklady, `/admin/candidates/new` ruční návrh |
| `/admin/review` | dokumenty s příznakem ke kontrole a návrhy oprav |
| `/admin/drafts` | připravované dokumenty a převod návrhu na vyhlášený předpis (po nasazení kroku 3) |
| `/admin/audit-log` | záznam rozhodnutí |

### A.4 Doporučený týdenní běh (do zavedení plánovače)

```
cd /home/laborator/DEVEL/nahyc-h2db
.venv/bin/python src/tools/check_validity.py
.venv/bin/python src/tools/backup_db.py --reason before_weekly_run
.venv/bin/python src/tools/backfill_document_states.py --apply
.venv/bin/python src/tools/import_candidates.py --apply
.venv/bin/python src/tools/harvest_sources.py --cadence weekly --apply   # po nasazení kroku 3
.venv/bin/python src/tools/backfill_document_states.py --apply           # stavy a data kontrol
```

První den každého měsíce (do zavedení plánovače) navíc promítnutí stavů,
aby se normy přepnuly na nové vydání v den jeho účinnosti (nejbližší
1. 12. 2026 a 1. 1. 2027):

```
.venv/bin/python src/tools/backup_db.py --reason before_monthly_states
.venv/bin/python src/tools/backfill_document_states.py --apply
```

Související dokumenty: `doc/DATABASE_SCOPE.md` (rozsah, stavy, četnost),
`doc/CITATION_CLOSURE.md` (uzávěr citací), `doc/DATA_SOURCES.md` (registr
zdrojů a plán vytěžování; postup prvního ostrého běhu a návrh plánovače
v odstavci 8.17), `doc/MPO_TABULKY.md` (tabulky MPO a CDV jako zlatá sada),
`doc/MPO_VYPORADANI.md` (vypořádání připomínek MPO).
