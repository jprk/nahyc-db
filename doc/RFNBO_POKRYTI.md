# Pokrytí tématu RFNBO v databázi h2db

Stav k 22.11.2026, živá databáze `h2regdocs` (jen čtení: 1506 dokumentů, 592 kandidátů ve frontě).
RFNBO = obnovitelná paliva nebiologického původu (renewable fuels of non-biological origin), tj. především
obnovitelný vodík a paliva z něj. Úrovně priority A/B/C podle `doc/DATABASE_SCOPE.md` odstavec 2.

## 1. Co databáze obsahuje

* **Web** `https://nahyc.fd.cvut.cz/h2db/?q=RFNBO` vrací 7 záznamů: RED II 2018/2001 (#106, EN #1470),
  RED III 2023/2413 (#83, EN #1479), 2023/1184 (#76), 2023/1185 (#77), NECP ČR 2024 (#1546),
  COM(2021) 550 (#1551), COM(2026) 370 (#1555).
* **Další RFNBO dokumenty v DB, které hledání „RFNBO“ nenajde** (zkratka není v názvu ani popisu):
  ReFuelEU Aviation 2023/2405 (#82), AFIR 2023/1804 (#81, #1478), plynárenská směrnice 2024/1788
  (#104, #1480, SK #84), plynárenské nařízení 2024/1789 (#105, #1481), směrnice 2009/30/ES (#1415),
  COM(2020) 301 Vodíková strategie (#79, SK #78), zákony 165/2012 (#66), 201/2012 (#53), 311/2006 (#1212),
  458/2000 (#72). Všechny mají aktuální verzi ve stavu `active`.
* **Fronta kandidátů** (stav: 140 new, 243 proposed, 163 rejected, 46 deferred) — RFNBO relevantní:
  #87 2022/996 (proposed), #88 FuelEU Maritime 2023/1805 (proposed), #329 2025/2359 (proposed),
  #5 EU ETS 2003/87 (proposed), #177 2023/959 (proposed), #52 zdanění energie 2003/96 (new),
  #587 Have your say 19592 „Revision of the production criteria for RFNBO“ (new, doporučení accept),
  #592 delegovaná směrnice s výchozími hodnotami GHG (proposed), #467 změna 2018/2001, 2019/944, 2024/1788
  (new, defer), **#184 NV 189/2018 Sb. o kritériích udržitelnosti (new, automat doporučuje reject)**.

## 2. Referenční seznam a porovnání

Existence a čísla EU aktů ověřeny v Cellaru (SPARQL nad názvy obsahujícími „non-biological origin“,
„low-carbon fuels“, „renewable hydrogen“ a nad čísly aktů). České předpisy jsou ověřené jen proti
plným textům v DB (zakonyprolidi.cz vrací ochranu Cloudflare); transpozici RED III do českého práva je
nutné ověřit v e-Sbírce.

| Referenční položka | Prior. | V DB | Ve frontě | Výsledek |
|---|---|---|---|---|
| RED II 2018/2001 | A | #106, #1470 | — | ok |
| RED III 2023/2413 | A | #83, #1479 | — | ok |
| DA 2023/1184 (aditionalita, výroba RFNBO) | A | #76 | — | ok (chybí EN, konsolidované znění 02023R1184-20240610) |
| DA 2023/1185 (metodika GHG, práh 70 %) | A | #77 | — | ok |
| IR 2022/996 (ověřování, certifikace) | A | — | #87 proposed | **chybí, čeká na potvrzení** |
| ReFuelEU Aviation 2023/2405 | A | #82 | — | ok |
| FuelEU Maritime 2023/1805 | A | — | #88 proposed | **chybí, čeká na potvrzení** |
| Směrnice 2024/1788 (vodík a plyn) | A | #104, #1480, #84 | — | ok |
| Nařízení 2024/1789 | A | #105, #1481 | — | ok |
| AFIR 2023/1804 | A | #81, #1478 | — | ok |
| DA 2025/2359 (nízkouhlíkový vodík, podle 2024/1788) | A | — | #329 proposed | **chybí, čeká na potvrzení** |
| Pokyny Komise k cílům RFNBO v průmyslu a dopravě, CELEX 52025XC02983 | A | — | — | **chybí** |
| EU ETS 2003/87/ES | B | — | #5 proposed | chybí (citován 18 dokumenty DB) |
| Novela ETS 2023/959 | B | — | #177 proposed | chybí |
| Governance 2018/1999 | B | #1442 | — | ok |
| Uznání dobrovolných schémat pro RFNBO: 2024/3176 (ISCC EU), 2024/3180 (CertifHy), 2024/3194 (REDcert-EU), 2026/2316 (RSB EU RED) | B | — | — | **chybí** |
| Základní uznání schémat 2022/599–2022/611, 2022/1656, 2022/1657, 2022/2461 (biopaliva, RFNBO jen okrajově) | C | — | — | chybí |
| Prováděcí akty FuelEU 2024/2027, 2024/2031, DA 2025/192 | C | — | — | chybí |
| Zdanění energie 2003/96/ES | B | — | #52 new | chybí |
| Směrnice FQD 98/70/ES | B | — | — | chybí (citována 31 dokumenty DB) |
| Směrnice 2015/652 (výpočet GHG paliv) | C | — | — | chybí (16 citací) |
| Have your say 19592 — revize kritérií výroby RFNBO (návrh) | A (návrh) | — | #587 new | chybí, neposouzeno |
| Delegovaná směrnice s výchozími hodnotami GHG (regdel 1054) | B (návrh) | — | #592 proposed | chybí |
| Zvláštní zpráva EÚD 11/2024 o obnovitelném vodíku | C | — | — | chybí (není předpis) |
| Zákon 165/2012 Sb. (podporované zdroje) | A | #66 | #398 | ok |
| Zákon 201/2012 Sb. (ochrana ovzduší, povinnost RFNBO v dopravě) | A | #53 | — | ok |
| Zákon 311/2006 Sb. (pohonné hmoty) | A | #1212 | — | ok |
| Zákon 458/2000 Sb. (energetický) | A | #72 | — | ok |
| NV 189/2018 Sb. (kritéria udržitelnosti, snižování emisí z PHM) | A | — | #184 new, automat: reject | **chybí; doporučení automatu je chybné** |
| Česká transpozice RED III (novely 201/2012, 165/2012, LEX OZE) | A | částečně (konsolidovaná znění) | — | ověřit v e-Sbírce |
| NECP ČR 2024, Vodíková strategie ČR | strategie | #1546; strategie ČR viz `MPO_VYPORADANI.md` příloha A | — | ok / mimo tento audit |

Pozn.: 2009/30/ES (#1415) je v DB; seznam ze zadání uváděl „zákon 382/2024 Sb.“ — v DB ani frontě
není a jeho souvislost s RFNBO se nepodařilo ověřit, do referenčního seznamu nezařazen.

**Citační uzávěr** (`citation_closure.closure()` v paměti, bez zápisu souborů): 2022/996 cituje
5 dokumentů DB (mj. #53, #66, #82, #83, #104); 2025/2359 cituje #1249; 2023/1185 citují #53 a #66
(česká transpozice); 2023/1184 cituje #1241. Mezi chybějícími akty citovanými RFNBO dokumenty
(#76, #77, #81–#83, #104–#106 a EN varianty) vedou 98/70/ES (31), 2003/87/ES (18), 2015/652 (16) a
2023/1805 (6).

## 3. Souhrn

* Priorita A: 21 položek, 14 v DB, 4 ve frontě (2022/996, 2023/1805, 2025/2359, #587 návrh),
  1 ve frontě s chybným doporučením zamítnutí (NV 189/2018), 1 úplně chybí (pokyny 52025XC02983),
  1 k ověření (česká transpozice RED III).
* Priorita B: 10 položek, 1 v DB, 5 ve frontě, chybí uznávací rozhodnutí pro RFNBO a FQD 98/70/ES.
* Hledání: dotaz „RFNBO“ najde 7 záznamů z ~20 relevantních; chybí synonymum
  (RFNBO ↔ „nebiologického původu“ ↔ „non-biological origin“) a vyhledávání v plném textu.

## 4. Opakovatelná kontrola

1. **Tematický golden set** `data/golden/rfnbo.json` (seznam CELEX / značek s prioritou) a test
   `tests/test_golden_rfnbo.py` po vzoru tabulek MPO: pro každou položku A selže, není-li v `Document`
   ani ve frontě ve stavu `new/proposed/deferred`; položky B hlásí jen varováním.
2. **Uložený dotaz do Cellaru** (spouštět měsíčně, výsledky porovnat s DB a frontou):
   ```sparql
   PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
   SELECT DISTINCT ?celex ?date ?title WHERE {
     ?w cdm:resource_legal_id_celex ?celex ; cdm:work_date_document ?date .
     ?e cdm:expression_belongs_to_work ?w ; cdm:expression_title ?title ;
        cdm:expression_uses_language <http://publications.europa.eu/resource/authority/language/ENG> .
     FILTER(CONTAINS(LCASE(STR(?title)),"non-biological origin") || CONTAINS(LCASE(STR(?title)),"low-carbon hydrogen")
            || CONTAINS(LCASE(STR(?title)),"renewable hydrogen") || CONTAINS(LCASE(STR(?title)),"low-carbon fuels"))
     FILTER(?date >= "2018-01-01"^^<http://www.w3.org/2001/XMLSchema#date>)
   }
   ```
   Doplnit filtrem podle EuroVoc (deskriptory „hydrogen“, „renewable energy“, „alternative fuel“)
   a dotazem na akty, které mění nebo provádějí 2018/2001, 2024/1788 a 2023/1184/1185 (`cdm:resource_legal_amends_resource_legal`, `based_on`).
3. **Citační uzávěr omezený na téma**: filtr řádků `closure()` podle `citing_ids` ∩ RFNBO dokumenty.
4. **Česká strana**: e-Sbírka, fulltext „nebiologického původu“ v platných předpisech; VeKLEP pro návrhy.
5. **Have your say**: sledovat iniciativy s „non-biological origin“ / „hydrogen“ (už dělá agentní pipeline, #587).

## 5. Návrh doplnění (nespouštěno)

* Potvrdit ve frontě #87, #88, #329 (druhý editor, `/admin/candidates`); #184 vrátit z doporučení reject
  a přijmout; rozhodnout #587, #592, #5, #177, #52.
* Vložit do fronty chybějící položky ručním návrhem (stránka `/admin/candidates`, „ruční návrh“), nebo
  přes `import_candidates.py` z JSON připraveného z výsledku dotazu v odstavci 4.2, nejprve nad
  `h2regdocs_test`:
  `.venv/bin/python src/tools/import_candidates.py --env-file .env.test <rfnbo_candidates.json>`
  (ověřit přesné parametry skriptu před během), položky: 52025XC02983, 32024D3176, 32024D3180,
  32024D3194, 32026D2316, 31998L0070.
* Vyhledávání: přidat synonyma RFNBO do hledání nebo zkratku do `popis_priblizny` dotčených dokumentů.
