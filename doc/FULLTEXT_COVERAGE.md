# Pokrytí plnými texty — audit k 2026-10-25

Účel: zjistit, u kterých dokumentů databáze nemáme text, vyřadit normy (k nim přístup
nemáme a nemáme ho mít, viz `DocumentType.restricted_fulltext`, R4.1), a u zbytku
ověřit, že texty máme opravdu všechny a že jsou ty správné. Dokument zapisuje zjištění
a doporučený postup; řešení jednotlivých položek je vždy samostatné rozhodnutí.

## 1. Shrnutí

| | dokumentů |
|---|---|
| celkem v databázi `h2regdocs` | 1 462 |
| **normy** (`Norma`, omezený typ — text se nestahuje) | 1 226 (1 219 bez souboru; 7 má soubor uložený dřív, aplikace ho neposkytuje) |
| ostatní (neomezené) typy | **236** |
| … z nich **má soubor** | **199** |
| … z nich **nemá soubor** | **37** |

**Odpověď na otázku „máme všechny ostatní texty?“: ne.** Chybí 37 dokumentů (oddíl 4).
Dalších 124 dokumentů má soubor, ale **v jiném jazyce, než jaký dokument uvádí**
(oddíl 5.3), a u jednoho (CLP nařízení) existuje jen PDF bez čitelného textu.

## 2. Postup

1. Seznam dokumentů bez `file_path` z databáze, vyřazení typů s `restricted_fulltext = 1`.
2. U každého zbylého: z databáze název, zdroj (`zdroj_dat`), jazyk, adresa; ze zdrojové
   tabulky (`data/20250712_Sinay/sinay_zakony_processed.json`, `database_merged_raw.json`)
   příbuzné záznamy; zkouška stažitelnosti každé adresy (bez ukládání): prosté HTTP pro
   běžné weby, headless Chromium pro EUR-Lex a Slov-Lex (jejich firewall / SPA); u PDF kontrola
   `%PDF-` a velikosti; u HTML kontrola, že jde o text aktu (`fetch_fulltext.is_document_page`).
3. U 199 dokumentů se souborem: (a) soubor existuje; (b) pochází z položky manifestu
   **vlastního zdroje a označení** dokumentu; (c) existuje vyčištěný text a obsahuje číslo
   a rok dokumentu; (d) jazyk textu odpovídá sloupci `language`.

## 3. Normy

Vyřazeny podle `DocumentType.restricted_fulltext = 1`. Není to chyba pokrytí: text norem je
placený a chráněný autorským právem (viz `src/tools/fetch_fulltext.py`, `is_norm_designation`).
Sedm norem má v `file_path` soubor z dřívějška; aplikace ho neposkytuje (`/fulltext/<id>`
vrací 403). Je to rozpor vůči duchu R4.1 jen ve smyslu uložené kopie na disku, ne zveřejnění.

## 4. Dokumenty bez souboru (37)

Přehled podle příčiny a nálezu. Čísla `#` jsou `Document.id`.

### 4.1 Slovenské jazykové varianty aktů EU (#57, #78, #84, #88)

Záznamy z `Sinay_Zakony`, které jsou slovenským protějškem aktu EU (viz
`doc/PLAN.md` §15, jazykové varianty jako samostatné dokumenty). Zdrojová data jim dala
adresu, která nevede na text, nebo žádnou.

