# Rozsah pokrytí databáze regulačních dokumentů

> Historie dokumentu:  
> 2026-10-27 jprk Návrh první verze  
> 2026-10-27 jprk Rozhodnuté otázky O1–O3 (odstavec 8)

Tento dokument vymezuje, které regulační dokumenty má databáze
regulačních předpisů a předrealizačních procesů (tedy výsledek V01 dílčího projektu DP004 centra NAHYC) obsahovat,
v jakém rozsahu za jejich úplnost odpovídáme, jaké stavy dokumentů rozlišujeme
a jak často se obsah kontroluje. Je výchozím bodem pro metodiku měření pokrytí této domény, popsanou v odstavci 7,
a pro registr sledovaných zdrojů (v tento okamžik na vývojové větvi `automation` v souborech 
`data/monitored_sources.json` a odstavci 11  dokumentu `doc/AUTOMATION.md`).

## 1. Účel a východisko

Cílem je, aby databáze podávala s určitým, doložitelným stupněm jistoty úplný
přehled regulačních dokumentů, jež se vztahují k vodíkovým technologiím, a to
minimálně pro území České republiky. Dnešní obsah vychází ze tří rešerší
(zdroje `Prokop`, `Sinay` a `Haltuf` v adresáři `data/`), které úplné být nemusí;
jejich úplnost nelze prokázat dalším vyhledáváním, jen porovnáním s nezávislým
referenčním bodem. Proto nejprve vymezujeme, co do rozsahu patří, a teprve
z tohoto vymezení odvozujeme, co a jak měřit.

Úplnost netvrdíme absolutně. Výstupem bude přehled pokrytí po jednotlivých
okruzích a typech dokumentů s datem poslední kontroly a s metrikami podle
odstavce 7.

## 2. Úrovně pokrytí

Rozlišujeme tři úrovně, podle nichž se liší, co databáze o daném druhu dokumentů
slibuje:

1. **Úroveň A — úplnost sledujeme a měříme.** Databáze má obsahovat všechny
   dokumenty dané skupiny v rozsahu odstavce 3; chybějící dokument je vada.
2. **Úroveň B — zahrnujeme, úplnost neměříme.** Dokumenty databáze obsahuje,
   pokud je známe nebo je přinesou sledované zdroje; jejich soupis však
   úplný být nemusí.
3. **Úroveň C — na vyžádání.** Dokumenty, které mohou být potřeba při
   posuzování záměru na konkrétním místě, ale neevidujeme je plošně;
   dohledávají se pro dané místo.

### 2.1 Geografický rozsah

* **Česká republika** — úroveň A pro předpisy celostátní, úroveň C pro předpisy
  krajů a obcí (odstavec 2.2).
* **Evropská unie** — úroveň A v rozsahu, v němž předpisy EU působí na území ČR:
  přímo použitelná nařízení i směrnice, u nichž sledujeme také transpozici do
  českého práva (vazba `IMPLEMENTS`).
* **Mezinárodní úroveň** — mezinárodní smlouvy a mezinárodní normy podle
  odstavce 4.
* **Slovenská republika** — dokumenty, které databáze již obsahuje, v ní
  ponecháváme; úplnost slovenského pokrytí negarantujeme (úroveň B).

### 2.2 Předpisy krajů a obcí

Předpisy územních samosprávných celků (obecně závazné vyhlášky a nařízení krajů
a obcí) zařazujeme na úroveň C: plošně je neevidujeme, ale pro konkrétní místo
záměru mohou být rozhodující. Pro jejich dohledání patrně nebude potřeba procházet
weby jednotlivých obcí a u předpisů krajů a obcí půjde tento krok patrně
automatizovat (odstavec 8, otázka O1):

* Od 1. 1. 2022 existuje centrální **Sbírka právních předpisů územních
  samosprávných celků a některých správních úřadů** (zákon č. 35/2021 Sb.,
  správcem je Ministerstvo vnitra, `https://sbirkapp.gov.cz/`). Má být veřejně
  přístupnou databází platných a účinných předpisů krajů a obcí; vyhlášení ve
  Sbírce je podmínkou platnosti předpisu.
* **Územně plánovací dokumentace** (územní plány, regulační plány) není právním
  předpisem, ale opatřením obecné povahy, a ve Sbírce proto není. Pro umístění
  záměru je přitom patrně důležitější než obecně závazné vyhlášky. Nový stavební
  zákon (č. 283/2021 Sb.) zavádí **Národní geoportál územního plánování**
  (`https://uzemniplanovani.gov.cz/`) jako centrální místo pro zveřejňování
  územně plánovací dokumentace, s účinností od 1. 7. 2023.

