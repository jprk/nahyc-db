# Vypořádání připomínek Ministerstva průmyslu a obchodu k výsledku V01

> Historie dokumentu:  
> 2026-11-19 jprk Návrh první verze jako podklad k jednání s MPO  
> 2026-11-19 jprk Doplněn stav etap 1 až 3, harmonogram s termíny, nabídka editorského přístupu pro MPO

Dokument shrnuje vypořádání připomínek, jež Ing. Petr Mervart, aplikační
garant dílčího projektu DP004 za Ministerstvo průmyslu a obchodu, vznesl
k výsledku V01 „Databáze regulačních předpisů a předrealizačních procesů“.
Ke každé připomínce uvádíme její znění, příčinu nedostatku, opatření, jež
jsme již provedli, a opatření, jež ještě provedeme, včetně předpokládaného
termínu. V odstavci 4 odpovídáme na otázky, jež MPO položilo nebo jež
z připomínek vyplývají, a nabízíme pracovníkům MPO editorský přístup
k databázi, v odstavci 5 uvádíme další nedostatky, jež jsme
při rozboru nalezli sami, a v odstavci 6 harmonogram dalšího postupu.
Dokument končí otevřenými otázkami k jednání (odstavec 7) a přílohou A se
seznamem strategických dokumentů z rešerše, z nichž jsme dokumenty
s prioritou A a B do databáze doplnili.

Stav databáze a webové aplikace uvádíme k 19. 11. 2026. Čísla o obsahu
databáze jsme ověřili dotazem nad provozní databází v tento den. Rozlišujeme
přitom dva stavy: opravy údajů z etapy 0 jsou v provozní databázi zčásti
zapsány; zbylé opravy etapy 0 a úpravy z etap 1 až 3 jsou dokončeny
a ověřeny automatickými testy nad kopií provozní databáze, do veřejné verze
aplikace je však teprve nasadíme (podle harmonogramu v odstavci 6 do
25. 11. 2026). U těchto úprav uvádíme výsledky zkoušek nad kopií databáze
a označujeme je slovem „připraveno“.

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

Na e-mail ze 17. 4. 2026 jsme reagovali se zpožděním až 20. 5. 2026
a telekonferenci, již MPO navrhlo na začátek června 2026, jsme
neuskutečnili, protože jsme k ní neměli připraveno vypořádání připomínek.
Vypořádání tak předkládáme se zpožděním několika měsíců, za něž se
omlouváme. Jednání s MPO navrhujeme jako první krok po odeslání tohoto
dokumentu, v prvním prosincovém týdnu (odstavec 6).

Připomínky považujeme za oprávněné. Jejich společnou příčinou patrně je, že
databáze vznikla sloučením tří samostatných rešerší, jež se lišily rozsahem,
způsobem zápisu označení i přiřazením odpovědných institucí, a že jsme
výsledek předali bez soustavné kontroly obsahu z pohledu uživatele a bez
nezávislého měření úplnosti. Obojí nyní napravujeme (odstavec 6).

## 2. Přehled stavu připomínek

