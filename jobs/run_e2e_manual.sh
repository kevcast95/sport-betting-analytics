#!/bin/bash
# E2E manual: ejecuta cada comando paso a paso.
# Cada paso imprime su resultado en consola.
# Requiere: DB_PATH, FECHA (YYYY-MM-DD), LIMIT (opcional, default 3)

set -e
cd "$(dirname "$0")/.."
DB="${DB_PATH:-./db/sport-tracker.sqlite3}"
FECHA="${FECHA:-$(date +%Y-%m-%d)}"
LIMIT="${LIMIT:-3}"

echo "=============================================="
echo "E2E MANUAL - Pipeline completo"
echo "DB=$DB  FECHA=$FECHA  LIMIT=$LIMIT"
echo "=============================================="

echo ""
echo ">>> PASO 1: Reset DB (vaciar todo)"
python3 jobs/reset_db.py --db "$DB" -y

echo ""
echo ">>> PASO 2: Ingest (fetch + persist bundles)"
python3 jobs/ingest_daily_events.py --sport football --date "$FECHA" --db "$DB" --limit "$LIMIT"

# Obtener el daily_run_id recién creado (tras reset, AUTOINCREMENT puede dar 2, 3, etc.)
DAILY_RUN_ID=$(python3 -c "
import sqlite3, sys
conn = sqlite3.connect('$DB')
cur = conn.execute('SELECT daily_run_id FROM daily_runs ORDER BY daily_run_id DESC LIMIT 1')
row = cur.fetchone()
print(row[0] if row else 1)
" 2>/dev/null || echo "1")
echo "  (daily_run_id=$DAILY_RUN_ID)"
echo ""
echo ">>> PASO 3: Select candidates (filtra + muestra payload DS)"
python3 jobs/select_candidates.py --db "$DB" --daily-run-id $DAILY_RUN_ID --limit 20 -o candidates.json

echo ""
echo ">>> PASO 4: Simular respuesta DS → crear picks.json manualmente"
echo "   Ejemplo: echo '{\"picks\":[{\"event_id\":123,\"market\":\"1X2\",\"selection\":\"1\",\"picked_value\":2.1}]}' > picks.json"
echo "   Luego: python3 jobs/persist_picks.py --daily-run-id $DAILY_RUN_ID --db $DB --input-json picks.json"
echo ""
read -p "¿Crear picks.json de ejemplo y persistir? [y/N]: " doit
if [ "$doit" = "y" ] || [ "$doit" = "Y" ]; then
  if [ -f candidates.json ]; then
    FIRST_EID=$(python3 -c "import json; d=json.load(open('candidates.json')); eids=d.get('selected',[]); print(eids[0] if eids else 0)" 2>/dev/null || echo "0")
    if [ -n "$FIRST_EID" ] && [ "$FIRST_EID" != "0" ]; then
      echo "[{\"event_id\":$FIRST_EID,\"market\":\"1X2\",\"selection\":\"1\",\"picked_value\":2.1}]" > picks.json
      echo "Creado picks.json con event_id=$FIRST_EID"
      python3 jobs/persist_picks.py --daily-run-id $DAILY_RUN_ID --db "$DB" --input-json picks.json
    else
      echo "No hay candidatos en candidates.json. Crea picks.json manualmente."
    fi
  else
    echo "No existe candidates.json. Ejecuta select_candidates primero."
  fi
fi

echo ""
echo ">>> PASO 5: Validar picks (solo si hay partidos ya finalizados)"
python3 jobs/validate_picks.py --db "$DB" --daily-run-id $DAILY_RUN_ID

echo ""
echo "=============================================="
echo "E2E COMPLETO"
echo "=============================================="
