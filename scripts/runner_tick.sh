#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Misma shell: horarios de prueba y TZ desde .env (bootstrap_env corre en subshell y no exporta aquí).
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi
export TZ="${COPA_FOXKIDS_TZ:-America/Bogota}"

# Producción por defecto. Para pruebas, en .env (mismo formato HH:MM, TZ de COPA_FOXKIDS_TZ):
#   COPA_TICK_SLOT_MIDNIGHT=09:05
#   COPA_TICK_SLOT_MORNING=09:10
#   COPA_TICK_SLOT_AFTERNOON=09:15
#   COPA_TICK_SLOT_REPORT=09:20
SLOT_MIDNIGHT="${COPA_TICK_SLOT_MIDNIGHT:-00:00}"
SLOT_MORNING="${COPA_TICK_SLOT_MORNING:-05:00}"
SLOT_AFTERNOON="${COPA_TICK_SLOT_AFTERNOON:-13:00}"
SLOT_REPORT="${COPA_TICK_SLOT_REPORT:-23:55}"

DATE="$(date +%Y-%m-%d)"
HM="$(date +%H:%M)"
STATE_DIR="out/state"
mkdir -p "$STATE_DIR"

run_once_per_day() {
  local slot="$1"      # midnight|05h|13h
  local cmd="$2"
  local stamp="$STATE_DIR/last_${slot}.txt"
  local last=""
  if [[ -f "$stamp" ]]; then
    last="$(cat "$stamp" || true)"
  fi
  if [[ "$last" == "$DATE" ]]; then
    return 0
  fi
  echo "[$(date +%F' '%T)] running slot=$slot date=$DATE"
  eval "$cmd"
  echo "$DATE" > "$stamp"
}

if [[ "$HM" == "$SLOT_MIDNIGHT" ]]; then
  # Primero: liquidar picks de la corrida tarde del día anterior (creación local ~16:00–23:59).
  run_once_per_day "midnight" "./scripts/run_validate_picks_scheduled.sh yesterday_evening && ./scripts/run_validate_picks_pending_all.sh && FECHA=\"$DATE\" ./scripts/run_independent_midnight.sh football && FECHA=\"$DATE\" ./scripts/run_independent_midnight.sh tennis"
elif [[ "$HM" == "$SLOT_MORNING" ]]; then
  run_once_per_day "05h" "FECHA=\"$DATE\" ./scripts/run_independent_window.sh morning football && FECHA=\"$DATE\" ./scripts/run_independent_window.sh morning tennis"
elif [[ "$HM" == "$SLOT_AFTERNOON" ]]; then
  # Primero: liquidar picks de la corrida mañana de HOY (creación local ~05:00–12:59).
  run_once_per_day "13h" "./scripts/run_validate_picks_scheduled.sh today_morning && FECHA=\"$DATE\" ./scripts/run_independent_window.sh afternoon football && FECHA=\"$DATE\" ./scripts/run_independent_window.sh afternoon tennis"
elif [[ "$HM" == "$SLOT_REPORT" ]]; then
  run_once_per_day "report" "DAYS=7 ./scripts/run_effectiveness_report.sh"
fi