| # | Připomínka (zkráceně) | Stav k 19. 11. 2026 | Zbývá |
|---|---|---|---|
| 1 | Dokument se ve výsledcích zobrazí dvakrát česky a dvakrát anglicky. | Duplicity odstraněny; dotčený dokument (rozhodnutí ECB) z databáze vyřazen jako nesouvisející. Zobrazení jazykových verzí v jednom řádku připraveno. | Nasadit (etapa 2, do 25. 11. 2026); vysvětlit uživatelům, u kterých dokumentů vedeme anglickou verzi. |
| 2 | Dotaz „RFNBO“ vrací čtyřikrát týž dokument. | Duplicity odstraněny; dotaz vrací jeden dokument. Vyhledávání podle zkratek a synonym připraveno; dotaz pak vrací čtyři předpisy, každý jednou. | Nasadit (etapa 2, do 25. 11. 2026). |
| 3 | V databázi chybějí akty v přenesené pravomoci. | Pět aktů v databázi je; nařízení (EU) 2023/1185 má nově český název. Podtyp aktů připraven; chybějící (EU) 2025/2359 připraveno k přijetí. | Nasadit podtyp (etapa 2); přijmout chybějící akty (etapa 1, do 11. 12. 2026). |
| 4 | Současně „MD“ i „Ministerstvo dopravy“. | Vyřešeno; zkratky nahrazeny plnými názvy. | — |
| 5 | MPO je uvedeno jako odpovědné za zákon o dráhách. | Vyřešeno; opraveny i další chybně přiřazené instituce. Filtr institucí podle jurisdikce připraven. | Nasadit (etapa 2, do 25. 11. 2026). |
| 6 | U energetického zákona se zobrazuje zastaralá hláška. | Vyřešeno; hláška i interní poznámky z vývoje odstraněny z veřejných popisů. | Doplnit popisy dokumentům, jež po odstranění poznámek popis nemají (průběžně). |
| 7 | Databáze neobsahuje připravované předpisy. | Sběr návrhů předpisů a převod návrhu na vyhlášený předpis připraveny; zkouška nanečisto nad provozní databází proběhla. | První běh nad provozní databází (etapa 3, do 25. 11. 2026); posouzení nálezů editory. |
| 8 | Chybějí i existující předpisy (tabulky MPO a CDV). | Rozbor proveden: z 42 českých předpisů tabulky MPO je v databázi 12. Pro chybějící předpisy připraveno 34 kandidátů s úředními údaji; automatický test pokrytí obou tabulek zaveden. | Posouzení a přijetí kandidátů editory (etapa 1, do 11. 12. 2026). |
| 9 | Nová kategorie „Strategie“. | Kategorie „Strategie“ zavedena (přejmenováním dosavadního typu), doplněno 13 strategií podle přílohy A, celkem 25 dokumentů. | Posoudit strategie s prioritou C; pravidelně kontrolovat aktuálnost strategií (etapa 3). |
| 10 | Jak bude zajištěna aktuálnost předpisů. | Kontrola platnosti a stavy dokumentů zavedeny; datum poslední kontroly u dokumentu připraveno; postup popsán v provozním dokumentu. | Nasadit (etapa 3); zavést pravidelné automatické spouštění kontrol. |

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

**Připraveno k nasazení:** Ve výsledcích vyhledávání je každý předpis
zobrazen jedním řádkem s českým názvem a jeho dostupné jazykové verze jsou
uvedeny jako štítky CS a EN, jež vedou na stránky jednotlivých verzí. Dotaz
i filtry se vyhodnocují nad všemi verzemi, takže řádek se najde i tehdy,
odpovídá-li dotazu jen anglický název. Počet nalezených dokumentů i údaj
o velikosti databáze na úvodní stránce počítají předpisy, nikoli jazykové
verze. Úpravu nasadíme do veřejné verze aplikace do 25. 11. 2026 (etapa 2).

**Co ještě uděláme:** Na stránce aplikace vysvětlíme, u kterých dokumentů
a proč vedeme i anglickou verzi (etapa 2, do 11. 12. 2026).

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

**Připraveno k nasazení:** Vyhledávání nově prochází i označení dokumentu
a využívá slovník zkratek a ustálených názvů (RFNBO, AFIR, AFID, RED II,
RED III, LEX OZE, TEN-E, ReFuelEU, ATEX, PED a další), takže dotaz na zkratku
najde i dokumenty, jež ji v názvu nemají. Zkratka se hledá jako celé slovo
(dotaz „RED II“ tedy nenajde RED III) a pod výsledky se zobrazí, která
synonyma byla použita. Dotaz „RFNBO“ při zkoušce nad kopií provozní databáze
vrátil čtyři předpisy, každý jednou: nařízení v přenesené pravomoci (EU)
2023/1184 a 2023/1185 a směrnice RED II a RED III. Jazykové verze jsou
zobrazeny podle odstavce 3.1. Úpravu nasadíme do 25. 11. 2026 (etapa 2).

