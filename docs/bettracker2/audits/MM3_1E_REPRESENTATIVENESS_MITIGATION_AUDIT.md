# MM-3.1E — Representativeness Mitigation + Final ROI-safe Dataset Decision

## 1. Executive summary

- Universo Big 5: **3806** partidos; ROI-safe v1: **3088** (con resultados listos en artifact).
- Riesgo representatividad (v1 vs universo, max |Δ| liga): **medium** (~**3.0** pp).
- Dataset **v2_full** (high-confidence MM-3.1D): **3126** filas; con resultados: **3088**.
- Decisión: `ready_for_mm3_2a_feature_engineering` = **True**; `ready_for_mm3_2a_model_training` = **True**; dataset recomendado: **roi_safe_subset_v2_stratified**.

## 2. Scope and restrictions

Solo SELECT Postgres + artefactos; sin TOA/SM/DSR; sin escrituras.

## 3. MM-3.1D recap

~82% match rate board, +1095 matches, digest P0 completo en alta confianza; el riesgo **critical** reportado en 1D usaba otra definición de denominador vs MM-3.1E (ver §4).

## 4. Why representativeness still matters

Los modelos absorben tasas de 1X2/OU/BTTS por liga/tiempo; un subset matched puede desviarse aunque el matching sea bueno.

**Nota metodológica:** en MM-3.1E las tasas de outcome comparan solo partidos **con marcador final** en DB. El `max_abs_league_delta_pp` de MM-3.1D (~14.6 pp) mezclaba fixtures matched sin resultado en el denominador; no son directamente comparables sin recalcular 1D en el mismo criterio.

## 5. Bias diagnosis

`scripts/outputs/mm3_1e_bias_diagnosis_rows.csv`, `mm3_1e_bias_summary.json`.

## 6. Root cause of remaining delta

`scripts/outputs/mm3_1e_representativeness_root_cause.json` — eje de outcome y liga dominante en max |Δ|.

## 7. Alias review

`scripts/outputs/mm3_1e_manual_alias_review_queue.csv` (propuestas + ambiguos).

## 8. Alias simulation

`mm3_1e_alias_simulated_match_rows.csv`, `mm3_1e_alias_simulated_coverage.csv` (impacto táctil; sin re-ejecución completa del matcher).

## 9. Dataset candidates

- `mm3_1e_roi_safe_subset_v2_full.csv`
- `mm3_1e_roi_safe_subset_v2_stratified.csv`
- `mm3_1e_roi_safe_subset_v2_weighted.csv`
- `mm3_1e_dataset_candidate_summary.csv`

## 10. Representativeness comparison

`mm3_1e_dataset_representativeness_comparison.csv`

## 11. Recommended dataset for MM-3.2

Ver `mm3_1e_mm3_2_decision.json` → **roi_safe_subset_v2_stratified**.

## 12. MM-3.2 readiness decision

Mismo JSON: entrenamiento oficial condicionado a protocolo ponderado/estratificado si el riesgo bruto sigue alto.

## 13. What this proves

Se pueden construir **v2_full / stratified / weighted** sin nuevos créditos TOA y cuantificar trade-offs de sesgo.

## 14. What this does not prove

Generalización out-of-sample multi-book, ni equivalencia con precios reales T-60 completos.

## 15. Recommended next step

Iniciar MM-3.2A feature engineering con dataset recomendado + validación estratificada obligatoria.

