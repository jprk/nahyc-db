# Vydání a platnost verzí právních předpisů (issue #38)

## 1. Co řešíme

Tabulka verzí na stránce dokumentu měla u právních předpisů prázdné sloupce „Vydání“ a „Platnost“ a prázdné
bylo často i pole „Platnost od“. Import vytvořil u každého předpisu jedinou verzi bez údajů a historii znění
jsme nenačítali. Výjimkou byly normy (`norm_editions.py`) a nařízení CLP a REACH (`eu_consolidations.py`).

## 2. Pravidla (rozhodnutí garanta v issue #38)

1. **Verze vedeme od okamžiku, kdy dokument poprvé vložíme do databáze.** Starší historii předpisu najde
   uživatel v jeho primárních zdrojích (e-Sbírka, EUR-Lex); do databáze ji nekopírujeme.
2. **U každé verze, kterou vedeme, držíme plný text ze zdroje i jeho vyčištěnou podobu.**
3. První verze popisuje text, který databáze už má (výchozí verze). Nástroj u ní doplní jen prázdná pole,
   takže hodnoty zadané editorem zůstanou.
4. Každé znění, které zdroj přidá po vložení dokumentu, zapíšeme jako novou verzi:
   - znění účinné ke dnešku je aktuální verze (`účinný`) a dokument zobrazuje jeho text;
   - předchozí verze jsou `nahrazený`;
   - znění vyhlášené s pozdějším dnem účinnosti je `vyhlášený, dosud neúčinný` a aktuální se stane v den
     účinnosti.
5. U zrušeného předpisu doplníme jen údaje výchozí verze, nové verze nepřidáváme.
6. CLP a REACH vede dál `eu_consolidations.py` s celou historií konsolidovaných znění (rozhodnutí
   z 20. 11. 2026); nový nástroj je vynechává. Slovenské předpisy zatím nepokrýváme, protože pro ně nemáme
   zdroj znění.

## 3. Zdroje

| Předpisy | Zdroj verzí | Výchozí verze | Text nové verze |
|---|---|---|---|
| české (`N/RRRR Sb.`: zákony, vyhlášky, nařízení vlády) | otevřená data e-Sbírky: seznam znění a den účinnosti každého z nich | znění účinné v den stažení uloženého textu, například „znění účinné od 1. 8. 2025“, odkaz na znění v e-Sbírce | stránka předpisu na zakonyprolidi.cz v den účinnosti znění (pole manifestu `zneni_<RRRRMMDD>`); nástroj ověří, že stránka uvádí právě toto znění |
| akty EU (směrnice, nařízení, rozhodnutí) | Cellar: den vstupu v platnost a konsolidovaná znění v jazyce dokumentu | „původní znění“ ke dni vstupu v platnost, odkaz do EUR-Lexu (uložený text je vyhlášený akt) | konsolidované znění z Cellaru (pole `konsolidace_<RRRRMMDD>`) |

Pole „Platnost od“ doplníme jen tam, kde je prázdné:
- u aktu EU dnem vstupu v platnost („24. 12. 2018“);
- u českého předpisu dnem účinnosti s poznámkou („20. 3. 2001 (účinnost)“), protože otevřená data e-Sbírky
  den vyhlášení neuvádějí.

## 4. Jak to funguje

- `src/tools/refresh_act_versions.py` se ptá e-Sbírky a Cellaru, výsledek ukládá do stavového souboru
  `data/act_versions_cache.json`, stahuje texty nových účinných znění a zapisuje verze do databáze.
- Při první kontrole předpisu nástroj uloží den, od kterého verze vedeme (`since`, den stažení uloženého
  textu), a znění, která zdroj do toho dne znal (`known`). Další kontroly tyto údaje nemění.
- Bez `--apply` nástroj běží nanečisto: zeptá se zdrojů a vypíše změny, ale nic nezapíše.
- Plánovač nástroj spouští denně po `refresh_eu_consolidations.py` (`scheduled_harvest.sh daily`, záloha jen
  před změnou) a v běhu `states` prvního dne v měsíci.
- Přestavba databáze (`init_db.py`) a měsíční stavy (`backfill_document_states.py`) promítnou verze ze
  stavového souboru a manifestu bez dotazu do sítě (`act_versions.apply()`).

```
.venv/bin/python src/tools/refresh_act_versions.py                     # nanečisto
.venv/bin/python src/tools/refresh_act_versions.py --apply --backup    # zápis
```

## 5. Stav při zavedení (27. 11. 2026)

- Nástroj pokrývá 226 předpisů: 73 českých a 153 aktů EU. Oba zdroje odpověděly u všech.
- Zkušební zápis do testovací databáze vyplnil u všech 226 předpisů výchozí verzi a u 164 z nich prázdné pole
  „Platnost od“.
- Šest českých předpisů už má po stažení svého textu nové znění, účinné od 1. 11. 2026: zákony č. 458/2000 Sb.,
  262/2006 Sb., 258/2000 Sb., 266/1994 Sb., 114/1992 Sb. a 13/1997 Sb. Nástroj stáhl jejich text a dokumenty
  ho zobrazují.
- 21 dalších znění je vyhlášených s pozdější účinností (nejbližší 1. 1. 2027).
- U aktů EU zatím žádné konsolidované znění po vložení nepřibylo.
