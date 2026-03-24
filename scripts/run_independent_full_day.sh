#!/usr/bin/env bash
# Análisis del día completo (sin franjas mañana/tarde) + persistencia de picks por defecto.
# Requiere out/candidates_${FECHA}_select.json (tras midnight / ingest + select_candidates).
set -euo pipefail
cd "$(dirname "$0")/.."
./scripts/bootstrap_env.sh >/dev/null
set -a
# shellcheck disable=SC1091
source .env
set +a
export TZ="${COPA_FOXKIDS_TZ:-America/Bogota}"
DATE="${FECHA:-$(date +%Y-%m-%d)}"
python3 jobs/independent_runner.py --mode full_day --date "$DATE" "$@"
