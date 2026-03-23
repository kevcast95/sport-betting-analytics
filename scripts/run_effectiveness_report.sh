#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
./scripts/bootstrap_env.sh >/dev/null
set -a
# shellcheck disable=SC1091
source .env
set +a
python3 jobs/report_effectiveness.py --days "${DAYS:-7}" --output-dir out/reports

