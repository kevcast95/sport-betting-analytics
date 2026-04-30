# v1 Core Identity Map

## Identificación

Para esta auditoría, `v1` no se trata como versión formal de BT2. Se identifica como el sistema previo/paralelo no-BT2 sustentado por `core/`, `jobs/`, `processors/`, `db/` SQLite y artefactos `out/`.

## Evidencia documental

- `docs/bettracker2/00_IDENTIDAD_PROYECTO.md`: BT2 objetivo exige API-first, ACL, CDM, trazabilidad y migración incremental sin apagar V1. No enumera todos los paths, pero separa conceptualmente V1 de V2/BT2.
- `docs/GUIA_OPERACION_Y_ARQUITECTURA.md`: define el sistema histórico: `core/` para HTTP/SofaScore/scraper/contratos, `jobs/` para ingest/select/DeepSeek/persist/validate/report, `db/` SQLite para `picks` y `pick_results`, `out/` para candidatos/batches/payloads.
- `openclaw.md`: confirma el flujo operativo previo: ingest -> select_candidates -> análisis DeepSeek -> persist_picks -> validate_picks.

## Rutas auditadas de v1/core y piezas asociadas

- `core/event_bundle_scraper.py`: construye bundles SofaScore por evento: event, lineups, statistics, h2h, team-streaks, odds/all, odds/featured; para tenis agrega rankings, stats y registry.
- `core/candidate_contract.py`: contrato de elegibilidad Tier A/B. Fútbol exige event + lineups + h2h + streaks + odds; tenis exige event + odds.
- `core/scraped_odds_anchor.py`: extrae cuota decimal scrapeada para 1X2, Double Chance, BTTS, OU2.5 y tenis match winner.
- `core/validate_pick.py` y `core/validate_1x2.py`: settlement vía SofaScore event final.
- `core/tennis_deepseek_contract.py`: prompt/contrato de tenis.
- `jobs/select_candidates.py`: selecciona `ds_input` desde `event_features`.
- `jobs/deepseek_batches_to_telegram_payload_parts.py`: prompt principal fútbol/tenis y llamada DeepSeek.
- `jobs/persist_picks.py`: persiste picks en SQLite.
- `jobs/validate_picks.py` + `processors/pick_settlement.py`: evaluación histórica.
- `jobs/report_effectiveness.py`: métricas win rate y ROI unitario.

## Rutas BT2 contrastadas

- `apps/api/bt2_*`, `scripts/bt2_*`, `apps/api/alembic/versions/*bt2*`.
- Shadow actual: `scripts/bt2_shadow_native_dsr_pilot.py`, `scripts/bt2_shadow_dsr_full_replay_native.py`, `apps/api/bt2_dsr_shadow_native_*`, tablas `bt2_shadow_*` y artefactos `scripts/outputs/bt2_shadow_dsr_replay/*`.

## Contexto Fase 4 usado

- Shadow v6 es single-stage, FT_1X2, input con odds+contexto juntos, universo `bt2_shadow_*`, adapter shadow-native TOA h2h-only.
- Métricas correctas: separar eligible, emitted, abstained, parse_failed, postprocess_reject, scored, pending_result, no_evaluable y ROI sobre scored.
- Selective FT_1X2 aún es scaffold, no runner persistido/evaluable.
- Two-stage existe como experimento formal documentado/scaffold, no como pipeline real.