Obě zjištění pocházejí z veřejně dostupných informací Ministerstva vnitra
a Ministerstva pro místní rozvoj. Ani jeden ze systémů nemá dokumentované
strojové rozhraní (odstavec 8, otázka O1); jak úplný je dnes obsah geoportálu,
zbývá ověřit.

## 3. Věcné okruhy

Za relevantní pro vodík považujeme regulační dokumenty, jež upravují celý
životní cyklus vodíku od výroby po využití, včetně podmínek pro umístění
a provoz zařízení. Okruhy jsou na úrovni A, pokud odstavec 4 u daného typu
dokumentu nestanoví jinak. Příklady uvádíme pro orientaci; nejde o úplný výčet.

1. **Výroba vodíku** — šedý, nízkouhlíkový i obnovitelný vodík nebiologického
   původu (RFNBO); elektrolýza, reformování, další procesy. Patří sem
   i **certifikace RFNBO a záruky původu**, bez nichž vodík za obnovitelný
   uznat nelze: směrnice (EU) 2018/2001 ve znění směrnice (EU) 2023/2413
   a delegovaná nařízení (EU) 2023/1184 a (EU) 2023/1185.
2. **Skladování** — tlakové zásobníky a nádoby, skladování v kapalném stavu
   a v chemicky vázané formě, podzemní zásobníky; tlaková zařízení
   (směrnice 2014/68/EU).
3. **Přeprava** — v libovolné formě (stlačený, zkapalněný, chemicky vázaný,
   ve směsi se zemním plynem) a libovolným způsobem: silniční (ADR), železniční
   (RID), vnitrozemská vodní (ADN), plynovody a vodíkové sítě (nařízení
   (EU) 2024/1789 a směrnice (EU) 2024/1788 o trzích s plynem a vodíkem),
   přepravitelná tlaková zařízení.
4. **Plnění do vozidel** — plnicí stanice, infrastruktura pro alternativní
   paliva (nařízení (EU) 2023/1804, AFIR), kvalita paliva (zákon o pohonných
   hmotách č. 311/2006 Sb., ČSN EN 17124) a **metrologie** výdejních stojanů
   (zákon o metrologii č. 505/1990 Sb.).
5. **Provoz vozidel** — schvalování silničních vozidel (nařízení (EU) 2018/858
   a (EU) 2019/2144, předpis EHK OSN č. 134), podmínky provozu vozidel na
   pozemních komunikacích (zákon č. 56/2001 Sb.), kolejová vozidla
   (technické specifikace pro interoperabilitu), případně provoz v garážích
   a tunelech.
6. **Využití vodíku mimo vozidla** — průmysl (rafinerie, výroba amoniaku,
   ocelářství), přimíchávání do plynárenské soustavy, stacionární palivové
   články, kombinovaná výroba elektřiny a tepla, akumulace energie
   (power-to-gas). Od novely provedené zákonem č. 469/2023 Sb. je vodík plynem
   podle energetického zákona, takže se tento okruh úzce prolíná s okruhem 9.
7. **Bezpečnost** — chemické látky a směsi (nařízení (ES) 1907/2006, REACH,
   nařízení (ES) 1272/2008, CLP, chemický zákon č. 350/2011 Sb.), prevence
   závažných havárií (zákon č. 224/2015 Sb., směrnice 2012/18/EU, SEVESO III),
   výbušná prostředí (směrnice 2014/34/EU a 1999/92/ES, ATEX), tlaková
   zařízení, požární ochrana (zákon č. 133/1985 Sb.) a bezpečnost a ochrana
   zdraví při práci (zákon č. 309/2006 Sb.).
8. **Stavební řízení a umístění** — stavební zákon č. 283/2021 Sb. a jeho
   prováděcí předpisy, technické požadavky na stavby, územní plánování
   (s územně plánovací dokumentací na úrovni C, odstavec 2.2).
9. **Energetika** — energetický zákon č. 458/2000 Sb., pravidla trhu s plynem
   a vodíkem, transevropská energetická infrastruktura (nařízení (EU) 2022/869),
   podporované zdroje energie (zákon č. 165/2012 Sb.).
10. **Životní prostředí** — posuzování vlivů na životní prostředí (zákon
    č. 100/2001 Sb., EIA), integrovaná prevence (zákon č. 76/2002 Sb.,
    směrnice 2010/75/EU), ochrana ovzduší (zákon č. 201/2012 Sb.), obchodování
    s povolenkami na emise.

