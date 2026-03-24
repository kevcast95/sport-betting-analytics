#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ ! -f ".env" ]]; then
  echo "Falta .env en $(pwd)" >&2
  exit 1
fi

set -a
source .env
set +a

missing=()
for v in DEEPSEEK_API_KEY TELEGRAM_BOT_TOKEN TELEGRAM_CHAT_ID DS_CHAT_MODEL DS_ANALYSIS_MODEL; do
  if [[ -z "${!v:-}" ]]; then
    missing+=("$v")
  fi
done

if (( ${#missing[@]} > 0 )); then
  echo "Variables faltantes en .env: ${missing[*]}" >&2
  exit 1
fi

echo "OK env cargado."
echo "DS chat model: $DS_CHAT_MODEL"
echo "DS analysis model: $DS_ANALYSIS_MODEL"

