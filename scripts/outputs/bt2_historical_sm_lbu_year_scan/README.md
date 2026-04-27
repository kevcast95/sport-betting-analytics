# BT2 — barrido `historical_sm_lbu` (2023–2025)

Read-only. Mismo contrato **T-60** que `bt2_historical_sm_lbu_replay_prototype.py`.

## Regenerar

Barrido completo (36 meses):

```bash
cd /Users/kevcast/Projects/scrapper
python3 scripts/bt2_historical_sm_lbu_year_scan.py
```

Reanudar tras corte (reusa `blocks/summary_*.json` existentes):

```bash
python3 scripts/bt2_historical_sm_lbu_year_scan.py --resume
```

Solo reescribir consolidado desde bloques ya guardados (sin BD):

```bash
python3 scripts/bt2_historical_sm_lbu_year_scan.py --consolidate-only
```

## Salidas

- `blocks/summary_YYYY-MM.json` — resumen por mes (+ inventario SQL liviano).
- `year_scan_consolidated.json` / `year_scan_consolidated.csv` — 36 filas (12×3 años) + agregados por año + `verdict_por_ano`.

**Nota:** `sql_n_join` y `n_fixtures` de `run()` deben coincidir; si no, revisar join o ventana.
