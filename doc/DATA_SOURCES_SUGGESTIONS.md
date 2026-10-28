# Katalog informačních zdrojů pro databázi vodíkových regulatorních dokumentů

**Projekt:** NAHYC – DP004, Vodíkový technologický inkubátor  
**Účel dokumentu:** Specifikace informačních zdrojů pro vyhledávání, evidenci a průběžnou aktualizaci regulatorních dokumentů vztahujících se k vodíkovým technologiím  
**Verze:** 1.0  
**Stav rešerše a ověření hlavních portálů:** 28. října 2026  
**Primární geografické zaměření:** Česká republika a Evropská unie; podle potřeby mezinárodní a zahraniční podklady

## 1. Cíl a vymezení

Cílem je vytvořit udržovaný **registr informačních zdrojů**, na jejichž základě lze sestavovat a aktualizovat databázi právních předpisů, technických norem, metodik, správních postupů a dalších regulatorně významných podkladů pro **přípravu, výstavbu, instalaci, schvalování, provoz, údržbu a kontrolu vodíkových zařízení**.

Tematické pokrytí zahrnuje zejména:

- výrobu vodíku (elektrolýza, jiné výrobní technologie, návaznost na energetiku a životní prostředí);
- skladování vodíku (tlakové a kryogenní systémy, tlakové lahve, zásobníky a související bezpečnost);
- přepravu a distribuci (silnice, železnice, plynovody, případně vodní doprava);
- výstavbu a provoz stacionárních a mobilních vodíkových plnicích stanic;
- vodíková vozidla, jejich homologaci, provoz, servis, parkování a technické prohlídky;
- kvalitu vodíku jako paliva, metrologii, odběr vzorků a kontrolní postupy;
- požární bezpečnost, ochranu před výbuchem, vyhrazená technická zařízení a BOZP;
- povolování staveb, EIA/SEA, integrovanou prevenci a případné další environmentální požadavky.

**Předmětem tohoto dokumentu jsou zdroje, nikoli úplný soupis jednotlivých předpisů.** Uvedená tematická relevance neznamená, že se na každou vodíkovou instalaci musí vztahovat všechny dokumenty daného zdroje.

## 2. Klasifikace zdrojů a způsob čtení katalogu

### 2.1 Role informačního zdroje

- **P – primární právní zdroj:** oficiální vyhlašování nebo autoritativní evidence právních aktů a jejich znění.
- **L – legislativní proces:** návrhy, připomínky, jednání, pozměňovací návrhy a připravované změny.
- **N – normativní/technický zdroj:** technické normy, technická pravidla a jejich katalogy.
- **M – metodický/regulatorní zdroj:** výklady, postupy, metodiky a informace kompetentních orgánů.
- **E – evidence rozhodnutí/případů:** správní řízení, povolení, posuzování záměrů a příklady aplikace předpisů.
- **S – sekundární odborný zdroj:** studie, doporučení, bezpečnostní návody a tematické rozcestníky.

Jeden portál může plnit více rolí. **Právní závaznost jednotlivého dokumentu se určuje samostatně**; nezařazuje se podle samotného provozovatele webu.

### 2.2 Priority

| Priorita | Význam | Navržený režim |
|---|---|---|
| **A – nezbytný** | Bez zdroje by bylo regulatorní pokrytí výrazně neúplné. | Zařadit do první vlny a nastavit průběžné monitorování. |
| **B – vysoká** | Zdroj významně rozšiřuje tematické pokrytí nebo umožňuje validovat údaje. | Zařadit do druhé vlny; kontrolovat pravidelně. |
| **C – doplňková** | Především metodický, srovnávací či úzce specializovaný přínos. | Rešerše podle tematické potřeby. |

### 2.3 Způsoby získávání dat

- **API – doloženo:** oficiálně zdokumentovaný strojový přístup (případně s registrací).
- **WEB – ověřit:** veřejné webové vyhledávání a dokumenty; dostupnost API, strojové extrakce či licenčních podmínek se musí ověřit při implementaci.
- **KATALOG / LICENCE:** zpravidla veřejná metadata, ale plné texty mohou být licencované nebo placené.
- **MANUÁLNĚ:** zejména specializované metodiky a jednotlivé publikace.

**Pozor:** Hodnota `WEB – ověřit` není tvrzením, že neexistuje API. Znamená pouze, že jeho existence a provozní podmínky nebyly pro tento katalog potvrzeny. Odkazy představují vstupní místa; hlubší podstránky a jejich adresy se mohou změnit.

## 3. Česká legislativa a legislativní proces

