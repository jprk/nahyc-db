# Registr sledovaných zdrojů

> Historie dokumentu:  
> 2026-10-28 jprk Převzato z odstavce 11 dokumentu `doc/AUTOMATION.md` (větev `automation`, stav 2026-10-24)  
> 2026-10-28 jprk Doplněno z návrhu katalogu informačních zdrojů: role a priority zdrojů, 36 nových zdrojů ověřených živě, pořadí prací, zpracování nálezu, vyhledávací výrazy, výhled  
> 2026-10-28 jprk Plán vytěžování zdrojů (odstavec 4) a pole `signal` a `stage` v registru  
> 2026-10-29 jprk Etapa E0 provedena (odstavec 4.3), první kontrola dostupnosti  
> 2026-11-04 jprk Provoz vytěžování a výsledky etapy E0 (odstavec 8)  
> 2026-11-04 jprk Etapa E1 provedena (odstavce 4.3 a 8.7)
> 2026-11-04 jprk Rozbor nálezů e-Sbírky a návrh řešení šumu (odstavec 8.8)
> 2026-11-04 jprk Omezení šumu provedeno (odstavec 8.9)
> 2026-11-04 jprk Etapa E2 provedena (odstavce 4.3 a 8.10)

Tento dokument popisuje registr zdrojů, v nichž opakovaně hledáme nové
regulační dokumenty pro databázi regulačních předpisů a předrealizačních
procesů (výsledek V01 dílčího projektu DP004). Registr sám je uložen
v souboru `data/monitored_sources.json`. Které dokumenty má databáze
obsahovat a jak často se obsah kontroluje, vymezuje `doc/DATABASE_SCOPE.md`;
řetězec, jímž se nalezený dokument dostává do databáze, popisuje
`doc/AUTOMATION.md` (zatím jen na vývojové větvi `automation`).

Předmětem registru jsou **zdroje, nikoli soupis jednotlivých předpisů**.
Že je zdroj pro vodíkové technologie tematicky relevantní, neznamená, že se na
každou vodíkovou instalaci vztahují všechny dokumenty, které zdroj nabízí.

---

## 1. Účel registru

Dnešní sledování stojí na třech zdrojích se screeningovými skripty
`src/tools/screen_eurlex.py`, `screen_esbirka.py` a `screen_slovlex.py`
(`doc/AUTOMATION.md`, odstavec 4.1), což zdaleka nepokrývá místa, kde nové
vodíkové předpisy vznikají. Registr `data/monitored_sources.json` proto vede
**úplný seznam zdrojů, jež sledujeme nebo sledovat chceme** — 78 položek,
u každé ověřená adresa, způsob dotazování, přínos a překážky. Registr je
strojově čitelný, aby z něj mohly budoucí screeningové skripty vycházet,
a zároveň čitelný člověkem, protože rozhodnutí typu „tento zdroj sledovat
nebudeme“ je nutné uchovat i s odůvodněním.

Registr je pracovní verzí: sám nic nestahuje ani nezapisuje do korpusu
a žádný skript z něj zatím nečte.

## 2. Struktura záznamu

Každá položka nese pole `id`, `name`, `category`, `jurisdiction`, `url`,
`access` (způsob a případná strojově čitelná adresa), `status`,
`screener` (cesta ke skriptu, pokud existuje), `cadence` (navrhovaná
perioda), `priority`, `role`, `signal` a `stage` (druh signálu a etapa
zapojení podle plánu vytěžování, odstavec 4), `adds` (co zdroj přináší nad
rámec stávajícího pokrytí), `constraints` a `verified_at`.

Pole `status` nabývá sedmi hodnot:

| Hodnota | Význam | Počet |
|---|---|---|
| `automated` | Sledujeme dnes, existuje skript. | 10 |
| `ready` | Strojově čitelná cesta ověřena, zbývá ji zapojit. | 24 |
| `needs_work` | Dostupné, ale vyžaduje sběr z HTML nebo nestabilní vzor adresy. | 17 |
| `manual_only` | Vhodné jen k občasné lidské kontrole, ne k automatizaci. | 12 |
| `prohibited` | Podmínky užití nebo `robots.txt` automatizovaný přístup zapovídají. | 5 |
| `blocked` | Technická překážka (ochrana proti robotům, aplikace vykreslovaná až v prohlížeči, rozhraní dostupné jen po registraci). | 9 |
| `rejected` | Ověřeno a zavrženo pro nedostatek užitečného signálu. | 1 |

Pole `verified_at` nese datum, kdy byla adresa naposledy ověřena živě.
Hodnota `null` znamená, že zdroj je v aktivním používání pipeline, a jeho
dostupnost tedy ověřuje provoz sám; u nově navržených zdrojů je datum
vyplněno vždy. Jedinou výjimkou je adresa kanálu RSS u ERÚ, převzatá
z patičky ověřené stránky, ale samostatně neověřená — v poli
`constraints` je to uvedeno.

Pole `access.method` udává způsob získávání dat: `sparql`, `rest_api`,
`json_api`, `rss`, `bulk_download` (hromadné stažení úplné datové sady,
například otevřených dat Poslanecké sněmovny), `pdf_pattern`, `pdf_index`,
`html`, `headless_browser` a `none`. Adresu v `access.endpoint` uvádíme jen
tehdy, byla-li ověřena dotazem; to, že zdroj rozhraní inzeruje, nepostačuje.

### 2.1 Role zdroje

Pole `role` zachycuje, jakou úlohu zdroj pro databázi plní. Jeden zdroj může
plnit více rolí:

- **P** — Primární právní zdroj: oficiální vyhlašování nebo autoritativní
  evidence právních aktů a jejich znění.
- **L** — Legislativní proces: návrhy, připomínky, jednání, pozměňovací
  návrhy a připravované změny.
- **N** — Normativní a technický zdroj: technické normy, technická pravidla
  a jejich katalogy.
- **M** — Metodický a regulační zdroj: výklady, postupy, metodiky
  a informace příslušných orgánů.
- **E** — Evidence záměrů a subjektů: posuzování záměrů, oznámené
  a akreditované subjekty a příklady uplatnění předpisů.
- **S** — Sekundární odborný zdroj: studie, doporučení, bezpečnostní
  návody, tematické rozcestníky a odborný tisk.

Role popisuje zdroj, nikoli jednotlivý dokument. Právní závaznost dokumentu
posuzujeme samostatně a neodvozujeme ji z toho, kdo web provozuje
(`doc/DATABASE_SCOPE.md`, odstavec 4).

### 2.2 Priorita zdroje

Pole `priority` nabývá hodnot `A`, `B` a `C` (u zavržených a zakázaných zdrojů
`null`). **Priorita zdroje nesouvisí s úrovněmi pokrytí A, B a C** podle
`doc/DATABASE_SCOPE.md`, odstavec 2; jde o shodné označení dvou nezávislých
stupnic.

| Priorita | Význam | Režim | Počet |
|---|---|---|---|
| A — nezbytný | Bez zdroje by bylo regulační pokrytí výrazně neúplné. | První vlna, průběžné sledování. | 16 |
| B — vysoká | Zdroj významně rozšiřuje věcné pokrytí nebo umožňuje ověřovat údaje. | Druhá vlna, pravidelná kontrola. | 30 |
| C — doplňková | Především metodický, srovnávací či úzce specializovaný přínos. | Rešerše podle věcné potřeby. | 28 |

### 2.3 Kategorie a jurisdikce

Pole `category` třídí zdroje podle druhu provozovatele: `legal_register`
(sbírky a registry předpisů), `draft_legislation` (registry návrhů a průběhu
legislativního procesu), `standards_body` (normalizační orgány a katalogy
norem a technických pravidel), `treaty_body` (orgány mezinárodních smluv),
`ministry`, `regulator` (energetičtí regulátoři), `authority` (jiné orgány
státní správy, inspekce a agentury), `case_register` (evidence záměrů,
oznámených a akreditovaných subjektů), `industry_association`,
`policy_tracker`, `metadata_catalogue` a `press_social`.

Pole `jurisdiction` nabývá hodnot `CZ`, `SK`, `EU`, `DE` a `international`.
Zahraniční předpisy (`DE`) slouží jen ke srovnání a k výkladu zahraničních
metodik, nikoli jako zdroj povinností podle českého práva.

## 3. Co registr přináší nového

Nejcennější zjištění se týká **včasného signálu**. Dnes vidíme předpis
až po vyhlášení; tři ověřené zdroje jej ukazují dříve:

1. **VeKLEP (ODok)** — Návrhy českých zákonů, nařízení vlády a vyhlášek
   v legislativním procesu, včetně připomínkového řízení. Nabízí
   stránkované rozhraní JSON (ověřeno: 8 655 položek) i kanál RSS.
   Patrně nejvýznamnější jednotlivý nález.
2. **Slov-Lex — legislatívny proces** — Slovenské návrhy v pripomienkovém
   konaní, a to prostým kanálem RSS. Obchází tím potíž, kvůli níž dnes
   Slov-Lex sledovat neumíme: vyhledávací rozhraní je aplikace
   vykreslovaná až v prohlížeči, kdežto tento kanál je běžné HTTP.
3. **Věstník ÚNMZ** — Měsíční přehled vydaných a zrušených ČSN
   v předvídatelně pojmenovaném souboru PDF. Nahradil by dnešní
   dotazování po jednotlivých označeních jedním hromadným přírůstkem.

Nejhodnotnějším dosud nedostupným zdrojem zůstává **rejstřík projednávání
ve výborech**, jenž nese návrhy prováděcích aktů před vyhlášením. Katalog
`data.europa.eu` sice inzeruje distribuci ve formátu CSV, ověřením se
však ukázalo, že uvedená adresa vrací tentýž obal aplikace jako rejstřík
sám. Získání dat by vyžadovalo headless prohlížeč — stejný postup, jaký
si už vyžádaly weby `iso.org` a `iec.ch`.

Pro oblast norem platí stejné omezení jako u stahování plných textů
(`doc/AUTOMATION.md`, odstavec 4.2): sledujeme výhradně katalogová
a bibliografická data, nikdy chráněné plné texty. U dvou jinak velmi
relevantních zdrojů (ISO/TC 197 a CEN/CLC/JTC 6 *Hydrogen in energy
systems*) jde nad rámec technické překážky i o výslovný zákaz —
`robots.txt` výboru CEN/CENELEC zapovídá veškerý automatizovaný přístup,
ačkoli by jeho stránky byly technicky snadno čitelné. Takový zdroj proto
vedeme jako `prohibited` a nesledujeme jej; náhradní cestou je katalog
ČSN, jenž převzaté evropské normy zrcadlí.

