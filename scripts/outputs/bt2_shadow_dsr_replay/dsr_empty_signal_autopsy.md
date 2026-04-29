# DSR Empty Signal Autopsy (v3 -> v4)

## Alcance

- Muestra fija: 32 eventos (`dsr_pilot_sample.csv`).
- Base de autopsia: los 22 eventos con `dsr_empty_signal` en `contract_v3`.
- Contraste: mismo sample en `contract_v4` (mismo modelo/carril, batch=1).

## Buckets de los 22 casos v3

| Bucket | Conteo | Causa concreta | Dictamen |
|---|---:|---|---|
| `explicit_model_abstention` | 16 | En v4 esos mismos eventos vuelven a `market_canonical=UNKNOWN` + `selection_canonical=unknown_side` con `no_pick_reason` explícito (falta de señales, coherencia débil, datos incompletos). | Abstención legítima del modelo |
| `resolved_to_ok` | 5 | En v4 esos mismos eventos pasan a `FT_1X2` canónico (`home/away`) con `selected_team` consistente. | Pérdida evitable por inestabilidad de salida/adhesión al contrato (no por parser mágico) |
| `resolved_to_dsr_failed` | 1 | En v4 el mismo evento cae en `ValueError` de llamada, sin output parseable. | Ruido operativo (no es `empty_signal`) |

## Hallazgos clave

- No aparece evidencia de estos patrones como causa dominante:
  - `market_canonical` válido con `selection_canonical` vacío.
  - `selected_team` útil no mapeado por normalización.
  - contradicciones internas del objeto con pick implícito recuperable.
- El patrón dominante real de `empty_signal` es abstención explícita (`UNKNOWN/unknown_side` + motivo).

## Corrección mínima aplicada en v4

- Se mantiene contrato minimalista (sin prose y sin fallback).
- Se añade trazabilidad estructurada por fila:
  - `raw_model_market`
  - `raw_model_selection`
  - `raw_selected_team`
  - `raw_no_pick_reason`
  - `empty_bucket`
- Se incorpora normalización mínima defensible:
  - si viene `selected_team` mapeable a home/away y el pick está incompleto, se fuerza solo a `FT_1X2 home/away`.
- Sin parser mágico, sin inventar picks, sin fallback de selección.