**Co ještě uděláme:** Slovník budeme rozšiřovat podle dotazů uživatelů;
pojem „LEX vodík“ do něj zařadíme, jakmile bude příslušný návrh zákona
v databázi (odstavec 3.7).

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

**Připraveno k nasazení:** Akty EU nesou podtyp „akt v přenesené
pravomoci“ nebo „prováděcí akt“, určený podle adresy aktu v EUR-Lexu, jinak
podle jeho úředního názvu. V nabídce typů dokumentů přibude skupina „Podtyp
aktu EU“: filtr „Akt v přenesené pravomoci (EU)“ vrací všech pět výše
uvedených nařízení, filtr „Prováděcí akt (EU)“ 11 předpisů. Řádek takového
aktu ve výsledcích nese štítek podtypu. Nařízení v přenesené pravomoci (EU)
2025/2359 a nařízení (EU) 2024/1679 o transevropské dopravní síti jsou
připravena jako kandidáti k přijetí s úředním českým názvem a údajem
o platnosti (odstavec 3.8).

**Co ještě uděláme:** Podtyp nasadíme do 25. 11. 2026 (etapa 2), chybějící
akty přijmou editoři do 11. 12. 2026 (etapa 1). Nové akty v přenesené
pravomoci a prováděcí akty bude průběžně zachycovat týdenní sledování
rejstříků Evropské komise a databáze EUR-Lex (odstavec 4.3), jež uvedeme do
provozu v etapě 3.

### 3.4 Instituce „MD“ a „Ministerstvo dopravy“

**Znění:** „Proč je v systému současně ‚MD‘ a ‚Ministerstvo dopravy‘? Čím
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

**Připraveno k nasazení:** Filtr odpovědných institucí dnes míchá česká
ministerstva, orgány EU a normalizační orgány. Nově je rozdělen do skupin
Česká republika, Slovensko, Evropská unie, mezinárodní organizace,
normalizační a odborné organizace a zahraniční státní orgány a nabízí jen
instituce, k nimž databáze obsahuje alespoň jeden dokument. Přibyl filtr
jurisdikce (Česká republika, Evropská unie, mezinárodní, Slovensko, ostatní
státy). Úpravu nasadíme do 25. 11. 2026 (etapa 2).

**Co ještě uděláme:** Slovenské dokumenty budou ve výchozím zobrazení
skryty (odstavec 5, bod 6). Při posouzení kandidátů z tabulky MPO ověříme
odpovědnou instituci každého nově přijímaného předpisu; například nařízení
vlády č. 191/2022 Sb., jež provádí zákon č. 250/2021 Sb., povedeme
v souladu s ním pod Ministerstvem práce a sociálních věcí.

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

**Připraveno k nasazení:** Editorské rozhraní pro připravované dokumenty
umožňuje u návrhu zaznamenat, jak skončil: buď se návrh stal vyhlášeným
předpisem (dokument získá stav „vyhlášený“ nebo „účinný“ a případně nové
označení, název a datum účinnosti), nebo je vyhlášený předpis v databázi
veden jako jiný dokument, s nímž se návrh propojí vazbou „návrh vyhlášen
jako“. Stejně jako přijetí nového dokumentu navrhuje změnu jeden editor
a potvrzuje ji jiný. Zkouška sběru nanečisto nad provozní databází
19. 11. 2026, při níž se nic nezapsalo, odhadla 252 nových kandidátů ze
všech sledovaných zdrojů; z toho 112 má k databázi přímý vztah (mění
dokument databáze nebo se týká vodíku), mezi nimi 28 sněmovních tisků
a 9 legislativních postupů EU.