Samostatnou kapitolou je odborný tisk a sociální sítě. Prověřili jsme
šest kanálů a **pět z nich zavrhli**: dva zapovídají automatizovaný
přístup v podmínkách užití (u jednoho jde o formální výhradu podle
§ 44b německého autorského zákona), jeden je placený a jeden sice nabízí
bezvadný kanál RSS, avšak bez jakéhokoli regulačního obsahu. Zbylé dva
vedeme jako `manual_only`. Důvod je zásadní a platí pro celou kategorii:
zpráva v tisku ani příspěvek na sociální síti nemohou být pramenem
záznamu v této databázi — jsou nanejvýš upozorněním, jež je stejně nutné
ověřit v autoritativním registru, který již sledujeme. Ze sociálních sítí
je ostatně automatizovanému čtení otevřena jediná (Bluesky); X i LinkedIn
jsou bez placeného přístupu uzavřené. Obdobně platí pro všechny sekundární
zdroje (role S): odborný komentář, metodika nebo prezentace nemusí odrážet
nejnovější právní stav a nemají účinky právního předpisu.

### 3.1 Doplnění podle návrhu katalogu (28. 10. 2026)

Návrh katalogu informačních zdrojů uváděl 55 zdrojů v sedmi oblastech.
Osmnáct z nich registr již obsahoval; zbylých 37 jsme doplnili jako 36 nových
položek (dvě publikační místa European Hydrogen Safety Panel vedeme jako jeden
zdroj) a každou ověřili živě (stav HTTP, `robots.txt`, kanály RSS a rozhraní,
u kanálů počet a datum položek). Dvě z nových položek doplňují stávající zdroj
téhož provozovatele o jinou stránku (DG ENER — trh s vodíkem, CEN/CENELEC —
přehled pro vodík). U devíti stávajících položek ověření přineslo upřesnění
(`esbirka-lod`, `csn-online`, `unece-wp29`, `iec-catalogue`, `sae-standards`,
`eiga-publications`, `cen-clc-jtc6`, `clean-hydrogen-partnership`,
`dg-ener-hydrogen`). Z nových zdrojů je 13 ve stavu `ready`, 11 `needs_work`,
6 `blocked` a 6 `manual_only`.

Doplněné zdroje podle oblastí:

- **Česká legislativa a legislativní proces** — e-Legislativa, sněmovní
  a senátní tisky, Sbírka právních předpisů územních samosprávných celků.
- **Legislativní proces EU** — Legislative Observatory Evropského parlamentu,
  veřejný registr dokumentů Rady EU, TRIS, registr dokumentů Komise.
- **Normy** — souhrnné seznamy harmonizovaných norem Evropské komise,
  přehled CEN/CENELEC pro vodík, katalog technických pravidel TPG Českého
  plynárenského svazu.
- **České orgány** — MMR (stavební právo), MŽP, Technická inspekce ČR,
  Hasičský záchranný sbor ČR, Státní úřad inspekce práce, CENIA
  (integrovaná prevence), informační systém EIA, Česká inspekce životního
  prostředí, Český metrologický institut, Česká obchodní inspekce, Český
  institut pro akreditaci.
- **Orgány EU** — DG ENER (trh s vodíkem), referenční dokumenty BREF,
  ECHA CHEM, NANDO, Agentura EU pro železnice, European Hydrogen Safety Panel.
- **Doprava** — Ministerstvo dopravy (ADR, drážní oblast), Drážní úřad (RID),
  EHK OSN (nebezpečné věci včetně ADN), OTIF (RID), IMO (IMDG).
- **Zahraniční podklady** — BAuA, Gesetze im Internet.

Ověření v několika bodech vyvrátilo nebo upřesnilo údaje návrhu:

1. **e-Sbírka a e-Legislativa** — REST API obou systémů existuje
   a dokumentace je volně dostupná, klíč však vyžaduje registraci podáním
   do datové schránky Ministerstva vnitra s posouzením předpokládaného objemu
   dotazů. Registrace je společná pro oba systémy; dokud neproběhne, vedeme
   e-Legislativu jako `blocked`. Povinné použití e-Legislativy platí pro zákony
   od 15. 1. 2026, pro novely zákonů je zákonem č. 583/2025 Sb. odloženo na
   15. 1. 2027 a rozpracované návrhy se dokončují dosavadním postupem; VeKLEP
   proto patrně bude potřeba sledovat i nadále.
2. **Senát** — `robots.txt` webu `senat.cz` zapovídá veškerý automatizovaný
   přístup, a to i ke kanálům RSS, jež Senát nabízí. Senátní tisky však
   obsahují i otevřená data Poslanecké sněmovny, jejichž stažení povoleno je;
   položka `senat-tisky` proto vede jen tuto cestu.
3. **Sbírka právních předpisů územních samosprávných celků** — není aplikací
   vykreslovanou až v prohlížeči, jak uvádělo dřívější zjištění
   (`doc/DATABASE_SCOPE.md`, odstavec 8, otázka O1), ale serverem vykreslované
   HTML s výsledky řazenými od nejnovějších. Dokumentované rozhraní ani kanál
   RSS nemá; upozornění rozesílá jen e-mailem po registraci.
4. **Ochrana proti robotům** — celá doména `unece.org` (ADR, ADN, předpisy
   pro vozidla), veřejný registr Rady EU, `baua.de` a web `echa.europa.eu` vracejí
   automatizovanému klientovi HTTP 403. Jde o technickou překážku, ne o zákaz;
   podmínky opakovaného užití dat ECHA proto zbývá přečíst ručně.
5. **Nefunkční nebo změněné adresy** — informační systém EIA leží na
   `portal.cenia.cz/eiasea/view/eia100_cr` (adresa z návrhu vrací 404),
   Legislative Observatory na `oeil.europarl.europa.eu`, referenční dokumenty
   BREF na `bureau-industrial-transformation.jrc.ec.europa.eu`, NANDO
   v aplikaci Single Market Compliance Space. Katalog ČSN zůstává na adrese
   již vedené v registru; adresa z návrhu je jen informační stránkou.
6. **Strojově čitelné cesty, které návrh neuváděl** — Legislative Observatory
   nabízí export RSS a XML (pro „hydrogen“ 139 postupů), Parlament navíc
   otevřené API; metadata norem SAE poskytuje otevřené API Crossref (98 norem
   k vodíku); Gesetze im Internet úplný seznam předpisů v XML.
7. **Změněné priority** — U pěti zdrojů jsme prioritu z návrhu snížili:
   ECHA CHEM z A na B (údaje o látkách, nikoli nové předpisy), registr
   dokumentů Komise z B na C (návrhy COM a pracovní dokumenty pokrývá
   EUR-Lex), referenční dokumenty BREF z B na C (závěry o BAT vycházejí
   v EUR-Lexu), NANDO a Český institut pro akreditaci z B na C (evidují
   subjekty, nikoli předpisy). Stávající položky ponechaly své priority,
   i když je návrh hodnotil jinak (například e-Sbírka, katalog ČSN, ISO/TC 197
   a MPO jako A).

Kanály RSS ministerstev a orgánů (MMR, MŽP, SÚIP, ČIŽP, ČOI, Drážní úřad)
nesou obecné zprávy úřadu, ne jen regulační dokumenty; stav `ready` u nich
znamená ověřený kanál, jejž bude třeba filtrovat podle vyhledávacích výrazů
z odstavce 6.

## 4. Plán vytěžování zdrojů

Tento odstavec popisuje, jak budeme ze zdrojů registru získávat dokumenty
a změny jejich stavu, a v jakém pořadí. Je zároveň zadáním pro budoucí
automatizaci: každý zdroj nese v registru pole `signal` (co z něj získáváme)
a `stage` (ve které etapě jej zapojíme), takže spouštěč popsaný v odstavci 4.2
bude moci plán číst přímo z registru.

### 4.1 Výchozí stav

Dokumenty se dnes do databáze dostávají třemi navzájem nepropojenými cestami:

1. **Screeningové skripty a skripty `add_*`** — `screen_eurlex.py`
   a `screen_esbirka.py` zapisují nálezy do
   `data/fulltext_screening_candidates.json`; skripty
   `add_eurlex_hydrogen_acts.py`, `add_esbirka_hydrogen_acts.py`
   a `add_hytep_hydrogen_docs.py` z nich po ověření a filtraci vytvářejí
   soubory `data/discovered_*.json`, jež při přestavbě načítá
   `build_unified_db.py`. Sklizeň katalogů IEC a DVGW
   (`harvest_iec_publications.py`, `harvest_dvgw_publications.py`) a modul
   `src/sites/eiga.py` fungují obdobně, každý vlastním způsobem.
2. **Fronta kandidátů** — tabulka `DocumentCandidate` a stránka
   `/admin/candidates`; plní ji uzávěr citací, kontrola platnosti (chybějící
   nástupci zrušených dokumentů) a ruční návrhy editorů. Přijetí dvěma editory
   vytvoří dokument ihned a zapíše jej do `data/accepted_candidates.json`.
3. **Agentní zpracování** (větev `automation`) — kandidáty z EUR-Lexu
   převádí na ověřené záznamy v `data/discovered_agentic_candidates.json`;
   tento soubor však přestavba zatím nenačítá (`doc/AUTOMATION.md`,
   odstavec 6.3).

Změny stavu již evidovaných dokumentů sleduje kontrola platnosti
(`check_validity.py` nad Cellarem, e-Sbírkou a zakonyprolidi.cz,
`backfill_document_states.py`) a u norem `check_csn_validity.py`
a `src/sites/normoff.py`. Žádná z cest neběží pravidelně, žádná
nezaznamenává kontroly, jež nic nepřinesly, a každý nový zdroj by dnes
znamenal další soubor `discovered_*.json` a další načítací blok
v přestavbě.

### 4.2 Cílový tvar

Navrhujeme sjednotit všechny cesty do jednoho tvaru:

