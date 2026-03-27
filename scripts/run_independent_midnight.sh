#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
./scripts/bootstrap_env.sh >/dev/null
# Exportar .env en esta shell para que python vea DEEPSEEK/TELEGRAM.
set -a
# shellcheck disable=SC1091
source .env
set +a
export TZ="${COPA_FOXKIDS_TZ:-America/Bogota}"
DATE="${FECHA:-$(date +%Y-%m-%d)}"
SPORT="${1:-football}"
python3 jobs/independent_runner.py --mode midnight --sport "$SPORT" --date "$DATE"

