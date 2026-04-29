# Semántica `value_pool_pass_rate` vs shadow picks — 2026-01..03

## Qué calcula la métrica en el backfill shadow

En `scripts/bt2_shadow_backfill_subset5.py`, `_compute_value_pool_pass`:

1. Solo puede evaluar **value pool SM LBU T-60** cuando existe **`bt2_event_id`** enlazado a `bt2_events` **y** hay fila `raw_sportmonks_fixtures.payload` para ese fixture.
2. Para cada fixture se reconstruye el value pool desde el payload raw y la política **T-60** (`cutoff_t60`), igual que en histórico LBU.

## Qué pasó en 2026-01 / 02 / 03

Esas tres corridas mensuales se construyeron con **`sportmonks_between_subset5_fallback`** (no había cohorte CDM en esas ventanas). Muchas filas llegan con **`bt2_event_id = 0` / sin enlace CDM**.

En ese caso `_compute_value_pool_pass` **no tiene join** `bt2_events + raw_sportmonks_fixtures` → el mapa `vp_map` queda con string vacío `""` por fixture (`setdefault`).

En `_summary_from_results`:

- `vp_vals` solo cuenta valores **no vacíos**.
- Si **todas** las filas tienen VP vacío → **`vp_total = 0`** → **`value_pool_pass_rate = 0.0`** (implementación actual: \(0\) cuando no hay muestra, no significa «0 % pasó»).

## ¿Contradicción con shadow picks generados?

**No es un bug lógico del picker:** la clasificación **`matched_with_odds_t60`** viene del **pipeline The Odds API histórico** (match + odds en ventana), **no** del gate de value pool.

En estos runs mensuales el carril shadow **no filtra** por VP para persistir picks: VP es **métrica de auditoría paralela**. Si VP no es computable (sin CDM/raw), **no puede mostrarse una tasa interpretable**; sigue siendo válido persistir picks **h2h T-60 US** para backtest.

## Comparabilidad con abril 2026 (CDM)

En **2026-04** la cohorte salió en gran parte desde **CDM** (`bt2_events`), así que **sí** hubo fixtures con `bt2_event_id` y raw → **VP recomputable** → `value_pool_pass_rate` puede ser **> 0** y es **comparable entre filas que tienen VP**.

Mezclar en un solo KPI agregado «VP rate global» **2026-01..03 + 04** sin estratificar por `source_path` **sí** mezcla semánticas distintas (VP ausente vs VP presente).

## Recomendación operativa pre-Fase 4

- Reportar **VP solo donde `vp_total > 0`** o estratificar por **`source_path`** (`shadow_source_path_audit.*`).
- No interpretar **`value_pool_pass_rate = 0`** en meses fallback como «ningún fixture pasó VP».
