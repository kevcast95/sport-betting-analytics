# Contrato — fuente de selección `dsr_api_only` (carril shadow)

## Alcance

- **No productivo**: solo tablas `bt2_shadow_*` y scripts locales.
- **No se reinterpreta** el ROI/hit-rate del baseline shadow anterior como si fuera motor DSR; ese baseline es **selección shadow no-DSR** (`historical_sm_lbu_t60` / heurística de outcomes TOA).
- **Universo**: misma cohorte que el baseline (subset5, `h2h`, `us`, T-60, SM fixture master, TOA historical h2h), repetida con picker **DSR API puro**.

## Modo oficial

| Campo | Valor |
|--------|--------|
| `selection_source` | `dsr_api_only` |
| `run_family` | `shadow_dsr_replay` |
| Invocación | `deepseek_suggest_batch_with_trace` en `apps/api/bt2_dsr_deepseek.py` (DeepSeek Chat Completions, mismo stack que BT2 DSR). |
| Lote ciego | `operating_day_key` del batch = `2099-06-15` (`BLIND_LOT_OPERATING_DAY_KEY`), alineado con replay admin. |
| `dsr_prompt_version` | `CONTRACT_VERSION_PUBLIC` (`bt2_dsr_contract`) + sistema/prompt batch T-170. |

## Excluido explícitamente

- `rules_fallback`
- `sql_stat_fallback` (`suggest_sql_stat_fallback_from_consensus`)
- Sustitución silenciosa cuando DSR falla o devuelve señal vacía.

## Estados de fallo (sin sustitución)

| `dsr_parse_status` | Significado |
|--------------------|-------------|
| `dsr_failed` | API/transporte o batch degradado (`event_id → None`). |
| `dsr_empty_signal` | Respuesta sin pick canónico (`UNKNOWN` / `unknown_side`). |
| `dsr_postprocess_reject` | `postprocess_dsr_pick` devolvió `None` (coherencia cuota/narrativa, etc.). |
| `dsr_non_h2h_canonical` | Pick canónico distinto de `FT_1X2` en un contrato centrado en mercado ganador h2h. |
| `ok` | Pick `FT_1X2` aceptado post-proceso. |

- **Pre-DSR**: si no hay agregación CDM válida al corte T-60 + value pool (`bt2_odds_snapshot`), el evento **no entra** en la muestra piloto (columna `cdm_odds_t60_ok` en CSV). Suele haber menos filas elegibles que filas shadow con `matched_with_odds_t60`: el baseline histórico puede haber cargado odds en artefactos TOA sin equivalencia completa en `bt2_odds_snapshot`. Una extensión puede hidratar cuotas desde `bt2_shadow_provider_snapshots` o persistir intentos como `prompt_build_failed`.

## Persistencia (separación del baseline no-DSR)

Migración `s1t2u3v4w5x6_bt2_shadow_dsr_replay_lane.py`:

- `bt2_shadow_runs`: `run_family`, `selection_source`.
- `bt2_shadow_daily_picks`: `dsr_parse_status`, `dsr_failure_reason`, `dsr_model`, `dsr_prompt_version`, `dsr_response_id`, `dsr_usage_json`, `dsr_raw_summary_json`, `selected_side_canonical`.

Los **run_key** nuevos deben ser distintos del baseline (p. ej. prefijo `shadow-dsr-replay-...`); no se sobrescriben corridas previas.

## Pilot vs universo completo

1. **Piloto** (20–40 fixtures, estratificado liga × mes): script `scripts/bt2_shadow_dsr_replay_prepare.py` sin pisar datos hasta que se añada paso de INSERT dedicado.
2. **Universo completo**: tras métricas aceptables del piloto, segundo script/job que inserta run `shadow_dsr_replay` + picks con los campos anteriores.

## Congelaciones respetadas

- Subset5, mercado/región/snapshot policy T-60 sin cambios.
- Sin selective release ni Fase 4 sobre el picker viejo del baseline no-DSR.
