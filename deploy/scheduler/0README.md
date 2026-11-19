# Adresář /deploy/scheduler

Návrh plánovače sběru sledovaných zdrojů (`doc/DATA_SOURCES.md`, odstavec 8.17;
četnosti podle `doc/DATABASE_SCOPE.md`, odstavec 6). **Nic z toho není
nainstalováno**: zda a kde plánovač poběží, rozhoduje zadavatel (požadavek R1.9,
`doc/DATA_SOURCES.md`, odstavec 4.5).

Všechny varianty volají týž skript `src/tools/scheduled_harvest.sh <četnost>`
(záloha databáze, běh zdrojů dané četnosti s `--apply`, stavy dokumentů a data
poslední kontroly). Ručně jej lze spustit i nanečisto (`--dry-run`).

* `h2db-harvest@.service` — služba systemd pro jeden běh; instance je četnost
  (`weekly`, `monthly`, `quarterly`), běží pod uživatelem `laborator`
  v hlavním stromu `/home/laborator/DEVEL/nahyc-h2db`.
* `h2db-harvest-weekly.timer` — v pondělí 3:30: registry předpisů a návrhů.
* `h2db-harvest-monthly.timer` — 2. den v měsíci 4:30: normy, kanály a stránky
  orgánů, stav ČSN/STN, kontrola dostupnosti zdrojů.
* `h2db-harvest-quarterly.timer` — 3. ledna, dubna, července a října 5:30:
  technická pravidla, metodiky, odborné publikace.
* `h2db-harvest.crontab` — tytéž běhy jako řádky crontabu (varianta bez systemd).

Instalace (až po rozhodnutí):

    sudo cp deploy/scheduler/h2db-harvest@.service deploy/scheduler/h2db-harvest-*.timer /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable --now h2db-harvest-weekly.timer h2db-harvest-monthly.timer h2db-harvest-quarterly.timer
    systemctl list-timers 'h2db-harvest*'

nebo `crontab -e` a vložit řádky z `h2db-harvest.crontab`.
