# Sprint 06 — Handoff Backend → Frontend / DX

## Contrato vault / snapshot (US-FE-052, T-165)

`GET /bt2/vault/picks` — cada ítem incluye (camelCase):

| Campo | Notas |
|-------|--------|
| `pipelineVersion` | `s6-rules-v0` (reglas / degradación) \| `s6-deepseek-v1` cuando **`dsrSource=dsr_api`** (**T-169** + **T-170** — lotes v1-equivalentes) |
| `dsrNarrativeEs` | Texto modelo **sin** JSON crudo de proveedor |
| `dsrConfidenceLabel` | p. ej. `low`, `medium` |
| `dsrSource` | `rules_fallback` (reglas locales) \| `dsr_api` (DeepSeek en vivo cuando **T-169** + **`BT2_DSR_PROVIDER=deepseek`**) — ver **D-06-018** |
| `marketCanonical` / `marketCanonicalLabelEs` | Código + etiqueta ES (mercado sugerido) |
| `modelMarketCanonical` / `modelSelectionCanonical` | Sugerencia DSR canónica |

`contractVersion` en `GET /bt2/meta`: **`bt2-dx-001-s6.0`** (sin bump por T-169: mismos campos; cambian solo valores de `pipelineVersion` / `dsrSource`).

### DeepSeek en vivo + lotes v1-equivalentes (T-169 / T-170, D-06-018 / D-06-019)

- **Camino:** `POST /bt2/session/open` → `_generate_daily_picks_snapshot` agrupa candidatos con contexto CDM en **lotes** de hasta **`BT2_DSR_BATCH_SIZE`** (default **15**) → **`deepseek_suggest_batch`** (`bt2_dsr_deepseek.py`): un JSON tipo v1 con **`ds_input`** + salida **`picks_by_event`** (misma idea que [`jobs/deepseek_batches_to_telegram_payload_parts.py`](../../../../jobs/deepseek_batches_to_telegram_payload_parts.py)). **Una petición HTTP OpenAI-compatible por lote**, no por evento.
- **Persistencia:** por cada evento del pool compuesto se inserta una fila; si el lote devolvió pick para ese `event_id` → `dsr_source=dsr_api`, `pipeline_version=s6-deepseek-v1`. Si el lote falla o falta entrada para ese `event_id` → degradación **por evento** vía `suggest_for_snapshot_row` (reglas) → `rules_fallback`, `s6-rules-v0`.
- **Config:** `BT2_DSR_PROVIDER=deepseek`, `DEEPSEEK_API_KEY`. Opcionales: `BT2_DSR_DEEPSEEK_BASE_URL`, `BT2_DSR_DEEPSEEK_MODEL`, `BT2_DSR_TIMEOUT_SEC` (**por lote**), `BT2_DSR_MAX_RETRIES`, **`BT2_DSR_BATCH_SIZE`**.
- **Hash** `dsr_input_hash`: por evento, solo `{ event_id, odds }` (**D-06-002**).
- **Logs:** prefijos `bt2_dsr_batch_*` (sin PII; tamaño de lote y códigos).
- **Idempotencia:** igual que antes — ver [`EJECUCION_COMPLETA_PUNTA_A_PUNTA.md`](./EJECUCION_COMPLETA_PUNTA_A_PUNTA.md) §3.12.

## Picks (US-FE-054, T-167)

`PickOut` (lista, detalle, POST create) incluye opcionalmente:

- `marketCanonical`, `marketCanonicalLabelEs`
- `modelMarketCanonical`, `modelSelectionCanonical`
- `modelPredictionResult` (`hit` \| `miss` \| `void` \| `n_a`) tras liquidar

## Analytics admin (US-FE-053, T-166)

- **GET** `/bt2/admin/analytics/dsr-day?operatingDayKey=YYYY-MM-DD`
- **Header:** `X-BT2-Admin-Key: <BT2_ADMIN_API_KEY>`
- Sin `BT2_ADMIN_API_KEY` en entorno → **503**
- Respuesta: `summary` (KPIs + `summaryHumanEs`) + `auditRows[]`

## Cron (OPS)

- Job: `python3 scripts/bt2_cdm/job_fetch_upcoming.py`
- Runbook: [`../../runbooks/bt2_fetch_upcoming_cron.md`](../../runbooks/bt2_fetch_upcoming_cron.md)

## Migración Alembic

`b3c4d5e6f7a8_sprint06_dsr_markets_analytics` — columnas en `bt2_daily_picks` y `bt2_picks`.
