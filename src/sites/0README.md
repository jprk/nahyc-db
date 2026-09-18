# Adresář /src/sites

Dedikované parsery pro autoritativní zdrojové weby dokumentů (doc/PLAN.md
§8, 2026-09-11) — jeden modul na doménu, každý s jednotným rozhraním
`extract(url, cached_path=None, session=None) -> {"title": str,
"description": str|None} | None` (nikdy nevyhazuje výjimku, `None` značí
"nepodařilo se, nezjišťovat proč"). Volané z
`src/tools/fetch_authoritative_metadata.py`, nikdy přímo z pipeline
skriptů. Žádný modul zde neuhaduje/nedomýšlí — jen extrahuje to, co
konkrétní stránka/služba skutečně vrací.

## Přehled modulů

* `eurlex.py` - Autoritativní název EU aktu (bez popisu — Cellar
  bibliografická metadata nemají volný abstrakt) přes veřejný,
  neautentizovaný Cellar SPARQL endpoint (`publications.europa.eu/webapi/
  rdf/sparql`), stejný, který `src/tools/screen_eurlex.py` už používá pro
  screening. `celex_from_url()` extrahuje CELEX id jen z URL, které jej
  nese explicitně (`?uri=CELEX:...`/`?uri=CELEX%3A...`) — ELI-styl
  (`.../eli/dir/2019/692/oj`) a holé Official-Journal odkazy
  (`?uri=OJ:L_...`) záměrně NEJSOU řešeny (žádná ověřená, needostavěná
  cesta z nich na CELEX nebyla nalezena — vrací `None`, nikdy nehádá).
  Klíčový detail nalezený testováním proti reálnému endpointu: CELEX
  literál v SPARQL dotazu MUSÍ nést explicitní `^^xsd:string` typovou
  anotaci, jinak dotaz tiše nevrátí nic, i pro potvrzeně existující CELEX.
  **2026-09-16 (doc/PLAN.md §16, uživatelský nález — "Gestor" u EU aktů)**:
  rozšířeno o `fetch_responsible_gestor()`, volané z nového
  `src/tools/backfill_eu_gestor.py` (ne z `fetch_authoritative_metadata.py`
  — jiný účel, jiný orchestrátor). Na rozdíl od `celex_from_url()` výše
  (záměrně jen explicitní `CELEX:` tvar) tahle nová cesta řeší i ELI a
  holý `OJ:L_...` tvar URL — přes `owl:sameAs` na Cellar `?work` zdroj
  (`resource_uris_from_text()`/`resource_uri_from_url()`), ne přes
  CELEX-konstrukci, takže obchází nejednoznačnost otočeného pořadí
  rok/pořadové číslo u předpisů z doby před rokem 2015. Čte
  `cdm:resource_legal_responsibility_of_agent` (odpovědné Generální
  ředitelství) s fallbackem na `cdm:work_created_by_agent` (u čistě
  Komisí vydaného aktu byl živě nalezen případ, kdy DG je jen tady) a
  název DG/instituce dotáhne v češtině přes `skos:prefLabel`. Když URL
  nedá žádnou shodu, `celex_candidates_from_designation()` zkusí
  sestavit kandidátní CELEX přímo z `identifier`/titulku (obě možná
  pořadí roku a čísla, nikdy neuhádne jen jedno).
  **2026-09-18 (doc/PLAN.md §38, uživatelské zadání — doplnění
  `nazev_eu`/`odkaz_eu`)**: `resolve_eu_act_by_designation(text,
  type_name, session=None)`, nová funkce pro volný citační text (poznámka
  pod čarou/příloha národního zákona), ne uloženou URL záznamu — zkouší
  ELI kandidáty (`eli_candidates_from_designation()`) a při neúspěchu
  CELEX kandidáty (živě nalezeno: starší Rozhodnutí typu 2002/159/ES
  nemají v Cellaru `owl:sameAs` záznam pod svým ELI zdrojem vůbec, jen
  pod CELEX). `_YEAR_NUMBER_RE` rozšířeno na jednociferné pořadové číslo
  (`\d{1,4}`) — živě nalezeno, že dřívější `\d{2,4}` tiše selhávalo na
  reálné Směrnici 2006/7/ES (o vodách ke koupání). Volající
  (`src/tools/populate_eu_transposition.py`) MUSÍ ověřit datum
  vráceného titulku proti datu v citaci předtím, než náhradní typ
  přijme — různé typy aktů EU mají nezávislé číslování v rámci roku,
  takže stejná dvojice rok/číslo může patřit dvěma zcela odlišným
  aktům (živě nalezeno u "2011/92": směrnice EIA i nesouvisející
  nařízení o sýru).
