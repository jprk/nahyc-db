# Kontrola záznamů databáze

Stav k 23.11.2026, větve `feature/record-checks` (kontrola) a `feature/record-fixes` (opravy, odstavec 7). Kontrolu jsme spustili nad živou databází
`h2regdocs` (1506 dokumentů), jen pro čtení.

## 1. Proč kontrolujeme

Při přiřazování klíčových slov jsme zjistili, že dva akty EU (#86, #91) mají v databázi název
a popis jiného předpisu. Oba záznamy pocházejí z rešerše Sinay, která u nich uvádí jen číslo
(„(EÚ) 2021/535 | áno | MD SR“). Český název a popis k číslu doplnil jazykový model
(`process_laws.py`) a vymyslel je. Stejnou chybu jsme dříve opravili u `(EU) 2023/1234`.
Popisy dalších dokumentů doplnil model také (`enrich_annotations.py`) a rešerše Sinay vznikla
převodem PDF, při kterém se řádky mohou posunout. Chyby tohoto druhu ručně přehlédneme snadno,
proto jsme zavedli soustavnou kontrolu ve dvou vrstvách.

## 2. Vrstva 1: porovnání s úředními registry a vnitřní kontroly (`check_records.py`)

Vrstva nic nestojí a běží několik sekund (Cellar se ptáme jen na akty, které ještě nemáme
v mezipaměti).

| Kontrola | Co ověřuje | Zdroj |
|---|---|---|
| `eu_not_found`, `eu_ambiguous` | číslo aktu EU existuje jako právě jeden akt | Cellar |
| `eu_title` | náš název jmenuje tentýž akt jako úřední název ve stejném jazyce | Cellar |
| `eu_type`, `eu_date` | typ dokumentu odpovídá druhu aktu, datum v názvu datu aktu | Cellar |
| `iso_not_found`, `iso_title` | norma ISO existuje, název odpovídá | otevřená data ISO |
| `iso_draft_published` | návrh, který vedeme, ISO mezitím vydala | otevřená data ISO |
| `iso_withdrawn` | poslední vydání normy ISO zrušila | otevřená data ISO |
| `auth_title` | název odpovídá autoritativnímu názvu ze zdrojového webu | `nazev_autoritativni` |
| `number_not_in_title` | číslo z označení je v názvu (normy, české předpisy) | databáze |
| `bad_identifier`, `title_fragment` | označení není úlomek, název není useknutý ani poznámka | databáze |
| `duplicate_title` | dva dokumenty nemají téměř shodný název bez vzájemné vazby | databáze |

Podobnost názvů měříme podílem věcných slov (bez úředních frází jako „nařízení Evropského
parlamentu a Rady“). Hranici 0,5 jsme ověřili na známých případech: #86 má 0,20, #91 0,29,
správné názvy 0,65 a více.

## 3. Vrstva 2: posouzení modelem (`check_records_model.py`)

Úřední registr existuje jen pro akty EU, normy ISO a dokumenty s autoritativním názvem. Pro
německé, slovenské a americké normy, strategie a hlavně pro popisy žádný registr nemáme. Druhá
vrstva proto předá modelu gpt-5.5 záznam (označení, typ, jazyk, název, popis) s dostupnými
podklady (úřední název, anotace ISO, začátek plného textu) a model odpoví, zda název odpovídá
dokumentu, zda popis popisuje tentýž dokument a jak dokument souvisí s vodíkovými technologiemi.
Na vzorku jsme ověřili, že model známé chyby (#62, #86, #91) najde a správné záznamy (#81,
#105) propustí.

Běh nad celou databází stál 10,37 USD (gpt-5.5). Odpovědi ukládáme do mezipaměti podle obsahu
záznamu, další běh proto pošle modelu jen nové nebo změněné záznamy.

## 4. Výsledky

Nález má 151 dokumentů: 47 chyb, 93 varování, 11 informací (úplný seznam v příloze A).
Namátkou jsme ověřili v databázi #35, #430, #531, #582 a #801: všechny nálezy platí.

### 4.1 Název nebo popis patří jinému dokumentu (chyby, opravit)

- **Akty EU s vymyšleným názvem:** #86 (EU) 2023/955 a #91 (EU) 2021/535 — opravené v
  `data/manual_corrections.json` podle rozhodnutí uživatele; #62 vedený jako 2010/75/EU je
  slovenské oznámení (známý problém).
- **Popis jiné normy** (posunuté řádky rešerší, chybné doplnění): #35 ČSN EN ISO 13850 (popis
  o poštovních zásilkách), #582 ISO 23828 (terminologie informační bezpečnosti), #801 API SPEC
  11D1 a #802 API SPEC 5CT (úvod ASME B31.12), #430 STN EN ISO 14001 (přilepený text GASTEC),
  #531 prEN IEC 63341-2 (název i popis části 3), #600 ISO/TS 19883, #594 a #1204 ISO 19880-7,
  #280, #281 EN 1555-3/-4 (popis části 1), #324 EN 60079-13, #397 EN IEC 62282-8-301,
  #616 ISO 18172-2, #1037 TRGS 3146, #113 EN 17339, #670 ISO/TS 18683.
- **Popis doplněný modelem, který odporuje názvu:** slovenské vyhlášky #93–#96 (popis o životním
  prostředí místo požární bezpečnosti), #131/#1482 (EU) 402/2013 (železniční bezpečnostní metoda
  zasazená do vodíku), #106/#1470 (EU) 2018/2001 (místo popisu odkaz na stránku Komise), #911 ES-TRIN.
- **Zástupný text místo popisu** („noch nocht vorhanden“): #575, #576, #587, #588, #589, #590.

### 4.2 Poškozené záznamy (chyby, opravit nebo vyřadit)

Úlomky jiného řádku zdroje: #385 („/ - 2024.08 — kombinovanými úrovňami ochrany“), #417
(„A1 — plynovým obsahom…“, změna A1 k ISO 11114-1), #1002 a #1003 („Part 1“, „Part 2“ bez
označení normy), #692 (název useknutý na „est Methods“), #821 (poznámka místo názvu), #1078,
#1157 (poznámka „dosiaľ neprijatý súbor“ místo názvu).

### 4.3 Duplicity (varování, rozhodnout)

