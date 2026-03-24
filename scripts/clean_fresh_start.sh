#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== Clean fresh start =="

# 1) Detener autorun si existe
./scripts/uninstall_launchd_autorun.sh || true

# 2) Limpiar artefactos runtime / salidas
rm -rf out/batches out/reports out/state out/logs || true
rm -f out/telegram_*.txt out/telegram_*.json out/payload_*.json out/*.txt out/*.json || true
mkdir -p out

# 3) Limpiar artefactos legacy en raíz
rm -f candidates*.json picks*.json picks_filtered.json || true
rm -f scrapper.db scrapper.db-shm scrapper.db-wal || true

# 4) Reinicio real de DB para volver a DR=1
rm -f db/sport-tracker.sqlite3 db/sport-tracker.sqlite3-shm db/sport-tracker.sqlite3-wal db/sport-tracker-test.sqlite3 || true

echo "OK limpieza completa."
echo "Siguiente paso: ./scripts/install_launchd_autorun.sh"

