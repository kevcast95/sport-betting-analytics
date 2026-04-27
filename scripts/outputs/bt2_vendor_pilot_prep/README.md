# BT2 — Preparación piloto The Odds API (subset 5)

- **Base:** `vendor_validation_sample.csv` + `pilot_league_manifest.json` — `priority_pilot_now`, subset5, `h2h`, `us`, T-60 (sample 3D).
- **Complemento (representatividad 5 ligas):** si el sample no trae alguna liga del subset5, se añaden fixtures desde `bt2_events` (cohorte A, mismo criterio mapeo/T-60 que 3D). Sin top-up: `BT2_PILOT_TOPUP_OFFLINE=1`.

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

Ver `pilot_prep_summary.json` para conteos, `pilot_representative_subset5_verdict` y créditos estimados.
