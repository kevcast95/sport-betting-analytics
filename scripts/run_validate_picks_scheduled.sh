#!/usr/bin/env bash
# Valida picks 1X2 pendientes según cohorte del pipeline (hora local COPA_FOXKIDS_TZ).
#
# Uso:
#   ./scripts/run_validate_picks_scheduled.sh yesterday_evening
#     → picks con created_at local AYER en [16, 24) (corrida tarde del día anterior).
#     → encajar con slot medianoche (00:00), ANTES de ingest.
#
#   ./scripts/run_validate_picks_scheduled.sh today_morning
#     → picks con created_at local HOY en [8, 16) (corrida mañana del mismo día).
#     → encajar con slot tarde (16:00), ANTES del análisis tarde.
#
set -euo pipefail
cd "$(dirname "$0")/.."
KIND="${1:?Uso: yesterday_evening|today_morning}"
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi
export TZ="${COPA_FOXKIDS_TZ:-America/Bogota}"
ROOT="$(pwd)"
DB="${DB_PATH:-$ROOT/db/sport-tracker.sqlite3}"
TODAY="$(python3 -c "import os; from datetime import datetime; from zoneinfo import ZoneInfo; z=ZoneInfo(os.environ.get('TZ','America/Bogota')); print(datetime.now(z).date().isoformat())")"
YESTERDAY="$(python3 -c "import os; from datetime import datetime, timedelta; from zoneinfo import ZoneInfo; z=ZoneInfo(os.environ.get('TZ','America/Bogota')); print((datetime.now(z).date()-timedelta(days=1)).isoformat())")"

MIN_E="${ALTEA_VALIDATE_AFTERNOON_HOUR_MIN:-16}"
MAX_E="${ALTEA_VALIDATE_AFTERNOON_HOUR_MAX_EXCL:-24}"
MIN_M="${ALTEA_VALIDATE_MORNING_HOUR_MIN:-8}"
MAX_M="${ALTEA_VALIDATE_MORNING_HOUR_MAX_EXCL:-16}"

if [[ "$KIND" == "yesterday_evening" ]]; then
  python3 jobs/validate_picks.py --db "$DB" --timezone "$TZ" \
    --only-created-local-on "$YESTERDAY" \
    --only-created-local-hour-min "$MIN_E" \
    --only-created-local-hour-max-excl "$MAX_E"
elif [[ "$KIND" == "today_morning" ]]; then
  python3 jobs/validate_picks.py --db "$DB" --timezone "$TZ" \
    --only-created-local-on "$TODAY" \
    --only-created-local-hour-min "$MIN_M" \
    --only-created-local-hour-max-excl "$MAX_M"
else
  echo "Valor inválido: $KIND (use yesterday_evening|today_morning)" >&2
  exit 2
fi
