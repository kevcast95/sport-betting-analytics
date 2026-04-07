#!/usr/bin/env bash
# Auto-lanzador: espera que Pass 1 termine y ejecuta Pass 5 (todas las ligas).
# Correr desde la raíz del repo:  bash scripts/bt2_atraco/auto_next_pass.sh
#
# Señal de que Pass 1 terminó: el reporte .md de Pass 1 existe en recon_results/.

set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
REPORT="$REPO/docs/bettracker2/recon_results/atraco_2023-08-01_2025-05-31.md"
LOG="$REPO/docs/bettracker2/recon_results/auto_next_pass.log"
PASS1_PID=40258   # PID del proceso de producción Pass 1

echo "[$(date '+%H:%M:%S')] Watcher iniciado — esperando Pass 1 (PID $PASS1_PID)..." | tee -a "$LOG"
echo "[$(date '+%H:%M:%S')] Señal de completado: $REPORT" | tee -a "$LOG"

# Esperar a que el proceso de Pass 1 termine
while kill -0 "$PASS1_PID" 2>/dev/null; do
    echo "[$(date '+%H:%M:%S')] Pass 1 aún corriendo... (siguiente chequeo en 3 min)" | tee -a "$LOG"
    sleep 180
done

echo "[$(date '+%H:%M:%S')] ✅ Pass 1 terminó (proceso $PASS1_PID ya no existe)." | tee -a "$LOG"

# Verificar que el reporte existe como confirmación extra
if [ -f "$REPORT" ]; then
    echo "[$(date '+%H:%M:%S')] Reporte Pass 1 confirmado: $REPORT" | tee -a "$LOG"
else
    echo "[$(date '+%H:%M:%S')] ⚠️  Reporte no encontrado — Pass 1 puede haber fallado. Revisá el log." | tee -a "$LOG"
    echo "[$(date '+%H:%M:%S')] Intentando Pass 5 de todas formas..." | tee -a "$LOG"
fi

# Pequeña pausa antes de lanzar
sleep 10

echo "[$(date '+%H:%M:%S')] 🚀 Lanzando Pass 5 (todas las ligas)..." | tee -a "$LOG"
cd "$REPO"

python3 scripts/bt2_atraco/run_atraco.py --pass 5 >> "$LOG" 2>&1

echo "[$(date '+%H:%M:%S')] ✅ Pass 5 completado. Revisá recon_results/ para el reporte." | tee -a "$LOG"
