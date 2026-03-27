#!/usr/bin/env bash
# Valida picks pending contra SofaScore para TODO el contenido pendiente en DB.
# Criterio: no hay filtros por ventana/fecha; validate_picks.py ya selecciona
# picks con status='pending' y sin pick_results (o con outcome='pending').
#
# Útil en 00:00 para corregir reprogramaciones/cancelaciones tardías.

set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

export TZ="${COPA_FOXKIDS_TZ:-America/Bogota}"
ROOT="$(pwd)"
DB="${DB_PATH:-$ROOT/db/sport-tracker.sqlite3}"

python3 jobs/validate_picks.py --db "$DB" --timezone "$TZ"

