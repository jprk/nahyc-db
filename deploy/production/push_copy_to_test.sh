#!/usr/bin/env bash
# Kopie produkce pro testovací web (doc/NASAZENI.md, odstavec 6): spouští se NA PRODUKCI
# (ručně nebo časovačem h2db-copy-to-test.timer). Vytvoří balík s databází a stavovými
# soubory, pošle ho s novými plnými texty na vývojový stroj (nahyc.fd.cvut.cz) a tam ho
# nainstaluje do databáze testovacího webu (h2regdocs; před přepsáním se zálohuje).
# Spojení navazuje produkce: vývojový stroj se na produkci nedostane (síť ZČU).
#
# Proměnné (výchozí hodnoty v závorce):
#   H2DB_TEST            účet na vývojovém stroji (laborator@nahyc.fd.cvut.cz)
#   H2DB_TEST_REPO       pracovní strom testovacího webu (/home/laborator/DEVEL/nahyc-h2db)
#   H2DB_TEST_INBOX      kam balík uložit (/home/laborator/h2db-from-production)
#   H2DB_REPO            pracovní strom na produkci (adresář nad deploy/)
#   H2DB_EXPORT          adresář balíků na produkci ($HOME/h2db-export)
set -euo pipefail

TEST="${H2DB_TEST:-laborator@nahyc.fd.cvut.cz}"
TEST_REPO="${H2DB_TEST_REPO:-/home/laborator/DEVEL/nahyc-h2db}"
TEST_INBOX="${H2DB_TEST_INBOX:-/home/laborator/h2db-from-production}"
REPO="${H2DB_REPO:-$(cd "$(dirname "$0")/../.." && pwd)}"
PY="${H2DB_PYTHON:-$REPO/.venv/bin/python}"
EXPORT="${H2DB_EXPORT:-$HOME/h2db-export}"

echo "=== $(date -Is) kopie produkce na $TEST"
"$PY" "$REPO/src/tools/transfer_bundle.py" export --dir "$EXPORT"
STAMP="$(readlink "$EXPORT/latest")"
ssh "$TEST" mkdir -p "$TEST_INBOX"
rsync -a --info=stats1 "$EXPORT/$STAMP/" "$TEST:$TEST_INBOX/$STAMP/"
rsync -a --info=stats1 "$REPO/data/fulltext/" "$TEST:$TEST_REPO/data/fulltext/"
rsync -a --info=stats1 "$REPO/data/fulltext_clean/" "$TEST:$TEST_REPO/data/fulltext_clean/"
ssh "$TEST" "$TEST_REPO/.venv/bin/python" "$TEST_REPO/src/tools/transfer_bundle.py" install \
    --dir "$TEST_INBOX/$STAMP" --replace-db
# staré balíky na produkci: ponecháme posledních 8
ls -1d "$EXPORT"/20* 2>/dev/null | sort | head -n -8 | xargs -r rm -rf
echo "=== $(date -Is) hotovo"
