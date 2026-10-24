# Automatizace aktualizací databáze

Tento dokument popisuje mechanismus automatizovaných aktualizací databáze
regulačních předpisů (dílčí projekt DP004, výsledek V01) — tedy řetězec,
jímž se nově vydaný nebo změněný předpis dostává od sledovaného
autoritativního zdroje až do běžící databáze. Ostatní části projektu
(datové schéma, webová aplikace, procesní vrstva) zde záměrně
nepopisujeme; pro ně odkazujeme na `PROJECT.md`, `doc/PLAN.md`
a `doc/konsolidace/0README.md`.

Podrobnosti jednotlivých modulů uvádíme v `src/agentic/0README.md`
a `src/tools/0README.md`; návrhová rozhodnutí a jejich odůvodnění
v `doc/PLAN.md` §3 (návrh architektury), §4 (získávání plných textů)
a §45 (realizace na větvi `automation`). Zde tyto zdroje shrnujeme do
jednoho provozního přehledu a doplňujeme je o stav, jenž z nich
jednotlivě není patrný.

---

## 1. Východisko a cíl

Zadání dílčího projektu formuluje požadavek na průběžnou aktualizaci
výslovně: „Databáze bude průběžně aktualizována na základě legislativních
změn a nově schválených regulací.“ (`PROJECT.md`). Formální podobu má
tento požadavek v `doc/REQUIREMENTS.md` jako **R1.9 — Automated
Maintenance**: „The architecture must be capable of receiving automated
or semi-automated updates reflecting legislative and regulatory changes.“

Skutečný stav je k datu tohoto dokumentu (2026-09-20) tento: **jednotlivé
kroky řetězce jsou automatizované, samotné spuštění řetězce nikoli.**
V repozitáři neexistuje žádný plánovač, cron, systemd timer ani CI
workflow — ověřeno přímo, nejen podle dokumentace. Každá dosavadní
aktualizace databáze byla vyvolána člověkem. Kontrolní report
`doc/requirements_check_report.md` proto hodnotí R1.9 jako *PARTIAL*
a toto hodnocení nadále platí. Odstavec 8 shrnuje, co k naplnění
požadavku zbývá doplnit.

Formulace „průběžně aktualizována“ tedy zatím popisuje zamýšlený, ne
dosažený stav; po doplnění kroků z odstavce 8 ji bude možné považovat za
naplněnou.

---

## 2. Celkový přehled řetězce

Řetězec má čtyři vrstvy. Každá z nich je samostatně spustitelná a každá
zapisuje svůj výstup do souboru, takže mezivýsledek lze kdykoli
zkontrolovat, aniž by bylo nutné spustit celý řetězec znovu.

1. **Sledování zdrojů** (odstavec 4) — Dotazování autoritativních
   registrů na nové či změněné dokumenty a stahování plných textů tam,
   kde to licenční podmínky dovolují.
2. **Agentní zpracování kandidátů** (odstavec 5) — Převod nalezeného
   dokumentu na strukturovaný záznam, jehož každé tvrzení je ověřené
   proti zdrojovému textu.
3. **Zapracování do databáze** (odstavec 6) — Šestikrokový přestavbový
   řetězec, jenž z datových souborů sestaví obsah běžící databáze.
4. **Lidská kontrola** (odstavec 7) — Cíl pro vše, co předchozí vrstvy
   samy bezpečně rozhodnout nedokážou.

Schematicky:

```
  autoritativní registry (EUR-Lex Cellar, e-Sbírka LOD, slov-lex.sk)
        │
        │  screen_eurlex.py / screen_esbirka.py / screen_slovlex.py
        ▼
  data/fulltext_screening_candidates.json      ← vrstva 1
        │
        │  run_agentic_pipeline.py  →  src/agentic/ (LangGraph)
        ▼
  discovered_agentic_candidates.json ─┬─ agentic_review_queue.json
                                      └─ agentic_not_relevant.json   ← vrstva 2
        │
        │  (chybějící článek — viz odstavec 6.3)
        ▼
  build_unified_db.py → deduplicate_db.py → link_document_versions.py
        → init_db.py → load_document_relations.py → load_process_layer.py
        ▼                                                             ← vrstva 3
  MariaDB `h2regdocs`
        │
        │  fronty ke kontrole + app/admin.py
        ▼
  editor (dvoustupňové potvrzení)                                     ← vrstva 4
```

---

## 3. Předpoklady provozu

