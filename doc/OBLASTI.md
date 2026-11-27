# Oblasti katalogu

Stav k 23.11.2026, názvy tabulek a klíčů `data/areas.json` k 25.11.2026 (odstavec 4).
Filtr „Oblast“ v katalogu a štítky u dokumentů v seznamu a na stránce dokumentu
nově ukazují **oblasti**: 30 českých hodnot (27 věcných, strategie, dokumenty obecné povahy
a pracovní „Oblast dosud neurčena“) navázaných na věcné okruhy `doc/DATABASE_SCOPE.md` (tento dokument, odstavec 3).
Dosud v nich byly kategorie převzaté ze zdrojových rešerší (do 25.11.2026 vedené jako
„klíčová slova“ v tabulce `Keyword`), které nedávaly moc smysl.

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

Počty z běhu nanečisto skriptu `assign_areas.py` nad živou databází (1506 dokumentů; dokument
může mít více oblastí). Sloupec „21. 11.“ ukazuje původní verzi pravidel, „22. 11.“ verzi, ve které
jsme přestali odvozovat oblasti z kategorií zdrojových tabulek (odstavec 3), a „23. 11.“ současnou
verzi s novými oblastmi Elektrolýza, Plnicí stanice a Doprava vodíku (odstavec 7). Dnes o oblasti
rozhoduje hlavně název a označení dokumentu, dále třídy ČSN, technická komise, která normu vydala,
okruhy zvolené editorem při přijetí kandidáta, několik vydavatelů s jednoznačným zaměřením a typ
dokumentu. Obsah dokumentu (anotaci, plný text) zatím nepoužíváme; úkol a měření k němu popisuje odstavec 8.

| Oblast | Okruh | 21. 11. | 22. 11. | 23. 11. |
|---|---|---|---|---|
| Elektrolýza | 1 | — | — | 10 |
| Výroba vodíku jinými postupy | 1 | 80 | 21 | 11 |
| Obnovitelný a nízkouhlíkový vodík, certifikace | 1 | 30 | 19 | 19 |
| Tlakové nádoby a lahve | 2 | 186 | 164 | 164 |
| Zkapalněný vodík a kryogenní technika | 2 | 172 | 102 | 102 |
| Podzemní zásobníky | 2 | 114 | 13 | 13 |
| Doprava vodíku (plynovody, sítě, přeprava) | 3 | 179+17 | 129+33 | 162 |
| Plnicí stanice | 4 | 94 | 70 | 69 |
| Kvalita vodíku, měření a metrologie | 4 | 153 | 133 | 133 |
| Silniční a speciální vozidla | 5 | 256 | 134 | 134 |
| Železnice a kolejová vozidla | 5 | 220 | 48 | 48 |
| Lodní a letecká doprava | 5 | 55 | 39 | 39 |
| Palivové články | 6 | 75 | 64 | 64 |
| Průmyslové využití a Power-to-X | 6 | 130 | 66 | 66 |
| Elektrárny, turbíny a tepelná zařízení | 6 | 73 | 69 | 69 |
| Plynové spotřebiče v domácnostech a provozovnách | 6 | 48 | 33 | 33 |
| Ochrana před výbuchem | 7 | 273 | 69 | 69 |
| Bezpečnost a prevence havárií | 7 | 240 | 56 | 56 |
| Chemické látky a směsi | 7 | 22 | 18 | 18 |
| BOZP a odborná způsobilost | 7 | 73 | 62 | 62 |
| Materiály a jejich zkoušení | 7 | 317 | 239 | 239 |
| Komponenty, armatury a potrubí | 7 | 281 | 239 | 239 |
| Řídicí systémy a kybernetická bezpečnost | 7 | 94 | 69 | 69 |
| Posuzování shody a certifikace výrobků | 7 | 134 | 14 | 14 |
| Stavby, územní plánování a umístění | 8 | 17 | 19 | 19 |
| Energetika a trh s plynem a vodíkem | 9 | 76 | 62 | 62 |
| Životní prostředí, emise a klima | 10 | 139 | 105 | 105 |
| Strategie, koncepce a studie | — | 38 | 38 | 38 |
| Dokumenty obecné povahy | — | — | — | 5 |
| Oblast dosud neurčena | — | 40 | 70 | 65 |
| **Oblastí na dokument (průměr)** | | 2.41 | 1.46 | 1.46 |

U sloučené oblasti Doprava vodíku uvádíme dřívější počty obou původních oblastí (Plynovody a plynárenské
sítě + Přeprava nebezpečných věcí); „Oblast dosud neurčena“ nahradila dřívější náhradní oblast
„Obecné a průřezové předpisy“. Rozpad podle původu (23. 11.): jen z názvu 1161 dokumentů, jen z kategorií
zdrojových rešerší 106, z obojího 157, z typu 12, z výčtu označení 5, oblast dosud neurčena 65.

