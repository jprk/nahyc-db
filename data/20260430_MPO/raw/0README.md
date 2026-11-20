# Adresář /data/20260430_MPO/raw

Tento adresář obsahuje surová, původně dodaná data.

## Přehled zdrojových souborů

* `Předpisy CZ - vodík_MPO.xlsx` – Tabulka MPO, list „Předpisy (30.4.2026)“: 43 řádků
  s českými právními předpisy a 7 řádků s normami ČSN. Sloupec „Zdroj“ uvádí původ
  položky (VS = Vodíková strategie ČR, ZPL = Zákony pro lidi, AI = dotaz přes umělou
  inteligenci), žlutě jsou označeny předpisy, které podle MPO databáze již obsahovala.
* `CDV - evropské právní předpisy_v01.xlsx` – Tabulka Centra dopravního výzkumu, list
  „Databáze EU (30.4.2026)“: 40 řádků s předpisy EU, mezinárodními úmluvami, normami
  a technickými komisemi (zdroje „Databáze CDV“ a „AI – Copilot“).

Obě tabulky přišly jako přílohy e-mailu MPO z 22. 5. 2026 (`doc/mail/`). Strojový tvar
vytváří `src/tools/mpo_tables.py convert` do `../mpo_tables.json`.
