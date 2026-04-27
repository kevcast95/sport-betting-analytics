# BT2 — Laboratorio pagado día 1 (subset5)

Ejecutado con `scripts/bt2_vendor_paid_lab_day1.py --all`.

## Entradas

- Manifiesto piloto: `scripts/outputs/bt2_vendor_pilot_prep/pilot_fixture_manifest.csv`
- Congelado día 1: `day1_lab_manifest.csv`

## Salidas clave

- `sm_day1_fixture_master_check.csv` — smoke SportMonks (sin includes de odds).
- `sm_day1_contextual_includes_check.csv` — events/statistics/lineups/…
- `toa_event_matching_results.csv` — discovery histórico + match.
- `toa_h2h_t60_results.csv` — odds h2h T-60; `ingested_at` es solo auditoría (no tiempo de mercado).
- `toa_credit_usage_summary.json` — headers de uso.
- `bt2_vs_toa_exploration.csv` — value pool BT2 vs muestra.
- `lab_day1_summary.json`

## Regenerar solo manifiesto día 1

```bash
python3 scripts/bt2_vendor_paid_lab_day1.py --freeze-only --limit 15
```