- **Python prostředí:** `.venv`, závislosti v `requirements.txt`
  (instalace `python3 -m venv .venv && .venv/bin/pip install -r
  requirements.txt`). Agentní vrstva přidává `langgraph==1.2.11`.
- **Přístup k databázi:** `.env` v kořeni repozitáře (vzor `.env.example`);
  pro zkušební běhy `.env.test`, jenž míří na oddělenou databázi
  `h2regdocs_test`. Volbu `--env-file` mají pouze skripty, u nichž má
  běh proti zkušební databázi smysl (`provision_db.py`,
  `run_agentic_pipeline.py`); skripty vlastního přestavbového řetězce
  (odstavec 6.1) čtou `.env` napevno. Většina doplňkových
  a obohacovacích skriptů se řídí konvencí přepínače `--apply` — bez něj
  provedou jen suchý běh a vypíšou, co by změnily.
- **Klíč k jazykovému modelu:** soubor `.openapi_key` v kořeni
  repozitáře. Není-li přítomen, agentní vrstva se nezhroutí — každý
  dotčený kandidát skončí v eskalační frontě, nikdy se nedoplní
  odhadem. Tuto vlastnost považujeme za podstatnou a udržujeme ji
  napříč všemi skripty, jež model volají.

---

## 4. Vrstva 1 — Sledování zdrojů

### 4.1 Screeningové skripty

Tři skripty dotazují tři různé registry. Zapisují sice do jednoho
souboru `data/fulltext_screening_candidates.json`, každý však pod vlastní
klíč a — což je pro další zpracování podstatné — **s odlišnou strukturou
záznamu a odlišnou mírou dořešenosti**. Tento rozdíl není v názvu souboru
patrný, a proto jej zde uvádíme výslovně.

Tyto tři skripty představují dnešní, nikoli zamýšlený rozsah sledování.
Úplný seznam zdrojů, jež sledujeme nebo sledovat chceme — včetně
ověřených adres, způsobu dotazování a překážek — vede registr popsaný
v odstavci 11.

| Skript | Zdroj | Klíč | Povaha výstupu |
|---|---|---|---|
| `screen_eurlex.py` | EUR-Lex Cellar SPARQL (veřejný, bez autentizace) | `"EUR-Lex"` | Skutečné vyhledávání nových dokumentů. Záznam `{celex, title, url, matched_keyword, screened_at}`, odrozdílovaný proti korpusu podle číselné reference aktu. Aktuálně 300 položek. |
| `screen_esbirka.py` | `opendata.eselpoint.gov.cz/sparql` (LOD) | `"e-Sbirka"` | Nedořešené fragmenty. Záznam `{uri, snippet, matched_keyword, note, screened_at}` — **neobsahuje pole `url` ani `title`** a neurčuje, kterému předpisu fragment náleží. Aktuálně 100 položek. |
| `screen_slovlex.py` | `slov-lex.sk` | `"Slov-Lex"` | **Nejde o vyhledávání nových dokumentů**, nýbrž o kontrolu funkčnosti již evidovaných odkazů `odkaz_sk`. Aktuálně 0 položek. |

Omezení u druhého a třetího zdroje nejsou opomenutím, nýbrž doloženým
stavem těchto služeb (podrobně v úvodních komentářích obou skriptů):

- Skutečné REST API e-Sbírky (`sbr-externi`) vyžaduje registraci klienta
  u Ministerstva vnitra datovou schránkou, tedy krok, jenž automatizovat
  nelze. Veřejně dostupná je pouze paralelní služba propojených
  otevřených dat, v jejímž grafu ovšem nalezený fragment nenese
  spolehlivou zpětnou vazbu na předpis, jemuž náleží.
- Slov-Lex nemá potvrzené veřejné API ani fulltextové vyhledávání
  dostupné běžným klientem; programový fulltext nabízí pouze placená
  služba třetí strany. Vyhledávání nových slovenských předpisů tedy zatím
  automatizovat nelze.

### 4.2 Stahování plných textů

`fetch_fulltext.py` stahuje plné texty do `data/fulltext/` a vede o nich
manifest `data/fulltext_manifest.json` (klíč `zdroj_dat|znacka|url_field`,
hodnota nese `status`, `local_path`, `sha256`, `http_status`
a `fetched_at`). Manifest čte přímo `init_db.py` při plnění sloupce
`Document.file_path`, a rovněž agentní vrstva, jež dává přednost již
staženému souboru před opakovaným dotazem na zdroj.

