# Klíčová slova dokumentů

Stav k 23.11.2026, větev `feature/keywords`; uložení (odstavec 4) k 25.11.2026, větev `feature/mpo-sjednoceni`.

## 1. Výchozí stav

Databáze dosud nemá u žádného dokumentu seznam klíčových slov, který by popisoval jeho obsah.
Tabulka `Keyword`/`DocumentKeyword` (1163 dokumentů) nese kategorie převzaté ze zdrojových
rešerší: u rešerše Sinay jde o 264 názvů skupin typu „Verflüssigung“ nebo „Untertage Gasspeicher“,
rešerše Prokop má v poli všude „-“ a rešerše Haltuf toto pole nemá. Anotace norem (838 z 1226)
obsahují úvodní větu normy z katalogu, klíčová slova v nich nejsou. Kategorie proto ponecháváme
(slouží k vyhledávání a do 23.11.2026 sloužily jako filtr „štítků“ v katalogu) a klíčová slova
vedeme odděleně. Od 25.11.2026 se tabulky kategorií jmenují podle obsahu `SourceCategory` a
`DocumentSourceCategory` (odstavec 4.1).

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

## 3. Výsledky (23.11.2026, živá databáze 1506 dokumentů)

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
uživatele (23.11.2026) jsou v `data/manual_corrections.json`: #86 slučujeme do (EU) 2024/1789 (#105),
#91 dostal úřední název z Cellaru a nový popis (akt obsahuje požadavky na vozidla s vodíkovým pohonem,
příloha XIV). Systematickou kontrolu dalších záznamů popisuje `doc/KONTROLA_ZAZNAMU.md`.

## 4. Uložení

Klíčová slova má po nahrání všech zdrojů všech 1506 dokumentů (zkušebně v `h2regdocs_test`).

Od 25.11.2026 vedeme klíčová slova v **centrální tabulce `Term`** a dokumenty na ně odkazují
**vazební tabulkou `DocumentTerm`**. Dřívější `DocumentTerm` nesla text klíčového slova u každého
dokumentu zvlášť (12 206 řádků pro 5 247 různých klíčových slov). Jedna tabulka klíčových slov
umožní našeptávač při ruční úpravě, hledání podobných klíčových slov a kontrolu duplicit; editor pak
opraví slovo na jednom místě pro všechny dokumenty. Tabulky popisuje `src/tools/vocabulary.py`,
převod existující databáze dělá `src/tools/migrate_vocabulary.py` (odstavec 4.2).

Tabulka `Term`:

| Sloupec | Význam |
|---|---|
| `id` | klíčové slovo |
| `origin` | `eurovoc`, `ics`, `cas`, `model` |
| `code` | kód deskriptoru EuroVoc nebo třídy ICS |
| `term` | klíčové slovo česky; u ICS „kód název“ |
| `term_en` | anglický tvar (EuroVoc) |
| `term_key` | co klíčové slovo v rámci původu identifikuje (binární porovnání): u EuroVoc a ICS kód, jinak přesný text s jednou mezerou mezi slovy |
| `term_norm` | text malými písmeny bez diakritiky („palivove clanky“), pro našeptávač a hledání podobných slov |

Unikátní je dvojice (`origin`, `term_key`). *Proč takto:* deskriptor EuroVoc a třída ICS mají stálý kód,
text je jen jejich popisek, který se může změnit (opravený popisek pak přepíše jeden řádek). Klíčová
slova ČAS a modelu kód nemají, identifikuje je text. Text porovnáváme binárně, ne podle řazení
`utf8mb4_czech_ci` ani podle `term_norm`: řazení `czech_ci` nerozlišuje velikost písmen, takže by
„Kotle“ a „kotle“ sloučilo samo, a `term_norm` navíc smaže rozdíl „plynu“/„plynů“, který je
gramaticky skutečný. O sloučení podobných tvarů má rozhodnout editor, ne migrace. Původ je součástí
klíče, protože stejný text z úřední indexace a z modelu má jinou spolehlivost (stránka dokumentu
odvozená slova označuje jako neověřená).