```
registr zdrojů (data/monitored_sources.json: signal, stage, cadence)
      │
      │  spouštěč: harvest_sources.py --stage E2 | --cadence weekly | --source <id>
      ▼
adaptér zdroje (jeden modul na zdroj nebo na druh rozhraní, např. společný adaptér RSS)
      │  vrací nálezy jednotného tvaru
      ▼
filtr věcné příslušnosti (vyhledávací výrazy, odstavec 6; classify_candidate() pro EUR-Lex)
      │
      ├── nový dokument / návrh ──▶ fronta kandidátů DocumentCandidate (source = id zdroje)
      ├── změna stavu ───────────▶ kontrola platnosti → stavy dokumentů (DATABASE_SCOPE.md, odst. 5)
      └── každý běh ─────────────▶ záznam o kontrole (i bez nálezu)
                                        │
                                        ▼
                             editor: návrh + potvrzení druhým editorem → dokument
```

Zásady cílového tvaru:

1. **Jediná vstupní brána je fronta kandidátů.** Nový zdroj nepřidává
   soubor `discovered_*.json` ani načítací blok v přestavbě; jeho nálezy
   končí ve frontě se zdrojem uvedeným identifikátorem z registru. Klíč
   kandidáta (`CZ:N/RRRR`, `EU:RRRR/N`, označení normy) zajišťuje, že týž
   dokument nalezený více zdroji vznikne jen jednou a že zamítnutý kandidát
   se znovu neotevře; seznam zdrojů, jež dokument zachytily, je zároveň
   podkladem pro provenance (`doc/DATABASE_SCOPE.md`, odstavec 7, bod 2).
2. **Jednotný tvar nálezu.** Adaptér vrací pro každý nález: identifikátor
   zdroje, druh signálu, klíč kandidáta (je-li odvoditelný), označení,
   název, adresu, datum a doslovný doklad (úryvek ze zdroje). Nález bez
   odvoditelného klíče se do fronty dostane také, ale s příznakem k ručnímu
   doplnění, nikoli s odhadnutým klíčem.
3. **Návrhy předpisů jsou kandidáti zvláštního druhu.** Signál `draft`
   (připravovaný předpis) vede po přijetí na dokument ve stavu
   „připravovaný“ (`draft`, jenž schéma již zná); po vyhlášení jej kontrola
   platnosti převede na vyhlášený nebo účinný a propojí s vyhlášeným
   předpisem.
4. **Každý běh se zaznamená**, i když nic nepřinese: zdroj, čas, rozsah
   dotazu, počet nálezů, chyba (`doc/DATABASE_SCOPE.md`, odstavec 6).
   Prvním krokem bude soubor záznamů, později tabulka `source_check`
   (odstavec 7).
5. **Adaptér nezapisuje do databáze dokumentů.** Do databáze zapisuje jen
   přijetí kandidáta editory a kontrola platnosti; adaptéry jen čtou zdroj
   a plní frontu, takže je lze spouštět opakovaně a bez rizika.
6. **Zdroj bez adaptéru se přeskočí a ohlásí**, nikdy se nezpracuje podle
   domněnky (obdobně jako tabulka `SOURCE_HANDLING` na větvi `automation`).

Pole `signal` nabývá těchto hodnot:

| Hodnota | Co zdroj přináší | Kam nález vede | Počet zdrojů |
|---|---|---|---|
| `new_document` | Nový dokument v rozsahu databáze. | Fronta kandidátů. | 33 |
| `draft` | Návrh předpisu v legislativním procesu (včasný signál). | Fronta kandidátů, stav „připravovaný“. | 12 |
| `state_change` | Zrušení, novelizace, nabytí účinnosti, nahrazení normy u dokumentu, jejž databáze již má. | Kontrola platnosti a stavy dokumentů. | 6 |
| `lookup` | Dohledání na vyžádání pro konkrétní dokument nebo místo záměru; zdroj se pravidelně neprochází. | Editor při posuzování. | 7 |
| `context` | Rámcové a odborné podklady, upozornění; samy pramenem záznamu nejsou. | Čtvrtletní kontrolní seznam pro editora. | 16 |
| `link_check` | Jen údržba odkazů. | Hlášení nefunkčních odkazů. | 1 |

Zdroj může nést více hodnot (EUR-Lex, e-Sbírka a Věstník ÚNMZ přinášejí
nové dokumenty i změny stavu). Zakázané a zavržené zdroje mají seznam prázdný.

### 4.3 Etapy

Etapy jsou seřazeny sestupně podle poměru přínosu k pracnosti; v rámci etapy
postupujeme podle priority zdroje. Každá etapa končí testy adaptérů nad
uloženými ukázkovými odpověďmi zdrojů (bez síťového přístupu) a zkušebním
během proti `h2regdocs_test`.

**E0 — Základ (bez nových zdrojů).** Spouštěč `harvest_sources.py`, jenž čte
registr a podle pole `stage`, `cadence` nebo identifikátoru volá adaptéry;
jednotný tvar nálezu; zápis do fronty kandidátů s identifikátorem zdroje
a s druhem `draft`; záznam o každém běhu; **kontrola dostupnosti** všech
78 adres registru (`url`, `access.endpoint`), jež hlásí změněné a nefunkční
adresy a aktualizuje `verified_at`. Kontrola dostupnosti je levná, týká se
i ručně kontrolovaných zdrojů a ověření z 28. 10. 2026 ukázalo, že ji
potřebujeme (odstavec 3.1).

*Stav 29. 10. 2026: provedeno.* Spouštěč `src/tools/harvest_sources.py`,
knihovna `harvest.py` (tvar nálezu, zápis do fronty, záznam běhů
`data/source_checks.jsonl`), modul registru `source_registry.py` a kontrola
dostupnosti `check_sources.py`; fronta kandidátů má sloupec `signal`, ukazuje
nálezy jednotlivých zdrojů a přijatý návrh předpisu zakládá jako dokument ve
stavu „připravovaný“. Tabulka adaptérů je zatím prázdná, spouštěč tedy všechny
zdroje přeskočí a ohlásí. První kontrola dostupnosti: 62 zdrojů v pořádku,
4 zablokované podle očekávání, 5 zakázaných jsme nestahovali. Šest webů
(Slov-Lex dvakrát, ASTM, IEC, EIGA, Baker McKenzie) odpovídá robotu, který se
poctivě identifikuje, kódem 403; u IEC a EIGA šlo o známou ochranu, u Slov-Lexu
a ASTM o změnu proti ověření ze září. Zda tyto zdroje převést do stavu
`blocked`, rozhodneme při jejich zapojení (Slov-Lex legislatívny proces patří
do etapy E2); jinou identifikaci robota, jež by kontrolu webu obcházela,
nepoužíváme. Kanál RSS VeKLEPu při kontrole neodpověděl včas, jeho rozhraní
JSON ano. Podrobně odstavec 8.

**E1 — Převod stávající automatizace (10 zdrojů).** `eurlex-cellar`,
`esbirka-lod`, `slovlex-linkcheck`, `csn-online`, `normoff-stn`,
`iec-catalogue`, `dvgw-publications`, `eiga-publications`, `hytep`,
`zakonyprolidi`. Stávající skripty se stanou adaptéry spouštěče: místo
souborů `discovered_*.json` budou plnit frontu kandidátů, filtr
`classify_candidate()` a `is_off_topic()` ze skriptu
`add_eurlex_hydrogen_acts.py` se přesune do filtru věcné příslušnosti.
Soubory `discovered_*.json` vzniklé dříve zůstanou vstupem přestavby, nové
však již nepřibudou. Nálezy e-Sbírky, jež nelze přiřadit předpisu
(`doc/AUTOMATION.md`, odstavec 4.1), půjdou do fronty s příznakem k ručnímu
doplnění.

*Stav 4. 11. 2026: provedeno s výhradami.* Adaptéry pěti zdrojů
(`src/tools/harvest_adapters.py`: EUR-Lex, e-Sbírka, katalog ČSN, registr STN,
HYTEP) spouštěč volá; zakonyprolidi.cz je obsažen v kontrole platnosti
e-Sbírky. Čtyři zdroje spouštěč výslovně odkládá, protože jejich stávající
skripty obcházejí ochranu webů proti robotům nebo web robota odmítá
(Slov-Lex, IEC, EIGA, DVGW); o nich zbývá rozhodnout. Nálezy e-Sbírky se nově
daří přiřadit k předpisu. Ostrý zápis jsme ověřili nad testovací databází;
do živé fronty zatím nevstoupil. Podrobně odstavec 8.7.

**E2 — Včasný signál (5 zdrojů).** `veklep-odok` (A), `slovlex-legislativny-proces`
(A), `psp-snemovni-tisky`, `senat-tisky`, `ep-oeil`. Všechny mají ověřenou
strojově čitelnou cestu (JSON, RSS, hromadná otevřená data). Zavádí do
databáze připravované předpisy a jejich převod na vyhlášené.

*Stav 4. 11. 2026: provedeno pro čtyři zdroje.* VeKLEP (přes kanál RSS, jeho
rozhraní JSON robota blokuje), sněmovní a senátní tisky a Legislative
Observatory spouštěč volá (`src/tools/harvest_drafts.py`); Slov-Lex
legislatívny proces odkládá, protože web robota odmítá. Návrh, který najde více
zdrojů, je jedním kandidátem. Převod připravovaného předpisu na vyhlášený
zatím proveden není. Podrobně odstavec 8.10.

**E3 — Normy, jen metadata (8 zdrojů).** `ec-harmonised-standards` (A),
`vestnik-unmz`, `unmz-news`, `astm-d03`, `asme-codes`, `cps-tpg`,
`sae-standards`, `vestnik-unms-sr`. Měsíční přírůstky ČSN z Věstníku ÚNMZ
nahradí dotazování po jednotlivých označeních; souhrnné seznamy
harmonizovaných norem doplní vazbu norma → směrnice.

**E4 — Kanály RSS ministerstev, orgánů a agentur (13 zdrojů).**
`mmr-stavebni-pravo` (A), `mzp-cz` (A), `coi` (A), `otif-rid` (A), `mpo-cz`,
`suip`, `du-rid`, `acer`, `era-railways`, `ehsp`, `mhsr-vodikova-strategia`,
`cizp`, `eru-cz`. Jeden společný adaptér RSS s filtrem podle vyhledávacích
výrazů (odstavec 6); kanály nesou obecné zprávy úřadů, takže přínos závisí
na kvalitě filtru, již bude třeba vyhodnotit na prvních během.

