# Automatické třídění fronty kandidátů

> Historie dokumentu:  
> 2026-11-20 Návrh první verze: technický účet, pravidla k odsouhlasení, posouzení jazykovým modelem, ukázka na vzorku 40 kandidátů  
> 2026-11-20 Úpravy podle vyjádření uživatele: R1 jen pro týž jazyk, nová pravidla R7 (jazyková verze) a R8 (zrušený předpis se přijímá se stavem „zrušený“), R2 zrušeno; vysvětlení R9

Fronta kandidátů na nové dokumenty (`doc/PROVOZ.md`, odstavec 4) obsahovala
20. 11. 2026 v živé databázi 591 nových kandidátů. Jejich ruční posouzení by
editory zaměstnalo na týdny, přičemž značnou část z nich lze rozhodnout podle
jednoduchých pravidel nebo s pomocí jazykového modelu. Tento dokument popisuje
automatické předtřídění fronty, předkládá k odsouhlasení seznam pravidel
(odstavec 2) a výsledky ukázkového posouzení modelem (odstavec 5). Pravidla ani
model nad živou databází zatím ostře **neběžely**; ostrý běh je technicky
zablokovaný, dokud uživatel souhlas nezapíše (odstavec 7). Uživatel se
20. 11. 2026 k pravidlům vyjádřil (odstavec 2); souhlas zatím zapsán není,
protože nerozhodl o kategoriích, v nichž smí model sám zamítat a odkládat,
ani o otázkách rozsahu z odstavce 8.

## 1. Technický účet „automat“

Rozhodnutí automatu provádí technický účet s přihlašovacím jménem `automat`
a jménem „Automatický navrhovatel“. Účet:

1. **Smí být prvním navrhovatelem přijetí.** Návrh, jejž založí, potvrzuje
   vždy přihlášený editor; podmínka `chk_dc_distinct_reviewers` platí beze
   změny, takže automat svůj návrh potvrdit nemůže ani na úrovni databáze.
2. **Smí podle odsouhlasených pravidel zamítnout nebo odložit.** Obojí je
   vratné: editor kandidáta znovu otevře, návrh automatu vrátí tlačítkem
   **Vrátit návrh**. Kandidáta, jejž editor znovu otevřel, automat při dalším
   běhu už nemění, jen u něj obnoví doporučení.
3. **Nepřihlásí se.** Je neaktivní (`is_active = 0`) a jeho heslový otisk
   (`!`) nevyhovuje žádnému heslu; přihlašovací stránka navíc účet `automat`
   odmítá výslovně a sezení s tímto jménem nepustí do editorské části.
4. **Je odlišený v rozhraní i v auditu.** Jeho návrhy a rozhodnutí nesou ve
   frontě i v auditním logu štítek „automat“, každý záznam auditu má příznak
   `"automat": true`, identifikátor pravidla a zdůvodnění; poznámka
   rozhodnutí začíná „Automat (R4-tpg): …“.

Účet založí první ostrý běh skriptu `src/tools/triage_candidates.py`
(funkce `candidates.automat_id()`).

## 2. Pravidla

Pravidla jsou zapsána jako data v souboru `data/triage_rules.json`, nikoli
v kódu; jejich změna tedy nevyžaduje zásah do programu. Zkoušejí se
v pořadí uvedeném v tabulce (ne podle čísla) a o kandidátovi rozhoduje první
pravidlo, jehož podmínka platí. Počty v posledním sloupci jsme zjistili suchým
během nad živou databází 20. 11. 2026 (`triage_candidates.py --rules-only`) ze
591 nových kandidátů.

| Pořadí | Pravidlo | Podmínka | Akce | Zdůvodnění | Zasáhne v živé DB |
|---|---|---|---|---|---|
| 1 | R1-duplicita | týž předpis (shodný klíč českého předpisu nebo aktu EU) už je v databázi **ve stejném jazyce**; u norem a technických pravidel shodné označení | zamítnout s odkazem na dokument | tentýž dokument nemá být v databázi dvakrát | 0 |
| 2 | R7-jazykova-verze (nové) | týž předpis je v databázi, ale jen v **jiném jazyce** (jazyk kandidáta CS, EN nebo SK) | navrhnout přijetí jako jazykovou verzi | znění v jiném jazyce je samostatný dokument propojený s ostatními verzemi (rozhodnutí uživatele z 20. 11. 2026) | 0 |
| 3 | R8-zruseny (nové, nahrazuje R2) | platnost podle kontroly platnosti „zrušený“ | navrhnout přijetí se stavem „zrušený“ | zrušený předpis se nezamítá; databáze jej vede se stavem a vazbou na předpis, který jej zrušil (rozhodnutí uživatele z 20. 11. 2026) | 1 (vyhláška č. 513/2021 Sb. z tabulek MPO, zrušená k 1. 1. 2026 vyhláškou č. 508/2025 Sb., jež čeká ve frontě) |
| 4 | R3-novinka | adresa novinky (`/news/`, `aktuality`) nebo název obsahuje webinář, factsheet, round table, newsletter, tiskovou zprávu | odložit | novinky nejsou regulační dokumenty; mohou však odkazovat na dokument, který do databáze patří, proto odložit, ne zamítnout | 6 (2× ACER, webinář a factsheet EHSP, kulatý stůl OTIF, aktualita TIČR) |
| 5 | R4-tpg | zdroj `cps-tpg` (katalog technických pravidel TPG) | navrhnout přijetí | rozhodnutí uživatele z 20. 11. 2026 zařadit všechna TPG; jen metadata a odkaz | 69 |
| 6 | R5-mpo | zdroj `mpo` (tabulky předpisů MPO/CDV z 30. 4. 2026) | navrhnout přijetí | referenční soubor objednatele (`doc/MPO_TABULKY.md`); typ a původce jsou u kandidátů již ověřené | 53 |
| 7 | R6-navrh-vodik | návrh předpisu nebo normy (signál `draft`) se známým typem dokumentu a s vodíkem, RFNBO nebo palivovými články v názvu | navrhnout přijetí jako připravovaný dokument | návrh výslovně o vodíku do rozsahu patří vždy | 3 (směrnice Komise v přenesené pravomoci o emisních hodnotách RFNBO, návrhy ČSN o armaturách pro vodíkové aplikace a o malých stacionárních napájecích systémech s palivovými články) |
| 8 | R9-model | všichni ostatní | posouzení jazykovým modelem (odstavec 2.3) | bez deterministického pravidla | 459 |

Pravidla rozhodnou o 132 kandidátech: 126 navrhnou k přijetí, 6 odloží
a žádného nezamítnou; o 459 rozhoduje model.

### 2.1 Proč R7 a R8 a co se stalo s R2