| ID | Zdroj / URL | Role | Co vyhledávat a proč | Priorita | Získávání dat |
|---|---|---|---|---|---|
| **CZ-01** | **e-Sbírka** – https://e-sbirka.gov.cz/ | P | Vyhlašované české zákony, vyhlášky, nařízení vlády a mezinárodní smlouvy; časová znění, novelizace a zrušení. Základ pro autoritativní evidenci českého práva. | **A** | **API – doloženo**, registrace a klíč; též web a otevřené formáty. |
| **CZ-02** | **e-Legislativa** – https://e-legislativa.gov.cz/ | L | Návrhy právních předpisů, fáze projednávání a dostupné verze. Důležité je přechodné období, kdy část návrhů pokračuje ve starších systémech. | **A** | **API – doloženo**, společná registrace s e-Sbírkou; web. |
| **CZ-03** | **ODok / VeKLEP** – https://odok.cz/portal/veklep/ | L | Vládní legislativní návrhy, meziresortní připomínkové řízení, připomínky a vypořádání, zejména u návrhů sledovaných starším postupem. | **A** | WEB – ověřit. |
| **CZ-04** | **Poslanecká sněmovna PČR – sněmovní tisky** – https://www.psp.cz/sqw/tisky.sqw | L | Sněmovní tisky, pozměňovací návrhy, usnesení výborů, průběh projednávání. | **B** | WEB – ověřit. |
| **CZ-05** | **Senát PČR** – https://www.senat.cz/ | L | Senátní tisky, projednávání návrhů a usnesení; doplnění legislativního životního cyklu. | **B** | WEB – ověřit. |
| **CZ-06** | **Sbírka právních předpisů územních samosprávných celků a některých správních úřadů** – https://sbirkapp.gov.cz/ | P | Právní předpisy obcí, krajů a vybraných správních úřadů; relevantní zejména při místní analýze konkrétní instalace. | **B** | WEB – ověřit; dostupné vyhledávání a notifikace. |

**Poznámka k CZ-02:** Povinné využití e-Legislativy bylo zavedeno postupně; novely zákonů přecházejí na tento režim až od **15. ledna 2027**. Při rešerši probíhajících legislativních procesů proto nelze předpokládat, že jeden portál pokrývá všechny návrhy.

## 4. Evropská legislativa, připravované akty a energetická regulace

| ID | Zdroj / URL | Role | Co vyhledávat a proč | Priorita | Získávání dat |
|---|---|---|---|---|---|
| **EU-01** | **EUR-Lex** – https://eur-lex.europa.eu/ | P, L | Nařízení, směrnice, rozhodnutí, delegované a prováděcí akty, Úřední věstník EU, konsolidovaná znění, změnové vazby, dokumenty přípravného procesu a národní transpoziční opatření. | **A** | **API – doloženo**: Cellar REST/SPARQL; další datové služby. |
| **EU-02** | **Legislative Observatory (OEIL), Evropský parlament** – https://oeil.secure.europarl.europa.eu/oeil/ | L | Stav evropských legislativních postupů, pozměňovací návrhy, stanoviska a průběh projednávání. | **B** | WEB – ověřit. |
| **EU-03** | **Veřejný registr dokumentů Rady EU** – https://www.consilium.europa.eu/en/documents/public-register/ | L | Podklady pracovních skupin a přípravné dokumenty Rady EU, vazby přes meziinstitucionální čísla spisů. | **B** | WEB – ověřit. |
| **EU-04** | **Comitology Register** – https://ec.europa.eu/transparency/comitology-register/ | L | Výbory komitologie, návrhy **prováděcích** aktů, podklady jednání a výsledky hlasování. | **B** | WEB – ověřit. |
| **EU-05** | **Interinstitutional Register of Delegated Acts** – https://webgate.ec.europa.eu/regdel/ | L | Návrhy a projednávání **delegovaných** aktů. Jde o odlišnou agendu od komitologie. | **B** | WEB – ověřit. |
| **EU-06** | **Have Your Say / Better Regulation** – https://ec.europa.eu/info/law/better-regulation/have-your-say_en | L | Připravované iniciativy Evropské komise, veřejné konzultace, posouzení dopadů a návrhy změn. | **B** | WEB – ověřit. |
| **EU-07** | **TRIS – Technical Regulation Information System** – https://technical-regulation-information-system.ec.europa.eu/en/home | L | Oznámené návrhy národních technických předpisů členských zemí EU; předběžný signál budoucích změn. | **B** | WEB – ověřit; ověřit nastavení upozornění. |
| **EU-08** | **Register of Commission Documents** – https://ec.europa.eu/transparency/documents-register/ | L, M | Návrhy, posouzení dopadů, pracovní dokumenty, sdělení, rozhodnutí a další materiály Komise. | **B** | WEB – ověřit. |
| **EU-09** | **Evropská komise – DG ENER, Hydrogen and Decarbonised Gas Market** – https://energy.ec.europa.eu/topics/markets-and-consumers/hydrogen-and-decarbonised-gas-market_en | M, L | Pravidla trhu s vodíkem a dekarbonizovanými plyny, vodíkové sítě, implementace evropského plynárenského balíčku. | **B** | WEB – ověřit. |
| **EU-10** | **ACER** – https://www.acer.europa.eu/ | M | Stanoviska, doporučení, monitorování a regulatorní analýzy energetických trhů a přeshraniční infrastruktury. | **C** | WEB – ověřit. |

