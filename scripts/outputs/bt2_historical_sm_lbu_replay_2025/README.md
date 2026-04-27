# BT2 historical_sm_lbu (2025) — compact outputs

Corrida exploratoria read-only con contrato temporal T-60 desde `raw_sportmonks_fixtures`.

## Malla mensual 2025 (12 bloques + consolidado)

Orquestador: `../../bt2_historical_sm_lbu_2025_monthly_batch.py` (importa `run()` del prototipo, mismo T-60).

```bash
cd /Users/kevcast/Projects/scrapper
python3 scripts/bt2_historical_sm_lbu_2025_monthly_batch.py
```

Genera:
- `blocks_2025_monthly/summary_YYYY-MM.json` — un resumen por mes
- `consolidated_2025_monthly.json` y `consolidated_2025_monthly.csv` — tablas comparativas (si un mes devuelve 0 fixtures, es **hueco de CDM** en la BD, no fallo del corte T-60).

## Ejemplo: un solo mes (muestreo acotado)

```bash
cd /Users/kevcast/Projects/scrapper
python3 scripts/bt2_historical_sm_lbu_replay_prototype.py \
  --day-from 2025-01-01 \
  --day-to 2025-01-31 \
  --max-fixtures 500 \
  --summary-only \
  --summary-out scripts/outputs/bt2_historical_sm_lbu_replay_2025/jan_2025_summary.json \
  --fixtures-csv scripts/outputs/bt2_historical_sm_lbu_replay_2025/jan_2025_fixtures.csv \
  --fixtures-ndjson scripts/outputs/bt2_historical_sm_lbu_replay_2025/jan_2025_fixtures.ndjson \
  -o scripts/outputs/bt2_historical_sm_lbu_replay_2025/jan_2025_summary_stdout.json
```

- `jan_2025_summary.json` — resumen agregado (sin `fixtures[]`).
- `jan_2025_fixtures.csv` / `jan_2025_fixtures.ndjson` — detalle por fixture.