V první verzi zamítalo pravidlo R1 i jinou jazykovou verzi předpisu
a pravidlo R2 každý zrušený předpis. Uživatel rozhodl jinak: zamítá se jen
duplicita ve stejném jazyce (upravené R1), jiná jazyková verze se přijme
(nové **R7**) a zrušený předpis se přijme se stavem „zrušený“ (nové **R8**).
Pravidlo R2 tím zaniklo a jeho číslo se už nepoužije. Nová pravidla dostala
čísla 7 a 8, aby posouzení modelem (R9) zůstalo posledním pravidlem; v pořadí
vyhodnocení stojí R7 a R8 hned za R1, aby zrušený předpis nebo jazykovou verzi
z tabulek MPO zachytila dřív než obecné R5.

**R7 — jazyková verze.** Kandidát dostane označení podle konvence
`language_variants.py`: české znění holé označení, anglické `<značka> [EN]`,
slovenské `<značka> [SK]`; věcné okruhy převezme od verzí, jež databáze má.
Při potvrzení vznikne vazba `TRANSLATION_OF` se **všemi** jazykovými verzemi
téhož předpisu v databázi: z anglického či slovenského znění na české
(stejný směr jako u dvojic z Haltufovy tabulky), mezi dvěma nečeskými zněními
od nového k existujícímu. Vazby se zapíší i do
`data/document_relations_editor.json`, který čte `load_document_relations.py`,
takže přežijí přestavbu databáze (soubor `data/document_relations_variants.json`
naproti tomu přepisuje `split_language_variants.py` při každém běhu, proto do něj
nezapisujeme). Je-li holé označení obsazené dokumentem v jiném jazyce (anglicky
titulované dokumenty bez přípony), návrh neprojde kontrolou označení a zůstane
jen doporučením.

**R8 — zrušený předpis.** Dokument vznikne se stavem `repealed`
(„zrušený“). Zrušující předpis se zjistí z podkladů kandidáta (`validity.repealed_by`,
kontrola platnosti u tabulek MPO) nebo z mezipaměti `data/validity_cache.json`:

1. Je-li zrušující předpis v databázi, vznikne při potvrzení vazba `REPEALS`
   od něj ke zrušenému.
2. Čeká-li ve frontě (u vyhlášky č. 513/2021 Sb. jde o vyhlášku č. 508/2025 Sb.,
   kandidáta z tabulek MPO), připíše se nový dokument do jeho `repeals_ids`;
   vazbu `REPEALS` pak vytvoří přijetí zrušujícího předpisu stávajícím
   mechanismem (`create_document()` v `app/candidates_admin.py`).
3. Není-li ani ve frontě, automat jej do fronty přidá jako kandidáta zdroje
   „nástupce zrušeného dokumentu“ bez sítě, s označením a adresou odvozenými
   z klíče; úřední název doplní nejbližší `import_candidates.py --apply`
   (v živé frontě se to dnes netýká žádného kandidáta).

Aby stav a vazba přežily přestavbu, zapíše přijetí údaj o platnosti do
`data/validity_cache.json`, chybí-li tam (u kandidátů z tabulek MPO);
`init_db.py` a `backfill_document_states.py` z něj stav i vazbu `REPEALS`
odvodí znovu (`document_states.py`).

### 2.2 Údaje návrhu

Technická pravidla TPG dostanou typ „Norma“
(stejně jako pravidla DVGW a EIGA v databázi a podle rozhodnutí
v `doc/DATA_SOURCES.md`, odstavec 8.12: u TPG databáze uchovává jen
metadata, typ „Norma“ zajistí, že `fetch_fulltext.py` text nestahuje), původce
„Český plynárenský svaz (ČPS)“, jazyk CS, jurisdikci CZ, název bez opakovaného
označení a adresu katalogu ČPS. Věcný okruh se u TPG odvodí z čísla pravidla
(řada 2 skladování, 304 plnicí stanice, 6 a 7 plynovody a regulace, 704 a 8
odběrná zařízení, 9 bezpečnost, 900–902 a 934 energetika a měření, 982 vozidla
CNG); u ostatních pravidel z okruhů, jež kandidát už má (tabulky MPO),
z výrazů v názvu (slovník `area_keywords`) a nakonec z výchozího okruhu
pravidla. Všechny údaje projdou stejnou kontrolou jako ruční návrh editora
(`candidates.validate_proposal()`); návrh, který kontrolou neprojde, zůstane
jen doporučením.

### 2.3 R9: co je „ostatní“ a jak probíhá posouzení modelem

Pravidlu R9 připadne každý kandidát, o němž žádné z pravidel R1 až R8
nerozhodlo: v živé frontě 459 kandidátů, převážně předpisy citované v textech
databáze (uzávěr citací, 287), nálezy e-Sbírky, sněmovní tisky, normy SAE
a Věstníku ÚNMZ, materiály EHSP a nástupci zrušených dokumentů. U nich nelze
z jednoduchých znaků (zdroj, platnost, název) poznat, zda do databáze patří;
posoudí je proto jazykový model OpenAI GPT (`gpt-4o-mini`), a to takto:

1. Skript složí pro kandidáta **zadání**: popis rozsahu databáze z dokumentu
   `doc/DATABASE_SCOPE.md` a údaje kandidáta (označení, název, adresa,
   veřejné úryvky textů, jež jej citují). Posílají se jen veřejné údaje
   (odstavec 3.1).
2. Model vrátí **doporučení** přijmout, zamítnout nebo odložit, věcné okruhy,
   typ dokumentu, původce, jistotu 0–1 a krátké zdůvodnění česky
   (odstavec 3.2).
3. Podle **prahů** v souboru pravidel automat s doporučením naloží: s jistotou
   alespoň 0,95 navrhne přijetí (potvrzuje vždy editor); zamítnout či odložit
   smí jen v kategoriích, jež uživatel odsouhlasí (zatím žádné); vše ostatní
   zůstane jen doporučením, které editor uvidí v seznamu i v detailu kandidáta
   (odstavec 3.3).
4. Odpověď se uloží do **mezipaměti**, takže se tentýž kandidát modelu
   neposílá dvakrát; před během skript odhadne cenu a běh nad rozpočtem
   odmítne (odstavec 3.4).

Model tedy sám nic do databáze nepřidá ani bez odsouhlasení nezamítne; jeho
výsledkem je návrh k potvrzení nebo doporučení editorovi.

### 2.4 K rozhodnutí uživatele

1. Pravidla R1, R3 až R8 odsouhlasil uživatel 20. 11. 2026 (R1, R7 a R8 ve
   znění podle jeho úprav).
2. Zbývá rozhodnout, ve kterých kategoriích smí model sám zamítnout či odložit
   (odstavec 3.3). Navrhujeme zamítat kategorie `mimo_rozsah`, `dane_dotace`
   a `zastaraly` a odkládat kategorii `neni_dokument`, vždy jen s jistotou
   alespoň 0,95.
