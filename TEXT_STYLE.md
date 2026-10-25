# TEXT_STYLE.md — Zásady pro textové výstupy (Jan Přikryl)

Přenositelná pravidla pro psaní odborných textů a generování DOCX dokumentů.
Odvozeno z ruční revize průvodce konsolidovanou databází (červenec 2026):
porovnání autorem přepsané verze proti výchozímu strojovému návrhu.
Platí pro formální dokumenty (zprávy, průvodce, metodiky, dokumentace).

> **Jak to použít:** Načti tento soubor na začátku práce na textovém/DOCX
> výstupu a řiď se jím. Pravidla mají přednost před výchozím stylem.

---

## 1. Jazyk a styl psaní

### 1.1 Autorský plurál (1. osoba množného čísla)
Píšeme z pozice autorského týmu, ne neosobně ve 3. osobě.

- ✅ „Technické detaily **záměrně vynecháváme**.“ · „V odstavci 8 **ukazujeme** na příkladu…“ · „Tabulky **rušíme** a vazby vedou přímo…“ · „Na jedné straně **máme** běžící databázi…“
- ❌ „Text záměrně vynechává.“ · „Kapitola 8 ukazuje…“ · „Tabulky se ruší.“

### 1.2 Formální lexikum, žádná hovorovost ani metafory
- Preferuj: *nepostačuje* (ne „nestačí“), *nazývá se* (ne „jmenuje se“), *jenž* (ne vždy „který“), *propojení / vazba* (ne obrazné „most mezi“).
- Vyhýbej se hovorovým obratům, familiárnímu tónu a expresivním metaforám. Text má znít věcně a odborně.

### 1.3 Přesnost a úplnost před stručností
- Rozepiš vágní pojmy na plnou terminologii: „databáze dokumentů“ → „databáze norem, zákonů a nařízení souvisejících s vodíkovými instalacemi“.
- Doplňuj odkaz na zdroj tvrzení: „sedm procesních uzlů, **definovaných v dokumentu V02**“, „původní návrh, **uvedený v dokumentu V02**“.
- **Dokonči výčty**, nezkracuj je. Když uvádíš „tři stavební kameny“, vyjmenuj je. Místo „Slovníček je na konci“ napiš, čím dokument končí, celou větou.

### 1.4 Opatrná (hedging) modalita
Tvrzení formuluj uvážlivě, ne absolutně.
- ✅ „**patrně** nejdůležitější místo“ · „Konsolidace **by** proto **neměla** nic odebrat“ · „aplikace, kterou **může používat** veřejnost“ · „omezení **k diskusi**“.
- ❌ „nejdůležitější místo“ · „nesmí nic odebrat“ · „kterou používá veřejnost“.

### 1.5 Neosobní dokumentový tón
Neoslovuj čtenáře přímo, nepersonalizuj účel dokumentu.
- ✅ „Průvodce je určen jako základní informace o návrhu…“
- ❌ „Průvodce je určen kolegům a kolegyním, kteří se teprve seznamují…“
- V titulcích a podtitulcích vynech oslovení cílové skupiny („…pro nové spolupracovníky“ raději vypustit).

### 1.6 Otevřenost o skutečném stavu
Nezastírej reálné příčiny a omezení; pojmenuj je věcně.
- Např. „díky nevhodně naplánovanému harmonogramu prací vznikal souběžně s V02, a procesy proto dosud reprezentovány nejsou“.

### 1.7 Budoucí čas pro plánované stavy
Odliš, co platí teď, od toho, co teprve nastane.
- „co **bude** celek **umět poskytnout** po dokončení vývojových prací“ · „aplikace **bude moci** běžet“ · „kde **bude potřeba** spolupráce expertů“.

### 1.8 Konzistentní terminologie
- „**dílčí** projekt DP004“ (ne jen „projekt“), „**výsledek** V01 / V02“, „**reprezentace** procesů“.
- Na číslované sekce dokumentu odkazuj slovem „**odstavec**“ (např. „viz odstavec 8“); drž jednotně napříč dokumentem.