**Co ještě uděláme:** Sběr uvedeme do provozu nad provozní databází
prvním ostrým během do 25. 11. 2026 (etapa 3). Nálezy přímo související
s databází posoudí editoři do 18. 12. 2026, ostatní do 15. 1. 2027
(odstavec 6). Připravované dokumenty jsou na stránce dokumentu označeny
stavem „připravovaný“.

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
  havárií (226/2015 Sb. a předpis uvedený jako 277/2015 Sb.), zákony č. 249/2025 Sb.
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

Každý z 90 řádků obou tabulek jsme dále jednotlivě porovnali s databází:
51 řádků databáze obsahuje (tabulka MPO 21, tabulka CDV 30), 31 řádků
odpovídá předpisům, jež do databáze doplníme (tabulka MPO 29, tabulka CDV 2),
a 8 řádků tabulky CDV neoznačuje dokumenty (sedm technických komisí
a souhrnná položka „UNECE předpisy (WP.29)“, odstavec 4.1). Při dohledávání
úředních názvů jsme narazili na nesrovnalosti, jež je vhodné znát:

1. **Řádek „277/2015 Sb.“** — Název v tabulce odpovídá vyhlášce
   č. 227/2015 Sb. o náležitostech bezpečnostní dokumentace; pod číslem
   277/2015 Sb. je vyhlášen nesouvisející předpis. Kandidátem je vyhláška
   č. 227/2015 Sb.
2. **Řádek „191/2022 Sb.“** — Název v tabulce („o vyhrazených tlakových
   zařízeních“) odpovídá nařízení vlády č. 192/2022 Sb., jež databáze
   obsahuje; nařízení vlády č. 191/2022 Sb. o vyhrazených technických
   plynových zařízeních se vodíkových zařízení týká také, a doplníme je proto
   rovněž.
3. **Vyhláška č. 513/2021 Sb.** — Jen novelizovala vyhlášku o regulačním
   výkaznictví, jež byla k 1. 1. 2026 nahrazena vyhláškou č. 508/2025 Sb.;
   kandidáty jsou obě, do databáze patrně zařadíme platnou vyhlášku.
4. **Vyhláška č. 146/2024 Sb.** — Podle dostupných údajů bude k 1. 1. 2027
   zrušena předpisem č. 215/2026 Sb.; editoři posoudí oba předpisy.
5. **Norma ČSN ISO 19880-1** — Databáze ji vede pod nesprávným označením
   ČSN EN ISO 19880-1; označení opravíme.

**Připraveno k nasazení:** Pro chybějící předpisy obou tabulek jsme
připravili 34 kandidátů do fronty kandidátů: 28 českých předpisů, 2 akty EU,
normu ČSN EN ISO 11114-4 (část řady, jež se týká slučitelnosti materiálů
s vodíkem) a 3 kandidáty, kteří ve frontě již byli. U každého je úřední
název, adresa v autoritativním zdroji (e-Sbírka nebo Zákony pro lidi,
EUR-Lex, katalog České agentury pro standardizaci), údaj o platnosti
a navržená odpovědná instituce podle sloupce „Nositel“ tabulky MPO,
mezi nimi Energetický regulační úřad (6 kandidátů) a Český báňský úřad
(6 kandidátů). Obě tabulky jsme převzali jako referenční soubor: automatický
test, jenž se spouští před každou změnou aplikace, ověřuje, že každý řádek
obou tabulek je dokumentem databáze, kandidátem ve frontě, nebo má uveden
důvod, proč dokumentem není, a že žádný dokument z tabulek z databáze
nezmizel.

**Co ještě uděláme:** Kandidáty zapíšeme do fronty kandidátů provozní
databáze do 25. 11. 2026; posoudí a přijmou je dva editoři do 11. 12. 2026
(etapa 1, odstavec 4.3). Současně doplníme další části řad norem
ČSN EN 60079 a ČSN EN 13445, jež databáze dosud vede jen v jiném národním
převzetí (u řady ČSN EN 60079 přednostně části 10-1, 14 a 17), a novely
zákonů z balíčků LEX OZE. Úplnost budeme dále měřit postupy popsanými
v provozním dokumentu (odstavec 4.3).

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

