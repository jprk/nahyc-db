# Vypořádání připomínek Ministerstva průmyslu a obchodu k výsledku V01

> Historie dokumentu:  
> 2026-11-19 jprk Návrh první verze jako podklad k jednání s MPO

Dokument shrnuje vypořádání připomínek, jež Ing. Petr Mervart, aplikační
garant dílčího projektu DP004 za Ministerstvo průmyslu a obchodu, vznesl
k výsledku V01 „Databáze regulačních předpisů a předrealizačních procesů“.
Ke každé připomínce uvádíme její znění, příčinu nedostatku, opatření, jež
jsme již provedli, a opatření, jež ještě provedeme, včetně předpokládaného
termínu. V odstavci 4 odpovídáme na otázky, jež MPO položilo nebo jež
z připomínek vyplývají, v odstavci 5 uvádíme další nedostatky, jež jsme
při rozboru nalezli sami, a v odstavci 6 harmonogram dalšího postupu.
Dokument končí otevřenými otázkami k jednání (odstavec 7) a přílohou A se
seznamem strategických dokumentů z rešerše, z nichž jsme dokumenty
s prioritou A a B do databáze doplnili.

Stav databáze a webové aplikace uvádíme k 19. 11. 2026. Všechna čísla jsme
ověřili dotazem nad provozní databází v tento den.

## 1. Podklady

Vypořádáváme připomínky ze dvou e-mailů:

1. **E-mail ze 17. 4. 2026** — Šest konkrétních výhrad doložených snímky
   obrazovky a celkové hodnocení, že výsledek „v této podobě“ nelze schválit,
   s upozorněním, že „aplikační garant a Ministerstvo průmyslu a obchodu
   nejsou beta-testeři aplikací“.
2. **E-mail z 22. 5. 2026** — Dvě tabulky předpisů, jež by podle MPO měly být
   v databázi (česká legislativa, zpracovaná Ing. Revíkovou, a evropská
   a mezinárodní legislativa, zpracovaná Centrem dopravního výzkumu), návrh
   nové kategorie „Strategie“, dotaz, jak bude zajištěna aktuálnost předpisů,
   a návrh telekonference začátkem června 2026.

Na e-mail ze 17. 4. 2026 jsme reagovali se zpožděním až 20. 5. 2026. Za
zpoždění se omlouváme. [DOPLNIT: zda telekonference navržená na začátek
června 2026 proběhla a co se na ní dohodlo.]

Připomínky považujeme za oprávněné. Jejich společnou příčinou patrně je, že
databáze vznikla sloučením tří samostatných rešerší, jež se lišily rozsahem,
způsobem zápisu označení i přiřazením odpovědných institucí, a že jsme
výsledek předali bez soustavné kontroly obsahu z pohledu uživatele a bez
nezávislého měření úplnosti. Obojí nyní napravujeme (odstavec 6).

## 2. Přehled stavu připomínek

| # | Připomínka (zkráceně) | Stav k 19. 11. 2026 | Zbývá |
|---|---|---|---|
| 1 | Dokument se ve výsledcích zobrazí dvakrát česky a dvakrát anglicky. | Duplicity odstraněny; dotčený dokument (rozhodnutí ECB) z databáze vyřazen jako nesouvisející. | Zobrazit jazykové verze v jednom řádku (etapa 2). |
| 2 | Dotaz „RFNBO“ vrací čtyřikrát týž dokument. | Duplicity odstraněny; dotaz vrací jeden dokument. | Vyhledávat i podle synonym a zkratek, aby dotaz našel i akty RFNBO (etapa 2). |
| 3 | V databázi chybějí akty v přenesené pravomoci. | Pět aktů v databázi je; nařízení (EU) 2023/1185 má nově český název. | Doplnit (EU) 2025/2359 a další (etapa 1); zavést podtyp aktů (etapa 2). |
| 4 | Současně „MD“ i „Ministerstvo dopravy“. | Vyřešeno; zkratky nahrazeny plnými názvy. | — |
| 5 | MPO je uvedeno jako odpovědné za zákon o dráhách. | Vyřešeno; opraveny i další chybně přiřazené instituce. | Rozdělit filtr institucí podle jurisdikce (etapa 2). |
| 6 | U energetického zákona se zobrazuje zastaralá hláška. | Vyřešeno; hláška i interní poznámky z vývoje odstraněny z veřejných popisů. | Doplnit popisy dokumentům, jež po odstranění poznámek popis nemají (průběžně). |
| 7 | Databáze neobsahuje připravované předpisy. | Sběr návrhů předpisů je vyvinut a ověřen na testovací databázi. | Uvést do provozu (etapa 3). |
| 8 | Chybějí i existující předpisy (tabulky MPO a CDV). | Rozbor proveden: z 42 českých předpisů tabulky MPO je v databázi 12. | Doplnit chybějící předpisy přes frontu kandidátů (etapa 1). |
| 9 | Nová kategorie „Strategie“. | Kategorie „Strategie“ zavedena (přejmenováním dosavadního typu), doplněno 13 strategií podle přílohy A, celkem 25 dokumentů. | Posoudit strategie s prioritou C; pravidelně kontrolovat aktuálnost strategií (etapa 3). |
| 10 | Jak bude zajištěna aktuálnost předpisů. | Kontrola platnosti a stavy dokumentů zavedeny; postup popsán v provozním dokumentu. | Pravidelné spouštění kontrol (etapa 3). |

