# Oblasti katalogu

Stav k 22.11.2026. 
Filtr „Oblast“ v katalogu a štítky u dokumentů v seznamu a na stránce dokumentu
nově ukazují **oblasti**: 29 českých hodnot (27 věcných, strategie a náhradní) 
navázaných na věcné okruhy `doc/DATABASE_SCOPE.md`b(tento dokument, odstavec 3).
Dosud v nich byla klíčová slova převzatá ze zdrojových rešerší, která nedávala
moc smysl.

## 1. Proč

Pole „Oblast (klíčové slovo)“ mělo v živé databázi k 21.11.2026 celkem 238 hodnot
(3294 vazeb, 343 dokumentů bez hodnoty):

* **jazyky:** většina hodnot je německá (převzatá z podkladů prof. Sinaye: „Explosionsschutz“ 
  247 dokumentů, „Schienenfahrzeuge“ 169, „Produktzertifizierung“ 124 …), část slovenská 
  („STN (prijatá v sústave)“ 375, „Stav k 02/2025: v príprave“ 34) a anglická („Controls“);
* **nejde o oblasti:** jsou tam vydavatelé („DIN - Deutsches Institut für Normung e.V.“, „ASTM …“, „EIGA …“,
  přes 40 hodnot), technické komise („Norm (ISO/TC 58/SC 3/WG 27)“, přes 100 hodnot, většinou s 1–5
  dokumenty), stavy normy („STN (zrušená bez náhrady)“), obecné hodnoty („EU“, „Norm“, „-“, „Information“);
* **duplicity a překlepy:** „Norm (IEC/TC 31)“ / „Norm (IEC/TC31)“, „Norm (ISO TC58 SC3)“ / „Norm (ISO/TC 58/SC 3)“,
  „DIN - Deutsches“ / „DIN - Deutsches Institut …“, „NACE - National“ / „NACE - National Association …“,
  „Palivové články“ / „3360 - Technologie palivových článků“ / „Brennstoffzelle“;
* **příliš podrobné:** třídy ČSN („4202 - Ingoty z ocelí. Tvářené výrobky z ocelí …“),
  pracovní skupiny komisí.

## 2. Nová sada oblastí

Počty z běhu nanečistu skriptu `assign_areas.py` nad živou databází (1506 dokumentů; dokument 
může mít více oblastí). „Před“ je původní verze pravidel (21.11.2026, odpoledne), „po“ verze
zpřesněná 22.11.2026 (viz odstavec 3 v tomto dokumentu): oblasti se už neodvozují z kategorií
zdrojových tabulek, rozhoduje název dokumentu \[DOPLNIT: Nerozhoduje jenom název, relevantní 
pro danou oblast může být i obsah dokumentu.\]

| Oblast | Okruh | Před | Po |
|---|---|---|---|
| Výroba vodíku | 1 | 80 | 21 |
| Obnovitelný a nízkouhlíkový vodík, certifikace | 1 | 30 | 19 |
| Tlakové nádoby a lahve | 2 | 186 | 164 |
| Zkapalněný vodík a kryogenní technika | 2 | 172 | 102 |
| Podzemní zásobníky | 2 | 114 | 13 |
| Plynovody a plynárenské sítě | 3 | 179 | 129 |
| Přeprava nebezpečných věcí | 3 | 17 | 33 |
| Plnicí stanice a infrastruktura paliv | 4 | 94 | 70 |
| Kvalita vodíku, měření a metrologie | 4 | 153 | 133 |
| Silniční a speciální vozidla | 5 | 256 | 134 |
| Železnice a kolejová vozidla | 5 | 220 | 48 |
| Lodní a letecká doprava | 5 | 55 | 39 |
| Palivové články | 6 | 75 | 64 |
| Průmyslové využití a Power-to-X | 6 | 130 | 66 |
| Elektrárny, turbíny a tepelná zařízení | 6 | 73 | 69 |
| Plynové spotřebiče v domácnostech a provozovnách | 6 | 48 | 33 |
| Ochrana před výbuchem | 7 | 273 | 69 |
| Bezpečnost a prevence havárií | 7 | 240 | 56 |
| Chemické látky a směsi | 7 | 22 | 18 |
| BOZP a odborná způsobilost | 7 | 73 | 62 |
| Materiály a jejich zkoušení | 7 | 317 | 239 |
| Komponenty, armatury a potrubí | 7 | 281 | 239 |
| Řídicí systémy a kybernetická bezpečnost | 7 | 94 | 69 |
| Posuzování shody a certifikace výrobků | 7 | 134 | 14 |
| Stavby, územní plánování a umístění | 8 | 17 | 19 |
| Energetika a trh s plynem a vodíkem | 9 | 76 | 62 |
| Životní prostředí, emise a klima | 10 | 139 | 105 |
| Strategie, koncepce a studie | — | 38 | 38 |
| Obecné a průřezové předpisy | — | 40 | 70 |
| **Oblastí na dokument (průměr)** | | 2.41 | 1.46 |

Rozpad podle původu (po): jen z názvu 1161 dokumentů, jen z klíčových slov 106, z obojího 157, z typu 12,
náhradní oblast 70.

### 2.1 Příklady (5 náhodně vybraných názvů z každé oblasti)

