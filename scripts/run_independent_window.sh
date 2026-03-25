#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
SLOT="${1:?Uso: morning|afternoon}"
SPORT="${2:-football}"
./scripts/bootstrap_env.sh >/dev/null
# Exportar .env en esta shell para que python vea DEEPSEEK/TELEGRAM.
set -a
# shellcheck disable=SC1091
source .env
set +a
export TZ="${COPA_FOXKIDS_TZ:-America/Bogota}"
DATE="${FECHA:-$(date +%Y-%m-%d)}"
python3 jobs/independent_runner.py --mode window --sport "$SPORT" --slot "$SLOT" --date "$DATE" --persist-picks

