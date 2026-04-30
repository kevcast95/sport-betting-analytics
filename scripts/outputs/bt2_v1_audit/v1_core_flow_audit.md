# v1 Core Flow Audit

## Flujo reconstruido

1. `jobs/ingest_daily_events.py` crea/completa `daily_runs` y persiste snapshots/features con ayuda de `core/event_bundle_scraper.py`.
2. `jobs/select_candidates.py` lee `event_features` del `daily_run.created_at_utc`, filtra por contrato Tier A/B y escribe `out/candidates_YYYY-MM-DD[_sport]_select.json`.
3. `jobs/event_splitter.py` corta por ventana `exec_06h`, `exec_14h` o `exec_full_day`.
4. `jobs/split_ds_batches.py --slim` parte `ds_input` en lotes bajo `out/batches/`.
5. `jobs/deepseek_batches_to_telegram_payload_parts.py` llama DeepSeek y transforma salida del modelo a payload publicable.
6. `jobs/merge_telegram_payload_parts.py`, `jobs/allocate_bankroll.py`, `jobs/render_telegram_payload.py` preparan Telegram.
7. `jobs/persist_picks.py --telegram-payload` persiste en `picks`.
8. `jobs/validate_picks.py` consulta SofaScore y liquida en `pick_results`.
9. `jobs/report_effectiveness.py` agrega win rate/ROI desde `picks` + `pick_results`.

## Script/job que generaba picks

- Orquestador: `jobs/independent_runner.py --mode window --persist-picks` o `--mode full_day`.
- Generador LLM: `jobs/deepseek_batches_to_telegram_payload_parts.py`.
- Persistencia: `jobs/persist_picks.py`.

## Modelo

- Default del runner: `DS_ANALYSIS_MODEL`, luego `DS_MODEL`, y si no existe: `deepseek-reasoner`.
- Script directo default: `deepseek-reasoner`.
- Chat fallback para convertir reasoning a JSON: `DS_CHAT_MODEL` o `deepseek-chat`.

## Fuentes de datos

- Principal: SofaScore vía Playwright/API request en `core/event_bundle_scraper.py`.
- Persistencia histórica: SQLite `db/sport-tracker.sqlite3` (`daily_runs`, `event_features`, `picks`, `pick_results`).
- Odds: `processed.odds_all`, `processed.odds_featured`; post-proceso usa `core/scraped_odds_anchor.py` para anclar cuotas scrapeadas cuando existen.

## Mercados observados en ventana 2026-03-23..2026-04-10

