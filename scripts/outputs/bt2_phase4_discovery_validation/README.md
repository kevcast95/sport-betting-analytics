# Discovery / validation — Fase 4

## Metodología

Ver `methodology.json` (parámetros congelados en código del script).

## Universo de esta corrida

- Filas: **99** (scored + `reference_decimal_odds` > 1)
- Días: **['2026-04-12', '2026-04-13', '2026-04-14', '2026-04-15', '2026-04-18', '2026-04-19', '2026-04-20']**
- Discovery días: ['2026-04-12', '2026-04-13', '2026-04-14', '2026-04-15']
- Validation días: ['2026-04-18', '2026-04-19', '2026-04-20']

## Cómo regenerar

```bash
cd /Users/kevcast/Projects/scrapper
PYTHONPATH=. python3 scripts/bt2_phase4_discovery_validation_audit.py
```