**Normy se nestahují nikdy.** Skript je vylučuje dvojí, na sobě nezávislou
kontrolou — podle typu dokumentu (`typ_dokumentu == "Norma"`) a podle
tvaru samotného označení, protože v korpusu se vyskytly citace norem
uvnitř zákonného zdroje. Důvodem je autorskoprávní ochrana a podmínky
užití vydavatelů (ÚNMZ, CEN/CENELEC, ISO/IEC), jež hromadné či
automatizované stahování zapovídají. Toto omezení je trvalé a žádná
z dalších vrstev je neobchází; u norem proto nelze provést ověření proti
plnému textu podle odstavce 5.3 a databáze u nich zůstává odkázána na
metadata a na (obvykle placené) služby třetích stran.

---

## 5. Vrstva 2 — Agentní zpracování kandidátů

Tuto vrstvu tvoří balík `src/agentic/`, řízený z příkazové řádky
skriptem `src/tools/run_agentic_pipeline.py`. Realizuje architekturu
navrženou v `doc/PLAN.md` §3 na základě externího podkladu
(`doc/automation_proposal/`). Vznikla na větvi `automation` a **vědomě
obchází dřívější zamítnutí této architektury v `doc/PLAN.md` §5**, a to
na základě výslovného zadání omezeného na tuto větev; pro větev `master`
zůstává zamítnutí v platnosti.

### 5.1 Důvod, proč agenti, a ne další skripty

Dosavadní obohacovací skripty (`enrich_eu_laws.py`, `process_laws.py`,
`enrich_annotations.py`) volají jazykový model jednorázově, bez ověření
výsledku, bez řízeného opakování a bez sdíleného stavu. Právě tento tvar
stojí za nedůvěryhodným deduplikačním během 281 → 165 záznamů, jejž
popisuje `doc/PLAN.md` §3.1. Agentní vrstva proti tomu staví
deterministický stavový automat (`langgraph`), v němž je ověření
samostatným, povinným krokem.

### 5.2 Složení a tok

Pět agentů podle `doc/PLAN.md` §3.2, zapojených do grafu
`src/agentic/graph.py`:

1. **Parser** (`parser.py`) — Převádí zdrojový dokument na čistý text.
   Přednost dává již staženému souboru z manifestu podle odstavce 4.2,
   jinak stahuje živě. PDF zpracovává knihovnou `pdfplumber`, HTML
   knihovnou `BeautifulSoup`. Oproti původnímu návrhu zde **nepoužíváme**
   model pro rozbor rozvržení stránky (LlamaParse, Docling, Marker):
   reálným vstupem jsou digitálně vzniklá PDF a HTML, nikoli skeny, takže
   by tato vrstva řešila problém, který zdejší korpus nemá.
2. **Extraction** (`extraction.py`) — Naplňuje strukturovaný záznam
   (`znacka`, `nazev`, `typ_dokumentu`, `gestor`) a povinné pole
   `verification_evidence` s doslovnými citacemi ze zdrojového textu.
3. **Verification** (`verification.py`) — Ověřuje každou citaci proti
   zdrojovému textu. Podrobně v odstavci 5.3.
4. **Research** (`research.py`) — Doplňuje pole, jež po ověření zůstala
   prázdná, a to živými dotazy na EUR-Lex Cellar
   (`src/sites/eurlex.py`). Spouští se pouze podmíněně. Nahrazuje
   `search_agent.py`, jenž se dotazoval obecného webového vyhledávače.
5. **Reconciliation** (`reconciliation.py`) — Porovnává kandidáta
   s obsahem běžící databáze. Nejprve přesnou shodou označení (sdílená
   funkce `link_document_relations_auto.digit_core()`), teprve poté
   heuristikou překryvu slov v názvu (Jaccardův koeficient, práh 0,6).
   Druhý krok označujeme za heuristiku záměrně — nejde o sémantickou
   podobnost počítanou z vektorových reprezentací, již návrh zmiňuje.
   **Agent nikdy neslučuje záznamy**; vrací pouze verdikt `new`,
   `existing`, nebo `ambiguous`.

Tok grafu: Parse → Extract → Verify → (opakování, nebo eskalace) →
Research (podmíněně) → Reconcile → (eskalace při `ambiguous`, jinak
konec). Selhání stahování eskaluje ihned, bez volání modelu.

Každá závislost na vnějším prostředí (stahování, volání modelu, spojení
s databází) se do `build_graph()` předává jako parametr s výchozí
hodnotou. Testy díky tomu procházejí celým grafem bez jediného
skutečného volání.

### 5.3 Ověřování proti zdroji