* `zakonyprolidi.py` - Autoritativní název + popis českého zákona ze
  `zakonyprolidi.cz` (soukromý, ale spolehlivý zrcadlový portál — viz
  `esbirka.py` níže, proč ne přímo oficiální zdroj). Parsuje `<meta
  property="og:title">`/`<meta property="og:description">` (fallback na
  `<title>`/`<meta name="description">`) — ověřeno živě 2026-09-11, žádný
  anti-bot problém s běžným prohlížečovým User-Agentem. Preferuje již
  stažený lokální soubor (`data/fulltext/{Haltuf_Dokumenty,Sinay_Zakony}/`,
  postavil `fetch_fulltext.py`) před novým síťovým dotazem.
* `slovlex.py` - Autoritativní název slovenského zákona ze `slov-lex.sk`
  (bez popisu — slovenská legislativní konvence už do samotného oficiálního
  názvu skládá celý předmět úpravy). Stránka je Angular SPA bez
  server-renderovaného obsahu, ale `<head>` nese `<script type="application/
  ld+json">` blok se schema.org `Legislation` typem, jehož pole `name` je
  přesně to, co potřebujeme — parsuje TOHLE, ne viditelný obsah stránky
  (fallback na `<title>` se svlečenou příponou "| Slov-Lex"). Ověřeno živě
  2026-09-11 s `allow_redirects=True` (3 přesměrování na reálné URL).
* `normoff.py` - **2026-09-16 (doc/PLAN.md §17)**: slovenský registr norem ÚNMS SR
  (`normy.normoff.gov.sk`) — jediný modul zde, který si cíl musí nejdřív **dohledat**.
  Korpus totiž u všech 101 těchto záznamů neukládá odkaz na konkrétní dokument, ale
  společný kořen katalogu, takže není co stáhnout; `resolve()` proto překládá označení
  normy na konkrétní katalogový záznam a teprve pak `extract()` čte detailní stránku.
  Jde o mechanismus „hledání podle označení", který `doc/PLAN.md` §8 odložil jako
  „podstatně větší a jinak tvarovaný úkol", zde postavený pro nejvýnosnější doménu.
  Dvě žádosti na označení, obě levné a deterministické: `/vyhladavanie-export/?name=…`
  vrátí malé CSV se všemi vydáními daného označení (katalogové číslo, název, datum
  vydání, **datum zrušení**, URL) — použito záměrně místo scrapování HTML výsledků,
  protože je to strukturované a web to sám nabízí; pak `/norma/<katalogové číslo>/`
  nese vlastní text „Predmet normy". Volba vydání kopíruje pravidlo, které už
  `check_csn_validity.find_best_match()` používá pro český registr: přednost má vydání
  stále platné (prázdné `Dátum zrušenia` — datové pole, ne vykreslený štítek), jinak
  nejnovější vydané, aby i zrušená norma dala skutečný popisný text místo ničeho.
  **Nikdy nehádá**: uznává jen PŘESNOU shodu označení (registr na částečné označení
  ochotně vrací blízké, ale jiné normy) a prázdná buňka „Predmet normy" dá `None`,
  ne text, který náhodou stojí vedle — dřívější verze modulu takto tiše vytáhla odkaz
  „Hore" ze zápatí stránky. `designation_variants()` normalizuje jen mezery kolem
  novelizační přípony (`"STN EN 16898 + A1"` → `"STN EN 16898+A1"`, tentýž dokument);
  záměrně NEspadne zpět na základní normu, když se nenajde novela
  (`"STN EN ISO 11114-1/Zmena"` → základ je JINÝ dokument a jeho předmět by popisoval
  něco jiného). Ověřeno na reálném vzorku: 13 z 20 záznamů má skutečný text předmětu,
  medián 875 znaků — srovnatelné s autentickými anotacemi, které už v korpusu jsou.
  Pokryto testy v `tests/test_sites_normoff.py`.