## 3. Vypořádání jednotlivých připomínek

### 3.1 Opakované zobrazení dokumentu v obou jazycích

**Znění:** „Proč, když je dokument vybrán podle nějakého kritéria, tak se
zobrazí několikrát, níže uvedený příklad 2× česky a 2× anglicky; že se to
zobrazí česky a anglicky chápu, ale proč 2× v každém jazyce.“ Příkladem bylo
rozhodnutí Evropské centrální banky (EU) 2018/546.

**Příčina:** Týž předpis byl zachycen ve více podkladových rešerších
a jejich záznamy se lišily zápisem označení, takže je slučování nerozpoznalo
jako jeden dokument. Česká a anglická verze téhož aktu byly navíc vedeny
jako dva samostatné řádky výsledků. Konkrétní rozhodnutí ECB se navíc
vodíkových technologií netýká; do databáze se patrně dostalo chybným
ztotožněním označení v jedné z rešerší.

**Co jsme udělali:** Duplicitní záznamy jsme sloučili; každá jazyková verze
aktu je nyní v databázi jen jednou a anglická verze je s českou propojena
vazbou „překlad“. Rozhodnutí ECB (EU) 2018/546 jsme jako dokument mimo
rozsah databáze vyřadili. Opravu jsme zapsali tak, aby ji neodstranilo ani
případné nové sestavení databáze z podkladů.

**Co ještě uděláme:** Ve výsledcích vyhledávání bude každý předpis zobrazen
jedním řádkem a jeho dostupné jazykové verze budou uvedeny jako štítky
(např. CS, EN) v tomto řádku (etapa 2). Na stránce aplikace vysvětlíme,
u kterých dokumentů a proč vedeme i anglickou verzi
[DOPLNIT po kroku 2].

### 3.2 Opakovaný výsledek dotazu „RFNBO“

**Znění:** „Proč, když zadám RFNBO, se mi objeví 4× stejný dokument,
tentokráte jen v ČJ, proč je tam něco jen v ČJ a jindy v ČJ a EN.“

**Příčina:** Směrnice (EU) 2023/2413 (RED III) byla v databázi několikrát
ze stejného důvodu jako v odstavci 3.1. Anglickou verzi vedeme jen
u dokumentů, jež ji měla podkladová rešerše (26 dvojic); tato zásada nebyla
uživateli nikde vysvětlena. Vyhledávání navíc prochází jen název a popis
dokumentu, nikoli zkratky a synonyma, takže dotaz „RFNBO“ nenachází akty
v přenesené pravomoci (EU) 2023/1184 a 2023/1185, jež pojem RFNBO přímo
vymezují.

**Co jsme udělali:** Duplicity jsme odstranili; dotaz „RFNBO“ nyní vrací
jediný dokument, směrnici RED III. Z jejího popisu jsme odstranili
zastaralou poznámku (odstavec 3.6).

**Co ještě uděláme:** Vyhledávání rozšíříme o klíčová slova a synonyma
(RFNBO, AFIR, RED III, LEX OZE, LEX vodík apod.), takže dotaz na zkratku
najde i dokumenty, jež ji v názvu nemají (etapa 2) [DOPLNIT po kroku 2].
Jazykové verze budou zobrazeny podle odstavce 3.1.

### 3.3 Akty v přenesené pravomoci

**Znění:** „Proč tam nejsou delegované akty, přestože to jsou jedny
z nejdůležitějších dokumentů pro vodíkové technologie?“

**Příčina:** Databáze akty v přenesené pravomoci obsahovala, ale nebylo
možné je jako takové najít: typ dokumentu nerozlišoval akty v přenesené
pravomoci a prováděcí akty od ostatních nařízení EU, nařízení (EU)
2023/1185 mělo jen anglický název a vyhledávání neznalo pojem „delegovaný“.
Některé akty v databázi skutečně chyběly, mimo jiné nařízení v přenesené
pravomoci (EU) 2025/2359 o metodice pro nízkouhlíkový vodík.

**Co jsme udělali:** Ověřili jsme, že databáze obsahuje nařízení
v přenesené pravomoci (EU) 2023/1184, 2023/1185, 2018/674, 2019/1745
a 2025/656. Nařízení (EU) 2023/1185 má nyní úřední český název.

**Co ještě uděláme:** Doplníme chybějící akty, především (EU) 2025/2359
(etapa 1). Zavedeme podtyp „akt v přenesené pravomoci“ a „prováděcí akt“,
podle něhož bude možné výsledky filtrovat (etapa 2). Nové akty v přenesené
pravomoci bude průběžně zachycovat sledování rejstříku aktů v přenesené
pravomoci Evropské komise (odstavec 4.3) [DOPLNIT po krocích 1 až 3].

### 3.4 Instituce „MD“ a „Ministerstvo dopravy“

**Znění:** „Proč je v systému současně ‚MD‘ a ‚Ministerstvo dopravy‘? Čím
se tyto instituce liší?“

**Příčina:** Podkladové rešerše zapisovaly odpovědné instituce zčásti
zkratkou a zčásti plným názvem a zápis jsme při slučování nesjednotili.

**Co jsme udělali:** Zkratky jsme nahradili plnými názvy institucí; každá
instituce je v nabídce uvedena jednou.

**Co ještě uděláme:** Nic dalšího; s připomínkou však souvisí odstavec 3.5.

### 3.5 MPO jako instituce odpovědná za zákon o dráhách