3. Zbývá rozhodnout otázky rozsahu z odstavce 8 (obecné předpisy o výrobcích;
   fondy, dotace a zakázky).

Po rozhodnutí se souhlas zapíše do souboru pravidel (`approval.approved_by`,
`approval.date`) a schválené kategorie se přesunou
z `model.proposed_auto_categories` do `model.auto_categories`.

## 3. Posouzení jazykovým modelem

### 3.1 Co model dostane

Model (OpenAI, `gpt-4o-mini`, volaný stejně jako v `deduplicate_db.py`,
klíč `.openapi_key`) dostane v systémové zprávě výňatek dokumentu
`doc/DATABASE_SCOPE.md` (odstavce 2.1, 3 a 4: geografický rozsah, deset
věcných okruhů, typy dokumentů a úrovně pokrytí), seznam okruhů a typů
dokumentů, počty dokumentů databáze podle typu a nejčastějších původců
a pokyny k hraničním případům (obecné předpisy bez zmínky o vodíku, daně
a dotace, normy cizích organizací, historické předpisy, úplná znění, návrhy
a novely). U kandidáta dostane jen veřejné údaje (`triage.build_payload()`):

* označení, název, typ podle zdroje, adresu, jurisdikci, zdroj, signál
  (nový dokument, návrh, novela), platnost, počet citujících dokumentů;
* nálezy sledovaných zdrojů (název, adresa, datum, veřejný úryvek, strojová
  poznámka kontroly);
* u uzávěru citací označení a názvy nejvýše pěti citujících dokumentů
  databáze a nejvýše dva úryvky citace z každého;
* názvy dokumentů databáze, jež kandidát mění nebo zrušil;
* u tabulek MPO číslo a název řádku (ne poznámky tabulky).

Jména editorů, jejich poznámky (`decision_note`) ani jiné interní údaje se
neposílají; ověřuje to test `test_payload_has_public_data_only`.

### 3.2 Co model vrátí

Strukturovaný JSON podle schématu (`response_format` typu `json_schema`,
přísný režim): zdůvodnění česky (nejvýše tři věty, píše se jako první, aby
model rozhodoval až po úvaze), doporučení (`accept`, `reject`, `defer`),
kategorii (`v_rozsahu`, `mimo_rozsah`, `dane_dotace`, `neni_dokument`,
`zastaraly`, `zahranicni`, `nejiste`), věcné okruhy, typ dokumentu ze seznamu
databáze, původce, úřední název (jen zná-li jej s jistotou) a jistotu 0–1.
Neplatnou odpověď skript zkusí získat znovu (nejvýše třikrát), jinak
kandidáta ponechá editorům.

**Jistota.** Malý model uvádí jistotu převážně 0,9 nebo 0,95 bez ohledu na
obtížnost případu. Skript proto zaznamenává i změřenou pravděpodobnost
prvního slova doporučení (z `logprobs`) a s prahy porovnává menší z obou
hodnot. Protože model rozhoduje až po zdůvodnění, je změřená pravděpodobnost
téměř vždy blízká 1; prakticky tedy rozhoduje jistota uvedená modelem.

### 3.3 Prahy a akce

| Doporučení modelu | Podmínka | Akce automatu |
|---|---|---|
| přijmout | jistota ≥ 0,95 (`accept_threshold`) a aspoň jeden okruh | navrhne přijetí s údaji podle modelu (typ, původce, okruhy; úřední název jen tam, kde kandidát název nemá nebo je zkrácený) |
| zamítnout, odložit | kategorie je v `auto_categories` a jistota ≥ 0,95 (`decline_threshold`) | zamítne, resp. odloží |
| cokoli jiného | — | jen uloží doporučení; editor je vidí v seznamu i v detailu |

Do odsouhlasení je `auto_categories` prázdné, model tedy sám nezamítá ani
neodkládá. Prah 0,95 jsme zvolili podle ukázky (odstavec 5): s prahem 0,9 by
automat navrhl přijetí i dvou dokumentů, jež do databáze zjevně nepatří.

### 3.4 Mezipaměť a cena

Odpovědi se ukládají do `data/triage_model_cache.json` s klíčem z modelu,
verze pokynů (`model.prompt_version`), pokynů a odeslaných údajů; nic se tedy
neposílá dvakrát a opakovaný běh je zdarma. Počty dokumentů databáze, jež se
mění s každým přijetím, v klíči nejsou. Před během skript odhadne počet
tokenů a cenu podle ceníku v souboru pravidel (`gpt-4o-mini`: 0,15 USD za
milion vstupních tokenů, 0,075 USD za milion tokenů z mezipaměti poskytovatele,
0,60 USD za milion výstupních) a běh odmítne, převýší-li odhad rozpočet
`budget_usd` (2 USD) nebo není-li cena modelu známa.

Model `gpt-6.2-astra` je na účtu dostupný, jeho cenu však neznáme, a skript
jej proto bez doplnění ceníku spustit odmítne (odstavec 8).

## 4. Rozhraní

Na stránce `/admin/candidates`:

* **Filtr „Automat“**: návrhy automatu k potvrzení (s počtem), kandidáti
  zamítnutí nebo odložení automatem, kandidáti s doporučením modelu; dále
  filtr doporučení (přijmout, zamítnout, odložit) a jistoty (≥ 0,95, ≥ 0,90,
  ≥ 0,70). Ve filtru automatu se zobrazují obě pásma.
* **Sloupec „Automat“**: doporučení modelu s jistotou (zdůvodnění v bublině),
  nebo identifikátor pravidla; ve sloupci stavu štítek „automat“ u návrhů
  a rozhodnutí automatu.
* **Hromadné akce**: zaškrtávací pole u každého otevřeného kandidáta (a „vybrat
  vše“), tlačítka **Potvrdit přijetí vybraných**, **Odložit vybrané**,
  **Zamítnout vybrané** (zamítnutí vyžaduje důvod). Každý kandidát se zpracuje
  zvlášť se stejnými kontrolami jako jednotlivě a zvlášť se zapíše do auditu
  (s příznakem `"bulk": true`); vlastní návrh ani kandidáta ve stavu, jenž krok
  nedovoluje, akce přeskočí. Potvrzovat smí jen přihlášený editor, nikdy
  automat.
* **Detail kandidáta**: blok „Doporučení automatu“ (pravidlo, doporučení,
  kategorie, zdůvodnění, okruhy, typ a původce, úřední název, jistota uvedená
  a změřená); formulář návrhu přijetí je předvyplněný podle automatu
  (editor údaje zkontroluje).
