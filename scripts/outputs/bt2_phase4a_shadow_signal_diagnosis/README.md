# Fase 4A.1 — Diagnóstico de señal (shadow) + preregistro 4B

Generado por `scripts/bt2_phase4a_shadow_signal_diagnosis.py`.
**Solo lectura descriptiva.** No implica edge ni apertura de Fase 4B productiva.

## Universo

- Picks: **297**, scored: **275**, ROI unidades (suma evals): **-23.43**.
- Pendientes / no evaluable: **14** / **8**.

## 4A.1 — N y lectura de estratos

- **Tier A (inadecuado):** scored < **20** — no interpretar dirección de ROI en el estrato.
- **Tier B (débil):** 20 ≤ scored < **50** — solo exploratorio; `signal_reading_banned_4a1` = true.
- **Tier C (descriptivo):** scored ≥ **50** — descriptivo agregado permitido; sigue sin probar edge.
- Columnas en CSV: `interpretation_tier`, `signal_reading_banned_4a1`.

## `selection_side` (post manifiesto)

- Distribución: home=137, away=125, unknown=19, unknown_resolved_teams=16
- Fuente: `bt2_events`+equipos → `raw_sportmonks_fixtures` → **manifest_row** en `bt2_shadow_pick_inputs`.

## Archivos

- `summary.json` — universo, N-thresholds, auditoría de sides, notas de diagnóstico.
- `preregister_phase4b.md` — borrador 4A.1 (histórico de intención).
- `preregister_phase4b_final.md` — **diseño 4B congelado** (holdout, segmentos, criterios cuantitativos).
- `phase4b_holdout_plan.json` — listas de `run_key` discovery/validation y umbrales fijos.
- `phase4b_allowed_segments.csv` — matriz permitida/prohibida por dimensión.
- `by_*.csv` — cortes con columnas de interpretación por estrato.

## Hallazgos (source_path, scored)

- **sportmonks_between_subset5_fallback**: scored=176, tier=C_adequate_descriptive, hit%=0.3523, roi%=-9.48
- **cdm_shadow**: scored=85, tier=C_adequate_descriptive, hit%=0.4471, roi%=-2.19
- **daily_shadow_sm_toa**: scored=14, tier=A_inadequate, hit%=0.2857, roi%=-34.86

### Ligas (ROI unidades, hit+miss)

- Serie A: **-20.18**
- Bundesliga: **-9.18**
- Premier League: **-6.69**
- La Liga: **-6.13**
- Ligue 1: **18.75**

## Veredicto 4A.1

- Composición de agregado: sigue alineada con 4A (volumen fallback + aportes a ROI; ver `summary.json`).
- **Fase 4B (cuando se ejecute):** seguir `preregister_phase4b_final.md` + JSON/CSV; no reabrir umbrales sin enmendar versión.

## Caveats baseline (vigentes)

- Carriles mezclados, VP no comparable entre paths, 14 `pending_result`.
