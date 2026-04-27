# Panel por liga — cohorte A

## Regenerar

```bash
cd /Users/kevcast/Projects/scrapper
python3 scripts/bt2_historical_sm_lbu_cohort_A_league_panel.py
```

## Umbral

Solo ligas con `n_fixtures >= 30` en `league_outliers_A.csv`. El resto en `summary.json` → `below_threshold_mass`.

## Contrato

Mismo `historical_sm_lbu` + T-60 que `bt2_historical_sm_lbu_replay_prototype.py`.