* **Telefon**: seznam se zobrazuje po kartách (zaškrtávací pole vlevo, pod
  sebou označení, název, stav, doporučení a tlačítko), stránka nemá vodorovný
  posun; ověřuje to scénář `tests/e2e/test_triage_queue.py`.

Auditní log (`/admin/audit-log`) označuje záznamy automatu štítkem a odkazuje
na kandidáta.

## 5. Ukázka: vzorek 40 kandidátů z živé databáze

Vzorek jsme vybrali náhodně (`--rule R9-model --sample 40`, semínko 20261120)
z 459 kandidátů, o nichž rozhoduje model; model se jen volal, do živé
databáze se nic nezapsalo. Pokyny modelu jsme po prvním běhu jednou upravili
(odstavec 5.2); tabulka uvádí výsledek druhého běhu, jenž odpovídá
odevzdané verzi pokynů. Sloupec „Akce automatu“ uvádí, co by automat udělal
s prahy podle odstavce 3.3 a dokud nejsou odsouhlasené kategorie zamítnutí.

| # | Zdroj | Označení a název | Doporučení | Kategorie | Okruhy | Jistota | Akce automatu | Zdůvodnění modelu |
|---|---|---|---|---|---|---|---|---|
| 9 | citace | 1992/43/EHS Směrnice Rady 92/43/EHS ze dne 21. května 1992 o ochraně přírodních stanovišť, volně žijících ž… | přijmout | v_rozsahu | 10 | 0.70 | jen doporučení | Směrnice Rady 92/43/EHS se týká ochrany přírodních stanovišť a volně žijících živočichů, což souvisí s ochranou životního prostředí. I když se přímo nezabývá vodíkovými technologiemi, její ustanovení mohou mít vliv na projekty související s vodíkem, zejména v kontextu posuzování vlivů na životní prostředí. Proto je relevantní pro okruh 10 (Životní prostředí). |
| 29 | citace | 2010/713/EU 2010/713/EU: Rozhodnutí Komise ze dne 9. listopadu 2010 o modulech pro postupy posuzování shody… | přijmout | v_rozsahu | 5, 7 | 0.70 | jen doporučení | Dokument 2010/713/EU je rozhodnutím Komise, které se týká modulů pro postupy posuzování shody a vhodnosti pro použití v technických specifikacích pro interoperabilitu železničního systému. I když se dokument přímo nezmiňuje o vodíku, jeho obsah se vztahuje na oblasti, které mohou mít vliv na provoz a bezpečnost železniční dopravy, což je relevantní pro okruh 5 (Provoz vozidel) a 7 (Bezpečnost). |
| 47 | citace | 148/2023 Sb. Zákon o jednotném environmentálním stanovisku | přijmout | v_rozsahu | 10 | 0.95 | navrhne přijetí | Zákon o jednotném environmentálním stanovisku se týká posuzování vlivů na životní prostředí, což je relevantní pro okruh 10 (Životní prostředí). Tento zákon je účinný a citovaný v několika dalších předpisech, což potvrzuje jeho význam v oblasti regulace životního prostředí. |
| 70 | citace | 1996/53/ES Směrnice Rady 96/53/ES ze dne 25. července 1996, kterou se pro určitá silniční vozidla provozova… | přijmout | v_rozsahu | 4, 5 | 0.95 | navrhne přijetí | Směrnice Rady 96/53/ES se týká maximálních rozměrů a hmotností silničních vozidel, což je relevantní pro okruh 5 (Provoz vozidel) a 4 (Plnění do vozidel), protože se vztahuje na technické požadavky a schvalování vozidel. Dokument je účinný a má citace v dalších relevantních předpisech EU, což potvrzuje jeho význam v oblasti regulace silniční dopravy. Proto patří do rozsahu databáze. |
| 82 | citace | (EU) č. 168/2013 Nařízení Evropského parlamentu a Rady (EU) č. 168/2013 ze dne 15. ledna 2013 o schvalování… | přijmout | v_rozsahu | 5 | 0.95 | navrhne přijetí | Nařízení (EU) č. 168/2013 se týká schvalování dvoukolových a tříkolových vozidel a čtyřkolek, což spadá do okruhu provozu vozidel. Tento dokument je relevantní pro regulaci vozidel, která mohou používat vodík jako alternativní palivo, a proto patří do rozsahu databáze. |
| 160 | citace | 2014/30/EU Směrnice Evropského parlamentu a Rady 2014/30/EU ze dne 26. února 2014 o harmonizaci právních př… | přijmout | v_rozsahu | 7 | 0.80 | jen doporučení | Směrnice 2014/30/EU se týká harmonizace právních předpisů členských států v oblasti elektromagnetické kompatibility, což je důležité pro zařízení, která mohou být součástí vodíkových technologií. I když se vodík přímo nezmiňuje, předpisy o elektromagnetické kompatibilitě mohou mít vliv na zařízení využívající vodík, a proto spadají do okruhu bezpečnosti a provozu zařízení. Dokument je platný a má význam pro EHP. |
| 171 | citace | (EU) 2019/1020 Nařízení Evropského parlamentu a Rady (EU) 2019/1020 ze dne 20. června 2019 o dozoru nad trh… | přijmout | v_rozsahu | 1, 4, 9 | 0.70 | jen doporučení | Nařízení (EU) 2019/1020 se týká dozoru nad trhem a souladu výrobků, což je důležité pro zajištění kvality a bezpečnosti výrobků, včetně těch, které se mohou týkat vodíkových technologií. I když se přímo nezmiňuje vodík, jeho aplikace v oblasti alternativních paliv a souvisejících regulací je relevantní pro okruhy databáze. Proto dokument patří do rozsahu databáze. |
| 179 | citace | 153/2023 Sb. Vyhláška o schvalování technické způsobilosti vozidel a technických podmínkách provozu vozidel… | přijmout | v_rozsahu | 5 | 0.95 | navrhne přijetí | Vyhláška o schvalování technické způsobilosti vozidel se týká podmínek provozu vozidel, což spadá do okruhu 5 (Provoz vozidel). Dokument je platný a byl citován v dalších předpisech, což potvrzuje jeho relevanci. Proto patří do rozsahu databáze. |
| 189 | citace | 345/2002 Sb. Vyhláška, kterou se stanoví měřidla k povinnému ověřování a měřidla podléhající schválení typu | přijmout | v_rozsahu | 4, 7 | 0.95 | navrhne přijetí | Vyhláška č. 345/2002 Sb. se týká měřidel, která podléhají ověřování a schválení typu, což je relevantní pro oblast metrologie a tím i pro okruh 4 (Plnění do vozidel) a 7 (Bezpečnost). Tato vyhláška je platná a má přímou vazbu na regulaci měření, což je důležité pro zajištění kvality a bezpečnosti v oblasti vodíkových technologií. |
| 207 | citace | 1986/278/EHS Směrnice Rady ze dne 12. června 1986 o ochraně životního prostředí a zejména půdy při používán… | přijmout | v_rozsahu | 10 | 0.90 | jen doporučení | Dokument se týká ochrany životního prostředí a používání kalů z čistíren odpadních vod, což spadá do okruhu 10 (Životní prostředí). I když se vodík výslovně nezmiňuje, předpisy o ochraně životního prostředí jsou relevantní pro regulaci vodíkových technologií, zejména v kontextu jejich vlivu na životní prostředí. |
| 591 | ČMI | OOP 0111-OOP-C068-17: Vibrační převodníky relativní hustoty plynů průtočného typu | přijmout | v_rozsahu | 7, 9 | 0.90 | jen doporučení | Dokument se týká vibračních převodníků relativní hustoty plynů, což spadá do oblasti metrologie. Tato metodika je relevantní pro měření a kontrolu plynů, což je důležité pro okruh 7 (Bezpečnost) a 9 (Energetika), protože správné měření hustoty plynů je klíčové pro bezpečnost a efektivitu provozu zařízení. Dokument tedy patří do rozsahu databáze. |
| 409 | e-Sbírka | 470/2012 Sb. Vyhláška o užívání pozemních komunikací zpoplatněných mýtným | přijmout | v_rozsahu | 5 | 0.90 | jen doporučení | Vyhláška se týká užívání pozemních komunikací a zmiňuje vodík v kontextu emisní třídy pro vozidla, což ji činí relevantní pro okruh provozu vozidel. I když se vodík nezmiňuje jako hlavní téma, předpis upravuje podmínky, které se na vodíková vozidla vztahují, a proto patří do rozsahu databáze. |
| 494 | SAE | SAE J2719/1 Application Guideline for Use of Hydrogen Quality Specification | přijmout | v_rozsahu | 4 | 0.95 | navrhne přijetí | Dokument je norma, která se týká specifikace kvality vodíku, což je relevantní pro okruh plnění do vozidel. I když je to mezinárodní norma, její obsah je důležitý pro regulaci vodíkových technologií v rámci databáze. |
| 498 | SAE | SAE J3219 Hydrogen Fuel Quality Screening Test of Chemicals for Fuel Cell Vehicles | přijmout | v_rozsahu | 4 | 0.95 | navrhne přijetí | Dokument je norma, která se týká kvality vodíku pro palivové články, což spadá do okruhu 4 (Plnění do vozidel). Jako mezinárodní norma je relevantní pro vodíkové technologie a její dodržení může ovlivnit shodu s požadavky na kvalitu paliva. Proto dokument patří do rozsahu databáze. |
| 56 | citace | (EU) č. 913/2010 Nařízení Evropského parlamentu a Rady (EU) č. 913/2010 ze dne 22. září 2010 o evropské žel… | zamítnout | mimo_rozsah | — | 0.95 | jen doporučení | Nařízení (EU) č. 913/2010 se týká evropské železniční sítě pro konkurenceschopnou nákladní dopravu, což je relevantní pro oblast dopravy, ale nezmiňuje vodík ani se netýká žádného z okruhů databáze. Proto dokument nepatří do rozsahu databáze. |
| 61 | citace | (EU) č. 651/2014 Nařízení Komise (EU) č. 651/2014 ze dne 17. června 2014 , kterým se v souladu s články 107… | zamítnout | mimo_rozsah | — | 0.90 | jen doporučení | Nařízení Komise (EU) č. 651/2014 se týká podpory v rámci vnitřního trhu, což může mít nepřímý vliv na oblasti jako energetika a využití obnovitelných zdrojů, včetně vodíku. Nicméně, toto nařízení se přímo nezabývá regulací vodíkových technologií nebo jejich životním cyklem, a proto není relevantní pro databázi zaměřenou na vodíkové technologie. Nařízení se tedy do databáze nezahrnuje. |
| 66 | citace | 222/1999 Sb. Zákon o zajišťování obrany ČR | zamítnout | mimo_rozsah | — | 0.95 | jen doporučení | Zákon o zajišťování obrany ČR se týká oblasti obrany a bezpečnosti, což není v souladu s okruhy databáze zaměřenými na vodíkové technologie. Tento zákon se nezabývá výrobou, skladováním, přepravou, plněním nebo využitím vodíku, ani jinými relevantními předpisy uvedenými v rozsahu databáze. |
| 73 | citace | (ES) č. 178/2002 Nařízení Evropského parlamentu a Rady (ES) č. 178/2002 ze dne 28. ledna 2002, kterým se st… | zamítnout | mimo_rozsah | — | 0.95 | jen doporučení | Nařízení (ES) č. 178/2002 se týká potravinového práva a bezpečnosti potravin, což není v souladu s okruhy databáze zaměřenými na vodíkové technologie. Tento dokument se nezabývá výrobou, skladováním, přepravou nebo využitím vodíku, a proto do databáze nepatří. |
| 111 | citace | (ES) č. 883/2004 Nařízení Evropského parlamentu a Rady (ES) č. 883/2004 ze dne 29. dubna 2004 o koordinaci … | zamítnout | mimo_rozsah | — | 0.95 | jen doporučení | Nařízení (ES) č. 883/2004 se týká koordinace systémů sociálního zabezpečení a nesouvisí s vodíkovými technologiemi ani s žádným z okruhů databáze. Tento dokument se zaměřuje na sociální zabezpečení, což je mimo rozsah databáze, která se soustředí na regulace týkající se vodíku a jeho využití. |
| 113 | citace | (ES) č. 1069/2009 Nařízení Evropského parlamentu a Rady (ES) č. 1069/2009 ze dne 21. října 2009 o hygienick… | zamítnout | mimo_rozsah | — | 0.95 | jen doporučení | Nařízení (ES) č. 1069/2009 se týká hygienických pravidel pro vedlejší produkty živočišného původu, což není v souladu s okruhy databáze zaměřenými na vodíkové technologie. Tento dokument se nevztahuje na výrobu, skladování, přepravu nebo využití vodíku, a proto do databáze nepatří. |
| 152 | citace | 2007/30/ES Směrnice Evropského parlamentu a Rady 2007/30/ES ze dne 20. června 2007 , kterou se mění směrnic… | zamítnout | mimo_rozsah | — | 0.90 | jen doporučení | Dokument je směrnicí EU, která se týká bezpečnosti a ochrany zdraví na pracovišti, což je důležité pro provoz zařízení, ale nezmiňuje vodík ani jeho specifické použití. Proto není relevantní pro okruhy databáze, které se zaměřují na vodíkové technologie. |
| 155 | citace | (EU) č. 1093/2010 Nařízení Evropského parlamentu a Rady (EU) č. 1093/2010 ze dne 24. listopadu 2010 o zříze… | zamítnout | mimo_rozsah | — | 0.95 | jen doporučení | Nařízení (EU) č. 1093/2010 se týká zřízení Evropského orgánu dohledu pro bankovnictví, což není v souladu s okruhy databáze zaměřenými na vodíkové technologie. Tento dokument se nevztahuje na výrobu, skladování, přepravu, plnění do vozidel, provoz vozidel, využití vodíku, bezpečnost, stavební řízení, energetiku ani životní prostředí v kontextu vodíkových technologií. |
| 163 | citace | 2014/89/EU Směrnice Evropského parlamentu a Rady 2014/89/EU ze dne 23. července 2014 , kterou se stanoví rá… | zamítnout | mimo_rozsah | — | 0.95 | jen doporučení | Směrnice 2014/89/EU se týká územního plánování námořních prostor, což není přímo spojeno s vodíkovými technologiemi ani s okruhy databáze. I když se v citovaných dokumentech objevuje, její obsah se nevztahuje na regulaci výroby, skladování, přepravy nebo využití vodíku. Proto dokument nepatří do rozsahu databáze. |
| 190 | citace | 35/2021 Sb. Zákon o Sbírce právních předpisů územních samosprávných celků a některých správních úřadů | zamítnout | mimo_rozsah | — | 0.95 | jen doporučení | Zákon o Sbírce právních předpisů územních samosprávných celků a některých správních úřadů se týká organizace a správy právních předpisů, ale nevztahuje se na žádný z okruhů regulace vodíkových technologií. Neobsahuje ani ustanovení, která by se přímo nebo nepřímo dotýkala výroby, skladování, přepravy nebo využití vodíku. |
| 195 | citace | 449/2001 Sb. Zákon o myslivosti | zamítnout | mimo_rozsah | — | 0.95 | jen doporučení | Zákon o myslivosti se týká oblasti myslivosti a ochrany přírody, což není v souladu s okruhy databáze zaměřenými na vodíkové technologie. Tento zákon se nezabývá výrobou, skladováním, přepravou nebo využitím vodíku, a proto do databáze nepatří. |
| 199 | citace | 6/1993 Sb. Zákon o České národní bance | zamítnout | mimo_rozsah | — | 0.95 | jen doporučení | Zákon o České národní bance se týká regulace bankovního sektoru a měnové politiky, což není v souladu s okruhy databáze zaměřenými na vodíkové technologie. Tento zákon se nezabývá výrobou, skladováním, přepravou nebo využitím vodíku, ani obecnými předpisy, které by se na vodík vztahovaly. |
| 215 | citace | 1997/81/ES Směrnice Rady 97/81/ES ze dne 15. prosince 1997 o Rámcové dohodě o částečném pracovním úvazku uz… | zamítnout | mimo_rozsah | — | 0.95 | jen doporučení | Dokument se týká pracovního práva a částečných pracovních úvazků, což není v souladu s okruhy regulace vodíkových technologií. Nezmiňuje se o vodíku ani o žádném z relevantních okruhů databáze. |
| 219 | citace | (ES) č. 2150/2002 Nařízení Evropského parlamentu a Rady (ES) č. 2150/2002 ze dne 25. listopadu 2002 o stati… | zamítnout | mimo_rozsah | — | 0.95 | jen doporučení | Nařízení (ES) č. 2150/2002 se týká statistiky odpadů, což je oblast, která není přímo relevantní pro vodíkové technologie a jejich regulaci. Tento dokument se tedy nevztahuje na žádný z okruhů databáze, které se zaměřují na výrobu, skladování, přepravu a využití vodíku. |
| 229 | citace | (ES) č. 1893/2006 Nařízení Evropského Parlamentu a Rady (ES) č. 1893/2006 ze dne 20. prosince 2006 , kterým… | zamítnout | mimo_rozsah | — | 0.95 | jen doporučení | Nařízení (ES) č. 1893/2006 se týká statistické klasifikace ekonomických činností, což není v souladu s okruhy databáze zaměřenými na vodíkové technologie. Tento dokument se nevztahuje na výrobu, skladování, přepravu nebo využití vodíku, a proto do databáze nepatří. |
| 241 | citace | (EU) č. 996/2010 Nařízení Evropského parlamentu a Rady (EU) č. 996/2010 ze dne 20. října 2010 o šetření a p… | zamítnout | mimo_rozsah | — | 0.95 | jen doporučení | Nařízení (EU) č. 996/2010 se týká civilního letectví a jeho šetření a prevence nehod, což není v souladu s okruhy databáze zaměřenými na vodíkové technologie. Tento dokument se nevztahuje na výrobu, skladování, přepravu nebo využití vodíku, a proto do databáze nepatří. |
| 267 | citace | 2018/1972/EU Směrnice Evropského parlamentu a Rady (EU) 2018/1972 ze dne 11. prosince 2018, kterou se stano… | zamítnout | mimo_rozsah | — | 0.95 | jen doporučení | Dokument je směrnicí EU, která se týká elektronických komunikací, což není přímo spojeno s vodíkovými technologiemi nebo jejich regulací. I když se v citovaných dokumentech objevují odkazy na vodík, směrnice sama o sobě neřeší žádný z relevantních okruhů databáze, jako je výroba, skladování nebo přeprava vodíku. |
| 282 | citace | (EU) 2021/523 Nařízení Evropského parlamentu a Rady (EU) 2021/523 ze dne 24. března 2021, kterým se zavádí … | zamítnout | mimo_rozsah | — | 0.95 | jen doporučení | Nařízení (EU) 2021/523 se týká zavedení programu InvestEU, což není přímo spojeno s regulací vodíkových technologií nebo jejich životním cyklem. Tento dokument neobsahuje žádné ustanovení, které by se vztahovalo na okruhy databáze, jako je výroba, skladování nebo využití vodíku. Proto dokument nepatří do rozsahu databáze. |
| 351 | e-Sbírka | 1/1925 Sb. Vyhláška, kterou se uvádí v prozatímní platnost dodatková úmluva k obchodní dohodě mezi ČSR a re… | zamítnout | zastaraly | — | 0.95 | jen doporučení | Dokument je vyhláškou z doby před rokem 1990, která se týká obchodních dohod a celních tarifů, což není relevantní pro okruhy databáze zaměřené na vodíkové technologie. Takové předpisy jsou považovány za historické a nemají význam pro současnou praxi. |
| 354 | e-Sbírka | 105/1933 Sb. Vyhláška o počátku platnosti nové přílohy I k Mezinárodní úmluvě o přepravě zboží po železnicí… | zamítnout | zastaraly | — | 0.95 | jen doporučení | Dokument je vyhláškou z roku 1933, což je předpis z doby před rokem 1990, a tudíž je považován za historický a neúčinný. Neobsahuje relevantní informace pro současnou praxi v oblasti vodíkových technologií. Proto je třeba jej odmítnout. |
| 355 | e-Sbírka | 110/1933 Sb. Vládní vyhláška, kterou se uvádí v prozatímní platnost dodatková dohoda k obchodní úmluvě mezi… | zamítnout | zastaraly | — | 0.95 | jen doporučení | Dokument je vyhláškou z doby před rokem 1990, která se týká obchodní úmluvy a neobsahuje žádné relevantní ustanovení pro vodíkové technologie. Takové předpisy jsou považovány za historické a nemají význam pro současnou praxi. |
| 392 | e-Sbírka | 349/2004 Sb. Úplné znění zákona č. 353/1999 Sb., o prevenci závažných havárií způsobených vybranými nebezpe… | zamítnout | zastaraly | — | 0.95 | jen doporučení | Dokument je označen jako "Úplné znění zákona", což znamená, že se jedná o historický nebo neúčinný předpis bez významu pro dnešní praxi. Tento typ dokumentu do databáze nepatří, protože se nejedná o aktuální regulační předpis. |
| 420 | e-Sbírka | 81/1951 Sb. Nařízení ministra dopravy, kterým se vyhlašuje Dohoda o přepravě cestujících a cestovních zavaz… | zamítnout | zastaraly | — | 0.95 | jen doporučení | Dokument je nařízení z doby před rokem 1990, což jej činí historickým a bez významu pro současnou praxi. Takové předpisy jsou považovány za zastaralé a do databáze nepatří. |
| 422 | e-Sbírka | 84/1992 Sb. Vyhláška federálního ministerstva dopravy, kterou se mění a doplňuje vyhláška federálního minis… | zamítnout | mimo_rozsah | — | 0.90 | jen doporučení | Vyhláška se týká dopravy, ale nezmiňuje vodík ani žádné okruhy databáze, jako jsou tlaková zařízení nebo přeprava nebezpečných věcí. Proto není relevantní pro regulaci vodíkových technologií. Dokument je tedy mimo rozsah databáze. |
| 424 | e-Sbírka | 90/1969 Sb. Dlouhodobá obchodní dohoda mezi Československou socialistickou republikou a Hospodářskou unií B… | zamítnout | zastaraly | — | 0.95 | jen doporučení | Dokument je obchodní dohodou z doby před rokem 1990, což jej činí historickým a bez významu pro současnou praxi. Takové předpisy jsou považovány za zastaralé a nepatří do databáze regulačních předpisů k vodíkovým technologiím. Proto je třeba jej odmítnout. |
| 456 | Sněmovna | Vládní návrh zákona, kterým se mění zákon č. 262/2006 Sb., zákoník práce, ve znění pozdějších předpisů, a n… | zamítnout | mimo_rozsah | — | 0.95 | jen doporučení | Dokument je vládní návrh zákona, který se týká změn v zákoníku práce a dalších zákonech, avšak nezmiňuje se o vodíkových technologiích ani o okruzích databáze. Proto do databáze nepatří, jelikož se nevztahuje na regulaci vodíku nebo souvisejících oblastí. |

