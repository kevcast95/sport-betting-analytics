# MM branch cleanup — antes de MM-3.2A

## 1. Branch actual

`phase4/mm3-data-science-feasibility` (ver `scripts/outputs/branch_cleanup_status_before.txt` tras cada corrida).

## 2. Qué se conserva (versionado)

- **Scripts MM-3:** `scripts/mm3_0a_*.py` … `scripts/mm3_1e_*.py`
- **Herramienta de inventario:** `scripts/tools_mm3_branch_cleanup_inventory.py`
- **Auditorías Markdown:** `docs/bettracker2/audits/MM3_*.md`
- **Artefactos pequeños** bajo `scripts/outputs/mm3_*` (JSON de resumen, readiness, decisiones, CSVs de cobertura/resumen que no superen el umbral de exclusión en `.gitignore`)
- **Fixture inventory** necesario para pipelines: `scripts/outputs/mm3_1a_big5_fixture_inventory.csv`
- **Metadatos de limpieza:** `scripts/outputs/branch_cleanup_*.{csv,txt,json}`

## 3. Qué se excluye del versionado (pero puede quedar en local)

- **Raw TOA / pilot raw:** `*raw*.json` (ya parcialmente cubierto; añadido `mm3_1a_toa_pilot_raw.json` explícito)
- **Checkpoints:** `*checkpoint*.json`
- **Filas masivas:** `mm3_1b_toa_p0_match_rows.csv`, `mm3_1b_toa_p0_rejections.csv`, `mm3_1b_toa_p0_market_board_rows.csv`
- **Detalle de rechazos / tolerancias / intentos de match:** `mm3_1c_rejection_detail_rows.csv`, `mm3_1c_kickoff_tolerance_candidates.csv`, `mm3_1d_matching_attempt_rows.csv`, `mm3_1d_best_match_rows.csv`, `mm3_1d_improved_market_board_rows.csv`
- **ROI subsets grandes:** `mm3_1c_roi_safe_subset_v0.*`, `mm3_1d_roi_safe_subset_v1.*`, `mm3_1e_roi_safe_subset_v2_*.csv`
- **Planes de batch grandes:** `mm3_1a_backfill_batches.json`

Motivo: reproducibles con scripts + DB (salvo raw TOA) o demasiado pesados para Git.

## 4. Archivos eliminados

Ninguno obligatorio: no se borró material MM-3 del disco (cadena de dependencias y raw TOA). Ver `scripts/outputs/branch_cleanup_removed_or_untracked.csv`.

## 5. Cambios a `.gitignore`

Se añadió un bloque **MM-3 lab** con rutas explícitas de artefactos grandes y `.pytest_cache/`. Las reglas previas (`*raw*.json`, `*checkpoint*.json`, etc.) se mantienen.

## 6. Scripts MM-3 conservados

`mm3_0a_local_db_market_data_universe_audit.py`, `mm3_1a_toa_historical_sweep_cost_estimator.py`, `mm3_1b_toa_p0_controlled_backfill.py`, `mm3_1c_toa_match_coverage_audit.py`, `mm3_1d_toa_matching_improvement.py`, `mm3_1e_representativeness_mitigation.py`.

## 7. Audits MM-3 conservados

`MM3_0A_*` … `MM3_1E_*` en `docs/bettracker2/audits/`.

## 8. Fix candidates (documentados en código / audits MM-3)

- **TOA historical:** `GET /v4/historical/sports/{sport}/odds` (no la ruta antigua HTML 404) — ver `REPO_FIX_CANDIDATES` en `scripts/mm3_1b_toa_p0_controlled_backfill.py` y audits 1A/1B.
- **Ligue 1 sport_key:** `soccer_france_ligue_one` — mapeo en `apps.api.bt2_theoddsapi_mapping` (usado por scripts MM-3).

## 9. Estado final del working tree

Tras commit: solo deben quedar sin trackear (si existen en disco) los archivos ignorados por `.gitignore` y `.env`. Ejecutar `git status` para confirmar.

## 10. Próximo paso recomendado: MM-3.2A

Definir el paquete de feature engineering (entrada: subset recomendado en `mm3_1e_mm3_2_decision.json` + `mm3_1a_big5_fixture_inventory.csv` + digest/odds según diseño) sin ejecutar TOA/DSR en esta fase.