**Znění:** „Proč je MPO odpovědné za zákon o dráhách?“

**Příčina:** Pravidlo, jímž jsme při slučování rešerší přiřazovali
odpovědnou instituci záznamům, jež ji v podkladu neměly, bylo chybné.
Kromě zákona o dráhách přiřadilo české instituce i předpisům slovenským
a některým předpisům EU a mezinárodním smlouvám.

**Co jsme udělali:** Zákon č. 266/1994 Sb., o dráhách, i zákon
č. 426/2021 Sb. mají nyní jako odpovědnou instituci Ministerstvo dopravy,
stejně jako nařízení vlády č. 133/2005 Sb.; zákon č. 250/2021 Sb. má
Ministerstvo práce a sociálních věcí. Všem 23 slovenským předpisům jsme
přiřadili slovenské orgány, dohodě ADR Evropskou hospodářskou komisi OSN,
řádu RID Mezivládní organizaci pro mezinárodní železniční přepravu (OTIF)
a sdělení Komise COM(2020) 301 Evropskou komisi. Slovenskému zákonu
č. 250/2012 Z. z., o regulácii v sieťových odvetviach, jsme jako
odpovědnou instituci přiřadili jeho předkladatele, Ministerstvo
hospodárstva Slovenskej republiky. Odpovědné instituce
českých předpisů jsme porovnali se sloupcem „Nositel“ tabulky MPO; jiná
neshoda než u zákona č. 250/2021 Sb. se nevyskytla.

**Co ještě uděláme:** Filtr odpovědných institucí dnes míchá česká
ministerstva, orgány EU a normalizační orgány. Rozdělíme jej podle
jurisdikce (Česká republika, Evropská unie, mezinárodní organizace,
normalizační orgány), aby se v něm uživatel snáze orientoval (etapa 2)
[DOPLNIT po kroku 2].

### 3.6 Zastaralá hláška u energetického zákona

**Znění:** „Proč, když si kliknu na energetický zákon, tak se i tam na jaře
2026 objeví zcela irelevantní hláška“ („Stav ke dni 30. 6. 2025 – čeká se na
podpis prezidenta“); „dnes již pracujeme na další aktualizaci LEX vodík“.

**Příčina:** Hláška pocházela z poznámky v podkladové rešerši a byla
převzata do popisu směrnice RED III, na niž se uživatel ze stránky
energetického zákona dostal přes vazby mezi dokumenty. Obdobně bylo
v popisech 231 dokumentů ponecháno interní sdělení o tom, jakým postupem byl
záznam do databáze získán. Takové poznámky do veřejného popisu nepatří a údaje
v nich s časem zastarávají.

**Co jsme udělali:** Popis směrnice RED III jsme nahradili popisem bez
údajů, jež zastarávají. Interní poznámky o původu záznamu jsme ze všech 231
popisů přesunuli do samostatného údaje, jejž veřejné stránky nezobrazují.
U 229 z nich byla poznámka jediným obsahem popisu; tyto dokumenty jsou nyní
bez popisu a jsou označeny ke kontrole editorem.

**Co ještě uděláme:** Dokumentům bez popisu doplníme popis převzatý
z autoritativního zdroje (průběžně, přednostně u předpisů). Připravovanou
aktualizaci „LEX vodík“ bude databáze zachycovat sledováním legislativního
procesu (odstavec 4.4).

### 3.7 Připravované předpisy

**Znění:** „Když jsme tento projekt připravovali, … sliboval, že si systém
bude sahat do databáze připravovaných zákonů a budou tam nejen ty
existující, ale ty připravované.“

**Příčina:** Výsledek V01 jsme předali ve stavu, kdy databáze evidovala
jen vyhlášené předpisy a normy; sledování legislativního procesu nebylo
součástí předané verze. Tento slib jsme tedy dosud nesplnili.

**Co jsme udělali:** Vyvinuli jsme sběr návrhů předpisů z Vládní
legislativní pracovní plochy (VeKLEP), z otevřených dat Poslanecké
sněmovny (sněmovní a senátní tisky) a z Legislativní observatoře
Evropského parlamentu a ověřili jej na testovací kopii databáze. Zkušební
běh 4. 11. 2026 našel 44 návrhů předpisů, jež se databáze týkají. Do
veřejné verze databáze tato část dosud nebyla nasazena. Podrobnosti uvádíme
v odstavci 4.4.

**Co ještě uděláme:** Sběr uvedeme do provozu nad provozní databází,
doplníme editorské rozhraní pro posouzení návrhů a převod připravovaného
předpisu na vyhlášený a na stránce dokumentu budeme stav „připravovaný“
zřetelně zobrazovat (etapa 3) [DOPLNIT po kroku 3].

### 3.8 Chybějící existující předpisy (tabulky MPO a CDV)

**Znění:** „Tady nejsou ani ty existující.“ (e-mail ze 17. 4. 2026);
„identifikovali jsme mnohem více dokumentů, které by měly být na webu
uvedeny“ (e-mail z 22. 5. 2026, se dvěma tabulkami).

**Příčina:** Obsah databáze vychází ze tří rešerší, jejichž úplnost jsme
před předáním neměřili. Kontrola úplnosti, již jsme zavedli později
(vyhledání předpisů citovaných v textech dokumentů databáze), tyto předpisy
nezachytila, protože je dokumenty databáze necitují nebo je citují jen
zřídka. Tabulky MPO a CDV jsou tak patrně nejcennějším nezávislým měřítkem
úplnosti, jež máme k dispozici.