Ověřovací krok je **deterministický, nikoli druhé volání modelu**.
Funkce `verify_evidence()` porovnává každou citaci s normalizovaným
zdrojovým textem; normalizace sjednocuje bílé znaky a velikost písmen,
záměrně však neodstraňuje interpunkci ani diakritiku, aby pozměněná
formulace neprošla. Chybějící či prázdné pole `verification_evidence`
je vyhodnoceno jako neúspěch — mlčení se za doklad nepovažuje.

Neúspěch vrací řízení agentu Extraction, jemuž se do zadání připojí
právě ty citace, které neobstály. Počet pokusů je omezen na tři
(`MAX_VERIFICATION_ATTEMPTS`); po jejich vyčerpání kandidát **eskaluje**,
nikdy neprojde mlčky dál.

Původní návrh (`doc/PLAN.md` §3.5) tento krok považoval za
neuskutečnitelný, protože žádný tehdejší skript neměl plný text, z něhož
by se dalo citovat. Tento předpoklad již neplatí: `fetch_fulltext.py`
(odstavec 4.2) plné texty zákonů má, takže ověření zde probíhá proti
skutečnému textu, nikoli jako náhradní strukturní kontrola.

### 5.4 Předfiltr věcné příslušnosti

U kandidátů z EUR-Lexu se před spuštěním grafu uplatní filtr převzatý ze
skriptu `add_eurlex_hydrogen_acts.py` (funkce `classify_candidate()`
a `is_off_topic()`). Důvod je konkrétní a byl zjištěn živým během při
vývoji: agenti Extraction a Verification ověřují, že dokument říká, co se
o něm tvrdí, nikoli že jde o **druh** dokumentu, jejž tato databáze
sleduje. Bez filtru by proto ověřením řádně prošly a jako nové záznamy se
zapsaly výzva k předkládání návrhů, pracovní dokument útvarů Komise,
písemná parlamentní otázka i zpráva o roční účetní závěrce.

Jde o tentýž jev, jejž zmíněný skript řešil již dříve (`doc/PLAN.md` §28:
z 51 živě ověřených závazných aktů bylo 38 falešně pozitivních); rozsah
dokládá i soubor `data/eurlex_administrative_not_imported.json` s 239
odloženými položkami. Filtr proto znovu používáme, místo abychom jej
psali podruhé.

### 5.5 Výstupy

| Soubor | Obsah |
|---|---|
| `data/discovered_agentic_candidates.json` | Kandidáti s verdiktem `new`, jež prošli ověřením. Tvar záznamu odpovídá rodině `discovered_*.json`. |
| `data/agentic_review_queue.json` | Eskalované případy a verdikty `existing`/`ambiguous` — cíl lidské kontroly podle `doc/PLAN.md` §3.3, krok 6. |
| `data/agentic_not_relevant.json` | Položky odfiltrované podle odstavce 5.4. Zaznamenáváme je, nikoli zahazujeme. |
| `data/agentic_pipeline_processed.json` | Evidence již zpracovaných URL. Zajišťuje, že opakovaný běh zpracuje pouze nové kandidáty. |

Spuštění:

```
.venv/bin/python src/tools/run_agentic_pipeline.py --env-file .env.test --limit 5
.venv/bin/python src/tools/run_agentic_pipeline.py --apply
```

### 5.6 Které zdroje vrstva zpracovává

Protože jeden soubor nese tři různé druhy obsahu (odstavec 4.1),
deklaruje skript `run_agentic_pipeline.py` v tabulce `SOURCE_HANDLING`
výslovně, co s kterým zdrojem dělá: kandidáti z EUR-Lexu se zpracovávají,
položky e-Sbírky a Slov-Lexu nikoli, a to s uvedeným důvodem. Zdroj
v tabulce neuvedený se přeskočí a ohlásí, nikdy nezpracuje na základě
domněnky; přidání nového screeningového skriptu tedy vyžaduje i vědomé
doplnění této tabulky.

Deklarace nahradila dřívější stav, v němž se položky e-Sbírky
přeskakovaly pouze proto, že nesou pole `uri`, nikoli `url`, a propadly
tak kontrolou prázdné adresy. Výsledek byl sice věcně správný, ale
náhodný: kdyby screeningový skript pole `url` kdykoli doplnil, začalo by
do zpracování vstupovat sto nedořešených fragmentů jako plnohodnotné
dokumenty. Regresní test na přesně tento případ (položka e-Sbírky
s vyplněným polem `url` musí být i tak přeskočena) je v
`tests/test_run_agentic_pipeline.py`.

