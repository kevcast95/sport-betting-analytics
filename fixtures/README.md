# Fixtures de prueba

## `ds_input_tier_B_synthetic.json`

Un único objeto con la misma forma que `ds_input[0]` tras `select_candidates`:

- **`selection_tier`: `"B"`** — simula `statistics_ok=false` (404 o vacío en SofaScore).
- **Partido no terminado** — útil para prompts “pre-partido”.
- **`processed.odds_*`** — cuotas decimales inventadas solo para **probar formato / reasoner**; no son de mercado real.

Uso: pegar el contenido en tu prompt RUN-ONCE como sustituto de `ds_input[0]` cuando no haya datos en vivo.

## Tier B y edge

Para **edge numérico** no hace falta panel de estadísticas del partido: basta **cuota** (`p_imp = 100/odds`) y una **`p_real`** subjetiva razonada con lineups, H2H, rachas y forma implícita en las cuotas. El modelo no debe exigir xG si el tier es B.

## Datos reales

Cuando SofaScore falle en `/statistics` pero respondan lineups + h2h + team-streaks + odds, el pipeline debe dejarte candidatos **Tier B**. Si sigues con 0 candidatos, revisa `rejection_reasons` en la salida de `select_candidates` (a menudo `h2h_not_ok` o `lineups_not_ok`, no solo estadísticas).
