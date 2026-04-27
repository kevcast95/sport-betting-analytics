# BT2 — Preparación piloto The Odds API (subset 5)

Congelado desde `vendor_validation_sample.csv` + `pilot_league_manifest.json`: solo `priority_pilot_now`, ligas subset5, `h2h`, `us`, T-60 del sample.

## Regenerar

```bash
cd /Users/kevcast/Projects/scrapper
python3 scripts/bt2_theoddsapi_pilot_day1_dryrun.py --generate
python3 scripts/bt2_theoddsapi_pilot_day1_dryrun.py
```

## Artefactos

- `pilot_fixture_manifest.csv`
- `pilot_request_plan.csv`
- `pilot_persistence_contract.md`
- `pilot_result_taxonomy.md`
- `pilot_prep_summary.json`

Ver `pilot_prep_summary.json` para conteos y créditos estimados.
