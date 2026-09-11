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
`tests/test_sites_esbirka.py` (mockované HTTP/SPARQL, žádná reálná síťová
volání).
