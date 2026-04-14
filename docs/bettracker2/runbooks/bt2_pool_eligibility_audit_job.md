# Runbook — Auditoría elegibilidad pool v1 (S6.3 / T-236)

## Regla

`pool-eligibility-v1` (Fase 0 §6, US-BE-051): fixture CDM + cuotas válidas (`event_passes_value_pool`) + **≥ 2 familias** de mercado con cobertura completa + sin faltantes críticos en trazas `ds_input` (raw SportMonks mínimo).

Códigos: `MISSING_FIXTURE_CORE`, `MISSING_VALID_ODDS`, `INSUFFICIENT_MARKET_FAMILIES`, `MISSING_DS_INPUT_CRITICAL` (ACTA T-244 §4).

## Ejecución

```bash
export BT2_DATABASE_URL='postgresql://…'
python3 scripts/bt2_cdm/job_pool_eligibility_audit.py
python3 scripts/bt2_cdm/job_pool_eligibility_audit.py --dry-run --limit 50
python3 scripts/bt2_cdm/job_pool_eligibility_audit.py --event-id 42
```

La tabla **`bt2_pool_eligibility_audit`** es **append-only** (cada corrida inserta filas). Para el último estado por evento:

```sql
SELECT DISTINCT ON (event_id)
  event_id, evaluated_at, is_eligible, primary_discard_reason
FROM bt2_pool_eligibility_audit
ORDER BY event_id, evaluated_at DESC;
```

## Código

Implementación: `apps/api/bt2_pool_eligibility_v1.py` · job: `scripts/bt2_cdm/job_pool_eligibility_audit.py`.
