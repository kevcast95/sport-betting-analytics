# MM-3.1B — TOA P0 Controlled Backfill (Audit)

## 1. Executive summary

- Modo: **HTTP ejecutado**.
- Requests ejecutados: **2740** (omitidos por resume: **0**).
- Créditos consumidos (suma `x-requests-last`): **54800.0**.
- Remaining final (header): **40777**.
- Partidos BT2 en alcance: **3806**; matcheados distintos: **2031** (53.4%).
- FT_1x2 listos: **2031**; totals listos: **2031**; OU 2.5 listo: **2031**.
- `ready_for_mm3_2_feature_dataset`: **False** — match_coverage_low:0.534.
- Stop: `None`.

## 2. Scope and restrictions

P0 only: **h2h, totals**, **eu**, **T-60**, Big 5 `sport_key` fijos. Sin DB writes, sin DSR/SM, sin P1/P2.

## 3. Why MM-3.1B was approved

MM-3.1A validó endpoint, **20 créditos/request** y matching piloto.

## 4. Pilot recap

Ver `docs/bettracker2/audits/MM3_1A_TOA_HISTORICAL_SWEEP_COST_ESTIMATOR_AUDIT.md` y piloto EPL.

## 5. Cost limits and stop conditions

Máx **60000** créditos, **3000** requests; abort si remaining **<35000**; checkpoint cada **50**; resume por `mm3_1b_toa_p0_checkpoint.json`; `x-requests-last` ≠ **20** aborta; errores consecutivos / mensaje repetido abortan.

## 6. Execution summary

Pares planeados: **2740**. Pares en checkpoint al final: **2740**.

## 7. Coverage by league

```json
{
  "soccer_epl": {
    "fixtures": 783,
    "matched_bt2": 595
  },
  "soccer_france_ligue_one": {
    "fixtures": 629,
    "matched_bt2": 248
  },
  "soccer_germany_bundesliga": {
    "fixtures": 837,
    "matched_bt2": 228
  },
  "soccer_italy_serie_a": {
    "fixtures": 780,
    "matched_bt2": 559
  },
  "soccer_spain_la_liga": {
    "fixtures": 777,
    "matched_bt2": 401
  }
}
```

## 8. Coverage by market

Resumen board: FT_1x2 ready **2031**, totals ready **2031**, líneas OU (suma por evento): **7510**, OU2.5 ready **2031**.

## 9. Match/rejection analysis

- Matches: `mm3_1b_toa_p0_match_rows.csv` (**2031** filas).
- Rechazos TOA-event: `mm3_1b_toa_p0_rejections.csv` (**21913** filas).

## 10. Cost reconciliation

Suma `x-requests-last` = **54800.0** vs **20 × requests** = **54800** → formula_ok **True**.

## 11. Output market board

- `mm3_1b_toa_p0_market_board.json`, `mm3_1b_toa_p0_market_board_rows.csv`.

## 12. What this proves

Existencia de snapshots TOA T-60 alineables a BT2 con mercados P0 presentes en payload (subconjunto verificado por filas board).

## 13. What this does not prove

ROI de estrategia, calidad de todas las casas, cobertura fuera del rango DB, ni ausencia de sesgo de matching.

## 14. Recommended next step

Persistencia controlada (fuera de MM-3.1B) o MM-3.2 feature matrix si `ready_for_mm3_2_feature_dataset` es true; si false, revisar stop_reason y umbrales de match.

## 15. Repo fix candidates (main / cleanup, fuera de MM-3.1B)

No modificar `theoddsapi_worker.py` dentro de este backfill. Candidato registrado (también en `mm3_1b_summary.json` → `repo_fix_candidates`):

```json
[
  {
    "id": "TOA_HISTORICAL_ODDS_URL_MM31A",
    "affected_path": "scripts/bt2_atraco/theoddsapi_worker.py",
    "bug": "endpoint histórico TOA incorrecto",
    "wrong_endpoint": "GET /v4/historical/odds?sport=...",
    "correct_endpoint": "GET /v4/historical/sports/{sport}/odds",
    "evidence": "MM-3.1A: ruta antigua → HTML 404 sin headers de uso; ruta correcta → HTTP 200 + x-requests-last=20 (h2h+totals, eu).",
    "recommendation": "Fix en branch limpia separada; no mezclar con backfill/artifacts MM-3.1B."
  }
]
```