**Co jsme udělali:** Obě tabulky jsme porovnali s databází:

* **Tabulka MPO (česká legislativa)** uvádí 42 různých právních předpisů
  (zákon č. 250/2021 Sb. dvakrát) a 7 norem ČSN. Z právních předpisů je
  v databázi 12, další 3 čekají na posouzení ve frontě kandidátů
  (108/2011 Sb., 345/2002 Sb., 586/1992 Sb.) a 27 v databázi chybí:
  vyhlášky Energetického regulačního úřadu (349/2015 Sb., 488/2021 Sb.,
  401/2010 Sb., 513/2021 Sb., 8/2016 Sb., 489/2021 Sb.), vyhlášky MPO
  (344/2012 Sb., 110/2022 Sb., 166/2022 Sb., 328/2022 Sb., 264/2020 Sb.),
  předpisy k zásobníkům plynu, těžbě a báňské bezpečnosti (44/1988 Sb.,
  61/1988 Sb., 62/1988 Sb., 71/2002 Sb., 72/2002 Sb., 104/1988 Sb.,
  239/1998 Sb., 392/2003 Sb., 85/2012 Sb.), předpisy k prevenci závažných
  havárií (226/2015 Sb., 277/2015 Sb.), zákony č. 249/2025 Sb.
  a 406/2000 Sb., nařízení vlády č. 191/2022 Sb. a 219/2016 Sb. a vyhláška
  č. 146/2024 Sb. Normy z tabulky v databázi jsou, z řady ČSN EN 60079 však
  jen část 0.
* **Tabulka CDV (evropská a mezinárodní legislativa)**: Chybí nařízení
  v přenesené pravomoci (EU) 2025/2359 a nařízení (EU) 2024/1679
  o transevropské dopravní síti. Nařízení AFIR (EU) 2023/1804 a balíček
  o trzích s vodíkem a plynem ((EU) 2024/1788 a (EU) 2024/1789) v databázi
  jsou, balíček však není veden jako celek. Položkám označujícím technické
  komise se věnujeme v odstavci 4.1. Položce „IMO pravidla pro přepravu
  vodíku“ odpovídá v databázi dokument IMO CCC 8/WP.3, příloha 2.

**Co ještě uděláme:** Všechny chybějící položky obou tabulek zařadíme do
fronty kandidátů, kde je posoudí a přijmou dva editoři (odstavec 4.3),
a doplníme chybějící instituce (Energetický regulační úřad, Český báňský
úřad) (etapa 1) [DOPLNIT po kroku 1: počet přijatých předpisů]. Obě tabulky
převezmeme jako referenční soubor dokumentů, jejichž přítomnost v databázi
bude hlídat automatický test, aby se případná ztráta dokumentu projevila
ihned. Úplnost budeme dále měřit postupy popsanými v provozním dokumentu
(odstavec 4.3).

### 3.9 Kategorie „Strategie“

**Znění:** „Navrhujeme také vytvořit novou kategorii: Strategie, kde by
mohla být minimálně česká a evropská vodíková strategie, případně i další
národní a evropské strategie.“

Odpověď uvádíme v odstavci 4.2.

### 3.10 Aktuálnost předpisů

**Znění:** „Bude nás také zajímat, jak se bude celý systém udržovat, aby se
zajistila aktuálnost předpisů.“

Odpověď uvádíme v odstavci 4.3.

### 3.11 Celkové hodnocení a role aplikačního garanta

**Znění:** „V této podobě to rozhodně nemůžeme schválit“; „aplikační
garant a Ministerstvo průmyslu a obchodu nejsou beta-testeři aplikací“.

**Příčina:** Před předáním jsme aplikaci testovali jen technicky (zda
stránky fungují), nikoli z pohledu uživatele, jenž v databázi hledá
konkrétní předpis. Nedostatky popsané v připomínkách 1 až 6 by takové
testování patrně odhalilo.

**Co ještě uděláme:** Každý scénář z připomínek MPO převedeme do
automatického testu v prohlížeči, jenž se spouští před každou změnou
aplikace a ověřuje, že se nedostatek neopakuje. Před opětovným předáním
necháme aplikaci projít osobou mimo vývojový tým (interní akceptace)
a výsledky akceptace předáme MPO spolu s tímto přehledem (etapa 4).

## 4. Odpovědi na otázky MPO

### 4.1 Proč položky „ISO/TC 22“ a obdobné nejsou dokumenty

Tabulka CDV obsahuje položky ISO/TC 22, ISO/TC 193, ISO/TC 268, IEC/TC 105
a CEN/TC 234, 235 a 268. Nejde o dokumenty, ale o označení **technických
komisí** normalizačních organizací, tedy pracovních orgánů, jež normy
připravují. Databáze eviduje dokumenty, jež lze citovat a jež mají stav
platnosti (normy, předpisy); komise sama žádnou povinnost nestanoví. Navíc
každá z těchto komisí vydává desítky až stovky norem, z nichž se vodíku
týká jen část, a zařazení komise jako celku by tedy o vodíkových normách
mnoho neřeklo.

Místo komisí proto nabízíme přehled norem, jež tyto komise vydaly a jež
databáze obsahuje. Pro představu uvádíme vybrané řady (počty zahrnují
i česká a slovenská převzetí téže normy):