**Pravidlo:** U právních aktů EU je preferovaným zdrojem jejich znění **EUR-Lex**. Ostatní portály poskytují především informace o přípravě, změnách a aplikaci právních aktů. Pro transpozici je třeba evidovat vazbu `směrnice EU → národní prováděcí předpis(y)` a skutečný stav provedení, nikoli pouze termín transpozice.

## 5. Technické normy, harmonizované normy a pravidla

| ID | Zdroj / URL | Role | Co vyhledávat a proč | Priorita | Získávání dat |
|---|---|---|---|---|---|
| **STD-01** | **Česká agentura pro standardizaci (ČAS) / ČSN online** – https://agenturacas.gov.cz/produkty-a-sluzby/csn-online/ | N | Metadata ČSN a TNI, označení, názvy, platnost, změny, náhrady a dostupnost českých převzetí EN/ISO/IEC. | **A** | **KATALOG / LICENCE**; katalogové vyhledávání je dostupné, plné texty zpravidla na předplatné. |
| **STD-02** | **Věstník ÚNMZ** – https://unmz.gov.cz/obecne/vestnik-unmz/ | N, M | Oznámení o vydání, změně, opravě a zrušení ČSN; harmonizované a určené normy, metrologická oznámení. | **A** | WEB/PDF – ověřit. |
| **STD-03** | **Evropská komise – Harmonised Standards** – https://single-market-economy.ec.europa.eu/single-market/goods/european-standards/harmonised-standards_en | N, P | Odkazy na harmonizované normy zveřejněné v Úředním věstníku EU; zejména ATEX, tlaková zařízení (PED), strojní zařízení a měřidla (MID). | **A** | WEB – ověřit; podle oblastí dostupná shrnutí a odběr novinek. |
| **STD-04** | **CEN/CENELEC – Hydrogen** – https://www.cencenelec.eu/areas-of-work/cenelec-sectors/energy-and-utilities-cenelec/hydrogen/ | N | Evropské technické komise, standardizační agenda a připravované evropské normy pro vodíkové technologie. | **B** | KATALOG / LICENCE. |
| **STD-05** | **ISO/TC 197 – Hydrogen Technologies** – https://www.iso.org/committee/54560.html | N | Mezinárodní standardizace výroby, skladování, přepravy, měření a použití vodíku; pracovní program a publikované normy. | **A** | KATALOG / LICENCE. |
| **STD-06** | **IEC Webstore** – https://webstore.iec.ch/ | N | Elektrotechnické normy, zařízení do výbušného prostředí, elektrická bezpečnost a palivové články. | **B** | KATALOG / LICENCE. |
| **STD-07** | **Český plynárenský svaz – technická pravidla TPG** – https://cgoa.cz/to.normativni-dokumenty/platna-tpg | N | Technická pravidla a doporučení plynárenství, včetně bezpečnosti, distribuce, potrubí a případných změn relevantních pro vodík. | **B** | KATALOG / LICENCE; ověřit podmínky jednotlivých textů. |
| **STD-08** | **SAE MOBILUS** – https://saemobilus.sae.org/ | N | Automobilové technické normy a doporučení, vodíkové palivové soustavy, plnění a provoz vozidel. | **C** | KATALOG / LICENCE. |

**Právní upozornění:** Norma není automaticky obecně závazným právním předpisem. Databáze musí rozlišovat (i) technické normy obecně používané dobrovolně, (ii) harmonizované normy umožňující za daných podmínek presumovat shodu a (iii) povinnosti vznikající přímým odkazem právního předpisu, rozhodnutím či jiným závazným mechanismem. **Odkaz na normu ve Věstníku ÚNMZ nebo v katalogu sám o sobě nenahrazuje analýzu jejího právního účinku.**

## 6. České kompetentní orgány: energetika, stavby, bezpečnost a životní prostředí

