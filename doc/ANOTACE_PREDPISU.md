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
č. 406/2004 Sb.“, „aplikovatelná jen vybraná ustanovení“), zůstávají jako popis jen tam, kde úvodní
ustanovení nenajdeme; jinak je nahradí ustanovení (v datech rešerše zůstávají, odstavec 6).

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

## 6. Otevřené otázky

1. Poznámky autorů rešerší o transpozici a použitelnosti ustanovení (např. „Transpozice provedena –
   nařízení vlády č. 406/2004 Sb.“) úvodní ustanovení z popisu vytlačí. Máme je na stránce dokumentu
   ukázat zvlášť jako „Poznámku z rešerše“? Vyžaduje to další sloupec.
2. Zápis do provozní databáze: po mergi `annotate_acts.py --apply` se zálohou (odstavec 5).
3. Tři předpisy bez popisu a 23 přibližných shrnutí čekají na editora ve frontě oprav.
