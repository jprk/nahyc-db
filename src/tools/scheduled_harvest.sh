#!/bin/bash
# Scheduled harvesting of the monitored sources (doc/DATA_SOURCES.md, odstavec 8.17):
# one run of the sources of a cadence against the database of .env, with a backup
# before it and the states of documents applied after it. Called by the timers
# or the crontab in deploy/scheduler/ (a proposal, NOT installed); by hand:
#
#   src/tools/scheduled_harvest.sh weekly|monthly|quarterly|states|daily [--dry-run]
#
# weekly    registers of acts and of drafts (cadence `weekly` of data/monitored_sources.json)
# monthly   standards, feeds and pages (`monthly`), the state checks of ČSN/STN
#           (csn-online, normoff-stn; catalogues of standards are monthly in
#           doc/DATABASE_SCOPE.md odstavec 6) and the availability check of every source
# quarterly technical rules, methodologies, publications (`quarterly`)
# states    only the states of documents (backfill_document_states.py), on the first day
#           of every month: ČSN take effect on the first day of a month, and an edition
#           issued with a later date of effect becomes the current one that day
#           (norm_editions.py; ČSN EN 13445 of 12/2026 on 1. 1. 2027); then also the
#           consolidated versions of EU acts (as `daily`)
# daily     only the consolidated versions of the EU acts of data/eu_consolidated_acts.json
#           (CLP, REACH; refresh_eu_consolidations.py): a new one found in Cellar, the one
#           in effect made current on its day, its text downloaded from Cellar and cleaned;
#           a backup is taken only when the database is to change (CLP 1. 1. 2027);
#           then the versions of the other Czech and EU acts (refresh_act_versions.py,
#           issue #38): e-Sbírka and Cellar, a version in effect added with its text
#
# Runs one at a time (flock on .harvest.lock, waiting up to 2 hours), logs to
# logs/harvest_YYYYMM.log of the working tree. Exit status 1 when an adapter failed
# (the run goes on and the states are still applied).
set -uo pipefail

CADENCE="${1:-}"
DRY_RUN="${2:-}"
case "$CADENCE" in weekly|monthly|quarterly|states|daily) ;; *) echo "usage: $0 weekly|monthly|quarterly|states|daily [--dry-run]" >&2; exit 2;; esac
REPO="${H2DB_REPO:-$(cd "$(dirname "$0")/../.." && pwd)}"
PY="${H2DB_PYTHON:-$REPO/.venv/bin/python}"
APPLY="--apply"
[ "$DRY_RUN" = "--dry-run" ] && APPLY=""

cd "$REPO" || exit 2
mkdir -p logs
if [ -z "${H2DB_NO_LOG_REDIRECT:-}" ]; then
    exec >>"logs/harvest_$(date +%Y%m).log" 2>&1
fi
exec 9>"$REPO/.harvest.lock"
flock -w 7200 9 || { echo "$(date -Is) $CADENCE: another run holds .harvest.lock, giving up"; exit 1; }

echo "=== $(date -Is) $CADENCE ${APPLY:-(dry run)}"
status=0
if [ "$CADENCE" = daily ]; then
    # consolidated versions of EU acts; backs up the database itself, and only before a change
    "$PY" src/tools/refresh_eu_consolidations.py $APPLY ${APPLY:+--backup} || status=1
    # versions of the other Czech and EU acts (issue #38); the same backup rule
    "$PY" src/tools/refresh_act_versions.py $APPLY ${APPLY:+--backup} || status=1
    echo "=== $(date -Is) $CADENCE finished, status $status"
    exit $status
fi
if [ -n "$APPLY" ]; then
    "$PY" src/tools/backup_db.py --reason "before_harvest_$CADENCE" || exit 1
fi
if [ "$CADENCE" != states ]; then
    "$PY" src/tools/harvest_sources.py --cadence "$CADENCE" $APPLY || status=1
fi
if [ "$CADENCE" = monthly ]; then
    "$PY" src/tools/harvest_sources.py --source csn-online --source normoff-stn $APPLY || status=1
    "$PY" src/tools/check_sources.py $APPLY || status=1
fi
# repealed / not yet in effect, REPEALS relations, the dates of the last checks, editions of standards
"$PY" src/tools/backfill_document_states.py $APPLY || status=1
if [ "$CADENCE" = states ]; then
    # consolidated versions of EU acts (Cellar, text of the version in effect); the backup is above
    "$PY" src/tools/refresh_eu_consolidations.py $APPLY || status=1
    "$PY" src/tools/refresh_act_versions.py $APPLY || status=1
fi
echo "=== $(date -Is) $CADENCE finished, status $status"
exit $status
