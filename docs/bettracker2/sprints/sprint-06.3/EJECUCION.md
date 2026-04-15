# Sprint 06.3 — EJECUCION

> **T-245:** regresión CI. **T-246–T-253:** cierre operativo real + mínimo paralelo F2 (este archivo).  
> **TASKS:** [`TASKS.md`](./TASKS.md) · **Cierre:** [`TASKS_CIERRE_S6_3.md`](./TASKS_CIERRE_S6_3.md) · **Handoff:** [`HANDOFF_CIERRE_S6_3.md`](./HANDOFF_CIERRE_S6_3.md) · **UI Fase 1:** [`EJECUCION_UI_FASE1.md`](./EJECUCION_UI_FASE1.md).

---

## T-245 — Comandos ejecutados (OK)

| Ámbito | Comando | Resultado |
|--------|---------|-----------|
| API BT2 | `python3 -m unittest discover -s apps/api -p '*_test.py'` (desde raíz del repo) | **78 tests**, OK |
| Web | `npm run test` en `apps/web` | **26 archivos / 127 tests**, OK |
| Web | `npm run build` en `apps/web` | `tsc -b && vite build`, OK |

**Ajuste en regresión:** `bt2_sprint06_test.TestDsrStub.test_stub_prefers_1x2` — el test exige **`1X2`** en la narrativa del stub (`bt2_dsr_suggest.py`).

## DoD por US (slice principal Fase 1)

| US | Verificación breve |
|----|-------------------|
| **US-BE-049** … **US-FE-061** | Ver tabla en commit T-245 / código referenciado en `TASKS.md`. |

## Check cierre Sprint 06.3 (slice principal)

| Ítem | Estado |
|------|--------|
| Evidencia de loop con picks reales | Cubierta en **§1** siguiente (muestra **2026-04-14**). |
| Resto de ítems `TASKS.md` | Sin cambio salvo referencia cruzada a este §. |

---

## T-246 — Ventana y entorno de validación real

| Campo | Valor |
|--------|--------|
| **Entorno** | Desarrollo local: API `uvicorn` + PostgreSQL definido en `.env` (`BT2_DATABASE_URL`). |
| **Muestra** | `operating_day_key = 2026-04-14`. |
| **Hechos comprobados** | `bt2_daily_picks`: **13** filas, **13** `event_id` distintos. Acceso a jobs (`scripts/bt2_cdm/`) y a BD verificados por ejecución el **2026-04-14** (cierre operativo). |

Ventana alternativa con más volumen histórico (referencia): `2026-04-13` (16 picks), `2026-04-12` (20 picks).

---

## T-247 / T-248 — Loop oficial con picks reales (evidencia)

### Job

- **Script:** `scripts/bt2_cdm/job_official_pick_evaluation.py`.
- **Métricas del día (sin mutar BD):**  
  `python3 scripts/bt2_cdm/job_official_pick_evaluation.py --metrics-only --metrics-day 2026-04-14`

**Salida real capturada:**

```text
[job_official_pick_evaluation] metrics {'suggested_picks_count': 13, 'official_evaluation_enrolled': 13, 'pending_result': 13, 'evaluated_hit': 0, 'evaluated_miss': 0, 'void_count': 0, 'no_evaluable': 0, 'hit_rate_on_scored_pct': None, 'no_evaluable_by_reason': {}, ...}
```

**Dry-run global** (muestra que el pipeline examina pendientes; no exige hit/miss):

```text
[job_official_pick_evaluation] {'backfill_inserted_or_would': 0, 'pending_rows_examined': 94, 'closed_to_final_this_run': 0, 'still_pending_after_run': 94, 'dry_run': True}
```

### SQL de validación (día **2026-04-14**)

```sql
-- Filas de evaluación oficial ligadas al día
SELECT e.evaluation_status, COUNT(*)::int AS c
FROM bt2_pick_official_evaluation e
JOIN bt2_daily_picks dp ON dp.id = e.daily_pick_id
WHERE dp.operating_day_key = '2026-04-14'
GROUP BY 1 ORDER BY 1;

-- Muestra de picks afectados (ids reales)
SELECT dp.id AS daily_pick_id, dp.event_id, e.evaluation_status
FROM bt2_daily_picks dp
JOIN bt2_pick_official_evaluation e ON e.daily_pick_id = dp.id
WHERE dp.operating_day_key = '2026-04-14'
ORDER BY dp.id;
```

### Resultado observado

| Métrica | Valor |
|---------|--------|
| Filas `bt2_pick_official_evaluation` para el día | **13** |
| Estado | **13 × `pending_result`** (partidos sin resultado final aún; válido como evidencia mínima de loop) |
| `daily_pick_id` (muestra) | 386–398 |
| `event_id` (muestra) | 102546–102579 |

---

## T-249 / T-251 — Auditoría de elegibilidad real (evidencia)