| ID | Zdroj / URL | Role | Co vyhledávat a proč | Priorita | Získávání dat |
|---|---|---|---|---|---|
| **REG-01** | **Ministerstvo průmyslu a obchodu (MPO)** – https://mpo.gov.cz/ | M, L | Vodíkové strategie a koncepce, předpisy k energetice, výrobě a distribuci vodíku, pohonné hmoty, technická regulace a transpozice. | **A** | WEB – ověřit. |
| **REG-02** | **Energetický regulační úřad (ERÚ)** – https://eru.gov.cz/ | M | Regulace plynárenství a energetiky, vyhlášky, pravidla trhu, licence, cenová rozhodnutí, metodická stanoviska. | **B** | WEB – ověřit. |
| **REG-03** | **Ministerstvo pro místní rozvoj (MMR)** – https://mmr.gov.cz/cs/ministerstvo/stavebni-pravo | M | Stavební právo, prováděcí předpisy a metodiky pro umístění a povolování technologických celků. | **A** | WEB – ověřit. |
| **REG-04** | **Ministerstvo životního prostředí (MŽP)** – https://mzp.gov.cz/ | M | EIA/SEA, ochrana ovzduší a vod, prevence závažných havárií, průmyslové emise, odpady a související metodiky. | **A** | WEB – ověřit. |
| **REG-05** | **Technická inspekce České republiky (TIČR)** – https://www.ticr.eu/ | M | Odborné informace o vyhrazených technických zařízeních, tlakových a plynových zařízeních, odborné způsobilosti a přezkušování. **Není vydavatelem obecně závazných vyhlášek.** | **A** | WEB – ověřit. |
| **REG-06** | **Hasičský záchranný sbor ČR (HZS)** – https://hzscr.gov.cz/ | M | Požární prevence, požární bezpečnost staveb, věstníky, metodické materiály a stanoviska. | **A** | WEB/PDF – ověřit. |
| **REG-07** | **Státní úřad inspekce práce (SÚIP)** – https://suip.gov.cz/ | M | BOZP, bezpečnost práce s tlakovými a plynovými zařízeními, výbušná prostředí a kontrolní doporučení. | **B** | WEB – ověřit. |
| **REG-08** | **CENIA – IPPC a integrovaná prevence** – https://cenia.gov.cz/odborna-podpora/ippc/ | M, E | České informace o integrovaném povolování, BAT/BREF a souvisejících správních postupech. | **B** | WEB – ověřit. |
| **REG-09** | **Informační systém EIA/SEA** – https://portal.cenia.cz/eiasea/ | E | Dokumentace konkrétních záměrů, závěry zjišťovacích řízení, stanoviska a empirické příklady povolovacích procesů. | **B** | WEB – ověřit. |
| **REG-10** | **European IPPC Bureau (EIPPCB, JRC)** – https://eippcb.jrc.ec.europa.eu/reference | M, N | Evropské referenční dokumenty BREF a související BAT pro průmyslové technologie podle relevantnosti. | **B** | WEB/PDF – ověřit. |
| **REG-11** | **Česká inspekce životního prostředí (ČIŽP)** – https://www.cizp.gov.cz/ | M, E | Výkladové a kontrolní informace k environmentálním povinnostem provozovatelů; doplňkově výsledky kontrol. | **C** | WEB – ověřit. |

**Zásada:** U institucí, které poskytují odborná stanoviska nebo metodiky (např. TIČR, HZS, SÚIP), se musí uchovat rozdíl mezi **právním předpisem**, **úřední metodikou**, **nezávazným odborným stanoviskem** a **individuálním správním aktem**. Originální znění českého právního předpisu se eviduje přes CZ-01.

## 7. Doprava, přeprava nebezpečných věcí a homologace

| ID | Zdroj / URL | Role | Co vyhledávat a proč | Priorita | Získávání dat |
|---|---|---|---|---|---|
| **TR-01** | **Ministerstvo dopravy ČR – ADR** – https://md.gov.cz/Zivotni-situace/Silnicni-doprava/Nakladni-doprava-%281%29/Preprava-nebezpecnych-veci-dohoda-adr | P, M | České znění a související informace k silniční přepravě nebezpečných věcí, odborná stanoviska a mnohostranné dohody. | **A** | WEB/PDF – ověřit. |
| **TR-02** | **UNECE – Dangerous Goods** – https://unece.org/transport/dangerous-goods | P, M | ADR, modelové předpisy OSN pro nebezpečné věci, změny pravidel a technické dokumenty; důležité pro transport stlačeného i zkapalněného vodíku. | **A** | WEB/PDF – ověřit. |
| **TR-03** | **OTIF** – https://otif.org/ | P, M | RID a jeho aktualizace pro mezinárodní železniční přepravu nebezpečných věcí. | **A** | WEB/PDF – ověřit. |
| **TR-04** | **Drážní úřad ČR – RID** – https://du.gov.cz/potrebuji-si-vyridit/rid-preprava-nebezpecnych-veci/ | M | České materiály k RID, metodické pokyny, schvalování cisteren a inspekční organizace. | **B** | WEB/PDF – ověřit. |
| **TR-05** | **UNECE – WP.29 / Vehicle Regulations** – https://unece.org/transport/vehicle-regulations | P, N | Homologační předpisy OSN pro vozidla a komponenty vodíkových palivových soustav. | **A** | WEB/PDF – ověřit. |
| **TR-06** | **European Union Agency for Railways (ERA)** – https://www.era.europa.eu/ | M, N | Technické specifikace interoperability, schvalování drážních vozidel a železniční bezpečnost. | **B** | WEB – ověřit. |
| **TR-07** | **Ministerstvo dopravy ČR – drážní oblast** – https://md.gov.cz/ | M | Česká železniční legislativa, mezinárodní dokumenty a správní postupy související s vodíkovými vozidly a provozem. | **B** | WEB – ověřit. |
| **TR-08** | **IMO – International Maritime Organization** – https://www.imo.org/ | N, M | IMDG Code a další bezpečnostní pravidla pro námořní přepravu nebezpečných věcí; pouze pro případy zahrnující námořní dopravu. | **C** | KATALOG / LICENCE / WEB. |

