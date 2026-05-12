# MM-3.1D — TOA Matching Improvement / Alias Layer Audit

## 1. Executive summary

- Partidos Big 5 en DB: **3806**. Matched MM-3.1B: **2031** (53.4%).
- Tras reprocesar **solo** `mm3_1b_toa_p0_raw.json` con normalización extendida + similitud + tolerancias: matched de board **3126** (82.1%), nuevos **1095**.
- Riesgo representatividad (max |Δ| liga): **critical** → **critical** (max Δ ≈ **14.6** pp).
- `ready_for_mm3_2a_subset`: **False**; `ready_for_mm3_2_full_big5`: **False**; ruta: **improve_matching_first**.

## 2. Scope and restrictions

Artifact-only + SELECT Postgres. Sin TOA/SM/DSR, sin escrituras, sin alias en DB.

## 3. Why MM-3.1D was needed

MM-3.1C mostró `team_name_mismatch` y sesgo por liga; el backfill MM-3.1B usó `_norm_team` estricto TOA↔BT2.

## 4. MM-3.1B / 1C recap

2031 matches, ~53% match rate, riesgo **critical**, `league_coverage_hole_flag` true (Ligue 1 baja vs EPL).

## 5. Name normalization strategy

Ver `scripts/outputs/mm3_1d_team_name_normalization_rules.json`. Opcional: `scripts/outputs/mm3_1d_manual_team_aliases.json` (lista `regex_bt2_substitutions`: `regex_bt2`, `replace_with`).

## 6. Alias proposals

`scripts/outputs/mm3_1d_team_alias_proposals.csv` (evidencia agregada; **no** aplicar a DB).

## 7. Kickoff tolerance strategy

Buckets en `mm3_1d_matching_attempt_rows.csv`: exact, ±5/15/30 min, mismo día con alta similitud de equipos.

## 8. Matching score design

`composite_score = 2 * team_block - time_pen + bonus_mercados_digest` con penalización swap leve; desempate por gap top1-top2 (**0.035**).

## 9. Improved match results

`mm3_1d_best_match_rows.csv`, `mm3_1d_ambiguous_match_rows.csv`.

## 10. Coverage before/after

`mm3_1d_coverage_after_matching.csv` + tasas por liga en `mm3_1d_representativeness_after_matching.json`.

## 11. Representativeness before/after

Riesgo previo: **critical**. Tras matching: **critical** (max |Δ| liga **14.56** pp).

## 12. ROI-safe subset v1

`mm3_1d_roi_safe_subset_v1.csv` / `.json` — solo **high** + **legacy_high** con flags digest h2h/totals/OU2.5; odds decimales siguen vacías (no están en digest).

## 13. MM-3.2 readiness decision

`scripts/outputs/mm3_1d_mm3_2_readiness.json`.

## 14. What this proves

Se puede **re-scorar** el universo TOA ya descargado y proponer matches/alias sin créditos adicionales.

## 15. What this does not prove

Equivalencia con el matcher de producción MM-3.1B, calidad de precios, ni ausencia de colisiones TOA no vistas en digest.

## 16. Recommended next step

Curación manual de `mm3_1d_manual_team_aliases.json` + revisión de filas `safe_to_auto_apply_artifact_only` antes de MM-3.2.

