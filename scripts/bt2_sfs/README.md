# Scripts BT2 — experimento SofaScore (S6.5)

Ver runbook: `docs/bettracker2/runbooks/bt2_sfs_experiment_s65.md`.

```bash
# Migración (desde apps/api)
alembic upgrade j4k5l6m7n8o9

# Ejemplos (raíz repo; requiere Postgres + datos bt2_events)
python scripts/bt2_sfs/cli.py historical --run-id s65-h1 --anchor-date 2026-04-17 --force
python scripts/bt2_sfs/cli.py metrics --run-id s65-h1 --out-json out/s65_metrics.json
python scripts/bt2_sfs/cli.py shadow --run-id s65-h1 --limit 20 --force
python scripts/bt2_sfs/cli.py export-join --run-id s65-h1 --out-csv out/s65_join.csv
```