---

## 2. Typografie (české zásady)

### 2.1 Velké písmeno po dvojtečce
Následuje-li po dvojtečce **samostatná věta**, začíná velkým písmenem.
- ✅ „Metodický dokument, jenž popisuje…: **Požaduje** strojově dotazovatelné vazby…“
- ✅ „**Zásadní praktické omezení k diskusi:** **Nad** vrstvou A běží…“
- (Následuje-li jen výčet nebo neúplný dovětek, ponech malé písmeno.)

### 2.2 Velké písmeno za pomlčkou v položce seznamu
Je-li položka seznamu **samostatný popisný celek**, začíná za pomlčkou velkým písmenem.
- ✅ „**V01** — **Veřejná** webová databáze regulačních dokumentů…“

### 2.3 Skutečné číslované seznamy
Používej nativní číslovaný seznam, ne odrážky s ručně vepsanými čísly.
- ✅ `1.` **Jen aditivní změny.** …  (styl číslovaného seznamu)
- ❌ `•` **1. Jen aditivní změny.** …  (odrážka s číslem v textu)

### 2.4 České konvence sazby
- Uvozovky „české“ (nikoli "rovné").
- Pomlčka „—“ s mezerami pro vsuvky; spojovník „-“ bez mezer.
- Diakritika vždy korektní; nezalomitelná mezera po jednopísmenných předložkách (k, s, v, z, o, u, a, i).
- Zkratkové identifikátory kódu (názvy tabulek/sloupců) neproporcionálním písmem — viz 3.5.

---

## 3. Formát DOCX (vzhled dokumentu)

> Základní princip: **spoléhej na vestavěné sémantické styly a výchozí motiv
> Wordu. Nepředefinovávej fonty ani barvy nadpisů.** Chyba výchozího návrhu
> byla vnucení Arialu a černých nadpisů.

### 3.1 Vestavěné sémantické styly, ne ruční formátování
- Titul → styl **Název (Title)**; podnadpisy → **Nadpis 1 / 2 / 3 (Heading 1/2/3)**.
- Nenastavuj u nadpisů ručně velikost, tučnost ani barvu — použij styl a nech motiv, ať je vykreslí.

### 3.2 Výchozí motiv a písmo — NEvnucuj Arial
- Ponech výchozí motiv Wordu: tělo **Aptos**, nadpisy **Aptos Display** (na starších instalacích Calibri / Calibri Light). Písmo nepřenastavuj na Arial.
- Tělo textu velikost 11 pt (sz 22).

### 3.3 Barevná hierarchie nadpisů — s override na tmavší navy
- Zachovej **barevné** nadpisy, ale přepiš je na tmavší odstín, než je výchozí motiv nabízí: `RGBColor(0x17, 0x36, 0x5D)` (navy `17365D`) pro **Název**, **Nadpis 1** i **Nadpis 2**. Nepřebarvuj na černou.
- Override dělej na úrovni **stylu** (`doc.styles["Heading 1"].font.color.rgb = ...`), ne na jednotlivých runech — projeví se konzistentně všude a zůstane to „vestavěný styl“, jen s jinými hodnotami.
- Konkrétní velikosti (napevno, override stylu): **Název 26 pt**, **Nadpis 1 16 pt**, **Nadpis 2 14 pt**.
- **Styl Název má JINÝ font než nadpisy** — přímé `Aptos ExtraBold` (ne motivové `Aptos Display`, které dostávají Nadpis 1/2 a Podtitul). Nastav ho explicitně (`doc.styles["Title"].font.name = "Aptos ExtraBold"`), jinak po přepnutí motivu (3.2) zdědí stejný font jako nadpisy a bude se od základního dokumentu vizuálně lišit.
- **Past:** výchozí šablona python-docx má u stylu Název už předvyplněné `w:spacing`(=5)/`w:kern`(=28) (standardní hodnoty MS Office stylu Title) a `w:contextualSpacing`. Než cokoli do `rPr`/`pPr` stylu ručně přidáváš, **nejdřív zkontroluj, jestli tam už není** (`rpr.find(qn("w:…"))`) — jinak vznikne duplicitní element a validace spadne na „element not expected“. Styl Název má navíc navíc nechtěný spodní rámeček (`w:pBdr`) — je potřeba ho odstranit, referenční dokument ho nemá.

