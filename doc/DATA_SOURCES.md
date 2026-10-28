# Registr sledovaných zdrojů

> Historie dokumentu:  
> 2026-10-28 jprk Převzato z odstavce 11 dokumentu `doc/AUTOMATION.md` (větev `automation`, stav 2026-10-24)  
> 2026-10-28 jprk Doplněno z návrhu katalogu informačních zdrojů: role a priority zdrojů, 36 nových zdrojů ověřených živě, pořadí prací, zpracování nálezu, vyhledávací výrazy, výhled  
> 2026-10-28 jprk Plán vytěžování zdrojů (odstavec 4) a pole `signal` a `stage` v registru

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

**E2 — Včasný signál (5 zdrojů).** `veklep-odok` (A), `slovlex-legislativny-proces`
(A), `psp-snemovni-tisky`, `senat-tisky`, `ep-oeil`. Všechny mají ověřenou
strojově čitelnou cestu (JSON, RSS, hromadná otevřená data). Zavádí do
databáze připravované předpisy a jejich převod na vyhlášené.

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