Pro **vnitrozemskou vodní dopravu** lze podle rozsahu další fáze doplnit také předpis **ADN** prostřednictvím agendy nebezpečných věcí UNECE. Přeprava silniční, železniční a vodní nemá být v databázi sloučena pod jediné nerozlišené „ADR/RID“.

## 8. Chemická bezpečnost, metrologie, paliva a posuzování shody

| ID | Zdroj / URL | Role | Co vyhledávat a proč | Priorita | Získávání dat |
|---|---|---|---|---|---|
| **Q-01** | **ECHA CHEM / European Chemicals Agency** – https://echa.europa.eu/information-on-chemicals | M, E | Informace o chemických látkách a regulatorních procesech REACH/CLP, klasifikaci a označování; také pomocné chemické látky a nosiče vodíku. | **A** | WEB – ověřit možnosti legálního datového přístupu a opakovaného užití. |
| **Q-02** | **Český metrologický institut (ČMI)** – https://cmi.gov.cz/node/212 | M, P | Opatření obecné povahy pro stanovená měřidla, jejich ověřování a relevantní metrologické postupy, zejména u výdeje vodíku. | **A** | WEB/PDF – ověřit. |
| **Q-03** | **Česká obchodní inspekce (ČOI)** – https://coi.gov.cz/ | M | Kontrola jakosti pohonných hmot, požadavky na čerpací stanice a relevantní kontrolní metodiky. | **A** | WEB – ověřit. |
| **Q-04** | **Evropská komise – NANDO** – https://single-market-economy.ec.europa.eu/single-market/goods/building-blocks/notified-bodies_en | E, M | Oznámené subjekty pro posuzování shody podle předpisů, zejména PED, ATEX a další výrobkové regulace. | **B** | WEB – ověřit. |
| **Q-05** | **Český institut pro akreditaci (ČIA)** – https://www.cai.cz/ | E, M | Akreditované zkušební a kalibrační laboratoře, inspekční a certifikační orgány; využití při ověřování metodiky kontroly kvality vodíku. | **B** | WEB – ověřit. |

**Poznámka k ECHA:** Starší databáze ECHA jsou postupně nahrazovány systémem **ECHA CHEM**. Je nutné sledovat aktuální datové služby a licenční podmínky, nikoli automaticky přebírat staré webové adresy pro registrace REACH a klasifikace CLP.

## 9. Odborné, metodické a komparativní zdroje

| ID | Zdroj / URL | Role | Co vyhledávat a proč | Priorita | Získávání dat |
|---|---|---|---|---|---|
| **SUP-01** | **HYTEP – Česká vodíková technologická platforma** – https://www.hytep.cz/ | S, M | Česká vodíková legislativa a strategie, regulatorní analýzy, metodiky a identifikace mezer v právním prostředí. | **B** | WEB / MANUÁLNĚ. |
| **SUP-02** | **European Hydrogen Observatory** – https://observatory.clean-hydrogen.europa.eu/ | S | Přehledy evropských a národních politik a právních rámců; rozcestník k relevantním předpisům, nikoli náhrada jejich originálů. | **B** | WEB – ověřit. |
| **SUP-03** | **European Hydrogen Safety Panel (EHSP)** – https://ehsp.eu/hydrogen-safety-reports/ | S, M | Bezpečnostní metodiky, přehledy *regulations, codes and standards*, hodnocení incidentů a bezpečnostní doporučení. | **B** | WEB/PDF – ověřit. |
| **SUP-04** | **Clean Hydrogen Partnership – referenční dokumenty EHSP** – https://www.clean-hydrogen.europa.eu/get-involved/european-hydrogen-safety-panel-0/reference-documents_en | S, M | Oficiální publikace bezpečnostních doporučení EHSP včetně jejich verzí. Jde o alternativní publikační místo k SUP-03, nikoli samostatnou normotvornou autoritu. | **B** | WEB/PDF – ověřit. |
| **SUP-05** | **European Industrial Gases Association (EIGA)** – https://www.eiga.eu/publications/ | S, N | Bezpečnostní doporučení a pracovní postupy pro výrobu, manipulaci, stlačování, skladování a dopravu průmyslových plynů. | **B** | WEB/PDF; ověřit uživatelská práva k textům. |
| **SUP-06** | **BAuA – Bundesanstalt für Arbeitsschutz und Arbeitsmedizin** – https://www.baua.de/ | S, M | Německé technické a bezpečnostní podklady k BOZP, výbušným prostředím a provozu technologických zařízení. | **C** | WEB/PDF – ověřit. |
| **SUP-07** | **Gesetze im Internet (Německo)** – https://www.gesetze-im-internet.de/ | P (zahraniční) | Znění německých právních předpisů pro komparativní analýzy a interpretaci zahraničních metodik. **Nepoužívat jako zdroj českých právních povinností.** | **C** | WEB – ověřit. |