### 3.4 Nadpisy jsou číslované — viditelně, přes SEQ pole (ne nativní numPr)
- Nadpisy **1. úrovně mají viditelné pořadové číslo** před textem (např. „1  Kontext“), nadpisy **2. úrovně** dostávají „N.M“ (M v rámci aktuální kapitoly, např. „5.1 Sedm procesních uzlů“).
- Číslo 1. úrovně vzniká **viditelným** polem `SEQ Kapitola \* ARABIC` obaleným záložkou (stejný mechanismus jako u obrázků/tabulek, viz 3.7) — díky tomu na něj lze odkazovat `REF … \# 0 \h` odjinud v dokumentu. Číslo 2. úrovně je prostý dopočtený text (ne pole), protože se na podkapitoly nikde neodkazuje — pokud by se to změnilo, promuj ho na stejný SEQ+bookmark mechanismus.
- **Vědomě NEpoužíváme** nativní Word „multilevel list linked to style“ (numPr na Heading 1/2 stylu, byť přesně to používá základní dokument) — spolehlivý REF `\# 0` cíl potřebuje literální číselný text v poli, který lze bookmarkovat; nativní outline číslo je vykreslováno Wordem za běhu a nejde ho takto adresovat bez rizikových přepínačů (`\r`/`\n`/`\w`), které v tomto prostředí (bez Wordu) nelze empiricky ověřit. Jediný mechanismus (SEQ+bookmark+REF `\# 0 \h`) napříč kapitolami/obrázky/tabulkami je jednodušší a spolehlivější, i za cenu drobné odchylky od vnitřní implementace referenčního dokumentu — vizuální výsledek je ekvivalentní.

### 3.5 Technické identifikátory neproporcionálně
- Názvy tabulek, sloupců a útržky kódu (`legal_document`, `source_reference`, `node_document`) sázej **monospace** písmem (Aptos Mono / Consolas).

### 3.6 Stránka a rozvržení
- Formát **A4**, okraje ~**2,5 cm** (1417 twips) ze všech stran.
- Číslování stran v **zápatí**.
- Obrázky **i tabulky** se číslují a mají **kurzívový popisek** velikosti 9,5 pt, centrovaný: obrázky „Obr. N — popis“ **pod** obrázkem, tabulky „Tabulka N — popis“ **nad** tabulkou. Číslo je vždy pole `SEQ Obrazek` / `SEQ Tabulka`, ne ručně vepsaná číslice — viz 3.7.
- Tabulky s **tučnou hlavičkou**; odrážky a číslování přes styly (List Bullet / List Number).

### 3.7 Křížové odkazy — vždy pole REF, nikdy vepsané číslo
Odkazuje-li text na jinou kapitolu, obrázek nebo tabulku („viz odstavec 8“, „z obrázku 6“), číslo se **nikdy nepíše jako obyčejný text**. Vždy jde o pole ve tvaru:

```
{ REF _reference_id_ \# 0 \h }
```