Tabulka `DocumentTerm`:

| Sloupec | Význam |
|---|---|
| `document_id` | dokument (cizí klíč, při smazání dokumentu se smaže i vazba) |
| `term_id` | klíčové slovo (cizí klíč; klíčové slovo s vazbou smazat nejde) |
| `position` | pořadí ve zdroji (model řadí od nejdůležitějšího) |
| `created_at` | kdy vazba vznikla |

Primární klíč je (`document_id`, `term_id`). `document_terms.py --apply` zapisuje klíčová slova do `Term`
(nové vloží, u existujících obnoví text a anglický tvar), vazby nahradí a klíčová slova, která po zápisu
žádný dokument nepoužívá, smaže.

Stažené a odvozené údaje držíme v mezipaměti pod správou verzí, klíčované označením dokumentu
(u dokumentu bez označení `url-<hash adresy>`; sdílí-li adresu více dokumentů bez označení, jako 14 letáků
BVEG pod `https://www.bveg.de/`, pak `title-<hash názvu>`), aby přežily přestavbu databáze:
`data/eurovoc_cache.json`, `data/ics_cache.json`, `data/keyword_model_cache.json`.
`init_db.py` obě tabulky při přestavbě vyprázdní a `document_terms.py --apply` je z mezipamětí naplní znovu.

### 4.1 Kategorie zdrojových rešerší

Tabulky `Keyword` a `DocumentKeyword` jsme přejmenovali podle obsahu:

| Dříve | Nyní | Proč |
|---|---|---|
| `Keyword` (`id`, `keyword`) | `SourceCategory` (`id`, `name`) | hodnoty jsou kategorie, do kterých rešerše Sinay, Prokop a Haltuf řadily celé skupiny dokumentů (doc/OBLASTI.md, odstavec 3), ne klíčová slova dokumentu; `name`, protože jde o název kategorie |
| `DocumentKeyword` (`document_id`, `keyword_id`) | `DocumentSourceCategory` (`document_id`, `category_id`) | vazba dokumentu na kategorii; název tabulky skládáme jako u ostatních vazeb (`DocumentArea`, `DocumentTerm`) |

Předponu *Source* volíme proto, aby kategorie nešlo zaměnit s oblastmi katalogu (`Area`) ani s typy
dokumentů. Řádky i jejich `id` zůstávají, takže starý odkaz `?keyword_id=…` aplikace přesměruje na
`?category_id=…` se stejným číslem. Export nese kategorie v poli `source_categories` (dříve `keywords`)
a v poli `keywords` nově klíčová slova dokumentu.

### 4.2 Převod existující databáze

`src/tools/migrate_vocabulary.py` (dry run bez `--apply`, `--env-file`, `--similar` vypíše všechny skupiny
podobných klíčových slov) přejmenuje tabulky kategorií i s jejich sloupci, indexy a cizími klíči a starou
`DocumentTerm` převede: z jejích řádků vytvoří `Term` a novou `DocumentTerm`, před záměnou tabulek porovná
každou vazbu (dokument, původ, klíč, pořadí) se starými řádky a starou tabulku smaže, až když souhlasí.
Vypíše počty před a po. Skript je idempotentní, převedenou databázi nechá beze změny.

Běh nanečisto nad živou databází (25.11.2026):

| | Před | Po (plán) |
|---|---|---|
| kategorie zdrojových rešerší | 238 | 238 |
| vazby dokument – kategorie | 3 239 (1 128 dokumentů) | 3 239 (1 128 dokumentů) |
| klíčová slova (`Term`) | — (12 206 řádků s textem) | 5 247: EuroVoc 315, ICS 137, ČAS 95, model 4 700 |
| vazby dokument – klíčové slovo | 12 206: EuroVoc 1 069, ICS 942, ČAS 231, model 9 964 | 12 206 (1 432 dokumentů) |
| kód s více texty | | 0 |
| řádky sloučené do jedné vazby | | 0 |