**Co jsme udělali:** Scénáře připomínek 1 až 6 jsme převedli do
automatických testů v prohlížeči, jež se spouštějí před každou změnou
aplikace nad kopií provozní databáze, ověřují, že se nedostatek neopakuje,
a pořizují snímky obrazovky. Testy ověřují mimo jiné, že dotaz „RFNBO“
vrací každý předpis jednou, že akty v přenesené pravomoci lze vybrat
filtrem, že nabídka institucí neobsahuje holé zkratky, že zákony o dráhách
mají jako odpovědnou instituci Ministerstvo dopravy, že žádná stránka
neobsahuje zastaralou hlášku ani interní poznámky a že stránky lze
používat na telefonu.

**Co ještě uděláme:** Testy doplníme o scénáře připomínek 7 až 10
(připravované předpisy, předpisy z tabulek MPO a CDV, kategorie
„Strategie“, datum poslední kontroly). Před opětovným předáním necháme
aplikaci projít osobou mimo vývojový tým (interní akceptace) a výsledky
akceptace předáme MPO spolu s výsledkem (etapa 4, odstavec 6).

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
jeden dokument“. Úprava není součástí etap 1 až 4; zařadíme ji, bude-li
o ni MPO stát (odstavec 7).

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
5. **Datum poslední kontroly.** Dnes aplikace v zápatí uvádí jen datum
   poslední změny databáze jako celku. Připraveno k nasazení je zobrazení
   údaje „Poslední kontrola stavu“ na stránce každého dokumentu, s datem
   a zdrojem kontroly (například „27. 10. 2026 (e-Sbírka)“), u dokumentu
   dosud neověřeného s textem „dosud neověřeno“. Po nasazení (etapa 3,
   do 25. 11. 2026) bude datum kontroly uvedeno patrně u 226 dokumentů
   (předpisy ověřené kontrolou platnosti a normy ověřené v katalozích
   norem); s každým dalším během kontrol se bude rozšiřovat.

Otevřeně upozorňujeme, že kontroly zatím spouštíme ručně. Pravidelné
automatické spouštění na serveru máme připraveno, zavedeno však dosud není;
do jeho zavedení odpovídá za dodržení četnosti kontrol správce databáze,
jenž je spouští ručně. Ve stávajícím stavu tedy aktuálnost závisí na tom,
zda kontrolu někdo spustí.

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

Tato část zatím běžela jen nad testovací kopií databáze a 19. 11. 2026
nanečisto nad provozní databází (odstavec 3.7). Do provozu ji uvedeme
prvním ostrým během do 25. 11. 2026 (etapa 3); návrhy přímo související
s databází posoudí editoři do 18. 12. 2026. Převod přijatého návrhu na
vyhlášený předpis je připraven v editorském rozhraní (odstavec 3.7).
Slovenský legislativní proces (Slov-Lex) automaticky sledovat nemůžeme,
protože web automatizovaný přístup odmítá.

### 4.5 Editorský přístup pro pracovníky MPO

Nabízíme, aby pracovníci MPO, například kolegyně, jež zpracovaly tabulky
předpisů, získali k databázi editorský přístup. Editor se přihlašuje
v editorské části webové aplikace; žádnou instalaci nepotřebuje. Může:

* posuzovat kandidáty na nové dokumenty a navrhovat jejich přijetí,
  zamítnutí nebo odložení;
* sám navrhnout nový dokument, například předpis, jejž v databázi postrádá;
* navrhovat opravy údajů existujících dokumentů (název, popis, odpovědná
  instituce, typ, jazyk);
* zaznamenat, že připravovaný předpis byl vyhlášen.