[
  {
    "market": "Match winner",
    "picks": 119,
    "hit": 65,
    "miss": 49,
    "pending_result": 2,
    "no_evaluable": 3,
    "void": 0,
    "scored": 114,
    "hit_rate_on_scored": 0.570175,
    "roi_flat_units": -14.652,
    "roi_flat_stake_pct_on_scored": -12.852632
  },
  {
    "market": "1X2",
    "picks": 84,
    "hit": 55,
    "miss": 26,
    "pending_result": 1,
    "no_evaluable": 0,
    "void": 2,
    "scored": 81,
    "hit_rate_on_scored": 0.679012,
    "roi_flat_units": 12.053,
    "roi_flat_stake_pct_on_scored": 14.880247
  },
  {
    "market": "Over/Under 2.5",
    "picks": 42,
    "hit": 9,
    "miss": 8,
    "pending_result": 0,
    "no_evaluable": 25,
    "void": 0,
    "scored": 17,
    "hit_rate_on_scored": 0.529412,
    "roi_flat_units": -1.997,
    "roi_flat_stake_pct_on_scored": -11.747059
  },
  {
    "market": "BTTS",
    "picks": 28,
    "hit": 15,
    "miss": 12,
    "pending_result": 1,
    "no_evaluable": 0,
    "void": 0,
    "scored": 27,
    "hit_rate_on_scored": 0.555556,
    "roi_flat_units": -0.005,
    "roi_flat_stake_pct_on_scored": -0.018519
  },
  {
    "market": "First set winner",
    "picks": 22,
    "hit": 12,
    "miss": 8,
    "pending_result": 1,
    "no_evaluable": 1,
    "void": 0,
    "scored": 20,
    "hit_rate_on_scored": 0.6,
    "roi_flat_units": -1.388,
    "roi_flat_stake_pct_on_scored": -6.94
  },
  {
    "market": "Double Chance",
    "picks": 9,
    "hit": 5,
    "miss": 4,
    "pending_result": 0,
    "no_evaluable": 0,
    "void": 0,
    "scored": 9,
    "hit_rate_on_scored": 0.555556,
    "roi_flat_units": -2.873,
    "roi_flat_stake_pct_on_scored": -31.922222
  },
  {
    "market": "Both Teams To Score",
    "picks": 3,
    "hit": 2,
    "miss": 1,
    "pending_result": 0,
    "no_evaluable": 0,
    "void": 0,
    "scored": 3,
    "hit_rate_on_scored": 0.666667,
    "roi_flat_units": 0.524,
    "roi_flat_stake_pct_on_scored": 17.466667
  },
  {
    "market": "Total Goals Over/Under 2.5",
    "picks": 2,
    "hit": 0,
    "miss": 0,
    "pending_result": 0,
    "no_evaluable": 2,
    "void": 0,
    "scored": 0,
    "hit_rate_on_scored": null,
    "roi_flat_units": 0,
    "roi_flat_stake_pct_on_scored": null
  },
  {
    "market": "full_time_1x2",
    "picks": 2,
    "hit": 0,
    "miss": 0,
    "pending_result": 0,
    "no_evaluable": 2,
    "void": 0,
    "scored": 0,
    "hit_rate_on_scored": null,
    "roi_flat_units": 0,
    "roi_flat_stake_pct_on_scored": null
  },
  {
    "market": "over_under_2.5",
    "picks": 2,
    "hit": 2,
    "miss": 0,
    "pending_result": 0,
    "no_evaluable": 0,
    "void": 0,
    "scored": 2,
    "hit_rate_on_scored": 1.0,
    "roi_flat_units": 1.95,
    "roi_flat_stake_pct_on_scored": 97.5
  },
  {
    "market": "Full Time 1X2",
    "picks": 1,
    "hit": 1,
    "miss": 0,
    "pending_result": 0,
    "no_evaluable": 0,
    "void": 0,
    "scored": 1,
    "hit_rate_on_scored": 1.0,
    "roi_flat_units": 2.2,
    "roi_flat_stake_pct_on_scored": 220.0
  },
  {
    "market": "Current set winner",
    "picks": 1,
    "hit": 0,
    "miss": 0,
    "pending_result": 0,
    "no_evaluable": 1,
    "void": 0,
    "scored": 0,
    "hit_rate_on_scored": null,
    "roi_flat_units": 0,
    "roi_flat_stake_pct_on_scored": null
  },
  {
    "market": "Over/Under 2.5 Goals",
    "picks": 1,
    "hit": 0,
    "miss": 1,
    "pending_result": 0,
    "no_evaluable": 0,
    "void": 0,
    "scored": 1,
    "hit_rate_on_scored": 0.0,
    "roi_flat_units": -1.0,
    "roi_flat_stake_pct_on_scored": -100.0
  }
]

## Política de emisión

- No era picker universal estricto: el prompt exigía una fila por evento, pero permitía `picks=[]` con `motivo_sin_pick`.
- Sí era picker/producto: máximo 2 picks por evento, multi-mercado, con edge subjetivo y confianza.
- Había filtros posteriores: cuota mínima, edge positivo, conflictos razón/selección, tenis requiere cuota scrapeada por defecto.
- No tenía contrato moderno de abstención: no separaba `abstained` como terminal comparable a Fase 4A.

## Outputs

- Artefactos: `out/candidates_*`, `out/batches/*`, `out/payload_*`, `out/telegram_payload.json`, `out/telegram_message.txt`, `out/reports/effectiveness_*`.
- Tablas: `picks`, `pick_results`, `daily_run_event_model_feedback`, `pick_baseline_snapshots`, `pick_signal_checks`.
