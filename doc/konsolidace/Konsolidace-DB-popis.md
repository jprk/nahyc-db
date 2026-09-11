# Konsolidované schéma databáze — regulační předpisy + předrealizační procesy

**Projekt:** NAHYC DP004 — Vodíkový technologický inkubátor
**Účel:** Konsolidace implementované databáze V01 (regulační dokumenty) s procesní
vrstvou navrženou v rámci V02 (uzly U1–U7) do jednoho schématu naplňujícího
požadavky metodického dokumentu V03 (compliance pathway, obousměrné vazby).
**Cílová platforma:** MariaDB 11.8 (produkční infrastruktura RICE FEL ZČU)
**Datum:** červenec 2026

---

## 1. Východiska a cíle konsolidace

Databáze V01 nese oficiální název *„Databáze regulačních předpisů
a předrealizačních procesů"*, její implementované schéma však pokrývá pouze
dokumentovou část (entity `Document`, `DocumentType`, `DocumentSource`,
`Keyword`, `DocumentKeyword`, `DocumentVersion`). Procesní vrstva existuje
zatím jen jako návrh (`Databáze.V02/V02-DB-schema.puml`) a propojení procesů
na předpisy je realizováno pouze měkce — přes klíčová slova.

Konsolidované schéma řeší tři úlohy:

1. **Doplnění procesní vrstvy** — procesní uzly U1–U7 a jejich satelitní
   entity podle návrhu V02 se stávají plnohodnotnou součástí schématu.
2. **Tvrdé propojení obou vrstev** — vazby uzel ↔ dokument jsou realizovány
   cizími klíči, nikoli klíčovými slovy; „stínové" tabulky `legal_document`
   a `source_reference` z návrhu V02 jsou zrušeny ve prospěch přímých vazeb
   na `Document`.
3. **Podpora compliance pathway (V03)** — nové entity pro podmínky aktivace
   procesů, typové scénáře a čtyři klasifikační hlediska umožňují strojově
   generovat sadu relevantních uzlů a předpisů pro zadaný projektový záměr.

### 1.1 Klíčová návrhová rozhodnutí

