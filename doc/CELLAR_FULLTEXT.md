# Plné texty z EUR-Lexu přes Cellar

Stav k 20. 11. 2026, větev `feature/mpo-cellar`. Dokument popisuje převod
stahování plných textů aktů EU z webu EUR-Lex na úložiště Cellar Úřadu pro
publikace EU, ověření úplnosti textů z Cellaru a stav po převodu.

## 1. Výchozí stav a důvod změny

EUR-Lex odpovídá automatizovaným klientům výzvou firewallu (HTTP 202
s prázdným tělem). Skript `src/tools/fetch_fulltext.py` ji od 25. 10. 2026
obcházel: stránku otevřel v headless prohlížeči Chromium (Playwright,
`fetch_with_browser`) a PDF stahoval kontextem prohlížeče poté, co
načetl úvodní stránku webu (`_fetch_eurlex_pdf_with_browser`). Takové
obcházení ochrany proti robotům je nepřípustné. Od 19. 11. 2026 se
z Cellaru stahovaly adresy s číslem CELEX; adresy ELI (`/eli/…`)
a adresy Úředního věstníku (`?uri=OJ:L_…`) dál šly přes prohlížeč.

Manifest `data/fulltext_manifest.json` k 20. 11. 2026 obsahoval
505 stažených položek z EUR-Lexu (288 různých souborů). Z nich
266 souborů (476 položek) bylo staženo před 19. 11. 2026 přímo z EUR-Lexu,
tedy prostým HTTP, nebo — od 25. 10. 2026 při výzvě firewallu — prohlížečem;
manifest nezaznamenává, kterou cestou. Zbylých 22 souborů (29 položek) již
pochází z Cellaru. Podle tvaru adresy jde o 151 souborů z adres ELI,
123 z adres s číslem CELEX a 14 z adres Úředního věstníku.
Soubor `data/fulltext_url_overrides.json` měl 11 přepsání adres na EUR-Lex.

## 2. Provedená změna

* **Žádný přístup na EUR-Lex.** `fetch_fulltext.py` se na
  `eur-lex.europa.eu` neobrací vůbec, ani prostým HTTP. Každou adresu
  EUR-Lexu stáhne z Cellaru (`src/sites/eurlex.py: fetch_cellar`)
  vyjednáním obsahu: jazyk podle adresy (`Accept-Language`), formát PDF
  pro adresu `TXT/PDF`, jinak XHTML nebo HTML. Co Cellar nedá, je
  zaznamenáno jako selhání.
* **Překlad adres na CELEX** (`resolve_celex`): číslo CELEX z adresy (včetně
  data konsolidovaného znění, např. `02022R0869-20250205`); adresa ELI
  a adresa Úředního věstníku přes dotaz SPARQL na `owl:sameAs` zdroje
  `http://publications.europa.eu/resource/eli/…` resp. `…/resource/oj/…`.
  Vrátí-li Cellar více čísel, výsledek se nehádá. Pro ELI, které Cellar
  s dílem nepropojil (nařízení (EU) 2021/535), se číslo CELEX sestaví z typu
  a čísla aktu a přijme se jen tehdy, nese-li název díla v Cellaru číslo
  aktu.
* **PDF bez profilu.** Část PDF (např. 1999/92/ES, (EU) 1300/2014) má Cellar
  jen pod obecným typem `application/pdf`; ten se zkouší jako poslední.
* **Kód prohlížeče pro EUR-Lex je odstraněn** (`_fetch_eurlex_pdf_with_browser`,
  `is_eurlex_pdf`, výzva firewallu jako důvod pro prohlížeč);
  `fetch_with_browser` adresu EUR-Lexu odmítne výjimkou.
* **Extraktor** `src/tools/extract_fulltext.py` čte XHTML Úředního věstníku
  celé (odstavec 4).

## 3. Postup ověření

Pro každý z 288 uložených souborů jsme skriptem
`src/tools/compare_cellar_fulltext.py` stáhli verzi z Cellaru (do
`data/fulltext_mpo_cellar/` ve worktree) a porovnali ji se souborem
v `data/fulltext/` hlavního stromu (u 22 souborů z 19. 11. 2026, jež
v hlavním stromu ještě nejsou, s kopií v jiném worktree):

* **jazyk** vytěženého textu (langdetect na jeho začátku);
* **délku** vytěženého textu (`extract_fulltext.py`, PDF přes `pdf_text.py`
  v interpretu `~/.cache/lit-tools/bin/python`);
* **přílohy** — počet řádků tvořených jen nadpisem „PŘÍLOHA …“, „ANNEX …“,
  „PRÍLOHA …“;
* **název** — číslo aktu (z čísla CELEX) na začátku textu z Cellaru
  a podobnost prvních 400 znaků obou textů.

Verdikt „shodné“ znamená bajtově shodný soubor, „úplné“ text z Cellaru ve
stejném jazyce, nejvýše o 3 % kratší, se stejným nebo vyšším počtem příloh
a s číslem aktu v názvu. Podrobné výsledky jsou v
`data/cellar_fulltext_comparison.json`.

## 4. Výsledek

| Verdikt | Souborů |
|---|--:|
| shodné (bajtově) | 68 |
| úplné | 218 |
| Cellar nedal soubor (celé číslo Úředního věstníku) | 2 |
| **celkem** | **288** |

* **Jazyk** souhlasí u všech 286 porovnaných souborů. Podobnost začátku
  textu je nejméně 0,84; nižší než 0,95 je jen u (EU) 2023/2405
  a (EU) 2024/1735, kde uložená stránka EUR-Lexu začíná navíc průběžným
  záhlavím (`2023/2405 31.10.2023`). Text samotný je shodný.
* **Žádný text z Cellaru není kratší** než uložený (rozdíl do 5 znaků,
  záhlaví Úředního věstníku).
* **Tři uložené soubory byly neúplné**, Cellar dává úplný text: (EU) 2019/776
  (uloženo 132 tis. znaků a 2 přílohy, Cellar 478 tis. a 8 příloh),
  (EU) 2021/535 (130 tis. / 387 tis., 8 / 14 příloh) a (EU) 2024/1789
  (367 tis. / 385 tis., 1 / 3 přílohy). Stránka EUR-Lexu v prohlížeči
  patrně nebyla načtena celá.