**E5 — Sběr z HTML a dohledání na vyžádání (15 zdrojů).** Pravidelně
procházené: `ticr` (A), `hzs-cr` (A), `cmi-oop` (A), `md-adr` (A), `ec-tris`,
`ec-have-your-say`, `european-hydrogen-observatory`,
`dg-ener-hydrogen-gas-market`, `dg-ener-hydrogen`, `nfpa-2`; změnu stránky
lze zjišťovat porovnáním otisku obsahu nebo pole data poslední změny. Na
vyžádání: `sbirka-pp-usc`, `is-eia`, `echa-chem`, `data-europa-search`,
`gesetze-im-internet` — pro ně postačí funkce dohledání volaná z editorského
rozhraní nebo z příkazové řádky, nikoli pravidelný běh.

**E6 — Zdroje vyžadující správní krok nebo rozhodnutí (9 zdrojů).**
`e-legislativa` (A) a REST API e-Sbírky (položka `esbirka-lod`) zpřístupní
jedna registrace podáním do datové schránky Ministerstva vnitra; podání je
vhodné učinit hned, protože posouzení trvá až deset pracovních dní a VeKLEP
postupně přestane návrhy pokrývat. `unece-wp29` (A),
`unece-dangerous-goods` (A), `ec-comitology-register` (A), `ec-regdel`,
`council-public-register`, `ec-documents-register`, `ec-nando` a `baua`
jsou za ochranou proti robotům nebo jde o aplikace vykreslované až
v prohlížeči. U aplikací bez ochrany (komitologie, rejstřík aktů v přenesené
pravomoci, registr dokumentů Komise, NANDO) postačí headless prohlížeč, jaký
již používá sklizeň IEC. U webů chráněných proti robotům (`unece.org`, registr
Rady EU, `baua.de`) obcházet ochranu nenavrhujeme: provozovatel jí dává
najevo, že automatizovaný přístup nepřeje. Náhradní cestou je ruční kontrola
(předpisy EHK OSN a ADR se mění zpravidla v dvouletém cyklu), u ADR, RID
a ADN též jejich vyhlášení ve Sbírce mezinárodních smluv přes e-Sbírku.

**Ruční kontrola (12 zdrojů).** Zdroje se stavem `manual_only` (`stage`
„manual“) spouštěč nevolá; vypíše je jednou za čtvrtletí jako kontrolní
seznam s datem poslední kontroly, jejíž výsledek editor zaznamená stejně
jako automatizovaný běh.

**Mimo plán (6 zdrojů).** Zakázané (`prohibited`) a zavržené (`rejected`)
zdroje nevytěžujeme; náhradní cesty jsou uvedeny v jejich poli
`constraints`.

### 4.4 Způsob zapojení zdroje

U každého zdroje volíme způsob zapojení v tomto pořadí:

1. Oficiální API nebo otevřený datový export, je-li dostupný a jeho užití
   povolené.
2. Oficiální kanál RSS, služba upozornění nebo seznam změn.
3. Strukturované procházení webu v mezích podmínek provozovatele
   a `robots.txt`.
4. Ruční rešerše a odborné ověření, zejména u placených norem, metodik
   a právně významných výkladů.

Webová stránka se může změnit, i když její obsah přetrvává; adaptéry proto
mají počítat s náhradními adresami a s chybami přístupu a kontrola
dostupnosti (etapa E0) má jejich selhání zachytit dříve, než se projeví
jako tichý výpadek signálu.

### 4.5 Plánované spouštění

Spouštěč poběží podle pole `cadence`: týdně registry předpisů a návrhů
(etapy E1 a E2), měsíčně normy a kanály orgánů (E3 až E5), čtvrtletně
kontrolní seznam ruční kontroly a měření úplnosti (`doc/DATABASE_SCOPE.md`,
odstavec 6). Pravidelné spouštění (cron nebo časovač systemd na serveru,
z něhož běží databáze) dosud neexistuje a zda je v rozsahu této fáze
projektu, zůstává otevřenou otázkou požadavku R1.9 (`doc/AUTOMATION.md`,
odstavec 8, bod 1). Do jejího rozhodnutí lze spouštěč spouštět ručně se
stejným výsledkem; plánovač se pak omezí na volání téhož příkazu.

### 4.6 Rozhodnutí, jež plán předpokládá

1. **Jediná vstupní brána.** Navrhujeme, aby všechny nálezy vedly do fronty
   kandidátů a nové soubory `discovered_*.json` již nevznikaly (odstavec 4.2,
   bod 1).
2. **Agentní zpracování.** Vrstva z větve `automation` by v tomto tvaru
   nepsala vlastní výstupní soubor, ale doplňovala by kandidáty ve frontě
   o ověřené údaje z plného textu (označení, název, druh, gestor s doslovnými
   citacemi) jako podklad pro editora. Tím by odpadl chybějící článek popsaný
   v `doc/AUTOMATION.md`, odstavec 6.3. Na větvi `master` však dosud platí
   zamítnutí této architektury (`doc/PLAN.md` §5); plán proto na agentní
   vrstvě nezávisí a etapy E0 až E5 lze provést bez ní.
3. **Registrace k REST API e-Sbírky a e-Legislativy** (etapa E6) — podání
   učiní Ministerstvu vnitra člen řešitelského týmu.
4. **Plánovač** (odstavec 4.5) — rozhodnutí přísluší zadavateli.

## 5. Zpracování nálezu

Automatizovaně zachycená změna **není právním posouzením**. Nález ze
sledovaného zdroje se stává kandidátem ve frontě kandidátů
(`/admin/candidates`, `app/candidates_admin.py`), kde jej editoři posuzují;
dokument vznikne až po návrhu jednoho editora a potvrzení druhým. Při
posouzení postupujeme takto:

1. Identifikujeme dokument v jednom nebo více zdrojích a zaznamenáme jeho
   původ.
2. Normalizujeme identifikátor (číslo předpisu ve Sbírce, CELEX nebo ELI,
   označení ČSN, EN nebo ISO, identifikátor metodiky).
3. Ověříme autoritativní znění a samostatně zaevidujeme jeho verze, platnost
   a účinnost (`doc/DATABASE_SCOPE.md`, odstavec 5), včetně přechodných
   ustanovení.
4. Posoudíme relevanci pro konkrétní typ zařízení, činnost a fázi záměru.
5. Vytvoříme vazby mezi právním aktem, prováděcím předpisem, normou,
   metodikou a procesním uzlem.
6. Neověřené vazby, nejasnou použitelnost nebo licenční omezení označíme
   jako otevřený bod (příznak `needs_review` s odůvodněním).

## 6. Vyhledávací výrazy

Vyhledávání nelze omezit na dokumenty obsahující slovo „vodík“; značná část
požadavků plyne z obecných předpisů pro tlaková zařízení, hořlavé plyny,
stavby, nebezpečné věci, životní prostředí nebo měřidla
(`doc/DATABASE_SCOPE.md`, odstavec 3). Pro filtrování kanálů a dotazy do
registrů navrhujeme tyto výrazy:

| Jazyk | Základní výrazy | Rozšiřující oblasti |
|---|---|---|
| čeština | vodík, vodíkový, elektrolyzér, elektrolýza, palivový článek, plnicí stanice | tlaková zařízení, plynová zařízení, hořlavý plyn, ATEX, ochrana před výbuchem, vyhrazená technická zařízení, přeprava nebezpečných věcí, metrologie, jakost paliva |
| angličtina | hydrogen, electrolysis, electrolyser / electrolyzer, fuel cell, hydrogen refuelling / refueling station | pressure equipment, explosive atmospheres, dangerous goods, hydrogen purity, fuel quality, conformity assessment, RFNBO, low-carbon hydrogen |
| němčina | Wasserstoff, Elektrolyseur, Brennstoffzelle, Wasserstofftankstelle | Druckgeräte, Explosionsschutz, Gefahrgut, Genehmigungsverfahren, Wasserstoffqualität |

Výrazy z rozšiřujících oblastí je vhodné kombinovat s konkrétním procesem,
technologií, druhem regulace nebo identifikátorem předpisu; samy o sobě by
patrně přinesly nepřiměřené množství nerelevantních výsledků.

## 7. Výhled: registr jako součást databáze

Registr je dnes souborem JSON. Pro auditovatelné sledování bude patrně
vhodné převést jej do databáze a oddělit **zdroj**, **vstupní bod zdroje**,
**kontrolu** a vazbu **dokument–zdroj**. Následující názvy jsou návrhem, nikoli
popisem současného schématu:

| Entita | Účel | Příklady údajů |
|---|---|---|
| `source` | Identita zdroje. | Označení, název, provozovatel, jurisdikce, role, priorita, věcné okruhy. |
| `source_endpoint` | Jednotlivé weby, rozhraní a kanály zdroje. | Adresa, druh rozhraní, formát, autentizace, licence, stav ověření, četnost. |
| `source_check` | Záznam o každé kontrole. | Čas, výsledek, stav HTTP, počet nových a změněných záznamů, chyba. |
| `document_source` | Původ dokumentu a jeho alternativní umístění. | Dokument, zdroj, adresa, datum zachycení, preferovaný zdroj. |

Tabulka `source_check` by naplnila požadavek zaznamenávat i kontroly, jež nic
nového nepřinesly (`doc/DATABASE_SCOPE.md`, odstavec 6), a `document_source`
požadavek na provenance (tamtéž, odstavec 7, bod 2). Identitu, verze, vazby
a věcné okruhy dokumentů již databáze vede (`Document`, `DocumentVersion`,
vazby `REPEALS`, `AMENDS`, `IMPLEMENTS`).

Proti dnešním polím registru by u zdroje přibyly tyto údaje:

1. **Provozovatel** zdroje (dnes jen v poli `name`).
2. **Věcné okruhy** podle `doc/DATABASE_SCOPE.md`, odstavec 3.
3. **Právní dostupnost** odděleně od technické: licence, možnost vytěžování,
   archivace a zveřejnění textů, požadavky na uvedení zdroje, zpoplatnění
   (dnes souhrnně v poli `constraints`).
4. **Provozní údaje**: poslední úspěšná kontrola, poslední zjištěná změna,
   technický stav a odpovědná osoba.

## 8. Provoz vytěžování