### Job (ventana alineada a bóveda)

Se añadió **`--operating-day-key YYYY-MM-DD`** al job para auditar solo `event_id` distintos de `bt2_daily_picks` ese día (ver runbook).

```bash
python3 scripts/bt2_cdm/job_pool_eligibility_audit.py --dry-run --operating-day-key 2026-04-14 --limit 200
```

**Salida real:**

```text
[job_pool_eligibility_audit] processed=13 missing_event=0 dry_run=True
```

(cada evento: `eligible=False`, `reason=INSUFFICIENT_MARKET_FAMILIES`.)

### SQL de validación

```sql
-- Última auditoría por evento candidato del día
SELECT DISTINCT ON (a.event_id)
  a.event_id, a.is_eligible, a.primary_discard_reason, a.evaluated_at
FROM bt2_pool_eligibility_audit a
JOIN (
  SELECT DISTINCT event_id FROM bt2_daily_picks WHERE operating_day_key = '2026-04-14'
) d ON d.event_id = a.event_id
ORDER BY a.event_id, a.evaluated_at DESC;
```

### Resultado observado

| Métrica | Valor |
|---------|--------|
| Eventos del día con fila de auditoría | **13 / 13** |
| Patrón «sin auditoría reciente» en admin para este día | **0** (todos con auditoría) |
| Motivo dominante | **`INSUFFICIENT_MARKET_FAMILIES`** (13/13) |
| `is_eligible` | **false** en la última fila por evento (coherente con regla ≥ 2 familias en datos CDM del corte) |

---

## T-250 — Validación summary / admin desde backend

**Endpoint:** `GET /bt2/admin/analytics/fase1-operational-summary?operatingDayKey=2026-04-14`  
**Header:** `X-BT2-Admin-Key: <BT2_ADMIN_API_KEY>`

### Consistencia BD ↔ JSON (corte real)

| Comprobación | BD (SQL / conteo) | Endpoint (JSON) |
|--------------|-------------------|-----------------|
| Candidatos | 13 eventos distintos | `poolCoverage.candidateEventsCount` = **13** |
| Con auditoría reciente | 13 | `eventsWithLatestAudit` = **13** |
| Elegibles pool | 0 | `eligibleEventsCount` = **0**, `poolEligibilityRatePct` = **0.0** |
| Descarte pool | `INSUFFICIENT_MARKET_FAMILIES` × 13 | mismo en `poolDiscardReasonBreakdown` |
| Picks sugeridos / enrolados / pendientes | 13 / 13 / 13 | `suggestedPicksCount` 13, `officialEvaluationEnrolled` 13, `pendingResult` 13 |
| Precisión por mercado | solo `FT_1X2`, 13 pending | `precisionByMarket[0].bucketKey` = `FT_1X2`, `pendingResult` = 13 |

**Conclusión:** el contrato admin refleja la BD para la ventana elegida. **FE (T-254–T-255) ya validado** sobre la misma clave/día y documentado en [`EJECUCION_UI_FASE1.md`](./EJECUCION_UI_FASE1.md).

---

## T-252 / T-253 — Mínimo paralelo F2 (sin abrir F2 completo)

### Cobertura por liga (misma ventana **2026-04-14**)

| Liga | Eventos distintos | Picks |
|------|-------------------|--------|
| Copa Libertadores | 5 | 5 |
| Copa Sudamericana | 5 | 5 |
| Championship | 2 | 2 |
| Serie B | 1 | 1 |

### Mercado piloto (slate del día)

| `model_market_canonical` | Picks |
|--------------------------|--------|
| `FT_1X2` | 13 |

### Descarte por causa principal (auditoría)

- **100%** `INSUFFICIENT_MARKET_FAMILIES` en los 13 eventos (última fila por evento).

### Conclusión (una sola, según handoff)

**La regla mínima actual se sostiene para este corte:** la auditoría v1 clasifica de forma estable y trazable; el 0% de elegibles en pool para este día es coherente con la regla de **≥ 2 familias** de mercado cuando el CDM/snapshot no cumple ese umbral para esos eventos. No se requiere ajuste puntual de código para cerrar este paralelo; cualquier mayor elegibilidad es decisión de producto (p. ej. ampliar familias en datos o relajar regla en otro sprint), explícitamente fuera de este cierre.

---

## Cuatro bloques de cierre (HANDOFF_CIERRE_S6_3 §4)

1. **Loop oficial real:** § T-247 / T-248.  
2. **Elegibilidad / auditoría real:** § T-249 / T-251.  
3. **Summary / backend (contrato admin):** § T-250 + validación FE en **T-254–T-255** (`EJECUCION_UI_FASE1.md`).  
4. **Paralelo F2 mínimo:** § T-252 / T-253.

---

*Última actualización: cierre operativo **BE + FE** documentado con muestra real **2026-04-14** (entorno local del repositorio).*
