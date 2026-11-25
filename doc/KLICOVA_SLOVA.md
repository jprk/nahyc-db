# Klíčová slova dokumentů

Stav k 23. 11. 2026, větev `feature/keywords`.

## 1. Výchozí stav

Databáze dosud nemá u žádného dokumentu seznam klíčových slov, který by popisoval jeho obsah.
Tabulka `Keyword`/`DocumentKeyword` (1163 dokumentů) nese kategorie převzaté ze zdrojových
rešerší: u rešerše Sinay jde o 264 názvů skupin typu „Verflüssigung“ nebo „Untertage Gasspeicher“,
rešerše Prokop má v poli všude „-“ a rešerše Haltuf toto pole nemá. Anotace norem (838 z 1226)
obsahují úvodní větu normy z katalogu, klíčová slova v nich nejsou. Tabulku `Keyword` proto
ponecháváme beze změny (slouží jako filtr „štítků“ v katalogu) a klíčová slova vedeme odděleně.

## 2. Zdroje klíčových slov

Klíčová slova získáváme ze čtyř zdrojů. U každého slova evidujeme původ, aby uživatel i editor
rozlišili úřední indexaci od odvozené.

| Původ (`origin`) | Zdroj | Dokumenty | Spolehlivost |
|---|---|---|---|
| `eurovoc` | deskriptory tezauru EuroVoc, které aktům EU přiděluje Úřad pro publikace EU (Cellar, `cdm:work_is_about_concept_eurovoc`), česky i anglicky | akty EU | úřední |
| `ics` | třídník ICS normy podle jejího českého převzetí v katalogu ČAS (`csnonline.agentura-cas.cz`, stránka „Detail normy“), s českými názvy tříd | evropské a mezinárodní normy s českým převzetím | úřední, hrubé třídění |
| `cas` | deskriptory a klíčová slova ČSN z téhož katalogu ČAS | část norem s českým převzetím | úřední |
| `model` | 5–10 českých klíčových slov, která odvodí jazykový model z názvu, anotace a začátku plného textu | všechny dokumenty kromě aktů EU s EuroVoc | odvozené, neověřené |

Normy ISO bez českého převzetí dostávají ICS z otevřených dat ISO (ISO Open Data, soubor
`iso_deliverables_metadata.jsonl` na úložišti ISO, týdně aktualizovaný; `iso_open_data.py`). Stránky
iso.org a iec.ch automatické klienty odmítají (HTTP 403), otevřená data ale ISO zveřejňuje právě pro
strojové zpracování. Obsahují i anglický název, anotaci, technickou komisi a stav vydání, které
využívá kontrola záznamů (`doc/KONTROLA_ZAZNAMU.md`). České názvy tříd ICS přebíráme z tříd, které
už známe z katalogu ČAS.

Normu ISO, EN nebo IEC hledáme v katalogu ČAS pod jejím mezinárodním označením
(„STN EN ISO 6145-11/ - 2009.02“ → „EN ISO 6145-11“). Třídník ICS je u všech národních převzetí
téže normy shodný, proto ho z ČSN přebíráme i ke slovenskému, německému nebo původnímu vydání.
Národní normy bez evropského či mezinárodního protějšku (DVGW, DIN, VDI, ASTM, SAE, EIGA, CGA)
v katalogu ČAS nejsou a třídník ICS z něj nedostanou.

## 3. Výsledky (23. 11. 2026, živá databáze 1506 dokumentů)

| Původ | Dokumenty | Poznámka |
|---|---|---|
| EuroVoc | 173 ze 174 aktů EU (po opravě odstavce 3.2) | průměrně 7 deskriptorů; bez deskriptorů zůstává #62 (slovenské oznámení vedené pod označením 2010/75/EU) |
| ICS | 729 ze 797 evropských a mezinárodních norem | 578 z katalogu ČAS, 151 norem ISO bez českého převzetí z otevřených dat ISO; zbývá 68 norem hlavně IEC, CEN a EN bez českého převzetí |
| deskriptory ČAS | 31 norem | katalog je uvádí jen u části ČSN; kódy, které katalog u některých ČSN uvádí místo slov („BL/BY“, „KNX.C“), vynecháváme |
| model | 1334 z 1334 dokumentů (všechny kromě 172 aktů s EuroVoc) | gpt-5.5, průměrně 7,7 slova (u 20 dokumentů jen s názvem 3–4); cena celé dávky 7,92 USD, s porovnáním modelů a doplňky asi 8,2 USD |

### 3.1 Výběr modelu

Na stejných 20 normách jsme porovnali pět modelů OpenAI. Malé modely (gpt-4o-mini, gpt-4.1-mini,
gpt-5.4-mini) dělaly pravopisné chyby a ponechávaly anglická slova („vodíkové embrittlement“,
„pozemsní vozidla“, „netlakové materiály“ místo „nekovové“). Model gpt-4.1 psal čistě, gpt-5.5
navíc volil přesnější odborné termíny („křehnoucí plyn“, „svazek lahví“, „tlakový sud“,
„PEM elektrolyzér“). Uživatel upřednostnil kvalitu, proto používáme gpt-5.5 (cena podle ceníku
OpenAI 5 USD za milion vstupních a 30 USD za milion výstupních tokenů).

