# Robustez cohorte A vs benchmark B

## Regenerar

```bash
cd /Users/kevcast/Projects/scrapper
python3 scripts/bt2_historical_sm_lbu_cohort_robustness.py
```

Solo mensual (sin consultas semanales a BD):

```bash
python3 scripts/bt2_historical_sm_lbu_cohort_robustness.py --skip-weekly
```

## Requisito

Summaries mensuales en `scripts/outputs/bt2_historical_sm_lbu_year_scan/blocks/summary_YYYY-MM.json`.

## Salidas

- `robustness_report.json`
- `cohort_A_monthly.csv`, `cohort_B_monthly.csv`
- `cohort_A_weekly.csv`, `cohort_B_weekly.csv` (si no se usa `--skip-weekly`)
