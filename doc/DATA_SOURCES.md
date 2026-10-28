# Registr sledovaných zdrojů

> Historie dokumentu:  
> 2026-10-28 jprk Převzato z odstavce 11 dokumentu `doc/AUTOMATION.md` (větev `automation`, stav 2026-10-24)  

Tento dokument popisuje registr zdrojů, v nichž opakovaně hledáme nové
regulační dokumenty pro databázi regulačních předpisů a předrealizačních
procesů (výsledek V01 dílčího projektu DP004). Registr sám je uložen
v souboru `data/monitored_sources.json`. Které dokumenty má databáze
obsahovat a jak často se obsah kontroluje, vymezuje `doc/DATABASE_SCOPE.md`;
řetězec, jímž se nalezený dokument dostává do databáze, popisuje
`doc/AUTOMATION.md` (zatím jen na vývojové větvi `automation`).

---

## 1. Účel registru

Dnešní sledování stojí na třech zdrojích se screeningovými skripty
`src/tools/screen_eurlex.py`, `screen_esbirka.py` a `screen_slovlex.py`
(`doc/AUTOMATION.md`, odstavec 4.1), což zdaleka nepokrývá místa, kde nové
vodíkové předpisy vznikají. Registr `data/monitored_sources.json` proto vede
**úplný seznam zdrojů, jež sledujeme nebo sledovat chceme** — 42 položek,
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
jsou bez placeného přístupu uzavřené.

## 4. Doporučené pořadí prací

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
