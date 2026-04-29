# DSR Batching Experiment (v2 vs v3)

## Setup fijo

- Muestra: `dsr_pilot_sample.csv` (32 filas, misma muestra fija).
- Modelo: `deepseek-v4-pro`.
- Carril: `dsr_api_only`.
- Sin fallback de selección.
- Sin cambios de universo/T-60/mercado/región/subset5.

## Variante v2 (control)

- Contrato: v2 (7 campos por evento).
- Batching: configuración por defecto (batch de 15).
- Resultado: `dsr_pilot_summary_contract_v2.json`.

## Variante v3 (prueba operativa)

- Contrato: v3 minimalista (5 campos por evento).
- Batching: `--dsr-batch-size 1` (1 evento por llamada).
- Resultado: `dsr_pilot_summary_contract_v3.json`.

## Resultados

| Métrica | v2 | v3 |
|---|---:|---:|
| dsr_failed | 30 | 6 |
| dsr_empty_signal | 0 | 22 |
| parseable_canonical | 2 | 4 |
| evaluable_ft_1x2_after_postprocess | 2 | 4 |
| ok total | 2 | 4 |
| usage_prompt_tokens_sum | 56000 | 68051 |
| usage_completion_tokens_sum | 9260 | 27912 |

## Lectura operativa

- El principal cuello `dsr_failed` baja de forma fuerte (30 → 6) al combinar contrato minimalista + batching 1x1.
- El costo sube de forma material (más llamadas y más completion tokens).
- Aumenta `dsr_empty_signal` (0 → 22): robustez sintáctica mejora, pero la producción de picks útiles sigue limitada.