Každý běh nyní vypisuje, kolik položek a z jakého důvodu přeskočil, a to
za celý vstupní soubor bez ohledu na volbu `--limit` — přeskočené
položky se tedy nikdy neztratí z dohledu. Položka zdroje označeného za
zpracovatelný, jíž deklarované pole s adresou chybí, se hlásí zvlášť
jako odchylka: znamená patrně, že se změnil tvar výstupu screeningového
skriptu.

---

## 6. Vrstva 3 — Zapracování do databáze

### 6.1 Přestavbový řetězec

Závazné pořadí kroků úplné přestavby udržuje seznam `PIPELINE_SCRIPTS`
ve skriptu `src/tools/check_requirements.py`. Jde o **šest** skriptů:

1. `build_unified_db.py` — Sloučí zdrojové soubory do
   `data/database_merged_raw.json` a aplikuje překryvné opravy
   (odstavec 6.2).
2. `deduplicate_db.py` — Vytvoří `data/database_merged_deduplicated.json`.
3. `link_document_versions.py` — Propojí vydání a novely; upravuje
   deduplikovaný soubor na místě.
4. `init_db.py` — Naplní databázi MariaDB z deduplikovaného souboru.
5. `load_document_relations.py` — Zavede vztahy mezi dokumenty.
6. `load_process_layer.py` — Zavede procesní vrstvu.

Krok 3 na několika místech starší dokumentace chybí (`src/tools/0README.md`
i vlastní komentář skriptu `backfill_descriptions.py` uvádějí řetězec
pětikrokový). Rozhodující je seznam v kódu; při nejbližší revizi těchto
textů bude vhodné je srovnat.

### 6.2 Překryvné opravy

`build_unified_db.py` aplikuje na každý záznam pět překryvných funkcí:
`apply_authoritative_metadata()`, `apply_synthesized_summary()`,
`apply_eu_transposition()`, `apply_missing_jurisdikce()`
a `apply_manual_corrections()`. Tím se udržuje zásada, jíž se projekt
řídí: oprava se zapisuje tam, odkud ji přestavba znovu načte, nikoli
pouze do běžící databáze. Poslední z nich přenáší do přestavby i opravy
potvrzené editorem ve webovém rozhraní (odstavec 7).

### 6.3 Chybějící článek mezi vrstvou 2 a vrstvou 3

Soubor `data/discovered_agentic_candidates.json` má sice tvar shodný
s ostatními soubory rodiny `discovered_*.json`, avšak **`build_unified_db.py`
pro něj dosud nemá načítací blok**. Pět existujících souborů této rodiny
(`discovered_eu_hydrogen_acts.json`, `discovered_cz_hydrogen_acts.json`,
`discovered_hytep_hydrogen_docs.json`, `discovered_iso_parent_standards.json`,
`discovered_eu_transposition_targets.json`) má každý vlastní, výslovně
zapsaný blok; pro agentní výstup takový blok chybí.

Prakticky to znamená, že výstup vrstvy 2 dnes do databáze nevstupuje —
řetězec na tomto místě končí u souboru, jejž žádný následující krok
nečte. Doplnění je nevelké (blok obdobný pěti stávajícím), pokládáme je
však za samostatný krok, jenž dosud nebyl proveden, a proto jej uvádíme
zde i v odstavci 8.

### 6.4 Doplňkové skripty `backfill_*`

Dřívější poznámka v `doc/PLAN.md` §40 uvádí, že automatizovaná aktualizace
bude muset volat všechny doplňkové skripty `backfill_*.py`. Podle
současného stavu kódu je toto tvrzení příliš silné: většina jejich
logiky byla mezitím přenesena přímo do `init_db.py`, respektive do
překryvných funkcí podle odstavce 6.2. Ověřený stav:

| Skript | Stav při úplné přestavbě |
|---|---|
| `backfill_language.py` | Nadbytečný — `init_db.py` provádí tutéž trojstupňovou kaskádu určení jazyka. |
| `backfill_norm_designation.py` | Nadbytečný — `init_db.py` volá `format_norm_title()` po vyřešení označení. |
| `backfill_slug.py` | Nadbytečný — obojí volá tutéž funkci `slug.assign_slugs()`. |
| `backfill_puvodce.py` | Nadbytečný — pokryto větví `resolve_puvodce()` ve funkci `resolve_gestor()`. |
| `backfill_standards_body.py` | Nadbytečný — pokryto větví pro typ `Norma` ve funkci `resolve_gestor()`. |
| `backfill_eu_gestor.py` | **Nadále nutný.** Viz níže. |
| `backfill_descriptions.py` | **Nepoužívat** — nahrazen (`doc/PLAN.md` §22). Zapisuje pouze do běžící databáze, takže nejbližší přestavba jeho výsledek tiše zahodí. |