Tento odstavec popisuje, jak se nástroje etapy E0 (odstavec 4.3) používají,
co zaznamenávají a jaký výsledek přinesla jejich první ostrá kontrola. Nástroje
jsou v adresáři `src/tools/` a spouštějí se interpretem hlavního stromu
(`.venv/bin/python`).

### 8.1 Nástroje

| Nástroj | Účel |
|---|---|
| `source_registry.py` | Čtení a zápis registru se zachováním jeho formátu (změna jednoho pole mění jediný řádek), kontrola slovníku hodnot (`validate()`) a výběr zdrojů běhu (`select()`). |
| `harvest.py` | Jednotný tvar nálezu (`Finding`), zápis nálezů do fronty kandidátů, vyhledávací výrazy z odstavce 6 a záznam běhů. |
| `harvest_sources.py` | Spouštěč: vybere zdroje, zavolá jejich adaptéry a nálezy zapíše do fronty. |
| `check_sources.py` | Kontrola dostupnosti všech adres registru. |

Spouštěč vybírá zdroje podle identifikátoru, etapy nebo četnosti:

```
.venv/bin/python src/tools/harvest_sources.py --stage E2            # suchý běh etapy
.venv/bin/python src/tools/harvest_sources.py --cadence weekly --apply
.venv/bin/python src/tools/harvest_sources.py --source veklep-odok --apply --env-file .env.test
.venv/bin/python src/tools/harvest_sources.py --checklist           # ručně kontrolované zdroje
.venv/bin/python src/tools/harvest_sources.py --record imo-imdg --note "beze změny" --found 0
.venv/bin/python src/tools/check_sources.py [--source ID ...] [--apply]
```

Bez volby `--apply` oba nástroje provedou jen suchý běh: spouštěč nálezy
vypíše, ale do databáze nezapíše, kontrola dostupnosti nezmění registr. Běh se
však zaznamená v obou případech, s příznakem, zda šlo o ostrý běh.

Adaptéry deklaruje výslovně tabulka `ADAPTERS` ve spouštěči (identifikátor
zdroje → `modul:funkce`). Adaptér dostane záznam zdroje z registru, sezení HTTP
a čas posledního úspěšného ostrého běhu téhož zdroje a vrací seznam nálezů.
Zdroj bez adaptéru spouštěč přeskočí a ohlásí, stejně jako zdroje ruční kontroly,
zdroje k dohledání na vyžádání (signál `lookup` nebo `context`) a zdroje
zakázané či zavržené. Selhání jednoho zdroje se zaznamená a běh pokračuje
dalším.

### 8.2 Nález a jeho cesta do fronty

Nález nese identifikátor zdroje, druh signálu, klíč kandidáta (je-li odvoditelný),
označení, název, adresu, datum a doslovný úryvek ze zdroje. Nález bez
odvoditelného klíče dostane klíč vlastní ve tvaru `<zdroj>:<identifikátor
položky>` a příznak, že označení předpisu je třeba doplnit ručně; klíč se nikdy
neodhaduje.

Nálezy se signálem `new_document` a `draft` se zapisují do fronty kandidátů
(tabulka `DocumentCandidate`, `/admin/candidates`):

1. Dokument, jejž databáze již obsahuje, se nezapíše a započte se jako známý.
2. Nový kandidát dostane metadata nálezu a jako zdroj identifikátor zdroje
   z registru; sloupec `signal` rozliší návrh předpisu od vyhlášeného dokumentu.
3. Kandidát, jejž již dříve ohlásila kontrola nebo jiný zdroj, dostane nález
   připsaný do svých dokladů (`evidence.findings`, jeden záznam na zdroj); datum
   prvního zachycení zůstává zachováno. Seznam zdrojů, jež dokument zachytily, je
   podkladem pro provenance (`doc/DATABASE_SCOPE.md`, odstavec 7, bod 2).
4. Kandidát, o němž editoři již rozhodli (přijat, zamítnut), se nemění.

Nálezy se signálem `state_change` se zatím jen počítají; do kontroly platnosti
je zapojí etapa E1. Detail kandidáta v editorském rozhraní ukazuje nálezy
jednotlivých zdrojů s datem, adresou a úryvkem; seznam kandidátů lze filtrovat
podle zdroje z registru. Přijatý návrh předpisu (signál `draft`) vznikne jako
dokument ve stavu „připravovaný“.

### 8.3 Záznam běhů

Soubor `data/source_checks.jsonl` nese jeden záznam JSON na řádek a pouze se
připisuje. Rozlišujeme tři druhy záznamů:

| Druh (`kind`) | Zapisuje | Obsah |
|---|---|---|
| `harvest` | `harvest_sources.py` | Zdroj, čas, ostrý či suchý běh, adaptér, čas, od něhož adaptér pokračoval, počet nálezů podle signálu, výsledky zápisu (vloženo, doplněno, ponecháno, známé), případná chyba. |
| `availability` | `check_sources.py` | Zdroj, čas, verdikt a u každé adresy stav HTTP, konečná adresa po přesměrování a výsledek. |
| `manual` | `harvest_sources.py --record` | Zdroj, čas, počet nových dokumentů a poznámka editora. |

Záznam vzniká i tehdy, když běh nic nepřinesl: doložené negativní výsledky jsou
součástí tvrzení o úplnosti (`doc/DATABASE_SCOPE.md`, odstavec 6). Dalšímu běhu
zdroje předá spouštěč čas posledního úspěšného ostrého běhu, takže adaptér může
dotaz omezit na novější položky.

### 8.4 Kontrola dostupnosti

Kontrola stáhne vstupní adresu každého zdroje a adresy z polí `access.endpoint`
a `access.feed`; přeskočí zakázané zdroje (jejich `robots.txt` stahování
zapovídá) a šablony adres. Na jednu doménu posílá nejvýše jeden požadavek za
sekundu a robota identifikuje poctivě (`NAHYC-DP004-harvest`). Každá adresa
dostane výsledek `ok` (2xx), `auth` (401), `blocked` (403, 429 nebo stránka
ochrany proti robotům), `missing` (404, 410), `reachable` (jiná odpověď 4xx,
typicky rozhraní volané bez parametrů), `server_error` (5xx) nebo
`unreachable` (bez odpovědi). Zdroj pak dostane verdikt:

| Verdikt | Význam |
|---|---|
| `ok` | Vstupní adresa odpovídá a žádná další adresa nechybí. |
| `as_expected` | Zdroj vedený jako `blocked` je stále za ochranou nebo za přihlášením. |
| `blocked` | Zdroj, jenž jako `blocked` veden není, odmítá robota. |
| `moved` | Vstupní adresa přesměrovává na jinou doménu. |
| `endpoint_problem` | Vstupní adresa odpovídá, rozhraní nebo kanál ne. |
| `broken` | Vstupní adresa neexistuje nebo neodpovídá. |

Verdikt `ok` říká, že adresa odpovídá, nikoli že je její obsah strojově
použitelný: aplikace vykreslovaná až v prohlížeči vrací obal stránky s kódem
200. S volbou `--apply` dostanou zdroje s verdiktem `ok` nebo `as_expected`
v poli `verified_at` dnešní datum; hodnotu `null` (zdroj v aktivním používání)
kontrola ponechá. Jiné pole registru nemění: přesunutou nebo nefunkční adresu
má opravit člověk.

### 8.5 Výsledek první kontroly (28. 10. 2026)

Kontrola proběhla 28. 10. 2026 mezi 22:55 a 22:57 UTC nad 73 zdroji a 113
adresami; pět zakázaných zdrojů jsme nestahovali. Výsledky adres: 99 `ok`,
11 `blocked`, po jedné `reachable`, `auth` a `unreachable`. Verdikty zdrojů:

| Verdikt | Počet | Zdroje |
|---|---|---|
| `ok` | 62 | Ostatní zdroje; mezi nimi i pět zdrojů vedených jako `blocked` kvůli aplikaci vykreslované v prohlížeči (e-Legislativa, rejstřík komitologie, rejstřík aktů v přenesené pravomoci, registr dokumentů Komise, NANDO) |
| `as_expected` | 4 | `unece-wp29`, `unece-dangerous-goods`, `council-public-register`, `baua` (HTTP 403) |
| `blocked` | 6 | `slovlex-linkcheck`, `slovlex-legislativny-proces` (vstupní adresa i kanál RSS), `astm-d03`, `iec-catalogue`, `eiga-publications`, `bakermckenzie-hydrogen-tracker` (HTTP 403) |
| `endpoint_problem` | 1 | `veklep-odok` — kanál RSS nedoběhl do 20 s, rozhraní JSON odpovědělo |
| `moved`, `broken` | 0 | — |

Kontrola obnovila datum `verified_at` u 23 zdrojů. Ze šesti zdrojů, jež nově
odmítají robota, je ochrana u IEC (AWS WAF, kvůli němuž stávající sklizeň
`harvest_iec_publications.py` používá headless prohlížeč) a u EIGA (stávající
modul `src/sites/eiga.py` volí upravený dotaz) známá a v registru popsaná; u Slov-Lexu a ASTM jde o změnu
proti ověření z 20. 9. 2026, kdy oba zdroje strojově čitelný přístup nabízely.
Zjištění jsme u všech šesti připsali do pole `constraints`, stav jsme však
nezměnili; rozhodneme o něm při zapojení zdroje. Zvlášť se to týká zdroje
`slovlex-legislativny-proces`, jenž má prioritu A a patří do etapy E2. Jinou
identifikaci robota, jež by kontrolu webu obcházela, nepoužíváme: provozovatel
jí dává najevo, že automatizovaný přístup nepřeje, a správnou cestou je patrně
požádat jej o přístup nebo zdroj sledovat ručně.

### 8.6 Nasazení a ověření

Etapa E0 je na větvi `feature/harvest-e0`, odvozené z větve
`feature/h2db-sources`; slučovat ji lze až po ní. Živou databázi `h2regdocs`
etapa zatím nezměnila. Sloupec `signal` tabulky `DocumentCandidate` se do ní
doplní sám při prvním ostrém běhu spouštěče nebo skriptu `import_candidates.py`
proti živé databázi (`candidates.ensure_schema()`); jde o přidaný sloupec, jenž
smí zůstat prázdný, před tímto během je však podle zvyklosti projektu vhodné
pořídit zálohu do adresáře `backups/`. Do té doby editorské rozhraní funguje
i bez sloupce.