| Komise | Zaměření | Vybrané řady norem | Záznamů v databázi |
|---|---|---|---|
| IEC/TC 105 | technologie palivových článků | IEC 62282 | 30 |
| ISO/TC 22 | silniční vozidla | ISO 6469, ISO 23273, ISO 12619, ISO 15500, ISO 21266 | 19 |
| ISO/TC 193 | zemní plyn | ISO 6974, ISO 6976, ISO 13686 | 4 |
| CEN/TC 234 | plynárenská infrastruktura | EN 1594, EN 12007, EN 1918 | 12 |
| CEN/TC 235 | regulátory tlaku plynu a bezpečnostní zařízení | EN 334, EN 14382 | 2 |
| CEN/TC 268 | kryogenní nádoby a specifické vodíkové technologie | EN 17124, EN 17127 | 5 |

Upozorňujeme, že ISO/TC 268 se zabývá udržitelnými městy a obcemi, nikoli
vodíkem; v tabulce CDV jde patrně o záměnu s CEN/TC 268. Naopak v tabulce
chybí patrně nejdůležitější komise, **ISO/TC 197 Vodíkové technologie**
(normy ISO 14687, ISO 19880, ISO 19881, ISO 19882 a další); z jejích řad
eviduje databáze 30 záznamů.

Navrhujeme na stránce dokumentu normy uvádět, kterou komisí byla připravena,
a umožnit podle komise filtrovat. Tím by se požadavek, jenž za položkami
tabulky patrně stojí, splnil v podobě, jež zachovává zásadu „jeden záznam,
jeden dokument“ [DOPLNIT po kroku 2, pokud bude zařazeno].

### 4.2 Kategorie „Strategie“

Typ dokumentu „Strategický dokument“, jenž databáze měla, jsme podle návrhu
MPO přejmenovali na „Strategie“ a kategorii doplnili. Obsahuje
25 dokumentů:

* Vodíková strategie České republiky (2021) a její aktualizace (2024);
* Vodíková strategie EU (2020): úřední české znění sdělení COM(2020) 301
  z EUR-Lexu, jež bylo dříve chybně vedeno jako „Nezařazeno“, a s ním
  propojené slovenské znění; dále český překlad zveřejněný platformou
  HYTEP;
* Vnitrostátní plán České republiky v oblasti energetiky a klimatu
  (aktualizace 2024), Státní energetická koncepce České republiky (2015)
  a Politika ochrany klimatu v České republice (2017);
* 2. aktualizace Národního akčního plánu čisté mobility (2024) a jí
  nahrazená aktualizace z roku 2019 s přílohou;
* devět sdělení Evropské komise: Zelená dohoda pro Evropu, Strategie EU
  pro integraci energetického systému, Strategie pro udržitelnou
  a inteligentní mobilitu, „Fit for 55“, Plán REPowerEU, Průmyslový plán
  Zelené dohody, Sdělení o Evropské vodíkové bance, Dohoda o čistém
  průmyslu a AccelerateEU;
* Akční plán digitální a zelené transformace pro vodíkové technologie
  (2026), Strategická výzkumná agenda pro rozvoj vodíkového hospodářství
  (2023), Cestovní mapa rozvoje vodíkového hospodářství (2023), Politický,
  legislativní a nelegislativní rámec EU pro rozvoj vodíkového trhu (2024)
  a Legislativní a politicko-strategický rámec EU s vlivem na rozvoj
  vodíkové mobility (2023/2024).

Třináct strategií jsme doplnili podle rešerše v příloze A (všechny
dokumenty s prioritou A a B). U každé uvádíme úřední název, vydavatele,
datum schválení, adresu na stránkách vydavatele nebo v EUR-Lexu a věcný
popis vztahu k vodíku; plný text je k dispozici u všech.
[DOPLNIT: datum zápisu do provozní databáze.]

Nahrazená strategie zůstává v databázi kvůli souvislostem: aktualizace
Národního akčního plánu čisté mobility z roku 2019 a její příloha jsou
vedeny jako nahrazené, s vazbou na 2. aktualizaci, jež je nahradila.
Strategie s prioritou C (šest sdělení Komise s okrajovou vazbou na vodík)
navrhujeme posoudit na jednání (odstavec 7). Aktualizaci Státní
energetické koncepce a aktualizaci Politiky ochrany klimatu do roku 2050
doplníme po jejich schválení vládou.

Strategie řadíme mezi dokumenty, jež databáze zahrnuje, aniž by
garantovala jejich úplnost (nejde o právně závazné předpisy). Jejich
aktuálnost budeme kontrolovat čtvrtletně (odstavec 4.3).

### 4.3 Jak bude zajištěna aktuálnost

Postup podrobně popisuje samostatný provozní dokument „Provoz a udržování
aktuálnosti databáze“, jejž přikládáme. Stručně:

1. **Sledované zdroje.** Nové dokumenty a změny stavu dokumentů budeme
   zjišťovat ze sledovaných zdrojů: e-Sbírky, EUR-Lexu, VeKLEPu, otevřených
   dat Poslanecké sněmovny a Senátu, Legislativní observatoře Evropského
   parlamentu, rejstříků Evropské komise, Věstníku ÚNMZ a dalších; registr
   sledovaných zdrojů obsahuje 78 položek s uvedením způsobu a četnosti
   kontroly.
2. **Četnost.** Registry předpisů a návrhů týdně, normy a zprávy úřadů
   měsíčně, strategie, technická pravidla a měření úplnosti čtvrtletně.
