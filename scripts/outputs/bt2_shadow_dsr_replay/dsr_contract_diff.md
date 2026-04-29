# DSR Contract Diff (after_fix vs contract_v2)

## Cambio aplicado

- Endurecimiento de prompt/contrato de salida a esquema canónico mínimo (`market_canonical`, `selection_canonical`, etc.).
- Parser más estricto: sin `reasoning_content`, sin rescate de JSON incrustado, sin `picks[]` anidado.
- Normalización mínima de aliases estrictamente mapeables (sin fallback de selección).
- Mismo experimento: misma muestra fija 32, `deepseek-v4-pro`, `dsr_api_only`.

## Métricas comparativas

| Métrica | after_fix | contract_v2 |
|---|---:|---:|
| prompts_built_ok | 32 | 32 |
| dsr_failed | 17 | 30 |
| dsr_empty_signal | 15 | 0 |
| parseable_canonical | 0 | 2 |
| evaluable_ft_1x2_after_postprocess | 0 | 2 |
| dsr_postprocess_reject | 0 | 0 |
| dsr_non_h2h_canonical | 0 | 0 |
| ok | 0 | 2 |
| usage_prompt_tokens_sum | 58568 | 56000 |
| usage_completion_tokens_sum | 8158 | 9260 |

## Lectura corta

- El contrato v2 estricto reduce `dsr_empty_signal` a 0, pero aumenta `dsr_failed` por salidas fuera de JSON puro.
- Aparecen 2 picks `ok` canónicos y evaluables (`FT_1X2`), ambos sin verdad final disponible aún.
- El principal cuello actual queda concentrado en parseabilidad estricta del lote (30/32 fallidos).
