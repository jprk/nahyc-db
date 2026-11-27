# Popis právních předpisů z jejich textu

Stav k 27. 11. 2026, větev `feature/anotace-predpisu`, issue #37.

## 1. Problém

U většiny právních předpisů pole „Popis“ na stránce dokumentu jen opakovalo úplný název (u zákona
č. 100/2001 Sb.: „Zákon č. 100/2001 Sb. - Zákon o posuzování vlivů na životní prostředí …“), u aktů EU
popis chyběl nebo obsahoval text, který dříve napsal jazykový model. Rešerše uváděly ve sloupci anotace
jen název a e-Sbírka ani zakonyprolidi.cz anotaci obsahu nevydávají. Plný text přitom máme u 203
z 207 předpisů. Zásada 7 v `doc/PROVOZ.md` stanoví, že popis přebíráme z anotace zdroje nebo z textu
dokumentu a cokoli odvozeného modelem označujeme jako neověřené.

## 2. Postup

Nástroj `src/tools/annotate_acts.py` zpracuje každý zákon, vyhlášku, nařízení vlády a směrnici,
nařízení a rozhodnutí EU, k nimž máme vyčištěný text (`data/fulltext_clean/`):

1. **Úvodní ustanovení doslova** (`act_provisions.opening_provision()`). Český a slovenský předpis
   zpravidla začíná „§ 1 Předmět úpravy“ („Tento zákon upravuje …“), akt EU „Článek 1 Předmět“
   („Tato směrnice stanoví …“, „Účelem tohoto nařízení je …“). Ustanovení převezmeme celé, doslova,
   jen bez značek poznámek pod čarou, a nejvýše 1500 znaků (delší zkrátíme na konci věty a označíme
   „…“). Nepoužijeme ho, když předpis jen mění jiný předpis („… se mění takto:“, „Přílohy … se
   nahrazují …“), když vymezuje pojmy, nebo když jen vyjmenovává transponované směrnice EU. Úvodní
   ustanovení, které předpisy EU zapracovává *a zároveň* říká, co předpis upravuje (energetický zákon:
   „Tento zákon zapracovává příslušné předpisy Evropské unie a upravuje …“), použijeme.