### 2.1 Příklady (5 náhodně vybraných názvů z každé oblasti)

* **Elektrolýza**: VDI 4635 Blatt 3.1 — Power-to-X; Hydrogen production through water electrolysis; DIN EN ISO 22734 — DIN EN ISO 22734; MB 12 — Inverkehrbringen von Wasser- Elektrolyseanlagen; Případová studie výstavby elektrolyzéru v České republice (2023); ČSN EN 60335-2-108 — Elektrické spotřebiče pro domácnost a podobné účely - Bezpečnost - Čá
* **Výroba vodíku jinými postupy**: ISO 16110-2 — Hydrogen generators using fuel processing technologies - Part 2: Test method; EIGA DOC 185 — DOC 185 / 20 - Safe Start Up and Shutdown Practices for Steam Reformers; Policy Paper HYTEP: The Cost Challenge: Unlocking the Potential of EU Renewable Hydrogen P; EIGA DOC 246 — DOC 246 / 23 - Guideline for Small Scale Hydrogen Production; EIGA DOC 210 — DOC 210 / 23 - Hydrogen Pressure Swing Adsorber (PSA) Mechanical Integrity 
* **Obnovitelný a nízkouhlíkový vodík, certifikace**: Zákon, ktorým sa mení a dopĺňa zákon č. 98/2004 Z. z. o spotrebnej dani z minerálneho olej; Směrnice Evropského parlamentu a Rady (EU) 2015/1513 ze dne 9. září 2015, kterou se mění s; Nařízení Evropského parlamentu a Rady (EU) 2023/955 ze dne 10. května 2023 o vnitřním trhu; (EU) 2023/2413 - DIRECTIVE OF THE EUROPEAN PARLIAMENT AND OF THE COUNCIL of 18 October 202; Směrnice Evropského parlamentu a Rady 2009/28/ES ze dne 23. dubna 2009 o podpoře využívání
* **Tlakové nádoby a lahve**: AS B12 — Cylinders for the storage and transport of anhydrous ammonia, chlorine and sulphu; ASME BPVC VIII.3 Article KD-10 — ASME Boiler and Pressure Vessel Code Special requirements; STN EN 10028-7 — Ploché výrobky z ocelí na tlakové nádoby a zariadenia. Časť 7: Nehrdzavej; STN EN ISO 11120 — Fľaše na plyny. Návratné bezšvové oceľové fľaše s vodnou kapacitou od 1; STN EN 13160-3+A1 — Systémy zisťovania netesností. Časť 3: Požiadavky a skúšobné metódy/me
* **Zkapalněný vodík a kryogenní technika**: DIN EN ISO 21009-2 — Cryogenic vessels - Static vacuum-insulated vessels - Part 2: Operati; ASTM C740-97 — Standard Practice for Evacuated Reflective Insulation in Cryogenic Service; STN EN 13648-1 — Kryogénne nádoby. Zabezpečovacie zariadenia na ochranu pred nadmerným tla; DIN EN ISO 21012 — Cryogenic vessels - Hoses; STN EN ISO 20257-2 — Inštalácia a vybavenie na skvapalnený zemný plyn (LNG). Návrh plávajú
* **Podzemní zásobníky**: STN EN 1918-4 — Plynárenská infraštruktúra. Podzemné zásobníky plynu. Časť 4: Funkčné poži; BVEG Technische Regel Bohrlochkontrolle; BVEG Leitfaden Futterrohrberechnung; BVEG Leitfaden Auswirkungen von Störfällen im Speicherbetrieb; STN EN 1918-1 — Plynárenská infraštruktúra. Podzemné zásobníky plynu. Časť 1: Funkčné poži
* **Doprava vodíku (plynovody, sítě, přeprava)**: ISO/AWI 5124 — Installations and equipment for LNG — LNG railcar applications; ISO 15156-2 — 2020 - Petroleum and natural gas industries — Materials for use in H2S-conta; G 102-4 (A) — Qualifikationsanforderungen an Sachkundige der Gasinfrastruktur – Teil 4: Sp; STN P CEN/TS 17977 — Plynárenská infraštruktúra. Kvalita plynu. Vodík používaný v opätovne; STN EN ISO 28460 — Ropný a plynárenský priemysel. Zariadenie a príslušenstvo na skvapalnen
* **Plnicí stanice**: EN 17127 — Outdoor hydrogen refuelling points dispensing gaseous hydrogen and incorporatin; ISO 19880-8 — Gaseous hydrogen - Fuelling stations - Part 8: Fuel quality control; IGC Doc 15/06/E — Gaseous hydrogen stations; ISO/AWI 13984 — Liquid Hydrogen Land Vehicle Fueling Protocol; ISO 19885-1 — Gaseous hydrogen — Fuelling protocols for hydrogen-fuelled vehicles — Part 1
* **Kvalita vodíku, měření a metrologie**: ISO 21087 — Gas analysis — Analytical methods for hydrogen fuel — Proton exchange membrane; Gas-Information Nr. 7 — Technische Spezifikation für DSfG-Realisierungen; ASTM D 7607/D 7607M — Standard Test Method for Analysis of Oxygen in Gaseous Fuels (Electr; STN EN ISO 6145-8 — Analýza plynov. Príprava kalibračných plynných zmesí dynamickými objem; DIN 1340 — Gaseous fuels and other gases; types, constituents, application
* **Silniční a speciální vozidla**: ISO 8713 — Electrically propelled road vehicles - vocabulary; ISO/TR 11954 — Fuel cell road vehicles — Performance measurement — Vehicles fuelled with c; STN EN 13385 — Prepravné fľaše na plyny. Batérie na vozidlách na stále a skvapalnené plyny; STN EN 1317-1 — Záchytné bezpečnostné zariadenia na pozemných komunikáciách. Časť 1: Termi; ISO 23273 — Fuel cell road vehicles - Safety specifications - Protection against hydrogen 
* **Železnice a kolejová vozidla**: Směrnice Komise 2014/106/EU ze dne 5. prosince 2014 , kterou se mění přílohy V a VI směrni; (EU) 2018/545 - COMMISSION IMPLEMENTING REGULATION (EU) of 4 April 2018 establishing pract; ČSN EN 50128 — Drážní zařízení - Sdělovací a zabezpečovací systémy a systémy zpracování da; Směrnice Evropského parlamentu a Rady 2007/59/ES ze dne 23. října 2007 o vydávání osvědčen; 133/2005 Sb. Nařízení vlády o technických požadavcích na provozní a technickou propojenost
* **Lodní a letecká doprava**: Nařízení Komise v Přenesené Pravomoci (EU) 2019/1745 ze dne 13. srpna 2019, kterým se dopl; Směrnice Rady 2014/112/EU ze dne 19. prosince 2014 , kterou se provádí Evropská dohoda o ú; ISO/AWI 18742 — Ship and marine technology — Hi-manganese austenitic steel — Specification; MSC.1/Circ.1647 — Interim guidelines for the safety of ships using fuel cell power install; IMO CCC8/WP.3 Annex 2 — Interim guidelines for ships using hydrogen as fuel
* **Palivové články**: STN EN IEC 62282-8-201 — Technológia palivových článkov. Časť 8-201: Systémy na akumuláciu; ISO 23828 — Fuel cell road vehicles - Energy consumption measurement - Vehicles fuelled wi; STN EN 62282-3-300 — Technológia palivových článkov. Časť 3-300: Stacionárne výkonové súst; MSC.1/Circ.1647 — Interim guidelines for the safety of ships using fuel cell power install; 2014/832/EU: Rozhodnutí Rady ze dne 7. listopadu 2014 o postoji, který má být zaujat jméne
* **Průmyslové využití a Power-to-X**: UL Standard (UL 565, Edition 6) — Standard for Liquid-Level Gauges for Anhydrous Ammonia a; STN EN 746-2 — Priemyselné zariadenia na tepelné spracovanie. Časť 2: Bezpečnostné požiada; Gas-Information Nr. 26 — Genehmigungsrechtlicher Leitfaden für Power-to-Gas-Anlagen - Erri; TNI CEN/TR 15339-4 — Žiarové striekanie. Bezpečnostné požiadavky na zariadenie na žiarové ; ISO 7106 — Liquefied anhydrous ammonia for industrial use -- Determination of oil content 
* **Elektrárny, turbíny a tepelná zařízení**: ISO 13577-4 — 2022 - Industrial furnaces and associated processing equipment — Safety — Pa; ZP 3100.100 — Zertifizierungsprogramm Prüfungen für Heizkessel für gasförmige Brennstoffe ; STN EN 50549-1 — Požiadavky na generátory určené na pripojenie paralelne s distribučnou si; ISO 23551-4 — Safety and control devices for gas burners and gas-burning appliances - Part; STN EN 1829-1 — Vysokotlakové vodné dýzové stroje. Požiadavky na bezpečnosť. Časť 1: Stroj
* **Plynové spotřebiče v domácnostech a provozovnách**: ISO/DIS 23551-12 — Safety and control devices for gas burners and gas-burning appliances -; STN EN 1106 — Ručne ovládané armatúry pre spotrebiče na plynné palivá; STN EN 14459 — Bezpečnostné a ovládacie zariadenia horákov a spotrebičov na plynné alebo k; STN EN 1643 — Bezpečnostné a ovládacie zariadenia pre horáky a spotrebiče spaľujúce plynné; ISO 23551-8 — Safety and control devices for gas burners and gas-burning appliances - Part
* **Ochrana před výbuchem**: prEN IEC 60079-2 — Explosive atmospheres - Part 2: Equipment protection by pressurized enc; IEC/TS 60079-46 — Explosive atmospheres - Part 46: Equipment assemblies; STN EN 60079-17 — Výbušné atmosféry. Časť 17: Revízia a údržba elektrických inštalácií; DIN EN IEC 60079-2 — Explosive atmospheres - Part 2: Equipment protection by pressurized e; STN EN 1127-1 — Výbušné atmosféry. Prevencia a ochrana pred výbuchom. Časť 1: Základné poj
* **Bezpečnost a prevence havárií**: ISO 45001 — 2018 - Occupational health and safety management systems; Vyhláška Ministerstva vnútra Slovenskej republiky, ktorou sa ustanovujú technické požiadav; STN EN ISO 12100 — Bezpečnosť strojov. Všeobecné zásady konštruovania strojov. Posudzovani; ANSI/AIAA G-095A — Guide to Safety of Hydrogen and Hydrogen Systems; VDI 3783 — Ausbreitung von störfallbedingten Freisetzungen - Sicherheitsanalyse
* **Chemické látky a směsi**: ISO 7106 — Liquefied anhydrous ammonia for industrial use -- Determination of oil content ; ISO 7103 — Liquefied anhydrous ammonia for industrial use -- Sampling -- Taking a laborato; ISO 4276 — Anhydrous ammonia for industrial use -- Evaluation of residue on evaporation --; ISO 6192 — Light olefins for industrial use -- Determination of ammonia -- Photometric met; Směrnice Evropského parlamentu a Rady 1999/45/ES ze dne 31. května 1999 o sbližování právn
* **BOZP a odborná způsobilost**: TRB 852 — Technische Regeln zur Druckbehälterverordnung Füllanlagen Füllanlagen zum Abfüll; STN ISO 45001 — Systémy manažérstva bezpečnosti a ochrany zdravia pri práci. Požiadavky s ; G 102-12 (M) — Qualifikationsanforderungen an Sachkundige der Gasinfrastruktur – Teil 12: ; BVEG Leitfaden Persönliche Schutzausrüstung; TRBS 3151/TRGS 751 — Vermeidung von Brand-, Explosions- und Druckgefährdungen an Tankstell
* **Materiály a jejich zkoušení**: STN EN ISO 9809-1 — Fľaše na plyny. Navrhovanie, konštrukcia a skúšanie znovuplniteľných b; ISO 2626 — 1973 - Copper — Hydrogen embrittlement test; DIN 50916-2 — Testingofcopperalloys–Stresscorrosioncrackingtestusingammonia– Part2:Testing; STN EN ISO 21028-1 — Kryogénne nádoby. Požiadavky na húževnatosť materiálu pri nízkych tep; ISO 11114-2 — 2021 Gas cylinders — Compatibility of cylinder and valve materials with gas 
* **Komponenty, armatury a potrubí**: ISO 23551-2 — Safety and control devices for gas burners and gas-burning appliances - Part; STN EN ISO 3183 — Ropný a plynárenský priemysel. Oceľové rúry na potrubné dopravné systémy; STN EN 13160-6 — Systémy zisťovania netesností. Časť 6: Senzory v monitorovacích sondách; DIN 16966-8 — Glass fibre reinforced polyester resin (UP-GF) pipe fittings and joints; Lam; STN EN 1106+A1 — Ručne ovládané armatúry pre spotrebiče na plynné palivá
* **Řídicí systémy a kybernetická bezpečnost**: ISO 13849-1 — 2023 - Safety of machinery — Safety-related parts of control systems — Part ; STN EN 61508-5 — Funkčná bezpečnosť elektrických/elektronických/programovateľných elektron; STN EN ISO 13849-1 — Bezpečnosť strojov. Bezpečnostné časti riadiacich systémov. Časť 1: V; ISO/AWI 19885-2 — Gaseous hydrogen — Fuelling protocols for hydrogen-fuelled vehicles — Pa; STN EN 62351-9 — Riadenie elektrických výkonových sústav a pridružená výmena informácií. B
* **Posuzování shody a certifikace výrobků**: ZP 3100.20 — Zertifizierungsprogramm Ergänzungsprüfungen für Heizkessel für gasförmige Bre; Prováděcí nařízení Komise (EU) 2019/250 ze dne 12. února 2019 o vzorech ES prohlášení a ce; H2.22:2022 — Certification program for hydrogen generators and their main components based; (EU) 2019/250 - COMMISSION IMPLEMENTING REGULATION of 12 February 2019 on the templates fo; Poznámka: ASME Section VIII of the code is dedicated to pressure vessels. It gives detaile
* **Stavby, územní plánování a umístění**: Zákon o výstavbe; Vyhláška Ministerstva vnútra Slovenskej republiky o zabezpečení stavieb vodou na hasenie p; Gas-Information Nr. 20 — Umsetzung der Homogenbereiche nach DIN 18300 im Erdbau für die Ve; ISO 13315-2 — Environmental management for concrete and concrete structures — Part 2: Syst; STN EN 15001-1 — Plynárenská infraštruktúra. Plynovody s prevádzkovým tlakom väčším ako 0,
* **Energetika a trh s plynem a vodíkem**: STN EN IEC 62282-8-301 — Technológia palivových článkov. Časť 8-301: Systémy na akumuláciu; Státní energetická koncepce České republiky (2015); Nařízení Evropského parlamentu a Rady (EU) 2023/955 ze dne 10. května 2023 o vnitřním trhu; (EU) 2019/942 - REGULATION OF THE EUROPEAN PARLIAMENT AND OF THE COUNCIL of 5 June 2019 es; VDE-AR-N 4105 — Generators connected to the low-voltage distribution network – Technical r
* **Životní prostředí, emise a klima**: ISO 14025 — 2026 - Environmental statements and programmes for products — Environmental pr; EN 1717 — Protection against pollution of water intended for human consumption in potable ; Směrnice Evropského parlamentu a Rady 2014/52/EU ze dne 16. dubna 2014 , kterou se mění sm; VDI 3783 Blatt 1 — Umweltmeteorologie - Ausbreitung von störfallbedingten Freisetzungen; ASTM D 7649 — Standard Test Method for Determination of Trace Carbon Dioxide, Argon, Nitro
* **Strategie, koncepce a studie**: SDĚLENÍ KOMISE EVROPSKÉMU PARLAMENTU, RADĚ, EVROPSKÉMU HOSPODÁŘSKÉMU A SOCIÁLNÍMU VÝBORU A; Legislativní a politicko-strategický rámec EU s vlivem na rozvoj vodíkové mobility (2023/2; Studie – Využití vodíkového pohonu v dopravě v České republice (2017); FDI Report Energie budoucnosti (H1 2024); Katalog studijních oborů českých vysokých škol v oblasti vodíku (2025/2026)
* **Dokumenty obecné povahy**: CGA G-5 — Hydrogen; 455/1991 Sb. Živnostenský zákon; EIGA DOC 247 — DOC 247 / 24 - Hydrogen Overview - Distribution-Storage-Applications; 353/2003 Sb. Zákon o spotřebních daních; Gas-Information Nr. 15 — Leitfaden Dokumentation
* **Oblast dosud neurčena**: Rozhodnutí Komise ze dne 22. prosince 1999 o přenosných nemocích, které musí být postupně ; ASTM D 1141 — Standard Practice For Preparation Of Substitute Ocean Water; Směrnice Rady 2000/78/ES ze dne 27. listopadu 2000, kterou se stanoví obecný rámec pro rov; Směrnice Evropského parlamentu A Rady 2002/14/ES ze dne 11. března 2002, kterou se stanoví; Oznámenie Ministerstva dopravy, pôšt a telekomunikácií Slovenskej republiky o vydaní výnos

## 3. Pravidla přiřazení (`data/areas.json`)

**Zpřesnění (22.11.2026 večer):** Kontrola vzorků ukázala, že zdrojová klíčová slova tabulky
prof. Sinaye a sekce rešerší doc. Prokopa / dr. Haltufa (např. „Schienenfahrzeuge“,
„Explosionsschutz“, „Stationäre und ortsbewegliche Druckbehälter“, „Untertage Gasspeicher“,
„Verflüssigung“, „A - výroba“, „Využití - ŽD“) jsou **kategorie celých skupin dokumentů**,
ne vlastnosti dokumentu: „Schienenfahrzeuge“ nesly i normy plnicích stanic, měděných armatur nebo
hořáků, „Untertage Gasspeicher“ i normy ocelových trubek, „A - výroba“ i směrnice o tlakových
zařízeních. Tyto hodnoty (61) proto vedeme v seznamu `group_categories` (do 25.11.2026 `source_categories`)
a oblast z nich neurčujeme.
Pravidla přiřazení píšeme tak, aby oblast seděla s obsahem dokumentu. Dnes obsah poznáváme hlavně
z názvu, protože anotace a plné texty máme jen u části dokumentů a pravidla nad nimi zatím přidávají
příliš šumu (odstavec 8). Raději přiřadíme méně oblastí než šum (průměr klesl z 2,41 na 1,46 oblasti
na dokument).

Oblast určujeme v tomto pořadí:

1. **Kategorie zdrojových rešerší jen tam, kde popisují samotný dokument** — `categories` (do 25.11.2026
   `keywords`): třídy ČSN („6972 - Kryogenické
   nádoby“), okruhy, které editor zvolí při přijetí kandidáta (`app/candidates_admin.py`), několik vydavatelů
   s jednoznačným zaměřením (OIML → metrologie, IMO a CESNI → lodní doprava, DGUV/BAuA/OSHA → BOZP);
   `committee_rules`: technická komise, která normu vydala (ISO/TC 58 a CEN/TC 23 → tlakové nádoby,
   IEC/TC 31 → výbuch, IEC/TC 9 a CEN/TC 256 → železnice …). Hodnoty v `group_categories` a `ignore`
   oblast neurčují. Neznámou hodnotu vypíše `assign_areas.py` a hlídá ji `tests/test_areas.py`.
2. **Výčet označení** — `identifiers`: dokumenty obecné povahy (odstavec 6).
3. **Typ dokumentu** — `type_rules`: strategie a studie zařadíme do „Strategie, koncepce a studie“.
4. **Název a označení** — `title_rules`: regulární výrazy v češtině, slovenštině, angličtině a němčině; volba
   `unless` pravidlo vyloučí (silniční vozidla nepřiřadíme, jde-li o kolejová vozidla; plnicí stanice ne u benzinových
   par; „Výroba vodíku jinými postupy“ ne u elektrolýzy). Železnici přiřadíme jen podle názvu: železnice,
   drážní, dráhy, kolejová vozidla, railway, TSI, interoperabilita, Eisenbahn.
5. Dokument, kterému žádné pravidlo nic nepřiřadí, dostane pracovní oblast „Oblast dosud neurčena“
   (`--uncertain` je vypíše). LLM nepoužíváme.

## 4. Co se stalo s kategoriemi zdrojových rešerší

Hodnoty, které pole „Oblast (klíčové slovo)“ dosud nabízelo, nejsou klíčová slova dokumentu, ale kategorie
převzaté ze zdrojových rešerší. Proto jsme 25.11.2026 přejmenovali tabulky `Keyword` a `DocumentKeyword` na
**`SourceCategory`** a **`DocumentSourceCategory`** (sloupce `name` a `category_id`; řádky i jejich id zůstaly,
převod dělá `src/tools/migrate_vocabulary.py`, doc/KLICOVA_SLOVA.md odstavec 4). Klíčová slova dokumentu
vedeme odděleně v tabulkách `Term` a `DocumentTerm`.

Kategorie **nemažeme**: prohledává je vyhledávání v katalogu (dotaz „Befüllungsanlagen“ dál najde příslušné
normy) a obsahují je exporty CSV/JSON/XML (pole `source_categories`, do 25.11.2026 `keywords`). Jen je
nenabízíme ve filtru a nezobrazujeme ve štítcích. *Důvod:* nesou informaci ze zdrojových rešerší (vydavatel,
technická komise, stav STN), kterou oblasti nenahrazují, a mapování z nich můžeme kdykoli přepočítat.
Filtr podle kategorie má parametr `?category_id=…`; starý odkaz `?keyword_id=…` aplikace přesměruje
na `?category_id=…` se stejným číslem (export parametr přijme přímo).

Oblasti ukládáme do tabulek `Area` (kód, název, okruh, pořadí, veřejná ano/ne) a `DocumentArea` (dokument,
oblast, původ: `category`, `identifier`, `type`, `title`, `fallback`; původ `category` se do 25.11.2026
jmenoval `keyword` a `assign_areas.py --apply` ho přepíše). Dokud v databázi nejsou, aplikace ukazuje
kategorie zdrojových rešerší.

## 5. Údržba

* `src/tools/assign_areas.py` — běh nanečisto vypíše rozpad; `--apply` oblasti zapíše; `--uncertain` vypíše
  dokumenty s oblastí dosud neurčenou. Skript je idempotentní; spouštíme ho po přestavbě databáze (`init_db.py`)
  a po každé změně `data/areas.json`.
* Při přijetí kandidáta aplikace přiřadí novému dokumentu oblasti hned (`areas.assign_document()`).
* Testy: `tests/test_areas.py` (soubor, pravidla, zápis), `tests/e2e/test_areas.py` (filtr, stránka dokumentu,
  hledání ve skrytých kategoriích, starý odkaz `?keyword_id=`). `run_tests.py` zapisuje oblasti do testovací
  databáze (`TEST_DB_MIGRATIONS`, po `migrate_vocabulary.py`).

## 6. Dokumenty obecné povahy a oblast dosud neurčena

Dřívější náhradní oblast „Obecné a průřezové předpisy“ spojovala dvě různé skupiny. Rozdělili jsme ji:

* **„Dokumenty obecné povahy“** (veřejná oblast, 5 dokumentů): dokumenty, které se týkají vodíku nebo podnikání
  s ním jako celku a žádné věcné oblasti nepatří — CGA G-5 (Hydrogen), EIGA DOC 247 (Hydrogen Overview),
  DVGW Gas-Information Nr. 15, zákon o spotřebních daních, živnostenský zákon. Vedeme je výčtem označení
  (`identifiers`), ne pravidlem, aby do oblasti nepadaly dokumenty jen proto, že je pravidla neumějí zařadit.
* **„Oblast dosud neurčena“** (pracovní oblast, 65 dokumentů): dokumenty, kterým žádné pravidlo oblast nepřiřadí.
  Jde o pracovní seznam pro editory, ne o vlastnost dokumentu. Proto ji **nenabízíme ve veřejném filtru
  a návštěvníkům ji nezobrazujeme ani jako štítek**: štítek by návštěvníkovi nic neřekl o obsahu a u předpisů mimo
  rozsah by sliboval, že je někdo zařadí. Přihlášený editor štítek v seznamu i na stránce dokumentu vidí
  (`Area.public = 0`, `app/app.py`, `area_tags()`), seznam celý vypíše `assign_areas.py --uncertain`.

Souhrn návrhů k 65 dokumentům v oblasti dosud neurčené (tabulka níže): 42 mimo rozsah databáze (pracovní právo,
rovné zacházení, přenosné nemoci, lasery, laboratorní voda, potraviny) navrhujeme posoudit k vyřazení přes
`data/manual_corrections.json` (`"exclude": true`; nic automaticky nemažeme), u 18 pravidel DVGW bez názvu
(záznam nese jen „Guideline G 404“) doplníme název a oblast pak určí pravidla, 2 poškozené záznamy opravíme
nebo vyřadíme, u 2 aktů EU doplníme úplný název z Cellaru a 1 dokument (2021/1187/EU, transevropská dopravní síť)
zařadíme ručně.

| # | Označení | Název | Návrh |
|---|---|---|---|
| 62 | 2010/75/EU | Oznámenie Ministerstva dopravy, pôšt a telekomunikácií Slovenskej republiky o vydaní výnosu o m | mimo rozsah: slovenské oznámení o výnosu (název zkomolený, chybné označení 2010/75/EU) — k posouzení vyřazení |
| 91 | (EU) 2021/535 | Nařízení Komise (EU) 2021/535 ze dne 31. března 2021, kterým se mění nařízení (ES) č. 1881/2006 | mimo rozsah: kontaminanty v potravinách (nařízení 1881/2006) — k vyřazení |
| 385 | / - 2024.08 | / - 2024.08 — kombinovanými úrovňami ochrany | poškozený záznam (název je zbytek řádku) — opravit nebo vyřadit |
| 445 | STN EN ISO 17526/ - 2003.12 | STN EN ISO 17526 — Optika a optické prístroje. Lasery a laserové zariadenia. Životnosť laserov  | mimo rozsah: lasery — k vyřazení |
| 472 | STN EN ISO 3696/ - 2000.02 | STN EN ISO 3696 — Kvalita vody na analytické účely. Špecifikácia a skúšobné metódy (ISO 3696:19 | mimo rozsah: voda pro laboratoře — k vyřazení |
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
| 1077 |  | je možné nájsť na stránkach jednotlivých technických komisií CEN, CENELEC, | poškozený záznam (název je věta z poznámky) — opravit nebo vyřadit |
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

## 7. Elektrolýza, plnicí stanice, doprava vodíku (23.11.2026)

Ověřili jsme, zda dokážeme spolehlivě poznat tři oblasti, které uživatel navrhl. Pravidla jsme testovali na
názvech; technické komise ISO/TC 197 (vodíkové technologie obecně) a IEC/TC 105 (palivové články) oblast
nerozliší, třídy ČSN pro tyto oblasti v databázi nemáme (kromě „3360 - Technologie palivových článků“).

* **Elektrolýza** — 10 dokumentů (ISO 22734 a jeho návrhy, DIN EN ISO 22734, ČSN EN 60335-2-108 o elektrolyzérech
  pro domácnost, VDI 4635 Blatt 3.1, DVGW MB 12 Wasser-Elektrolyseanlagen, instrukce MPO k živnostenskému oprávnění,
  případová studie výstavby elektrolyzéru). Šum ve vzorku 0 z 10. Chybí: H2.22 (certifikační program pro
  elektrolyzéry má v názvu překlep „elctrolyzer“) a dokumenty, které elektrolýzu zmiňují jen v anotaci.
  **Zavedli jsme ji jako samostatnou oblast**; oblast „Výroba vodíku“ jsme zúžili na „Výroba vodíku jinými postupy“
  (11 dokumentů: reformování, PSA, generátory s úpravou paliva), aby se elektrolýza nepočítala dvakrát.
* **Plnicí stanice** — stávající oblast obsahovala už téměř jen vodíkové plnicí stanice a AFIR (69 dokumentů:
  řada ISO 19880, ISO 17268, SAE J2601/J2600, CSA HGV 4.x, ISO 19885, EN 17127, TRBS 3151). Šum ve vzorku 0 z 10
  po vyloučení směrnice 2009/126/ES o benzinových parách. **Přejmenovali jsme ji na „Plnicí stanice“**; AFIR a akty
  k infrastruktuře alternativních paliv v ní ponecháváme, protože upravují právě síť plnicích stanic.
* **Doprava vodíku** — pravidlo jen s výrazem „transport“ a slovem vodík dávalo 35 dokumentů s velkým šumem
  (permeace vodíku v kovech, emise skleníkových plynů „…transport…“). Spolehlivější je **sloučit** dřívější oblasti
  „Plynovody a plynárenské sítě“ a „Přeprava nebezpečných věcí“: obě jsme už vzorkovali a dohromady pokrývají
  plynovody a sítě (včetně vtláčení vodíku), přepravitelné lahve a svazky, ADR/RID/ADN a lodní přepravu
  zkapalněného vodíku. Nová oblast „Doprava vodíku (plynovody, sítě, přeprava)“ má 162 dokumentů; ve vzorku
  10 dokumentů je 1 zjevně mimo (ISO 16530-1 o integritě vrtů) a 1 sporný (bunkrování LNG), šum odhadujeme
  na 10–15 %. Normy plynovodů pro zemní plyn v oblasti ponecháváme, protože vodík se do plynárenských sítí přimíchává
  (směrnice (EU) 2024/1788). Tube trailery a návěsy v názvech dokumentů v databázi nejsou; pokrýváme je přes
  přepravitelné lahve, svazky a ADR.

## 8. Úkol: oblasti i z obsahu dokumentu

**Dnešní stav:** oblast určujeme podle názvu a označení a podle několika druhů kategorií zdrojových rešerší
(odstavec 3).
Pro danou oblast ale může být relevantní i obsah dokumentu, který se v názvu neobjeví.

**Úkol:** doplníme oblasti z obsahu. Podklady máme: anotaci má 838 norem (celkem 967 dokumentů s popisem),
plné texty asi 300 předpisů, akty EU mají deskriptory EuroVoc (Cellar) a normy třídění ICS. Postup: nejdřív
zmapujeme EuroVoc a ICS na oblasti (strukturované, s malým šumem), potom vyzkoušíme pravidla nad anotací
s přísnějšími výrazy a s vyšší vahou výskytu v úvodní větě anotace, každou novou vazbu označíme původem
(`annotation`, `eurovoc`, `ics`) a vzorek zkontrolujeme dřív, než pravidla zapneme.

**Měření (23.11.2026, jen běh nanečisto, pravidla jsme nezměnili):** stávající pravidla názvu jsme pustili i na
anotaci (`description`, `popis_autoritativni`). Ze 967 dokumentů s anotací přibude oblast u 418 dokumentů
(672 nových vazeb; nejvíc Materiály 75, Komponenty 64, Životní prostředí 58, Kvalita a měření 40, Doprava vodíku 37,
Tlakové nádoby 37); z oblasti dosud neurčené zařadí 16 dokumentů. Ve vzorku 10 dokumentů (17 nových vazeb)
sedí obsahu 9 vazeb, šum je tedy kolem 45 %:

| Dokument | Nově přidané oblasti | Hodnocení |
|---|---|---|
| IGC Doc 114/03/E — Operation of static cryogenic vessels | Tlakové nádoby, Doprava, Výbuch, Bezpečnost, Životní prostředí | 2 z 5 (výbuch, bezpečnost); zbytek z věty o výjimkách |
| STN EN 60079-29-3 — Detektory plynu, funkčná bezpečnosť | Řídicí systémy | sedí |
| ISO/AWI 22734-1 — elektrolyzéry | Spotřebiče | nesedí („appliances“ ve významu zařízení) |
| IEC/TS 62443-1-5 — informační bezpečnost | Posuzování shody | nesedí (zmínka v závorce) |
| Sdělení Komise o Evropské vodíkové bance | RFNBO, Energetika | sedí |
| STN EN 1514-1 — Příruby, rozměry těsnění | Materiály | nesedí („typickým materiálům“) |
| ISO/AWI 19882 — tlakové pojistky pro nádrže vozidel | Palivové články, Elektrárny | nesedí (zmínka o čistotě paliva a spalovacích motorech) |
| VDI 4635 Blatt 1.2 — Power-to-X, systemic aspects | Výroba jinými postupy, Životní prostředí | 1 ze 2 (výroba) |
| API 5L PSL 1 — Line pipe | Doprava vodíku, Materiály | sedí |
| ISO 11114-1 — kompatibilita materiálů lahví | Doprava vodíku | sedí (přepravitelné lahve) |

Závěr měření: pravidla názvu pustit na anotaci beze změny nemůžeme. Šum vzniká z vedlejších zmínek (výjimky z rozsahu,
odkazy na jiné dokumenty, obecná slova „materials“, „appliances“). Pro anotace připravíme samostatná, užší pravidla
a začneme strukturovanými údaji EuroVoc a ICS.
