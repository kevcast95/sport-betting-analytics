# BT2 Fase 4 — edge audit (primer corte)

Ventana: **2026-04-13** → **2026-04-20** (evaluación oficial scored).

Archivos:
- `summary.json` — global, bloques A/B, candidatos “mejor que global” heurísticos.
- `segments.csv` — una fila por dimensión:valor de segmento.

Regenerar:

```bash
cd /Users/kevcast/Projects/scrapper
PYTHONPATH=. python3 scripts/bt2_phase4_selective_release_edge_audit.py \
  --date-from 2026-04-13 --date-to 2026-04-20 --split-day 2026-04-19
```

N global scored (esta corrida): **79**.