Model dostává jen veřejné údaje: označení, typ, jazyk, název, anotaci (nejvýše 2000 znaků)
a začátek vyčištěného plného textu (nejvýše 5000 znaků). Pokyny mu ukládají psát klíčová slova
česky bez ohledu na jazyk dokumentu, v prvním pádě, bez obecných slov typu „norma“ či „požadavky“
a jen z předaných údajů. U norem, k nimž máme jen název, vrací méně klíčových slov.

### 3.2 Kontrola názvů aktů EU

Úřední názvy všech 174 aktů z Cellaru jsme porovnali s názvy v databázi (ve stejném jazyce).
U dvou dokumentů název neodpovídá číslu aktu:

| Dokument | Označení | Název v databázi | Akt s tímto číslem |
|---|---|---|---|
| #86 | (EU) 2023/955 | nařízení o vnitřním trhu s obnovitelnými plyny a zemním plynem (to je nařízení (EU) 2024/1789) | nařízení, kterým se zřizuje Sociální klimatický fond |
| #91 | (EU) 2021/535 | nařízení, kterým se mění nařízení (ES) č. 1881/2006 (limity ochratoxinu A) | prováděcí nařízení k nařízení (EU) 2019/2144 o schvalování typu motorových vozidel |

Obě chyby vznikly stejně: tabulka rešerše Sinay uvádí jen číslo aktu („(EÚ) 2021/535 | áno | MD SR“)
a český název s popisem k němu doplnil jazykový model (`process_laws.py`). Opravy podle rozhodnutí
uživatele (23. 11. 2026) jsou v `data/manual_corrections.json`: #86 slučujeme do (EU) 2024/1789 (#105),
#91 dostal úřední název z Cellaru a nový popis (akt obsahuje požadavky na vozidla s vodíkovým pohonem,
příloha XIV). Systematickou kontrolu dalších záznamů popisuje `doc/KONTROLA_ZAZNAMU.md`.

## 4. Uložení

Klíčová slova má po nahrání všech zdrojů všech 1506 dokumentů (zkušebně v `h2regdocs_test`).

Tabulka `DocumentTerm` (vzniká automaticky při prvním zápisu, `document_terms.ensure_schema()`):

| Sloupec | Význam |
|---|---|
| `document_id` | dokument (cizí klíč, při smazání dokumentu se smaže i slovo) |
| `origin` | `eurovoc`, `ics`, `cas`, `model` |
| `code` | kód deskriptoru EuroVoc nebo třídy ICS |
| `term` | klíčové slovo česky; u ICS „kód název“ |
| `term_en` | anglický tvar (EuroVoc) |
| `position` | pořadí ve zdroji (model řadí od nejdůležitějšího) |

Stažené a odvozené údaje držíme v mezipaměti pod správou verzí, klíčované označením dokumentu
(u dokumentu bez označení `url-<hash adresy>`; sdílí-li adresu více dokumentů bez označení, jako 14 letáků
BVEG pod `https://www.bveg.de/`, pak `title-<hash názvu>`), aby přežily přestavbu databáze:
`data/eurovoc_cache.json`, `data/ics_cache.json`, `data/keyword_model_cache.json`.
`init_db.py` tabulku při přestavbě vyprázdní a `document_terms.py --apply` ji z mezipamětí naplní znovu.

## 5. Webové rozhraní

- Stránka dokumentu má panel „Klíčová slova“ se skupinami podle původu a vysvětlivkou ke každé
  skupině; slova odvozená modelem označujeme jako neověřená. Každé slovo odkazuje na vyhledání
  v katalogu (u ICS hledáme název třídy). U deskriptorů EuroVoc ukazuje anglický tvar bublina.
- Fulltextové vyhledávání v katalogu prohledává i klíčová slova (včetně synonym vyhledávání).
  Dokud tabulka `DocumentTerm` v databázi není, aplikace se chová jako dosud.

## 6. Příkazy

```
cd src/tools
../../.venv/bin/python fetch_eurovoc.py                # deskriptory EuroVoc nových aktů EU
../../.venv/bin/python fetch_ics.py                    # ICS a deskriptory ČAS nových norem (2 s mezi dotazy)
../../.venv/bin/python extract_keywords.py             # jen odhad ceny, nic neodešle
../../.venv/bin/python extract_keywords.py --run       # klíčová slova modelem (mezipaměť, rozpočet --budget)
../../.venv/bin/python document_terms.py               # počty, bez zápisu
../../.venv/bin/python document_terms.py --apply --env-file <.env>   # zápis do databáze
```

Před zápisem do živé databáze pořizujeme zálohu (`backup_db.py`). Skripty `fetch_*` a
`extract_keywords.py` databázi jen čtou. Nový dokument dostane klíčová slova při dalším běhu
těchto skriptů; model zavoláme znovu jen u dokumentu, jehož vstup (název, anotace, text) se změnil.

## 7. Co zbývá

- ICS pro 68 norem IEC, CEN a EN bez českého převzetí. Weby iso.org a iec.ch odmítají automatické
  klienty (HTTP 403); ISO však zveřejňuje metadata všech norem jako otevřená data (odstavec 2),
  IEC srovnatelný zdroj nenabízí. Zbytek doplníme ručně, pokud ho budeme potřebovat.
- Ruční kontrola vzorku klíčových slov z modelu editorem a případný slovník preferovaných termínů
  (sjednocení „palivový článek“ / „palivové články“).
- Filtr katalogu podle třídy ICS a podle deskriptoru EuroVoc.
