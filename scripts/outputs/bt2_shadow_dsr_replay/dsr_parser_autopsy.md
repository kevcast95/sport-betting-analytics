# DSR Parser Autopsy (muestra fija 32)

## Contexto

- Muestra congelada: `scripts/outputs/bt2_shadow_dsr_replay/dsr_pilot_sample.csv` (32 filas).
- Modelo forzado en rerun: `deepseek-v4-pro`.
- Sin fallback de selección (`rules/sql_stat`) por contrato `dsr_api_only`.

## Evidencia principal

- El propio `raw_content_excerpt` del batch muestra salida no-JSON (cadena explicativa en inglés): `We are asked to analyze two events from the given batch and produce picks. The output must be JSON with picks_by_event array containing one object per event. Maximum 2 picks per event. If no pick, picks empty and motivo_sin_pick is required.  We need to use only the provided data: consensus odds, diagnostics (including prob_coherence if present), and processed blocks with available: true. For each event, we must select the market with best support from the data in the lot. Market options are onl...`.
- Cuando la salida no es JSON, `_parse_json_object` falla y el batch degrada (`dsr_failed`).
- En batches que sí parsean JSON, el parser recibe filas sin pick canónico (`UNKNOWN/unknown_side`) y marca `dsr_empty_signal`.

## Clasificación por patrón (after_fix)

| Patrón | Conteo | Evidencia |
|---|---:|---|
| `dsr_failed` | 17 | Fallo parse JSON/batch degradado. |
| `dsr_empty_signal` | 15 | JSON parseado pero sin pick canónico (`no_canonical_pick`). |
| `dsr_postprocess_reject` | 0 | No es la causa principal actual. |

## Distribución por response_id (after_fix)

| response_id | dsr_failed | dsr_empty_signal |
|---|---:|---:|
| `06aa52bb-b337-427c-be54-916c160acea5` | 0 | 15 |
| `0e18a353-7c2c-404f-9597-5681f3aa4d09` | 2 | 0 |
| `dfccfe70-05b5-46c3-9a97-03d6deab775c` | 15 | 0 |

## Causa raíz

- **Mixta (2 causas):**
  1. **Formato de salida del modelo fuera de contrato JSON estricto** en parte de los lotes (`parse_json`).
  2. **Salida parseada pero sin market/selection canónicos útiles** para BT2 (`no_canonical_pick`).
- **No** hay evidencia de rechazo por postprocess en esta corrida (0 `dsr_postprocess_reject`).

## Corrección mínima aplicada

- Parser JSON reforzado en `apps/api/bt2_dsr_deepseek.py` con extracción por llaves balanceadas (tolerante a texto extra).
- Traza extendida: `raw_content_excerpt` para evidenciar formato real devuelto por el modelo.
- Runner fijado a muestra congelada + modelo explícito: `--fixed-sample-csv`, `--model`, `--output-tag`.

## Resultado

- La corrección mejoró observabilidad y control del experimento, pero **no resolvió** parseabilidad canónica (sigue 0 evaluables).
