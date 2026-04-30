# v1 Prompt And Input Audit

## Prompt principal fútbol

Ubicación: `jobs/deepseek_batches_to_telegram_payload_parts.py`, `_build_system_prompt` y `_build_user_prompt`.

System prompt observado: analista de fútbol para apuestas, salida solo JSON, razones en español, no inventar cuotas, usar odds desde `processed`.

User prompt observado: “con el lote `batch` (`ds_input`), elige picks para cada evento”. Pide `picks_by_event`, con `motivo_sin_pick` y una lista `picks` de máximo 2 por evento. Mercados permitidos: `1X2`, `Over/Under 2.5`, `BTTS`, `Double Chance`. Pide calcular edge subjetivo: `p_imp_pct = 100 / odds`, elegir `p_real_pct`, `edge_pct = p_real_pct - p_imp_pct`, y confianza por umbrales.

## Prompt tenis

Ubicación: `core/tennis_deepseek_contract.py`.

Define analista ATP/WTA, JSON estricto, no inventar cuotas, usar `processed.tennis_odds` y `processed.odds_all`. En ganador de partido no permite empate; selection `1` o `2`. Mercados: `Match winner`, `First set winner`, `Total games Over/Under` en contrato, aunque el pipeline permite/publica principalmente match winner si hay ancla.

## Input real que veía el modelo

Shape desde `jobs/select_candidates.py`:

- `event_id`
- `sport`
- `selection_tier` A/B
- `schedule_display` con UTC/local
- `event_context`: torneo, equipos/jugadores, estado, start timestamp, score si existe, ids, ronda/superficie en tenis cuando aplica
- `processed`: lineups, statistics, h2h, team_streaks, team_season_stats, odds_all, odds_featured; tenis agrega tennis_odds, rankings, stats y registry
- `diagnostics`: flags de endpoints OK y errores

## Criterio de decisión

- Formulación más cercana a picker de producto: “elige picks” y máximo 2 por evento.
- Abstención operativa: `picks=[]` con motivo, no contrato formal `emit/abstain`.
- Direccionalidad: busca valor por edge subjetivo; no solo “quién gana”.
- Post-filtros alineados a publicabilidad: edge positivo, cuota mínima, ancla scrapeada en tenis, conflicto razón/selección.

## Hallazgos

- El input era más simple y directo que BT2 shadow v6 en framing de producto, pero mezclaba mercado, contexto, edge subjetivo y publicación en un mismo paso.
- SofaScore aportaba señales que BT2 shadow-native h2h-only no siempre usa en el adapter actual: lineups, h2h, rachas, estadísticas, season stats, odds_all extendido, odds_featured y para tenis rankings/superficie.
- El sistema permitía multi-mercado real, pero la evaluabilidad histórica fue irregular: varios OU2.5 quedaron `pending` por normalización `bad_line_or_side_ou`; mercados no soportados quedaron `unsupported_market`.