| # | Rozhodnutí | Zdůvodnění |
|---|-----------|------------|
| R1 | **Jedno schéma, aditivní rozšíření V01.** Stávající tabulky V01 se nemění destruktivně (pouze nové sloupce s `NULL`/výchozí hodnotou), nové tabulky se přidávají. | Nad V01 běží produkční Flask aplikace (https://nahyc.fel.zcu.cz/h2db/) — konsolidace ji nesmí rozbít. |
| R2 | **Zrušení stínových tabulek.** `legal_document` a `source_reference` z návrhu V02 se do schématu nepřebírají; právní předpisy i bibliografické prameny jsou řádky `Document` a uzly na ně odkazují přímo. | V jednom schématu ztrácí „shadow records" smysl; duplicitní evidence by porušila zásadu jediného zdroje pravdy a V03 požaduje strojově dotazovatelné vazby. |
| R3 | **Sjednocená vazební tabulka `node_document`.** Nahrazuje `node_legal_document` i `node_source`; typ vazby rozlišuje sloupec `link_type` (`LEGAL_BASIS` / `SOURCE`). | Obě vazby mají po R2 stejný cíl (`Document`) a téměř stejné atributy; jedna tabulka zjednodušuje dotazy „všechny dokumenty k uzlu". |
| R4 | **Podmínky aktivace jako strukturovaná pravidla** (`node_activation_rule` + číselník `project_criterion`). | V03 označuje podmínky aktivace za metodicky zásadní atribut a základ prvního mechanismu compliance pathway; volný text v `trigger_condition` je pro strojové filtrování nedostatečný. |
| R5 | **Typový scénář jako nosič klasifikace** (`use_case_scenario` + číselníky čtyř hledisek). | V03: „typové scénáře tvoří organizační jádro celého systému"; scénář je přirozený vstupní bod uživatele (investora) a nese hodnoty čtyř klasifikačních hledisek. |
| R6 | **Klíčová slova zůstávají** primárním tematickým indexem dokumentů. | Řízený slovník je zaveden v produkci a ve správních procesech; strukturované vazby jej doplňují, nenahrazují. |
| R7 | **Verzování procesní vrstvy** sloupci `valid_from` / `valid_to` na `process_node`. | Implementační poznámka V02-DB-popis §8; analogicky k `DocumentVersion` umožňuje zachytit reformu procesní struktury (např. nový stavební zákon). |
| R8 | **Konvence pojmenování:** tabulky V01 ponechávají PascalCase (`Document`), nové tabulky používají snake_case (`process_node`). | Zpětná kompatibilita s produkční aplikací má přednost před kosmetickou jednotností; přejmenování V01 tabulek by vyžadovalo zásah do aplikace bez funkčního přínosu. |

---

## 2. Architektura schématu — čtyři vrstvy

```
┌─────────────────────────┐      ┌──────────────────────────┐
│  A. REGULATORNÍ VRSTVA  │      │  B. PROCESNÍ VRSTVA      │
│  (V01, rozšířeno)       │      │  (dle návrhu V02)        │
│  Document, DocumentType,│◄────►│  process_node U1–U7,     │
│  DocumentSource, Keyword│  C   │  větve, kroky, vstupy,   │
│  DocumentVersion        │      │  výstupy, subjekty, …    │
└─────────────────────────┘      └──────────────────────────┘
             ▲                                ▲
             │        C. INTEGRAČNÍ VRSTVA    │
             └────────  node_document  ───────┘
             ▲                                ▲
┌────────────┴────────────────────────────────┴─────────────┐
│  D. KLASIFIKACE A COMPLIANCE (dle V03)                     │
│  use_case_scenario, node_activation_rule,                  │
│  project_criterion, application_area, technology_type,     │
│  integration_level, value_chain_stage                      │
└────────────────────────────────────────────────────────────┘
```

- **Vrstva A** je dynamická (předpisy se mění průběžně, spravuje ji verzovací
  mechanismus a týdenní automatizovaná verifikace vůči EUR-Lex / eSbírka / ČAS).
- **Vrstva B** je stabilní (struktura uzlů se mění jen při zásadní legislativní
  reformě) — oddělení obou vrstev odpovídá metodickému požadavku V03 §7.5.
- **Vrstva C** zajišťuje obousměrnost: od procesu k předpisům i od předpisu
  k procesům (V03 §7.1).
- **Vrstva D** realizuje generování compliance pathway (V03 §7.3): parametry
  záměru → aktivované uzly → relevantní dokumenty.

Grafická podoba: UML schéma `Konsolidace-DB-schema.puml` (render na
https://www.plantuml.com/plantuml), konceptuální přehled
`Konsolidace-DB-koncept.dot` (Graphviz; PNG/SVG přiloženy).

---

## 3. Přehled tabulek

| Vrstva | Tabulka | Obsah | Původ |
|--------|---------|-------|-------|
| A | `Document` | Regulatorní/metodický dokument (metadata) | V01 + sloupce `identifier`, `jurisdikce` |
| A | `DocumentType` | Číselník typů dokumentů | V01 beze změny |
| A | `DocumentSource` | Číselník zdrojů/institucí | V01 + `institution_type`, `jurisdiction` |
| A | `Keyword`, `DocumentKeyword` | Řízený slovník + M:N vazba | V01 beze změny |
| A | `DocumentVersion` | Verze dokumentů | V01 + `is_current`, `edition_label`, `effective_date`, `lifecycle_state` |
| A | `document_relation` | Vztah mezi dvěma samostatně číslovanými dokumenty (novela zákona jiným zákonem) | nová (Krok 1 follow-up #16) |
| B | `process_class` | Číselník tříd procesů (7) | V02 |
| B | `process_node` | Uzly U1–U7 | V02 + `valid_from`/`valid_to` |
| B | `node_description` | 1:1 narativní texty šablony P6 | V02 |
| B | `node_branch`, `branch_step` | Větve průběhu a jejich kroky | V02 |
| B | `node_input`, `node_output` | Vstupy a výstupy uzlu | V02 |
| B | `subject`, `node_subject` | Aktéři a jejich role v uzlech | V02 |
| B | `node_edge` | Hrany procesní sítě | V02 |
| B | `installation_type` | Číselník 4 oblastí instalací | V02 + FK na `value_chain_stage` |
| B | `intensity_level` | Číselník intenzit (●●●/●●○/●○○) | V02 |
| B | `node_variability` | Matice 4×7 | V02 |
| B | `node_problem`, `node_problem_installation` | Typické problémy | V02 |
| C | `node_document` | Uzel ↔ Dokument (`LEGAL_BASIS`/`SOURCE`) | nová; nahrazuje `node_legal_document`, `node_source`, `legal_document`, `source_reference` |
| D | `value_chain_stage` | Číselník: výroba/distribuce/skladování/využití | nová (V03 hledisko 1) |
| D | `technology_type` | Číselník technologických řešení | nová (V03 hledisko 2) |
| D | `integration_level` | Číselník míry integrace | nová (V03 hledisko 3) |
| D | `application_area` | Číselník aplikačních oblastí | nová (V03 hledisko 4) |
| D | `project_criterion` | Číselník parametrů záměru | nová |
| D | `node_activation_rule` | Strukturované podmínky aktivace uzlů | nová |
| D | `use_case_scenario` | Typové scénáře (use-cases) | nová |
| D | `scenario_value_chain`, `scenario_technology` | M:N klasifikace scénáře | nové |
| D | `scenario_node` | Scénář ↔ uzel (s intenzitou) | nová |
| D | `scenario_document` | Scénář ↔ dokument (přímé vazby) | nová |

DDL skript pro MariaDB: `Konsolidace-DB-schema.sql`.

---

## 4. Vrstva A — regulatorní (změny oproti V01)

Tabulky `DocumentType`, `Keyword`, `DocumentKeyword` zůstávají beze změny.

### 4.1 `Document` — rozšíření

| Nový sloupec | Typ | Popis |
|---|---|---|
| `identifier` | `VARCHAR(100)` NULL UNIQUE | Oficiální identifikátor předpisu (`č. 283/2021 Sb.`, `EU 2023/1184`, `EN 17124:2022`). Přebírá roli `legal_document.identifier` z návrhu V02. U dokumentů bez oficiálního čísla (studie, metodiky) zůstává NULL. Reálná data (Krok 2, 2026-09-09) navíc obsahují ojedinělé kolize téhož čísla mezi jurisdikcemi (např. `ASTM F1624-12` existuje jako CZ i US adopce) — v takovém případě zůstává `identifier` u druhého záznamu NULL, nikdy se nevynucuje umělá jedinečnost. |
| `jurisdikce` | `VARCHAR(20)` NULL | **Doplněno Krokem 2 (2026-09-09).** `CZ` / `SK` / `DE` / `EU` / `mezinárodní` / `neurčeno` / … — viz oprava u `DocumentSource.jurisdiction` níže: toto pole, ne to na zdroji, je autoritativní pro jurisdikci konkrétního dokumentu. |
| `jurisdikce_uroven` | `ENUM('mezinárodní','EU','národní')` NULL, **GENERATED** (virtuální, z `jurisdikce`) | **Doplněno per `doc/REQUIREMENTS.md` R1.2 (2026-09-11, viz doc/PLAN.md §6).** Explicitní zařazení do jedné ze tří jurisdikčních úrovní požadovaných R1.2 — `jurisdikce` samo zůstává konkrétní hodnotou (kód konkrétního státu, `EU`, `mezinárodní`, `neurčeno`) a nadále slouží jako veto proti slučování cizích národních adopcí téže normy; `jurisdikce_uroven` je z něj automaticky odvozeno (`CASE`): `jurisdikce = 'mezinárodní'` → `'mezinárodní'`, `jurisdikce = 'EU'` → `'EU'`, jakýkoli jiný nevyprázdněný/ne-"neurčeno" kód (`CZ`, `SK`, `DE`, `US`, `CA`, `FR`, `UK`, budoucí `PL`, …) → `'národní'` — "národní" zde znamená SKUTEČNÝ konkrétní stát, ne vymyšlenou zástupnou hodnotu. `NULL`/`"neurčeno"` (184 dokumentů, 2026-09-11) zůstává čestně `NULL`, ne odhadnuto na některou ze tří úrovní. Jako `GENERATED`/`VIRTUAL` sloupec nepotřebuje žádnou udržovací logiku v `init_db.py` a libovolný budoucí konkrétní stát spadne do `'národní'` bez zásahu do kódu. |

Ostatní pole (`title`, `description`, `type_id`, `source_id`, `language`,
`url`, `file_path`, `effective_date`, `version`, `created_at`, `updated_at`)
beze změny. Pole `short_title` z návrhu V02 se nepřebírá — pracovní název
pokrývá `title` + `description`.

### 4.2 `DocumentSource` — rozšíření

| Nový sloupec | Typ | Popis |
|---|---|---|
| `institution_type` | `VARCHAR(50)` NULL | Typ instituce (ministerstvo, EU orgán, normalizační organizace, profesní sdružení, …). Krokem 2 (2026-09-09) zatím nikdy nevyplněno — ve zdrojových datech pro to není spolehlivý signál a raději se nehádá. |
| `jurisdiction` | `VARCHAR(20)` NULL | `CZ` / `EU` / `mezinárodní` / … — přebírá roli `legal_document.jurisdiction` z návrhu V02. **Oprava (Krok 2, 2026-09-09): tvrzení, že „jurisdikce je vlastností zdroje, ne dokumentu" (V03 §6.4), je pro tento projekt prokazatelně chybné.** 95 % záznamů (téměř všechny normy) sdílí prázdného/nevyplněného `gestor`, takže by spadly do jediného společného `DocumentSource` řádku napříč 11 různými jurisdikcemi — na této úrovni tedy jurisdikci držet nelze. Autoritativním zdrojem jurisdikce je nově `Document.jurisdikce` (viz §4.1). Tento sloupec zůstává jako doplňkový, best-effort údaj jen pro těch ~68 záznamů se skutečným (neprázdným) `gestor`, kde bylo empiricky ověřeno, že nedochází ke kolizi (žádný `gestor` nemá dvě různé neprázdné jurisdikce) — `src/tools/init_db.py`'s `build_gestor_jurisdiction_map`/`resolve_source_jurisdiction`. |

### 4.3 `DocumentVersion` — rozšíření

| Nový sloupec | Typ | Popis |
|---|---|---|
| `is_current` | `BOOLEAN` DEFAULT FALSE | Příznak aktuální platné verze (V03 §6.3: „aktuální platná verze je označena příznakem"). Nejvýše jedna verze dokumentu smí mít TRUE (vynuceno aplikačně, případně triggerem). |
| `edition_label` | `VARCHAR(200)` NULL | **Doplněno Krokem 1 follow-up #16 (2026-09-11).** Lidsky čitelné, skutečně citovatelné označení TÉTO konkrétní verze/vydání (např. `"STN EN 13445-2+A1/ - 2024.02"`) — na rozdíl od `version` (jen neprůhledné pořadové číslo 1, 2, …). Vždy verbatim převzato ze zdrojové značky té edice, nikdy nevymýšleno. |
| `effective_date` | `VARCHAR(200)` NULL | Vlastní datum platnosti TÉTO verze (na rozdíl od `Document.effective_date`, které po naplnění verzí odráží nejnovější/aktuální edici). Stejná „volný text" filozofie jako `Document.effective_date`. |
| `lifecycle_state` | `ENUM('active','superseded','draft')` NOT NULL DEFAULT `'active'` | **Doplněno per `doc/REQUIREMENTS.md` R1.5 (2026-09-11).** Explicitní životní stav TÉTO verze — `is_current` výše je jen binární „je toto nejnovější verze", ne stav, jak R1.5 žádá. NENÍ `GENERATED` (na rozdíl od `Document.jurisdikce_uroven`, R1.2): zdrojový text (volné pole `platnost`, u verzovaných záznamů promítnuté do `effective_date` výše) je nestrukturovaný vícejazyčný text, ne pár řízených hodnot — klasifikace (`classify_lifecycle_state()` v `src/tools/init_db.py`, pokryto testy) proto běží v Pythonu při importu, stejně jako `resolve_document_type()`. Pravidlo: `is_current = FALSE` → vždy `'superseded'` (nahrazená verze, bez ohledu na svůj vlastní tehdejší `platnost` text); `is_current = TRUE` a text obsahuje skutečný draft/work-item marker (`"Entwurf"`/`"Návrh"`, `"Arbeitsdokument"`/`"pracovný dokument"`, `"PWI"` — reálné, ověřené řetězce z korpusu) → `'draft'`; jinak → `'active'`. Ověřeno na reálném korpusu (2026-09-11): `active` 1035, `draft` 153, `superseded` 20 (z 1208 řádků `DocumentVersion`). |

Naplňuje `src/tools/link_document_versions.py`: detekuje skupiny záznamů
sdílející jádro značky (bez novelizační přípony `+A1`/`/A1`/`/AC` a bez
datové přípony edice) i jurisdikci, a alespoň jeden člen skupiny musí
nést skutečnou novelizační příponu (jinak jde jen o shodu titulků, ne o
verzní pár — to je práce `deduplicate_db.py`, ne tohoto skriptu). Řadí
podle novelizační úrovně (`+A1` < `+A2`, `/AC` počítáno jako úroveň 1) —
záměrně NE podle volně-textového `platnost`/edice-data, které v tomto
korpusu není spolehlivě autoritativním datem konkrétní edice (nalezeno:
jeden základní záznam má v `platnost` cizí datum interního sledování
pracovní položky, ne datum vlastního vydání). `src/tools/init_db.py`
načte jeden `DocumentVersion` řádek na položku seznamu `versions`
(chybí-li seznam — běžný, neverzovaný případ — zachovává historické
chování: jeden řádek, `version=1`, `is_current=TRUE`, bez
`edition_label`/`effective_date`).

### 4.4 `document_relation` — nová tabulka

**Doplněno Krokem 1 follow-up #16 (2026-09-11).** Zákon novelizovaný
JINÝM, samostatně číslovaným zákonem (na rozdíl od normy výše, kde
novelizační přípona sdílí číslo se základní normou a je tedy jen další
`DocumentVersion` téhož `Document`) zůstává navždy samostatný, citovatelný
`Document` řádek — vlastní `identifier`, vlastní název. Vztah mezi
novelizujícím a novelizovaným zákonem (reálný příklad z korpusu:
`426/2021 Sb.` AMENDS `266/1994 Sb.` — zákon o dráhách) se eviduje zde,
NE jako verze. Pokud korpus někdy získá „úplné znění" (konsolidovaný
přetisk téhož čísla zákona po zapracování novel), TO by naopak patřilo
do `DocumentVersion` (stejný `identifier`, nové vydání) — ne sem.

| Sloupec | Typ | Popis |
|---|---|---|
| `from_document_id` | `INT` NOT NULL, FK → `Document.id` | Novelizující/vztahující se dokument. |
| `to_document_id` | `INT` NOT NULL, FK → `Document.id` | Dokument, ke kterému se vztahuje. |
| `relation_type` | `ENUM('AMENDS','REPEALS','IMPLEMENTS','CONSOLIDATES','ADOPTS')` NOT NULL | Typ vztahu. `ADOPTS` doplněno per R1.3/R1.4 (2026-09-11, viz níže). |
| `note` | `VARCHAR(500)` NULL | Volný text (odůvodnění/kontext vztahu). |

Naplňuje `src/tools/load_document_relations.py` ze dvou zdrojů: ručně
kurátorovaný `data/document_relations.json` (zákon novelizovaný jiným
zákonem — detekce napříč celým korpusem vyžaduje lidský úsudek,
novelizující zákon obvykle ve svém vlastním názvu cituje novelizovaný
zákon jménem/předmětem, ne číslem — např. "426/2021 Sb. - novela Zákona
o drahách" — proto se zde záměrně nezkouší automatické dolování, stejný
princip jako `data/v03_layer_d_draft.json`) a automaticky vygenerovaný
`data/document_relations_auto.json` (viz `src/tools/
link_document_relations_auto.py` níže). Nenapárované položky (neznámý
`identifier` nebo `relation_type`) jdou do
`data/document_relations_review_queue.json`, nikdy se nehádají.

**Doplněno per `doc/REQUIREMENTS.md` R1.3/R1.4 (2026-09-11, viz
doc/PLAN.md §6): `src/tools/link_document_relations_auto.py`** mechanicky
generuje `data/document_relations_auto.json` nad
`data/database_merged_deduplicated.json`, ve dvou nezávislých krocích:

- **R1.4 (lokalizace normy — `ADOPTS`)**: seskupí záznamy podle
  "mezinárodního jádra" značky (`international_core()` — odstraní
  národní prefix STN/ČSN/DIN/… i případný mezivrstvý prefix "EN " před
  ISO/IEC, takže "STN EN ISO 11114-4", "EN ISO 11114-4" i "ISO 11114-4"
  padnou na stejné jádro `iso 11114-4`) a podle jurisdikční ÚROVNĚ
  (mezinárodní/EU vs. národní — nikoli konkrétní `jurisdikce_uroven`
  sloupec z DB, ale ekvivalentní logika počítaná přímo nad JSON polem
  `jurisdikce`, protože tento skript běží PŘED `init_db.py`). Skupina se
  propojí, jen když obsahuje aspoň jeden mezinárodní/EU člen (rodič) A
  aspoň jeden národní člen (dítě) — každé dítě dostane `ADOPTS` hranu ke
  KAŽDÉMU rodiči ve skupině (víc mezinárodních vydání ve skupině = víc
  hran, záměrně žádné hádání, které konkrétní vydání dítě adoptovalo).
  Ověřeno na reálném korpusu: 13 skupin, 17 hran (2026-09-11) — mnohem
  méně, než kolik STN/ČSN/DIN adopcí v korpusu skutečně existuje, protože
  drtivá většina nemá svůj mezinárodní protějšek vůbec sebraný jako
  vlastní záznam (to je mezera v ÚPLNOSTI dat, ne v mechanismu propojení).
- **R1.3 (transpozice směrnice EU — `IMPLEMENTS`)**: pro každý záznam,
  jehož VLASTNÍ značka NENÍ ve tvaru EU aktu (`is_eu_act_znacka()` —
  "(EU) NNNN/RRRR", "RRRR/NNNN/EU" apod.), vytáhne z jeho
  `nazev_eu`/`odkaz_eu` KAŽDOU citovanou značku EU aktu (regulérní výraz
  na `(EU/ES/EC/EÚ/EEC/EHS) č./No NNNN/RRRR` / `RRRR/NNNN/(ES|EC|EU|…)`
  tvary — `finditer`, ne jen první shodu, protože jeden text běžně cituje
  víc aktů najednou), vyloučí sebe-citace (vlastní `znacka` záznamu) a
  záznamy bez použitelné vlastní značky (prázdná/víceřádková — nemohly by
  se stejně nikdy stát `from_document_id`). Zde je klíčové, že vylučovací
  podmínka pro "kdo smí citovat" NENÍ založená na `jurisdikce`/
  `jurisdikce_uroven`: v tomto korpusu má `jurisdikce` prázdnou hodnotu
  jak u národních zákonů, tak u samotných aktů EU (zdroje
  `Sinay_Zakony`/`Haltuf_Dokumenty` ji nikdy nevyplňují u žádného z nich)
  — jediný spolehlivý signál je TVAR VLASTNÍ ZNAČKY citujícího záznamu.
  Bez tohoto rozlišení by např. prováděcí nařízení Komise "(EU) 2023/1184"
  citující svou "rodičovskou" směrnici "(EU) 2018/2001" vytvořilo falešnou
  `IMPLEMENTS` hranu — reálný vztah, ale ve tvaru EU-akt→EU-akt, ne
  R1.3's národní-zákon→EU-akt. Pokud takto nalezená EU norma už v korpusu
  existuje jako vlastní záznam, vytvoří se `IMPLEMENTS` hrana; pokud ne,
  zapíše se kandidát (národní zákon + citovaná, ale chybějící EU norma)
  do `data/eu_transposition_missing_targets.json` k lidskému rozhodnutí,
  zda tu chybějící EU normu přidat (stejný princip jako Krok 1 follow-up
  #17's `data/v03_layer_d_draft.json`-style doplnění chybějících
  dokumentů) — ověřeno na reálném korpusu (2026-09-11): 6 takových
  kandidátů (`201/2012 Sb.`, `56/2001 Sb.`, `458/2000 Sb.`, každý cituje
  po dvě chybějící EU normy), 0 hotových `IMPLEMENTS` hran (cílové EU akty
  zatím nejsou v korpusu vlastními záznamy).

---

## 5. Vrstva B — procesní (dle návrhu V02)

Tabulky jsou převzaty z `Databáze.V02/V02-DB-popis.md` §4.1–4.15 beze změn
struktury, s těmito výjimkami:

### 5.1 `process_node` — doplněné verzování

| Sloupec | Typ | Popis |
|---|---|---|
| `id` | `VARCHAR(3)` PK | `U1` … `U7` |
| `name` | `VARCHAR(200)` | Název uzlu |
| `chapter_ref` | `VARCHAR(10)` | Odkaz na kapitolu dokumentu V02 |
| `process_class_id` | FK → `process_class` | Třída procesu |
| `has_branches` | `BOOLEAN` | Příznak větvení |
| `valid_from` | `DATE` NULL | **nové** — začátek platnosti procesní definice |
| `valid_to` | `DATE` NULL | **nové** — konec platnosti (NULL = platný) |

Poznámka k U7: dle V03 se uzel nazývá *„Příprava certifikační schopnosti dle
RFNBO"* (v V02 *„Certifikace produktu"*) — v referenčních datech použít znění V03.

### 5.2 `installation_type` — napojení na hodnotový řetězec

Textový sloupec `value_chain_position VARCHAR(50)` je nahrazen cizím klíčem
`value_chain_stage_id` → `value_chain_stage` (viz §7.1). Tím se hodnotový
řetězec stává sdíleným číselníkem pro matici variability i pro klasifikaci
scénářů.

### 5.3 Ostatní tabulky vrstvy B

`process_class`, `node_description`, `node_branch`, `branch_step`,
`node_input`, `node_output`, `subject`, `node_subject`, `node_edge`,
`intensity_level`, `node_variability`, `node_problem`,
`node_problem_installation` — beze změny oproti návrhu V02
(detailní popis viz `Databáze.V02/V02-DB-popis.md`).

Sloupec `node_branch.activation_condition` (volný text) zůstává jako lidsky
čitelný popis; strojově vyhodnotitelná pravidla jsou v `node_activation_rule`
(§7.3), která mohou na konkrétní větev odkazovat.

---

## 6. Vrstva C — integrační

### 6.1 `node_document` — vazba uzel ↔ dokument

Nahrazuje čtyři tabulky návrhu V02 (`legal_document`, `node_legal_document`,
`source_reference`, `node_source`). Právní předpisy, normy i bibliografické
prameny jsou evidovány jako řádky `Document` (rozlišené přes `DocumentType`)
a uzly na ně odkazují přímo:

| Sloupec | Typ | Popis |
|---|---|---|
| `id` | `INT AUTO_INCREMENT` PK | Technický identifikátor |
| `node_id` | `VARCHAR(3)` FK → `process_node` | Procesní uzel |
| `document_id` | `INT` FK → `Document` | Dokument |
| `link_type` | `ENUM('LEGAL_BASIS','SOURCE')` | `LEGAL_BASIS` = právní/normativní opora uzlu (sekce U.x.2), `SOURCE` = bibliografický pramen citovaný pro uzel (U.x.2, U.x.11) |
| `is_primary_basis` | `BOOLEAN` DEFAULT FALSE | Primární právní opora (jen u `LEGAL_BASIS`) |
| `relevance_note` | `TEXT` | Proč je dokument pro uzel relevantní / kontext citace |

**Omezení:** `UNIQUE(node_id, document_id, link_type)`

Obousměrnost (V03 §7.1): dotaz *od procesu k předpisům* filtruje podle
`node_id`, dotaz *od předpisu k procesům* podle `document_id` — obojí přes
indexované FK, bez prostředníka klíčových slov.

---

## 7. Vrstva D — klasifikace a compliance pathway

### 7.1 Číselníky čtyř klasifikačních hledisek (V03 §5.5)

**`value_chain_stage`** — funkce v hodnotovém řetězci:

| id | code | name |
|----|------|------|
| 1 | `VYROBA` | výroba vodíku |
| 2 | `DISTRIBUCE` | distribuce a přeprava |
| 3 | `SKLADOVANI` | skladování |
| 4 | `VYUZITI` | využití |

**`technology_type`** — typ technologického řešení (`code`, `name`,
`description`; např. `ELEKTROLYZER_PEM`, `ELEKTROLYZER_ALK`,
`TLAKOVY_ZASOBNIK`, `PLNICI_TECHNOLOGIE`, `FCEV_VOZIDLO`, `KVET_JEDNOTKA`).
Číselník je otevřený — doplňuje se podle technologických profilů projektů.

**`integration_level`** — míra integrace a provozního uspořádání:

| id | code | name |
|----|------|------|
| 1 | `SAMOSTATNA` | samostatná instalace |
| 2 | `INTEGROVANA` | integrovaný systém |
| 3 | `KOMPLEXNI` | komplexní řešení (vodíkové údolí, areál) |
| 4 | `OSTROVNI` | ostrovní řešení |

**`application_area`** — aplikační oblast:

| id | code | name |
|----|------|------|
| 1 | `MOBILITA` | vodíková mobilita |
| 2 | `ENERGETIKA` | energetika |
| 3 | `PRUMYSL` | průmyslové využití |
| 4 | `PILOTNI` | výzkumné, pilotní a demonstrační projekty |

### 7.2 `project_criterion` — číselník parametrů záměru

Parametry projektu, podle nichž se vyhodnocuje aktivace procesních uzlů
(V03 §5.7: kapacita, typ technologie, umístění, aplikační oblast, …).

| Sloupec | Typ | Popis |
|---|---|---|
| `id` | `INT AUTO_INCREMENT` PK | |
| `code` | `VARCHAR(40)` UNIQUE | např. `KAPACITA_ELEKTROLYZERU`, `OBJEM_SKLADOVANI`, `TYP_TECHNOLOGIE`, `UMISTENI`, `APLIKACNI_OBLAST`, `PRODEJ_TRETIM_STRANAM`, `PRIPOJENI_K_SOUSTAVE`, `PRITOMNOST_NEBEZPECNYCH_LATEK` |
| `name` | `VARCHAR(150)` | Název parametru |
| `data_type` | `ENUM('NUMERIC','BOOLEAN','ENUM','TEXT')` | Datový typ hodnoty |
| `unit` | `VARCHAR(20)` NULL | Jednotka (MW, kg, m³, …) |
| `description` | `TEXT` | Vysvětlení parametru |

### 7.3 `node_activation_rule` — strukturované podmínky aktivace

Formalizuje podmínky, při jejichž splnění se uzel (případně konkrétní větev)
stává pro záměr relevantním. Doplňuje narativní `node_description.trigger_condition`
a `node_branch.activation_condition` o strojově vyhodnotitelnou podobu.

| Sloupec | Typ | Popis |
|---|---|---|
| `id` | `INT AUTO_INCREMENT` PK | |
| `node_id` | `VARCHAR(3)` FK → `process_node` | Uzel, který pravidlo aktivuje |
| `branch_id` | `INT` FK → `node_branch` NULL | Konkrétní větev; NULL = pravidlo aktivuje uzel jako celek |
| `criterion_id` | `INT` FK → `project_criterion` | Vyhodnocovaný parametr |
| `comparator` | `ENUM('EQ','NE','GT','GTE','LT','LTE','IN','IS_TRUE','IS_FALSE')` | Operátor porovnání |
| `value` | `VARCHAR(200)` NULL | Porovnávaná hodnota (u `IN` seznam oddělený `;`) |
| `rule_group` | `INT` DEFAULT 1 | Skupina pravidel: pravidla ve stejné skupině se skládají AND, skupiny mezi sebou OR |
| `description` | `TEXT` | Lidsky čitelné znění podmínky |
| `basis_document_id` | `INT` FK → `Document` NULL | Předpis, který práh/podmínku stanovuje (např. příloha zákona o EIA) |

**Poznámka k neurčitosti:** V03 upozorňuje, že podmínky aktivace často
nevyplývají jednoznačně z předpisu, ale z kombinace zákonných parametrů
a výkladové praxe. Pravidla proto nejsou závazným právním výrokem, ale
analytickou formalizací; sloupec `description` uchovává výhrady a kontext.

### 7.4 `use_case_scenario` — typové scénáře

Typové scénáře identifikované v metodice V01/V03 (výstavba malého/velkého
elektrolyzéru, provoz vodíkové autobusové dopravy, plnicí stanice včetně
mobilních, logistická centra, skladování a přeprava ADR/RID, KVET, …).

| Sloupec | Typ | Popis |
|---|---|---|
| `id` | `INT AUTO_INCREMENT` PK | |
| `code` | `VARCHAR(40)` UNIQUE | Strojový kód (`MALY_ELEKTROLYZER`, `HRS_VEREJNA`, …) |
| `name` | `VARCHAR(200)` | Název scénáře |
| `description` | `TEXT` | Popis aplikační situace |
| `application_area_id` | FK → `application_area` | Aplikační oblast (hledisko 4) |
| `integration_level_id` | FK → `integration_level` | Míra integrace (hledisko 3) |

Hlediska 1 a 2 jsou M:N (scénář typicky pokrývá více fází řetězce a více
technologií):

- **`scenario_value_chain`** (`scenario_id`, `stage_id`; kompozitní PK)
- **`scenario_technology`** (`scenario_id`, `technology_type_id`; kompozitní PK)

### 7.5 `scenario_node` — procesní profil scénáře

Který uzel se ve scénáři uplatňuje a s jakou intenzitou. Zobecňuje matici
variability (ta zůstává v `node_variability` pro 4 kanonické oblasti
instalací; `scenario_node` ji rozšiřuje na libovolné scénáře).

| Sloupec | Typ | Popis |
|---|---|---|
| `scenario_id` | FK → `use_case_scenario` | |
| `node_id` | FK → `process_node` | |
| `intensity_code` | FK → `intensity_level` | ●●● / ●●○ / ●○○ |
| `note` | `TEXT` | Specifika uplatnění uzlu ve scénáři |

**PK:** `(scenario_id, node_id)`

### 7.6 `scenario_document` — přímé vazby scénáře na dokumenty

Pro dokumenty relevantní pro scénář nad rámec dokumentů zděděných přes uzly
(např. dotační podmínky, sektorové metodiky).

| Sloupec | Typ | Popis |
|---|---|---|
| `scenario_id` | FK → `use_case_scenario` | |
| `document_id` | FK → `Document` | |
| `relevance_note` | `TEXT` | Kontext |

**PK:** `(scenario_id, document_id)`

---

## 8. Compliance pathway — referenční dotazy

### 8.1 Od scénáře k procesním uzlům a předpisům

```sql
-- Kompletní compliance pathway pro scénář 'HRS_VEREJNA'
SELECT pn.id AS uzel, pn.name, il.label AS intenzita,
       d.identifier, d.title, nd.link_type, nd.is_primary_basis
FROM use_case_scenario s
JOIN scenario_node sn      ON sn.scenario_id = s.id
JOIN process_node pn       ON pn.id = sn.node_id AND pn.valid_to IS NULL
JOIN intensity_level il    ON il.code = sn.intensity_code
LEFT JOIN node_document nd ON nd.node_id = pn.id AND nd.link_type = 'LEGAL_BASIS'
LEFT JOIN Document d       ON d.id = nd.document_id
WHERE s.code = 'HRS_VEREJNA'
ORDER BY pn.id, nd.is_primary_basis DESC;
```

### 8.2 Aktivace uzlů podle parametrů záměru

```sql
-- Uzly aktivované pro záměr: elektrolyzér 1.2 MW s prodejem třetím stranám
-- (vyhodnocení skupin pravidel: AND uvnitř skupiny, OR mezi skupinami
--  se provádí v aplikační vrstvě; zde výběr kandidátních pravidel)
SELECT nar.node_id, nar.rule_group, pc.code, nar.comparator, nar.value, nar.description
FROM node_activation_rule nar
JOIN project_criterion pc ON pc.id = nar.criterion_id
WHERE pc.code IN ('KAPACITA_ELEKTROLYZERU', 'PRODEJ_TRETIM_STRANAM')
ORDER BY nar.node_id, nar.rule_group;
```

### 8.3 Od předpisu k procesům (obrácený směr)

```sql
-- V jakých uzlech se uplatňuje energetický zákon?
SELECT pn.id, pn.name, nd.relevance_note
FROM Document d
JOIN node_document nd ON nd.document_id = d.id
JOIN process_node pn  ON pn.id = nd.node_id
WHERE d.identifier = '458/2000 Sb.'  -- bez prefixu "č." (viz reálná data po Kroku 2)
  AND nd.link_type = 'LEGAL_BASIS';
```

### 8.4 Dopad legislativní změny na procesní vrstvu

```sql
-- Které uzly a scénáře jsou dotčeny novelizací dokumentu id = :doc_id?
SELECT 'uzel' AS typ, pn.id AS kod, pn.name
FROM node_document nd JOIN process_node pn ON pn.id = nd.node_id
WHERE nd.document_id = :doc_id
UNION ALL
SELECT 'aktivační pravidlo', nar.node_id, nar.description
FROM node_activation_rule nar WHERE nar.basis_document_id = :doc_id
UNION ALL
SELECT 'scénář', s.code, s.name
FROM scenario_document sd JOIN use_case_scenario s ON s.id = sd.scenario_id
WHERE sd.document_id = :doc_id;
```

Tento dotaz podporuje rozhodovací proceduru V03 §7.5 (zda změna vyžaduje jen
aktualizaci V01, nebo revizi procesního popisu V02).

---

## 9. Migrační plán z produkčního stavu V01

Migrace je navržena jako **čistě aditivní** — žádný krok nemění ani nemaže
existující data či sloupce, produkční aplikace zůstává funkční po celou dobu.

1. **Rozšíření vrstvy A** — `ALTER TABLE` na `Document` (`identifier`,
   **`jurisdikce`** — doplněno Krokem 2, viz §4.1 oprava),
   `DocumentSource` (`institution_type`, `jurisdiction`), `DocumentVersion`
   (`is_current`). **Provedeno a zpětně naplněno 2026-09-09** (`src/tools/init_db.py`):
   `identifier` z pole `znacka` (1337/1344 dokumentů — zbytek jsou
   ojedinělé kolize mezi jurisdikcemi nebo hodnota delší než sloupec),
   `Document.jurisdikce` přímo z pole `jurisdikce` v `database_merged_deduplicated.json`
   (ne odvozeno ze zdroje — viz §4.2 oprava), `DocumentSource.jurisdiction`
   jen doplňkově pro dokumenty se skutečným `gestor`.
2. **Založení vrstvy B** — vytvoření procesních tabulek, import referenčních
   dat U1–U7 z dokumentu V02 (7 uzlů, ~25 větví, ~80 kroků, ~50 vstupů,
   ~30 výstupů, ~25 subjektů, ~25 hran, matice 4×7, ~40 problémů).
3. **Naplnění vrstvy C** — pro každý předpis/pramen citovaný v uzlech V02:
   dohledat či založit řádek `Document` (deduplikace podle `identifier`),
   vytvořit vazbu `node_document`. Bibliografické prameny [1]–[59] se
   zakládají jako `Document` s odpovídajícím `DocumentType` (studie,
   strategie, metodika, …).
4. **Založení vrstvy D** — číselníky hledisek, kritéria, formalizace
   aktivačních pravidel (analytická práce nad sekcemi U.x.3 dokumentu V02),
   typové scénáře z metodiky V01/V03 a jejich procesní profily.
5. **Verifikace** — kontrolní dotazy: každý uzel má ≥1 `LEGAL_BASIS` dokument,
   každý dokument typu legislativa má vyplněný `identifier`, matice
   `node_variability` má přesně 28 řádků, každý scénář má ≥1 uzel.

Lokální soubor `Databáze.V01/regulatory_documents.db` (SQLite) je vývojový
artefakt — migrace se provádí nad produkční MariaDB; SQLite verzi lze
regenerovat z DDL pro lokální vývoj (SQLite nezná `ENUM`, v DDL jsou proto
ENUMy doplněny CHECK constrainty jako přenositelná alternativa — viz
poznámky v `Konsolidace-DB-schema.sql`).

---

## 10. Implementační poznámky

- **Znaková sada:** `utf8mb4` / `utf8mb4_czech_ci` (česká diakritika, řazení).
- **Engine:** InnoDB (referenční integrita, transakce).
- **ENUM vs. číselník:** ENUM je použit jen pro uzavřené technické domény
  (`link_type`, `comparator`, `data_type`); věcné domény, u nichž lze čekat
  růst (typy technologií, kritéria, oblasti), jsou číselníkové tabulky.
- **Fulltext:** FULLTEXT indexy na `node_description` a `node_problem.description`
  (MariaDB podporuje na InnoDB); na `Document.description` dle potřeby aplikace.
- **Kaskády:** `ON DELETE CASCADE` pouze u čistých satelitů uzlu
  (`node_description`, `branch_step`, …); vazby na `Document` mají
  `ON DELETE RESTRICT` — dokument citovaný uzlem nelze smazat (soft-delete
  přes verzování je preferovaný postup V01).
- **Aplikační vrstva:** vyhodnocení aktivačních pravidel (AND/OR skládání
  skupin) a označování `is_current` verze patří do aplikační logiky (Flask);
  schéma poskytuje data, ne rozhodovací stroj.
- **Rozšiřitelnost:** budoucí entity plánované V03 (projektové záměry
  konkrétních investorů, technologické profily) se napojí na
  `use_case_scenario` / `technology_type` bez zásahu do stávajících tabulek.