* **Přílohy 2022/2427 a dalších aktů.** XHTML Úředního věstníku (z Cellaru
  i pohled EUR-Lexu `TXT/HTML`) obsahuje akt v `div.eli-container` a každou
  přílohu jako sourozenecký `div` za `hr.oj-doc-sep`. Extraktor bral jen
  první `.eli-container`: u verze 2022/2427 z Cellaru tak zbylo 2,5 tisíce
  znaků ze 111 tisíc, bez příloh se závěry BAT. Táž chyba postihla i uložené
  stránky `TXT/HTML` z EUR-Lexu: vyčištěné texty 33 souborů (21 aktů,
  např. 2014/68/EU 108 tis. místo 230 tis. znaků, (EU) 2014/1302 13 tis.
  místo 410 tis., (EU) 2019/773 8 tis. místo 178 tis.) jsou na webu bez
  příloh. Extraktor nyní bere celý nadřazený prvek (`_act_with_annexes`);
  po mergi a novém běhu `extract_fulltext.py --apply` budou přílohy na webu.
* **Staré akty (před 2004)** má Cellar jako stránku s odstavci obalenými
  `<p><TXT_TE>`; parser vnořil celý akt do prvního odstavce a text splynul.
  Extraktor obal nyní odstraní (1999/92/ES, 2001/42/ES aj. vycházejí shodně).
* **Směrnice 2014/34/EU (ATEX):** zdroj uvádí PDF celého čísla Úředního
  věstníku L 96/2014 (380 stran), nikoli směrnici; Cellar číslo věstníku
  jako akt nevydává. Řešení: přepsání adresy na PDF směrnice
  (`…/TXT/PDF/?uri=CELEX:32014L0034`, česky i anglicky) v
  `data/fulltext_url_overrides.json`. PDF z Cellaru jsme ověřili stejně:
  česky 132 537 znaků a 12 příloh, anglicky 151 923 znaků (text HTML
  z Cellaru 131 226 a 150 777 znaků), jazyk souhlasí.

**Manifest je přepnut na Cellar u všech 505 stažených položek** (verdikt
„shodné“ nebo „úplné“, u 2014/34/EU PDF směrnice): `local_path` ukazuje na
soubor z Cellaru (`data/fulltext/<název>`, soubory jsou zatím
v `data/fulltext_mpo_cellar/`), položka nese `"via": "cellar"` a číslo
CELEX. Adresy (`url`) se nemění, s výjimkou 2014/34/EU.

## 5. Co zůstává

* **Čtyři selhané položky** (bez souboru, dokument má text z jiné položky):
  * nařízení CLP (ES) 1272/2008, `odkaz_eu` (ELI) a dvojče HTML: Cellar
    nyní české XHTML má (23 MB, 2,47 mil. znaků, 7 příloh), dokument má text
    z PDF (2,81 mil. znaků). Doplnění HTML navrhujeme zvážit; text z PDF je
    úplný.
  * REACH (ES) 1907/2006, dvě dvojčata HTML: Cellar české HTML nemá; text
    je z PDF (834 tis. znaků, 21 příloh). Řešení není potřeba.
* **Soubory PDF bez varianty v Cellaru** nezůstal žádný.
* **Jiné weby s prohlížečem nebo s identitou prohlížeče** (mimo rozsah této
  změny, uvedeno k rozhodnutí):
  * Slov-Lex (`fetch_fulltext.py: fetch_with_browser`,
    `populate_eu_transposition.py`) — jednostránková aplikace, jež se
    vykreslí jen v prohlížeči; ochranu proti robotům neobchází, prohlížeč
    však používá; `src/sites/slovlex.py` a `src/sites/zakonyprolidi.py`
    se představují jako prohlížeč (User-Agent);
  * IEC (`harvest_iec_publications.py`, AWS WAF Bot Control), DVGW
    (`harvest_dvgw_publications.py`) — odloženo k rozhodnutí
    (`doc/MPO_PRIPOMINKY.md`, odstavec 5.2);
  * ISO (`add_missing_iso_parents.py`) — iso.org vrací prostému HTTP 403,
    skript jej obchází headless prohlížečem s User-Agentem prohlížeče;
    navrhujeme jej zařadit k IEC, EIGA a DVGW a vypnout.

## 6. Postup po mergi

V hlavním stromu (`/home/laborator/DEVEL/nahyc-h2db`):

```
git pull
cp -n .claude/worktrees/mpo-cellar/data/fulltext_mpo_cellar/*.html \
      .claude/worktrees/mpo-cellar/data/fulltext_mpo_cellar/*.pdf data/fulltext/
.venv/bin/python src/tools/backup_db.py --reason before_cellar_fulltext
.venv/bin/python src/tools/prune_fulltext.py --apply      # nejprve bez --apply
.venv/bin/python src/tools/sync_fulltext_paths.py --apply # nejprve bez --apply
~/.cache/lit-tools/bin/python src/tools/extract_fulltext.py --apply
```

`prune_fulltext.py` smaže staré soubory, na něž manifest už neukazuje
(a jejich vyčištěné texty), `sync_fulltext_paths.py --apply` pak přesměruje
`Document.file_path`, jež ukazuje na chybějící soubor, na soubor z Cellaru
podle manifestu, `extract_fulltext.py --apply` vytvoří vyčištěné texty znovu
(s přílohami). Mezi druhým a posledním krokem stránky dotčených dokumentů
krátce nenabízejí text; kroky proto spouštíme bezprostředně po sobě.

## 7. Tabulka ověření

Jeden řádek na uložený soubor. „Dokument“ je značka z klíče manifestu
(u českého zákona s odkazem na akt EU je to značka zákona, CELEX ukazuje
stažený akt), „Starý zdroj“ tvar adresy a formát, délky jsou počty znaků
vytěženého textu (stará délka s opraveným extraktorem), „Přílohy“ počet
nadpisů příloh uloženého souboru / souboru z Cellaru.

