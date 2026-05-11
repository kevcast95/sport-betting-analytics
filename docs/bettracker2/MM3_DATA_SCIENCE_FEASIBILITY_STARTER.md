# MM3 Data Science Feasibility Starter

MM means Multi-Market: evaluating BT2 beyond a single market lane, especially FT_1X2 and OU2.5, while preserving market/selection/line contracts and avoiding leakage.

## Why MM-3

MM-3 is a data science feasibility phase, not another prompt bake-off. The MM lab found that DSR did not beat benchmark in the repaired 2025 baseline sample, Opus/GPT screenshot/minimal prompts did not produce robust edge, enriched SportMonks context is safe descriptively but not ready as a decision signal, OU2.5 was toxic in evaluated slices, and FT_1X2 benchmark/policy appears more promising.

## Objective

Audit whether the data across the 120 leagues can support ML: build a leakage-safe dataset, train simple models, validate temporally against benchmark, and simulate ROI/policy before any product claim.

## Phases

- MM-3.0 data coverage audit.
- MM-3.1 feature dataset.
- MM-3.2 baseline ML models.
- MM-3.3 temporal validation.
- MM-3.4 ROI/policy simulation.

## Branch recommendation

Create `phase4/mm3-data-science-feasibility` from `origin/main` only after the MM branch consolidation is documented and minimal fixes are either promoted or explicitly deferred.

## Non-goals

Do not run DSR, TOA, SportMonks, betting, Telegram, vault, production jobs, or DB writes as part of this starter.