**Podobná klíčová slova** (tvary, které se liší jen velikostí písmen nebo diakritikou, `term_norm`): 56 skupin
se 112 tvary. Migrace je neslučuje. 34 skupin jsou tvary z modelu, které se liší diakritikou, většinou
jednotné a množné číslo („analýza plynu“ 2× / „analýza plynů“ 38×, „zkoušení materiálu“ / „zkoušení materiálů“,
„tlakových lahví“ / „tlakových láhví“, „motorový benzin“ / „motorový benzín“); 21 skupin se liší jen velkým
písmenem na začátku, z toho 15 napříč původy (deskriptor ČAS „Bezpečnost“ / slovo modelu „bezpečnost“)
a 6 uvnitř deskriptorů ČAS („Konstrukce“ / „konstrukce“); 1 skupina je „emise CO2“ / „emise CO₂“.

## 5. Webové rozhraní

- Stránka dokumentu má panel „Klíčová slova“ se skupinami podle původu a vysvětlivkou ke každé
  skupině; slova odvozená modelem označujeme jako neověřená. Každé slovo odkazuje na vyhledání
  v katalogu (u ICS hledáme název třídy). U deskriptorů EuroVoc ukazuje anglický tvar bublina.
- Fulltextové vyhledávání v katalogu prohledává i klíčová slova (včetně synonym vyhledávání).
  Dokud tabulka `DocumentTerm` v databázi není, aplikace se chová jako dosud.
- Aplikace pozná, které uspořádání tabulek databáze má (`vocab()` v `app/app.py`, jednou za požadavek):
  před převodem čte `Keyword`/`DocumentKeyword` a starou `DocumentTerm`, po převodu nové tabulky. Kód
  proto můžeme nasadit (`git pull`) před spuštěním `migrate_vocabulary.py` a server po převodu
  nemusíme restartovat.

## 6. Příkazy

```
cd src/tools
../../.venv/bin/python fetch_eurovoc.py                # deskriptory EuroVoc nových aktů EU
../../.venv/bin/python fetch_ics.py                    # ICS a deskriptory ČAS nových norem (2 s mezi dotazy)
../../.venv/bin/python extract_keywords.py             # jen odhad ceny, nic neodešle
../../.venv/bin/python extract_keywords.py --run       # klíčová slova modelem (mezipaměť, rozpočet --budget)
../../.venv/bin/python migrate_vocabulary.py           # převod na Term/DocumentTerm a SourceCategory, nanečisto
../../.venv/bin/python migrate_vocabulary.py --apply --env-file <.env>   # převod (jednou, po záloze)
../../.venv/bin/python document_terms.py               # počty, bez zápisu
../../.venv/bin/python document_terms.py --apply --env-file <.env>   # zápis do databáze
../../.venv/bin/python document_terms.py --similar     # skupiny podobných klíčových slov
```

Před zápisem do živé databáze pořizujeme zálohu (`backup_db.py`). Skripty `fetch_*` a
`extract_keywords.py` databázi jen čtou. Nový dokument dostane klíčová slova při dalším běhu
těchto skriptů; model zavoláme znovu jen u dokumentu, jehož vstup (název, anotace, text) se změnil.

## 7. Co zbývá

- ICS pro 68 norem IEC, CEN a EN bez českého převzetí. Weby iso.org a iec.ch odmítají automatické
  klienty (HTTP 403); ISO však zveřejňuje metadata všech norem jako otevřená data (odstavec 2),
  IEC srovnatelný zdroj nenabízí. Zbytek doplníme ručně, pokud ho budeme potřebovat.
- Ruční kontrola vzorku klíčových slov z modelu editorem a případný slovník preferovaných termínů
  (sjednocení „palivový článek“ / „palivové články“). Podklad: 56 skupin podobných klíčových slov
  (odstavec 4.2, `document_terms.py --similar`); o sloučení rozhodne editor.
- Našeptávač klíčových slov při ruční úpravě dokumentu (nad `Term.term_norm`).
- Filtr katalogu podle třídy ICS a podle deskriptoru EuroVoc.