Etapu ověřují testy `tests/test_source_registry.py` (včetně kontroly, že vložený
registr je konzistentní a zapisuje se beze změny), `tests/test_harvest.py`,
`tests/test_harvest_sources.py`, `tests/test_check_sources.py` a nový scénář
v `tests/test_candidates_admin.py` (návrh předpisu nalezený zdrojem až po
dokument ve stavu „připravovaný“, nad databází `h2regdocs_test`). Testy se obejdou
bez síťového přístupu. Celý běh `src/tools/run_tests.py` 29. 10. 2026 prošel
(unit, integrační, smoke a prohlížečové testy). Vzhled nového bloku s nálezy
v detailu kandidáta ověřuje jen test obsahu stránky; snímek obrazovky jsme
nepořídili.

### 8.7 Etapa E1 (4. 11. 2026)

Etapa převedla stávající automatizaci pod spouštěč. Adaptéry jsou v modulu
`src/tools/harvest_adapters.py` a používají funkce skriptů, jež nahrazují;
způsob dotazování zdrojů nemění. Jeden zdroj může mít více adaptérů, jeden na
každý druh nálezu:

| Zdroj | Adaptér | Co přináší |
|---|---|---|
| `eurlex-cellar` | `eurlex_new` | Závazné akty EU (CELEX R, L, D) s „hydrogen“ nebo „RFNBO“ v názvu, bez vzorů chemických a správních nálezů ze skriptu `add_eurlex_hydrogen_acts.py`; klíč `EU:rok/číslo` z čísla CELEX. Klasifikaci jazykovým modelem adaptér nepoužívá: nejisté případy posoudí editor ve frontě. |
| `eurlex-cellar` | `validity_eu` | Platnost aktů EU v databázi z Cellaru (funkce `check_validity.eu_status()`). |
| `esbirka-lod` | `esbirka_new` | České předpisy, jež databáze nemá a jejichž poslední znění obsahuje slovo „vodík“ a je účinné (viz níže). |
| `esbirka-lod` | `validity_cz` | Platnost českých předpisů v databázi z e-Sbírky, zrušující předpis ze zakonyprolidi.cz (`check_validity.cz_status()`). |
| `csn-online` | `csn_state` | Platnost norem ČSN v databázi z bezplatného katalogu ČSN. |
| `normoff-stn` | `normoff_state` | Platnost norem STN v databázi z registru ÚNMS SR. |
| `hytep` | `hytep_new` | Dokumenty ze dvou seznamů HYTEP; nemají označení, databáze je zná podle adresy. |

Kontroly platnosti procházejí jen dokumenty, jejichž záznam v mezipaměti chybí
nebo je starší než 30 dní. Změny stavu zapisuje ostrý běh do mezipaměti
kontroly platnosti (`data/validity_cache.json`), odkud je do stavů dokumentů
promítá `backfill_document_states.py` jako dosud; stav norem jde do nové
mezipaměti `data/norm_validity_cache.json`, protože stavy norem databáze zatím
nerozlišuje (`doc/DATABASE_SCOPE.md`, odstavec 5). Katalog ČSN i registr STN jsou
určeny pro cílené dotazy, oba zdroje proto mají četnost „na vyžádání“
a pravidelný běh je nevolá; volba `--limit N` omezí zkušební běh na N dokumentů.

**Odložené zdroje.** Spouštěč je vynechá a důvod ohlásí (tabulka `DEFERRED`):

1. `slovlex-linkcheck` — Web od 28. 10. 2026 odmítá poctivě identifikovaného
   robota kódem 403 (odstavec 8.5).
2. `iec-catalogue` — Stávající sklizeň prochází ochranou AWS WAF Bot Control
   pomocí headless prohlížeče.
3. `eiga-publications` — Stávající modul se ochraně WAF vyhýbá upraveným
   dotazem.
4. `dvgw-publications` — Stávající sklizeň se vydává za prohlížeč (hlavička
   User-Agent).

U bodů 2 až 4 jde o obcházení ochrany, jíž provozovatel dává najevo, že
automatizovaný přístup nepřeje. Do pravidelného běhu je proto bez rozhodnutí
nezapojujeme; náhradou pro IEC je patrně webstore `webstore.iec.ch`, jenž je
čitelný bez prohlížeče a jehož `robots.txt` nic nezakazuje (odstavec 3.1).
Zdroj `zakonyprolidi` není samostatně spouštěn, protože jej využívá adaptér
`validity_cz`.

**Přiřazení nálezů e-Sbírky k předpisu.** Dosavadní screening vracel zásahy do
textu (fragmenty), u nichž neuměl určit předpis (`doc/AUTOMATION.md`,
odstavec 4.1). Ověřením jsme zjistili, že fragment je v otevřených datech
připojen k uzlu ELI svého znění vlastností `obsahuje-fragment` (binární soubor
o krok dál vlastností `má-binární-soubor`) a že adresa uzlu nese rok, číslo
a datum znění (`…/eli/cz/sb/2015/294/2025-07-01/dokument/…`). Adaptér proto
nejprve najde všechny uzly se slovem „vodík“, seskupí je podle předpisu a znění,
u předpisů, jež databáze nemá, zjistí jejich poslední znění a konec jeho
účinnosti, a ponechá jen předpisy, jejichž poslední znění slovo obsahuje
a dosud platí. Dosavadní screening měl navíc limit 100 výsledků a odpověď
ořezával, aniž by to ohlásil; adaptér oříznutí odpovědi považuje za chybu.

**První běhy (4. 11. 2026).** Suché běhy nad živou databází a ostrý běh nad
`h2regdocs_test`:

| Adaptér | Výsledek |
|---|---|
| `eurlex_new` | 15 závazných aktů, všechny již v databázi. |
| `validity_eu`, `validity_cz` | Žádný dokument ke kontrole (mezipaměť z 27. 10. 2026 je mladší než 30 dní). |
| `esbirka_new` | Slovo „vodík“ obsahuje 364 předpisů (8 411 míst v textu ve všech zněních); z nich 185 předpisů databáze nemá a jejich poslední znění je účinné. Ostrý běh vložil 177 kandidátů a u 8 kandidátů, jež již ohlásil uzávěr citací, nález připsal k dokladům. |
| `hytep_new` | 19 dokumentů, z toho 1 nový („Politicko-strategický, legislativní a nelegislativní rámec EU pro rozvoj…“). |
| `csn_state` | 39 norem ČSN v databázi: 7 zrušených (mj. ČSN EN 1717, ČSN EN 50128, ČSN EN 50129, ČSN EN 62282-3-200), ostatní platné. |
| `normoff_state` | Zkušební běh na 5 normách (397 STN v databázi): u 4 nezjištěno, viz níže. |

Opakovaný ostrý běh nad testovací databází nic nevložil a jen obnovil doklady
(185 kandidátů e-Sbírky, 1 HYTEP); bod, od něhož adaptér pokračuje, se
posunul. Záznam běhu nese název databáze, takže běh nad testovací databází
neovlivní běhy nad živou.

Mezi 185 předpisy e-Sbírky jsou dokumenty věcně patrně velmi cenné, jež
databáze dosud nemá: například 87/2025 Sb. (vodíková přepravní soustava),
369/2025 Sb. (výrobna vodíku), 42/2025 Sb. (dodání vodíku na čerpací stanici),
413/2025 Sb. (obsah vodíku ve směsi plynu) nebo 443/2025 Sb. (transpozice
směrnice (EU) 2024/1788). Vedle nich je však i šum: chemické tabulky
expozičních limitů, sazebníky, rozbory potravin a 17 předpisů z let 1925 až
1989. Značnou část tvoří novely. Výběr nefiltrujeme podle roku ani podle počtu
výskytů; posouzení přísluší editorům, frontu je však vhodné procházet
s vědomím, že jde zhruba o 185 kandidátů najednou. Rozbor těchto kandidátů
a návrh, jak šum omezit, uvádíme v odstavci 8.8.

**Otevřené body.**

1. **Ostrý běh proti živé databázi.** Dosud neproběhl. Doplní do tabulky
   `DocumentCandidate` sloupec `signal` a vloží zhruba 186 kandidátů; před ním
   je vhodné pořídit zálohu do `backups/` a v živé databázi musí existovat
   alespoň dva editorské účty (`src/db/dbuser_add.py`), jinak kandidáty nikdo
   nepřijme.
2. **Odložené zdroje** (IEC, EIGA, DVGW, Slov-Lex) — rozhodnutí, zda je
   zapojit, nahradit jinou cestou (webstore IEC), nebo sledovat ručně.
3. **Označení norem STN.** Řada STN je v databázi zapsána s datem vydání
   (`STN 07 8304/ - 1989.01`); registr ÚNMS takové označení přesně nenajde.
   Označení neupravujeme odhadem, protože by se tím mohl převzít stav jiného
   vydání normy.
4. **Stavy norem v databázi.** Výsledky kontroly ČSN a STN zatím zůstávají
   v mezipaměti; jejich promítnutí do stavů dokumentů předpokládá rozšíření
   stavů podle `doc/DATABASE_SCOPE.md`, odstavec 5.
5. **Dosavadní skripty.** `screen_eurlex.py`, `screen_esbirka.py`
   a skripty `add_*` zůstávají v repozitáři a soubory `discovered_*.json`
   zůstávají vstupem přestavby; nové nálezy však již vedou do fronty
   kandidátů.

### 8.8 Šum v nálezech e-Sbírky a návrh jeho omezení

Všech 185 předpisů, jež adaptér `esbirka_new` 4. 11. 2026 nalezl, jsme
roztřídili; rozbor je v souboru `data/esbirka_candidates_20261104.csv` (klíč,
název ze zakonyprolidi.cz, rok, druh, počet výskytů v posledním znění, z toho
v novelizačních bodech a v přílohách, měněný předpis a pásmo). Pro třídění
jsme využili strukturu otevřených dat: adresa uzlu, v němž se slovo vyskytuje,
prozrazuje, zda jde o novelizační bod (`…/dokument/novela/…`) nebo o přílohu
(`…/dokument/prilohy/…`). Toto vodítko je spolehlivější než název předpisu,
jenž jsme použili jen doplňkově.