## 10. Pokrytí a doporučené pořadí implementace

### 10.1 První vlna – nezbytné zdroje

Prioritně integrovat **CZ-01 až CZ-03, EU-01, STD-01 až STD-03, STD-05, REG-01, REG-03 až REG-06, TR-01 až TR-03, TR-05, Q-01 až Q-03**. Právní zdroje zpracovávat přednostně na úrovni identifikátorů a časových verzí, technické normy na úrovni metadat a právních vazeb.

### 10.2 Druhá vlna – cílené doplnění

Doplnit parlamentní a evropské registry, TPG, další resortní portály, EIA/IPPC, Drážní úřad, ERA, NANDO, ČIA, HYTEP a EHSP. Tyto zdroje jsou nezbytné zejména pro detekci mezer a provázání regulace s konkrétními procesy.

### 10.3 Tematická kontrola úplnosti

U každé aplikace vyplnit matici:

| Fáze vodíkového řetězce | Stavební a územní právo | Technická bezpečnost / ATEX / tlak | Životní prostředí | Doprava / homologace | Kvalita / měření |
|---|---|---|---|---|---|
| **Výroba** | Prověřit | Prověřit | Prověřit | Dle případu | Dle použití vodíku |
| **Skladování** | Prověřit | Prověřit | Dle lokality a rozsahu | Dle režimu přepravy | Dle požadované kvality |
| **Distribuce a přeprava** | U trvalých zařízení | Prověřit | Dle technologie | **Prověřit ADR/RID a další režimy** | Dle řetězce kvality |
| **Plnicí stanice** | Prověřit | Prověřit | Prověřit | Dle typu stanice a vozidel | **Prověřit** |
| **Vozidla a využití** | U areálů/servisu | Prověřit | Dle zařízení | **Prověřit** | Dle aplikace |

„Prověřit“ znamená ověřit použitelnost právního režimu pro **konkrétní scénář**, nikoli automaticky přidělit povinnost. Dokumenty označené jako `nenalezeno` se nesmějí bez dalšího vykládat jako právní mezera: může jít o obecný předpis, odkazovanou normu, chybějící tematický index nebo o skutečně neexistující úpravu.

## 11. Specifikace registru zdrojů v databázi

### 11.1 Doporučená minimální struktura

Pro evidenci a automatizaci je vhodné oddělit **zdroj**, **konkrétní vstupní bod**, **jednotlivý dokument** a **verzi dokumentu**.

| Entita / tabulka | Hlavní účel | Příklady údajů |
|---|---|---|
| `sources` | Autoritativní identita zdroje. | `source_id`, název, provozovatel, jurisdikce, role, priorita, popis, tematické oblasti. |
| `source_endpoints` | Jednotlivé weby, API a informační kanály zdroje. | URL, typ rozhraní, formát, autentizace, licence, stav ověření, frekvence. |
| `source_checks` | Audit kontrol dostupnosti a změn. | Čas kontroly, výsledek, HTTP status, identifikátor požadavku, počet nových či změněných záznamů, chyba. |
| `documents` | Jednoznačná identita regulatorního dokumentu. | Typ, vydavatel, stabilní identifikátor, název, právní status a oblast působnosti. |
| `document_versions` | Jednotlivá vydání a časová znění dokumentu. | Publikace, účinnost od/do, verze, checksum, odkaz na originál. |
| `document_sources` | Původ a alternativní lokace téhož dokumentu. | `document_id`, `source_id`, URL, datum objevení, preferovaný zdroj, druh odkazu. |
| `document_relations` | Vazby předpisů a norem. | Novelizuje, ruší, provádí, transponuje, odkazuje na normu, nahrazuje normu. |
| `document_topics` | Použitelnost pro technologický proces. | Výroba, skladování, přeprava, plnění, vozidla, BOZP, environmentální oblast apod. |

Tyto názvy jsou **návrhem implementační struktury**, nikoli tvrzením o současném fyzickém schématu databáze DP004.

### 11.2 Povinné údaje u zdroje

U každého zdroje ukládat minimálně:

1. **Identita:** ID, název, provozovatel, země/jurisdikce, oficiální URL.
2. **Charakter dokumentů:** právní akty, návrhy, normy, metodiky, správní rozhodnutí, odborné zprávy.
3. **Autorita:** primární/autentický, oficiální informační, sekundární; samostatně právní závaznost jednotlivého dokumentu.
4. **Tematické pokrytí:** štítky technologií, životní fáze instalace a regulační oblasti.
5. **Technická dostupnost:** API, datové formáty, stránkování, identifikátory, RSS/notifikace, limity požadavků, historie změn.
6. **Právní dostupnost:** licence, možnost vytěžování, možnost archivace a publikace textů, požadavky na atribuci, zpoplatnění.
7. **Monitoring:** doporučený interval, poslední úspěšná kontrola, poslední zjištěná změna, technický stav a správce.
8. **Kvalita:** datum ověření, míra důvěryhodnosti, pravidla deduplikace a odkazy na případné alternativní zdroje.

