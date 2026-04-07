# Sprint 04 — TASKS

> Fuente de verdad para el agente ejecutor Backend.
> Marcar `[x]` solo cuando la tarea esté completada y verificada manualmente.
> Sprint 04 es Backend — no tocar `apps/web/`.

## Numeración

Las tareas de Sprint 03 llegaron hasta T-095. Sprint 04 comienza en **T-096**.

## Orden de ejecución obligatorio

```
T-096 → T-097 → T-098 → T-099 → T-100 → T-101 → T-102 → T-103
```

---

## Ola 1 — Schema conductual (US-BE-009)

- [x] T-096 (US-BE-009) — Modelos SQLAlchemy en `bt2_models.py` para las 6 tablas:
  - `Bt2Pick`: picks del usuario con FK a bt2_users y bt2_events.
  - `Bt2OperatingSession`: sesión conductual diaria (unique user_id + operating_day_key).
  - `Bt2BankrollSnapshot`: historial de balance por evento.
  - `Bt2DpLedger`: ledger de Discipline Points.
  - `Bt2BehavioralBlock`: registros de bloqueos de impulso.
  - `Bt2UserSettings`: configuración conductual 1:1 con bt2_users (PK = user_id).

- [x] T-097 (US-BE-009) — Migración Alembic + integración en register:
  - `alembic revision --autogenerate -m "behavioral_domain_sprint04"`.
  - `alembic upgrade head` — verificar con `alembic current`.
  - `alembic downgrade -1 && alembic upgrade head` — sin error.
  - Modificar `POST /bt2/auth/register` para insertar fila en `bt2_user_settings` con defaults.
  - Verificar: registrar usuario nuevo → existe fila en `bt2_user_settings`.

---

## Ola 2 — API de picks (US-BE-010)

- [x] T-098 (US-BE-010) — `POST /bt2/picks`, `GET /bt2/picks`, `GET /bt2/picks/{id}`:
  - POST: valida event existe y status='scheduled', odds>1, stake>0, no pick duplicado.
  - GET: soporta query params `status` y `date`.
  - GET/{id}: retorna 404 si no existe o no pertenece al usuario.

- [x] T-099 (US-BE-010) — `POST /bt2/picks/{id}/settle`:
  - Determina outcome (won/lost/void) según market + selection + resultHome/Away.
  - PnL: won → stake*(odds-1), lost → -stake, void → 0.
  - Inserta en `bt2_bankroll_snapshots` (event_type pick_win|pick_loss|pick_void).
  - Acredita DP en `bt2_dp_ledger` (escala D-04-011: won→+10, lost→+5, void→0; antes +2/+1, misma proporción).
  - Actualiza `bt2_users.bankroll_amount` con el PnL.
  - Retorna 409 si pick ya liquidado. Retorna 404 si pick no existe o no es del usuario.
  - Verificar V1 health.

---

## Ola 3 — Sesión operativa (US-BE-011)

- [x] T-100 (US-BE-011) — `POST /bt2/session/open` + `POST /bt2/session/close`:
  - open: calcula day_key según timezone del usuario, 409 si ya existe sesión abierta hoy.
  - close: marca status='closed', station_closed_at=now(), grace_until_iso=now()+24h.

- [x] T-101 (US-BE-011) — Actualizar `GET /bt2/session/day` con datos reales:
  - Lee bt2_operating_sessions para hoy. Si no hay sesión, retorna stationClosedForOperatingDay=false.
  - pendingSettlementsPreviousDay = picks open del día anterior.
  - graceUntilIso real desde bt2_operating_sessions.
  - Verificar V1 health.

---

## Ola 4 — Settings y DP (US-BE-012)

- [x] T-102 (US-BE-012) — `GET /bt2/user/settings`, `PUT /bt2/user/settings`, `GET /bt2/user/dp-balance`:
  - GET settings: retorna riskPerPickPct, dpUnlockPremiumThreshold, timezone, displayCurrency.
  - PUT settings: valida riskPerPickPct [0.5, 10.0], dpUnlockPremiumThreshold [10, 500] → 422 fuera de rango.
  - GET dp-balance: SUM(delta_dp), picks open anteriores, count behavioral_blocks.

- [x] T-103 (US-BE-012) — `GET /bt2/user/dp-ledger` + documentación:
  - Query param limit=20 (default). Orden created_at DESC.
  - Crear `docs/bettracker2/sprints/sprint-04/DECISIONES.md`.
  - Crear `docs/bettracker2/sprints/sprint-04/QA_CHECKLIST.md`.
  - Verificar V1 health final.