Každá změna se schvaluje dvoustupňově: jeden editor ji navrhne a druhý,
odlišný editor ji potvrdí; databáze tuto podmínku sama vynucuje. Návrh
editora MPO tak potvrdí editor řešitele a naopak, nebo dva editoři MPO
navzájem. Každé rozhodnutí se zaznamenává (kdo, kdy a co navrhl, potvrdil,
zamítl nebo odložil). MPO by tak mohlo doplňovat a opravovat obsah databáze
přímo, bez prostředníka, a průběžně by vidělo, co a proč se v databázi
mění.

Účet založíme na vyžádání; potřebujeme jméno a e-mailovou adresu
pracovníka. K účtu připojíme krátký návod a nabízíme úvodní seznámení
s editorskou částí aplikace, například v rámci jednání podle odstavce 6.

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
5. **Další chybné záznamy** — Záznam s označením (EU) 2014/1302 nesl název
   prováděcího nařízení (EU) 2019/776 a působil jako duplicita; předpis
   EHK OSN č. 134 byl v databázi dvakrát; záznam s označením 98/2004 Z. z.
   byl ve skutečnosti novelou č. 492/2010 Z. z.; slovenské znění směrnice
   (EU) 2024/1788 nemělo úřední název. Opravy jsou připraveny a do provozní
   databáze je zapíšeme do 25. 11. 2026.
6. **Slovenská znění aktů EU** — Slovenská znění čtyř aktů EU (mimo jiné
   Vodíkové strategie EU a směrnice (EU) 2024/1788) byla v katalogu
   samostatnými řádky bez vazby na české znění; s českým zněním je
   propojíme (do 25. 11. 2026) a zobrazují se jako jeho jazyková verze, stejně jako znění
   anglická.
7. **Další chybné záznamy** — Česká varianta směrnice 2012/18/EU
   (Seveso III) nesla název a adresu směrnice 2014/34/EU (ATEX); norma
   ČSN ISO 19880-1 byla vedena pod neexistujícím označením
   ČSN EN ISO 19880-1; předpis EHK OSN č. 100 (elektrické hnací ústrojí
   vozidel) nesl název publikace EIGA o vodíkových lahvích a byl s ní
   sloučen a týž název dostalo i pravidlo DVGW G 100. Opravy jsou připraveny
   a do provozní databáze je zapíšeme do 25. 11. 2026; publikace
   EIGA pak bude opět samostatným dokumentem.
8. **Slovenské normy a předpisy** — Databáze obsahuje 444 slovenských
   dokumentů, převážně normy STN, jež mohou českého uživatele mást.
   Rozhodli jsme, že ve výchozím zobrazení veřejného katalogu budou skryty;
   zobrazit je bude moci přihlášený editor přepínačem jurisdikce. Úpravu
   nasadíme do 25. 11. 2026. Bude-li MPO považovat za vhodné slovenské
   dokumenty veřejnosti nabízet, lze výchozí zobrazení změnit.

## 6. Harmonogram

Většina úprav je k 19. 11. 2026 dokončena a ověřena automatickými testy
nad kopií provozní databáze; zbývá je nasadit do veřejné verze, zapsat
připravené kandidáty a nechat je posoudit editory. Harmonogram jsme proto
sestavili co nejkratší. U každého termínu uvádíme podmínku, na níž jeho
dodržení závisí.