- `_reference_id_` je záložka (`w:bookmarkStart`/`w:bookmarkEnd`) obalující číslo v místě jeho definice (v nadpisu, popisku obrázku/tabulky).
- `\# 0` vytáhne z bookmarkovaného pole jen holé číslo (potlačí název objektu typu „Obrázek“/„Tabulka“ — proto obal jen kolem `SEQ` pole, ne kolem celého „Obr. N“).
- `\h` dělá z odkazu hypertextový odkaz.
- Číslo samotné vzniká polem `SEQ <Kapitola|Obrazek|Tabulka> \* ARABIC`, ne ručním číslem — jedině tak ho může `REF … \# 0` převzít a jedině tak se automaticky přepočítá při přeuspořádání dokumentu.
- Řetězec instrukce má mít mezery na obou koncích (` REF _Ref… \# 0 \h `) a atribut `xml:space="preserve"` na `<w:instrText>`.
- Do `word/settings.xml` dopiš `<w:updateFields w:val="true"/>`, aby aplikace pole přepočítala hned při otevření (jinak se zobrazí jen dosazená „cache“ hodnota z generování). **Pozor na pořadí prvků** — `updateFields` patří až za `savePreviewPicture` a před `compat`/`docVars` (schéma `CT_Settings`, viz 4.5).
- Záložky pojmenovávej popisně (`_RefKapPathway`, `_RefObrPathway`, `_RefTabHlediska`), ne generickým `_Ref12345` — snazší ladění. Musí být unikátní v celém dokumentu a odpovídat pravidlům OOXML pro jména záložek (písmeno/podtržítko na začátku, jen alfanumerika a podtržítka, max. 40 znaků).
- Cache-hodnotu (viditelný text, dokud se pole nepřepočítá) nastav na skutečné pořadové číslo — usnadní kontrolu bez nutnosti pole přepočítávat.

### 3.8 Jazyk dokumentu — vždy cs-CZ, na každém běhu
Výchozí šablona python-docx má jazyk `en-US` (v `docDefaults` i implicitně na každém runu bez vlastního přepisu). Bez opravy aplikace dokument nabízí/kontroluje jako anglický, i když je text česky.
- Nastav `w:lang w:val="cs-CZ" w:eastAsia="cs-CZ" w:bidi="ar-SA"` na **úplně každém** `<w:r>` v těle i v zápatí/záhlaví — ne jen v `docDefaults`. Referenční dokument to má takto (Word to dělá automaticky při ručním nastavení „Nastavit jazyk korektur“ pro celý text).
- `w:lang` je **poslední** prvek v pořadí `EG_RPrBase` (za `em`, před `eastAsianLayout`) — lze ho tedy vždy bezpečně připojit jako poslední potomek libovolného `w:rPr`, bez ohledu na to, co v něm už je.
- Oprav i `docDefaults` v `styles.xml` (`en-US` → `cs-CZ`) pro konzistenci, i když funkčně stačí runy.

---

## 4. Praktický postup generování DOCX (python-docx)

1. **Nepřepisuj** fonty stylů `Normal`, `Heading 1–3`, `Title` na Arial — výchozí šablona python-docx už používá motivové písmo; ponech ho. Barvu/velikost těchto stylů ale **napevno přepiš** na hodnoty z 3.3 (`doc.styles["Heading 1"].font.color.rgb = RGBColor(0x17,0x36,0x5D)`, `.font.size = Pt(16)` apod.).
2. Přiřazuj obsah přes **styly** (`doc.add_paragraph(text, style="Heading 1")`, `style="Title"`, `style="List Number"`, `style="List Bullet"`), ne ručním formátováním runů.
3. Pro identifikátory kódu nastav u příslušného runu monospace font (`run.font.name = "Consolas"`).
4. Oprav známý defekt šablony: element `w:zoom` potřebuje atribut `w:percent` (jinak neprojde validací).
5. **Čísla kapitol/obrázků/tabulek a křížové odkazy na ně** (3.4, 3.6, 3.7) python-docx nativně nepodporuje — stav se přímo v OOXML přes `docx.oxml.OxmlElement`/`qn`:
   - Pole (`SEQ`/`REF`) = pětice runů: `w:fldChar[begin]` → `w:instrText` (s `xml:space="preserve"`) → `w:fldChar[separate]` → `w:t` (cache hodnota) → `w:fldChar[end]`.
   - Záložka = `w:bookmarkStart`/`w:bookmarkEnd` s unikátním `w:id` a jménem, obaluje přesně tu pětici runů, na kterou se má odkazovat.
   - Hotový vzor je v `Databáze.Konsolidovaná/gen_pruvodce.py` (funkce `insert_bookmarked_field`, `append_field`, `heading()`, `picture()`, `table()`) — při dalším formálním DOCX výstupu s kapitolami/obrázky/tabulkami odsud zkopíruj základ, ne od nuly.