Výjimka `backfill_eu_gestor.py` má strukturní důvod: tento skript jako
jediný **plní** vyrovnávací paměť `data/eu_gestor_cache.json`, kterou
`init_db.py` (prostřednictvím `puvodce.load_eu_gestor_cache()`) pouze
čte. Nově přidaný akt EU, jenž v paměti dosud není, proto zůstane bez
gestora a označený k revizi. Skript navíc pracuje nad **běžící
databází**, nikoli nad datovými soubory, takže jeho pořadí je dané:
spouští se **po** `init_db.py` a jeho přínos se do dat promítne až při
následující přestavbě. Automatizovaná aktualizace, jež přidává akty EU,
tedy bude potřebovat dva průchody, nebo samostatné doplnění paměti před
přestavbou.

---

## 7. Vrstva 4 — Lidská kontrola

Žádná z předchozích vrstev nerozhoduje sporné případy sama. Vše, co
bezpečně rozhodnout nelze, se zapisuje do některé z front ke kontrole;
jejich současný stav uvádíme pro představu o rozsahu:

| Fronta | Položek | Původ |
|---|---|---|
| `data/incomplete_records_review_queue.json` | 340 | `init_db.py` — neúplné záznamy |
| `data/dvgw_unresolved_review_queue.json` | 32 | nedohledaná označení DVGW |
| `data/orphan_amendment_review_queue.json` | 10 | novely bez nalezeného základu |
| `data/agentic_review_queue.json` | — | vrstva 2 (odstavec 5.5) |
| `data/dedup_review_queue.json`, `data/document_relations_review_queue.json`, `data/process_layer_review_queue.json`, `data/esbirka_relevance_review_queue.json` | 0 | vyčerpáno |

Vedle nich stojí soubory `*_not_imported.json`, jež zaznamenávají vědomě
nezařazené položky (`data/eurlex_administrative_not_imported.json` 239,
`data/esbirka_off_topic_not_imported.json` 55,
`data/eurlex_off_topic_not_imported.json` 38). Zásadou je, že vyloučená
položka se zaznamenává, nikoli tiše zahazuje.

Pro opravy přímo v datech slouží editorské rozhraní `app/admin.py`
(`doc/PLAN.md` §42): přihlášený editor navrhne opravu, jiný editor ji
potvrdí (různost obou editorů vynucuje i databázové omezení
`chk_ri_distinct_reviewers`), teprve poté se oprava promítne do živého
záznamu, zapíše do auditního záznamu a současně do
`data/manual_corrections.json`, odkud ji převezme nejbližší přestavba.

**Fronta z vrstvy 2 do tohoto rozhraní zatím napojena není.** Důvod je
věcný: tabulka `ReviewItem` se váže na existující `Document.id`, kdežto
eskalovaný kandidát z agentní vrstvy svůj záznam v databázi zatím nemá.
Napojení proto vyžaduje buď samostatný typ položky pro dosud nezaložený
dokument, nebo pořadí, v němž kandidát nejprve vznikne jako záznam
označený k revizi.

---

## 8. Co zatím automatizované není

Následující body považujeme za zbývající rozsah prací k naplnění
požadavku R1.9. Uvádíme je úplně, včetně těch, jež jsou důsledkem
vnějších omezení a patrně trvat budou.

1. **Plánovač.** Neexistuje žádný cron, systemd timer ani CI workflow;
   celý řetězec se spouští ručně. Jde patrně o nejdůležitější chybějící
   článek: bez něj zůstává „průběžná aktualizace“ vlastností, kterou
   řetězec umožňuje, nikoli kterou vykazuje. Souvisí s tím dosud
   nerozhodnutá otázka, již eviduje `doc/requirements_check_report.md`
   (bod 8 seznamu k dořešení): zda je skutečný plánovač v rozsahu této
   fáze projektu, nebo zda by se naopak mělo upravit znění požadavku
   R1.9 tak, aby odpovídalo ručnímu spouštění. Rozhodnutí přísluší
   zadavateli a mělo by patrně padnout dříve, než se plánovač začne
   budovat.
2. **Napojení výstupu vrstvy 2 na přestavbu** (odstavec 6.3) — Dokud
   `build_unified_db.py` nemá načítací blok pro
   `discovered_agentic_candidates.json`, výsledky agentní vrstvy se do
   databáze nedostanou.