| Dokument | Starý zdroj | Cellar (CELEX) | Jazyk | Délka stará | Délka Cellar | Přílohy | Verdikt |
|---|---|---|---|--:|--:|--:|---|
| (ES) 1272/2008 | CELEX, PDF | 32008R1272 | CS | 2808620 | 2808620 | 7 / 7 | shodné |
| (ES) 1907/2006 | CELEX, PDF | 32006R1907 | CS | 834130 | 834130 | 21 / 21 | shodné |
| (EU) 1300/2014 | CELEX, HTML | 32014R1300 | CS | 161420 | 161420 | 1 / 1 | úplné |
| (EU) 1300/2014 | CELEX, PDF | 32014R1300 | CS | 169220 | 169220 | 1 / 1 | shodné |
| (EU) 1300/2014 [EN] | CELEX, PDF | 32014R1300 | EN | 168859 | 168859 | 1 / 1 | shodné |
| (EU) 1300/2014 [EN] | CELEX, HTML | 32014R1300 | EN | 161043 | 161043 | 1 / 1 | úplné |
| (EU) 1303/2014 | CELEX, PDF | 32014R1303 | CS | 75001 | 75001 | 1 / 1 | shodné |
| (EU) 1303/2014 | CELEX, HTML | 32014R1303 | CS | 68832 | 68832 | 1 / 1 | úplné |
| (EU) 1303/2014 [EN] | CELEX, HTML | 32014R1303 | EN | 70172 | 70172 | 1 / 1 | úplné |
| (EU) 1303/2014 [EN] | CELEX, PDF | 32014R1303 | EN | 76561 | 76561 | 1 / 1 | shodné |
| (EU) 2008/521 | CELEX, HTML | 32008R0521 | CS | 58010 | 58005 | 1 / 1 | úplné |
| (EU) 2009/79 | CELEX, HTML | 32009R0079 | CS | 41322 | 41317 | 7 / 7 | úplné |
| (EU) 2010/406 | CELEX, HTML | 32010R0406 | CS | 220554 | 220549 | 7 / 7 | úplné |
| (EU) 2011/1183 | CELEX, HTML | 32011R1183 | CS | 6704 | 6699 | 1 / 1 | úplné |
| (EU) 2012/630 | CELEX, HTML | 32012R0630 | CS | 28987 | 28982 | 1 / 1 | úplné |
| (EU) 2013/732 | ELI, HTML | 32013D0732 | CS | 36321 | 36316 | 1 / 1 | úplné |
| (EU) 2013/732 | ELI, HTML | 32013D0732 | EN | 36486 | 36481 | 1 / 1 | úplné |
| (EU) 2014/1301 | CELEX, HTML | 32014R1301 | CS | 96357 | 96357 | 1 / 1 | úplné |
| (EU) 2014/1301 | CELEX, PDF | 32014R1301 | CS | 105423 | 105423 | 1 / 1 | shodné |
| (EU) 2014/1301 [EN] | CELEX, PDF | 32014R1301 | EN | 109056 | 109056 | 1 / 1 | shodné |
| (EU) 2014/1301 [EN] | CELEX, HTML | 32014R1301 | EN | 100387 | 100387 | 1 / 1 | úplné |
| (EU) 2014/1302 | CELEX, PDF | 32014R1302 | CS | 424950 | 424950 | 1 / 1 | shodné |
| (EU) 2014/1302 | CELEX, HTML | 32014R1302 | CS | 409773 | 409773 | 1 / 1 | úplné |
| (EU) 2014/1302 [EN] | CELEX, HTML | 32014R1302 | EN | 423580 | 423580 | 1 / 1 | úplné |
| (EU) 2014/1302 [EN] | CELEX, PDF | 32014R1302 | EN | 438253 | 438253 | 1 / 1 | shodné |
| (EU) 2014/1304 | CELEX, PDF | 32014R1304 | CS | 42767 | 42767 | 1 / 1 | shodné |
| (EU) 2014/1304 | CELEX, HTML | 32014R1304 | CS | 39257 | 39257 | 1 / 1 | úplné |
| (EU) 2014/1304 [EN] | CELEX, PDF | 32014R1304 | EN | 44523 | 44523 | 1 / 1 | shodné |
| (EU) 2014/1304 [EN] | CELEX, HTML | 32014R1304 | EN | 41133 | 41133 | 1 / 1 | úplné |
| (EU) 2014/559 | CELEX, HTML | 32014R0559 | CS | 58905 | 58900 | 1 / 1 | úplné |
| (EU) 2014/832 | CELEX, HTML | 32014D0832 | CS | 2238 | 2233 | 0 / 0 | úplné |
| (EU) 2016/797 | CELEX, PDF | 32016L0797 | CS | 171866 | 171866 | 6 / 6 | shodné |
| (EU) 2016/797 | CELEX, HTML | 32016L0797 | CS | 171868 | 171868 | 6 / 6 | úplné |
| (EU) 2016/797 [EN] | CELEX, PDF | 32016L0797 | EN | 194574 | 194574 | 6 / 6 | shodné |
| (EU) 2016/797 [EN] | CELEX, HTML | 32016L0797 | EN | 194581 | 194581 | 6 / 6 | úplné |
| (EU) 2016/798 | CELEX, PDF | 32016L0798 | CS | 149036 | 149036 | 5 / 5 | shodné |
| (EU) 2016/798 | CELEX, HTML | 32016L0798 | CS | 151925 | 151925 | 5 / 5 | úplné |
| (EU) 2016/798 [EN] | CELEX, HTML | 32016L0798 | EN | 163180 | 163180 | 5 / 5 | úplné |
| (EU) 2016/798 [EN] | CELEX, PDF | 32016L0798 | EN | 160605 | 160605 | 5 / 5 | shodné |
| (EU) 2018/2001 | CELEX, HTML | 32018L2001 | CS | 384535 | 384535 | 11 / 11 | úplné |
| (EU) 2018/2001 | CELEX, PDF | 32018L2001 | CS | 392173 | 392173 | 11 / 11 | shodné |
| (EU) 2018/2001 [EN] | CELEX, HTML | 32018L2001 | EN | 390309 | 390309 | 11 / 11 | úplné |
| (EU) 2018/2001 [EN] | CELEX, PDF | 32018L2001 | EN | 397086 | 397086 | 11 / 11 | shodné |
| (EU) 2018/545 | CELEX, PDF | 32018R0545 | CS | 105256 | 105256 | 3 / 3 | shodné |
| (EU) 2018/545 | CELEX, HTML | 32018R0545 | CS | 104262 | 104262 | 3 / 3 | úplné |
| (EU) 2018/545 [EN] | CELEX, HTML | 32018R0545 | EN | 116082 | 116082 | 3 / 3 | úplné |
| (EU) 2018/545 [EN] | CELEX, PDF | 32018R0545 | EN | 117104 | 117104 | 3 / 3 | shodné |
| (EU) 2018/546 | CELEX, PDF | 32018D0010(01) | CS | 16694 | 16694 | 0 / 0 | shodné |
| (EU) 2018/546 | CELEX, HTML | 32018D0010(01) | CS | 16596 | 16596 | 0 / 0 | úplné |
| (EU) 2018/546 [EN] | CELEX, HTML | 32018D0010(01) | EN | 16605 | 16605 | 0 / 0 | úplné |
| (EU) 2018/546 [EN] | CELEX, PDF | 32018D0010(01) | EN | 16696 | 16696 | 0 / 0 | shodné |
| (EU) 2018/674 | CELEX, HTML | 32018R0674 | CS | 5960 | 5955 | 0 / 0 | úplné |
| (EU) 2018/858 | ELI, HTML | 32018R0858 | EN | 586596 | 586591 | 12 / 12 | úplné |
| (EU) 2018/858 | ELI, HTML | 32018R0858 | CS | 536137 | 536132 | 12 / 12 | úplné |
| (EU) 2018/858 [SK] | CELEX, HTML | 32018R0858 | SK | 553128 | 553128 | 12 / 12 | shodné |
| (EU) 2019/1745 | CELEX, HTML | 32019R1745 | CS | 16733 | 16728 | 0 / 0 | úplné |
| (EU) 2019/2144 | ELI, HTML | 32019R2144 | EN | 108240 | 108235 | 4 / 4 | úplné |
| (EU) 2019/2144 | ELI, HTML | 32019R2144 | CS | 102095 | 102090 | 4 / 4 | úplné |
| (EU) 2019/250 | CELEX, PDF | 32019R0250 | CS | 30725 | 30725 | 7 / 7 | shodné |
| (EU) 2019/250 | CELEX, HTML | 32019R0250 | CS | 30084 | 30084 | 7 / 7 | úplné |
| (EU) 2019/250 [EN] | CELEX, PDF | 32019R0250 | EN | 35105 | 35105 | 7 / 7 | shodné |
| (EU) 2019/250 [EN] | CELEX, HTML | 32019R0250 | EN | 34483 | 34483 | 7 / 7 | úplné |
| (EU) 2019/692 | ELI, HTML | 32019L0692 | EN | 27538 | 27533 | 0 / 0 | úplné |
| (EU) 2019/692 | ELI, HTML | 32019L0692 | CS | 24652 | 24647 | 0 / 0 | úplné |
| (EU) 2019/773 | CELEX, PDF | 32019R0773 | CS | 184973 | 184973 | 1 / 1 | shodné |
| (EU) 2019/773 | CELEX, HTML | 32019R0773 | CS | 178498 | 178478 | 1 / 1 | úplné |
| (EU) 2019/773 [EN] | CELEX, HTML | 32019R0773 | EN | 181524 | 181504 | 1 / 1 | úplné |
| (EU) 2019/773 [EN] | CELEX, PDF | 32019R0773 | EN | 188738 | 188738 | 1 / 1 | shodné |
| (EU) 2019/776 | CELEX, HTML | 32019R0776 | CS | 132234 | 478169 | 2 / 8 | úplné; uložený soubor neúplný |
| (EU) 2019/776 | CELEX, PDF | 32019R0776 | CS | 471711 | 471711 | 8 / 8 | shodné |
| (EU) 2019/776 [EN] | CELEX, PDF | 32019R0776 | EN | 490700 | 490700 | 8 / 8 | shodné |
| (EU) 2019/776 [EN] | CELEX, HTML | 32019R0776 | EN | 498787 | 498787 | 8 / 8 | úplné |
| (EU) 2019/942 | CELEX, PDF | 32019R0942 | CS | 99203 | 99203 | 2 / 2 | shodné |
| (EU) 2019/942 | CELEX, HTML | 32019R0942 | CS | 99154 | 99154 | 2 / 2 | úplné |
| (EU) 2019/942 [EN] | CELEX, PDF | 32019R0942 | EN | 115716 | 115716 | 2 / 2 | shodné |
| (EU) 2019/942 [EN] | CELEX, HTML | 32019R0942 | EN | 115666 | 115666 | 2 / 2 | úplné |
| (EU) 2021/535 | ELI, HTML | 32021R0535 | CS | 129597 | 386967 | 8 / 14 | úplné; uložený soubor neúplný |
| (EU) 2021/535 | ELI, HTML | 32021R0535 | EN | 410341 | 410336 | 14 / 14 | úplné |
| (EU) 2022/2427 | ELI, HTML | 32022D2427 | CS | 111315 | 111310 | 1 / 1 | úplné |
| (EU) 2022/2427 [SK] | CELEX, HTML | 32022D2427 | SK | 116480 | 116480 | 1 / 1 | shodné |
| (EU) 2022/2427 [SK] | ELI, HTML | 32022D2427 | SK | 116485 | 116480 | 1 / 1 | úplné |
| (EU) 2022/869 | CELEX, HTML | 02022R0869-20250205 | CS | 190543 | 190381 | 7 / 7 | úplné |
| (EU) 2022/869 | ELI, HTML | 32022R0869 | EN | 233286 | 233281 | 6 / 6 | úplné |
| (EU) 2022/869 | ELI, HTML | 32022R0869 | CS | 220658 | 220653 | 6 / 6 | úplné |
| (EU) 2022/869 | CELEX, PDF | 02022R0869-20250205 | CS | 195936 | 195936 | 7 / 7 | shodné |
| (EU) 2022/869 [EN] | CELEX, HTML | 02022R0869-20250205 | EN | 197347 | 197185 | 7 / 7 | úplné |
| (EU) 2022/869 [EN] | CELEX, PDF | 02022R0869-20250205 | EN | 202415 | 202415 | 10 / 10 | shodné |
| (EU) 2023/1184 | ELI, HTML | 32023R1184 | EN | 34501 | 34496 | 0 / 0 | úplné |
| (EU) 2023/1184 | ELI, HTML | 32023R1184 | CS | 35254 | 35249 | 0 / 0 | úplné |
| (EU) 2023/1185 | ELI, HTML | 32023R1185 | EN | 40815 | 40810 | 1 / 1 | úplné |
| (EU) 2023/1185 | ELI, HTML | 32023R1185 | EN | 40815 | 40810 | 1 / 1 | úplné |
| (EU) 2023/1804 | ELI, HTML | 32023R1804 | CS | 166840 | 166835 | 4 / 4 | úplné |
| (EU) 2023/1804 | ELI, HTML | 32023R1804 | EN | 177430 | 177425 | 4 / 4 | úplné |
| (EU) 2023/1804 | CELEX, HTML | 32023R1804 | CS | 166835 | 166835 | 4 / 4 | úplné |
| (EU) 2023/1804 | CELEX, PDF | 32023R1804 | CS | 166879 | 166879 | 4 / 4 | shodné |
| (EU) 2023/1804 [EN] | CELEX, PDF | 32023R1804 | EN | 177474 | 177474 | 4 / 4 | shodné |
| (EU) 2023/1804 [EN] | CELEX, HTML | 32023R1804 | EN | 177425 | 177425 | 4 / 4 | úplné |
| (EU) 2023/2405 | ELI, HTML | 32023R2405 | EN | 119436 | 119410 | 2 / 2 | úplné |
| (EU) 2023/2405 | ELI, HTML | 32023R2405 | CS | 116772 | 116746 | 2 / 2 | úplné |
| (EU) 2023/2413 | Úř. věstník, HTML | 32023L2413 | CS | 295614 | 295614 | 2 / 2 | úplné |
| (EU) 2023/2413 | Úř. věstník, PDF | 32023L2413 | CS | 295459 | 295459 | 2 / 2 | shodné |
| (EU) 2023/2413 | ELI, HTML | 32023L2413 | CS | 295640 | 295614 | 2 / 2 | úplné |
| (EU) 2023/2413 | ELI, HTML | 32023L2413 | EN | 305513 | 305487 | 2 / 2 | úplné |
| (EU) 2023/2413 [EN] | Úř. věstník, PDF | 32023L2413 | EN | 305108 | 305108 | 2 / 2 | shodné |
| (EU) 2023/2413 [EN] | Úř. věstník, HTML | 32023L2413 | EN | 305487 | 305487 | 2 / 2 | úplné |
| (EU) 2023/955 | ELI, HTML | 32023R0955 | EN | 158827 | 158822 | 5 / 5 | úplné |
| (EU) 2023/955 | ELI, HTML | 32023R0955 | CS | 145247 | 145242 | 5 / 5 | úplné |
| (EU) 2024/1735 | ELI, HTML | 32024R1735 | CS | 253331 | 253306 | 1 / 1 | úplné |
| (EU) 2024/1788 | Úř. věstník, PDF | 32024L1788 | CS | 402574 | 402574 | 4 / 4 | shodné |
| (EU) 2024/1788 | Úř. věstník, HTML | 32024L1788 | CS | 402749 | 402749 | 4 / 4 | úplné |
| (EU) 2024/1788 [EN] | Úř. věstník, HTML | 32024L1788 | EN | 430094 | 430094 | 4 / 4 | úplné |
| (EU) 2024/1788 [EN] | Úř. věstník, PDF | 32024L1788 | EN | 429989 | 429989 | 4 / 4 | shodné |
| (EU) 2024/1788 [SK] | CELEX, HTML | 32024L1788 | SK | 415176 | 415151 | 4 / 4 | úplné |
| (EU) 2024/1789 | Úř. věstník, HTML | 32024R1789 | CS | 366907 | 384988 | 1 / 3 | úplné; uložený soubor neúplný |
| (EU) 2024/1789 | Úř. věstník, PDF | 32024R1789 | CS | 384899 | 384899 | 3 / 3 | shodné |
| (EU) 2024/1789 [EN] | Úř. věstník, HTML | 32024R1789 | EN | 419897 | 419897 | 3 / 3 | úplné |
| (EU) 2024/1789 [EN] | Úř. věstník, PDF | 32024R1789 | EN | 419854 | 419854 | 3 / 3 | shodné |
| (EU) 2025/1486 | CELEX, HTML | 32025D1486 | CS | 8457 | 8343 | 0 / 0 | úplné |
| (EU) 2025/258 | CELEX, HTML | 32025R0258 | CS | 232373 | 232361 | 11 / 11 | úplné |
| (EU) 2025/656 | CELEX, HTML | 32025R0656 | CS | 34263 | 34249 | 1 / 1 | úplné |
| (EU) 2026/1551 | CELEX, HTML | 32026D1551 | CS | 8419 | 8305 | 0 / 0 | úplné |
| (EU) 402/2013 | CELEX, HTML | 32013R0402 | CS | 60320 | 60320 | 3 / 3 | úplné |
| (EU) 402/2013 | CELEX, PDF | 32013R0402 | CS | 59289 | 59289 | 3 / 3 | shodné |
| (EU) 402/2013 [EN] | CELEX, PDF | 32013R0402 | EN | 63777 | 63777 | 3 / 3 | shodné |
| (EU) 402/2013 [EN] | CELEX, HTML | 32013R0402 | EN | 64907 | 64907 | 3 / 3 | úplné |
| (EU)1305/2014 | CELEX, HTML | 32014R1305 | CS | 142572 | 142572 | 1 / 1 | úplné |
| (EU)1305/2014 | CELEX, PDF | 32014R1305 | CS | 149127 | 149127 | 1 / 1 | shodné |
| (EU)1305/2014 [EN] | CELEX, HTML | 32014R1305 | EN | 149160 | 149160 | 1 / 1 | úplné |
| (EU)1305/2014 [EN] | CELEX, PDF | 32014R1305 | EN | 156001 | 156001 | 1 / 1 | shodné |
| 100/2001 Sb. | ELI, HTML | 32001L0042 | CS | 27011 | 27007 | 2 / 2 | úplné |
| 114/1992 Sb. | ELI, HTML | 32006R0865 | CS | 178739 | 178734 | 12 / 12 | úplné |
| 116/2016 Sb. | ELI, HTML | 32014L0034 | CS | 131231 | 131226 | 12 / 12 | úplné |
| 13/1997 Sb. | ELI, HTML | 31999L0062 | CS | 22289 | 22285 | 2 / 2 | úplné |
| 133/2010 Sb. | ELI, HTML | 31998L0070 | EN | 27991 | 27987 | 4 / 4 | úplné |
| 146/2023 Z. z. | ELI, HTML | 31994L0063 | SK | 33640 | 33636 | 4 / 4 | úplné |
| 165/2012 Sb. | ELI, HTML | 32009L0028 | CS | 181468 | 181463 | 7 / 7 | úplné |
| 192/2022 Sb. | ELI, HTML | 32009L0104 | CS | 40204 | 40199 | 4 / 4 | úplné |
| 1998/2119/ES | ELI, HTML | 31998D2119 | CS | 18894 | 18890 | 1 / 1 | úplné |
| 1998/2119/ES | ELI, HTML | 31998D2119 | CS | 18894 | 18890 | 1 / 1 | úplné |
| 1999/31/ES | ELI, HTML | 31999L0031 | CS | 61052 | 61048 | 3 / 3 | úplné |
| 1999/45/ES | ELI, HTML | 31999L0045 | CS | 142914 | 142910 | 9 / 9 | úplné |
| 1999/62/ES | ELI, HTML | 31999L0062 | CS | 22289 | 22285 | 2 / 2 | úplné |
| 1999/63/ES | ELI, HTML | 31999L0063 | CS | 15132 | 15128 | 1 / 1 | úplné |
| 1999/70/ES | ELI, HTML | 31999L0070 | CS | 20621 | 20617 | 1 / 1 | úplné |
| 1999/92/ES | CELEX, HTML | 31999L0092 | CS | 23516 | 23516 | 3 / 3 | úplné |
| 1999/92/ES | CELEX, PDF | 31999L0092 | CS | 23369 | 23369 | 3 / 3 | shodné |
| 1999/92/ES [EN] | CELEX, HTML | 31999L0092 | EN | 26322 | 26322 | 3 / 3 | úplné |
| 1999/92/ES [EN] | CELEX, PDF | 31999L0092 | EN | 26028 | 26028 | 3 / 3 | shodné |
| 2000/43/ES | ELI, HTML | 32000L0043 | CS | 19528 | 19524 | 0 / 0 | úplné |
| 2000/54/ES | ELI, HTML | 32000L0054 | CS | 54191 | 54187 | 9 / 9 | úplné |
| 2000/60/ES | ELI, HTML | 32000L0060 | CS | 171621 | 171617 | 11 / 11 | úplné |
| 2000/71/ES | ELI, HTML | 32000L0071 | CS | 6427 | 6423 | 4 / 4 | úplné |
| 2000/78/ES | ELI, HTML | 32000L0078 | CS | 28999 | 28995 | 0 / 0 | úplné |
| 2000/79/ES | ELI, HTML | 32000L0079 | CS | 12321 | 12317 | 1 / 1 | úplné |
| 2000/96/ES | CELEX, HTML | 32000D0096 | CS | 9604 | 9600 | 2 / 2 | úplné |
| 2001/23/ES | ELI, HTML | 32001L0023 | CS | 17984 | 17980 | 2 / 2 | úplné |
| 2001/42/ES | ELI, HTML | 32001L0042 | CS | 27011 | 27007 | 2 / 2 | úplné |
| 2001/86/ES | ELI, HTML | 32001L0086 | CS | 35946 | 35942 | 1 / 1 | úplné |
| 2002/14/ES | ELI, HTML | 32002L0014 | CS | 19436 | 19432 | 0 / 0 | úplné |
| 2002/15/ES | ELI, HTML | 32002L0015 | CS | 19323 | 19319 | 0 / 0 | úplné |
| 2002/253/ES | ELI, HTML | 32002D0253 | CS | 40687 | 40683 | 1 / 1 | úplné |
| 2002/44/ES | ELI, HTML | 32002L0044 | CS | 24480 | 24476 | 1 / 1 | úplné |
| 2002/49/ES | ELI, HTML | 32002L0049 | CS | 42146 | 42142 | 6 / 6 | úplné |
| 2003/17/ES | ELI, HTML | 32003L0017 | CS | 24359 | 24355 | 2 / 2 | úplné |
| 2003/30/ES | ELI, HTML | 32003L0030 | CS | 19510 | 19506 | 0 / 0 | úplné |
| 2003/72/ES | ELI, HTML | 32003L0072 | CS | 40300 | 40296 | 1 / 1 | úplné |
| 2003/88/ES | ELI, HTML | 32003L0088 | CS | 32825 | 32821 | 2 / 2 | úplné |
| 2004/10/ES | ELI, HTML | 32004L0010 | CS | 41557 | 41553 | 3 / 3 | úplné |
| 2004/107/ES | ELI, HTML | 32004L0107 | CS | 37650 | 37645 | 5 / 5 | úplné |
| 2004/113/ES | ELI, HTML | 32004L0113 | CS | 22895 | 22890 | 0 / 0 | úplné |
| 2004/37/ES | ELI, HTML | 32004L0037 | CS | 26040 | 26036 | 5 / 5 | úplné |
| 2004/42/ES | ELI, HTML | 32004L0042 | CS | 24811 | 24807 | 3 / 3 | úplné |
| 2004/54/ES | ELI, HTML | 32004L0054 | CS | 52980 | 52976 | 3 / 3 | úplné |
| 2004/9/ES | ELI, HTML | 32004L0009 | CS | 49322 | 49318 | 3 / 3 | úplné |
| 2005/47/ES | ELI, HTML | 32005L0047 | CS | 15935 | 15930 | 1 / 1 | úplné |
| 2006/118/ES | ELI, HTML | 32006L0118 | CS | 40551 | 40546 | 4 / 4 | úplné |
| 2006/123/ES | ELI, HTML | 32006L0123 | CS | 141433 | 141428 | 0 / 0 | úplné |
| 2006/38/ES | ELI, HTML | 32006L0038 | CS | 49351 | 49346 | 3 / 3 | úplné |
| 2006/54/ES | ELI, HTML | 32006L0054 | CS | 49014 | 49009 | 2 / 2 | úplné |
| 2006/7/ES | ELI, HTML | 32006L0007 | CS | 39046 | 39041 | 5 / 5 | úplné |
| 2006/865/ES | ELI, HTML | 32006R0865 | CS | 178739 | 178734 | 12 / 12 | úplné |
| 2007/46/ES | ELI, HTML | 32007L0046 | CS | 330595 | 330590 | 21 / 21 | úplné |
| 2007/59/ES | ELI, HTML | 32007L0059 | CS | 79283 | 79278 | 7 / 7 | úplné |
| 2007/875/ES | ELI, HTML | 32007D0875 | CS | 3878 | 3873 | 2 / 2 | úplné |
| 2008/104/ES | ELI, HTML | 32008L0104 | CS | 21846 | 21841 | 0 / 0 | úplné |
| 2008/105/ES | ELI, HTML | 32008L0105 | CS | 42440 | 42435 | 3 / 3 | úplné |
| 2008/426/ES | ELI, HTML | 32008D0426 | CS | 71002 | 70997 | 1 / 1 | úplné |
| 2008/50/ES | ELI, HTML | 32008L0050 | CS | 116063 | 116058 | 17 / 17 | úplné |
| 2008/56/ES | ELI, HTML | 32008L0056 | CS | 69848 | 69843 | 6 / 6 | úplné |
| 2008/57/ES | ELI, HTML | 32008L0057 | CS | 127782 | 127777 | 11 / 11 | úplné |
| 2008/96/ES | ELI, HTML | 32008L0096 | CS | 26358 | 26353 | 4 / 4 | úplné |
| 2008/98/ES | ELI, HTML | 32008L0098 | CS | 89517 | 89512 | 5 / 5 | úplné |
| 2009/104/EU | ELI, HTML | 32009L0104 | CS | 40204 | 40199 | 4 / 4 | úplné |
| 2009/126/EU | ELI, HTML | 32009L0126 | CS | 15053 | 15048 | 0 / 0 | úplné |
| 2009/13/EU | ELI, HTML | 32009L0013 | CS | 60947 | 60942 | 1 / 1 | úplné |
| 2009/148/EU | ELI, HTML | 32009L0148 | CS | 29023 | 29018 | 3 / 3 | úplné |
| 2009/177/EU | ELI, HTML | 32009D0177 | CS | 54954 | 54949 | 6 / 6 | úplné |
| 2009/28/EU | ELI, HTML | 32009L0028 | CS | 181468 | 181463 | 7 / 7 | úplné |
| 2009/30/EU | ELI, HTML | 32009L0030 | CS | 94470 | 94465 | 1 / 1 | úplné |
| 2009/31/EU | ELI, HTML | 32009L0031 | CS | 82071 | 82066 | 2 / 2 | úplné |
| 2009/312/EU | ELI, HTML | 32009D0312 | CS | 5443 | 5438 | 1 / 1 | úplné |
| 2009/363/EU | ELI, HTML | 32009D0363 | CS | 4657 | 4652 | 1 / 1 | úplné |
| 2009/38/EU | ELI, HTML | 32009L0038 | CS | 51638 | 51633 | 3 / 3 | úplné |
| 2009/539/EU | ELI, HTML | 32009D0539 | CS | 3750 | 3745 | 0 / 0 | úplné |
| 2009/540/EU | ELI, HTML | 32009D0540 | CS | 2212 | 2207 | 0 / 0 | úplné |
| 2009/547/EU | ELI, HTML | 32009D0547 | CS | 12126 | 12121 | 1 / 1 | úplné |
| 2009/73/ES | ELI, HTML | 32009L0073 | CS | 182809 | 182804 | 2 / 2 | úplné |
| 201/2012 Sb. | ELI, HTML | 32013D0732 | CS | 36321 | 36316 | 1 / 1 | úplné |
| 2010/32/EU | ELI, HTML | 32010L0032 | CS | 22853 | 22848 | 1 / 1 | úplné |
| 2010/40/EU | ELI, HTML | 32010L0040 | CS | 40353 | 40348 | 2 / 2 | úplné |
| 2010/75/EU | ELI, HTML | 32010L0075 | CS | 259403 | 259398 | 10 / 10 | úplné |
| 2011/18/EU | ELI, HTML | 32011L0018 | CS | 15912 | 15907 | 3 / 3 | úplné |
| 2011/92/EU | ELI, HTML | 32011L0092 | CS | 48696 | 48691 | 6 / 6 | úplné |
| 2012/18/EU | CELEX, PDF | 32012L0018 | CS | 107946 | 107946 | 8 / 8 | shodné |
| 2012/18/EU | CELEX, HTML | 32012L0018 | CS | 107000 | 107000 | 7 / 7 | shodné |
| 2012/18/EU [EN] | CELEX, PDF | 32012L0018 | EN | 118798 | 118798 | 8 / 8 | shodné |
| 2012/18/EU [EN] | CELEX, HTML | 32012L0018 | EN | 118019 | 118019 | 7 / 7 | úplné |
| 2012/27/EU | ELI, HTML | 32012L0027 | CS | 181427 | 181422 | 15 / 15 | úplné |
| 2012/34/EU | ELI, HTML | 32012L0034 | CS | 161696 | 161691 | 14 / 14 | úplné |
| 2014/106/EU | ELI, HTML | 32014L0106 | CS | 16837 | 16832 | 2 / 2 | úplné |
| 2014/112/EU | ELI, HTML | 32014L0112 | CS | 26436 | 26431 | 1 / 1 | úplné |
| 2014/34/EU | CELEX, HTML | 32014L0034 | CS | 131226 | 131226 | 12 / 12 | úplné |
| 2014/34/EU | Úř. věstník, PDF | – | – | – | – | – | Cellar nedal soubor |
| 2014/34/EU [EN] | Úř. věstník, PDF | – | – | – | – | – | Cellar nedal soubor |
| 2014/34/EU [EN] | CELEX, HTML | 32014L0034 | EN | 150777 | 150777 | 12 / 12 | úplné |
| 2014/52/EU | ELI, HTML | 32014L0052 | CS | 53197 | 53192 | 2 / 2 | úplné |
| 2014/66/EU | ELI, HTML | 32014L0066 | CS | 72275 | 72270 | 0 / 0 | úplné |
| 2014/67/EU | ELI, HTML | 32014L0067 | CS | 68799 | 68794 | 0 / 0 | úplné |
| 2014/68/EU | CELEX, PDF | 32014L0068 | CS | 230887 | 230887 | 6 / 6 | shodné |
| 2014/68/EU | CELEX, HTML | 32014L0068 | CS | 230242 | 230242 | 6 / 6 | úplné |
| 2014/68/EU [EN] | CELEX, PDF | 32014L0068 | EN | 264633 | 264633 | 9 / 9 | shodné |
| 2014/68/EU [EN] | CELEX, HTML | 32014L0068 | EN | 264189 | 264189 | 6 / 6 | úplné |
| 2014/80/EU | ELI, HTML | 32014L0080 | CS | 8298 | 8293 | 1 / 1 | úplné |
| 2014/94/EU | ELI, HTML | 32014L0094 | CS | 73550 | 73545 | 2 / 2 | úplné |
| 2015/1513/EU | ELI, HTML | 32015L1513 | CS | 94614 | 94609 | 2 / 2 | úplné |
| 2015/1794/EU | ELI, HTML | 32015L1794 | CS | 12720 | 12715 | 0 / 0 | úplné |
| 2015/2193/EU | ELI, HTML | 32015L2193 | CS | 56870 | 56865 | 3 / 3 | úplné |
| 2016/2284/EU | ELI, HTML | 32016L2284 | CS | 81716 | 81711 | 6 / 6 | úplné |
| 2016/2370/EU | ELI, HTML | 32016L2370 | CS | 58560 | 58555 | 0 / 0 | úplné |
| 2016/802/EU | ELI, HTML | 32016L0802 | CS | 52513 | 52508 | 4 / 4 | úplné |
| 2018/1999/EU | ELI, HTML | 32018R1999 | CS | 252444 | 252439 | 13 / 13 | úplné |
| 2018/957/EU | ELI, HTML | 32018L0957 | CS | 33574 | 33569 | 0 / 0 | úplné |
| 2019/1152/EU | ELI, HTML | 32019L1152 | CS | 53241 | 53236 | 0 / 0 | úplné |
| 2019/1158/EU | ELI, HTML | 32019L1158 | CS | 49564 | 49559 | 1 / 1 | úplné |
| 2019/1936/EU | ELI, HTML | 32019L1936 | CS | 40084 | 40079 | 1 / 1 | úplné |
| 2019/520/EU | ELI, HTML | 32019L0520 | CS | 93053 | 93048 | 4 / 4 | úplné |
| 2020/2184/EU | ELI, HTML | 32020L2184 | CS | 165926 | 165921 | 7 / 7 | úplné |
| 2021/1187/EU | CELEX, HTML | 32021L1187 | CS | 34732 | 34727 | 1 / 1 | úplné |
| 2022/2041/EU | ELI, HTML | 32022L2041 | CS | 56363 | 56358 | 0 / 0 | úplné |
| 2022/362/EU | ELI, HTML | 32022L0362 | CS | 122079 | 122074 | 3 / 3 | úplné |
| 224/2015 Sb. | ELI, HTML | 32012L0018 | CS | 107005 | 107000 | 7 / 7 | úplné |
| 24/2006 Z. z. | ELI, HTML | 32001L0042 | SK | 27436 | 27432 | 2 / 2 | úplné |
| 248/2023 Z. z. | ELI, HTML | 32010L0075 | SK | 268377 | 268372 | 10 / 10 | úplné |
| 251/2023 Z. z. | ELI, HTML | 31998L0070 | EN | 27991 | 27987 | 4 / 4 | úplné |
| 254/2001 Sb. | ELI, HTML | 31975L0440 | CS | 14525 | 14521 | 2 / 2 | úplné |
| 258/2000 Sb. | ELI, HTML | 31995L0046 | CS | 68805 | 68801 | 0 / 0 | úplné |
| 262/2006 Sb. | ELI, HTML | 31998L0059 | CS | 12318 | 12314 | 2 / 2 | úplné |
| 266/1994 Sb. | ELI, HTML | 32007L0059 | CS | 79283 | 79278 | 7 / 7 | úplné |
| 309/2006 Sb. | ELI, HTML | 31989L0391 | CS | 26780 | 26776 | 1 / 1 | úplné |
| 311/2006 Sb. | ELI, HTML | 31998L0070 | CS | 27349 | 27345 | 4 / 4 | úplné |
| 350/2011 Sb. | ELI, HTML | 31967L0548 | CS | 10451 | 10447 | 4 / 4 | úplné |
| 364/2004 Z. z. | ELI, HTML | 31991L0271 | SK | 31224 | 31220 | 3 / 3 | úplné |
| 378/2001 Sb. | ELI, HTML | 31989L0655 | CS | 15257 | 15253 | 1 / 1 | úplné |
| 406/2004 Sb. | ELI, HTML | 31999L0092 | CS | 23520 | 23516 | 3 / 3 | úplné |
| 458/2000 Sb. | ELI, HTML | 32019L0692 | CS | 24652 | 24647 | 0 / 0 | úplné |
| 541/2020 Sb. | ELI, HTML | 31986L0278 | CS | 17425 | 17421 | 0 / 0 | úplné |
| 56/2001 Sb. | ELI, HTML | 32018R0858 | EN | 586596 | 586591 | 12 / 12 | úplné |
| COM(2019) 640 | CELEX, HTML | 52019DC0640 | CS | 76622 | 76622 | 0 / 0 | shodné |
| COM(2020) 299 | CELEX, HTML | 52020DC0299 | CS | 70548 | 70548 | 0 / 0 | shodné |
| COM(2020) 301 | CELEX, HTML | 52020DC0301 | CS | 81326 | 81326 | 0 / 0 | shodné |
| COM(2020) 301 [SK] | CELEX, HTML | 52020DC0301 | SK | 83527 | 83527 | 0 / 0 | shodné |
| COM(2020) 301 [SK] | CELEX, PDF | 52020DC0301 | SK | 83499 | 83499 | 0 / 0 | shodné |
| COM(2020) 789 | CELEX, HTML | 52020DC0789 | CS | 81980 | 81980 | 0 / 0 | shodné |
| COM(2021) 550 | CELEX, HTML | 52021DC0550 | CS | 44583 | 44583 | 0 / 0 | shodné |
| COM(2022) 230 | CELEX, HTML | 52022DC0230 | CS | 54502 | 54502 | 0 / 0 | shodné |
| COM(2023) 156 | CELEX, HTML | 52023DC0156 | CS | 45658 | 45658 | 1 / 1 | shodné |
| COM(2023) 62 | CELEX, HTML | 52023DC0062 | CS | 76715 | 76715 | 0 / 0 | shodné |
| COM(2025) 85 | CELEX, HTML | 52025DC0085 | CS | 77470 | 77470 | 0 / 0 | shodné |
| COM(2026) 370 | CELEX, HTML | 52026DC0370 | CS | 53549 | 53549 | 0 / 0 | shodné |
| Nařízení vlády 133/2005 | ELI, HTML | 32008L0057 | CS | 127782 | 127777 | 11 / 11 | úplné |
| UNECE Regulation No. 100 (Revision 2) | CELEX, HTML | 42015X0331(01) | EN | 131624 | 131624 | 18 / 18 | shodné |
| Zákon č. 250/2021 Sb. | ELI, HTML | 32009L0104 | CS | 40204 | 40199 | 4 / 4 | úplné |
| [2019/795] | CELEX, PDF | 42019X0795 | CS | 122898 | 122898 | 5 / 5 | shodné |
| [2019/795] | CELEX, HTML | 42019X0795 | CS | 117848 | 117848 | 5 / 5 | úplné |
| [2019/795] [EN] | CELEX, HTML | 42019X0795 | EN | 119139 | 119139 | 5 / 5 | úplné |
| [2019/795] [EN] | CELEX, PDF | 42019X0795 | EN | 123987 | 123987 | 5 / 5 | shodné |
| url-e809ad20 | ELI, HTML | 31989L0459 | SK | 3790 | 3786 | 0 / 0 | úplné |
| url-edfd3c21 | ELI, HTML | 32001L0042 | SK | 27436 | 27432 | 2 / 2 | úplné |