### 11.3 Způsob automatizace

Doporučené pořadí integrace pro jednotlivý zdroj:

1. **Oficiální API nebo otevřený datový export**, pokud je dostupný a povolený.
2. **Oficiální RSS, notifikační služba nebo seznam změn.**
3. **Strukturované vyhledávání na webu** s respektováním podmínek provozovatele.
4. **Manuální rešerše a kurátorské ověření**, zejména u placených norem, metodik a právně významných interpretací.

Automatizovaná detekce změn **není automatickým právním posouzením**. Záznam o změně musí být ověřen vůči originálnímu právnímu aktu a případným přechodným ustanovením.

## 12. Rešeršní a validační metodika

### 12.1 Doporučené vyhledávací výrazy

Vyhledávání nesmí být omezeno pouze na dokumenty obsahující slovo „vodík“. Významná část požadavků vyplývá z obecných pravidel pro tlaková zařízení, hořlavé plyny, výstavbu, nebezpečné věci, ochranu životního prostředí nebo měřidla.

| Jazyk | Základní výrazy | Rozšířené oblasti |
|---|---|---|
| **Čeština** | vodík, vodíkový, elektrolyzér, elektrolýza, palivový článek, plnicí stanice | tlaková zařízení, plynová zařízení, hořlavý plyn, ATEX, ochrana před výbuchem, vyhrazená technická zařízení, přeprava nebezpečných věcí, metrologie, jakost paliva |
| **Angličtina** | hydrogen, electrolysis, electrolyser / electrolyzer, fuel cell, hydrogen refuelling / refueling station | pressure equipment, explosive atmospheres, dangerous goods, hydrogen purity, fuel quality, conformity assessment, RFNBO, low-carbon hydrogen |
| **Němčina** | Wasserstoff, Elektrolyseur, Brennstoffzelle, Wasserstofftankstelle | Druckgeräte, Explosionsschutz, Gefahrgut, Genehmigungsverfahren, Wasserstoffqualität |

U širších výrazů používat kombinaci s konkrétním procesem, technologií, kategorií regulace nebo identifikátorem legislativy; jinak vzniká nepřiměřený počet nerelevantních výsledků.

### 12.2 Postup zpracování nálezu

1. **Identifikovat** dokument v jednom nebo více zdrojích a zaznamenat jeho původ.
2. **Normalizovat identifikátor** (např. české číslo předpisu, CELEX/ELI, označení ČSN/EN/ISO, identifikátor metodiky).
3. **Ověřit autoritativní znění** a zaevidovat samostatně jeho verze, platnost a účinnost.
4. **Posoudit relevanci** pro konkrétní typ zařízení, činnost a fázi projektu.
5. **Vytvořit vazby** mezi právním aktem, prováděcím předpisem, normou, metodikou, správním postupem a případovým scénářem.
6. **Nastavit monitorování** změn a uchovat historii kontrol.
7. **Zaznamenat nejistotu**: neověřené vztahy, nejasnou použitelnost nebo licenční omezení označit jako otevřený úkol.

### 12.3 Metriky úplnosti

Doporučuje se průběžně sledovat alespoň:

- procento prioritních zdrojů se zprovozněným a úspěšně kontrolovaným vstupním bodem;
- podíl evidovaných dokumentů s ověřenou autoritativní lokalitou, verzí a datem účinnosti;
- podíl tematických oblastí a modelových scénářů se zpracovanou regulatorní rešerší;
- počet detekovaných změn, které ještě nebyly odborně validovány;
- počet dokumentů s nevyřešenou právní relevancí nebo nejasným statusem.

## 13. Návrh provozního režimu

| Skupina | Návrh frekvence | Způsob kontroly |
|---|---|---|
| e-Sbírka, e-Legislativa, EUR-Lex | Denně až týdně | API; strojové porovnání identifikátorů, dat a verzí. |
| ODok, parlamentní registry, OEIL, komitologie, delegované akty, TRIS | Týdně | Přehledy nových návrhů a změn; notifikace, pokud jsou dostupné. |
| ČAS, ÚNMZ, harmonizované normy, ISO/CEN/CENELEC, TPG | Měsíčně, případně dle publikačního cyklu | Sledování katalogových změn a věstníků. |
| Resortní metodiky a portály regulátorů | Měsíčně | Kontrola nových dokumentů a změn URL, revize relevantních oblastí. |
| Specializované odborné publikace (EHSP, EIGA, HYTEP aj.) | Čtvrtletně nebo při zveřejnění aktuality | Kurátorská kontrola publikací a jejich verzí. |