### 5.1 Kritický posudek

Ze 40 kandidátů pokládáme rozhodnutí modelu u 33 za správné, u 5 za hraniční
(odpověď závisí na tom, jak úzce vykládáme rozsah databáze) a u 2 za chybné:

1. **Chybná doporučení přijetí:** směrnice 86/278/EHS o kalech z čistíren
   odpadních vod (#207) a vyhláška č. 470/2012 Sb. o mýtném (#409). Model
   v obou případech nalezl spojitost s okruhem (životní prostředí, provoz
   vozidel) a přehlédl, že jde o věcně vzdálenou oblast, resp. o poplatek,
   který pokyny výslovně vyřazují. Obě doporučení mají jistotu 0,9, takže by
   s prahem 0,95 automat nic nenavrhl; s prahem 0,9 by je navrhl.
2. **Hraniční případy:** směrnice 92/43/EHS o stanovištích (Natura 2000 se
   uplatní při povolování záměru), rozhodnutí 2010/713/EU o modulech
   posuzování shody pro interoperabilitu železnic, směrnice 2014/30/EU
   o elektromagnetické kompatibilitě, nařízení (EU) 2019/1020 o dozoru nad trhem
   a opatření ČMI o vibračních převodnících hustoty plynů. Model je doporučil
   přijmout s jistotou 0,7 až 0,9, automat je tedy jen ukáže editorům.
   Rozhodnutí, zda obecné předpisy o posuzování shody a dozoru nad trhem do
   databáze patří, přísluší uživateli (odstavec 8).
3. **Zkrácené názvy** (například #422, „Vyhláška federálního ministerstva
   dopravy, kterou se mění a doplňuje vyhláška federálního ministerst...“)
   dávají modelu málo podkladů; model pak rozhoduje podle úryvku. Zde zamítnutí
   pravděpodobně správné je (stará novela předpisu o přepravě nebezpečných
   věcí), jistotu však model nadhodnocuje.
4. **Kategorie bývá nepřesná**, doporučení přitom správné: nařízení
   (EU) č. 651/2014 o blokových výjimkách pro veřejnou podporu model zamítl jako
   `mimo_rozsah`, ne jako `dane_dotace`. Pro automatické zamítnutí to nevadí,
   pokud budou odsouhlaseny obě kategorie.
5. **Jistota rozlišuje slabě.** Model uvádí převážně 0,9 nebo 0,95; změřená
   pravděpodobnost doporučení je téměř vždy 1,0 (odstavec 3.2). Prah proto
   odděluje jasné případy od hraničních jen zčásti a návrhy automatu je nutné
   před potvrzením zkontrolovat, nikoli potvrzovat naslepo.

### 5.2 Úprava pokynů po prvním běhu

V prvním běhu (pokyny bez seznamu hraničních případů a bez složení databáze)
model zamítl normy SAE J3219 a J2719/1 jako „zahraniční předpis“ a úplné znění
zákona o prevenci závažných havárií jako věcně nesouvisející; jistotu uváděl
u všech 40 kandidátů 0,9. Doplnili jsme do pokynů složení databáze (typy
a nejčastější původci), výslovné poučení, že normy cizích organizací do
databáze patří, výčet oblastí mimo rozsah a pořadí „nejdřív zdůvodnění,
pak rozhodnutí“. Ve druhém běhu model normy SAE doporučil přijmout a úplné
znění správně zařadil jako zastaralé.

### 5.3 Cena ukázky

Oba běhy ukázky (2 × 40 volání) stály podle spotřeby vrácené rozhraním
**0,049 USD** (443 tisíc vstupních tokenů, z toho 74 % z mezipaměti
poskytovatele, a 12 tisíc výstupních tokenů); jedno posouzení vychází na
přibližně 0,0006 USD.

## 6. Odhad pro celou frontu

Celý běh pravidel (ve znění podle úprav uživatele) a modelu jsme vyzkoušeli s `--apply` nad testovací
databází `h2regdocs_test`, obnovenou kopií živé databáze, pod zámkem testů.
Výsledek pro 591 nových kandidátů:

| Cesta | Kandidátů | Akce |
|---|---|---|
| R4-tpg, R5-mpo, R6-navrh-vodik, R8-zruseny | 126 | návrh přijetí podle pravidel (69 TPG, 53 MPO, 3 návrhy, 1 zrušený předpis) |
| R3-novinka | 6 | odložení |
| model, přijmout s jistotou ≥ 0,95 | 137 | návrh přijetí |
| model, zamítnout s jistotou ≥ 0,95 v kategoriích navržených k odsouhlasení | 169 | po odsouhlasení zamítnutí (`mimo_rozsah` 147, `zastaraly` 18, `dane_dotace` 4), do té doby jen doporučení |
| model, ostatní (přijmout 91, zamítnout 62, odložit 1 s jistotou pod 0,95) | 153 | jen doporučení editorům |

Automaticky by tedy šlo vyřídit (navrhnout k potvrzení, zamítnout nebo
odložit) **438 kandidátů** (74 %) a na samostatné posouzení lidmi by zůstalo
**153** (26 %). I návrhy přijetí (263) však vyžadují potvrzení editorem;
hromadné potvrzení je zrychlí, nikoli nahradí.

**Kvalita.** Při procházení 137 návrhů přijetí podle modelu jsme odhadem
u 20 až 25 z nich (15 až 18 %) narazili na dokumenty, jež do databáze patrně
nepatří, převážně fondy a podpůrné programy (nařízení o Nástroji pro
oživení a odolnost, o Fondu pro spravedlivou transformaci, zákon o Státním
fondu dopravní infrastruktury), zadávání zakázek (směrnice 2014/25/EU),
organizační zákony (zákon o hlavním městě Praze) a definici malých a středních
podniků. Model u nich dobře rozpozná okruh, podle něhož se o dokumentu
v databázi mluví, ale nerozliší, že dokument sám nic technicky nereguluje.
Mezi 169 navrženými zamítnutími jsme chyby téměř nenašli; hraniční jsou
směrnice NIS 2 (kritická infrastruktura energetiky), katalog odpadů
(vyhláška č. 8/2021 Sb.) a vyhláška ČBÚ č. 22/1989 Sb. o bezpečnosti práce
v hornictví, kterou model považoval za zastaralou.

**Cena.** Celý běh 459 posouzení stál **0,30 USD** (2,67 milionu vstupních
tokenů, z toho 72 % z mezipaměti poskytovatele, 79 tisíc výstupních);
odhad skriptu před během byl 0,44 USD. Celkem jsme 20. 11. 2026 za ukázku
a zkoušku utratili přibližně 0,35 USD. Odpovědi jsou v mezipaměti
`data/triage_model_cache.json`; protože testovací databáze byla kopií živé,
ostrý běh nad živou databází bude pro dnešní frontu zdarma (ověřili jsme,
že všech 459 kandidátů živé fronty, o nichž rozhoduje model, má odpověď
v mezipaměti); platit se bude jen za kandidáty, kteří mezitím přibudou
nebo se změní. Další běhy (desítky nových
kandidátů týdně) budou stát řádově setiny dolaru.

## 7. Postup ostrého běhu

Po odsouhlasení pravidel (odstavec 2) a sloučení větve do `master`:

1. Do `data/triage_rules.json` zapsat `approval.approved_by` a `approval.date`
   a přesunout odsouhlasené kategorie do `model.auto_categories`.
2. V hlavním stromu (web se po `git pull` nasadí; nové sloupce tabulky
   `DocumentCandidate` vzniknou až prvním během s `--apply`, do té doby
   rozhraní filtry doporučení nenabízí):

```
cd /home/laborator/DEVEL/nahyc-h2db
.venv/bin/python src/tools/triage_candidates.py --rules-only            # suchý běh pravidel
.venv/bin/python src/tools/triage_candidates.py                         # suchý běh s modelem (z mezipaměti)
.venv/bin/python src/tools/backup_db.py --reason before_triage
.venv/bin/python src/tools/triage_candidates.py --apply                 # ostrý běh
```

3. Editoři projdou filtr „návrhy automatu k potvrzení“ a potvrdí, vrátí či
   zamítnou návrhy; filtr „zamítnuté či odložené automatem“ slouží ke kontrole
   rozhodnutí automatu.
4. Další běhy: po každém sběru zdrojů a importu kandidátů
   (`doc/PROVOZ.md`, příloha A.4).

Ostrý běh nad databází, jejíž název nekončí `_test`, skript bez vyplněného
`approval` odmítne. Volbou `--model` lze zvolit jiný model; ten se spustí,
jen má-li v souboru pravidel ceník a vejde-li se odhad do `budget_usd`
(jinak `--max-usd`).

## 8. Otevřené otázky

1. **Odsouhlasení pravidel a kategorií** (odstavec 2): dokud nejsou
   odsouhlasena, nic se v živé databázi nezmění.
2. **Obecné předpisy o výrobcích**: patří do databáze předpisy o posuzování
   shody, dozoru nad trhem, normalizaci (nařízení (EU) č. 1025/2012),
   elektromagnetické kompatibilitě a strojních zařízeních? Model je zčásti
   doporučuje přijmout; rozhodnutí by sjednotilo posuzování.
3. **Fondy, podpůrné programy a zadávání zakázek**: navrhujeme je
   v pokynech modelu výslovně zařadit do kategorie `dane_dotace` (verze
   pokynů 3); tím by z návrhů přijetí ubylo odhadem 10 až 15 chybných.
4. **Model `gpt-6.2-astra`**: je dostupný, ale jeho ceník neznáme. Doplní-li
   uživatel cenu za milion vstupních a výstupních tokenů, lze jej vyzkoušet
   na stejném vzorku (`--model gpt-6.2-astra --rule R9-model --sample 40`)
   a porovnat přesnost; s `gpt-4o-mini` zůstává na účtu podle odhadu přes
   5,6 USD.
5. **Technická pravidla TPG v pásmu 2**: pravidlo R4 navrhne všech 69 pravidel
   podle rozhodnutí uživatele, i ta bez přímého vztahu k vodíku (například
   kurzy svařování plastů). Editoři je mohou při potvrzování vynechat.