3. **Fronta kandidátů a dva editoři.** Nic se do databáze nedostane
   automaticky. Každý nový dokument nalezený ve zdrojích je nejprve
   kandidátem; dokumentem se stane, až jej jeden editor navrhne k přijetí
   a druhý, jiný editor návrh potvrdí. Stejným způsobem se schvalují opravy
   údajů. Každé rozhodnutí se zaznamenává.
4. **Kontrola platnosti.** U předpisů ČR a EU ověřujeme v e-Sbírce
   a v databázi Úřadu pro publikace EU, zda jsou účinné, dosud neúčinné, nebo
   zrušené; zrušený předpis zůstává v databázi s vazbou na předpis, jenž jej
   zrušil. Poslední kontrola 27. 10. 2026 ověřila 747 předpisů ČR a EU
   (předpisy v databázi i kandidáty na doplnění); databáze nyní vede 35
   dokumentů jako zrušené.
5. **Datum poslední kontroly.** U každého dokumentu bude zobrazeno, kdy byl
   naposledy ověřen a v jakém zdroji (etapa 3) [DOPLNIT po kroku 3]. Dnes
   aplikace v zápatí uvádí jen datum poslední změny databáze jako celku.

Otevřeně upozorňujeme, že kontroly zatím spouštíme ručně: pravidelné
automatické spouštění na serveru není dosud zavedeno a o jeho zavedení
a provozovateli bude třeba rozhodnout (odstavec 7). Ve stávajícím stavu
by aktuálnost závisela na tom, zda kontrolu někdo spustí.

### 4.4 Připravované předpisy

Připravované předpisy budeme zachycovat z těchto zdrojů:

| Zdroj | Co přináší | Stav |
|---|---|---|
| VeKLEP (Vládní legislativní pracovní plocha) | návrhy zákonů a podzákonných předpisů ve fázi připomínkového řízení | vyvinuto; čte kanál novinek, jenž pokrývá zhruba dva týdny, proto je nutný týdenní běh |
| Poslanecká sněmovna (otevřená data) | vládní a poslanecké návrhy zákonů, stav projednávání, předpisy, jež návrh mění | vyvinuto |
| Senát (sněmovní otevřená data) | senátní tisky navázané na sněmovní tisky | vyvinuto |
| Legislativní observatoř Evropského parlamentu | legislativní postupy EU týkající se vodíku | vyvinuto |
| Rejstříky Evropské komise (akty v přenesené pravomoci, komitologie, dokumenty Komise) | návrhy aktů v přenesené pravomoci a prováděcích aktů, návrhy Komise (COM) | vyvinuto |
| CEN, ISO, IEC a Věstník ÚNMZ | návrhy norem (prEN, DIS) | vyvinuto; v databázi je již 151 návrhů norem |
| e-Legislativa (nástupce VeKLEPu) | návrhy v novém systému | vyžaduje registraci u Ministerstva vnitra; dosud neprovedena |

Návrh předpisu, jenž se databáze týká (mění předpis, jejž databáze obsahuje,
nebo se týká vodíku či věcných okruhů databáze), se stane kandidátem ve
frontě. Po přijetí editory vznikne dokument ve stavu „připravovaný“, propojený
s předpisy, jež mění. Po vyhlášení bude převeden na vyhlášený předpis.
Zkušební běh 4. 11. 2026 našel 44 návrhů: 28 českých a 9 evropských, jež
mění dokumenty databáze nebo se týkají vodíku, a 7 dalších českých
z věcných okruhů databáze. Mezi evropskými byly například revize směrnic
(EU) 2018/2001, (EU) 2019/944 a (EU) 2024/1788.

Tato část zatím běžela jen nad testovací kopií databáze; do veřejné verze
ji uvedeme v etapě 3 [DOPLNIT po kroku 3: datum prvního běhu a počet
přijatých návrhů]. Převod přijatého návrhu na vyhlášený předpis zatím
není dokončen. Slovenský legislativní proces (Slov-Lex) automaticky
sledovat nemůžeme, protože web automatizovaný přístup odmítá.

## 5. Další nedostatky, jež jsme nalezli sami

Při rozboru připomínek jsme v databázi nalezli další nedostatky, jež MPO
patrně také uvidí. Uvádíme je kvůli úplnosti:

1. **Slovenské předpisy s českými institucemi** — Opraveno, viz odstavec 3.5.
2. **Interní poznámky ve veřejných popisech** — Opraveno, viz odstavec 3.6.
3. **Chybné názvy záznamů** — Dva záznamy nesly místo názvu předpisu název
   webu „Slov-Lex“; opraveno.
4. **Dokumenty bez popisu** — Ke kontrole editorem je označeno 558 dokumentů,
   z toho 540 nemá popis (406 z nich jsou normy, u nichž popis nelze převzít
   z chráněného textu).
5. **Dosud neopravené záznamy** — Záznam s označením (EU) 2014/1302 nese
   název prováděcího nařízení (EU) 2019/776 a působí jako duplicita; předpis
   EHK OSN č. 134 je v databázi dvakrát; záznam s označením 98/2004 Z. z. je
   ve skutečnosti novelou zákona č. 492/2010 Z. z. Opravíme je v etapě 1.
6. **Slovenská znění aktů EU** — Slovenská znění čtyř aktů EU (mimo jiné
   Vodíkové strategie EU a směrnice (EU) 2024/1788) byla v katalogu
   samostatnými řádky bez vazby na české znění; nyní jsou s českým zněním
   propojena a zobrazují se jako jeho jazyková verze, stejně jako znění
   anglická.
