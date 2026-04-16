# Sprint 06.3 — EJECUCION cierre normativo F2 (T-266)

> Norma: [`DECISIONES_CIERRE_F2_S6_3_FINAL.md`](./DECISIONES_CIERRE_F2_S6_3_FINAL.md).  
> Tasks: [`TASKS_CIERRE_F2_S6_3.md`](./TASKS_CIERRE_F2_S6_3.md).

## Implementación BE (T-258–T-264)

| Entrega | Ubicación |
|---------|-----------|
| **T-258** | `apps/api/bt2_f2_league_constants.py`; runbook [`docs/bettracker2/runbooks/bt2_f2_official_leagues.md`](../../runbooks/bt2_f2_official_leagues.md); `.env.example` (`BT2_F2_OFFICIAL_LEAGUE_IDS`). |
| **T-259–T-262** | `apps/api/bt2_pool_eligibility_v1.py` — versión auditoría `pool-eligibility-f2-v1`, tier Base/A, FT_1X2 + 1 core, Tier A raw obligatorio, lineups opcionales vía `BT2_F2_TIER_A_REQUIRE_LINEUPS`, campo `causal_audit_class` en `detail_json`. |
| **T-263** | `GET /bt2/admin/analytics/f2-pool-eligibility-metrics` — modelo `Bt2AdminF2PoolMetricsOut` en `bt2_schemas.py`; lógica `apps/api/bt2_f2_metrics.py`. |
| **T-264** | `scripts/bt2_cdm/job_f2_closure_report.py` |

### Compatibilidad RealDict

Ajustes en `bt2_dsr_context_queries.fetch_odds_ingest_meta` y `bt2_dsr_ds_input_builder` (payload raw) para cursores `RealDictCursor` al evaluar en jobs/API.

---

## Evidencia — primer run T-264 (local)

**Comando:** `python3 scripts/bt2_cdm/job_f2_closure_report.py --days 14`

**Fecha de captura:** 2026-04-15 (entorno dev del repo; `BT2_DATABASE_URL` local).

**Resultado (extracto):** en la ventana analizada, los candidatos en las 5 ligas resueltas quedaron con descarte dominante **`MISSING_VALID_ODDS`** (sin mercado canónico completo en snapshot para pasar `event_passes_value_pool`), no `INSUFFICIENT_MARKET_FAMILIES`. Umbrales 60% / 40%: **no pasan** — coherente con datos de ingest actuales, no con un fallo del script.

```json
{
  "league_bt2_ids_resolved": [45751, 48313, 51884, 53065, 53391],
  "window_from": "2026-04-02",
  "window_to": "2026-04-15",
  "metrics_global": {
    "candidate_events_count": 60,
    "eligible_official_count": 0,
    "eligible_relaxed_count": 0,
    "pool_eligibility_rate_official_pct": 0.0,
    "pool_eligibility_rate_relaxed_pct": 0.0,
    "primary_discard_breakdown_official": { "MISSING_VALID_ODDS": 60 }
  },
  "thresholds": {
    "pass_global_60": false,
    "pass_all_leagues_40": false
  },
  "insufficient_market_families_dominant": false
}
```

**API (misma lógica):**  
`GET http://127.0.0.1:8000/bt2/admin/analytics/f2-pool-eligibility-metrics?days=14`  
Header: `X-BT2-Admin-Key: <BT2_ADMIN_API_KEY>`

---

## FE (T-265)

Pendiente: consumir `Bt2AdminF2PoolMetricsOut` en web cuando BE estabilice contrato en cliente.