| Termín | Krok | Obsah | Podmínka |
|---|---|---|---|
| 19. 11. 2026 (provedeno) | Etapa 0, první část | Opravy údajů v provozní databázi: odpovědné instituce, zastaralá hláška, interní poznámky, chybné názvy, vyřazení rozhodnutí ECB (odstavce 3.1 až 3.6). | — |
| do 25. 11. 2026 | Nasazení etap 0 až 3 | Zbylé opravy etapy 0 (odstavec 5, bod 5); úpravy rozhraní etapy 2 (jeden řádek na předpis, filtr institucí a jurisdikce, skrytí slovenských dokumentů, podtyp aktů EU, vyhledávání podle synonym); zápis 34 kandidátů z tabulek MPO a CDV do fronty kandidátů; etapa 3 (první ostrý běh sběru zdrojů a návrhů předpisů, datum poslední kontroly u dokumentu, rozhraní pro připravované předpisy). | Úspěšné automatické testy sloučené verze nad kopií provozní databáze; záloha provozní databáze před zápisem; dva funkční editorské účty. |
| do 27. 11. 2026 | Odeslání vypořádání | Tento dokument a provozní dokument „Provoz a udržování aktuálnosti databáze“ odešleme MPO. | Nasazení podle předchozího řádku, aby veřejná verze aplikace odpovídala popsanému stavu; doplnění jmen garanta a editorů v provozním dokumentu. |
| 1. až 4. 12. 2026 | Jednání s MPO | Projednání vypořádání a otevřených otázek (odstavec 7); dohoda o postupu opětovného schválení výsledku V01; případné založení editorských účtů pro pracovníky MPO a úvodní seznámení s editorskou částí. Navrhujeme úterý 1. 12., středu 2. 12. nebo čtvrtek 3. 12. 2026, online nebo osobně. | Časové možnosti MPO; dohodne-li se pozdější termín, posouvá se o stejnou dobu i termín opětovného předání. |
| do 11. 12. 2026 | Etapa 1 | Posouzení a přijetí kandidátů z tabulek MPO a CDV dvěma editory; přejmenování typu na „Strategie“ a zařazení 11 strategií s prioritou A a B; další části řad norem ČSN EN 60079 a ČSN EN 13445; novely LEX OZE; oprava dvou chybných záznamů (odstavec 5, bod 5); vysvětlení jazykových verzí na stránce aplikace. | Dva editoři s dostatečnou časovou kapacitou (34 kandidátů z tabulek, 11 strategií, části norem a novely LEX OZE). |
| do 18. 12. 2026 | Etapa 4 | Posouzení nálezů prvního sběru, jež přímo souvisejí s databází (odhadem 112); testy scénářů připomínek 7 až 10; interní akceptace osobou mimo vývojový tým; zapracování závěrů jednání s MPO. | Dostupnost osoby pro interní akceptaci v týdnu 14. až 18. 12. 2026; závěry jednání nevyžadují rozsáhlé úpravy. |
| 22. 12. 2026 | Opětovné předání | Předání výsledku V01 MPO k posouzení postupem dohodnutým na jednání, s výsledky interní akceptace. | Interní akceptace bez závažných nálezů; dohoda o postupu schválení. |
| do 15. 1. 2027 | Provoz | Posouzení ostatních nálezů prvního sběru (odhadem 140); dále průběžně podle provozního dokumentu. | Opětovné předání na tomto kroku nezávisí. |

## 7. Otevřené otázky k jednání

1. **Postup schválení výsledku V01:** Po odeslání tohoto vypořádání
   bychom MPO rádi požádali o dohodu na postupu opětovného posouzení
   a schválení výsledku V01: jaké podklady MPO očekává, kdo se posouzení
   zúčastní a jakou formou bude vystaveno potvrzení o schválení výsledku
   pro Technologickou agenturu ČR.
2. **Editorské účty pro MPO:** Má MPO zájem o editorský přístup pro své
   pracovníky (odstavec 4.5), a pokud ano, pro koho?
3. **Referenční soubor:** Můžeme tabulky MPO a CDV převzít jako referenční
   soubor dokumentů pro měření úplnosti a požádat kolegyně z MPO a CDV
   o jejich průběžné doplňování?
4. **Lhůty posouzení kandidátů:** Navrhujeme, aby editoři kandidáty
   z týdně kontrolovaných zdrojů posoudili do dvou týdnů od zachycení
   a ostatní do konce kalendářního čtvrtletí. Vyhovují tyto lhůty MPO?
