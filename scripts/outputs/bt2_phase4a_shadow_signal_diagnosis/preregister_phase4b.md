# Preregistro metodológico — Fase 4B (selective release *disciplinado*, no ejecutado)

Documento generado en Fase 4A.1. **No abre 4B**; fija reglas antes de cualquier ejecución.

## Alcance permitido (cuando se abra 4B)

- **Stack:** mismo shadow validado (subset5, h2h, us, T-60); sin nuevos proveedores.
- **Segmentos elegibles para *screening* (no para concluir edge):**
  - `source_path` ∈ {`cdm_shadow`, `sportmonks_between_subset5_fallback`} con **scored ≥ 50** en el estrato.
  - `by_league` con **scored ≥ 50** por liga (subset5 → normalmente una liga a la vez alcanza umbral).
  - `by_odds_band` con bandas fijas (mismas que 4A) y **scored ≥ 50** por banda.
- **Ventana temporal:** holdout: último mes o último run mensual *no* usado en el ajuste de reglas; definir en el arranque de 4B (pre-registro adicional con fecha de corte).

## Segmentos **no** permitidos para decisiones 4B sin ampliar N

- `daily_shadow_sm_toa` con **picks_total < 50** (muestra actual insuficiente).
- Cualquier estrato con **scored < 50** → solo descriptivo; **prohibido** rotular como “señal” o “regla de release”.
- Estratos con **scored < 20** → **no interpretar** direccionalidad de ROI.

## Reglas fijas reutilizables

- **Bandas de cuota (decimal):** `dec_lt_2`, `dec_2_to_2_5`, `dec_2_5_to_3`, `dec_3_to_4`, `dec_4_to_6`, `dec_ge_6`, `unknown_odds`.
- **Mínimos de N (scored):** ver `summary.json` → `methodology.n_thresholds_scored_4a1` (A/B/C). Criterio 4B: **C_adequate_descriptive** (≥50) para plantear *candidato* a regla; **B** solo genera hipótesis.
- **Split temporal:** proponer “entrenamiento descriptivo” = consolidado pre-Fase 4 hasta corte T; “validación” = sombra posterior o mes siguiente. Detallar en el PR de 4B.

## Criterio “prometedor” vs “ruido”

- **Prometedor (candidato):** ROI% y hit_rate en estrato C con consistencia con narrativa 4A (p. ej. no contradice agregado sin explicación); **sigue siendo** candidato, no producto.
- **Ruido:** tier A o B, o contradicción fuerte con otras capas (path/liga) sin replicación.

## Criterio “no interpretar”

- `interpretation_tier` = `A_inadequate`, o `signal_reading_banned_4a1` = true bajo reglas 4A.1.

## `selection_side` (post 4A.1)

- Distribución al generar: {"home": 137, "away": 125, "unknown": 19, "unknown_resolved_teams": 16}

---

*Fase 4A.1: solo diagnóstico; 4B requiere aprobar explícitamente este preregistro o enmendarlo con versión fechada.*