3. **Vyhledávání nových dokumentů mimo EUR-Lex.** Agentní vrstvou dnes
   projdou pouze kandidáti z EUR-Lexu, a to nyní na základě výslovné
   deklarace (tabulka `SOURCE_HANDLING`, odstavec 5.6), nikoli náhody.
   Zbývající mezera je věcná, nikoli programátorská: pro e-Sbírku
   neumíme nalezený fragment přiřadit k předpisu, jemuž náleží, a pro
   Slov-Lex neexistuje veřejné fulltextové vyhledávání, z něhož by se
   dalo vycházet (odstavec 4.1). Obojí bude vyžadovat nový zdroj
   signálu, ne úpravu agentní vrstvy — viz registr sledovaných zdrojů
   v odstavci 11.
4. **Napojení eskalační fronty na editorské rozhraní** (odstavec 7).
5. **Rozšíření schématu podle `doc/PLAN.md` §3.4** — Pole
   `hydrogen_specifics` a `legal_relationships` z navrženého
   extrakčního schématu nemají dosud v databázi žádný sloupec.
   Rozhodnutí z `doc/PLAN.md` §5 (normalizované číselníky ve stylu
   konsolidovaného schématu) zůstává v platnosti, realizováno však
   nebylo.
6. **Agent Research pro slovenské a české zdroje** — Doplňování
   chybějících polí dnes funguje pouze proti EUR-Lex Cellar; pro
   Slov-Lex ani e-Sbírku obdobný strukturovaný zdroj k dispozici není
   (odstavec 4.1).
7. **Plné texty norem** (odstavec 4.2) — Trvalé omezení dané
   autorskoprávní ochranou, nikoli nedokončená práce. U norem proto
   ověření proti plnému textu možné nebude.

---

## 9. Spuštění dnes

Úplný ruční průchod řetězcem, od sledování zdrojů po naplněnou databázi.
Pořadí je závazné; skripty vrstvy 1 a 2 lze spouštět samostatně
a opakovaně, neboť jsou idempotentní.

```bash
# 1. Sledování zdrojů (volitelně, dle potřeby)
.venv/bin/python src/tools/screen_eurlex.py
.venv/bin/python src/tools/fetch_fulltext.py

# 2. Agentní zpracování kandidátů (nejprve nanečisto)
.venv/bin/python src/tools/run_agentic_pipeline.py --env-file .env.test --limit 5
.venv/bin/python src/tools/run_agentic_pipeline.py --apply

# 3. Přestavba databáze (šest kroků, závazné pořadí)
.venv/bin/python src/tools/build_unified_db.py
.venv/bin/python src/tools/deduplicate_db.py
.venv/bin/python src/tools/link_document_versions.py
.venv/bin/python src/tools/init_db.py
.venv/bin/python src/tools/load_document_relations.py
.venv/bin/python src/tools/load_process_layer.py

# 4. Doplnění gestorů u aktů EU (nad živou databází, viz odstavec 6.4)
.venv/bin/python src/tools/backfill_eu_gestor.py --apply

# 5. Kontrola souladu s požadavky
.venv/bin/python src/tools/check_requirements.py
```

Zkušební běhy doporučujeme vést proti databázi `h2regdocs_test`, již lze
kdykoli znovu založit skriptem
`provision_db.py --env-file .env.test --schema-only`. U skriptů, které
volbu `--env-file` nemají (kroky 3 a 4 výše, viz odstavec 3), je k tomu
nutné dočasně přesměrovat samotný soubor `.env` — proto doporučujeme
zkoušet zvlášť vrstvu 2, jež zkušební databázi podporuje přímo.

---

## 10. Testy

Agentní vrstvu pokrývá 38 testů v souborech `tests/test_agentic_*.py`
a `tests/test_run_agentic_pipeline.py`; jejich rozsah popisuje
`tests/0README.md`. Testy jsou čisté — celý graf procházejí
s podvrženými implementacemi stahování, jazykového modelu i databázového
spojení, takže neprovádějí žádné skutečné síťové volání. Spuštění celé
sady (952 testů):

```
.venv/bin/python -m unittest discover -s tests -p "test_*.py"
```

Nad rámec testů byla agentní vrstva ověřena i živě (2026-09-19, databáze
`h2regdocs_test`): skutečné stažení, extrakce, ověření a porovnání nad
reálnými kandidáty z EUR-Lexu, včetně obou chybových cest — vyčerpání tří
pokusů o ověření a okamžité eskalace při selhání stahování.

---

## 11. Registr sledovaných zdrojů