Intervaly představují **návrh provozu**, nikoli doloženou periodicitu aktualizace jednotlivých portálů. U právně a bezpečnostně zásadních předpisů je vhodné využít notifikace o změně co nejdříve po jejich zveřejnění.

## 14. Omezení, právní a technická rizika

- **Nelicencované šíření textů norem:** metadata a bibliografické odkazy obvykle neznamenají právo ukládat nebo veřejně distribuovat plná znění norem. Pravidla přístupu je nutné ověřit u držitele práv.
- **Rozdíl mezi platností a účinností:** právní akt může být publikován, ale ještě nemusí být účinný; mohou existovat přechodné režimy.
- **Sekundární zdroje:** odborný komentář, metodika nebo prezentace nemusí odrážet nejnovější právní stav a zpravidla nemá stejné právní účinky jako právní předpis.
- **Působnost předpisu:** mnohé obecné předpisy se vztahují na vodík bez jeho výslovné zmínky; nelze spoléhat na pouhé fulltextové hledání slova „vodík“.
- **Místní správní praxe:** příklady z EIA, vydaná povolení a individuální stanoviska nejsou automaticky přenositelná na jiný projekt.
- **Rozdíl jurisdikcí:** cizojazyčná pravidla a zahraniční návody slouží hlavně ke srovnání a inspiraci; jejich česká použitelnost vyžaduje zvláštní ověření.
- **Stabilita integrace:** veřejná webová stránka se může změnit, i když její obsah přetrvává; systém musí podporovat alternativní URL, chyby přístupu a revizi konektorů.

## 15. Vybrané oficiální podklady k této specifikaci

Níže uvedené odkazy slouží zejména k **ověření fungování systémů a technické dostupnosti dat**. Nejde o úplnou bibliografii předpisů pro vodík.

1. [e-Sbírka: použití REST API](https://e-sbirka.gov.cz/restful-api) – registrace, klíče, OpenAPI a služby pro aktualizaci dat.
2. [Ministerstvo vnitra: e-Sbírka a e-Legislativa](https://mv.gov.cz/e-sbirka-a-e-legislativa) – účel systémů a harmonogram přechodu.
3. [Ministerstvo vnitra: povinné používání e-Legislativy pro zákony](https://zakony.gov.cz/povinne-pouzivani-elegislativy-pro-zakony-od-15-ledna-2026) – přechodný režim novel zákonů.
4. [EUR-Lex: reuse of EUR-Lex content](https://eur-lex.europa.eu/content/help/data-reuse/reuse-contents-eurlex-details.html) – Cellar, REST a SPARQL.
5. [ČAS: ČSN online](https://agenturacas.gov.cz/produkty-a-sluzby/csn-online/) – katalog a placený přístup k plným textům.
6. [ÚNMZ: Věstník](https://unmz.gov.cz/obecne/vestnik-unmz/) – oznámení o normách, metrologii a posuzování shody.
7. [Evropská komise: harmonizované normy](https://single-market-economy.ec.europa.eu/single-market/goods/european-standards/harmonised-standards_en) – seznamy odkazů zveřejněných v Úředním věstníku EU.
8. [ISO/TC 197: Hydrogen Technologies](https://www.iso.org/committee/54560.html) – rozsah standardizace, pracovní program a vydané normy.
9. [Drážní úřad: RID](https://du.gov.cz/potrebuji-si-vyridit/rid-preprava-nebezpecnych-veci/) – české materiály a kompetence příslušného orgánu.
10. [ECHA: Search for chemicals](https://echa.europa.eu/information-on-chemicals) – přechod na databázi ECHA CHEM.
11. [Sbírka právních předpisů územních samospráv](https://sbirkapp.gov.cz/) – místní právní předpisy a související akty.
12. [Clean Hydrogen Partnership: EHSP reference documents](https://www.clean-hydrogen.europa.eu/get-involved/european-hydrogen-safety-panel-0/reference-documents_en) – bezpečnostní metodiky a jejich aktualizace.
13. [Český plynárenský svaz: platná TPG](https://cgoa.cz/to.normativni-dokumenty/platna-tpg) – katalog technických pravidel plynárenství.
14. [Evropská komise: hydrogen and decarbonised gas market](https://energy.ec.europa.eu/topics/markets-and-consumers/hydrogen-and-decarbonised-gas-market_en) – evropský regulatorní rámec vodíkového trhu.

---

**Závěr:** Tento katalog je výchozí specifikací pro registr informačních zdrojů DP004. Úplnost pokrytí se má vyhodnocovat podle **technologických scénářů a kategorií regulatorních požadavků**, nikoli pouze podle počtu sledovaných webových portálů. Registr je potřeba udržovat jako samostatnou, verzovanou a auditovatelnou součást znalostní databáze.
