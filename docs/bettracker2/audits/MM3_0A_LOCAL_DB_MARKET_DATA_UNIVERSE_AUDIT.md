# MM-3.0A — Auditoría del universo market/data (DB local BT2)

**Modo:** solo lectura (`SELECT`). Sin APIs externas, SportMonks, TOA, DSR ni escrituras.

**Generado (UTC):** `2026-05-12T01:22:43.864251+00:00`

## Resumen ejecutivo

| Métrica | Valor |
|--------|-------|
| Eventos `bt2_events` | 44225 |
| Kickoff min / max | `2023-08-01 11:30:00-05:00` / `2026-04-22 18:30:00-05:00` |
| Con marcador final (goles home/away) | 43569 |
| Filas `raw_sportmonks_fixtures` (payload objeto) | 55541 |
| Fixture date min/max (raw) | `2023-08-01` / `2026-04-22` |
| Cobertura probabilística base (marcador) | **43569** eventos |
| Cobertura ROI FT (prematch + marcador) | **102** eventos |
| Cobertura ROI OU2.5 (ex-ante, patrón texto) | **0** eventos |
| Cobertura ROI cualquier mercado prematch | **102** eventos |
| Filas FT en snapshot (ignora `fetched_at`; solo presencia) | **41724** eventos con marcador |
| Filas OU 2.5 en snapshot (ignora tiempo) | **0** eventos con marcador |
| Cualquier fila odds (ignora tiempo) | **41724** eventos con marcador |

**Interpretación:** si `n_snap_*` ≫ `n_roi_*`, las cuotas están materializadas pero **no** como capturas pre-partido en `fetched_at` (típico de backfill batch). Para ROI ex-ante estricto, MM-3.1 puede necesitar timestamps de libro en `raw_sportmonks_fixtures` (LBU) u otra fuente temporal — fuera del alcance de este script read-only.

Base operativa: **partidos con `result_home` y `result_away` no nulos** en `bt2_events` (ver `mm3_0a_market_outcome_feasibility.csv`). Derivados OU/BTTS son deterministas desde el marcador.

### B. ROI / backtest

Regla temporal auditada: **filas en `bt2_odds_snapshot` con `fetched_at < kickoff_utc`** (corte pre-partido simple). No se aplicó T-60 aquí; si MM-3 exige T-60, refinar en MM-3.1 con la misma DB.

Corners/tarjetas como **outcome de modelo**: no hay columnas dedicadas en `bt2_events`; proxies sobre `raw_sportmonks_fixtures.payload` en `mm3_0a_market_outcome_feasibility.csv`. Mercados de corners/tarjetas en cuotas: ver patrones en `mm3_0a_odds_market_coverage.csv`.

## Artefactos

| Archivo | Descripción |
|---------|-------------|
| `scripts/outputs/mm3_0a_table_inventory.csv` | Inventario tablas `public` + estimates |
| `scripts/outputs/mm3_0a_historical_range_summary.json` | earliest/latest kickoff, años, seasons |
| `scripts/outputs/mm3_0a_historical_range_inventory.csv` | Por año y `sm_league_id`: filas `bt2_events` + `raw_sportmonks_fixtures`; comparación raw vs bt2 en el JSON resumen |
| `scripts/outputs/mm3_0a_event_result_coverage.csv` | Por año/mes/liga |
| `scripts/outputs/mm3_0a_market_outcome_feasibility.csv` | Factibilidad de outcomes |
| `scripts/outputs/mm3_0a_odds_market_coverage.csv` | Odds por año/liga/mercado |
| `scripts/outputs/mm3_0a_market_training_candidate_matrix.csv` | Matriz prob vs ROI |
| `scripts/outputs/mm3_0a_league_coverage_120_sm.csv` | Top 120 ligas del catálogo por volumen |
| `scripts/outputs/mm3_0a_recommended_markets.json` | Recomendación conservadora |

## Conteos exactos (tablas núcleo)

```json
{
  "bt2_events": 44225,
  "raw_sportmonks_fixtures": 55541,
  "bt2_odds_snapshot": 457934,
  "bt2_leagues": 100,
  "bt2_teams": 3074,
  "bt2_daily_picks": 195
}
```

## Respuesta a la pregunta MM-3.0A

Con **esta** instantánea de la DB local:

1. **Años:** ver lista `calendar_years_by_kickoff_utc` en `mm3_0a_historical_range_summary.json` y granularidad en los CSV por año/mes.
2. **Ligas:** `mm3_0a_league_coverage_120_sm.csv` prioriza las 120 ligas del catálogo con más eventos en `bt2_events` (si el catálogo tiene menos de 120 filas, habrá menos filas).
3. **Mercados para modelo de probabilidad:** cualquier outcome derivable del marcador (FT, OU líneas, BTTS) donde haya muestra en **A**; proxies corners/cards desde estadísticas raw si aplica.
4. **Mercados para ROI:** subconjunto de **A** donde existan filas prematch en `bt2_odds_snapshot` para el mercado objetivo (matriz en `mm3_0a_market_training_candidate_matrix.csv`).
5. **Primer target sugerido MM-3:** **`FT_1X2`** (mayor solidez outcome + presencia histórica de mercados 1X2 / Match Winner en snapshots); **`OU_GOALS_2_5`** como segundo eje por alineación con CDM histórico — validar año por año en cobertura de odds.

**Limitación:** esta auditoría no evalúa calidad de cuotas ni fugas temporales más allá del corte `fetched_at < kickoff_utc`.