**Doplňkové okruhy, prozatím odložené:** daně a dotace. Výjimkou je certifikace
RFNBO (okruh 1), jež patří do jádra, protože na ní závisí samotné vymezení
obnovitelného vodíku.

Okruhy budou navázány na klasifikaci, kterou databáze již používá
(sekce typu „A - výroba“ ve zdrojových rešerších a procesní uzly U1–U7
definované v dokumentu V02). Z takového propojení vznikne matice pokrytí
okruh × typ dokumentu, nad níž se pokrytí v odstavci 7 měří.

## 4. Typy dokumentů

| Typ | Příklady | Úroveň | Odkud se zjišťuje stav |
|---|---|---|---|
| Národní předpisy | zákony, nařízení vlády, vyhlášky | A | e-Sbírka; návrhy VeKLEP |
| Předpisy EU | nařízení (přímo použitelná), směrnice (s transpozicí), rozhodnutí, akty v přenesené pravomoci a prováděcí akty | A | EUR-Lex / Cellar; návrhy Komise (COM) |
| Mezinárodní smlouvy | ADR, RID (COTIF), ADN, předpisy EHK OSN | A | depozitáři smluv (EHK OSN, OTIF); jejich vyhlášení ve Sbírce mezinárodních smluv |
| Normy převzaté do soustavy ČSN | ČSN, ČSN EN, ČSN EN ISO; harmonizované normy s vazbou na směrnici | A (jen metadata) | ÚNMZ a jeho Věstník, katalog ČSN |
| Mezinárodní normy dosud nepřevzaté | všechny relevantní normy ISO a IEC (a EN) bez českého převzetí; návrhy (prEN, DIS) | A (jen metadata) | CEN, ISO, IEC |
| Technická pravidla a metodiky | technická pravidla TPG, TD a TIN Českého plynárenského svazu, metodické pokyny ministerstev, doporučení EIGA a HYTEP | B (u TPG, TD a TIN jen metadata a odkaz) | vydavatelé |
| Strategie a koncepce | Vodíková strategie ČR, strategie EU | B | vydavatelé |
| Předpisy krajů a obcí; územně plánovací dokumentace | obecně závazné vyhlášky, územní plány | C | Sbírka právních předpisů ÚSC; Národní geoportál územního plánování |

U norem databáze uchovává jen metadata (označení, název, stav, vazby); plný
text je chráněný a databáze ho nenabízí (požadavek R4.1 v `doc/REQUIREMENTS.md`).

Technická pravidla TPG, TD a TIN Českého plynárenského svazu jsou dostupná
bezplatně, ale jen ke čtení v on-line prohlížeči po bezplatné registraci;
dokumenty nesou vodoznaky a jejich stažení ani tisk nejsou dovoleny. Databáze
proto u nich uchovává jen metadata a uživatele přesměrovává na stránky Českého
plynárenského svazu. **Poznámka pro analytickou část:** pro elektronické
zpracování v poradním systému bude třeba tato pravidla obstarat v podobě, jež
jejich načtení a zpracování umožní (odstavec 8, otázka O2).

**Mimo rozsah:** judikatura, individuální správní akty (rozhodnutí, povolení)
a prozatím daně a dotace (odstavec 3).

## 5. Stavy dokumentů

České právo rozlišuje **platnost** (vyhlášení) a **účinnost** (okamžik, od něhož
se předpis použije). Původně navrhované rozlišení „platný / neplatný / připravovaný“ proto
nepostačuje a zavádíme tyto stavy:

| Stav | Význam | Příklad |
|---|---|---|
| připravovaný | návrh v legislativním procesu | návrh ve VeKLEP, návrh Komise (COM), prEN |
| vyhlášený, dosud neúčinný | platný předpis s odloženou účinností | zákon s pozdějším dnem účinnosti |
| účinný | předpis, jenž se použije | běžný stav |
| zrušený nebo nahrazený | předpis, jenž se již nepoužije; s vazbou na nástupce | zrušený zákon, nahrazená norma |

Pro jednotlivé typy dokumentů stavy upřesňujeme:

* **Směrnice EU** mají navíc stav „účinná, dosud netransponovaná“, odvozený
  z vazby `IMPLEMENTS` na české prováděcí předpisy.
* **Normy** mají stavy „návrh“ (prEN, DIS), „platná“ a „zrušená“ nebo
  „nahrazená“.
* **Strategie a technická pravidla** rozlišují jen „aktuální“ a „nahrazený“.