6. **Jazyk** (3.8): před `doc.save()` projeď celý strom (`document.element.body` + `section.footer.part.element`) a na každém `<w:r>` bez `<w:lang>` ho dopiš — vzor `set_lang_everywhere()` v `gen_pruvodce.py`.
7. Po vygenerování **ověř** skriptem `docx/scripts/office/validate.py` (přes ASCII cestu — česká diakritika v cestě komolí argumenty Pythonu v Bashi; kopíruj do scratchpadu nebo použij PowerShell). Pokud je cílový soubor otevřený ve Wordu, zápis selže na `PermissionError` — generuj nejdřív pod jiným jménem a ověř, teprve pak přepiš originál (případně požádej o zavření souboru).

### 4.1 Ověřování pořadí elementů v OOXML (např. `settings.xml`)
Když validátor nahlásí „element not expected, expected is one of (...)“, nehádej pořadí — over si ho v oficiálním schématu, které je součástí docx dovednosti:
`C:\Users\janpr\.claude\skills\docx\scripts\office\schemas\ISO-IEC29500-4_2016\wml.xsd`.
Najdi příslušný `<xsd:complexType name="CT_…">` (např. `CT_Settings`) a přečti pořadí `<xsd:element>` v jeho `xsd:sequence` — to je závazné pořadí, ve kterém prvky (i nepovinné, přeskočené) musí být v XML.

### 4.2 Past: vestavěné styly už často mají to, co se chystáš přidat
Než do `rPr`/`pPr` vestavěného stylu (Título, Heading…) ručně vložíš nový element (spacing, kern, border…), **nejdřív ho vyhledej** (`element.find(qn("w:…"))`) — výchozí šablona python-docx do nich leccos předvyplňuje (u stylu Název např. `spacing`, `kern`, `contextualSpacing`, `pBdr`). Slepé přidání vede k duplicitnímu elementu a pádu validace („element not expected“) na prvním elementu ZA tím duplicitním — chyba se tedy hlásí jinde, než je skutečná příčina.

---

## 5. Rychlý kontrolní seznam (před odevzdáním)

- [ ] Autorský plurál, ne neosobní 3. osoba.
- [ ] Formální lexikum, žádné metafory ani hovorovost.
- [ ] Vágní pojmy rozepsané, výčty dokončené, zdroje odkázané.
- [ ] Opatrná modalita (patrně, by měl/neměl, může).
- [ ] Neosobní tón, bez přímého oslovování.
- [ ] Budoucí čas u plánovaných stavů.
- [ ] Velké písmeno po dvojtečce (samostatná věta) a za pomlčkou v seznamu.
- [ ] Skutečné číslované seznamy.
- [ ] Vestavěné styly Wordu; žádný vnucený Arial; nadpisy navy `17365D` (Název 26 pt, Nadpis 1 16 pt, Nadpis 2 14 pt); styl Název má vlastní font `Aptos ExtraBold` (ne stejný jako nadpisy).
- [ ] Identifikátory kódu monospace.
- [ ] A4, okraje 2,5 cm, číslování stran.
- [ ] Nadpisy 1. úrovně viditelně číslované (SEQ Kapitola); 2. úrovně „N.M“.
- [ ] Obrázky i tabulky číslované přes `SEQ` pole, s popiskem (obrázek pod, tabulka nad).
- [ ] Odkazy na kapitoly/obrázky/tabulky jsou pole `REF … \# 0 \h`, ne vepsaná čísla.
- [ ] `<w:updateFields w:val="true"/>` v settings.xml (na správném místě dle schématu).
- [ ] Jazyk `cs-CZ` na každém runu (tělo i zápatí) a v `docDefaults`.
- [ ] DOCX ověřen validátorem; u polí/záložek zkontrolovat i strukturu (unikátní id, cíle REF existují) — viz kontrolní skript v historii generátoru.
- [ ] Cílový soubor není otevřený ve Wordu (jinak zápis selže na PermissionError).
