# Sprint 06.3 — EJECUCION cierre normativo F2 (T-266)

> Norma: [`DECISIONES_CIERRE_F2_S6_3_FINAL.md`](./DECISIONES_CIERRE_F2_S6_3_FINAL.md).  
> Tasks: [`TASKS_CIERRE_F2_S6_3.md`](./TASKS_CIERRE_F2_S6_3.md).

## Definición operativa de candidatos (KPI §6)

**Denominador del KPI F2** en API y script (`fetch_f2_event_ids_in_window` en `bt2_f2_metrics.py`): **todos** los `bt2_events` cuyo `league_id` está en las **5 ligas F2** resueltas y cuya fecha de **kickoff en America/Bogota** cae en la ventana `[window_from, window_to]` (inclusive). **No** se restringe a eventos con fila en `bt2_daily_picks`.

**Ancla de ventana rolling** (cuando no se pasa `operatingDayKey`): fin = `MAX(operating_day_key)` en `bt2_daily_picks` si existe; si no hay picks, fin = **fecha actual en Bogotá** (para que el KPI sea computable).

Texto resumido en respuesta API: campo `noteEs` de `Bt2AdminF2PoolMetricsOut` / payload JSON del job.

### Acuerdos explícitos cierre F2 — S6.3 (acta 2026-04-15)

| Tema | Decisión |
|------|----------|
| Universo candidatos KPI | **B** — todos los `bt2_events` de las 5 ligas en la ventana (kickoff Bogotá), no solo con pick. |
| Umbrales 60 % / 40 % | **A** — meta operativa; el acta S6.3 cierra con **instrumento + evidencia honesta** aunque no se cumplan. |
| Tier A refuerzo mercados | **A** — lo actual (raw obligatorio en A, sin más familias mínimas extra) **sí** para este cierre. |
| `BT2_F2_TIER_A_REQUIRE_LINEUPS` | **A** — **apagado** (incl. staging/prod) hasta cobertura estable. |
| Auditoría §3 | **A** — se acepta `causal_audit_class` actual; **sin** mapeo 1:1 a las 4 categorías literales en este cierre. |
| `available: false` SM | **A** — vale proxy `raw_fixture_missing` / `lineups_ok`. |
| Job `job_pool_eligibility_audit` | **A** — persistencia **siempre** con umbral oficial **min_fam = 2**; el env `BT2_POOL_ELIGIBILITY_MIN_FAMILIES=1` **no** define la verdad append-only en BD. |

### Frase para acta

> S6.3 — cierre F2 extendido: instrumentación y evidencia completas según acuerdos del 2026-04-15; umbrales §6 como meta operativa, no condición de cierre.

---

## Implementación BE (T-258–T-264)

| Entrega | Ubicación |
|---------|-----------|
| **T-258** | `apps/api/bt2_f2_league_constants.py`; runbook [`docs/bettracker2/runbooks/bt2_f2_official_leagues.md`](../../runbooks/bt2_f2_official_leagues.md); `.env.example` (`BT2_F2_OFFICIAL_LEAGUE_IDS`). |
| **T-259–T-262** | `apps/api/bt2_pool_eligibility_v1.py` — versión auditoría `pool-eligibility-f2-v1`, tier Base/A, FT_1X2 + 1 core, Tier A raw obligatorio, lineups opcionales vía `BT2_F2_TIER_A_REQUIRE_LINEUPS`, campo `causal_audit_class` en `detail_json`. |
| **T-263** | `GET /bt2/admin/analytics/f2-pool-eligibility-metrics` — modelo `Bt2AdminF2PoolMetricsOut` en `bt2_schemas.py`; lógica `apps/api/bt2_f2_metrics.py` (incl. `core_family_coverage_counts`: `ft_1x2_complete`, `second_core_family`, `raw_present`, `lineups_ok`). |
| **T-264** | `scripts/bt2_cdm/job_f2_closure_report.py` (default **`--days 30`**). |

### Compatibilidad RealDict

Ajustes en `bt2_dsr_context_queries.fetch_odds_ingest_meta` y `bt2_dsr_ds_input_builder` (payload raw) para cursores `RealDictCursor` al evaluar en jobs/API.

---

## Evidencia — run canónico T-264 (ventana **30 días**)

**Comando:** `python3 scripts/bt2_cdm/job_f2_closure_report.py --days 30`