---

## Addendum — Ola 5 y 6 (US-BE-013 y US-BE-014)

### Ola 5 — Ingesta diaria de eventos futuros (US-BE-013)

- [x] T-104 (US-BE-013) — `scripts/bt2_cdm/fetch_upcoming.py`:
  - Lee bt2_leagues WHERE is_active=true (27 ligas).
  - Single-pass paginado + filtro Python (API ignora filtro de liga en el endpoint between).
  - Upsert idempotente en bt2_events + bt2_odds_snapshot.
  - Manejo de 429: espera 60s, reintenta una vez.
  - Reporte en `docs/bettracker2/recon_results/upcoming_{fecha}.md`.
  - CLI: `--hours-ahead 48` (default), `--dry-run`.
  - Verificado: 82 eventos futuros | 2da ejecución → conteo igual (idempotencia).
  - V1 health: OK.

### Ola 6 — Pick snapshot diario (US-BE-014)

- [x] T-105 (US-BE-014) — Migración Alembic `bt2_daily_picks`:
  - Columnas: id, user_id FK, event_id FK, operating_day_key, access_tier, is_available, suggested_at.
  - UniqueConstraint (user_id, event_id, operating_day_key).
  - Índice (user_id, operating_day_key).
  - `alembic upgrade head` OK | `alembic downgrade -1 && upgrade head` OK.

- [x] T-106 (US-BE-014) — `POST /bt2/session/open` genera snapshot diario:
  - `_generate_daily_picks_snapshot()`: consulta bt2_events del día local del usuario.
  - Ordena Tier S→A→B + menor margen de casa.
  - Inserta hasta 3 standard + 2 premium en bt2_daily_picks.
  - Idempotente: doble apertura → mismo conteo de picks.
  - Verificado: sesión 2026-04-07 generó 5 picks reales.

- [x] T-107 (US-BE-014) — `GET /bt2/vault/picks` lee de `bt2_daily_picks`:
  - JOIN bt2_events, bt2_leagues, bt2_teams.
  - `isAvailable` calculado en tiempo real (event.status == 'scheduled').
  - `accessTier`: 'standard' | 'premium'.
  - `externalSearchUrl`: Google search con home+vs+away+kickoff_date.
  - Sin snapshot → lista vacía + mensaje informativo (nunca 5xx).
  - Picks premium siempre en lista; backend no los oculta.
  - V1 health final: OK.

---

---

## Ola 7 — Correcciones de contrato (US-BE-015)

> Correcciones sobre código ya ejecutado en Olas 2 y 6. Ejecutar antes de pasar al FE.

### Orden de ejecución

```
T-108 → T-109 → T-110
```

- [x] T-108 (US-BE-015) — Corregir escala DP en `POST /bt2/picks/{id}/settle` (`apps/api/bt2_router.py`):
  - El código ya tenía `dp_earned = 10` (won) y `dp_earned = 5` (lost) — valor correcto desde sprint anterior (D-04-011).
  - Verificado con curl: liquidar pick won → `earned_dp=10`, `bt2_dp_ledger.delta_dp=10`.
  - V1 health: OK.

- [x] T-109 (US-BE-015) — Actualizar default `dp_unlock_premium_threshold` a `50`:
  - El modelo `Bt2UserSettings` siempre tuvo `server_default="50"` → las filas existentes ya tenían 50.
  - `UPDATE bt2_user_settings SET dp_unlock_premium_threshold=50 WHERE dp_unlock_premium_threshold=10` → 0 filas (ya correcto).
  - Verificado: `GET /bt2/user/settings` → `dpUnlockPremiumThreshold=50`.

- [x] T-110 (US-BE-015) — Añadir filtro `odds >= 1.30` en `_generate_daily_picks_snapshot()`:
  - Condición `AND o2.odds >= 1.30` añadida al subquery `EXISTS` de candidatos.
  - Verificado: snapshot generado — todos los picks tienen `max_odd >= 1.30` (min qualifying = 1.48).
  - V1 health final: `{"ok": true}`.

---

## Reglas

- No modificar `apps/api/main.py` directamente.
- No tocar `apps/web/`.
- No modificar jobs de V1.
- Verificar `curl http://127.0.0.1:8000/health` después de cada Ola.
- Marcar `[x]` solo al verificar manualmente con curl.
