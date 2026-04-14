# Runbook — Job evaluación oficial de picks (S6.3 / T-234)

## Objetivo

Cerrar el loop **modelo vs resultado oficial CDM** (`bt2_events`), sin usar liquidación del usuario (`bt2_picks`). Contrato: **ACTA T-244** / **D-06-050**.

## Precondiciones

1. **Migración aplicada** — existe `bt2_pick_official_evaluation` (revisión Alembic `h2a3b4c5d6e7`).
2. **`BT2_DATABASE_URL`** — URL sync Postgres (`postgresql://…` o `postgresql+asyncpg://…` normalizada por el script).
3. **CDM actualizado** — `bt2_events` con `status` y `result_home` / `result_away` coherentes tras ingest (p. ej. `normalize_fixtures` / cadena SportMonks).

## Ejecución manual

Desde la raíz del repo:

```bash
export BT2_DATABASE_URL='postgresql://USER:PASS@HOST:5432/DB'
python3 scripts/bt2_cdm/job_official_pick_evaluation.py
```

- Primera fase: **backfill** (una fila de evaluación por `bt2_daily_picks` aún sin enrolar).
- Segunda fase: **evaluate** — solo filas en `pending_result`; no sobrescribe estados finales.

### Opciones útiles

| Flag | Efecto |
|------|--------|
| `--dry-run` | Cuenta inserciones/cierres posibles sin `COMMIT`. |
| `--limit-backfill N` / `--limit-evaluate N` | Lotes acotados (pruebas o cron incremental). |
| `--backfill-only` / `--evaluate-only` | Una sola fase (no usar ambas a la vez). |
| `--metrics-only` | Solo imprime métricas globales (T-233). |
| `--metrics-only --metrics-day YYYY-MM-DD` | Métricas filtradas por día operativo. |

Tras una corrida normal (sin `--metrics-only`), el script imprime también un bloque **`metrics_global`** con pendientes, hit rate sobre scored, void, no evaluable y desglose de motivos.

## Lectura de estados (SQL rápido)

```sql
SELECT evaluation_status, COUNT(*) FROM bt2_pick_official_evaluation GROUP BY 1;
```

## API admin (misma semántica que métricas del job)

`GET /bt2/admin/analytics/official-evaluation-loop?operatingDayKey=YYYY-MM-DD` (opcional)  
Header: `X-BT2-Admin-Key: <BT2_ADMIN_API_KEY>`

Respuesta: contadores + `hitRateOnScoredPct` (solo hit+miss) + `noEvaluableByReason`.

## Cron sugerido (orientativo)

Tras actualizar fixtures/resultados CDM, ejecutar el job cada 15–60 min o post-ingest. Ajustar según volumen y latencia deseada.