**Norma:** `DECISIONES_CIERRE_F2_S6_3_FINAL.md` §6 L257–L260 (ventana 30d).

**Captura:** 2026-04-15 — entorno local con `BT2_DATABASE_URL`; JSON **actualizado** tras acuerdo candidatos = `bt2_events` (kickoff Bogotá) + job auditoría siempre oficial = 2.

**API (misma lógica, ventana 30d rolling):**  
`GET …/bt2/admin/analytics/f2-pool-eligibility-metrics?days=30`  
Header: `X-BT2-Admin-Key: <BT2_ADMIN_API_KEY>`

```json
{
  "league_bt2_ids_resolved": [45751, 48313, 51884, 53065, 53391],
  "window_from": "2026-03-17",
  "window_to": "2026-04-15",
  "operating_day_key_filter": null,
  "metrics_global": {
    "candidate_events_count": 253,
    "eligible_official_count": 0,
    "eligible_relaxed_count": 0,
    "pool_eligibility_rate_official_pct": 0.0,
    "pool_eligibility_rate_relaxed_pct": 0.0,
    "primary_discard_breakdown_official": {
      "MISSING_VALID_ODDS": 253
    },
    "core_family_coverage_counts": {
      "ft_1x2_complete": 0,
      "second_core_family": 0,
      "raw_present": 3,
      "lineups_ok": 3
    }
  },
  "metrics_by_league": [
    {
      "league_id": 53065,
      "league_name": "Bundesliga",
      "candidate_events_count": 216,
      "pool_eligibility_rate_official_pct": 0.0,
      "pass_league_40": false
    },
    {
      "league_id": 48313,
      "league_name": "La Liga",
      "candidate_events_count": 10,
      "pool_eligibility_rate_official_pct": 0.0,
      "pass_league_40": false
    },
    {
      "league_id": 51884,
      "league_name": "Ligue 1",
      "candidate_events_count": 7,
      "pool_eligibility_rate_official_pct": 0.0,
      "pass_league_40": false
    },
    {
      "league_id": 45751,
      "league_name": "Premier League",
      "candidate_events_count": 10,
      "pool_eligibility_rate_official_pct": 0.0,
      "pass_league_40": false
    },
    {
      "league_id": 53391,
      "league_name": "Serie A",
      "candidate_events_count": 10,
      "pool_eligibility_rate_official_pct": 0.0,
      "pass_league_40": false
    }
  ],
  "thresholds": {
    "target_global_official_pct": 60.0,
    "target_per_league_official_pct": 40.0,
    "pass_global_60": false,
    "pass_all_leagues_40": false
  },
  "insufficient_market_families_dominant": false,
  "note_es": "KPI oficial = re-evaluación en vivo con min_fam=2 (norma F2). Relajado = min_fam=1 (observabilidad §5). Candidatos = todos los bt2_events de las 5 ligas F2 con kickoff en ventana (fecha local America/Bogota). Umbrales 60/40 = meta operativa, no bloqueo de acta (S6.3). Fin ventana rolling = MAX(operating_day_key) en picks si existe; si no, hoy Bogota."
}
```

---

## Muestra corta histórica (14 días, no canónica)

Ejecución de referencia **2026-04-15** con `--days 14` solo para depuración local; **no** sustituye la evidencia **30d** de §6.

**Comando usado:** `python3 scripts/bt2_cdm/job_f2_closure_report.py --days 14`

**Extracto (ejemplo):** descarte dominante observado **`MISSING_VALID_ODDS`**; umbrales 60% / 40% **no pasan** — coherente con datos de ingest, no con fallo del script.

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

---

## FE (T-265)

**Estado:** implementado.

- Vista: `apps/web/src/pages/AdminFase1OperationalPage.tsx` — sección **«4 · Pool elegibilidad F2»** (`data-testid="fase1-f2-block"`), datos desde `fetchBt2AdminF2PoolEligibilityMetrics` (oficial vs relajado, umbrales, desglose, por liga).
- Contrato TS: `apps/web/src/lib/bt2Types.ts` — `Bt2AdminF2PoolMetricsOut`.
- Test: `apps/web/src/pages/AdminFase1OperationalPage.test.tsx`.

**Evidencia visual:** captura de pantalla en entorno real **opcional** (no bloquea merge técnico).
