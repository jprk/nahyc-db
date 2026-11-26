#!/usr/bin/env bash
# První nasazení (doc/NASAZENI.md, odstavec 4): spouští se NA PRODUKCI (nahyc.fel.zcu.cz).
# Stáhne z vývojového stroje (nahyc.fd.cvut.cz) poslední balík s databází a stavovými soubory
# (src/tools/transfer_bundle.py export) a plné texty, ověří je a nainstaluje.
#
#   deploy/production/pull_from_development.sh              # do prázdné databáze
#   deploy/production/pull_from_development.sh --replace-db # databáze už tabulky má (zálohuje se)
#
# Proměnné (výchozí hodnoty v závorce):
#   H2DB_SOURCE          účet na vývojovém stroji (laborator@nahyc.fd.cvut.cz)
#   H2DB_SOURCE_REPO     pracovní strom na vývojovém stroji (/home/laborator/DEVEL/nahyc-h2db)
#   H2DB_SOURCE_EXPORT   adresář balíků na vývojovém stroji (/home/laborator/h2db-export)
#   H2DB_REPO            pracovní strom na produkci (adresář nad deploy/)
#   H2DB_INBOX           kam stáhnout balík ($HOME/h2db-inbox)
#   H2DB_ALLOW_COMMIT_MISMATCH=1  pokračovat, i když produkce běží na jiném commitu než vývoj
set -euo pipefail

SOURCE="${H2DB_SOURCE:-laborator@nahyc.fd.cvut.cz}"
SOURCE_REPO="${H2DB_SOURCE_REPO:-/home/laborator/DEVEL/nahyc-h2db}"
SOURCE_EXPORT="${H2DB_SOURCE_EXPORT:-/home/laborator/h2db-export}"
REPO="${H2DB_REPO:-$(cd "$(dirname "$0")/../.." && pwd)}"
PY="${H2DB_PYTHON:-$REPO/.venv/bin/python}"
INBOX="${H2DB_INBOX:-$HOME/h2db-inbox}"

STAMP="$(ssh "$SOURCE" readlink "$SOURCE_EXPORT/latest")"
[ -n "$STAMP" ] || { echo "na $SOURCE chybí $SOURCE_EXPORT/latest (nejdřív transfer_bundle.py export)" >&2; exit 1; }
echo "== balík $STAMP z $SOURCE"
mkdir -p "$INBOX"
rsync -a --info=stats1 "$SOURCE:$SOURCE_EXPORT/$STAMP/" "$INBOX/$STAMP/"

COMMIT="$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1]))["git_commit"])' "$INBOX/$STAMP/meta.json")"
HEAD="$(git -C "$REPO" rev-parse HEAD)"
if [ "$COMMIT" != "$HEAD" ] && [ -z "${H2DB_ALLOW_COMMIT_MISMATCH:-}" ]; then
    echo "vývoj běží na commitu $COMMIT, produkce na $HEAD: nejdřív 'git -C $REPO fetch && git -C $REPO checkout $COMMIT'" >&2
    echo "(nebo H2DB_ALLOW_COMMIT_MISMATCH=1, když je rozdíl jen v dokumentaci)" >&2
    exit 1
fi

echo "== plné texty"
mkdir -p "$REPO/data/fulltext" "$REPO/data/fulltext_clean"
rsync -a --info=stats1 "$SOURCE:$SOURCE_REPO/data/fulltext/" "$REPO/data/fulltext/"
rsync -a --info=stats1 "$SOURCE:$SOURCE_REPO/data/fulltext_clean/" "$REPO/data/fulltext_clean/"

echo "== databáze a stavové soubory"
"$PY" "$REPO/src/tools/transfer_bundle.py" install --dir "$INBOX/$STAMP" "$@"
touch "$REPO/wsgi.py"   # mod_wsgi načte aplikaci znovu
echo "== hotovo; kontrola podle doc/NASAZENI.md, odstavec 4.6"