7. **Další chybné záznamy** — Česká varianta směrnice 2012/18/EU
   (Seveso III) nesla název a adresu směrnice 2014/34/EU (ATEX); norma
   ČSN ISO 19880-1 byla vedena pod neexistujícím označením
   ČSN EN ISO 19880-1; předpis EHK OSN č. 100 (elektrické hnací ústrojí
   vozidel) nesl název publikace EIGA o vodíkových lahvích a byl s ní
   sloučen a týž název dostalo i pravidlo DVGW G 100. Opraveno; publikace
   EIGA je opět samostatným dokumentem.
8. **Slovenské normy a předpisy** — Databáze obsahuje 444 slovenských
   dokumentů, převážně normy STN, jež mohou českého uživatele mást. Zda je
   ve výchozím zobrazení skrýt, navrhujeme rozhodnout na jednání
   (odstavec 7).

## 6. Harmonogram

| Etapa | Obsah | Předpokládaný termín |
|---|---|---|
| 0 | Opravy údajů v databázi (odstavce 3.1 až 3.6 a 5) | provedeno 19. 11. 2026 |
| 1 | Doplnění předpisů z tabulek MPO a CDV, strategií podle přílohy A a chybějících institucí; referenční soubor a jeho automatická kontrola | [DOPLNIT termín] (odhadem 1 až 2 týdny) |
| 2 | Úpravy rozhraní: jeden řádek na předpis, filtr institucí podle jurisdikce, podtyp aktů v přenesené pravomoci, vyhledávání podle synonym | [DOPLNIT termín] |
| 3 | Průběžná aktualizace: uvedení sběru zdrojů a návrhů předpisů do provozu, datum poslední kontroly u dokumentu, rozhraní pro připravované předpisy | [DOPLNIT termín] |
| 4 | Testy všech scénářů z připomínek, interní akceptace, opětovné předání výsledku V01 | [DOPLNIT termín] |

Etapy 1 až 3 probíhají souběžně; jejich výsledky doplníme do tohoto
dokumentu před jeho odesláním [DOPLNIT po krocích 1 až 3].

## 7. Otevřené otázky k jednání

1. **Slovenské dokumenty:** Ponechat slovenské předpisy a normy STN ve
   veřejném katalogu, nebo je ve výchozím zobrazení skrýt či oddělit?
2. **Kategorie „Strategie“:** Souhlasí MPO s názvem kategorie a s jejím
   rozsahem (odstavec 4.2)? Máme doplnit i strategie s prioritou C
   z přílohy A?
3. **Referenční soubor:** Můžeme tabulky MPO a CDV převzít jako referenční
   soubor dokumentů pro měření úplnosti a požádat kolegyně z MPO a CDV
   o jejich průběžné doplňování?
4. **Editoři:** Kdo bude posuzovat frontu kandidátů? Navrhujeme, aby
   alespoň jeden z editorů byl z okruhu aplikačního garanta.
5. **Provoz:** Kdo bude provozovat pravidelné spouštění kontrol na serveru
   a kde bude databáze provozována po skončení projektu?
6. **Normy podle komisí:** Vyhovuje MPO přehled norem podle technických
   komisí (odstavec 4.1) místo položek s označením komisí?
7. **Schválení výsledku:** Jaký postup a jaké podklady MPO pro opětovné
   posouzení a schválení výsledku V01 očekává?

## Příloha A: Strategické dokumenty z rešerše

Rešerši jsme provedli 19. 11. 2026. Dokumenty s prioritou A a B jsme do
databáze doplnili (odstavec 4.2), dokumenty s prioritou C předkládáme
k posouzení. U každého dokumentu jsme ověřili, že
oficiální adresa existuje (české dokumenty přímo na stránkách vydavatele,
dokumenty EU v databázi Úřadu pro publikace EU, jež je oficiálním úložištěm
dokumentů EUR-Lexu), a dotazem nad databází, že dokument v ní ani ve frontě
kandidátů není. Priorita A znamená přímý vztah k vodíku nebo nadřazený
rámec vodíkových předpisů, B rámcový dokument s menším podílem vodíku, C
okrajovou vazbu k posouzení editorem.

### A.1 Národní strategie

| Dokument | Vydavatel | Datum | Vztah k vodíku | Priorita |
|---|---|---|---|---|
| Vnitrostátní plán České republiky v oblasti energetiky a klimatu (aktualizace prosinec 2024) | MPO, schválila vláda ČR | 18. 12. 2024 | Národní příspěvek k cílům EU do roku 2030 včetně podílu RFNBO v průmyslu (42 % v roce 2030, 60 % v roce 2035) a opatření k výrobě a využití vodíku. | A |
| 2. aktualizace Národního akčního plánu čisté mobility (usnesení vlády č. 590/2024) | MPO ve spolupráci s MD a MŽP | 28. 8. 2024 | Cíle pro roky 2025, 2030 a 2035 včetně vodíkové mobility a plnicích stanic; vychází z nařízení AFIR. Nahrazuje verzi 2019, jež je v databázi. | A |
| Státní energetická koncepce České republiky | MPO, schválila vláda ČR | 18. 5. 2015 | Rámec energetické politiky státu; vodík okrajově. Aktualizace byla připravena, vláda však v červenci 2024 její schválení odložila. | B |
| Politika ochrany klimatu v České republice (usnesení vlády č. 207/2017) | MŽP, schválila vláda ČR | 22. 3. 2017 | Strategie snižování emisí do roku 2030 s výhledem do roku 2050; vodík mezi opatřeními v dopravě a průmyslu. Aktualizace na období 2025–2050 je zveřejněna jako návrh; její schválení jsme nedohledali. | B |

