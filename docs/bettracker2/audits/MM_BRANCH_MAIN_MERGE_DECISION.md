# MM Branch Main Merge Decision

## Compared branches

- Lab branch: `phase3g/monitor-resultados-shadow-mode`
- Clean merge branch: `cleanup/mm-promote-minimal-fixes`
- Base main: `origin/main` at `192f706d92de058ddc916ccf82051d3727659b64`

## Decision

Do not merge the lab branch into `main`.

Merge only `cleanup/mm-promote-minimal-fixes`, which extracts the minimal reusable fixes from the MM lab:

- TOA Ligue 1 sport key corrected to `soccer_france_ligue_one`.
- Totals line preservation in BT2 odds aggregation, so `OU_GOALS_2_5` is not inferred from totals rows without an explicit 2.5 line.
- Focused unit tests for both fixes.
- Ignore rules for future MM/raw/model-output artifacts.
- Short MM-3 starter doc.

## Main diff to merge

The clean branch changes only:

- `.gitignore`
- `apps/api/bt2_dsr_odds_aggregation.py`
- `apps/api/bt2_sprint06_test.py`
- `apps/api/bt2_theoddsapi_mapping.py`
- `apps/api/bt2_theoddsapi_mapping_test.py`
- `docs/bettracker2/MM3_DATA_SCIENCE_FEASIBILITY_STARTER.md`
- `docs/bettracker2/audits/MM_BRANCH_CLEAN_START_EXECUTION.md`
- `docs/bettracker2/audits/MM_BRANCH_MAIN_MERGE_DECISION.md`
- `scripts/bt2_atraco/run_atraco.py`
- `scripts/bt2_atraco/theoddsapi_worker.py`

## Excluded from main

- MM raw payloads and large generated CSV/JSON outputs.
- DSR raw/model outputs and rendered prompt packages.
- Manual bake-off outputs.
- Experimental MM runners and enriched-context scanners.
- Shadow monitoring branch commits unrelated to the minimal MM cleanup.

## Verification before merge

- `SPORTMONKS_API_KEY=dummy BT2_DATABASE_URL=postgresql://user:pass@localhost:5432/db python3 -m unittest apps.api.bt2_theoddsapi_mapping_test apps.api.bt2_sprint06_test apps.api.bt2_fixture_prob_coherence_test apps.api.bt2_sfs_odds_bridge_test`
- `python3 -m py_compile apps/api/bt2_theoddsapi_mapping.py apps/api/bt2_dsr_odds_aggregation.py scripts/bt2_atraco/run_atraco.py scripts/bt2_atraco/theoddsapi_worker.py`
- `rg -n "soccer_france_ligue_1" apps scripts -g '!scripts/outputs/**'`

## Next branch

After `main` is fast-forwarded to this clean commit, create/switch to:

`phase4/mm3-data-science-feasibility`

This branch starts from clean `main` and should not contain MM-3 implementation yet.