* `eiga.py` - **2026-09-17 (doc/PLAN.md §24)**: publikace EIGA (European
  Industrial Gases Association, `eiga.eu`) — stejný tvar úlohy jako
  `normoff.py`: korpus ukládá jen společnou domovskou stránku, ne odkaz
  na konkrétní publikaci, takže `resolve()` opět předchází `extract()`u.
  Na rozdíl od `normoff.py` ale NEEXISTUJE samostatná detailní stránka —
  výsledek hledání (`GET /publications/?_sf_s=<číslice>`) už sám nese
  „READ MORE" text přímo v syrovém HTML (skrytý jen `display:none`, ne
  JS-vykreslený). Cesta k funkčnímu dotazu stála za to zaznamenat: stránka
  sama inzeruje pole `_sf_search[]`/`_sft_ct_doc_cats[]` (výchozí
  pojmenování pluginu Search & Filter Pro) a i svůj vlastní AJAX endpoint
  (`?sfid=1550&sf_action=get_data&sf_data=results`) — oba vrátily HTTP 200
  a oba tiše ignorovaly dotaz a vrátily nefiltrovaný výchozí výpis; funkční
  parametr `_sf_s=<číslice>` na `/publications/` přímo dodal až uživatel,
  ne rozbor formulářového markupu stránky. Web navíc pod třemi číslicemi
  (vlastní dokumentované minimum) nebo pro číslo bez aktuální shody vrací
  místo prázdného výsledku fuzzy fulltextové zásahy (ověřeno živě: dotaz
  „100" vrátil 10 nesouvisejících dokumentů) — `extract()` proto nikdy
  nedůvěřuje „prvnímu výsledku", ale ověřuje vlastní číslo KAŽDÉHO
  výsledku (z jeho titulku) proti číslicím vloženým do URL. Když výpis
  nemá vlastní shrnutí, záložní krok stáhne PDF (`a.list-download`) a
  zkusí `pdfplumber` na první stránku — nejistý pokus (mnoho PDF má na
  první straně jen titulní list), nikdy nevyhazuje. Pokryto testy v
  `tests/test_sites_eiga.py`.
* `iec.py` - **doc/PLAN.md §25 (2026-09-17)**: na rozdíl od KAŽDÉHO jiného modulu v tomto adresáři nedělá ŽÁDNÝ živý požadavek — jen čte lokální index (`data/iec_publications_index.json`), který postavil `src/tools/harvest_iec_publications.py` (přehled tam). Důvod: `www.iec.ch` je potřeba k rozřešení označení na konkrétní výbor (IEC značky samy nenesou informaci o vydávajícím výboru), ale je za AWS WAF Bot Control „challenge" akcí, kterou obyčejný `requests` klient nemůže projít — jen headless prohlížeč, moc těžké na spouštění při každém běhu `fetch_authoritative_metadata.py` kvůli hrstce záznamů. `normalize_designation()` odpovídá `harvest_iec_publications.py`'s vlastní `reference_base()` na straně korpusu: odřízne Sinay's edice příponu (`"IEC 60092-506/ - 2003.06"` → `"IEC 60092-506"`), předponu `"prEN "` (korpusovo vlastní označení „koncept evropské adopce IEC dokumentu", ne součást identity IEC dokumentu samotného), a — nalezeno až párováním proti reálným sklizeným klíčům — lomítkem spojený typ dokumentu (`"IEC/TR"`/`"IEC/TS"`/`"IEC/PAS"`) na mezerou oddělený tvar, jaký používá katalog IEC samotný (`"IEC TR 62351-13:2016"`). Designace bez shody v indexu (koncept ještě nepublikovaný, nebo skutečně jiný typ dokumentu) správně vrací `None`, nikdy neuhaduje. Pokryto testy v `tests/test_sites_iec.py`.
* `dvgw.py` - **doc/PLAN.md §26 (2026-09-17)**: stejný tvar jako `iec.py` — žádný živý požadavek, jen čte lokální index (`data/dvgw_publications_index.json`), který postavil `src/tools/harvest_dvgw_publications.py` (přehled tam — `dvgw-regelwerk.de`'s vlastní hledání je nespolehlivé, detailní stránky placené za jeden podtitulek). `normalize_designation()` odřízne jen korpusovu vlastní příponu stavu (`"G 260 (A)"` → `"G 260"`, `"(A)"`="Arbeitsblatt", `"(M)"`="Merkblatt"). Index pokrývá jen 41 ze 101 korpusových DVGW označení (kurátorované výpisy, ne celý katalog) — designace bez shody správně vrací `None`. Pokryto testy v `tests/test_sites_dvgw.py`.
* `esbirka.py` - **NENÍ zdroj obsahu** — `e-sbirka.gov.cz` je skutečný
  oficiální zdroj českého práva (na rozdíl od `zakonyprolidi.cz`), ale jeho
  vlastní frontend je needostupný Angular SPA (`<esel-app>` prázdná
  schránka, ověřeno živě) a jeho REST API vyžaduje registraci klienta u
  Ministerstva vnitra (viz `src/tools/screen_esbirka.py`). Veřejný LOD
  SPARQL endpoint (`opendata.eselpoint.gov.cz`, stejný jako
  `screen_esbirka.py`) MÁ uzel adresovatelný přes ELI (sestavitelný přímo
  ze znacky českého zákona), ale skutečný text názvu nikde neleží jako
  prosté pole — graf je strukturovaný na úrovni jednotlivých odstavcových
  fragmentů (stovky uzlů na zákon), ne jako metadatový záznam dokumentu
  (ověřeno prošetřením grafu do několika úrovní, 2026-09-11). Tento modul
  proto jen OVĚŘUJE citaci (`verify()` — potvrdí, že daný ELI uzel nese
  přesně odpovídající citaci) a vrátí lidsky čitelnou referenční URL
  (`https://e-sbirka.gov.cz/sb/{rok}/{číslo}`), kterou
  `fetch_authoritative_metadata.py` připojí jako `zdroj_esbirka_url` vedle
  `zakonyprolidi.py`'s skutečného textu názvu/popisu.
  **Budoucí migrace (zatím nepostaveno — chybí přístupový klíč):** až bude
  k dispozici registrovaný přístup k e-Sbírka REST API, tento modul je
  přirozené místo pro rozšíření na plnohodnotný zdroj názvu/popisu
  (nahradil by `zakonyprolidi.py`'s roli pro české zákony) — viz
  `REST_API_TODO` poznámka v souboru.

Pokryto testy v `tests/test_sites_eurlex.py`, `tests/test_sites_
zakonyprolidi.py`, `tests/test_sites_slovlex.py`,
`tests/test_sites_esbirka.py`, `tests/test_sites_normoff.py`,
`tests/test_sites_eiga.py` (mockované HTTP/SPARQL/CSV, žádná reálná
síťová volání), `tests/test_sites_iec.py` a `tests/test_sites_dvgw.py`
(`iec.py`/`dvgw.py` samy o sobě žádnou síť nepoužívají — čistě lokální
slovník místo mocku).