Oficiální adresy:

* Vnitrostátní plán: <https://mpo.gov.cz/cz/energetika/strategicke-a-koncepcni-dokumenty/vnitrostatni-plan-ceske-republiky-v-oblasti-energetiky-a-klimatu--285293/>
* 2. aktualizace NAP CM: <https://mpo.gov.cz/cz/prumysl/zpracovatelsky-prumysl/automobilovy-prumysl/2--aktualizace-narodniho-akcniho-planu-ciste-mobility--283771/>
* Státní energetická koncepce: <https://mpo.gov.cz/cz/energetika/statni-energeticka-politika/statni-energeticka-koncepce--223620/>
* Politika ochrany klimatu: <https://www.mzp.gov.cz/cz/kontakty-pro-media/publikace/politika-ochrany-klimatu-v-cr>

### A.2 Strategie Evropské unie

Všechny dokumenty jsou sdělení Evropské komise; adresa má tvar
`https://eur-lex.europa.eu/legal-content/CS/TXT/?uri=CELEX:<číslo CELEX>`.

| Dokument | Označení (CELEX) | Datum | Vztah k vodíku | Priorita |
|---|---|---|---|---|
| Plán REPowerEU | COM(2022) 230 (52022DC0230) | 18. 5. 2022 | Cíl 10 mil. t domácí výroby a 10 mil. t dovozu obnovitelného vodíku do roku 2030. | A |
| „Fit for 55“: plnění klimatického cíle EU pro rok 2030 na cestě ke klimatické neutralitě | COM(2021) 550 (52021DC0550) | 14. 7. 2021 | Zastřešující sdělení k balíčku, z něhož vzešly revize směrnice o obnovitelných zdrojích, AFIR a balíček o trzích s vodíkem a plynem. | A |
| Cesta ke klimaticky neutrálnímu hospodářství: Strategie EU pro integraci energetického systému | COM(2020) 299 (52020DC0299) | 8. 7. 2020 | Vydána souběžně s Vodíkovou strategií EU; úloha vodíku v propojeném energetickém systému. | A |
| Sdělení o Evropské vodíkové bance | COM(2023) 156 (52023DC0156) | 16. 3. 2023 | Nástroj podpory výroby a dovozu obnovitelného vodíku. | A |
| Sdělení o Dohodě o čistém průmyslu: společný plán konkurenceschopnosti a dekarbonizace | COM(2025) 85 (52025DC0085) | 26. 2. 2025 | Mechanismus pro vodík, akt o nízkouhlíkovém vodíku, dekarbonizace průmyslu. | A |
| AccelerateEU – energetická unie: Cenově dostupná a bezpečná energie prostřednictvím urychlených opatření | COM(2026) 370 (52026DC0370) | 22. 4. 2026 | Ohlašuje cílený přezkum kritérií výroby obnovitelného vodíku (RFNBO), tedy možnou změnu nařízení (EU) 2023/1184 a 2023/1185. | A |
| Zelená dohoda pro Evropu | COM(2019) 640 (52019DC0640) | 11. 12. 2019 | Rámcová strategie, z níž vychází Vodíková strategie EU i balíček „Fit for 55“. | B |
| Strategie pro udržitelnou a inteligentní mobilitu | COM(2020) 789 (52020DC0789) | 9. 12. 2020 | Cíle pro bezemisní vozidla a infrastrukturu plnicích stanic; východisko nařízení AFIR. | B |
| Průmyslový plán Zelené dohody pro věk s nulovými čistými emisemi | COM(2023) 62 (52023DC0062) | 1. 2. 2023 | Ohlašuje Evropskou vodíkovou banku a akt o průmyslu pro nulové čisté emise. | B |
| Sdělení o revizi strategického plánu pro energetické technologie (SET) | COM(2023) 634 (52023DC0634) | 20. 10. 2023 | Výzkumné priority EU včetně vodíkových technologií. | C |
| Klimatický cíl pro Evropu na rok 2040 a cesta ke klimatické neutralitě do roku 2050 | COM(2024) 63 (52024DC0063) | 6. 2. 2024 | Dlouhodobý rámec; vodík v průmyslu a jako sezonní akumulace. | C |
| Akční plán pro cenově dostupnou energii | COM(2025) 79 (52025DC0079) | 26. 2. 2025 | Vodíkové sítě a sektorové smlouvy včetně vodíku. | C |
| Průmyslový akční plán pro evropský automobilový průmysl | COM(2025) 95 (52025DC0095) | 5. 3. 2025 | Vodíková vozidla jen okrajově. | C |
| Balíček opatření pro evropské elektrizační soustavy | COM(2025) 1005 (52025DC1005) | 10. 12. 2025 | Investiční potřeba vodíkových sítí, vodíkové koridory mezi prioritními projekty. | C |

K Plánu REPowerEU patří též pracovní dokument útvarů Komise SWD(2022) 230
s vodíkovým urychlovačem; jeho české znění není k dispozici.

Úplné údaje včetně adres a způsobu ověření jsou ve strojově čitelném
seznamu, jejž předáme spolu s tímto dokumentem na vyžádání.
