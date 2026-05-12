# MM-3.1C — TOA P0 Match Coverage, Rejection and Representativeness Audit

## 1. Executive summary

- Fixtures Big 5 (DB): **3806**; matcheados TOA T-60: **2031** (**53.4%**).
- Cuello principal: **matching BT2 ↔ TOA** (nombres + umbral de score + `commence` vs `kickoff_utc`), no proveedor ni créditos.
- Riesgo representatividad global: **critical** (máx. |Δ| entre ligas ~ **19.1** pp en tasas clave).
- Decisión MM-3.2: `ready_for_mm3_2a_subset` = **False**; `ready_for_mm3_2_full_big5` = **False**; ruta recomendada: **improve_matching_first**.

## 2. Scope and restrictions

Solo artefactos MM-3.1A/B + SELECT Postgres. Sin TOA/SM/DSR, sin escrituras, sin nuevo backfill.

## 3. MM-3.1B recap

Ver `scripts/outputs/mm3_1b_summary.json`: 2740 requests, 54800 créditos, fórmula confirmada, 0 errores proveedor.

## 4. Coverage by league/year/month

`scripts/outputs/mm3_1c_coverage_by_league_year_month.csv`

## 5. Rejection analysis

- Resumen: `scripts/outputs/mm3_1c_rejection_reason_summary.csv`
- Detalle: `scripts/outputs/mm3_1c_rejection_detail_rows.csv`  
Clasificación heurística a partir del mejor candidato BT2 por `sport_key` + día calendario UTC ±1.

## 6. Team alias findings

`scripts/outputs/mm3_1c_team_alias_candidates.csv` — pares BT2 vs TOA con similitud alta pero `norm` distinto (acentos, & vs and, Town, AFC, etc.).

## 7. Kickoff tolerance findings

`scripts/outputs/mm3_1c_kickoff_tolerance_candidates.csv` — para no matcheados, si existe par TOA en rechazos con **mismos nombres normalizados**, se reporta el **mínimo** |Δseg| entre `kickoff_utc` BT2 y `commence_toa` TOA.

## 8. Matched vs full representativeness

`scripts/outputs/mm3_1c_matched_vs_full_representativeness.csv`, `scripts/outputs/mm3_1c_representativeness_summary.json`.

## 9. ROI-safe subset v0

`scripts/outputs/mm3_1c_roi_safe_subset_v0.csv` + `.json` — lista de eventos matcheados con resultados y outcomes; **odds vacíos** (no estaban en digest MM-3.1B).

## 10. MM-3.2 readiness decision

`scripts/outputs/mm3_1c_mm3_2_readiness.json`

## 11. What this proves

El subconjunto matcheado tiene mercados P0 completos en board; el gap de cobertura es explicable por naming/timing.

## 12. What this does not prove

Calidad de precios por casa, ausencia de leakage, ni que el subset sea i.i.d. respecto al universo completo sin ajustes.

## 13. Recommended next step

Mejorar normalización/alias y umbral de matching antes de exigir Big 5 completo.

## 14. Repo fix candidates (referencia MM-3.1B)

`theoddsapi_worker.py` debe migrar a `GET /v4/historical/sports/{sport}/odds` (fix separado en main).
