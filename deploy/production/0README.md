# Adresář /deploy/production

Soubory pro produkční server `nahyc.fel.zcu.cz` (`doc/NASAZENI.md`).

| Soubor | Účel |
|---|---|
| `pull_from_development.sh` | první nasazení: produkce stáhne z vývojového stroje balík (`transfer_bundle.py export`) a plné texty a nainstaluje je (odstavec 4.3) |
| `push_copy_to_test.sh` | kopie produkce na testovací web `nahyc.fd.cvut.cz/h2db`: produkce vytvoří balík, pošle ho s plnými texty na vývojový stroj a tam nainstaluje (odstavec 6) |
| `h2db-copy-to-test.service`, `h2db-copy-to-test.timer` | jednotky systemd pro týdenní kopii (neděle 3:30) |
| `apache-h2db.conf` | vzor konfigurace Apache (mod_wsgi pod účtem `h2db`) |
| `env.example` | vzor `.env` produkce včetně `H2DB_STATE_DIR` |

Cesty (`/srv/h2db/repo`, `/srv/h2db/state`) a účet `h2db` jsou návrh; jiné stačí promítnout do `.env`,
konfigurace Apache a jednotek systemd.