* **Výroba vodíku**: EIGA DOC 246 — DOC 246 / 23 - Guideline for Small Scale Hydrogen Production; ISO 16110-1 — Hydrogen generators using fuel processing technologies - Part 1: Safety; VDI 4635 Blatt 3.1 — Power-to-X; Hydrogen production through water electrolysis; ISO 22734:2019 — Hydrogen generators using water electrolysis — Industrial, commercial, an; DIN EN ISO 22734 — DIN EN ISO 22734
* **Obnovitelný a nízkouhlíkový vodík, certifikace**: (EU) 2018/2001 - DIRECTIVE (EU) 2018/2001 OF THE EUROPEAN PARLIAMENT AND OF THE COUNCIL of; Nařízení Komise v přenesené pravomoci (EU) 2023/1185 ze dne 10. února 2023, kterým se dopl; DIN EN 16325 — Guarantees of Origin related to energy - Guarantees of Origin for Electrici; Zákon, ktorým sa mení a dopĺňa zákon č. 98/2004 Z. z. o spotrebnej dani z minerálneho olej; Recommendations of HYTEP on the Delegated Act specifying a methodology for assessing GHG e
* **Tlakové nádoby a lahve**: STN EN 13160-5 — Systémy zisťovania netesností. Časť 5: Požiadavky a skúšobné metódy/metód; STN EN 720-1 — Fľaše na prepravu plynov. Plyny a zmesi plynov. Časť 1: Vlastnosti čistých ; STN EN ISO 11114-4 — Prepravné fľaše na plyny. Kompatibilita fľašových a ventilových mater; STN EN 13096 — Fľaše na prepravu plynov. Podmienky plnenia plynov do nádob. Jednozložkové ; AS B12 — Cylinders for the storage and transport of anhydrous ammonia, chlorine and sulphu
* **Zkapalněný vodík a kryogenní technika**: ASTM C1774-13 — Standard Guide for Thermal Performance Testing of Cryogenic Insulation Sys; STN EN 1626 — Kryogénne nádoby. Ventily na kryogénnu prevádzku; ISO 24132 — Ships and marine technology — Design and testing of marine transfer arms for l; STN EN ISO 20088-1 — Určenie odolnosti izolačných materiálov proti kryogénnemu prenikaniu.; DIN EN ISO 21009-2 — Cryogenic vessels - Static vacuum-insulated vessels - Part 2: Operati
* **Podzemní zásobníky**: API SPEC 11D1 — Packers and Bridge Plugs; STN EN 1918-1 — Plynárenská infraštruktúra. Podzemné zásobníky plynu. Časť 1: Funkčné poži; BVEG Leitfaden Auswirkungen von Störfällen im Speicherbetrieb; STN EN 1918-2 — Plynárenská infraštruktúra. Podzemné zásobníky plynu. Časť 2: Funkčné poži; STN EN 1918-4 — Plynárenská infraštruktúra. Podzemné zásobníky plynu. Časť 4: Funkčné poži
* **Plynovody a plynárenské sítě**: STN EN 15001-1 — Plynárenská infraštruktúra. Plynovody s prevádzkovým tlakom väčším ako 0,; G 655 (M) — Guideline H2-Readiness Gas Utilisation; STN EN 12327 — Plynárenská infraštruktúra. Tlakové skúšky, uvedenie do prevádzky a odstave; EIGA IGC Doc 121/14 (2014) — Hydrogen Pipeline System; STN EN 12279 — Systémy zásobovania plynom. Regulačné zariadenia na prípojkách. Požiadavky 
* **Přeprava nebezpečných věcí**: STN EN 1089-3 — Prepravné fľaše na plyny. Označovanie fliaš (okrem LPG). Časť 3: Farebné o; STN EN ISO 11114-1/Zmena — Prepravné fľaše na plyny. Kompatibilita fľašových a ventilových; IGC Doc 77/01/E — Protection of cryogenic transportable tanks against excessive pressure d; STN EN 13322-1 — Prepravné fľaše na plyny. Navrhovanie a výroba znovuplniteľných oceľových; STN EN ISO 11114-4 — Prepravné fľaše na plyny. Kompatibilita fľašových a ventilových mater
* **Plnicí stanice a infrastruktura paliv**: SAE J2601 — Fueling Protocols for Light Duty Gaseous Hydrogen Surface Vehicles; ISO/AWI 19885-3 — Gaseous hydrogen — Fuelling protocols for hydrogen-fuelled vehicles — Pa; ISO 13984 — Liquid hydrogen — Land vehicle fuelling system interface; ISO/DIS 13984 — Liquid hydrogen — Land vehicle fueling protocol; TRGS 751 — Vermeidung von Brand-, Explosions- und Druckgefährdungen an Tankstellen und Gas
* **Kvalita vodíku, měření a metrologie**: STN EN ISO 6145-6 — Analýza plynov. Príprava kalibračných plynných zmesí dynamickými objem; STN EN ISO 6142-1 — Analýza plynov. Príprava kalibračných plynných zmesí. Časť 1: Gravimet; STN EN ISO 16664 — Analýza plynov. Manipulácia s kalibračnými plynmi a plynnými zmesami. P; DIN 50450-2 — Testing of materials for semiconductor technology; determination of impuriti; Směrnice Evropského parlamentu a Rady 2003/30/ES ze dne 8. května 2003 o podpoře užívání b
* **Silniční a speciální vozidla**: Nařízení Komise v Přenesené Pravomoci (EU) 2019/1745 ze dne 13. srpna 2019, kterým se dopl; SAE J3089 — Characterization of On-Board Vehicular Hydrogen Sensors; Studie – Využití vodíkového pohonu v dopravě v České republice (2017); 205/2025 Sb. Vyhláška, kterou se mění vyhláška č. 294/2015 Sb., kterou se provádějí pravid; ISO/TR 11954 (2008) — Fuel cell road vehicles - Maximum speed measurement
* **Železnice a kolejová vozidla**: 173/1995 Sb. Vyhláška, kterou se vydává dopravní řád drah; EN 50128 — Railway applications - Communications, signalling and processing systems - Soft; Nařízení Komise (EU) č. 1305/2014 ze dne 11. prosince 2014 o technické specifikaci pro int; (EU) 2019/250 - COMMISSION IMPLEMENTING REGULATION of 12 February 2019 on the templates fo; Nařízení Komise (EU) č. 1302/2014 ze dne 18. listopadu 2014 o technické specifikaci pro in
* **Lodní a letecká doprava**: Směrnice Evropského parlamentu a Rady 2009/30/ES ze dne 23. dubna 2009 , kterou se mění sm; MSC.1/Circ.1647 — Interim guidelines for the safety of ships using fuel cell power install; Směrnice Rady 1999/63/ES ze dne 21. června 1999 o dohodě o úpravě pracovní doby námořníků ; ISO 16904 — 2016 - Petroleum and natural gas industries — Design and testing of LNG marine; ISO/AWI 18735 — Ship and marine technology — Hi-manganese austenitic steel — Specification
* **Palivové články**: ISO 14687-1 — Hydrogen fuel - Product specification - Part 1: All applications except prot; SAE J2760 — Pressure Terminology Used in Fuel Cells and Other Hydrogen Vehicle Application; STN EN 62282-3-201 — Technológia palivových článkov. Časť 3-201: Malé stacionárne výkonové; STN EN IEC 62282-3-100 — Technológia palivových článkov. Časť 3-100: Stacionárne výkonové ; DIN EN IEC 63341-2 (VDE 0115-341-2) — Railway applications - Rolling stock - Fuel cell sys
* **Průmyslové využití a Power-to-X**: AS 1678.8.0.010 — Emergency procedure guide - Transport - Ammonia solution (ammonium hydro; UL Standard (UL 565, Edition 6) — Standard for Liquid-Level Gauges for Anhydrous Ammonia a; VDI 4635 Blatt 3.1 — Power-to-X; Hydrogen production through water electrolysis; ISO 7105 — Liquefied anhydrous ammonia for industrial use -- Determination of water conten; VDI 4635 Blatt 3.3 — Power-to-X; Methanation; System parameters and measurands
* **Elektrárny, turbíny a tepelná zařízení**: STN EN 12953-13 — Veľkopriestorové vodné kotly. Časť 13: Prevádzkové pokyny; STN EN 12953-5 — Veľkopriestorové vodné kotly. Časť 5: Kontrola počas výroby, dokumentácia; ISO 23551-10 — Safety and control devices for gas burners and gas-burning appliances - Par; ISO 23551-4 — Safety and control devices for gas burners and gas-burning appliances - Part; ISO 23551-5 — Safety and control devices for gas burners and gas-burning appliances - Part
* **Plynové spotřebiče v domácnostech a provozovnách**: ISO/DIS 23551-12 — Safety and control devices for gas burners and gas-burning appliances -; DIN EN 88-3 — Safety and control devices for gas burners and gas burning appliances - Part; STN EN 1643 — Bezpečnostné a ovládacie zariadenia pre horáky a spotrebiče spaľujúce plynné; STN EN 16678 — Bezpečnostné a ovládacie zariadenia horákov a spotrebičov na plynné palivá.; ISO 23551-4 — Safety and control devices for gas burners and gas-burning appliances - Part
* **Ochrana před výbuchem**: DIN EN IEC 60079-26 — Explosive atmospheres - Part 26: Equipment with separation elements ; STN EN 1127-1 — Výbušné atmosféry. Prevencia a ochrana pred výbuchom. Časť 1: Základné poj; Směrnice Evropského parlamentu a Rady 1999/92/ES ze dne 16. prosince 1999 o minimálních po; STN EN IEC 60079-26 — Výbušné atmosféry. Časť 26: Zariadenie s oddeľovacími prvkami alebo ; DIN EN IEC 60079-17*VDE 0165-10-1 — Explosive atmospheres - Part 17: Electrical installati
* **Bezpečnost a prevence havárií**: STN EN ISO 16852 — Protiplameňové uzávery. Požiadavky na účinnosť, skúšobné metódy a obmed; VDI 3783 Blatt 1 — Umweltmeteorologie - Ausbreitung von störfallbedingten Freisetzungen; ISO/TR 15916 — Basic considerations for the safety of hydrogen systems; G 1001 (A) — Sicherheit in der Gas- und Wasserstoffversorgung; Risikomanagement von gastec; ISO 26142 — Hydrogen detection apparatus — Stationary applications
* **Chemické látky a směsi**: 350/2011 Sb. Chemický zákon; Nařízení Evropského parlamentu a Rady (ES) č. 1272/2008 ze dne 16. prosince 2008 o klasifi; ISO 7104 — Liquefied anhydrous ammonia for industrial use -- Determination of water conten; ISO 7106 — Liquefied anhydrous ammonia for industrial use -- Determination of oil content ; ISO 4276 — Anhydrous ammonia for industrial use -- Evaluation of residue on evaporation --
* **BOZP a odborná způsobilost**: 258/2000 Sb. Zákon o ochraně veřejného zdraví; G 102-7 (M) — Qualifikationsanforderungen an Sachkundige der Gasinfrastruktur – Teil 7: Sp; Zákon o bezpečnosti a ochrane zdravia pri práci a o zmene a doplnení niektorých zákonov; STN EN ISO 45001 — Systémy manažérstva bezpečnosti a ochrany zdravia pri práci. Požiadavky; TRGS 510 — Lagerung von Gefahrstoffen in ortsbeweglichen Behältern
* **Materiály a jejich zkoušení**: STN EN ISO 10893-11 — Nedeštruktívne skúšanie oceľových rúr. Časť 11: Automatizované ultra; STN EN 10217-2 — Zvárané oceľové rúry na tlakové účely. Technické dodacie podmienky. Časť ; DIN EN 13322-1 — Transportable gas cylinders - Refillable welded steel gas cylinders - Des; STN EN 14620-4 — Navrhovanie a výroba na mieste stavaných vertikálnych valcových oceľových; STN EN ISO 9809-4 — Fľaše na plyny. Navrhovanie, konštrukcia a skúšanie znovuplniteľných b
* **Komponenty, armatury a potrubí**: ISO 12619-4 — Road vehicles — Compressed gaseous hydrogen (CGH2) and hydrogen/natural gas ; ISO 21012 — 2024 - Cryogenic vessels — Hoses; ISO 15330 — 1999 - Fasteners — Preloading test for the detection of hydrogen embrittlement; IEC/TS 63208 — Low-voltage switchgear and controlgear - Security aspects; STN EN 10217-2 — Zvárané oceľové rúry na tlakové účely. Technické dodacie podmienky. Časť 
* **Řídicí systémy a kybernetická bezpečnost**: STN EN IEC 62351-8 — Riadenie elektrických výkonových sústav a pridružená výmena informáci; DIN IEC/TS 62351-100-1 (VDE V 0112-351-100-1) — Power systems management and associated in; NIST Special Publication 800-207 — Zero Trust Architecture; ISO 19885-2 — Gaseous hydrogen — Fuelling protocols for hydrogen-fuelled vehicles — Part 2; STN EN IEC 62061 — Bezpečnosť strojov. Funkčná bezpečnosť bezpečnostných riadiacich systém
* **Posuzování shody a certifikace výrobků**: (EU) 2019/250 - COMMISSION IMPLEMENTING REGULATION of 12 February 2019 on the templates fo; H2.22:2022 — Certification program for hydrogen generators and their main components based; DIN 3384-2 — Pipework — Part 2: Conformity assessment of connection for corrugated stainle; STN EN 50549-10 — Požiadavky na generátory určené na pripojenie paralelne s distribučnou s; ZP 3502.20 — Zertifizierungsprogramm Ergänzungsprüfungen für Gebläsebrenner für gasförmige
* **Stavby, územní plánování a umístění**: STN 73 6005 — Priestorové usporiadanie vedení technického vybavenia; ISO 13315-2 — Environmental management for concrete and concrete structures — Part 2: Syst; Nařízení Komise (EU) č. 1303/2014 ze dne 18. listopadu 2014 o technické specifikaci pro in; Vyhláška Ministerstva vnútra Slovenskej republiky, ktorou sa ustanovujú technické požiadav; Zákon o územnom plánovaní
* **Energetika a trh s plynem a vodíkem**: (EU) 2024/1789 - Nařízení Evropského parlamentu a Rady (EU) 2024/1789 ze dne 13. června 20; Vyhláška Úradu pre reguláciu sieťových odvetví, ktorou sa ustanovuje cenová regulácia vybr; STN EN 50549-1 — Požiadavky na generátory určené na pripojenie paralelne s distribučnou si; Politický, legislativní a nelegislativní rámec EU pro rozvoj vodíkového trhu (2024); 165/2012 Sb. Zákon o podporovaných zdrojích energie a o změně některých zákonů
* **Životní prostředí, emise a klima**: Směrnice Evropského parlamentu a Rady 2010/75/EU ze dne 24. listopadu 2010 o průmyslových ; ISO 17179 — 2016 - Stationary source emissions — Determination of the mass concentration o; STN EN 378-1+A1 — Chladiace systémy a tepelné čerpadlá. Požiadavky na bezpečnosť a ochranu; STN ISO 17179 — Ochrana ovzdušia. Stacionárne zdroje emisií. Meranie hmotnostnej koncentrá; ISO 13315-2 — Environmental management for concrete and concrete structures — Part 2: Syst
* **Strategie, koncepce a studie**: Vodíková stratégia pre klimaticky neutrálnu Európu; Studie – Využití vodíkového pohonu v dopravě v České republice (2017); SDĚLENÍ KOMISE EVROPSKÉMU PARLAMENTU, RADĚ, EVROPSKÉMU HOSPODÁŘSKÉMU A SOCIÁLNÍMU VÝBORU A; SDĚLENÍ KOMISE EVROPSKÉMU PARLAMENTU, RADĚ, EVROPSKÉMU HOSPODÁŘSKÉMU A SOCIÁLNÍMU VÝBORU A; SDĚLENÍ KOMISE EVROPSKÉMU PARLAMENTU, RADĚ, EVROPSKÉMU HOSPODÁŘSKÉMU A SOCIÁLNÍMU VÝBORU A
* **Obecné a průřezové předpisy**: Směrnice Rady 2001/86/ES ze dne 8. října 2001, kterou se doplňuje statut evropské společno; G 1030 (A) — Code of Practice G 1030; Směrnice Evropského parlamentu a Rady (EU) 2021/1187 ze dne 7. července 2021 o zjednodušen; CGA G-5 — Hydrogen; 2009/540/ES: Rozhodnutí Komise ze dne 10. července 2009 , kterým se mění rozhodnutí 2002/2

## 3. Pravidla přiřazení (`data/areas.json`)

**Zpřesnění (22.11.2026 večer):** Kontrola vzorků ukázala, že zdrojová klíčová slova tabulky 
prof. Sinaye a sekce rešerší doc. Prokopa / dr. Haltufa (např. „Schienenfahrzeuge“,
„Explosionsschutz“, „Stationäre und ortsbewegliche Druckbehälter“, „Untertage Gasspeicher“,
„Verflüssigung“, „A - výroba“, „Využití - ŽD“) jsou **kategorie celých skupin dokumentů**, 
ne vlastnosti dokumentu: „Schienenfahrzeuge“ nesly i normy plnicích stanic, měděných armatur nebo
hořáků, „Untertage Gasspeicher“ i normy ocelových trubek, „A - výroba“ i směrnice o tlakových 
zařízeních. Tyto hodnoty (60) jsou proto v seznamu `source_categories` a oblast neurčují.
Pravidla přiřazení píšeme tak, aby oblast seděla s obsahem podle názvu
\[DOPLNIT: Nerozhoduje jenom název, relevantní pro danou oblast může být i obsah dokumentu.\];
raději méně oblastí než šum (průměr klesl z 2,41 na 1,46 oblasti na dokument).

1. **Původní klíčová slova jen tam, kde jde o vlastnost dokumentu** — `keywords`: třídy ČSN („6972 - Kryogenické
   nádoby“), okruhy přidané editorem při přijetí kandidáta (`app/candidates_admin.py`), několik vydavatelů
   s jednoznačným zaměřením (OIML → metrologie, IMO a CESNI → lodní doprava, DGUV/BAuA/OSHA → BOZP);
   `committee_rules`: technická komise, která normu vydala (ISO/TC 58 a CEN/TC 23 → tlakové nádoby,
   IEC/TC 31 → výbuch, IEC/TC 9 a CEN/TC 256 → železnice …); `source_categories` a `ignore` oblast neurčují.
   Neznámou hodnotu vypíše `assign_areas.py` a hlídá `tests/test_areas.py`.
2. **Typ dokumentu** — `type_rules`: strategie a studie → „Strategie, koncepce a studie“.
3. **Název a označení** — `title_rules`: regulární výrazy v češtině, slovenštině, angličtině a němčině; `unless`
   pravidlo vyloučí (silniční vozidla ne, jde-li o kolejová vozidla). Železnice jen podle názvu: železnice,
   drážní, dráhy, kolejová vozidla, railway, TSI, interoperabilita, Eisenbahn.
4. **Náhradní oblast** `obecne` dostane dokument, kterému žádné pravidlo nic nepřiřadilo (`--uncertain`).
   LLM se nepoužívá.

## 4. Co se stalo s klíčovými slovy

Původní klíčová slova se **nemažou**: zůstávají v tabulkách `Keyword` a `DocumentKeyword`, 
prohledává je vyhledávání v katalogu (dotaz „Befüllungsanlagen“ dál najde příslušné normy)
a obsahují je exporty CSV/JSON/XML. Nejsou jen nabízena ve filtru ani zobrazena ve štítcích.
*Důvod:* nesou informaci ze zdrojových rešerší (vydavatel, technická komise, stav STN), kterou
oblasti nenahrazují, a mapování se z nich dá kdykoli přepočítat.
Starý odkaz `?keyword_id=…` dál funguje.

Oblasti jsou v tabulkách `Area` (kód, název, okruh, pořadí) a `DocumentArea` (dokument, oblast, původ:
`keyword`, `type`, `title`, `fallback`). Dokud v databázi nejsou, aplikace ukazuje původní klíčová slova.

## 5. Údržba

* `src/tools/assign_areas.py` — dry run s rozpadem; `--apply` zapíše; `--uncertain` vypíše nejisté.
  Idempotentní; spustit po přestavbě databáze (`init_db.py`) a po změně `data/areas.json`.
* Přijetí kandidáta oblasti novému dokumentu přiřadí hned (`areas.assign_document()`).
* Test: `tests/test_areas.py` (soubor, pravidla, zápis), `tests/e2e/test_areas.py` (filtr, stránka dokumentu,
  hledání ve skrytých klíčových slovech). `run_tests.py` oblasti do testovací databáze zapisuje
  (`TEST_DB_MIGRATIONS`).

## 6. Náhradní oblast: 70 dokumentů s návrhem

Souhrn návrhů: 42 mimo rozsah databáze (pracovní právo, rovné zacházení, přenosné nemoci, lasery, laboratorní voda,
potraviny — k posouzení vyřazení přes `data/manual_corrections.json`, `"exclude": true`; nic se nemaže automaticky),
18 pravidel DVGW bez názvu (záznam nese jen „Guideline G 404“ — doplnit název, oblast pak určí pravidla),
2 poškozené záznamy, 2 zkrácené názvy aktů EU (doplnit z Cellaru), 1 přiřadit ručně (2021/1187/EU, transevropská
dopravní síť) a 5 ponechat v náhradní oblasti (3 obecné dokumenty o vodíku, zákon o spotřebních daních, živnostenský zákon). U dokumentů, kde šlo určit
oblast pravidlem (perlit, DSfG, „suitability for hydrogen“, NEC, zemní práce …), je pravidlo doplněno a v seznamu
už nejsou.

| # | Označení | Název | Návrh |
|---|---|---|---|
| 62 | 2010/75/EU | Oznámenie Ministerstva dopravy, pôšt a telekomunikácií Slovenskej republiky o vydaní výnosu o m | mimo rozsah: slovenské oznámení o výnosu (název zkomolený, chybné označení 2010/75/EU) — k posouzení vyřazení |
| 74 | 353/2003 Sb. | 353/2003 Sb. Zákon o spotřebních daních | mimo rozsah: daně (doplňkový okruh odložený, doc/DATABASE_SCOPE.md) — ponechat v náhradní oblasti |
| 91 | (EU) 2021/535 | Nařízení Komise (EU) 2021/535 ze dne 31. března 2021, kterým se mění nařízení (ES) č. 1881/2006 | mimo rozsah: kontaminanty v potravinách (nařízení 1881/2006) — k vyřazení |
| 385 | / - 2024.08 | / - 2024.08 — kombinovanými úrovňami ochrany | poškozený záznam (název je zbytek řádku) — opravit nebo vyřadit |
| 445 | STN EN ISO 17526/ - 2003.12 | STN EN ISO 17526 — Optika a optické prístroje. Lasery a laserové zariadenia. Životnosť laserov  | mimo rozsah: lasery — k vyřazení |
| 472 | STN EN ISO 3696/ - 2000.02 | STN EN ISO 3696 — Kvalita vody na analytické účely. Špecifikácia a skúšobné metódy (ISO 3696:19 | mimo rozsah: voda pro laboratoře — k vyřazení |
| 711 | CGA G-5 | CGA G-5 — Hydrogen | obecný dokument o vodíku — ponechat v náhradní oblasti, nebo Bezpečnost (CGA G-5 je bezpečnostní příručka) |
| 740 | EIGA DOC 247 | EIGA DOC 247 — DOC 247 / 24 - Hydrogen Overview - Distribution-Storage-Applications | obecný přehled — ponechat v náhradní oblasti |
| 745 | G 404 (M) | G 404 (M) — Guideline G 404 | chybí název (pravidlo DVGW, jen označení) — doplnit název, oblast pak určí pravidla |
| 746 | G 409 (M) | G 409 (M) — Guideline G 409 | chybí název (pravidlo DVGW, jen označení) — doplnit název, oblast pak určí pravidla |
| 747 | G 102-11 (M) | G 102-11 (M) — Guideline G 102-11 | chybí název (pravidlo DVGW, jen označení) — doplnit název, oblast pak určí pravidla |
| 748 | G 102-13 (M) | G 102-13 (M) — Code of Practice G 102-13 | chybí název (pravidlo DVGW, jen označení) — doplnit název, oblast pak určí pravidla |
| 749 | G 102-2 (A) | G 102-2 (A) — Code of Practice G 102-2 | chybí název (pravidlo DVGW, jen označení) — doplnit název, oblast pak určí pravidla |
| 750 | G 102-3 (M) | G 102-3 (M) — Code of Practice G 102-3 | chybí název (pravidlo DVGW, jen označení) — doplnit název, oblast pak určí pravidla |
| 751 | G 102-5 (A) | G 102-5 (A) — Code of Practice G 102-5 | chybí název (pravidlo DVGW, jen označení) — doplnit název, oblast pak určí pravidla |
| 752 | G 102-8 (M) | G 102-8 (M) — Guideline G 102-8 | chybí název (pravidlo DVGW, jen označení) — doplnit název, oblast pak určí pravidla |
| 753 | G 1030 (A) | G 1030 (A) — Code of Practice G 1030 | chybí název (pravidlo DVGW, jen označení) — doplnit název, oblast pak určí pravidla |
| 754 | G 290 (A) | G 290 (A) — Guideline G 290 | chybí název (pravidlo DVGW, jen označení) — doplnit název, oblast pak určí pravidla |
| 755 | G 292-2 (A) | G 292-2 (A) — Code of Practice G 292-2 | chybí název (pravidlo DVGW, jen označení) — doplnit název, oblast pak určí pravidla |
| 756 | G 294 (M) | G 294 (M) — Guideline G 294 | chybí název (pravidlo DVGW, jen označení) — doplnit název, oblast pak určí pravidla |
| 757 | G 441 (A) | G 441 (A) — Code of Practice G 441 | chybí název (pravidlo DVGW, jen označení) — doplnit název, oblast pak určí pravidla |
| 758 | G 453 (A) | G 453 (A) — Guideline G 453 | chybí název (pravidlo DVGW, jen označení) — doplnit název, oblast pak určí pravidla |
| 759 | G 458-1 (A) | G 458-1 (A) — Code of Practice G 458-1 | chybí název (pravidlo DVGW, jen označení) — doplnit název, oblast pak určí pravidla |
| 760 | G 466-1 (A) | G 466-1 (A) — Code of Practice G 466-1 | chybí název (pravidlo DVGW, jen označení) — doplnit název, oblast pak určí pravidla |
| 761 | G 474 (M) | G 474 (M) — Code of Practice G 474 | chybí název (pravidlo DVGW, jen označení) — doplnit název, oblast pak určí pravidla |
| 762 | G 497 (A) | G 497 (A) — Code of Practice G 497 | chybí název (pravidlo DVGW, jen označení) — doplnit název, oblast pak určí pravidla |
| 826 | ASTM D 1141 | ASTM D 1141 — Standard Practice For Preparation Of Substitute Ocean Water | mimo rozsah: náhradní mořská voda — k vyřazení |
| 827 | ASTM D 1193 | ASTM D 1193 — Standard Specification for Reagent Water | mimo rozsah: reagenční voda — k vyřazení |
| 834 | ASTM F 21 | ASTM F 21 — Standard Test Method for Hydrophobic Surface Films by the Atomizer Test | mimo rozsah — k vyřazení |
| 976 | Gas-Information Nr. 15 | Gas-Information Nr. 15 — Leitfaden Dokumentation | obecné (dokumentace) — ponechat v náhradní oblasti |
| 1077 |  | je možné nájsť na stránkach jednotlivých technických komisií CEN, CENELEC, | poškozený záznam (název je věta z poznámky) — opravit nebo vyřadit |
| 1213 | 455/1991 Sb. | 455/1991 Sb. Živnostenský zákon | mimo rozsah věcných okruhů (živnostenský zákon); souvisí s živnostenským oprávněním k výrobě vodíku — ponechat |
| 1234 | (EU) 2025/1486 | Prováděcí rozhodnutí Komise (EU) 2025/1486 ze dne 22. července 2025, kterým se stanoví pravidla | zkrácený název, z označení nelze určit — doplnit úplný název z Cellaru |
| 1237 | (EU) 2026/1551 | Prováděcí rozhodnutí Komise (EU) 2026/1551 ze dne 9. července 2026, kterým se stanoví pravidla  | zkrácený název — doplnit úplný název z Cellaru |
| 1305 | ISO 17526 | ISO 17526 — 2003 - Optics and optical instruments — Lasers and laser-related equipment — Lifeti | mimo rozsah: lasery — k vyřazení |
| 1332 | ISO 3696 | ISO 3696 — 1987 - Water for analytical laboratory use — Specification and test methods | mimo rozsah: voda pro laboratoře — k vyřazení |
| 1368 | 1999/70/ES | Směrnice Rady 1999/70/ES ze dne 28. června 1999 o rámcové dohodě o pracovních poměrech na dobu  | mimo rozsah (pracovní právo, zdraví, nemoci) — k posouzení vyřazení |
| 1369 | 2000/43/ES | Směrnice Rady 2000/43/ES ze dne 29. června 2000, kterou se zavádí zásada rovného zacházení s os | mimo rozsah (pracovní právo, zdraví, nemoci) — k posouzení vyřazení |
| 1373 | 2000/78/ES | Směrnice Rady 2000/78/ES ze dne 27. listopadu 2000, kterou se stanoví obecný rámec pro rovné za | mimo rozsah (pracovní právo, zdraví, nemoci) — k posouzení vyřazení |
| 1375 | 2001/23/ES | Směrnice Rady 2001/23/ES ze dne 12. března 2001 o sbližování právních předpisů členských států  | mimo rozsah (pracovní právo, zdraví, nemoci) — k posouzení vyřazení |
| 1377 | 2001/86/ES | Směrnice Rady 2001/86/ES ze dne 8. října 2001, kterou se doplňuje statut evropské společnosti s | mimo rozsah (pracovní právo, zdraví, nemoci) — k posouzení vyřazení |
| 1378 | 2002/14/ES | Směrnice Evropského parlamentu A Rady 2002/14/ES ze dne 11. března 2002, kterou se stanoví obec | mimo rozsah (pracovní právo, zdraví, nemoci) — k posouzení vyřazení |
| 1379 | 2002/15/ES | Směrnice Evropského parlamentu A Rady 2002/15/ES ze dne 11. března 2002 o úpravě pracovní doby  | mimo rozsah (pracovní právo, zdraví, nemoci) — k posouzení vyřazení |
| 1380 | 2002/253/ES | Rozhodnutí Komise ze dne 19. března 2002, kterou se stanoví definice případů pro hlášení přenos | mimo rozsah (pracovní právo, zdraví, nemoci) — k posouzení vyřazení |
| 1381 | 2002/44/ES | Směrnice Evropského parlamentu a Rady 2002/44/ES ze dne 25. června 2002 o minimálních požadavcí | mimo rozsah (pracovní právo, zdraví, nemoci) — k posouzení vyřazení |
| 1385 | 2003/72/ES | Směrnice Rady 2003/72/ES ze dne 22. července 2003, kterou se doplňuje statut evropské družstevn | mimo rozsah (pracovní právo, zdraví, nemoci) — k posouzení vyřazení |
| 1386 | 2003/88/ES | Směrnice Evropského parlamentu a Rady 2003/88/ES ze dne 4. listopadu 2003 o některých aspektech | mimo rozsah (pracovní právo, zdraví, nemoci) — k posouzení vyřazení |
| 1389 | 2004/113/ES | Směrnice Rady 2004/113/ES ze dne 13. prosince 2004, kterou se zavádí zásada rovného zacházení s | mimo rozsah (pracovní právo, zdraví, nemoci) — k posouzení vyřazení |
| 1398 | 2006/54/ES | Směrnice Evropského parlamentu a Rady 2006/54/ES ze dne 5. července 2006 o zavedení zásady rovn | mimo rozsah (pracovní právo, zdraví, nemoci) — k posouzení vyřazení |
| 1401 | 2007/875/ES | 2007/875/ES: Rozhodnutí Komise ze dne 18. prosince 2007 , kterým se mění rozhodnutí Evropského  | mimo rozsah (změna rozhodnutí o síti pro přenosné nemoci) — k posouzení vyřazení |
| 1402 | 2008/104/ES | Směrnice Evropského parlamentu a Rady 2008/104/ES ze dne 19. listopadu 2008 o agenturním zaměst | mimo rozsah (pracovní právo, zdraví, nemoci) — k posouzení vyřazení |
| 1404 | 2008/426/ES | 2008/426/ES: Rozhodnutí Komise ze dne 28. dubna 2008 , kterým se mění rozhodnutí 2002/253/ES, k | mimo rozsah (pracovní právo, zdraví, nemoci) — k posouzení vyřazení |
| 1409 | 2009/104/EU | Směrnice Evropského parlamentu a Rady 2009/104/ES ze dne 16. září 2009 o minimálních požadavcíc | mimo rozsah (pracovní právo, zdraví, nemoci) — k posouzení vyřazení |
| 1413 | 2009/177/EU | 2009/177/ES: Rozhodnutí Komise ze dne 31. října 2008 , kterým se provádí směrnice Rady 2006/88/ | mimo rozsah (pracovní právo, zdraví, nemoci) — k posouzení vyřazení |
| 1417 | 2009/312/EU | 2009/312/ES: Rozhodnutí Komise ze dne 2. dubna 2009 , kterým se mění rozhodnutí 2000/96/ES, pok | mimo rozsah (pracovní právo, zdraví, nemoci) — k posouzení vyřazení |
| 1418 | 2009/363/EU | 2009/363/ES: Rozhodnutí Komise ze dne 30. dubna 2009 , kterým se mění rozhodnutí 2002/253/ES, k | mimo rozsah (pracovní právo, zdraví, nemoci) — k posouzení vyřazení |
| 1419 | 2009/38/EU | Směrnice Evropského parlamentu a Rady 2009/38/ES ze dne 6. května 2009 o zřízení evropské rady  | mimo rozsah (pracovní právo, zdraví, nemoci) — k posouzení vyřazení |
| 1420 | 2009/539/EU | 2009/539/ES: Rozhodnutí Komise ze dne 10. července 2009 , kterým se mění rozhodnutí 2000/96/ES  | mimo rozsah (pracovní právo, zdraví, nemoci) — k posouzení vyřazení |
| 1421 | 2009/540/EU | 2009/540/ES: Rozhodnutí Komise ze dne 10. července 2009 , kterým se mění rozhodnutí 2002/253/ES | mimo rozsah (pracovní právo, zdraví, nemoci) — k posouzení vyřazení |
| 1422 | 2009/547/EU | 2009/547/ES: Rozhodnutí Komise ze dne 10. července 2009 , kterým se mění rozhodnutí 2000/57/ES  | mimo rozsah (pracovní právo, zdraví, nemoci) — k posouzení vyřazení |
| 1423 | 2010/32/EU | Směrnice Rady 2010/32/EU ze dne 10. května 2010 , kterou se provádí Rámcová dohoda o prevenci p | mimo rozsah (pracovní právo, zdraví, nemoci) — k posouzení vyřazení |
| 1432 | 2014/66/EU | Směrnice Evropského parlamentu a Rady 2014/66/EU ze dne 15. května 2014 o podmínkách vstupu a p | mimo rozsah (pracovní právo, zdraví, nemoci) — k posouzení vyřazení |
| 1443 | 2018/957/EU | Směrnice Evropského parlamentu a Rady (EU) 2018/957 ze dne 28. června 2018, kterou se mění směr | mimo rozsah (pracovní právo, zdraví, nemoci) — k posouzení vyřazení |
| 1444 | 2019/1152/EU | Směrnice Evropského parlamentu a Rady (EU) 2019/1152 ze dne 20. června 2019 o transparentních a | mimo rozsah (pracovní právo, zdraví, nemoci) — k posouzení vyřazení |
| 1445 | 2019/1158/EU | Směrnice Evropského parlamentu a Rady (EU) 2019/1158 ze dne 20. června 2019 o rovnováze mezi pr | mimo rozsah (pracovní právo, zdraví, nemoci) — k posouzení vyřazení |
| 1449 | 2021/1187/EU | Směrnice Evropského parlamentu a Rady (EU) 2021/1187 ze dne 7. července 2021 o zjednodušení opa | patrně Silniční/Železnice (zjednodušení opatření pro transevropskou dopravní síť) — přiřadit ručně |
| 1450 | 2022/2041/EU | Směrnice Evropského parlamentu a Rady (EU) 2022/2041 ze dne 19. října 2022 o přiměřených minimá | mimo rozsah (pracovní právo, zdraví, nemoci) — k posouzení vyřazení |
| 1452 | 2000/96/ES | Rozhodnutí Komise ze dne 22. prosince 1999 o přenosných nemocích, které musí být postupně podch | mimo rozsah (pracovní právo, zdraví, nemoci) — k posouzení vyřazení |
| 1453 | 2006/865/ES | Nařízení Komise (ES) č. 865/2006 ze dne 4. května 2006 o prováděcích pravidlech k nařízení Rady | mimo rozsah (pracovní právo, zdraví, nemoci) — k posouzení vyřazení |
| 1455 | 1998/2119/ES | Rozhodnutí Evropského parlamentu a Rady č. 2119/98/ES ze dne 24. září 1998 o zřízení sítě epide | mimo rozsah (pracovní právo, zdraví, nemoci) — k posouzení vyřazení |