19 dvojic s téměř shodným názvem. Nejčastěji vedeme tentýž projekt ISO víckrát v různých fázích
(ISO/AWI a ISO/DIS 18735, 18741, 18742, 18760; ISO/AWI a ISO 19885-2, -3; ISO/PWI a ISO/AWI
17268-2), dále AGBF Leitfaden (#796/#1079), SAE J2578 (#25/#1022), ASTM F1624-12 (#14/#707),
ISO 14687 a ISO/CD 14687 (#111/#1190).

### 4.4 Zastaralé návrhy a zrušené normy (varování, aktualizovat)

39 záznamů vedeme jako návrh (ISO/AWI, CD, DIS, FDIS), ačkoli ISO normu mezitím vydala (např.
ISO/DIS 18760 → ISO 18760:2026, ISO/DIS 19880-7 → ISO 19880-7:2025, ISO/FDIS 19881 → ISO 19881:2025).
U 13 norem ISO zrušila poslední vydání (např. ISO 4276:1978, ISO 14687-1:1999). Tyto záznamy
patří do pravidelné kontroly platnosti (`doc/PROVOZ.md`): navrhujeme je převést na vydanou normu,
resp. označit stavem „zrušený“.

### 4.5 Rozsah databáze (rozhodnout)

48 dokumentů podle modelu s vodíkem nesouvisí. 28 z nich jsou směrnice a rozhodnutí EU, které
jsme doplnili jako cíle transpozice citované v českých zákonech (`EU_Transposition_Targets_Import`):
pracovní právo, rovné zacházení, epidemiologický dozor, veterinární předpisy. Dále staré
australské normy pro amoniak (AS), ISO 7106–7109 z roku 1985 a jednotlivé záznamy bez označení.
Podle `doc/DATABASE_SCOPE.md` nepatří do úrovně A ani B; navrhujeme je vyřadit z veřejného
katalogu, nebo je ponechat jen jako cíle transpozice bez zobrazení.

## 5. Další postup

1. **Opravy podle odstavců 4.1 a 4.2.** Každou opravu ověříme ve zdroji a zapíšeme do
   `data/manual_corrections.json` (tak přežije přestavbu); u popisů převezmeme anotaci z ISO,
   ČAS nebo úvodu plného textu, kde ji máme, jinak popis odstraníme a záznam označíme k doplnění.
2. **Rozhodnutí podle odstavců 4.3 až 4.5** (duplicity, vydané návrhy, rozsah).
3. **Pravidelný běh.** Vrstvu 1 spouštíme po každém přijetí kandidátů a týdně s kontrolou platnosti
   (zdarma). Vrstvu 2 spouštíme po každé změně záznamů; díky mezipaměti posílá modelu jen nové
   a změněné záznamy (řádově centy za běh).
4. **Fronta editorů.** Nálezy můžeme zapsat do tabulky `ReviewItem`, kterou aplikace zobrazuje
   editorům k posouzení; zatím jsou jen ve zprávách `data/record_checks.json` a
   `data/record_checks_model.json`.
5. **Ochrana proti opakování.** Model nesmí dodávat název ani popis bez podkladu: nový dokument
   přebírá název z úředního registru (Cellar, e-Sbírka, ČAS, ISO) a popis z anotace zdroje;
   co model odvodí, označíme jako neověřené (jako u klíčových slov).

## 6. Příkazy

```
cd src/tools
../../.venv/bin/python check_records.py                      # vrstva 1, zpráva data/record_checks.json
../../.venv/bin/python check_records_model.py                # vrstva 2, jen odhad ceny
../../.venv/bin/python check_records_model.py --run          # vrstva 2, zpráva data/record_checks_model.json
../../.venv/bin/python check_records_model.py --run --ids 35,582
```

Oba skripty databázi jen čtou (`--env-file` vybere jinou než živou).

## 7. Provedené opravy (23.11.2026)

Uživatel rozhodl (23.11.2026): opravit 47 chyb s ověřením každého dokumentu ve zdroji, popis
převzít z anotace ISO, ČAS nebo z textu a nejistý popis odstranit; duplicity sloučit; vydané návrhy
převést na vydanou normu; 28 aktů EU mimo rozsah vyřadit z katalogu; zapsat opravy a klíčová slova
do živé databáze a zbylé nálezy předat editorům. Opravy jsou v `data/manual_corrections.json` (tak
přežijí přestavbu); sestavuje je `src/tools/plan_record_fixes.py`, který u každé uvádí zdroj ověření.

| Skupina | Počet | Postup |
|---|---|---|
| Normy ISO (návrhy, duplicity projektů, chybné popisy) | 37 upravených, 33 sloučených | označení, název a anotace podle otevřených dat ISO; vydaný návrh dostal označení vydané normy (např. ISO/DIS 18760 → ISO 18760), rozpracovaný aktuální fázi (ISO 19885-2 → ISO/DIS 19885-2); trvalý odkaz (slug) zůstal; starší fáze téhož projektu jsme sloučili |
| Popis jiné normy u převzetí ISO | 2 | ČSN EN ISO 13850, STN EN ISO 14001: anotace ISO 13850 a ISO 14001 |
| Popis bez podkladu | 14 | odstraněn (slovenské vyhlášky, EN 17339, EN 1555-3/-4, EN 60079-13, API SPEC 11D1 a 5CT, (EU) 2018/2001 a 402/2013 v obou jazycích); dokument čeká na doplnění popisu |
| Jednotlivé opravy | 6 | #62 → (EU) 2013/732 [SK] (úřední slovenský název z Cellaru), #416 doplněný název změny A1, #531 název části 2 podle zdroje, #833 název bez přípony staršího vydání, #911 úřední název ES-TRIN, #1037 TRBS 3146 / TRGS 726 s vlastním názvem |
| Úlomky a duplicity mimo ISO | 12 sloučených | úlomky řádků PDF (#385, #417, #1001–#1003) do úplných záznamů; ASTM F1624-12, SAE J2578, AGBF Leitfaden, oprava AC k STN EN 14638-3, prEN IEC 62282-2-400, IEC/TS 62933-5-1, DIN ISO 19884 |
| Akty EU mimo rozsah | 28 vyřazených | cíle transpozice bez vztahu k vodíku (pracovní právo, rovné zacházení, epidemiologie, veterinární předpisy); fronta kandidátů je znovu nenavrhne (`candidates.excluded_keys()`) |
| (EU) 2023/955, (EU) 2021/535 | 2 | odstavec 3.2 v `doc/KLICOVA_SLOVA.md` |

Dva záznamy se stejným označením ze dvou rešerší (ASTM F1624-12, SAE J2578) rozliší opravu klíč
`"<označení> @<zdroj>"`, který jsme kvůli tomu doplnili do `build_unified_db.py` a
`apply_manual_corrections.py`.

**Živá databáze:** záloha `backups/h2regdocs_20261123_164103_before_record_fixes_and_keywords.sql.gz`,
potom `apply_manual_corrections.py --apply` (60 dokumentů opraveno, 74 sloučeno nebo vyřazeno;
1506 → 1432 dokumentů), klíčová slova (`document_terms.py --apply`, všech 1432 dokumentů) a nové
kontroly: vrstva 1 hlásí 19 nálezů, vrstva 2 dvě chyby a 18 dokumentů bez vztahu k vodíku.

**Fronta editorů:** zbylé nálezy 36 dokumentů jsme zapsali do fronty (`review_findings.py --apply`:
`ReviewItem` se stavem `needs_review` a důvod „Kontrola záznamů: …“ v `review_reason`). Jde o:
- #208 STN EN 1254-2: slovenský název („lisovacie tvarovky“) neodpovídá normě (spoje sevřením podle
  ČSN EN 1254-2); úřední název STN doplní editor z katalogu ÚNMS SR;
- 13 norem, jejichž poslední vydání ISO zrušila (ISO 22734:2019, ISO 14687-1 až -3 a další): převést
  na stav „zrušený“, případně na nahrazující normu;
- 3 normy, které ISO neuvádí (ISO 19887, ISO/DIS 19887, ISO/WD 17268-3.2), 3 useknuté názvy
  (#692, #821, #1078);
- 18 dokumentů bez vztahu k vodíku podle modelu (staré australské normy pro amoniak, ISO 7106–7109,
  (EU) 1300/2014 a další): rozhodnout o rozsahu.

Nález u #397 (STN EN IEC 62282-8-301) jsme ověřili jako chybný: norma se skutečně týká systémů
power-to-methane a popis odpovídá; do fronty nejde (`review_findings.VERIFIED`).

**Pozor:** sloučené dokumenty zanikly i s trvalým odkazem (např. `/dokument/eu-2023-955` vrací 404).
Odkazy přejmenovaných norem ISO zůstaly.

## Příloha A: dokumenty s nálezem

Závažnost `error` = záznam jmenuje nebo popisuje jiný dokument; `warning` = posoudí editor;
`info` = pro informaci. Stav živé databáze k 23.11.2026, před opravou #86 a #91.

| # | Označení | Závažnost | Kontroly | Nález |
|---|---|---|---|---|
| 35 | ČSN EN ISO 13850 | error | model_description | popis neodpovídá dokumentu. Popis se týká měření přepravní doby prioritních poštovních zásilek, nikoli normy ČSN EN ISO 13850 o funkci nouzového zastavení strojních zařízení. |
| 62 | 2010/75/EU | error | eu_title, model_title, model_relevance | Název v databázi popisuje jiný akt než úřední název. název neodpovídá dokumentu. Označení 2010/75/EU odkazuje na předpis EU, zatímco název a autoritativní název uvádějí slovenské oznámení ministerstva o zdravotní způsobilosti posádek plavidel. dokument … |
| 86 | (EU) 2023/955 | error | eu_title, model_title, model_description | Název v databázi popisuje jiný akt než úřední název. název neodpovídá dokumentu. Název v databázi neodpovídá podkladům: nařízení (EU) 2023/955 zřizuje Sociální klimatický fond a mění nařízení (EU) 2021/1060, nikoli vnitřní trh s obnovitelnými plyny, zemním … |
| 91 | (EU) 2021/535 | error | eu_title, model_title, model_description | Název v databázi popisuje jiný akt než úřední název. název neodpovídá dokumentu. Název v databázi se týká změny limitů pro ochratoxin A v potravinách, zatímco podklady uvádějí prováděcí nařízení k technickým specifikacím a schvalování typu vozidel z … |
| 93 | 124/2000 Z. z. | error | model_description | popis neodpovídá dokumentu. Popis nesprávně uvádí, že vyhláška se zaměřuje na ochranu životního prostředí, zatímco podle podkladů upravuje požární bezpečnost při činnostech s hořlavými a hoření podporujícími plyny. |
| 94 | 94/2004 Z. z. | error | model_description | popis neodpovídá dokumentu. Popis nesprávně uvádí, že vyhláška se zaměřuje na ochranu životního prostředí a obnovitelné zdroje, zatímco podle názvu a textu stanoví technické požadavky na protipožární bezpečnost při výstavbě a užívání staveb. |
| 95 | 96/2004 Z. z. | error | model_description | popis neodpovídá dokumentu. Popis nepřesně tvrdí, že vyhláška se zaměřuje na bezpečnost a ochranu zdraví při práci, zatímco podle podkladů upravuje protipožární bezpečnost při manipulaci a skladování hořlavých kapalin, olejů a tuků. |
| 96 | 699/2004 Z. z. | error | model_description | popis neodpovídá dokumentu. Popis mylně uvádí, že vyhláška se zaměřuje na technické a organizační požadavky v oblasti ochrany životního prostředí, zatímco podle podkladů upravuje zabezpečení staveb vodou na hašení požárů. |
| 106 | (EU) 2018/2001 | error | model_description | popis neodpovídá dokumentu. Popis je pouze odkaz na stránku Evropské komise o infrastruktuře pro alternativní paliva, nikoli popis směrnice (EU) 2018/2001 o podpoře využívání energie z obnovitelných zdrojů. |
| 113 | EN 17339 | error | model_description | popis neodpovídá dokumentu. Popis je příliš obecný a mylně uvádí zařízení a systémy využívající vodík jako palivo místo přepravitelných lahví a trub z uhlíkového kompozitu pro vodík. |
| 131 | (EU) 402/2013 | error | model_description | popis neodpovídá dokumentu. Popis nepřesně zasazuje nařízení do energetických systémů a vodíku, zatímco podle podkladů jde o společnou bezpečnostní metodu pro hodnocení a posuzování rizik v železničním odvětví.; Vztah k vodíkovým technologiím z podkladů … |
| 208 | STN EN 1254-2/ - 2021.09 | error | model_title | název neodpovídá dokumentu. Název uvádí lisovací tvarovky, zatímco popis dokumentu EN 1254-2:2021 se týká svěrných/kompresních spojek pro spojování s měděnými trubkami. |
| 280 | STN EN 1555-3/ - 2021.10 | error | model_description | popis neodpovídá dokumentu. Popis uvádí obecné aspekty PE potrubních systémů a použitelnost ve spojení s částmi 2 až 5, což odpovídá spíše obecné části EN 1555-1 než části 3 o tvarovkách. |
| 281 | STN EN 1555-4/ - 2021.10 | error | model_description | popis neodpovídá dokumentu. Popis zřejmě odpovídá obecné části EN 1555-1, protože mluví o obecných aspektech a o potrubích, tvarovkách i armaturách, zatímco označení a název uvádějí EN 1555-4 pro armatúry. |
| 324 | STN EN 60079-13/ - 2018.04 | error | model_description | popis neodpovídá dokumentu. K záznamu nejsou předány žádné podklady, takže správnost názvu nelze ověřit.; Popis se týká jiskrově bezpečných zařízení a odkazuje na požadavky typu ochrany „eigensicher“, což odpovídá jiné části souboru EN 60079 než části 13 … |
| 385 | / - 2024.08 | error | bad_identifier, title_fragment, model_relevance | Označení je úlomek (část jiného označení nebo jiného řádku zdroje), ne označení normy. Název normy začíná malým písmenem, nejspíš je useknutý. dokument nesouvisí s vodíkem. K záznamu nejsou uvedeny žádné podklady, takže nelze ověřit správnost názvu ani … |
| 397 | STN EN IEC 62282-8-301/ - 2023.11 | error | model_description | popis neodpovídá dokumentu. Popis hovoří o systémech přeměny energie na metan s dodávkou vody, CO2 a elektřiny, zatímco autoritativní název se týká systémů akumulace energie s moduly palivových článků v reverzním režimu a energetických systémů na bázi … |
| 417 | A1/ - 2024.03 | error | bad_identifier, title_fragment | Označení je úlomek (část jiného označení nebo jiného řádku zdroje), ne označení normy. Název normy začíná malým písmenem, nejspíš je useknutý. |
| 430 | STN EN ISO 14001/ - 2016.04 | error | model_description | popis neodpovídá dokumentu. K záznamu nejsou dodány podklady, takže nelze ověřit přesné znění názvu podle registru.; Popis kombinuje obecnou anotaci ISO 14001 s nesouvisejícím textem o GASTEC QA certifikaci pro vodíkový plyn, který neodpovídá normě ISO 14001. |
| 531 | prEN IEC 63341-2 | error | model_title, model_description | název neodpovídá dokumentu. Označení záznamu je prEN IEC 63341-2, ale autoritativní název i databázový název uvádějí Part 3, tedy IEC 63341-3.; Popis výslovně popisuje IEC 63341-3:2025 a uvádí, že vodíkové palivové systémy řeší IEC 63341-2, takže … |
| 562 | ISO 13984/ - 1999.03 | error | model_title | název neodpovídá dokumentu. Název v databázi uvádí „Land vehicle fuelling system interface“, zatímco podklady k ISO 13984 uvádějí název „Liquid hydrogen — Land vehicle fuelling protocol“. |
| 573 | ISO 19884 (súbor) | error | model_title | název neodpovídá dokumentu. Názov v databáze uvádza tlakové nádoby pre stacionárne skladovanie, zatiaľ čo podklad ISO uvádza fľaše a rúrkové nádoby pre stacionárne skladovanie. |
| 575 | ISO 19885-2 | error | duplicate_title, model_description | Téměř shodný název má dokument #587 (ISO/AWI 19885-2). popis neodpovídá dokumentu. Popis je zjevně zástupný text („noch nocht vorhanden“) a nepopisuje dokument. |
| 576 | ISO 19885-3 | error | duplicate_title, model_description | Téměř shodný název má dokument #588 (ISO/AWI 19885-3). popis neodpovídá dokumentu. Popis nepopisuje dokument; obsahuje pouze zástupný text „noch nocht vorhanden“. |
| 582 | ISO 23828/ - 2022.06 | error | model_description | popis neodpovídá dokumentu. Popis se týká terminologie informační bezpečnosti a neodpovídá normě o měření spotřeby energie a dojezdu silničních vozidel s palivovými články na stlačený vodík. |
| 587 | ISO/AWI 19885-2 | error | model_description | popis neodpovídá dokumentu. Popis „noch nocht vorhanden“ není věcným popisem dokumentu a neodpovídá podkladům. |
| 588 | ISO/AWI 19885-3 | error | model_description | popis neodpovídá dokumentu. Popis je pouze zástupný text „noch nocht vorhanden“ a nepopisuje dokument. |
| 589 | ISO/AWI TR 19884-2 | error | iso_not_found, model_description | ISO normu „ISO/AWI TR 19884-2“ neuvádí. popis neodpovídá dokumentu. K záznamu nejsou dodány žádné podklady, takže nelze ověřit správnost názvu.; Popis je pouze zástupný text „noch nocht vorhanden“ a nepopisuje dokument. |
| 590 | ISO/AWI TR 19884-3 | error | iso_draft_published, model_title | Návrh ISO/AWI TR 19884-3 ISO vydala jako ISO/TR 19884-3:2026 (2026-08-03). název neodpovídá dokumentu. Název v databázi neodpovídá přesně podkladům: uvádí „Cylinders and tubes“ a „shallow pressure cycle“, zatímco název ISO uvádí „Pressure vessels“ a … |
| 594 | ISO/DIS 19880-7 | error | duplicate_title, iso_draft_published, model_description | Téměř shodný název má dokument #1204 (ISO/WD 19880-7). Návrh ISO/DIS 19880-7 ISO vydala jako ISO 19880-7:2025 (2025-08-06). popis neodpovídá dokumentu. Popis uvádí pouze neaplikovatelnost na palubní tlakové lahve ve vozidlech na zemní plyn, což neodpovídá … |
| 600 | ISO/TS 19883/ - 2017.03 | error | model_description | popis neodpovídá dokumentu. Popis neodpovídá normě ISO/TS 19883:2017, která se týká bezpečnostních opatření a návrhu PSA systémů pro separaci a čištění vodíku, nikoli trubek většího objemu. |
| 616 | ISO 18172-2/ - 2007.03 | error | model_description | popis neodpovídá dokumentu. Popis chybně uvádí „Teil 1“, zatímco označení i podklady se týkají části 2.; Popis uvádí „Testdruck größer 60bar“, což neodpovídá názvu a anotaci s tlakem větším než 6 MPa, tj. 60 bar. |
| 670 | ISO/TS 18683/ - 2021.11 | error | model_description | popis neodpovídá dokumentu. Popis nepopisuje obsah ISO/TS 18683 k bezpečnosti a posuzování rizik při bunkrování LNG, ale uvádí obecnou formulaci o duplicitních inspekcích a chybějících mezinárodních normách, která z podkladů nevyplývá.; Dokument se týká … |
| 801 | API SPEC 11D1 | error | model_description | popis neodpovídá dokumentu. Popis neodpovídá API SPEC 11D1, ale cituje ASME B31.12 pro vodíkové potrubí. |
| 802 | API SPEC 5CT | error | model_description | popis neodpovídá dokumentu. Popis neodpovídá API SPEC 5CT pro casing and tubing a zjevně popisuje dokument pro potrubí a potrubní systémy ve vodíkové službě. |
| 833 | ASTM E1529-22 | error | model_title | název neodpovídá dokumentu. Název obsahuje označení starší edice „2016e1“, které neodpovídá uvedenému označení ASTM E1529-22.; Popis chybí. |
| 911 | ES-TRIN | error | model_title, model_description | název neodpovídá dokumentu. Označení ES-TRIN se vztahuje k evropské normě technických požadavků na plavidla vnitrozemské plavby obecně, nikoli pouze k využívání alternativních paliv.; Popis zužuje dokument na požadavky na bunkrování, skladování a … |
| 1002 | Part 1 | error | bad_identifier, model_relevance | Označení je úlomek (část jiného označení nebo jiného řádku zdroje), ne označení normy. dokument nesouvisí s vodíkem. Označení „Part 1“ je neúplné a bez podkladů nelze ověřit, k jaké normě část patří.; Bez podkladů nelze potvrdit, že název „Part 1 — … |
| 1003 | Part 2 | error | bad_identifier | Označení je úlomek (část jiného označení nebo jiného řádku zdroje), ne označení normy. |
| 1037 | TRGS 3146 / TRGS 726 | error | model_description | popis neodpovídá dokumentu. Popis se týká ortsfester Druckanlagen zur Lagerung von Gasen a HCN, zatímco název TRGS 3146 / TRGS 726 se týká ortsbewegliche Druckgasbehälter a jejich plnění, připravení, vnitropodnikové přepravy a vyprazdňování. |
| 1157 | DIN ISO 19884 | error | title_fragment, model_title | Název normy začíná malým písmenem, nejspíš je useknutý. název neodpovídá dokumentu. Název v databázi uvádí „Pressure vessels for stationary storage / tlakové nádoby“, zatímco podklad ISO uvádí „Cylinders and tubes for stationary storage“. |
| 1167 | ISO/TR 11954 (2008) | error | model_title | název neodpovídá dokumentu. Název v databázi zužuje dokument na měření maximální rychlosti, zatímco podklady uvádějí normu pro měření výkonových parametrů vozidel na stlačený vodík obecně. |
| 1187 | ISO/AWI 22734-1 | error | iso_draft_published, model_title | Návrh ISO/AWI 22734-1 ISO vydala jako ISO 22734-1:2025 (2025-07-03). název neodpovídá dokumentu. Název v databázi doplňuje oblasti použití a obecné požadavky, zkušební protokoly a bezpečnostní požadavky, zatímco podklady uvádějí název „Hydrogen generators … |
| 1188 | ISO/AWI 5124 | error | iso_draft_published, iso_title, model_title | Návrh ISO/AWI 5124 ISO vydala jako ISO 5124:2024 (2024-10-01). Název v databázi se liší od názvu normy v ISO. název neodpovídá dokumentu. Název v databázi mluví obecně o „LNG railcar applications“, zatímco podklady uvádějí konkrétně nakládku a vykládku LNG … |
| 1204 | ISO/WD 19880-7 | error | iso_draft_published, model_description | Návrh ISO/WD 19880-7 ISO vydala jako ISO 19880-7:2025 (2025-08-06). popis neodpovídá dokumentu. Popis uvádí neaplikovatelnost na palubní tlakové lahve vozidel na zemní plyn, což nepopisuje tuto normu pro pryžové O-kroužky ve vysokotlakých zařízeních … |
| 1470 | (EU) 2018/2001 [EN] | error | model_description | popis neodpovídá dokumentu. Popis je pouze odkaz na stránku o infrastruktuře alternativních paliv, nikoli popis směrnice (EU) 2018/2001 o podpoře využívání energie z obnovitelných zdrojů. |
| 1482 | (EU) 402/2013 [EN] | error | model_description | popis neodpovídá dokumentu. Popis zavádí oblast energetických systémů, vodíku a obnovitelných zdrojů, zatímco podklady ukazují, že nařízení se týká společné bezpečnostní metody pro hodnocení rizik v železničním sektoru podle směrnice o bezpečnosti železnic. |
| 14 | ASTM F1624-12 | warning | duplicate_title | Téměř shodný název má dokument #707 (None). |
| 25 | SAE J2578 | warning | duplicate_title | Téměř shodný název má dokument #1022 (None). |
| 111 | ISO 14687 | warning | duplicate_title | Téměř shodný název má dokument #1190 (ISO/CD 14687). |
| 136 | (EU) 1300/2014 | warning | model_relevance | dokument nesouvisí s vodíkem.  |
| 235 | STN EN 1317-1/ - 2011.02 | warning | model_relevance | dokument nesouvisí s vodíkem.  |
| 272 | STN EN 14638-3/ - 2010.12 | warning | duplicate_title | Téměř shodný název má dokument #1107 (STN EN 14638-3/AC – 2010.12). |
| 445 | STN EN ISO 17526/ - 2003.12 | warning | model_relevance | dokument nesouvisí s vodíkem. K záznamu nejsou dodány žádné podklady, takže nelze ověřit správnost názvu ani popisu.; Podle uvedeného názvu a popisu se norma týká životnosti laserů a nemá zřejmý vztah k vodíkovým technologiím. |
| 542 | prEN IEC 62282-2-400 | warning | duplicate_title | Téměř shodný název má dokument #1138 (DIN EN IEC 62282-2-400). |
| 577 | ISO 19887/ - 2024.10 | warning | iso_not_found | ISO normu „ISO 19887“ neuvádí. |
| 586 | ISO/AWI 17268-2 | warning | duplicate_title | Téměř shodný název má dokument #1203 (ISO/PWI 17268-2). |
| 591 | ISO/AWI TS 15916 | warning | iso_draft_published | Návrh ISO/AWI TS 15916 ISO vydala jako ISO/TS 15916:2026 (2026-01-27). |
| 592 | ISO/CD 13985 | warning | iso_draft_published | Návrh ISO/CD 13985 ISO vydala jako ISO 13985:2006 (2006-10-20). |
| 593 | ISO/DIS 13984 | warning | iso_draft_published | Návrh ISO/DIS 13984 ISO vydala jako ISO 13984:2026 (2026-03-11). |
| 595 | ISO/FDIS 17268-1 | warning | duplicate_title, iso_draft_published | Téměř shodný název má dokument #1191 (ISO/CD 17268-1). Návrh ISO/FDIS 17268-1 ISO vydala jako ISO 17268-1:2025 (2025-08-06). |
| 596 | ISO/FDIS 19880-5 | warning | duplicate_title, iso_draft_published | Téměř shodný název má dokument #1184 (ISO/AWI 19880-5). Návrh ISO/FDIS 19880-5 ISO vydala jako ISO 19880-5:2025 (2025-07-01). |
| 597 | ISO/FDIS 19881 | warning | iso_draft_published | Návrh ISO/FDIS 19881 ISO vydala jako ISO 19881:2025 (2025-06-13). |
| 598 | ISO/FDIS 22734-1 | warning | iso_draft_published | Návrh ISO/FDIS 22734-1 ISO vydala jako ISO 22734-1:2025 (2025-07-03). |
| 601 | ISO/WD 17268-3.2 | warning | iso_not_found | ISO normu „ISO/WD 17268-3.2“ neuvádí. |
| 646 | ISO 7106/ - 1985.06 | warning | model_relevance | dokument nesouvisí s vodíkem.  |
| 647 | ISO 7108/ - 1985.06 | warning | model_relevance | dokument nesouvisí s vodíkem.  |
| 648 | ISO 7109/ - 1985.06 | warning | model_relevance | dokument nesouvisí s vodíkem.  |
| 656 | ISO/DIS 18735 | warning | duplicate_title, iso_draft_published | Téměř shodný název má dokument #1179 (ISO/AWI 18735). Návrh ISO/DIS 18735 ISO vydala jako ISO 18735:2026 (2026-03-02). |
| 657 | ISO/DIS 18741 | warning | duplicate_title, iso_draft_published | Téměř shodný název má dokument #1180 (ISO/AWI 18741). Návrh ISO/DIS 18741 ISO vydala jako ISO 18741:2026 (2026-02-06). |
| 658 | ISO/DIS 18742 | warning | duplicate_title, iso_draft_published | Téměř shodný název má dokument #1181 (ISO/AWI 18742). Návrh ISO/DIS 18742 ISO vydala jako ISO 18742:2026 (2026-02-10). |
| 659 | ISO/DIS 18760 | warning | duplicate_title, iso_draft_published | Téměř shodný název má dokument #1182 (ISO/AWI 18760). Návrh ISO/DIS 18760 ISO vydala jako ISO 18760:2026 (2026-02-06). |
| 660 | ISO/DIS 18819 | warning | iso_draft_published | Návrh ISO/DIS 18819 ISO vydala jako ISO 18819:2026 (2026-03-02). |
| 692 | ANSI/CSA CHMC 2-2019 | warning | title_fragment | Název normy začíná malým písmenem, nejspíš je useknutý. |
| 796 | AGBF- Leitfaden – Wasserstoff | warning | duplicate_title | Téměř shodný název má dokument #1079 (AGBF- Leitfaden – Wasserstoff und dessen Gefahren). |
| 808 | AS 1678.8.0.010-1984 | warning | model_relevance | dokument nesouvisí s vodíkem. K záznamu nejsou poskytnuty žádné podklady, takže nelze ověřit správnost názvu ani popisu.; Z názvu a popisu plyne, že dokument se týká přepravy roztoku amoniaku, nikoli vodíkových technologií. |
| 809 | AS 1871.10-1976 | warning | model_relevance | dokument nesouvisí s vodíkem. K záznamu nejsou předány žádné podklady, takže nelze ověřit správnost názvu ani popisu.; Název a popis se týkají stanovení amoniakálního dusíku ve vodách, což z předaných údajů nesouvisí s vodíkovými technologiemi. |
| 814 | AS 2508.8.015-1988 | warning | model_relevance | dokument nesouvisí s vodíkem. K záznamu nejsou dodány žádné podklady, takže nelze ověřit správnost názvu ani popisu.; Podle uvedeného názvu se dokument týká zředěného roztoku amoniaku, nikoli vodíkových technologií. |
| 821 | ASME Section VIII | warning | title_fragment | Místo názvu je poznámka. |
| 838 | — | warning | model_relevance | dokument nesouvisí s vodíkem. K záznamu nejsou předány žádné podklady ani označení, takže nelze ověřit název ani popis.; Téma postkvantové kryptografie podle předaných údajů nesouvisí s vodíkovými technologiemi. |
| 846 | — | warning | model_relevance | dokument nesouvisí s vodíkem. Chybí označení dokumentu i podklady, takže nelze ověřit, zda název odpovídá konkrétní normě nebo doporučení. |
| 855 | C 260 (A) | warning | model_relevance | dokument nesouvisí s vodíkem. K záznamu nejsou poskytnuty žádné podklady, takže nelze ověřit správnost názvu ani popisu.; Z uvedeného názvu a popisu jde o normu k vlastnostem a přepravě proudů CO2, nikoli o vodíkové technologie. |
| 1077 | — | warning | model_relevance | dokument nesouvisí s vodíkem. Chybí označení normy i podklady, takže nelze ověřit název dokumentu.; Uvedený „název“ nepůsobí jako název normy, ale jako úryvek věty o technických komisích CEN/CENELEC. |
| 1078 | CEN/CLC/JTC 6 Hydrogen in energy | warning | title_fragment | Název normy začíná malým písmenem, nejspíš je useknutý. |
| 1164 | IEC 62933-5-1 | warning | duplicate_title | Téměř shodný název má dokument #1166 (IEC/TS 62933-5-1). |
| 1171 | ISO 4276 | warning | iso_withdrawn, model_relevance | Poslední vydání ISO 4276:1978 ISO zrušila (stav 9599). dokument nesouvisí s vodíkem.  |
| 1172 | ISO 6192 | warning | iso_withdrawn, model_relevance | Poslední vydání ISO 6192:1981 ISO zrušila (stav 9599). dokument nesouvisí s vodíkem.  |
| 1176 | ISO/AWI 13984 | warning | iso_draft_published | Návrh ISO/AWI 13984 ISO vydala jako ISO 13984:2026 (2026-03-11). |
| 1177 | ISO/AWI 13985 | warning | iso_draft_published | Návrh ISO/AWI 13985 ISO vydala jako ISO 13985:2006 (2006-10-20). |
| 1179 | ISO/AWI 18735 | warning | iso_draft_published | Návrh ISO/AWI 18735 ISO vydala jako ISO 18735:2026 (2026-03-02). |
| 1180 | ISO/AWI 18741 | warning | iso_draft_published | Návrh ISO/AWI 18741 ISO vydala jako ISO 18741:2026 (2026-02-06). |
| 1181 | ISO/AWI 18742 | warning | iso_draft_published | Návrh ISO/AWI 18742 ISO vydala jako ISO 18742:2026 (2026-02-10). |
| 1182 | ISO/AWI 18760 | warning | iso_draft_published | Návrh ISO/AWI 18760 ISO vydala jako ISO 18760:2026 (2026-02-06). |
| 1183 | ISO/AWI 18819 | warning | iso_draft_published | Návrh ISO/AWI 18819 ISO vydala jako ISO 18819:2026 (2026-03-02). |
| 1184 | ISO/AWI 19880-5 | warning | iso_draft_published | Návrh ISO/AWI 19880-5 ISO vydala jako ISO 19880-5:2025 (2025-07-01). |
| 1185 | ISO/AWI 19881 | warning | iso_draft_published | Návrh ISO/AWI 19881 ISO vydala jako ISO 19881:2025 (2025-06-13). |
| 1186 | ISO/AWI 19882 | warning | iso_draft_published | Návrh ISO/AWI 19882 ISO vydala jako ISO 19882:2025 (2025-02-12). |
| 1190 | ISO/CD 14687 | warning | iso_draft_published | Návrh ISO/CD 14687 ISO vydala jako ISO 14687:2025 (2025-02-12). |
| 1191 | ISO/CD 17268-1 | warning | iso_draft_published | Návrh ISO/CD 17268-1 ISO vydala jako ISO 17268-1:2025 (2025-08-06). |
| 1192 | ISO/CD 19880-2 | warning | iso_draft_published | Návrh ISO/CD 19880-2 ISO vydala jako ISO 19880-2:2025 (2025-02-03). |
| 1194 | ISO/CD 19880-8 | warning | iso_draft_published | Návrh ISO/CD 19880-8 ISO vydala jako ISO 19880-8:2024 (2024-12-13). |
| 1195 | ISO/CD 19880-9 | warning | iso_draft_published | Návrh ISO/CD 19880-9 ISO vydala jako ISO 19880-9:2024 (2024-07-16). |
| 1196 | ISO/CD 7039 | warning | iso_draft_published | Návrh ISO/CD 7039 ISO vydala jako ISO 7039:2024 (2024-07-22). |
| 1197 | ISO/DIS 11326 | warning | iso_draft_published | Návrh ISO/DIS 11326 ISO vydala jako ISO 11326:2024 (2024-11-01). |
| 1198 | ISO/DIS 19885-1 | warning | iso_draft_published | Návrh ISO/DIS 19885-1 ISO vydala jako ISO 19885-1:2024 (2024-05-13). |
| 1199 | ISO/DIS 19887 | warning | iso_not_found | ISO normu „ISO/DIS 19887“ neuvádí. |
| 1200 | ISO/DIS 23551-12 | warning | iso_draft_published | Návrh ISO/DIS 23551-12 ISO vydala jako ISO 23551-12:2023 (2023-10-06). |
| 1201 | ISO/FDIS 13577-2 | warning | duplicate_title, iso_draft_published | Téměř shodný název má dokument #1287 (ISO 13577-2). Návrh ISO/FDIS 13577-2 ISO vydala jako ISO 13577-2:2023 (2023-12-15). |
| 1202 | ISO/FDIS 24132 | warning | iso_draft_published | Návrh ISO/FDIS 24132 ISO vydala jako ISO 24132:2024 (2024-06-27). |
| 1205 | ISO/WD TS 19870 | warning | duplicate_title, iso_draft_published | Téměř shodný název má dokument #1273 (ISO/TS 19870). Návrh ISO/WD TS 19870 ISO vydala jako ISO/TS 19870:2023 (2023-11-30). |
| 1305 | ISO 17526 | warning | model_relevance | dokument nesouvisí s vodíkem.  |
| 1367 | 1999/63/ES | warning | model_relevance | dokument nesouvisí s vodíkem.  |
| 1368 | 1999/70/ES | warning | model_relevance | dokument nesouvisí s vodíkem. Dokument se týká pracovních poměrů na dobu určitou a podle předaných podkladů nemá vztah k vodíkovým technologiím ani navazujícím technickým či povolovacím oblastem. |
| 1369 | 2000/43/ES | warning | model_relevance | dokument nesouvisí s vodíkem. Dokument se týká rovného zacházení a zákazu diskriminace podle rasy nebo etnického původu, nikoli vodíkových technologií ani související technické regulace. |
| 1374 | 2000/79/ES | warning | model_relevance | dokument nesouvisí s vodíkem.  |
| 1375 | 2001/23/ES | warning | model_relevance | dokument nesouvisí s vodíkem.  |
| 1377 | 2001/86/ES | warning | model_relevance | dokument nesouvisí s vodíkem.  |
| 1380 | 2002/253/ES | warning | model_relevance | dokument nesouvisí s vodíkem. Dokument se týká definic případů pro hlášení přenosných nemocí a nemá z předaných údajů vztah k vodíkovým technologiím. |
| 1385 | 2003/72/ES | warning | model_relevance | dokument nesouvisí s vodíkem.  |
| 1389 | 2004/113/ES | warning | model_relevance | dokument nesouvisí s vodíkem.  |
| 1401 | 2007/875/ES | warning | model_relevance | dokument nesouvisí s vodíkem. Dokument se týká epidemiologického dozoru nad přenosnými nemocemi, nikoli vodíkových technologií ani souvisejících technických či povolovacích oblastí. |
| 1402 | 2008/104/ES | warning | model_relevance | dokument nesouvisí s vodíkem.  |
| 1404 | 2008/426/ES | warning | model_relevance | dokument nesouvisí s vodíkem. Dokument se týká definic případů pro hlášení přenosných nemocí a epidemiologického dozoru, nikoli vodíkových technologií ani souvisejících oblastí. |
| 1413 | 2009/177/EU | warning | model_relevance | dokument nesouvisí s vodíkem. Dokument se týká veterinárních požadavků, akvakultury a nákaz vodních živočichů, nikoli vodíkových technologií ani souvisejících oblastí. |
| 1417 | 2009/312/EU | warning | model_relevance | dokument nesouvisí s vodíkem. Dokument se týká epidemiologického dozoru nad přenosnými nemocemi a nemá z předaných údajů vztah k vodíkovým technologiím. |
| 1418 | 2009/363/EU | warning | model_relevance | dokument nesouvisí s vodíkem.  |
| 1419 | 2009/38/EU | warning | model_relevance | dokument nesouvisí s vodíkem.  |
| 1420 | 2009/539/EU | warning | model_relevance | dokument nesouvisí s vodíkem.  |
| 1421 | 2009/540/EU | warning | model_relevance | dokument nesouvisí s vodíkem.  |
| 1422 | 2009/547/EU | warning | model_relevance | dokument nesouvisí s vodíkem. Dokument se týká systému včasného varování a reakce pro přenosné nemoci, nikoli vodíkových technologií ani souvisejících technických či povolovacích oblastí. |
| 1423 | 2010/32/EU | warning | model_relevance | dokument nesouvisí s vodíkem.  |
| 1432 | 2014/66/EU | warning | model_relevance | dokument nesouvisí s vodíkem. Dokument se týká podmínek vstupu a pobytu státních příslušníků třetích zemí při převedení v rámci společnosti, nikoli vodíkových technologií ani související regulace. |
| 1437 | 2015/1794/EU | warning | model_relevance | dokument nesouvisí s vodíkem.  |
| 1445 | 2019/1158/EU | warning | model_relevance | dokument nesouvisí s vodíkem.  |
| 1447 | 2019/520/EU | warning | model_relevance | dokument nesouvisí s vodíkem.  |
| 1450 | 2022/2041/EU | warning | model_relevance | dokument nesouvisí s vodíkem.  |
| 1452 | 2000/96/ES | warning | model_relevance | dokument nesouvisí s vodíkem. Dokument se týká epidemiologického dozoru nad přenosnými nemocemi a nemá z předaných údajů vztah k vodíkovým technologiím. |
| 1453 | 2006/865/ES | warning | model_relevance | dokument nesouvisí s vodíkem. Dokument se týká prováděcích pravidel k ochraně druhů volně žijících živočichů a planě rostoucích rostlin a regulace obchodu s nimi, nikoli vodíkových technologií. |
| 1455 | 1998/2119/ES | warning | model_relevance | dokument nesouvisí s vodíkem.  |
| 1463 | (EU) 1300/2014 [EN] | warning | model_relevance | dokument nesouvisí s vodíkem.  |
| 11 | ISO 22734:2019 | info | iso_withdrawn | Poslední vydání ISO 22734:2019 ISO zrušila (stav 9599). |
| 599 | ISO/TR 15916/ - 2015.12 | info | iso_withdrawn | Poslední vydání ISO/TR 15916:2015 ISO zrušila (stav 9599). |
| 1168 | ISO 14687-1 | info | iso_withdrawn | Poslední vydání ISO 14687-1:1999 ISO zrušila (stav 9599). |
| 1169 | ISO 14687-2 | info | iso_withdrawn | Poslední vydání ISO 14687-2:2012 ISO zrušila (stav 9599). |
| 1170 | ISO 14687-3 | info | iso_withdrawn | Poslední vydání ISO 14687-3:2014 ISO zrušila (stav 9599). |
| 1173 | ISO 7104 | info | iso_withdrawn | Poslední vydání ISO 7104:1985 ISO zrušila (stav 9599). |
| 1175 | ISO 8713 | info | iso_withdrawn | Poslední vydání ISO 8713:2005 ISO zrušila (stav 9599). |
| 1189 | ISO/AWI TR 15916 | info | iso_withdrawn | Poslední vydání ISO/TR 15916:2015 ISO zrušila (stav 9599). |
| 1289 | ISO 13631 | info | iso_withdrawn | Poslední vydání ISO 13631:2002 ISO zrušila (stav 9599). |
| 1460 | ČSN ISO 14687-1 | info | iso_withdrawn | Poslední vydání ISO 14687-1:1999 ISO zrušila (stav 9599). |
| 1461 | ČSN ISO 14687-2 | info | iso_withdrawn | Poslední vydání ISO 14687-2:2012 ISO zrušila (stav 9599). |
