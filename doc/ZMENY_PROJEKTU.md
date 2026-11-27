# Záznam změn v projektu

Krátké záznamy o tom, co jsme v databázi a aplikaci změnili, v pořadí od nejnovějšího. Slouží jako podklad
pro zprávy MPO a TAČR. Každý záznam uvádí datum, co jsme udělali a kde je podrobný popis. Záznam
přidáváme po každém dokončeném kroku.

## 27.11.2026

- **Kandidáti z tabulek MPO a CDV vždy v pásmu 1.** Norma ČSN EN IEC 60079-29-0 z tabulky MPO se v seznamu
  kandidátů nezobrazovala: nález ve Věstníku ÚNMZ ji přesunul do pásma 2 („nepřímý vztah“), které seznam ve
  výchozím stavu skrývá. Kandidát, kterého tabulky MPO a CDV uvádějí, nyní zůstává v pásmu 1 bez ohledu na to,
  který zdroj ho najde později. V provozní databázi jsme pásmo opravili u dvou kandidátů (norma ČSN EN IEC 60079-29-0
  a zamítnutý zákon č. 586/1992 Sb.).
- **Formát data v dokumentech (PR #46).** Všechna data v dokumentaci projektu (`doc/`) jsme převedli na tvar `dd.mm.yyyy`
  bez mezer (478 výskytů ve 21 dokumentech, mezi nimi `MPO_VYPORADANI.md` a `PROVOZ.md`). Odeslané přílohy
  v `doc/mpo_odeslani/` jsme nechali beze změny. Data ve tvaru ISO (`2026-11-27`) zůstávají.
- **Směrnice 2010/75/EU má zase své označení (PR #45).** Oprava slovenského záznamu rešerše, který pod číslem
  směrnice uváděl rozhodnutí (EU) 2013/732, zasáhla i samotnou směrnici o průmyslových emisích. Ta tak
  zůstala bez označení, textu a popisu, a vazby národních předpisů, které ji provádějí, vedly na
  rozhodnutí. Opravu jsme omezili na záznam rešerše. Směrnice má označení, plný text, popis podle čl. 1
  a čtyři vazby IMPLEMENTS (`doc/ANOTACE_PREDPISU.md`, odstavec 3).
- **Vydání a platnost verzí právních předpisů (issue #38, PR #44, `doc/VERZE_PREDPISU.md`).** Tabulka verzí u zákonů,
  vyhlášek, nařízení vlády a aktů EU uvádí, které znění databáze má, od kdy je účinné, a odkazuje na ně
  v e-Sbírce nebo EUR-Lexu. Verze vedeme od vložení dokumentu do databáze. Nové znění, které e-Sbírka nebo
  Cellar zveřejní později, nástroj zapíše jako novou verzi a v den účinnosti stáhne jeho text. Nástroj
  pokrývá 226 předpisů. Šest zákonů (například energetický zákon č. 458/2000 Sb.) už má nové znění, účinné
  od 01.11.2026. První běh doplní prázdné pole „Platnost od“ u 164 předpisů. Plánovač nástroj spouští denně.
- **Jednotný formát data.** Web uvádí všechna data ve tvaru `dd.mm.yyyy` bez mezer (například „01.11.2026“):
  štítky verzí předpisů a konsolidovaných znění, „Platnost od“, poslední kontrolu stavu, čas aktualizace databáze
  a zdroj kandidátů „MPO/CDV 30.04.2026“. Stejný formát používáme v dokumentech projektu.
- **Popisy předpisů přidaných z fronty kandidátů (PR #43).** U 53 předpisů bez plného textu jsme texty stáhli,
  vyčistili a odvodili z nich popis: 47 má doslovné úvodní ustanovení, 6 zkontrolované přibližné shrnutí
  a čeká na editora (`doc/ANOTACE_PREDPISU.md`, odstavec 3). Nový krok nasazení `state_paths.py --seed`
  doplní do stavového adresáře stavové soubory, které přibyly v nové verzi (`doc/NASAZENI.md`, odstavec 5);
  `act_descriptions.json` tam dosud chyběl.
- **Poznámky z rešerší u předpisů vyřazeny (PR #41).** Krátké poznámky autorů rešerší („Transpozice provedena – …“) už jako
  popis předpisu nezobrazujeme; transpozici zaznamenávají vazby `IMPLEMENTS` (105 vazeb ke 77 aktům EU). Předpis
  bez úvodního ustanovení čeká na popis od editora (`doc/ANOTACE_PREDPISU.md`, odstavec 2).
- **Jeden původce pro Evropský parlament a Radu.** Přijímání kandidátů založilo vedle původce „Evropský
  parlament a Rada Evropské unie“ druhého s názvem „Evropský parlament a Rada“. Oba jsme v provozní databázi
  sloučili (19 dokumentů, 35 kandidátů, záznamy přijatých kandidátů); aplikace i automatický navrhovatel
  nově zkrácený název převádějí na úplný, takže duplikát znovu nevznikne.
- **Katalog po přijetí kandidátů z tabulek MPO.** Nabídka původců řadí nové instituce do správných skupin
  (Český báňský úřad a Energetický regulační úřad mezi české orgány, Evropský parlament a Rada mezi orgány
  EU). Filtr „Ke kontrole“ zařazuje dokumenty s důvodem „popis je třeba doplnit ručně“ pod volbu „Chybí
  popis“. Testy počítají s tím, že dotaz na energetický zákon vrací vedle zákona i jeho přijaté novely.
- **Seznam kandidátů si pamatuje filtr (#39).** Odkaz zpět z detailu kandidáta i přesměrování po návrhu,
  zamítnutí nebo odložení vedou na seznam se stejným filtrem a stránkou, jaké editor nastavil. Odkaz zpět
  má kratší tučnou šipku zarovnanou s textem, menší písmo a větší odstup od označení kandidáta; seznam
  souvisejících dokumentů má odstup od upozornění pod ním.
- **Úpravy rozhraní detailu kandidáta (#39).** Detail kandidáta je stejně široký jako hlavička stránky
  a popisky řádků v jeho tabulkách (například „Doporučení automatu“) se na počítači nelámou uprostřed slova.
  Upozornění a tlačítko pod ním mají stejné zaoblení rohů i odsazení podle společného pravidla ve stylech.
- **Popis právních předpisů z jejich textu (issue #37, PR #40, `doc/ANOTACE_PREDPISU.md`).** Místo popisu, který jen opakoval
  název, ukazuje stránka zákona, vyhlášky, nařízení či aktu EU doslovné úvodní ustanovení („§ 1 Předmět úpravy“,
  „Článek 1 Předmět“) s uvedením zdroje (173 předpisů). Kde úvodní ustanovení předmět nepopisuje (hlavně novely),
  napsal jazykový model krátké shrnutí, které jiný model zkontroloval; web ho označuje jako přibližné a neověřené
  (23 předpisů) a dokument čeká na doplnění popisu editorem. Zatím v testovací kopii databáze.

## 26.11.2026

- **Testovací web ukládá stavové soubory mimo git.** Soubory, které se mění za provozu (přijaté kandidáty,
  opravy záznamů, mezipaměti kontrol), ukládá testovací web do adresáře z proměnné `H2DB_STATE_DIR`
  (`/home/laborator/nahyc-h2db/.local-test-state`), ne do `data/` pracovního stromu gitu. Adresář jsme
  založili, zkopírovali do něj stavové soubory z `data/` a webovému serveru jsme v něm povolili zápis včetně
  výchozích práv pro nové soubory; doplnili jsme také záznam přijatého kandidáta 87/2025 Sb., který se
  předtím nezapsal (`doc/NASAZENI.md`, odstavec 4.5).
- **Oprava rozvržení seznamu kandidátů.** Sloupec s názvem kandidáta má nejmenší čitelnou šířku a slova se
  v něm nelámou uprostřed; sloupec se zdrojem se zalamuje dřív, takže se tabulka dál vejde do rámečku.
- **Testovací web označen jako testovací verze (PR #36).** Na `nahyc.fd.cvut.cz/h2db` platí `H2DB_INSTANCE=test`, úvodní
  stránka a patička ukazují upozornění „Testovací verze“. Do `doc/NASAZENI.md` (odstavec 4.5) jsme doplnili, že
  po každé změně `.env` je nutné aplikaci znovu načíst (`touch wsgi.py`).
- **Příprava nasazení na produkční server (PR #35, `doc/NASAZENI.md`).** Soubory, které se mění za provozu (opravy a
  rozhodnutí editorů, mezipaměti plánovače, manifest plných textů), aplikace a skripty nově hledají v adresáři
  z `.env` (`H2DB_STATE_DIR`, `src/tools/state_paths.py`), na produkci tedy mimo pracovní strom gitu. Nástroj
  `transfer_bundle.py` přenese databázi a stavové soubory jako ověřený balík (kontrolní součty, počty řádků,
  záloha cílové databáze); skripty v `deploy/production/` jej stáhnou na produkci a jednou týdně pošlou kopii
  produkce na testovací web `nahyc.fd.cvut.cz/h2db`. Přenos jsme vyzkoušeli z provozní do testovací databáze.
- **Verze webu a označení testovací verze (PR #35).** Patička uvádí „Verze webu (git)“ i tehdy, když proces webového serveru
  git spustit nesmí (commit čteme přímo ze souborů `.git`). Server s `H2DB_INSTANCE=test` v `.env` ukazuje na úvodní
  stránce a v patičce upozornění „Testovací verze“ s odkazem na produkční web (`doc/NASAZENI.md`, odstavec 4.5).
- **Potvrzení kandidáta nekončí chybou serveru (PR #34).** První přijatý kandidát (vyhláška č. 146/2024 Sb.)
  skončil chybou 500, ačkoli se přijetí do databáze zapsalo: webový server neměl právo zapsat soubor
  `data/accepted_candidates.json`, z něhož se databáze obnovuje při přestavbě. Webovému serveru jsme
  povolili zápis do čtyř souborů, které editorské akce mění, a chybějící záznam jsme doplnili. Aplikace
  nově při selhání zápisu takového souboru zobrazí editorovi varování a chybu zaznamená do protokolu, místo
  aby skončila chybovou stránkou.
- **Filtr „Ke kontrole“ v katalogu pro editory (PR #33).** Přihlášený editor zúží katalog na dokumenty s příznakem ke
  kontrole podle druhu důvodu: vše ke kontrole, vady k opravě, nálezy kontroly záznamů, odhadnutý jazyk
  a chybějící popis. Filtr editor kombinuje s ostatními filtry, hledáním i stránkováním a u každé volby vidí
  počet; export pro editora navíc obsahuje označení, adresu záznamu a důvody kontroly, takže slouží jako
  pracovní seznam. Návštěvník volbu nevidí a parametr se na něj nevztahuje (`doc/PROVOZ.md`, odstavec 4.6).
- **Přehlednější stav kandidáta ve frontě (PR #33).** Sloupec „Stav“ v seznamu kandidátů ukazuje stav na jednom
  řádku a pod ním samostatný štítek „automat“ nebo jméno navrhovatele; zdroj kandidáta se láme jen mezi
  slovy.
- **Dokumenty pro MPO podle stavu k 26. 11. (PR #30).** Vypořádání připomínek, provozní dokument a návrh průvodního
  e-mailu uvádějí čísla ověřená nad provozní databází a veřejným webem (veřejný katalog 967 dokumentů,
  z toho 825 platných, 116 připravovaných a 26 historických). Doplnili jsme kontrolu záznamů, klíčová slova,
  oblasti a rozšíření tématu RFNBO a přílohy DOCX a PDF jsme vygenerovali znovu. Opakovaná prohlídka webu
  nenašla žádnou novou vadu (`doc/MPO_OVERENI_WEBU.md`, odstavec 4).
- **Issue #2 (plné texty) uzavřeno.** Čistý text zobrazujeme ve vlastní šabloně aplikace, surové stažené
  stránky nedoručujeme a text má 247 z 251 nenormových dokumentů. Zbývající otázky jsme převedli do dvou
  nových issues: hledání v plném textu (#31) a ověření práv k veřejnému zobrazení textů jiných
  vydavatelů (#32).
- **Nasazení PR #29 do provozu.** Kategorie zdrojových rešerší jsme přejmenovali (`SourceCategory`),
  klíčová slova dokumentů jsou v centrální tabulce `Term` (5247 klíčových slov, 12 206 vazeb). Opravili
  jsme pole „Platnost od“ u 466 norem, sedm úředních názvů směrnic, propojili slovenské znění rozhodnutí
  (EU) 2013/732 s českým, přidali pět kandidátů k RFNBO a všem 1432 dokumentům přiřadili oblasti
  (`doc/OBLASTI.md`, `doc/KLICOVA_SLOVA.md`).

## 25.11.2026

- **Sloučení rozpracovaných větví (PR #29).** Klíčová slova, kontrolu a opravy záznamů, opravy vad webu,
  RFNBO, oblasti katalogu a dokumenty pro MPO jsme spojili do jedné změny a celou sadu testů spustili nad
  kopií provozní databáze.

## 23.11.2026

- **Kontrola a opravy záznamů.** Záznamy jsme porovnali s úředními rejstříky (Cellar, otevřená data ISO)
  a mezi sebou a nechali je posoudit jazykovým modelem (`doc/KONTROLA_ZAZNAMU.md`). Opravili jsme názvy
  a anotace norem ISO, odstranili popisy bez doloženého zdroje, sloučili duplicity a vyřadili 28 aktů EU
  mimo rozsah databáze; počet záznamů klesl z 1506 na 1432. Zbylé nálezy předali editorům ke kontrole.
  Zavedli jsme zásadu, že jazykový model nedodává název ani popis dokumentu bez zdroje.
- **Klíčová slova dokumentů.** Akty EU mají deskriptory EuroVoc, normy třídy ICS a deskriptory ČSN,
  všechny dokumenty česká klíčová slova odvozená jazykovým modelem (`doc/KLICOVA_SLOVA.md`).

## 21. až 22.11.2026

- **Prohlídka veřejného webu proti připomínkám MPO.** Připomínky 1 až 10 web potvrdil; našli jsme pět
  dalších vad (počty na úvodní stránce, lupa na telefonu, pole „Platnost od“ u norem, neúřední názvy
  směrnic, datum kontroly u CLP a REACH) a opravili je (`doc/MPO_OVERENI_WEBU.md`).
- **RFNBO.** Porovnali jsme pokrytí tématu s autoritativními zdroji (`doc/RFNBO_POKRYTI.md`), rozšířili
  vyhledávání (dotaz „RFNBO“ najde 12 dokumentů místo 7), pět chybějících aktů zařadili do fronty kandidátů
  a zavedli test pokrytí.
- **Oblasti katalogu.** Filtr „Oblast“ ukazuje 29 veřejných českých oblastí navázaných na věcné okruhy
  databáze místo 238 kategorií převzatých ze zdrojových rešerší (`doc/OBLASTI.md`).

## 20.11.2026

- **Nasazení vypořádání připomínek MPO (PR #26 až #28).** Jeden řádek na předpis se štítky jazykových
  verzí, filtr institucí a jurisdikce, podtyp aktů EU, vyhledávání podle zkratek a synonym, kategorie
  „Strategie“ (32 dokumentů), skrytí slovenských dokumentů, datum poslední kontroly u dokumentu, plné texty
  aktů EU z Cellaru, konsolidovaná znění CLP a REACH, první sběr zdrojů a návrhů předpisů (242 nálezů).
- **Automatické předtřídění fronty kandidátů.** Z 592 kandidátů automat navrhl k přijetí 242, zamítl 163
  a odložil 46; každé přijetí potvrzuje editor (`doc/FRONTA_AUTOMAT.md`).

## 19.11.2026

- **Rozbor připomínek MPO a první opravy dat.** Připomínky z e-mailů ze 17. 4. a 22.05.2026 jsme porovnali
  se stavem aplikace a navrhli postup vypořádání (`doc/MPO_PRIPOMINKY.md`). Opravili jsme odpovědné
  instituce, zastaralou hlášku, interní poznámky a chybné názvy a vyřadili nesouvisející rozhodnutí ECB.