5. **Kategorie „Strategie“ a priorita C:** Souhlasí MPO s názvem
   kategorie a jejím rozsahem (odstavec 4.2)? Má databáze zahrnout
   i strategické dokumenty s okrajovou vazbou na vodík (příloha A,
   priorita C)?
6. **Normy podle komisí:** Vyhovuje MPO přehled norem podle technických
   komisí (odstavec 4.1) místo položek s označením komisí? Má být komise
   uvedena na stránce normy a sloužit jako filtr?

## Příloha A: Strategické dokumenty z rešerše

Rešerši jsme provedli 19. 11. 2026. Dokumenty s prioritou A a B jsme do
databáze doplnili (odstavec 4.2), dokumenty s prioritou C předkládáme
k posouzení. U každého dokumentu jsme ověřili, že
oficiální adresa existuje (české dokumenty přímo na stránkách vydavatele,
dokumenty EU v databázi Úřadu pro publikace EU, jež je oficiálním úložištěm
dokumentů EUR-Lexu), a dotazem nad databází, že dokument v ní ani ve frontě
kandidátů není. Priorita A znamená přímý vztah k vodíku nebo nadřazený
rámec vodíkových předpisů, B rámcový dokument s menším podílem vodíku, C
okrajovou vazbu k posouzení editorem.

### A.1 Národní strategie

| Dokument | Vydavatel | Datum | Vztah k vodíku | Priorita |
|---|---|---|---|---|
| Vnitrostátní plán České republiky v oblasti energetiky a klimatu (aktualizace prosinec 2024) | MPO, schválila vláda ČR | 18. 12. 2024 | Národní příspěvek k cílům EU do roku 2030 včetně podílu RFNBO v průmyslu (42 % v roce 2030, 60 % v roce 2035) a opatření k výrobě a využití vodíku. | A |
| 2. aktualizace Národního akčního plánu čisté mobility (usnesení vlády č. 590/2024) | MPO ve spolupráci s MD a MŽP | 28. 8. 2024 | Cíle pro roky 2025, 2030 a 2035 včetně vodíkové mobility a plnicích stanic; vychází z nařízení AFIR. Nahrazuje verzi 2019, jež je v databázi. | A |
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
| Plán REPowerEU | COM(2022) 230 (52022DC0230) | 18. 5. 2022 | Cíl 10 mil. t domácí výroby a 10 mil. t dovozu obnovitelného vodíku do roku 2030. | A |
| „Fit for 55“: plnění klimatického cíle EU pro rok 2030 na cestě ke klimatické neutralitě | COM(2021) 550 (52021DC0550) | 14. 7. 2021 | Zastřešující sdělení k balíčku, z něhož vzešly revize směrnice o obnovitelných zdrojích, AFIR a balíček o trzích s vodíkem a plynem. | A |
| Cesta ke klimaticky neutrálnímu hospodářství: Strategie EU pro integraci energetického systému | COM(2020) 299 (52020DC0299) | 8. 7. 2020 | Vydána souběžně s Vodíkovou strategií EU; úloha vodíku v propojeném energetickém systému. | A |
| Sdělení o Evropské vodíkové bance | COM(2023) 156 (52023DC0156) | 16. 3. 2023 | Nástroj podpory výroby a dovozu obnovitelného vodíku. | A |
| Sdělení o Dohodě o čistém průmyslu: společný plán konkurenceschopnosti a dekarbonizace | COM(2025) 85 (52025DC0085) | 26. 2. 2025 | Mechanismus pro vodík, akt o nízkouhlíkovém vodíku, dekarbonizace průmyslu. | A |
| AccelerateEU – energetická unie: Cenově dostupná a bezpečná energie prostřednictvím urychlených opatření | COM(2026) 370 (52026DC0370) | 22. 4. 2026 | Ohlašuje cílený přezkum kritérií výroby obnovitelného vodíku (RFNBO), tedy možnou změnu nařízení (EU) 2023/1184 a 2023/1185. | A |
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