| Skupina | Počet | Charakter |
|---|---|---|
| Novely předpisu, jenž je sám kandidátem | 63 | Novela vložila zmínku o vodíku do předpisu, jenž je mezi kandidáty také (například osm novel nařízení vlády č. 361/2007 Sb.). |
| Novely předpisu, jejž databáze má | 11 | Například 42/2025 Sb. a 172/2018 Sb. (zákon o ochraně ovzduší), 223/2025 Sb. a 469/2023 Sb. (energetický zákon), 152/2017 Sb. (zákon o pohonných hmotách). |
| Ostatní novely | 10 | Čtyři novely předpisů mimo databázi (potraviny, zemědělský půdní fond), šest novel, u nichž měněný předpis z názvu určit nelze (mj. hromadné změnové zákony). |
| Úplná znění | 2 | Vyhlášená úplná znění zákonů č. 353/1999 Sb. a č. 76/2002 Sb. |
| Název ve věcném rozsahu | 28 | Například 108/2011 Sb. (měření plynu), 146/2024 Sb. (požadavky na výstavbu), 211/2018 Sb. (technické prohlídky vozidel), 488/2021 Sb. (připojení k plynárenské soustavě), 516/2020 Sb. (požadavky na pohonné hmoty), 328/2022 Sb. (záruky původu energie). |
| Název mimo rozsah, zmínka v textu nebo v přílohách | 41 | Převážně šum (mýtné, daně z příjmů, radiační ochrana), ale i předpisy patrně relevantní: 361/2007 Sb. (ochrana zdraví při práci), 226/2015 Sb. (zóny havarijního plánování), 293/2003 Sb. (výbušniny), 266/2025 Sb. (kritická infrastruktura). |
| Zjevně mimo rozsah | 30 | Programy statistických zjišťování, smlouvy o volném obchodu, klasifikace produkce, sazebníky, seznam zdravotních výkonů, potraviny, léčiva, kosmetika, hnojiva. |
| Předpisy z let 1925–1989 | 16 | Převážně přílohy Mezinárodní úmluvy o přepravě zboží po železnicích (předchůdce RID) a obchodní úmluvy; e-Sbírka u nich konec účinnosti neuvádí. |

Z rozboru plyne, že šum nelze omezit jediným pravidlem. Filtr podle roku by
vyřadil i předchůdce RID, filtr podle názvu by vyřadil nařízení vlády
o ochraně zdraví při práci a filtr podle příloh i vyhlášku o vykazování
energie. Navrhujeme proto pět kroků, z nichž žádný kandidáta beze stopy
nezahodí:

1. **Novely připojit k předpisu, jejž mění.** Novelu, jejíž všechny výskyty leží
   v novelizačních bodech (nebo jejíž název zní „…, kterým se mění …“
   a novelizační body obsahuje), nevkládat jako samostatného kandidáta.
   Měněný předpis určit z názvu (`citation_closure.own_keys()`). Je-li měněný
   předpis kandidátem, připsat novelu k jeho dokladům („zmínku o vodíku vložila
   novela X“); má-li jej databáze, zaznamenat ji jako změnu dokumentu
   v databázi (nový druh nálezu, jenž editorovi nabídne vazbu `AMENDS`
   a kontrolu, zda databáze nepotřebuje nové znění). Totéž platí pro vyhlášená
   úplná znění, jež patří k základnímu předpisu. Postup odpovídá uzávěru
   citací, jenž předpisy citované převážně jako novela rovněž nenavrhuje
   (`doc/CITATION_CLOSURE.md`). Dotkne se to 76 předpisů.
2. **Zjevně nesouvisející druhy vyřadit se záznamem.** Seznam vzorů názvů
   (statistická zjišťování, smlouvy o volném obchodu, klasifikace produkce,
   sazebníky, potraviny, léčiva, kosmetika, hnojiva a další), odvozený z této
   dávky stejně jako seznam vzorů u EUR-Lexu (`add_eurlex_hydrogen_acts.py`).
   Vyřazené předpisy zapsat do souboru `data/esbirka_not_imported.json`
   s uvedeným vzorem, nikoli zahodit; seznam vzorů revidovat při každé větší
   změně výsledků. Na této dávce vzory zachytily 30 předpisů a ruční kontrolou
   všech 30 názvů jsme mezi nimi relevantní předpis nenašli.
3. **Zbylé kandidáty rozdělit do dvou pásem.** Pásmo 1 tvoří předpisy, jejichž
   název obsahuje výraz věcných okruhů z `doc/DATABASE_SCOPE.md`, odstavec 3
   (energetika, plyn, paliva, emise, vozidla, doprava, nebezpečné věci, tlaková
   a plynová zařízení, požární ochrana, stavby, havárie, metrologie a další);
   pásmo 2 ostatní. Fronta kandidátů by pásmo 1 ukazovala ve výchozím zobrazení
   a pásmo 2 v samostatném filtru, k občasnému projití; z pásma 2 nic
   automaticky nevypadne.
4. **U historických předpisů ověřit platnost, nikoli rok.** Pro předpisy, u nichž
   e-Sbírka konec účinnosti neuvádí, zkusit zrušující předpis na zakonyprolidi.cz
   (`check_validity.repealing_act()`, jak to již dělá kontrola platnosti);
   předpis, jehož zrušení se potvrdí, do fronty nevložit, ostatní zařadit do
   pásma 2.
5. **Řadit podle pásma a počtu výskytů.** Ve frontě uvést nejprve pásmo 1,
   v něm předpisy s více výskyty v posledním znění.

Výsledek na dávce ze 4. 11. 2026 by byl tento: 28 kandidátů v pásmu 1,
51 v pásmu 2 (z toho 16 historických k ověření), 76 nálezů připojených
k jiným předpisům a 30 předpisů vyřazených se záznamem. Editor by tak místo
185 kandidátů nejprve posuzoval 28.

Návrh jsme provedli téhož dne; pravidla, jak jsou implementována, a jejich
výsledek popisuje odstavec 8.9. Slovník okruhů
pro pásmo 1 i seznam vzorů jsou heuristiky odvozené z jediné dávky; po prvních
týdnech provozu je bude třeba ověřit podle toho, jak editoři kandidáty
skutečně rozhodnou. Stejný postup se patrně uplatní i u kanálů RSS etapy E4,
jež nesou obecné zprávy úřadů.

### 8.9 Omezení šumu: provedení (4. 11. 2026)

Návrh z odstavce 8.8 je proveden v adaptéru `esbirka_new`
(`src/tools/harvest_adapters.py`, funkce `classify_act()`), v zápisu nálezů
(`src/tools/harvest.py`, `src/tools/candidates.py`) a ve frontě kandidátů
(`app/candidates_admin.py`). Na větvi `feature/esbirka-noise`.

**Pravidla.** Každý předpis, jejž adaptér nalezne (databáze jej nemá, jeho
poslední znění obsahuje slovo „vodík“ a je účinné), projde těmito pravidly
v uvedeném pořadí:

1. **Vyřazení podle vzoru názvu.** Název odpovídá některému ze vzorů
   `DENY_PATTERNS`: programy statistických zjišťování, smlouvy o volném obchodu,
   klasifikace produkce, seznam zboží, sazebníky, seznam zdravotních výkonů,
   potraviny, léčiva, kosmetika, hnojiva, agrochemické zkoušení, zemědělský
   půdní fond, oceňovací vyhláška, digitální technická mapa, obsahové náplně
   živností, původ zboží, dohody o přidružení k Evropským společenstvím, obchod
   s vojenským materiálem. Předpis se vyřadí a vzor se uvede jako důvod.
2. **Novela.** Předpis je novelou, leží-li všechny výskyty slova v jeho
   posledním znění v novelizačních bodech (`…/dokument/novela/…`), nebo zní-li
   jeho název „…, kterým (kterou) se mění …“ či „… o změně …“ a alespoň jeden
   výskyt v novelizačních bodech leží. Měněné předpisy se čtou z názvu
   (`citation_closure.own_keys()`). Pak:
   - Má-li měněný předpis databáze, vznikne nález druhu `amendment` („novela
     dokumentu v databázi“) s identifikátory měněných dokumentů; přijetí
     takového kandidáta založí dokument s vazbou `AMENDS` na každý z nich.
     Pásmo 1.
   - Je-li měněný předpis mezi nalezenými, novela samostatným kandidátem není;
     připojí se k nálezu měněného předpisu (pole `amended_by`, v detailu
     kandidáta „Zmínku vložily nebo mění novely“). Je-li měněný předpis vyřazen,
     vyřadí se s ním i novela.
   - Jinak zůstane novela kandidátem v pásmu 2 s poznámkou, který předpis
     mění, nebo že jej z názvu určit nelze.
3. **Úplné znění.** Název začíná „Úplné znění …“. Má-li databáze vyhlašovaný
   předpis, úplné znění se vyřadí s odkazem na něj; jinak se s ním naloží jako
   s novelou (připojí se k předpisu, je-li mezi nalezenými).
4. **Předpis z doby před rokem 1990.** Adaptér zkusí zrušující předpis na
   zakonyprolidi.cz (`check_validity.repealing_act()`); potvrdí-li se zrušení,
   předpis se vyřadí s datem a zrušujícím předpisem jako důvodem, jinak jde do
   pásma 2 s poznámkou.
5. **Pásmo.** Ostatní předpisy jsou v pásmu 1, obsahuje-li název výraz věcných
   okruhů z `doc/DATABASE_SCOPE.md`, odstavec 3 (vodík, elektrolýza, palivové
   články, plnicí a čerpací stanice, pohonné hmoty a paliva, energie, plyn,
   elektřina, teplárenství, emise, ovzduší, skleníkové plyny, obnovitelné zdroje,
   biopaliva, vozidla, pozemní komunikace, silniční a drážní doprava, železnice,
   přeprava, nebezpečné věci, látky a zboží, tlaková a plynová zařízení,
   vyhrazená technická zařízení, výbuch a výbušniny, požární ochrana,
   bezpečnost a ochrana zdraví při práci, stavby a výstavba, územní plánování,
   posuzování vlivů, integrovaná prevence, havárie a havarijní plánování,
   chemické látky, metrologie a měřidla, jakost, technické požadavky, kritická
   infrastruktura); ostatní v pásmu 2.

Vyřazené předpisy se zapisují do souboru `data/harvest_not_imported.json`
(po zdrojích: klíč, název, adresa, důvod, datum prvního a posledního zachycení),
takže zůstávají dohledatelné a vzory lze revidovat. Názvy předpisů adaptér bere
z fronty kandidátů, má-li je tam, jinak ze zakonyprolidi.cz.

