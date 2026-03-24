#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
./scripts/bootstrap_env.sh >/dev/null
set -a
# shellcheck disable=SC1091
source .env
set +a
python3 jobs/report_effectiveness.py --days "${DAYS:-7}" --output-dir out/reports

# Aviso Telegram (fallback móvil): resumen corto al terminar reporte.
python3 - <<'PY'
from __future__ import annotations
import json
from pathlib import Path

report_path = Path("out/reports/effectiveness_latest.json")
msg_path = Path("out/telegram_message.txt")
if not report_path.exists():
    raise SystemExit(0)

try:
    data = json.loads(report_path.read_text(encoding="utf-8"))
except Exception:
    raise SystemExit(0)

tot = data.get("totals") if isinstance(data.get("totals"), dict) else {}
start = data.get("range_start") or "?"
end = data.get("range_end") or "?"
issued = tot.get("issued", 0)
settled = tot.get("settled", 0)
wr = tot.get("win_rate")
roi = tot.get("roi_unit")
gen = data.get("generated_at_utc") or "?"

def pct(v):
    if v is None:
        return "n/d"
    try:
        return f"{float(v)*100:.1f}%"
    except Exception:
        return "n/d"

by_conf = data.get("by_confidence") if isinstance(data.get("by_confidence"), dict) else {}
ORDER = ["Alta", "Media-Alta", "Media", "Baja", "sin_confianza"]

def _conf_sort(k):
    try:
        return (ORDER.index(k), k)
    except ValueError:
        return (50, k)

conf_lines = []
for key, row in sorted(by_conf.items(), key=lambda kv: _conf_sort(kv[0])):
    if not isinstance(row, dict):
        continue
    if int(row.get("issued") or 0) == 0:
        continue
    s = int(row.get("settled") or 0)
    w = int(row.get("wins") or 0)
    wr_c = row.get("win_rate")
    conf_lines.append(f"· {key}: {w}/{s} settled · WR {pct(wr_c)}")

conf_block = ""
if conf_lines:
    conf_block = "📊 Por confianza:\n" + "\n".join(conf_lines[:8]) + "\n"
    if len(conf_lines) > 8:
        conf_block += f"… +{len(conf_lines) - 8} filas más en JSON\n"

text = (
    "✅ Reporte de efectividad listo\n"
    f"📅 Ventana: {start} → {end}\n"
    f"🎯 Picks emitidos: {issued} · Settled: {settled}\n"
    f"📈 Win rate: {pct(wr)} · ROI unitario: {pct(roi)}\n"
    f"{conf_block}"
    f"🕒 Generado: {gen}\n"
)
msg_path.parent.mkdir(parents=True, exist_ok=True)
msg_path.write_text(text, encoding="utf-8")
PY

python3 jobs/send_telegram_message.py --message-file out/telegram_message.txt --parse-mode ""

