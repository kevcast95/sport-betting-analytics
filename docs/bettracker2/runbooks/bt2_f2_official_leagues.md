# Runbook — Universo F2: 5 ligas y KPI de cierre (T-258 / T-264)

## Fuente normativa

[`DECISIONES_CIERRE_F2_S6_3_FINAL.md`](../sprints/sprint-06.3/DECISIONES_CIERRE_F2_S6_3_FINAL.md) §7.

## IDs canónicos

- **Código:** `apps/api/bt2_f2_league_constants.py` — `F2_OFFICIAL_LEAGUE_SPORTMONKS_IDS` (SportMonks) y resolución a `bt2_leagues.id`.
- **Override:** variable de entorno `BT2_F2_OFFICIAL_LEAGUE_IDS` (lista de `bt2_leagues.id` separados por coma) si tu seed no coincide con los `sportmonks_id` por defecto.

## Verificación en SQL

```sql
SELECT id, name, sportmonks_id FROM bt2_leagues
WHERE id = ANY(string_to_array(current_setting('app.f2_ids', true), ',')::int[]);
-- o manual: WHERE sportmonks_id IN (8, 564, 384, 82, 301);
```

## KPI y reporte 30d

- **API:** `GET /bt2/admin/analytics/f2-pool-eligibility-metrics` (header `X-BT2-Admin-Key`).
  - Parámetros: `operatingDayKey` opcional, `days` (default 30) si no hay día único.
- **Script:** `python3 scripts/bt2_cdm/job_f2_closure_report.py --days 30`
  - Opcional: `--write-md ruta/snippet.md` para pegar evidencia en `EJECUCION_CIERRE_F2_S6_3.md`.

## Tier A — lineups

Refuerzo opcional: `BT2_F2_TIER_A_REQUIRE_LINEUPS=1` (por defecto **0** en código) para exigir `lineups_ok` en eventos Tier A de las 5 ligas cuando la cobertura sea estable.
