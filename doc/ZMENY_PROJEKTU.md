# Záznam změn v projektu

Krátké záznamy o tom, co jsme v databázi a aplikaci změnili, v pořadí od nejnovějšího. Slouží jako podklad
pro zprávy MPO a TAČR. Každý záznam uvádí datum, co jsme udělali a kde je podrobný popis. Záznam
přidáváme po každém dokončeném kroku.

## 26. 11. 2026

- **Filtr „Ke kontrole“ v katalogu pro editory.** Přihlášený editor zúží katalog na dokumenty s příznakem ke
  kontrole podle druhu důvodu: vše ke kontrole, vady k opravě, nálezy kontroly záznamů, odhadnutý jazyk
  a chybějící popis. Filtr editor kombinuje s ostatními filtry, hledáním i stránkováním a u každé volby vidí
  počet; export pro editora navíc obsahuje označení, adresu záznamu a důvody kontroly, takže slouží jako
  pracovní seznam. Návštěvník volbu nevidí a parametr se na něj nevztahuje (`doc/PROVOZ.md`, odstavec 4.6).
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

## 25. 11. 2026

- **Sloučení rozpracovaných větví (PR #29).** Klíčová slova, kontrolu a opravy záznamů, opravy vad webu,
  RFNBO, oblasti katalogu a dokumenty pro MPO jsme spojili do jedné změny a celou sadu testů spustili nad
  kopií provozní databáze.

## 23. 11. 2026

- **Kontrola a opravy záznamů.** Záznamy jsme porovnali s úředními rejstříky (Cellar, otevřená data ISO)
  a mezi sebou a nechali je posoudit jazykovým modelem (`doc/KONTROLA_ZAZNAMU.md`). Opravili jsme názvy
  a anotace norem ISO, odstranili popisy bez doloženého zdroje, sloučili duplicity a vyřadili 28 aktů EU
  mimo rozsah databáze; počet záznamů klesl z 1506 na 1432. Zbylé nálezy předali editorům ke kontrole.
  Zavedli jsme zásadu, že jazykový model nedodává název ani popis dokumentu bez zdroje.
- **Klíčová slova dokumentů.** Akty EU mají deskriptory EuroVoc, normy třídy ICS a deskriptory ČSN,
  všechny dokumenty česká klíčová slova odvozená jazykovým modelem (`doc/KLICOVA_SLOVA.md`).

## 21. až 22. 11. 2026

- **Prohlídka veřejného webu proti připomínkám MPO.** Připomínky 1 až 10 web potvrdil; našli jsme pět
  dalších vad (počty na úvodní stránce, lupa na telefonu, pole „Platnost od“ u norem, neúřední názvy
  směrnic, datum kontroly u CLP a REACH) a opravili je (`doc/MPO_OVERENI_WEBU.md`).
- **RFNBO.** Porovnali jsme pokrytí tématu s autoritativními zdroji (`doc/RFNBO_POKRYTI.md`), rozšířili
  vyhledávání (dotaz „RFNBO“ najde 12 dokumentů místo 7), pět chybějících aktů zařadili do fronty kandidátů
  a zavedli test pokrytí.
- **Oblasti katalogu.** Filtr „Oblast“ ukazuje 29 veřejných českých oblastí navázaných na věcné okruhy
  databáze místo 238 kategorií převzatých ze zdrojových rešerší (`doc/OBLASTI.md`).

## 20. 11. 2026

- **Nasazení vypořádání připomínek MPO (PR #26 až #28).** Jeden řádek na předpis se štítky jazykových
  verzí, filtr institucí a jurisdikce, podtyp aktů EU, vyhledávání podle zkratek a synonym, kategorie
  „Strategie“ (32 dokumentů), skrytí slovenských dokumentů, datum poslední kontroly u dokumentu, plné texty
  aktů EU z Cellaru, konsolidovaná znění CLP a REACH, první sběr zdrojů a návrhů předpisů (242 nálezů).
- **Automatické předtřídění fronty kandidátů.** Z 592 kandidátů automat navrhl k přijetí 242, zamítl 163
  a odložil 46; každé přijetí potvrzuje editor (`doc/FRONTA_AUTOMAT.md`).

## 19. 11. 2026

- **Rozbor připomínek MPO a první opravy dat.** Připomínky z e-mailů ze 17. 4. a 22. 5. 2026 jsme porovnali
  se stavem aplikace a navrhli postup vypořádání (`doc/MPO_PRIPOMINKY.md`). Opravili jsme odpovědné
  instituce, zastaralou hlášku, interní poznámky a chybné názvy a vyřadili nesouvisející rozhodnutí ECB.