**Fronta kandidátů.** Tabulka `DocumentCandidate` má sloupce `tier` (pásmo)
a `occurrences` (počet výskytů v posledním znění); doplní je migrace
v `candidates.ensure_schema()`. Seznam kandidátů ukazuje ve výchozím
zobrazení pásmo 1 (sem patří i kandidáti z kontrol, kteří pásmo nemají),
filtr „pásmo“ nabízí pásmo 2 a obě pásma i s počty. Řadí se nejprve návrhy
k přijetí, pak podle pásma, počtu citací a počtu výskytů. Kandidát pásma 2 nese
v seznamu označení „pásmo 2“; detail uvádí pásmo, počet výskytů, poznámku,
připojené novely a u novely dokumentu v databázi měněné dokumenty. Opakovaný
běh obnoví pásmo a počet výskytů a zástupný název („N/RRRR Sb.“) nahradí
skutečným; název, jejž upravil editor, ponechá.

**Výsledek (4. 11. 2026).** Suchý běh nad živou databází a ostrý běh nad
`h2regdocs_test` dávají shodný výsledek. Ze 185 předpisů:

| Výsledek | Počet |
|---|---|
| Pásmo 1 — nový dokument | 27 |
| Pásmo 1 — novela dokumentu v databázi | 11 |
| Pásmo 2 — nový dokument | 44 |
| Připojeno k nálezu měněného předpisu | 47 |
| Vyřazeno podle vzoru názvu | 38 |
| Vyřazeno jako novela vyřazeného předpisu | 8 |
| Vyřazeno jako zrušený historický předpis | 1 |
| Vyřazeno jako úplné znění předpisu v databázi | 1 |

Osm z nalezených předpisů již bylo kandidáty z uzávěru citací; nález se jim
připsal (šest v pásmu 1, dva v pásmu 2). Editor tedy ve výchozím zobrazení
posuzuje 38 kandidátů ze sledovaného zdroje, nikoli 185. Mezi novelami
dokumentů v databázi jsou například 87/2025 Sb. (67 výskytů; novela
energetického zákona č. 458/2000 Sb.), 382/2021 Sb. (podporované zdroje
energie) a 42/2025 Sb. a 172/2018 Sb. (ochrana ovzduší); v pásmu 1 například
přílohy RID (29/1998 Sb., 60/1999 Sb.), 146/2024 Sb. (požadavky na výstavbu),
328/2022 Sb. (záruky původu energie), 488/2021 Sb. (připojení k plynárenské
soustavě) a 361/2007 Sb. (ochrana zdraví při práci, s osmi připojenými
novelami). Z 16 historických předpisů se zrušení potvrdilo u jediného
(103/1949 Sb., zrušen 1. 9. 1953); ostatní jsou v pásmu 2.

**Omezení.** Vzory i slovník okruhů jsou odvozeny z jediné dávky a pásmo 1
zahrnuje i předpisy, jež název řadí do okruhů jen volně (například předpisy
o mírovém využívání jaderné energie podle výrazu „energ“). Po prvních týdnech
provozu je bude třeba porovnat s rozhodnutími editorů a upravit. Do živé
fronty dosud nic nevstoupilo (odstavec 8.7, otevřené body).

### 8.10 Etapa E2 (4. 11. 2026)

Etapa přinesla do fronty kandidátů **návrhy předpisů v legislativním procesu**
(signál `draft`), tedy včasný signál o tom, co se teprve připravuje. Adaptéry
jsou v modulu `src/tools/harvest_drafts.py`:

| Zdroj | Adaptér | Co čte |
|---|---|---|
| `veklep-odok` | `veklep_rss` | Kanál RSS novinek VeKLEPu: zhruba 17 posledních materiálů (asi dva týdny), u každého název, předkladatel, důvod předložení a identifikátor materiálu (PID). |
| `psp-snemovni-tisky` | `psp_bills` | Otevřená data Poslanecké sněmovny (`tisky.zip`, `sbirka.zip`, `poslanci.zip`): návrhy zákonů (vládní a ostatní) aktuálního volebního období, jež Sněmovna dosud neprojednala, se stavem projednávání a s předpisy, jež tisk mění nebo ruší (tabulka `sb_pre`). |
| `senat-tisky` | `senate_bills` | Senátní tisky z otevřených dat Sněmovny (`se_tisk.zip`, vazba `psp2senat`): návrhy zákonů aktuálního funkčního období Senátu. Web Senátu robotům přístup zapovídá. |
| `ep-oeil` | `oeil_procedures` | Export RSS Legislative Observatory pro „hydrogen“: legislativní postupy (COD, CNS, DEA), každý ověřený v otevřeném API Parlamentu. |

**Jeden návrh, jeden kandidát.** Český návrh dostane klíč
`DRAFT-CZ:eklep:<PID>`, má-li materiál v eKLEP (tabulka `tisk_eklep` připojuje
k materiálu sněmovní tisk, tabulka `psp2senat` senátní tisk ke sněmovnímu),
jinak `DRAFT-CZ:psp:<tisk>` nebo `DRAFT-CZ:senat:<tisk>`; postup EU klíč
`DRAFT-EU:<číslo postupu>`. Nálezy VeKLEPu, Sněmovny a Senátu o témže návrhu
se tak setkají u jednoho kandidáta.

**Pravidla výběru.** Do fronty vstupuje jen návrh, jenž se databáze týká:

1. **Pásmo 1** — Návrh mění nebo ruší dokument, jejž databáze má (u tisků podle
   tabulky `sb_pre`, u VeKLEPu podle předpisů uvedených v názvu), nebo jeho
   název obsahuje základní výraz k vodíku (odstavec 6).
2. **Pásmo 2** — Název obsahuje výraz věcných okruhů (týž slovník jako
   v odstavci 8.9, pravidlo 5).
3. **Ostatní návrhy** do fronty nevstupují a nezapisují se ani mezi vyřazené:
   jde o zbytek legislativy, nikoli o nález, jejž by vyřadil filtr.

Návrh, jenž mění dokumenty databáze, nese jejich identifikátory
(`amends_ids`); přijetím vznikne dokument ve stavu „připravovaný“ s vazbami
`AMENDS` na ně. U postupů EU je rozhodující, zda je postup uzavřen: uzavřen je,
nese-li v datech Parlamentu událost vyhlášení v Úředním věstníku. Akty
v přenesené pravomoci (DEA) Parlament jen přezkoumává a tuto událost nikdy
nemají; postup DEA proto považujeme za uzavřený, neproběhla-li v něm žádná
událost po dobu 180 dní (lhůta k námitce činí dva plus dva měsíce). Bez tohoto
pravidla se jako otevřené jevily i postupy z let 2017 až 2023, mezi nimi
metodiky RFNBO, z nichž vzešla nařízení (EU) 2023/1184 a 2023/1185, jež databáze
obsahuje. Postupy z vlastního podnětu Parlamentu (INI) a další nelegislativní
druhy adaptér vynechává.

**Výsledek (4. 11. 2026).** Suchý běh nad živou databází a ostrý běh nad
`h2regdocs_test`:

| Zdroj | Nálezy | Výsledek zápisu |
|---|---|---|
| VeKLEP | 1 | 1 nový kandidát (pásmo 2: novela vyhlášky o registraci vozidel) |
| Sněmovní tisky | 34 (ze 143 neprojednaných návrhů zákonů období) | 34 nových kandidátů |
| Senátní tisky | 4 | 4 nálezy připsané ke kandidátům ze Sněmovny |
| Legislative Observatory | 9 (z 59 legislativních postupů pro „hydrogen“) | 9 nových kandidátů |

Celkem 44 kandidátů: 28 českých a 9 evropských v pásmu 1, 7 českých v pásmu 2.
Všech 28 českých návrhů v pásmu 1 mění dokument databáze; jde mimo jiné
o novely energetického zákona, zákona o pozemních komunikacích, zákona
o provozu na pozemních komunikacích, zákona o podmínkách provozu vozidel,
zákona o technických požadavcích na výrobky, zákona o chemických látkách,
zákona o odpadech, ale také zákoníku práce či zákona o spotřebních daních.
Databáze tyto obecné předpisy obsahuje, protože se na vodíková zařízení
vztahují; jejich novely se však vodíku často netýkají, a pásmo 1 proto
zahrnuje i návrhy, jež editor patrně zamítne. Mezi návrhy EU jsou například
revize směrnic (EU) 2018/2001, (EU) 2019/944 a (EU) 2024/1788 (2025/0400(COD)),
hlavních směrů pro transevropské energetické sítě (2025/0399(COD)) a zahrnutí
vodíku mezi referenční paliva nesilničních mobilních strojů (2026/0294(COD)).

**Zjištění při provádění.**

1. **Rozhraní JSON VeKLEPu robota blokuje** stránkou „Požadavek byl
   zablokován“, a to s kódem HTTP 200. Kontrola dostupnosti z etapy E0 ji proto
   vyhodnotila jako funkční; nově takové stránky rozpoznává (`check_sources.py`,
   `BLOCK_PAGE_MARKERS`). Kanál RSS téhož webu robota pouští; zachycuje však jen
   zhruba dva týdny, týdenní běh je proto nutný.
2. **VeKLEP neuvádí kódování** odpovědi v hlavičce; kanál se čte jako bajty,
   aby rozhodla deklarace XML.
3. **Sněmovní data** nesou vše potřebné bez procházení webu: stav projednávání,
   vazbu na materiál VeKLEPu, předpisy, jež tisk mění, i předpis Sbírky, jenž
   z tisku vzešel. Volební období se určuje z tabulky orgánů
   (`PSP10` = 10. období).

**Otevřené body.**

1. **Převod připravovaného předpisu na vyhlášený.** Tabulka `sbirka` váže
   předpis Sbírky k tisku, z něhož vzešel; po vyhlášení by tedy šlo přijatý
   návrh (dokument ve stavu „připravovaný“) automaticky propojit s vyhlášeným
   předpisem. Zatím to provedeno není.
2. **Slov-Lex legislatívny proces** zůstává odložen (odstavec 8.5).
3. **Novely obecných předpisů** v pásmu 1 (výše): po prvních rozhodnutích
   editorů posoudit, zda je neodsunout do pásma 2, pokud jejich název ani text
   vodík nezmiňuje.

