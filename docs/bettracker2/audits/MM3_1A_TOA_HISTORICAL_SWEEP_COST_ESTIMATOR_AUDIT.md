# MM-3.1A — TOA Historical Sweep Cost Estimator (Audit)

## 1. Executive summary

- Universo Big 5 en DB local: **3806** eventos con kickoff en rango filtrado.
- Kickoff UTC (min/max): `2023-08-11T12:30:00-05:00` → `2026-04-22T14:30:00-05:00`.
- **Créditos estimados (P0 h2h+totals, eu, política `t60`)**: **54800** (2740 requests × 20 créditos/request).
- Política recomendada para empezar: **T-60** (un snapshot prepartido estable por evento, alineado al laboratorio SM LBU).
- Piloto seguro: **1 liga** (`soccer_epl`), **3–5 días** calendario locales con volumen, **h2h+totals**, **eu**, **T-60**, **request_cap** bajo.
- **¿Listos para backfill mayor?** **No** por defecto (`ready_for_full_backfill=false`); falta piloto exitoso + reconciliación + aprobación explícita.

## 2. Why TOA sweep is needed

`bt2_odds_snapshot` batch no provee `fetched_at` ROI-safe prematch (MM-3.0A). TOA `historical/odds` permite snapshots en timestamps explícitos prepartido.

## 3. Inputs used

- `bt2_events` + `bt2_leagues` + `bt2_teams` (SELECT).
- Mapeo TOA: `apps/api/bt2_theoddsapi_mapping.py`.
- Flags: markets=['h2h', 'totals'], regions=['eu'], timezone=America/Bogota, policy=t60.
- Artefactos previos opcionales: `scripts/outputs/bt2_vendor_lab_day1/toa_credit_usage_summary.json`.

## 4. Fixture inventory

Archivo: `scripts/outputs/mm3_1a_big5_fixture_inventory.csv`.

## 5. Market priorities

- P0: h2h, totals (ejecución estimada / piloto).
- P1: spreads (solo escenarios CSV).
- P2: BTTS, corners, cards, team_totals (scenario F, costo event-level estimado).

## 6. Snapshot policies

- `closing_approx`: kickoff − 3 min (proxy documentado).
- `t60`, `t24`, `t24_t60`, `multi` (T-24 + T-6 + T-1h + cierre-2min).

## 7. Cost formula

Featured `GET /v4/historical/odds`: **créditos = 10 × regiones × mercados × requests**, donde cada **request** es un par único `(sport_key, timestamp_utc)` (deduplicado). Con 2 mercados (h2h+totals) y 1 región (eu) ⇒ **20 créditos por request**.

Para políticas con un solo offset por evento (`closing_approx`, `t60`, `t24`), si los timestamps resultantes no colisionan entre partidos, **requests ≈ número de eventos** (en este inventario: **2740** ≈ **3806** eventos). `t24_t60` y `multi` suman offsets y luego deduplican ⇒ más requests.

P2 event-level / additional markets (escenario F): **10 × R × M × eventos** (estimación conservadora de orden de magnitud; no ejecutado).

## 8. Scenario estimates

`scripts/outputs/mm3_1a_scenario_estimates.csv`.

| Escenario | Mercados | Regiones | Política | Requests | Créditos |
|---|---|---|---:|---:|---:|
| A | h2h,totals | eu | t60 | 2740 | 54800 |
| B | h2h,totals | eu | t24_t60 | 5278 | 105560 |
| C | h2h,totals,spreads | eu | t60 | 2740 | 82200 |
| D | h2h,totals | eu,uk | t60 | 2740 | 109600 |
| E | h2h,totals | eu | multi | 10615 | 212300 |
| F | btts,corners,cards,team_totals,additional_other | eu | t60 | 3806 | 190300 |

## 9. Recommended pilot

- `soccer_epl`, 3–5 días locales, h2h+totals, eu, T-60, cap 20.
- Comando: `python3 scripts/mm3_1a_toa_historical_sweep_cost_estimator.py --allow-toa-api --no-dry-run --request-cap 20`

## 10. Batch plan

- `scripts/outputs/mm3_1a_backfill_batches.json` incluye `pilot_batch_recommended` + `batches`.
- Primer batch sugerido (piloto): `soccer_epl` ventana local `2023-08-11` → `2023-08-14`, ~**7** requests, ~**140** créditos (política `t60` actual).

## 11. Pilot execution status

Ejecutado

## 12. Cost reconciliation

`scripts/outputs/mm3_1a_cost_reconciliation.json`.

## 13. Sweep readiness

`scripts/outputs/mm3_1a_sweep_readiness.json`.

## 14. Risks

- Mismatch equipos BT2 ↔ TOA; líneas ausentes en timestamp; costo real vs `x-requests-last`; rate limits.

## 15. Recommended next step

1. Ejecutar piloto con `--allow-toa-api --no-dry-run` y revisar `mm3_1a_cost_reconciliation.json`.
2. Ajustar batch size según headers reales.
3. Solicitar aprobación explícita antes de cualquier backfill amplio.
