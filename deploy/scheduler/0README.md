# Adresář /deploy/scheduler

Návrh plánovače sběru sledovaných zdrojů (`doc/DATA_SOURCES.md`, odstavec 8.17;
četnosti podle `doc/DATABASE_SCOPE.md`, odstavec 6). **Nic z toho není
nainstalováno**: zda a kde plánovač poběží, rozhoduje zadavatel (požadavek R1.9,
`doc/DATA_SOURCES.md`, odstavec 4.5).

Všechny varianty volají týž skript `src/tools/scheduled_harvest.sh <četnost>`
(záloha databáze, běh zdrojů dané četnosti s `--apply`, stavy dokumentů a data
poslední kontroly). Ručně jej lze spustit i nanečisto (`--dry-run`).

* `h2db-harvest@.service` — služba systemd pro jeden běh; instance je četnost
  (`weekly`, `monthly`, `quarterly`, `states`), běží pod uživatelem `laborator`
  v hlavním stromu `/home/laborator/DEVEL/nahyc-h2db`.
* `h2db-harvest-weekly.timer` — v pondělí 3:30: registry předpisů a návrhů.
* `h2db-harvest-monthly.timer` — 2. den v měsíci 4:30: normy, kanály a stránky
  orgánů, stav ČSN/STN, kontrola dostupnosti zdrojů.
* `h2db-harvest-quarterly.timer` — 3. ledna, dubna, července a října 5:30:
  technická pravidla, metodiky, odborné publikace.
* `h2db-states-monthly.timer` — 1. den v měsíci 0:30: jen stavy dokumentů
  (`scheduled_harvest.sh states`, tj. záloha a `backfill_document_states.py`).
  ČSN nabývají účinnosti prvním dnem měsíce; nové vydání normy, jež kontrola
  katalogu ČSN zachytila jako vydané s pozdější účinností, se v ten den stane
  aktuální verzí dokumentu (`src/tools/norm_editions.py`; ČSN EN 13445 z 12/2026
  k 1. 1. 2027).
  Po stavech v týž běh i konsolidovaná znění aktů EU (jako `daily`).
* `h2db-consolidations-daily.timer` — denně 1:15: konsolidovaná znění aktů EU
  ze seznamu `data/eu_consolidated_acts.json` (CLP, REACH;
  `scheduled_harvest.sh daily`, tj. `refresh_eu_consolidations.py --apply --backup`):
  nové znění zjištěné v Cellaru se v den své účinnosti stane aktuální verzí
  dokumentu, jeho text se stáhne z Cellaru a vyčistí (`doc/CELLAR_FULLTEXT.md`,
  odstavec 7). Záloha databáze jen před změnou. Nové konsolidované znění CLP
  nabývá účinnosti 1. 1. 2027.
* `h2db-harvest.crontab` — tytéž běhy jako řádky crontabu (varianta bez systemd).

**Plánovač je třeba nainstalovat do konce prosince 2026.** Závisí na něm
přepnutí norem ČSN EN 13445 a ČSN EN 1717+A1 na vydání 12/2026 a přechod
nařízení CLP na konsolidované znění k 1. 1. 2027 (obojí 1. 1. 2027). Nebude-li
nainstalován, je třeba 1. nebo 2. 1. 2027 v hlavním stromu ručně spustit
(nouzový postup, `doc/PROVOZ.md`, odstavec 5.4):

    .venv/bin/python src/tools/backup_db.py --reason before_states_20270101
    .venv/bin/python src/tools/backfill_document_states.py --apply
    .venv/bin/python src/tools/refresh_eu_consolidations.py --apply

Instalace (až po rozhodnutí):

    sudo cp deploy/scheduler/h2db-harvest@.service deploy/scheduler/h2db-harvest-*.timer deploy/scheduler/h2db-states-monthly.timer deploy/scheduler/h2db-consolidations-daily.timer /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable --now h2db-harvest-weekly.timer h2db-harvest-monthly.timer h2db-harvest-quarterly.timer h2db-states-monthly.timer h2db-consolidations-daily.timer
    systemctl list-timers 'h2db-*'

nebo `crontab -e` a vložit řádky z `h2db-harvest.crontab`.
