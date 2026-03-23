#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

SERVICE_LABEL="com.copafoxkids.independent.runner"
PLIST="$HOME/Library/LaunchAgents/${SERVICE_LABEL}.plist"

usage() {
  cat <<'EOF'
Uso:
  ./run.sh start      # activa ejecución automática (launchd)
  ./run.sh stop       # detiene ejecución automática
  ./run.sh restart    # stop + start
  ./run.sh status     # estado del servicio
  ./run.sh logs       # ver logs live del runner
  ./run.sh reset      # limpieza total + reset DB (fresh start)
  ./run.sh tick       # ejecuta un tick manual ahora
  ./run.sh run-now <midnight|morning|afternoon|report>
  ./run.sh scrape ... # modo legado: event_bundle_scraper.py

Tip alias:
  alias fox='./run.sh'
  fox start

Horarios automáticos (pruebas): en .env define COPA_TICK_SLOT_* (HH:MM) y opcional COPA_FOXKIDS_TZ.
Ver README § Scheduler (launchd).
EOF
}

run_legacy_scraper() {
  export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-$(pwd)/playwright-browsers}"
  if [[ ! -d ".venv" ]]; then
    echo "Creando entorno virtual..."
    python3 -m venv .venv
  fi
  # shellcheck disable=SC1091
  source .venv/bin/activate
  if ! python -c "import playwright" 2>/dev/null; then
    echo "Instalando dependencias..."
    pip install -r requirements.txt -q
    echo "Instalando Chromium..."
    playwright install chromium
  fi
  python event_bundle_scraper.py "$@"
}

cmd="${1:-help}"
shift || true

case "$cmd" in
  start)
    ./scripts/install_launchd_autorun.sh
    ;;
  stop)
    ./scripts/uninstall_launchd_autorun.sh
    ;;
  restart)
    ./scripts/uninstall_launchd_autorun.sh
    ./scripts/install_launchd_autorun.sh
    ;;
  status)
    if launchctl list | awk '{print $3}' | grep -qx "$SERVICE_LABEL"; then
      echo "Servicio activo: $SERVICE_LABEL"
    else
      echo "Servicio inactivo: $SERVICE_LABEL"
    fi
    echo "plist: $PLIST"
    ;;
  logs)
    mkdir -p out/logs
    touch out/logs/launchd_runner.out.log out/logs/launchd_runner.err.log
    tail -f out/logs/launchd_runner.out.log out/logs/launchd_runner.err.log
    ;;
  reset)
    ./scripts/clean_fresh_start.sh
    ;;
  tick)
    ./scripts/runner_tick.sh
    ;;
  run-now)
    slot="${1:-}"
    date_arg="${2:-$(date +%Y-%m-%d)}"
    case "$slot" in
      midnight)
        FECHA="$date_arg" ./scripts/run_independent_midnight.sh
        ;;
      morning)
        FECHA="$date_arg" ./scripts/run_independent_window.sh morning
        ;;
      afternoon)
        FECHA="$date_arg" ./scripts/run_independent_window.sh afternoon
        ;;
      report)
        DAYS="${3:-7}" ./scripts/run_effectiveness_report.sh
        ;;
      *)
        echo "Uso: ./run.sh run-now <midnight|morning|afternoon|report> [YYYY-MM-DD] [days]"
        exit 1
        ;;
    esac
    ;;
  scrape)
    run_legacy_scraper "$@"
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    # Compatibilidad: si pasan argumentos sin subcomando, usar scraper legado.
    run_legacy_scraper "$cmd" "$@"
    ;;
esac
