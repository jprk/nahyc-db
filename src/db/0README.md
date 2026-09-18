# Adresář /src/db

Skripty pro ruční správu editorských účtů (`User` tabulka, přihlašovací
systém `app/admin.py` — doc/PLAN.md §42/§43, 2026-09-18). Žádná
samoregistrace neexistuje ani nebude — malá skupina důvěryhodných
editorů se zakládá a spravuje výhradně těmito skripty, se stejnou
`[--apply]`/dry-run kázní jako `src/tools/backfill_*.py`. Heslo se vždy
čte interaktivně (`getpass`), nikdy jako argument příkazové řádky, a
hashuje přes `werkzeug.security.generate_password_hash`.

## Přehled skriptů

* `dbuser_add.py` - Založí nový editorský účet (login, čitelné jméno,
  e-mail, heslo). Odmítne, pokud login nebo e-mail už existuje (oba jsou
  `UNIQUE`), i pokud zadaný e-mail neprojde základní kontrolou tvaru
  (jen sanity check proti překlepu, ne plný RFC 5322 validátor). Použití:
  `.venv/bin/python src/db/dbuser_add.py <login> <name> <email> [--apply] [--env-file .env]`.
* `dbuser_passwd.py` - Změní heslo existujícího účtu (podle loginu,
  vyžaduje dvojí zadání pro potvrzení). Odmítne, pokud login neexistuje.
  Použití:
  `.venv/bin/python src/db/dbuser_passwd.py <login> [--apply] [--env-file .env]`.

Oba skripty přijímají `--env-file` (výchozí `.env`, lze `.env.test`) pro
provisioning na zkušební databázi bez zásahu do produkční. Bez vlastních
testů — stejná konvence jako tenké jednorázové provisioning skripty v
`src/tools/` (`backfill_puvodce.py`, `backfill_eu_gestor.py`, ...), které
také nemají vlastní testovací soubor.

**Nahrazuje** `src/tools/create_editor_user.py` (odstraněno) — ten dělal
totéž jedním skriptem, bez polí `name`/`email`, bez odděleného skriptu
pro pouhou změnu hesla.
