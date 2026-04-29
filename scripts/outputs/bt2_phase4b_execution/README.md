# Fase 4B — Ejecución (preregistro congelado)

Generado por `scripts/bt2_phase4b_execute.py`.

## Fuentes

- Umbrales y partición: `phase4b_holdout_plan.json` (sin modificación).
- Partición discovery/validation por `run_key`.

## Archivos

- `summary.json` — conteos, notas estructurales y veredicto.
- `by_segment_discovery_validation.csv` — todos los segmentos evaluados.
- `promising_candidates.csv` — estratos `prometedor` (puede estar vacío).
- `noise_segments.csv` / `do_not_interpret_segments.csv` — partición de resultados.

**No producción.** Solo lectura DB shadow.
