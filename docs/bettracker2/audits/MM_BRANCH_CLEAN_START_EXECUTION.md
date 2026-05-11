# MM Branch Clean Start Execution

Generated from the clean branch `cleanup/mm-promote-minimal-fixes`.

## Summary

This branch promotes only the small, reusable fixes found during the MM lab consolidation. It does not merge the lab branch, does not include raw outputs, does not run DSR/TOA/SportMonks, and does not start MM-3.

## Promoted now

- Centralized The Odds API Tier S mapping in `apps/api/bt2_theoddsapi_mapping.py`.
- Fixed Ligue 1 TOA key usage from stale `soccer_france_ligue_1` to `soccer_france_ligue_one`.
- Preserved totals line semantics in odds aggregation: provider `point` is now used when available, so `OU_GOALS_2_5` is activated only for line 2.5 and other supported lines remain separate.
- Added focused unit tests for the TOA mapping and totals line preservation.
- Added `.gitignore` rules for future heavy lab outputs under `scripts/outputs`.

## Verification

- `SPORTMONKS_API_KEY=dummy BT2_DATABASE_URL=postgresql://user:pass@localhost:5432/db python3 -m unittest apps.api.bt2_theoddsapi_mapping_test apps.api.bt2_sprint06_test apps.api.bt2_fixture_prob_coherence_test apps.api.bt2_sfs_odds_bridge_test` -> 20 tests OK.
- `python3 -m py_compile apps/api/bt2_theoddsapi_mapping.py apps/api/bt2_dsr_odds_aggregation.py scripts/bt2_atraco/run_atraco.py scripts/bt2_atraco/theoddsapi_worker.py` -> OK.
- `rg -n "soccer_france_ligue_1" apps scripts -g '!scripts/outputs/**'` -> no runtime matches.

## Kept out of main

- MM raw payloads, model outputs, rendered prompts, stage packages, logs, checkpoints, and manual bake-off outputs.
- Full MM/DSR/enriched/backtest runners from the lab branch.
- Any production, vault, Telegram, DB write, provider API, or betting flow.

## MM-3 start rule

Start MM-3 from `origin/main` or from this minimal cleanup branch after review/merge. Do not start MM-3 from `phase3g/monitor-resultados-shadow-mode`.
