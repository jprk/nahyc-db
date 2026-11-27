# Plné texty z EUR-Lexu přes Cellar

Stav k 20.11.2026, větev `feature/mpo-cellar`. Dokument popisuje převod
stahování plných textů aktů EU z webu EUR-Lex na úložiště Cellar Úřadu pro
publikace EU, ověření úplnosti textů z Cellaru a stav po převodu.

## 1. Výchozí stav a důvod změny

EUR-Lex odpovídá automatizovaným klientům výzvou firewallu (HTTP 202
s prázdným tělem). Skript `src/tools/fetch_fulltext.py` ji od 25.10.2026
obcházel: stránku otevřel v headless prohlížeči Chromium (Playwright,
`fetch_with_browser`) a PDF stahoval kontextem prohlížeče poté, co
načetl úvodní stránku webu (`_fetch_eurlex_pdf_with_browser`). Takové
obcházení ochrany proti robotům je nepřípustné. Od 19.11.2026 se
z Cellaru stahovaly adresy s číslem CELEX; adresy ELI (`/eli/…`)
a adresy Úředního věstníku (`?uri=OJ:L_…`) dál šly přes prohlížeč.

Manifest `data/fulltext_manifest.json` k 20.11.2026 obsahoval
505 stažených položek z EUR-Lexu (288 různých souborů). Z nich
266 souborů (476 položek) bylo staženo před 19.11.2026 přímo z EUR-Lexu,
tedy prostým HTTP, nebo — od 25.10.2026 při výzvě firewallu — prohlížečem;
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
v `data/fulltext/` hlavního stromu (u 22 souborů z 19.11.2026, jež
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

* **Selhané položky** (bez souboru, dokument má text z jiné položky); ze čtyř zbývají dvě:
  * nařízení CLP (ES) 1272/2008, `odkaz_eu` (ELI) a dvojče HTML: doplněno
    20.11.2026, odstavec 5.1.
  * REACH (ES) 1907/2006, dvě dvojčata HTML: Cellar české HTML původního
    znění nemá; text původního znění je z PDF (834 tis. znaků, 21 příloh).
    Od 20.11.2026 dokument zobrazuje konsolidované znění z HTML
    (odstavec 7), takže řešení není potřeba.
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

### 5.1 Nařízení CLP (20.11.2026, větev `feature/mpo-normy-clp`)

Obě položky jsme stáhli z Cellaru (`fetch_fulltext.py --only … --out-dir
data/fulltext_mpo_normy_clp`): `odkaz_hlavni_html`
(`…/legal-content/CS/TXT/HTML/?uri=CELEX:32008R1272`) i `odkaz_eu`
(`…/eli/reg/2008/1272/oj/ces`, Cellar jej přeloží na tentýž CELEX) daly
týž soubor `ES_1272_2008__b8cbcaee.html` (české XHTML Úředního věstníku,
23 MB). Volba `--out-dir` ukládá soubor do adresáře ve worktree, manifest
jej vede jako `data/fulltext/<název>`, kam se po mergi zkopíruje.

**Které znění.** Adresy záznamu (PDF, HTML i ELI `…/oj`) vedou na původní
znění nařízení vyhlášené v Úředním věstníku L 353 z 31.12.2008 (CELEX
`32008R1272`), nikoli na konsolidované znění. Stažený text tedy neobsahuje
pozdější změny (adaptace na technický pokrok a další novely). Cellar vede
konsolidovaná znění `02008R1272-<datum>`; ke 20.11.2026 je účinné znění
ze 01.07.2026 (`02008R1272-20260701`) a připraveno je znění k 01.01.2027.
Uživatel 20.11.2026 rozhodl zobrazovat aktuální konsolidované znění
a původní znění ponechat jako nahrazenou verzi (odstavec 7).

**Převod extraktorem.** `extract_fulltext.py` převede XHTML na čitelný text
za 30 s s nejvyšší spotřebou paměti 0,8 GB (BeautifulSoup nad 23 MB); výsledek
má 2,52 mil. znaků, 7 příloh a 528 tabulek, vyčištěné HTML 4,2 MB. Úplnost
jsme ověřili proti textu z PDF: oba texty obsahují všech 3 068 indexových
čísel látek přílohy VI a všech 7 příloh. Při převodu jsme opravili jednu
chybu extraktoru: odstavce v jedné buňce tabulky splývaly v prostém textu
(„Flam. Gas 1Press. Gas“, „GHS02GHS04Dgr“); nyní jsou odděleny mezerou.
Oprava se týká všech textů s tabulkami a projeví se po novém běhu
`extract_fulltext.py --apply`.

**HTML, nebo PDF.** Čitelný text dokumentu (stránka „text“ a fulltextové
vyhledávání) se nově tvoří z HTML, PDF zůstává staženým originálem
dokumentu (`Document.file_path`). Postupujeme tak stejně jako u ostatních
aktů EU, u nichž máme PDF i HTML (`fetch_fulltext.html_alternative`,
`extract_fulltext.clean_name_source`). Důvody:

* text z PDF obsahuje 9 886 slov rozdělených na konci řádku („Chro- nic“,
  „nebez- pečnosti“), text z HTML 50 (jde o skutečné spojovníky);
* tabulky přílohy VI mají v PDF záhlaví zopakované na každé stránce (1 012×),
  v HTML jednou na tabulku;
* HTML nese strukturu aktu (články, body, poznámky pod čarou) a tabulky
  jako tabulky, nikoli jako řádky rekonstruované z polohy textu na stránce;
* text z HTML je o 0,29 mil. znaků kratší právě o tyto artefakty, obsah je
  shodný (indexová čísla, přílohy).

PDF ponecháváme jako soubor ke stažení: je to obraz vyhlášeného Úředního
věstníku a návštěvník jej může potřebovat k citaci stránky.

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
(s přílohami). Mezi druhým a posledním krokem stránky dotčených dokumentů
krátce nenabízejí text; kroky proto spouštíme bezprostředně po sobě.

Nařízení CLP (odstavec 5.1) přidává před `prune_fulltext.py` jeden soubor:

```
cp -n .claude/worktrees/mpo-normy-clp/data/fulltext_mpo_normy_clp/ES_1272_2008__b8cbcaee.html data/fulltext/
```

`Document.file_path` se nemění (PDF), `extract_fulltext.py --apply`
přepíše vyčištěný text `data/fulltext_clean/ES_1272_2008__1fe6eaaa.*`
textem z HTML.

Konsolidovaná znění CLP a REACH (odstavec 7) přidávají před
`prune_fulltext.py` dva soubory a před `extract_fulltext.py` zápis verzí:

```
cp -n .claude/worktrees/mpo-konsolidace/data/fulltext_mpo_konsolidace/*.html data/fulltext/
.venv/bin/python src/tools/backup_db.py --reason before_eu_consolidations
.venv/bin/python src/tools/refresh_eu_consolidations.py           # suchý běh
.venv/bin/python src/tools/refresh_eu_consolidations.py --apply
```

## 7. Konsolidovaná znění (CLP, REACH; 20.11.2026, větev `feature/mpo-konsolidace`)

**Rozhodnutí.** U nařízení CLP (ES) č. 1272/2008 a REACH (ES) č. 1907/2006
zobrazujeme aktuální konsolidované znění a obnovujeme je při každé změně;
původní znění nemažeme, zůstává u dokumentu jako nahrazená verze
(rozhodnutí uživatele z 20.11.2026, `doc/MPO_PRIPOMINKY.md`, odstavec 5.1).

**Zjištění v Cellaru.** Konsolidované znění je v Cellaru samostatné dílo
(typ `CONS_TEXT`, CELEX sektoru 0 s datem, například `02008R1272-20260701`),
s původním aktem je spojeno vlastností `act_consolidated_based_on_resource_legal`
a den, od něhož se znění použije, nese `act_consolidated_date`. Dotaz SPARQL
(`src/sites/eurlex.py: consolidated_versions`) vrací znění, jež má Cellar
v jazyce dokumentu, včetně znění připravených s budoucí účinností.
Ke 20.11.2026:

| Akt | Původní znění | Konsolidovaných znění v češtině | Účinné k 20.11.2026 | Budoucí |
|---|---|--:|---|---|
| CLP | `32008R1272`, Úř. věst. L 353, 31.12.2008, účinnost 20.01.2009 | 31 (01.12.2010 až 01.01.2027) | `02008R1272-20260701` | `02008R1272-20270101` |
| REACH | `32006R1907`, Úř. věst. L 396, 30.12.2006, účinnost 01.06.2007 | 69 (23.11.2007 až 22.06.2026) | `02006R1907-20260622` | žádné |

Znění CLP `02008R1272-20090120` (ke dni účinnosti původního znění) Cellar
v češtině nemá; jde o obsah původního znění, a proto je nevedeme.

**Model v databázi.** Každé znění je verzí (`DocumentVersion`) jediného
dokumentu aktu; dokument, jeho označení a trvalá adresa se nemění:

* **Původní znění** — verze 1 s označením „původní znění (Úř. věst. L 353,
  31.12.2008)“, dnem účinnosti, uloženým textem (`file_path`: PDF, jehož
  čitelný text je u CLP z HTML) a odkazem na stránku aktu v EUR-Lexu
  (`DocumentVersion.url`); stav „nahrazený“.
* **Konsolidovaná znění** — verze 2 a další v pořadí dat, s označením
  „konsolidované znění ke dni 01.07.2026“, datem a odkazem na stránku
  znění v EUR-Lexu (`…/legal-content/CS/TXT/?uri=CELEX:02008R1272-20260701`).
  Znění účinné k danému dni je aktuální verzí (stav „účinný“), starší znění
  jsou „nahrazená“, znění s budoucím datem „vyhlášené, dosud neúčinné“.
* **Zobrazený text** (`Document.file_path`) je nejnovější účinné znění, jehož
  text máme; stahujeme jen text aktuálního znění (z Cellaru, české XHTML,
  položka manifestu `konsolidace_<RRRRMMDD>`). Text dříve aktuálního znění
  zůstává u jeho verze, starší konsolidovaná znění odkazují jen do EUR-Lexu.

Všechna historická znění vedeme jako verze proto, aby stránka dokumentu
nabízela úplnou historii s odkazy a aby se další znění jen připisovala.
Model jsme převzali od vydání norem (`norm_editions.py`), jež také vedou
nahrazená vydání jako verze; odlišný je jen zdroj (Cellar místo katalogu
ČSN) a to, že se mění zobrazený text. Nevýhodou je počet verzí (CLP 32,
REACH 70); stránka dokumentu proto starší nahrazená znění sbaluje.

**Stránka dokumentu.** Panel „Verze“ uvádí, které znění se zobrazuje
(„Zobrazený text: konsolidované znění ke dni 01.07.2026“), u každé verze
odkaz do EUR-Lexu a u verzí s uloženým textem odkaz „náš text“
(`/dokument/<slug>/verze/<číslo>/text`). Původní, aktuální a budoucí znění
jsou vidět vždy, ostatní znění jsou v rozbalovacím seznamu „Starší znění“.
Stránka čitelného textu uvádí, o které znění jde.

**Obnova při každé změně.** `refresh_eu_consolidations.py` (denně,
plánovač `scheduled_harvest.sh daily`, a 1. den v měsíci po promítnutí
stavů):

1. zjistí v Cellaru konsolidovaná znění aktů ze seznamu
   `data/eu_consolidated_acts.json` a uloží je do
   `data/eu_consolidation_cache.json` (při chybě dotazu ponechá dosavadní);
2. v den účinnosti nového znění chybí-li jeho text, stáhne jej z Cellaru
   (`fetch_fulltext.fetch_one`, nikoli z EUR-Lexu) a vytvoří čitelný text
   (`extract_fulltext.py`);
3. zapíše verze (`eu_consolidations.apply`): nové znění se stane aktuální
   verzí, dosavadní nahrazenou, zobrazený text se přepne na nový.

Totéž promítnutí verzí (bez Cellaru a stahování) provádí
`backfill_document_states.py` a sestavení databáze `init_db.py`.
Přestavba z JSON tak výsledek zachová: Seznam aktů, mezipaměť znění
a manifest stažených textů jsou datové soubory pod správou verzí
(`init_db.resolve_file_path` dává aktům ze seznamu text účinného znění).
Akt, jejž kontrola platnosti vede jako zrušený, se nemění.

**Ověření úplnosti stažených textů:**

| Akt | Znění | Soubor | Velikost | Znaky textu (bez mezer) | Přílohy | Články |
|---|---|---|--:|--:|---|--:|
| CLP | `02008R1272-20260701` | `ES_1272_2008__2d5ccccc.html` | 28,4 MB | 1 812 593 (99,3 % textu souboru) | I až VIII | 1 až 62 |
| REACH | `02006R1907-20260622` | `ES_1907_2006__0a76c85e.html` | 4,9 MB | 917 399 (98,2 %) | I až XVII | 1 až 141 |

Cellar vrací obě znění jako jediný soubor (žádné další položky `DOC_n`).
Čitelný text CLP obsahuje 4 018 indexových čísel látek přílohy VI
(původní znění 3 068; přibyly harmonizované klasifikace z adaptací na
technický pokrok) a je kratší než text původního znění (2,27 mil. znaků
proti 2,94 mil.), protože tabulka 3.2 přílohy VI byla zrušena. Převod
extraktorem trvá 34 s pro oba soubory.

**Další akty.** Mechanismus se zapne přidáním položky do
`data/eu_consolidated_acts.json`. Hodí se pro akty měněné tak často, že
původní znění čtenáře zavádí. Z aktů, jež databáze má v češtině s textem,
navrhujeme (k rozhodnutí uživatele): směrnici RED II (EU) 2018/2001 (#106,
podstatně změněna směrnicí (EU) 2023/2413, jež zavádí cíle pro obnovitelná
paliva nebiologického původu včetně vodíku), nařízení AFIR (EU) 2023/1804
(#81, plnicí stanice vodíku), nařízení TEN-E (EU) 2022/869 (#80), nařízení
o schvalování typu motorových vozidel (EU) 2018/858 (#89) a směrnici
Seveso III 2012/18/EU (#110); méně často měněné směrnice 2014/68/EU (#107)
a 2014/34/EU (#108) stačí ponechat v původním znění. Před zapnutím je třeba
ověřit, že označení dokumentu se shoduje se seznamem a že Cellar vede
konsolidovaná znění aktu v češtině (suchý běh `refresh_eu_consolidations.py`
to ukáže).

## 8. Tabulka ověření

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