Dnešní sledování stojí na třech zdrojích (odstavec 4.1), což zdaleka
nepokrývá místa, kde nové vodíkové předpisy vznikají. Registr
`data/monitored_sources.json` proto vede **úplný seznam zdrojů, jež
sledujeme nebo sledovat chceme** — 42 položek, u každé ověřená adresa,
způsob dotazování, přínos a překážky. Registr je strojově čitelný, aby
z něj mohly budoucí screeningové skripty vycházet, a zároveň čitelný
člověkem, protože rozhodnutí typu „tento zdroj sledovat nebudeme“ je
nutné uchovat i s odůvodněním.

### 11.1 Struktura záznamu

Každá položka nese pole `id`, `name`, `category`, `jurisdiction`, `url`,
`access` (způsob a případná strojově čitelná adresa), `status`,
`screener` (cesta ke skriptu, pokud existuje), `cadence` (navrhovaná
perioda), `priority`, `adds` (co zdroj přináší nad rámec stávajícího
pokrytí), `constraints` a `verified_at`.

Pole `status` nabývá sedmi hodnot:

| Hodnota | Význam | Počet |
|---|---|---|
| `automated` | Sledujeme dnes, existuje skript. | 10 |
| `ready` | Strojově čitelná cesta ověřena, zbývá ji zapojit. | 10 |
| `needs_work` | Dostupné, ale vyžaduje sběr z HTML nebo nestabilní vzor adresy. | 7 |
| `manual_only` | Vhodné jen k občasné lidské kontrole, ne k automatizaci. | 6 |
| `prohibited` | Podmínky užití nebo `robots.txt` automatizovaný přístup zapovídají. | 5 |
| `blocked` | Technická překážka (ochrana proti robotům, aplikace vykreslovaná až v prohlížeči). | 3 |
| `rejected` | Ověřeno a zavrženo pro nedostatek užitečného signálu. | 1 |

Pole `verified_at` nese datum, kdy byla adresa naposledy ověřena živě.
Hodnota `null` znamená, že zdroj je v aktivním používání pipeline, a jeho
dostupnost tedy ověřuje provoz sám; u nově navržených zdrojů je datum
vyplněno vždy. Jedinou výjimkou je adresa kanálu RSS u ERÚ, převzatá
z patičky ověřené stránky, ale samostatně neověřená — v poli
`constraints` je to uvedeno.

### 11.2 Co registr přináší nového

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

Pro oblast norem platí omezení popsané v odstavci 4.2 i zde: sledujeme
výhradně katalogová a bibliografická data, nikdy chráněné plné texty.
U dvou jinak velmi relevantních zdrojů (ISO/TC 197 a CEN/CLC/JTC 6
*Hydrogen in energy systems*) jde nad rámec technické překážky
i o výslovný zákaz — `robots.txt` výboru CEN/CENELEC zapovídá veškerý
automatizovaný přístup, ačkoli by jeho stránky byly technicky snadno
čitelné. Takový zdroj proto vedeme jako `prohibited` a nesledujeme jej;
náhradní cestou je katalog ČSN, jenž převzaté evropské normy zrcadlí.

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
jsou bez placeného přístupu uzavřené.

### 11.3 Doporučené pořadí prací

Navrhujeme zapojovat v tomto pořadí, sestupně podle poměru přínosu
k pracnosti:

1. **VeKLEP** a **Slov-Lex legislatívny proces** — Oba jsou strojově
   čitelné, oba přinášejí včasný signál, který dnes nemáme vůbec, a oba
   se tvarem blíží stávajícím skriptům `screen_*.py`.
2. **Věstník ÚNMZ** — Jeden hromadný měsíční přírůstek ČSN.
3. **ASTM** a **ASME** — Jediné dva mezinárodní normalizační zdroje
   současně dostupné, server-side vykreslené a bez omezení v `robots.txt`.
4. **UNECE** — Věcně nejhodnotnější (GTR č. 13 pro vodíková vozidla
   a ADR/RID pro přepravu, tedy oblast, kterou nepokrýváme vůbec, a bez
   problému s podmínkami užití), ale vyžádá si headless prohlížeč.

Registr je zároveň podkladem pro pravidelnou kontrolu dostupnosti: pole
`url` a `access.endpoint` lze strojově procházet a hlásit, které adresy
přestaly odpovídat. Tuto kontrolu zatím žádný skript neprovádí; vzhledem
k tomu, že se během tohoto ověřování potvrdil přesun českých úřadů na
doménu `.gov.cz`, půjde patrně o užitečné doplnění.
