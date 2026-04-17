# Runbook — experimento SofaScore S6.5 (US-OPS-003)

## Roles

- **PO:** accountable presupuesto y aprobación de uso experimental.
- **TL:** responsible caps, throttling, diseño técnico, `--force` si procede.

## Variables (.env)

| Variable | Valor arranque (cerrado) |
|----------|---------------------------|
| `BT2_SFS_EXPERIMENT_ENABLED` | `false` en prod; `true` solo staging durante ventana. |
| `BT2_SFS_EXPERIMENT_MAX_EVENTS_PER_RUN` | `500` |
| `BT2_SFS_HTTP_MAX_RPS` | `4` |
| `BT2_SFS_HTTP_TIMEOUT_SEC` | `25` |
| `BT2_SFS_BASE_URL` | `https://www.sofascore.com/api/v1` |
| `BT2_SFS_JOIN_SEED_JSON_PATH` | opcional: JSON `{"sportmonks_fixture_id": sofascore_event_id, ...}` |
| `BT2_DATABASE_URL` | **solo** Postgres staging para corridas del experimento. |

## Kill switch / apagado

1. Poner `BT2_SFS_EXPERIMENT_ENABLED=false`.
2. Detener cualquier cron `scripts/bt2_sfs/cli.py`.
3. Verificar que no queden procesos `cli.py` en el host (`ps` / supervisor).
4. Registrar fecha y operador en `sprint-06.5-validate/EJECUCION.md` § drill.

## Job daily (corte 00:00 UTC día siguiente)

- El job **no** debe reactivarse solo: una corrida manual o cron explícito por día.
- Tras `00:00 UTC` del día siguiente al ancla, cerrar la corrida y no ampliar `run_id` existente.

## Retención (T-276)

- Evidencia: durante el sprint + acta + **30 días**.
- Post-30d: ticket o job `DELETE` sobre `bt2_provider_odds_snapshot` / `bt2_dsr_ds_input_shadow` / `bt2_sfs_join_audit` por `run_id` de prueba (no automatizado en este repo salvo script explícito futuro).

## Comandos

Ver `scripts/bt2_sfs/cli.py -h`.

Migración: `alembic upgrade j4k5l6m7n8o9` (revision `j4k5l6m7n8o9`).

## Alerta 80 % cap

Si el conteo de requests SFS se acerca al presupuesto diario acordado, TL notifica a PO antes de ampliar límites (solo por escrito en `EJECUCION.md` o PR).
