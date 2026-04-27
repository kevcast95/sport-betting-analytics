# Drill-down cohorte A (semanas débiles)

## Regenerar

Requiere `cohort_A_weekly.csv` del paso de robustez:

```bash
cd /Users/kevcast/Projects/scrapper
python3 scripts/bt2_historical_sm_lbu_cohort_robustness.py
python3 scripts/bt2_historical_sm_lbu_cohort_A_drilldown.py
```

## Salidas

- `drilldown_summary.json` — criterio de selección, ranking, semanas elegidas, razones `observable_reason` entre no-VP.
- `fixtures_selected_weeks.csv` — nivel fixture.
- `aggregates_by_league_tier_week.csv`, `aggregates_by_day_week.csv`, `aggregates_by_hour_bucket_week.csv`
- `aggregates_by_league_pooled.csv` — ligas en las semanas objetivo (pooled).

**T-60** y agregador: mismos que `bt2_historical_sm_lbu_replay_prototype.py`.
