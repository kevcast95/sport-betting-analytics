#!/usr/bin/env bash
# Uso: FECHA=2026-03-22 ./scripts/run_slot_window.sh morning|afternoon
# Lee siempre out/candidates_${FECHA}_select.json (compartido por las dos ventanas del día).
set -euo pipefail
cd "$(dirname "$0")/.."
SLOT="${1:?Uso: morning o afternoon}"
FECHA="${FECHA:-$(date +%Y-%m-%d)}"
TZ="${COPA_FOXKIDS_TZ:-America/Bogota}"
IN="out/candidates_${FECHA}_select.json"
case "$SLOT" in
  morning|m|1)  SPLIT_SLOT="morning";  OUT="out/candidates_${FECHA}_exec_08h.json" ;;
  afternoon|a|2|p) SPLIT_SLOT="afternoon"; OUT="out/candidates_${FECHA}_exec_16h.json" ;;
  *) echo "SLOT debe ser morning o afternoon" >&2; exit 1 ;;
esac
if [[ ! -f "$IN" ]]; then
  echo "Falta $IN — ejecuta select_candidates con -o $IN tras ingest." >&2
  exit 1
fi
python3 jobs/event_splitter.py -i "$IN" -o "$OUT" --date "$FECHA" --slot "$SPLIT_SLOT" --timezone "$TZ"
echo "OK $OUT"
