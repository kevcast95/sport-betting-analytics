# Previous vs Current DSR Radiography

## 1) Flujo previo real

- **Flujo A (shadow baseline 2025)**: no fue `dsr_api_only`; la selección persistida en `bt2_shadow_daily_picks.dsr_source` es `historical_sm_lbu_t60` (100% en ambos runs 2025).
- En código (`scripts/bt2_shadow_backfill_subset5.py`) la selección sale de `outcomes_decimal_summary` TOA y se persiste directo; no hay llamada DeepSeek en ese script.
- Métrica asociada (~20 picks y ~51%): en `shadow_backtest_final_summary.json` los dos runs base tienen 20 picks cada uno y hit-rate 0.5263 / 0.4737 (promedio simple ~0.50; ponderado 0.5).
- **Flujo A2 (BT2 daily picks histórico con DSR API real)**: en DB hay `dsr_source=dsr_api` con `pipeline_version=s6-deepseek-v1` y hit-rate oficial 0.5357 (56 scored, 30 hit). Es otro carril/universo.

## 2) Flujo actual (`shadow_dsr_replay`)

- `selection_source=dsr_api_only`, `run_family=shadow_dsr_replay`, muestra fija 32 del universo shadow subset5.
- Modelo forzado: `deepseek-v4-pro` (summary after_fix).
- Sin `rules_fallback`/`sql_stat_fallback` por contrato del experimento.
- Resultado actual: 17 `dsr_failed` + 15 `dsr_empty_signal`; 0 pick canónico, 0 postprocess_ok, 0 persistidos.

## 3) Waterfall comparativo

Ver `previous_vs_current_dsr_waterfall.csv`.

## 4) Dónde se rompe el volumen

- La caída principal no ocurre en universo ni en T-60 de la muestra fija; ocurre en el tramo `api_success/parseable_json -> canonical_pick` del flujo nuevo.
- En el flujo previo shadow, ese tramo **no existía** (no había API/parsing canónico): se persistía selección directa `historical_sm_lbu_t60`.
- Por eso comparar “20 picks shadow previos” vs “0 picks canónicos dsr_api_only” mezcla dos semánticas de pick válido distintas.

## 5) Cambios concretos que explican el gap

- Cambio de source_path: `historical_sm_lbu_t60` -> `dsr_api_only` (sin fallback).
- Cambio de criterio de validez: antes `selection` textual persistida; ahora requiere JSON parseable + canonicalización + `FT_1X2` postprocess.
- Cambio de modelo/nomenclatura: histórico productivo `s6-deepseek-v1` (`dsr_api`) vs piloto actual `deepseek-v4-pro`.
- Cambio de política: router productivo puede degradar a `sql_stat_fallback/rules`; `shadow_dsr_replay` lo prohíbe explícitamente.

## 6) Evidencia DB clave

- `bt2_daily_picks` por source: dsr_api:108, rules_fallback:67, sql_stat_fallback:20.
- `dsr_api` oficial: 56 scored / 30 hit / hit_rate 0.535714.
- `shadow` 2025 base: `dsr_source=historical_sm_lbu_t60` en 40/40 picks.