2. **Ustanovení vyhledané modelem** (`--locate`), když první ustanovení nevyhovuje (komentář k issue
   #37, bod 1). Model gpt-5.5 dostane začátek textu (25 000 znaků) a vrátí doslova pasáž, která říká,
   co předpis upravuje nebo jaký má účel; u novely smí vybrat bod odůvodnění, který mluví o této
   novele („Tato směrnice mění …, aby …“). Pasáž přijmeme, jen když se v textu vyskytuje doslova
   a projde stejnými pravidly jako v bodě 1; bod odůvodnění, který popisuje měněný předpis, odmítneme.
3. **Přibližné shrnutí** (`--summarize`), když žádné ustanovení nevyhovuje (komentář, bod 2). Model
   gpt-5.5 napíše z textu 2–4 české věty, jiný model (gpt-5.4) je porovná s textem a opraví pravopis.
   Shrnutí s tvrzením, které z textu neplyne, kontrolor zamítne a nepoužijeme ho. Shrnutí jde do pole
   `popis_priblizny` (web ho ukazuje se štítkem „Přibližné shrnutí, neověřeno“), `popis_autoritativni`
   zůstává prázdné a dokument dostane příznak „popis je třeba doplnit ručně“.
4. **Popis, který jen opakuje název, vyprázdníme** (`act_provisions.restates_title()`; při přestavbě
   `init_db.resolve_description()`). Dokument pak má příznak „chybí popis/anotace dokumentu“.
5. **Popis od editora nepřepíšeme.** Oprava v `data/manual_corrections.json`, která popis zadává,
   má přednost; oprava, která popis bez podkladu jen odstranila (kontrola záznamů z 23. 11. 2026),
   úvodní ustanovení nezablokuje.

Poznámky autorů rešerší, které nejsou přepisem názvu („Transpozice provedena – nařízení vlády
č. 406/2004 Sb.“, „aplikovatelná jen vybraná ustanovení“), **vyřazujeme** (rozhodnutí uživatele
z 27. 11. 2026): jsou to jen krátké informační texty a transpozici zaznamenávají vazby `IMPLEMENTS`
(105 vazeb ke 77 aktům EU, mimo jiné 1999/92/ES ← nařízení vlády č. 406/2004 Sb., 2014/34/EU ← nařízení
vlády č. 116/2016 Sb., 2012/18/EU ← zákon č. 224/2015 Sb.). Předpis, u něhož úvodní ustanovení nenajdeme,
proto nemá popis vůbec, nanejvýš přibližné shrnutí, a čeká na editora.

## 3. Výsledek (kopie provozní databáze k 27. 11. 2026)

| Typ | celkem | bez textu | popis editora | ustanovení (vzor) | ustanovení (model) | shrnutí | ručně |
|---|---|---|---|---|---|---|---|
| Zákon | 39 | 1 | 0 | 36 | 0 | 2 | 0 |
| Vyhláška | 16 | 1 | 0 | 8 | 2 | 5 | 0 |
| Nařízení vlády | 6 | 0 | 0 | 6 | 0 | 0 | 0 |
| Směrnice EU | 86 | 1 | 1 | 68 | 4 | 10 | 2 |
| Nařízení EU | 53 | 0 | 3 | 39 | 4 | 6 | 1 |
| Rozhodnutí EU | 7 | 1 | 0 | 6 | 0 | 0 | 0 |
| **Celkem** | **207** | **4** | **4** | **163** | **10** | **23** | **3** |

- 173 předpisů má jako popis doslovné úvodní ustanovení se zdrojem („§ 1 Předmět úpravy, doslova
  z textu předpisu“); u 10 z nich ustanovení vyhledal model (zdroj to uvádí).
- 23 předpisů (hlavně novely) má zkontrolované přibližné shrnutí; ve 3 případech kontrolor shrnutí
  zamítl ((EU) 2019/776 [EN], (EU) 2023/2413 [EN], 2000/71/ES) a popis doplní editor.
- Modelové kroky stály asi 4,15 USD (gpt-5.5 a gpt-5.4, včetně opakování s upřesněnými pokyny);
  odpovědi jsou v mezipaměti, další běh volá model jen u předpisu, jehož text se změnil.

### Doplnění plných textů (27. 11. 2026)

V provozní databázi zbylo 54 předpisů bez plného textu, a proto bez popisu: 52 předpisů přidaných
z fronty kandidátů (22 vyhlášek, 12 zákonů, 2 nařízení vlády, 9 nařízení EU, 7 směrnic EU),
rozhodnutí (EU) 2013/732 [SK] a směrnice 2010/75/EU. U prvních 53 jsme texty stáhli (`fetch_fulltext.py`), vyčistili
(`extract_fulltext.py`) a pustili na ně `annotate_acts.py`:

- 47 předpisů má doslovné úvodní ustanovení, 46 podle vzoru, u zákona č. 44/1988 Sb. ho vyhledal model.
- 6 předpisů má zkontrolované přibližné shrnutí a čeká na editora: novely 87/2025 Sb., 469/2023 Sb.,
  19/2023 Sb. a 513/2021 Sb., vyhláška č. 401/2010 Sb. a vyhláška č. 104/1988 Sb.
- U vyhlášky č. 104/1988 Sb. model vybral § 5 (povolování hornické činnosti). Ten ale popisuje jen
  jednu ze tří částí vyhlášky (§ 1 je zrušen), proto jsme ho v mezipaměti ručně odmítli.
- Modelové kroky stály 0,63 USD.
- Směrnice 2010/75/EU (dokument 1222) neměla označení. Oprava záznamu ze 23. 11. 2026 přejmenovala
  slovenský záznam rešerše Sinay vedený pod číslem 2010/75/EU na (EU) 2013/732 [SK], klíč opravy
  (`2010/75/EU`) ale zasáhl i záznam směrnice se stejným číslem. Klíč jsme omezili na záznam Sinay
  (`2010/75/EU @Sinay_Zakony`), směrnice tak má zase označení 2010/75/EU, text a popis podle čl. 1
  (větev `feature/smernice-2010-75`). Přejmenování podle klíče se zdrojem se týká jen vazeb, které dal
  tentýž zdroj (`build_unified_db.renamed_designations()`): vazby IMPLEMENTS národních předpisů, které
  směrnici citují (201/2012 Sb., 541/2020 Sb., 146/2023 Z. z., 248/2023 Z. z.), vedou zase na směrnici.

Zkontrolovali jsme vzorky: u novel model nejdřív vybíral výčty změn, definice, úvodní věty vyhlášek
nebo body odůvodnění o měněném předpisu. Proto citaci ověřujeme stejnými pravidly jako vzor
(`act_provisions.describes()`) a body odůvodnění přijímáme, jen když mluví o tomto předpisu.

## 4. Uložení a zobrazení

- `data/act_descriptions.json` (stavový soubor, `state_paths.STATE_FILES`): pro každý předpis klíč
  dokumentu, kontrolní součet textu, nalezené ustanovení (`provision`), výsledek modelu (`located`)
  a shrnutí s výsledkem kontroly (`summary`).
- `build_unified_db.apply_act_description()` při přestavbě nastaví `popis_autoritativni` a nový
  sloupec `Document.popis_zdroj`, nebo `popis_priblizny` a příznak k ručnímu doplnění.
- Stránka dokumentu ukazuje popis s odstavci a pod ním „Úvodní ustanovení: § 1 Předmět úpravy,
  doslova z textu předpisu“.
- `annotate_acts.py --apply` zapíše popisy do databáze (sloupec `popis_zdroj` sám založí).

## 5. Příkazy

```
cd src/tools
../../.venv/bin/python annotate_acts.py                          # úvodní ustanovení, přehled
../../.venv/bin/python annotate_acts.py --locate --summarize     # + odhad ceny modelových kroků
../../.venv/bin/python annotate_acts.py --locate --summarize --run
../../.venv/bin/python annotate_acts.py --apply --env-file <.env>   # zápis do databáze (předtím záloha)
```

## 6. Rozhodnutí z 27. 11. 2026

1. Poznámky z rešerší vyřazujeme, další sloupec nepřidáváme (odstavec 2).
2. Popisy zapíšeme do provozní databáze: záloha, pak `annotate_acts.py --apply` (odstavec 5).