| # | co to je | adresa ve zdroji | nález |
|---|---|---|---|
| 57 | SK varianta prováděcího rozhodnutí (EU) 2022/2427 (BAT, #58); název „Slov-Lex“ je zástupný | `slov-lex.sk/…/ZZ/2022/2427/` — Slov-Lex takový předpis nemá (stránka bez textu) | Slovenské znění je na EUR-Lexu: `…/legal-content/SK/TXT/HTML/?uri=CELEX:32022D2427` (ověřeno, text se vykreslí, 535 KB) |
| 78 | SK varianta sdělení Komise COM(2020) 301 „Vodíková stratégia pre klimaticky neutrálnu Európu“ (#79); název „Slov-Lex“ je zástupný | `slov-lex.sk/…/ZZ/2021/587/` — neexistuje | SK znění na EUR-Lexu: `…/SK/TXT/HTML/?uri=CELEX:52020DC0301` (nezkoušeno; dokumenty COM bývají PDF/XHTML) |
| 84 | SK varianta směrnice (EU) 2024/1788 (#104); bez označení, bez adresy | žádná | SK znění: `…/SK/TXT/HTML/?uri=CELEX:32024L1788` (ověřeno, 1 MB) |
| 88 | SK/EN varianta nařízení (EU) 2018/858 (#89), označení `2018/858/ES`, název „Smernica 2018/858/ES“ (je to nařízení) | žádná | SK znění: `…/SK/TXT/HTML/?uri=CELEX:32018R0858` (ověřeno, 3 MB). Navazuje na ně vztah z českého zákona 56/2001 Sb. (#69) |

Doporučení: doplnit tyto adresy jako opravy zdroje (`data/fulltext_url_overrides.json`
neumí dokument bez označení, viz 7.1). Názvy „Slov-Lex“ (#57, #78) jsou zástupné a
patří mezi vady R1.7 (zástupný název).

### 4.2 Slovenské předpisy se Slov-Lex adresou, bez označení (#65, #67, #68, #70, #71, #99)

Dokumenty bez `identifier` (slug `doc-…`), proto je manifest (klíč podle označení) nezná.
Adresy jsou **stažitelné a vedou na správný předpis** (ověřeno názvem stránky):

| # | předpis | adresa | stažitelnost |
|---|---|---|---|
| 65 | 128/2015 Z. z. (závažné průmyslové havárie) | `…/SK/ZZ/2015/128/` | ano, 1,2 MB, text se vykreslí |
| 67 | 309/2009 Z. z. (obnovitelné zdroje) | `…/SK/ZZ/2009/309/` | ano, 2,6 MB |
| 68 | 271/2011 Z. z. (kritériá udržateľnosti — biopalivá) | `…/SK/ZZ/2011/271/` | **ano po opravě** — viz níže |
| 70 | 214/2021 Z. z. (ekologické vozidlá) | `…/SK/ZZ/2021/214/` | ano, 0,3 MB |
| 71 | 134/2018 Z. z. (prevádzka vozidiel) | `…/SK/ZZ/2018/134/` | ano, 1,3 MB |
| 99 | 124/2006 Z. z. (BOZP) | `…/SK/ZZ/2006/124/` | ano, 1,4 MB |

**Nalezená chyba stahování (opraveno v tomto PR):** u předpisu bez platného znění
(271/2011 je novelizován) Slov-Lex ukáže „História predpisu“ a stahování otevíralo
*poslední odkaz v řádku historie*. Tím byl odkaz ve sloupci „Novela“ (novelizující předpis
68/2023 Z. z.), ne verze předpisu. `_slovlex_latest_version_url` teď bere jen sloupec verzí
(`td.title`); 271/2011 se stáhne jako sám a extrahuje (37 KB textu).

### 4.3 Chybně namapované záznamy a duplicity (#62, #1222, #92, #79)

* **#62 `2010/75/EU`** — slovenské *oznámení* Ministerstva dopravy (`75/2010 Z. z.`) se
  zdrojovou značkou, která je shodná s označením směrnice o průmyslových emisích.
  Zdrojová tabulka přiřadila slovenskému oznámení omylem číslo směrnice. **Při dřívějším
  doplňování cest jsem mu omylem přiřadil soubor s textem směrnice 2010/75/EU** (hledání
  jen podle označení, bez ohledu na zdroj). Zjištěno tímto auditem; cesta byla v databázi
  vyčištěna a `sync_fulltext_paths.py` nyní bere jen položky manifestu vlastního zdroje
  dokumentu (test `OwnSourceTestCase`). Co ten záznam správně je, určuje zdroj; text
  slovenského oznámení by dal Slov-Lex `…/SK/ZZ/2010/75/`.
* **#1222** — směrnice 2010/75/EU o průmyslových emisích (CS, bez označení). Adresa
  `eli/dir/2010/75/oj` je stažitelná (1,8 MB). Doporučení: dát záznamu označení
  `2010/75/EU` (teď ho nese #62) a text mu přiřadit.
* **#92 `(EHK OSN) č. 134`** — duplicita záznamu #139 `[2019/795]` (předpis EHK OSN
  č. 134, `doc/PLAN.md` §13); #139 už má stažený PDF. Adresa z EUR-Lexu
  (`CELEX:42019X0795`) je sama stažitelná (2,6 MB). Doporučení: sloučit záznamy, nebo
  mu přiřadit soubor #139.
* **#79** — české znění sdělení COM(2020) 301 (adresa ve zdroji je anglická). Anglická
  stránka je stažitelná (301 KB). Adresa `…/legal-content/CS/TXT/HTML/?uri=CELEX:52020DC0301`
  vrací jen odkaz na soubor `.docx`, tedy jako HTML nepoužitelná; české znění by vyžadovalo
  jiný formát.

### 4.4 Mezinárodní předpisy (#119, #120, #121)

| # | dokument | nález |
|---|---|---|
| 119 | ADR 2025 (UNECE) | **nelze stáhnout automaticky**: `unece.org` i přímé PDF vrací HTTP 403 (Cloudflare „Just a moment…“) i headless prohlížeči. Zbývá ruční stažení z `https://unece.org/sites/default/files/2025-01/2412006_E_ECE_TRANS_352_Vol.I_WEB_0.pdf`. Ministerstvo dopravy má vlastní stránku „Dohoda ADR 2025“ (`md.gov.cz/Zivotni-situace/Silnicni-doprava/Nakladni-doprava-(1)/Preprava-nebezpecnych-veci-dohoda-adr/Dohoda-ADR-2025`, nezkoumáno). |
| 120 | RID 2025, české znění (md.gov.cz) | adresa ve zdroji je **mrtvá** (404). Nová adresa nalezena na stránce ministerstva: `https://md.gov.cz/getattachment/Dokumenty/Drazni-doprava/Preprava-nebezpecnych-veci-drazni-dopravou/Preprava-nebezpecnych-veci-Obecne-informace/RID-2025.pdf.aspx` — PDF, 36 MB, stažitelné. |
| 121 | RID 2025, anglické znění (OTIF) | adresa ve zdroji **funguje**: PDF 14,8 MB. |

### 4.5 Strategie, studie a metodiky (#1240–#1259, 20 dokumentů)

Z importů `MPO_Hydrogen_Strategy` a `HYTEP` (+ jeden z `cistadoprava.cz`), bez označení
(slug `doc-…`). **Všechny adresy jsou stažitelné** a vedou na PDF (ověřeno hlavičkou
`%PDF-` a velikostí): #1240–#1241 (MPO), #1242–#1253, #1255–#1259 (HYTEP), #1254
(NAHYC DP010). Velikosti 0,1–7,9 MB, výjimka #1259 (případová studie elektrolyzéru)
**39,6 MB**. Pro čitelný text by bylo potřeba extrahovat text z PDF (nemají HTML dvojníka,
na rozdíl od PDF z EUR-Lexu).

### 4.6 Nepodařilo se / nelze

* #119 ADR 2025 — Cloudflare, ruční stažení (4.4).
* Žádný jiný dokument ze 37 není nestažitelný: u všech byl nalezen odpovídající zdroj
  nebo je adresa funkční. (#62 a #92 jsou věcně chybné/duplicitní záznamy, ne chyby stahování.)

## 5. Kontrola dokumentů se souborem (199)

### 5.1 Správný dokument

U všech 206 dokumentů, které měly soubor před tímto auditem (199 neomezených + 7 norem),
byla ověřena shoda zdroje a označení s položkou manifestu. **Jediná chyba: #62** (4.3),
opravena; u ostatních 205 souhlasí zdroj i označení.

### 5.2 Text existuje a obsahuje označení

197 z 199 (stav při auditu, před doplněním #1455, jehož vyčištěný text vznikne až při příštím
`extract_fulltext.py --apply`) má vyčištěný text a v jeho začátku se objeví číslo a rok
dokumentu. Zbývají dva:
* **#1220 `(ES) 1272/2008` (CLP)** — EUR-Lex vydává jen PDF (HTML vrací prázdnou stránku
  i na adrese CELEX); PDF je stažené, **čitelný text neexistuje**.
* #50 `24/2006 Z. z.` — heuristika selhala (zákon z prosince 2005, číslo 24/2006): falešný poplach.

### 5.3 Jazyk textu (zjištěno tímto auditem)

| sloupec `language` | jazyk textu | dokumentů |
|---|---|---|
| CS | CS | 40 |
| **CS** | **EN** | **123** |
| EN | EN | 17 |
| EN | CS | 1 (#108 `2014/34/EU`) |
| SK | SK | 16 |

**123 dokumentů označených jako české má anglický text** (EU akty, jejichž adresa je
`eur-lex.europa.eu/eli/<typ>/<rok>/<číslo>/oj` bez jazyka; EUR-Lex pak vydá EN a parametr
`?lang=CS` ignoruje). Řešení je ověřené: adresa **s jazykovou příponou** `…/oj/ces` (česky),
`…/oj/slk` (slovensky) vrací český/slovenský text a extraktor ho čte (zkoušeno na
2022/869, 2010/75 a 1999/31). Doporučení: stahovat EU akty v jazyce dokumentu
(`ces`/`slk`/`eng` podle `language`) a stávající anglické texty nahradit; u PDF je
`…/CS/TXT/…` v adrese už česky.

## 6. Opravy provedené při auditu

* **Databáze:** `#62` zbaven chybně přiřazeného souboru; `#1455` (`1998/2119/ES`, stažitelné,
  jen nebylo staženo) dostal soubor `data/fulltext/1998_2119_ES__de568c03.html`.
* **Kód:** `sync_fulltext_paths.py` bere jen položky manifestu vlastního zdroje dokumentu
  (`resolve_by_identifier(..., sources)`); `fetch_fulltext._slovlex_latest_version_url` bere
  jen sloupec verzí (ne odkazy na novelizující předpisy). Testy v `tests/`.

## 7. Doporučený postup (rozhodnutí na uživateli)

1. **Dokumenty bez označení** (33 ze 37: #57, #65, #67, #68, #70, #71, #78, #79, #84, #99,
   #120, #121, #1222, #1240–#1259; označení mají jen #62, #88, #92, #119): manifest klíčuje
   podle označení, proto je nelze stahovat. Je potřeba klíč podle adresy a úprava
   `init_db.resolve_file_path` (nebo jim označení doplnit — u #1222 a slovenských předpisů
   je odvoditelné).
2. **Jazyk EU aktů** (5.3): znovu stáhnout 123 dokumentů v češtině přes `…/oj/ces`.
3. **Duplicity a chybná čísla:** #62 / #1222 (označení `2010/75/EU`), #92 / #139,
   zástupné názvy „Slov-Lex“ (#57, #78).
4. **PDF strategií a studií** (#1240–#1259): stáhnout originály; čitelný text až po
   rozhodnutí o extrakci z PDF.
5. **ADR 2025 (#119):** ruční stažení.

## 8. Jak audit zopakovat

* Dokumenty bez souboru: `SELECT d.id, d.identifier, d.title, d.url FROM Document d JOIN
  DocumentType dt ON dt.id = d.type_id WHERE dt.restricted_fulltext = 0 AND d.file_path IS NULL`.
* Jazyk textu: porovnat `Document.language` s převažující abecedou a slovy v
  `data/fulltext_clean/<soubor>.txt` (angličtina: slova *the, of, shall*; čeština: znaky
  `ěřů`; slovenština: `ľĺŕôä`).
* Shoda zdroje: pro každý `file_path` najít v `data/fulltext_manifest.json` položku se stejným
  `local_path` a porovnat její zdroj (`<zdroj>|<označení>|<pole>`) se `Document.zdroj_dat`.