Zrušené a nahrazené dokumenty v databázi ponecháváme kvůli souvislostem
(procesní vrstva, historie změn) a propojujeme je s nástupcem (vazby `REPEALS`
a `AMENDS`). Původní návrh databáze rozlišoval jen stavy `active`, `draft`
a `superseded` (`DocumentVersion.lifecycle_state`). Od 27. 10. 2026 přibyly stavy
`promulgated` (vyhlášený, dosud neúčinný) a `repealed` (zrušený); u aktuální verze
dokumentu je nastavuje kontrola platnosti (`src/tools/check_validity.py`
a `src/tools/document_states.py`), zrušený dokument je vazbou `REPEALS` propojen
s předpisem, který jej zrušil, pokud jej databáze obsahuje. Stavy specifické pro
směrnice, normy a strategie (výše) zatím zavedeny nejsou.

## 6. Četnost kontrol

Četnost odlišujeme podle povahy zdroje:

| Četnost | Co se kontroluje |
|---|---|
| týdně | registry předpisů: e-Sbírka, EUR-Lex (Cellar), VeKLEP |
| měsíčně | normy (Věstník ÚNMZ vychází měsíčně), mezinárodní smlouvy |
| čtvrtletně | strategie, technická pravidla a metodiky; měření úplnosti podle odstavce 7 |

Každá automatizovaná kontrola sleduje nejen **nové dokumenty**, ale i **změny stavu dokumentů,
které databáze již obsahuje** (zrušení, novelizace, nabytí účinnosti, nahrazení
normy). Pro aktuálně platný přehled je druhé patrně stejně důležité jako první.
Výsledek kontroly se zaznamenává i tehdy, když nic nového nepřinese (zdroj,
datum, rozsah dotazu), protože doložené negativní výsledky jsou součástí
tvrzení o úplnosti.

## 7. Navazující práce

Z vymezení vyplývají tyto kroky:

1. **Měření úplnosti.** Pro dokumenty úrovně A budeme kombinovat nezávislé
   kontroly: uzávěr citací (předpisy citované v textech, které databáze ještě
   neobsahuje), porovnání s autoritativním registrem shora (u směrnic EU úplný
   seznam českých prováděcích předpisů z EUR-Lexu, u českých předpisů vazby
   novelizací a platnosti z e-Sbírky), odhad počtu nenalezených dokumentů
   z překryvu tří rešerší a zlatou sadu dokumentů sestavenou odborníky.
   Doplňkovým hlediskem je procesní vrstva: procesní uzel nebo technologie bez
   jediného regulačního dokumentu ukazuje na mezeru.
2. **Provenance.** U každého dokumentu je potřeba evidovat, které zdroje jej
   kdy zachytily; bez toho nelze měřit přínos zdrojů ani odhadovat, co chybí.
3. **Návrhy nových zdrojů.** Registr sledovaných zdrojů rozšíříme o stav
   „navržený“ a o standardní zkušební sondu, jež před napsáním stahovacího
   modulu změří, kolik nových dokumentů z rozsahu podle tohoto dokumentu by
   zdroj přinesl.
4. **Stavy dokumentů.** Rozšíření schématu o stavy podle odstavce 5.

## 8. Rozhodnuté otázky

Otázky položené v předešlých verzích dokumentu a jejich řešení:

- **O1: Strojové rozhraní Sbírky právních předpisů ÚSC a Národního geoportálu
  územního plánování.** Sbírka právních předpisů územních samosprávných celků
  dokumentované rozhraní nemá; jde o webovou aplikaci (SPA), jež si data pro
  vyhledávání stahuje na pozadí. Patrně by bylo možné použít její interní,
  nedokumentované rozhraní, s rizikem, že se bez ohlášení změní. Národní geoportál
  územního plánování je dostupný jen po přihlášení přes Národní identitní autoritu
  (NIA), takže jeho automatizované procházení patrně možné nebude a územně
  plánovací dokumentaci budeme dohledávat ručně pro konkrétní místo záměru.
- **O2: Dostupnost technických pravidel TPG, TD a TIN.** Pravidla nejsou placená,
  ale jsou dostupná jen ke čtení v on-line prohlížeči po bezplatné registraci,
  s vodoznaky a se zákazem stažení a tisku. Databáze je uživatelům poskytovat
  nemůže; uchovává metadata a odkazuje na stránky Českého plynárenského svazu
  (odstavec 4). Pro analýzu v poradním systému je bude třeba obstarat
  k elektronickému zpracování.
- **O3: Rozsah norem nepřevzatých do soustavy ČSN.** Sledujeme všechny relevantní
  normy ISO a IEC, nejen ty, na které odkazují předpisy úrovně A; skupina tím
  přechází na úroveň A (jen metadata, odstavec 4).
