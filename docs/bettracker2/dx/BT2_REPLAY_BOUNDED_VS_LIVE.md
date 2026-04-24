# BT2 — Replay acotado (bounded) vs funnel live (bóveda)

## Qué es el GET admin `backtest-replay`

Es un **replay acotado para backtest / analítica**, no un simulador de paridad 1:1 con la materialización diaria de **La Bóveda**.

| Aspecto | Replay admin (`bt2_admin_backtest_replay`) | Live bóveda (`_materialize_daily_picks_snapshot` + `build_value_pool_for_snapshot`) |
|--------|-----------------------------------------------|----------------------------------------------------------------------------------------|
| Modo | `bounded_backtest` (ver `replayMeta` en la respuesta) | Producto operativo |
| Universo “candidatos” | Partidos con kickoff en el día operativo Bogotá, liga activa, excluye solo cancelados/postpuesto/abandonado/awarded | Solo `status = 'scheduled'` en la ventana del día |
| Barrido | Como máximo `max(1, max_events_per_day × 3)` IDs, orden tier + kickoff | Hasta 220 en prefilter; luego recortes y `compose_vault_daily_picks` (franjas) |
| Cuotas | Corte: `fetched_at` ≤ fin del día Bogotá | Sin corte temporal al agregar desde snapshot |
| SFS | `skip_sfs_fusion=True` | Puede fusionar si `BT2_SFS_MARKETS_FUSION_ENABLED` |
| Métrica `candidate_events` | Conteo SQL del universo replay (amplio) | **No** es el “pool live del día” |
| Métrica `eligible_events` | Eventos que entran al lote `prepared` (≤ `max_events_per_day` / día), tras corte + `event_passes_value_pool` | **No** es “todos los que pasarían valor pool en el día” |

## Herramienta de trazabilidad

`scripts/bt2_replay_exclusion_trace.py` clasifica cada `event_id` del universo replay por **primera causa** de exclusión en ese funnel (read-only, sin LLM). Sirve para interpretar `candidate_events` vs `eligible_events` **en el sentido bounded**, no para exigir igualdad con picks persistidos en `bt2_daily_picks`.

## Futuro (fuera de este documento)

Una **herramienta de parity replay** sería un artefacto aparte (endpoint o script) que reutilice explícitamente el SQL y límites del pool live, con semántica propia; no sustituye al bounded replay sin decisión de producto.
