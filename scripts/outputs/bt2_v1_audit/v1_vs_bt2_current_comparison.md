# v1 vs BT2 Current Comparison

## Comparación metodológica

No es apples-to-apples. v1/core usa SofaScore + SQLite + multi-mercado + Telegram/producto. BT2 shadow v6 usa `bt2_shadow_*`, subset5 SportMonks/TOA, FT_1X2/h2h-only en el adapter shadow-native y replay controlado.

## v1/core

- Filosofía: picker publicable, máximo 2 picks por evento, multi-mercado, edge subjetivo.
- Input: bundles SofaScore procesados con lineups, h2h, rachas, stats, odds_all/featured; tenis con rankings/superficie.
- Emisión: puede devolver `picks=[]`, pero no hay abstención formal como terminal.
- Evaluación: `pick_results.outcome` win/loss/pending; no existe `no_evaluable` nativo, se infiere en esta auditoría.
- Performance ventana 2026-03-23..2026-04-10: {'picks': 316, 'events_with_picks': 232, 'hit': 166, 'miss': 109, 'pending_result': 5, 'no_evaluable': 34, 'void': 2, 'scored': 275, 'hit_rate_on_scored': 0.603636, 'roi_flat_units': -5.188, 'roi_flat_stake_pct_on_scored': -1.886545}.

## BT2 shadow v6 actual

Según docs Fase 4:

- Filosofía real observada: single-stage FT_1X2; prompt dice no elegir favorito automáticamente, pero `UNKNOWN` queda restringido y se prefiere pick.
- Input: `ds_input` shadow-native con odds/contexto juntos; lee `bt2_shadow_*` para gate/persistencia y CDM/raw SM como contexto/verdad auxiliar.
- Mercado: efectivamente FT_1X2/h2h desde TOA. BTTS/OU2.5 no están listos en shadow-native.
- Emisión: 246 OK de 259 ejecutados en v6, 12 postprocess reject, 1 failed.
- Sesgo al favorito: 245/246 picks OK igualan favorito en summary original; benchmark recalculado 245/259 comparables igualan favorito, 94.5946%.
- Performance documentada: DSR 129/246 hit, ROI -2.1463%; always-favorite 134/259 hit, ROI -2.8340%.

## Selective FT_1X2 nuevo

- Estado: contrato/scaffold, no runner persistido/evaluable.
- Promesa metodológica: `emit/abstain`, clasificación `reinforce/strong_tension/weak_tension/unresolved/market_only`, benchmark always-favorite same-slice.
- No hay evidencia de performance aún.

## Qué ganó BT2

- Separación shadow/producto más limpia.
- Trazabilidad por run family, prompt version, parse status, truth source y benchmark trivial.
- Métricas más correctas si se implementa el contrato Fase 4A.

## Qué perdió frente a v1/core

- Framing directo de producto: “dado un grupo de eventos, dime picks probables/publicables”.
- Multi-mercado práctico.
- Señales SofaScore ricas y simples en el input pre-modelo.
- Post-filtros de publicación como edge positivo, cuota mínima y ancla scrapeada.

## Qué no es comparable

- Universo: v1 incluye fútbol, tenis, ligas/torneos amplios e incluso ITF; BT2 v6 subset5 FT_1X2.
- Mercado: v1 multi-mercado; BT2 v6 FT_1X2.
- Evaluación: v1 SofaScore/SQLite con `pending` ambiguo; BT2 shadow usa CDM/SM y estados más explícitos.
- Momento y setup: v1 corridas operativas/Telegram; BT2 v6 replay shadow.
