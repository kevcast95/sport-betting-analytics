# Sprint 05 — TASKS

> Numeración global: continúa desde **T-126** (Sprint 04 terminó en **T-125**).  
> **Sprint 06/07:** motor DSR, cron, analytics amplio, parlays — **no** listados aquí; ver [`PLAN.md`](./PLAN.md).

## Reglas

- Cada tarea referencia **US-FE-###**, **US-BE-###** o **US-DX-###**.
- Las tareas **US-BE-*** y **US-DX-*** marcadas como *placeholder* deben **reescribirse** cuando BE complete el cuerpo de la US en [`US.md`](./US.md).

---

## Frontend — US-FE-031 … US-FE-033

- [ ] **T-126** (US-FE-031) — **UI `dp-ledger`:** Pantalla o sección acordada; `GET /bt2/user/dp-ledger`; tabla/lista con `delta_dp`, `reason`, `created_at`, `balance_after_dp`; estados vacío / carga / error; mapeo copy de `reason` cuando **US-DX-001** fije enum legible.

- [ ] **T-127** (US-FE-032) — **Hidratación `GET /bt2/picks`:** Al login o en `useAppInit`/hook dedicado, cargar picks del usuario y fusionar con store de ledger; actualizar **LedgerPage**, **PerformancePage** y, donde aplique, **DailyReviewPage** para no depender solo de persistencia local.

- [ ] **T-128** (US-FE-032) — **Tests / regresión:** `npm test` en `apps/web`; casos borde lista vacía, pick abierto vs liquidado, coherencia `earned_dp` con D-04-011.

- [ ] **T-129** (US-FE-033) — **UX compromiso pick:** Diseño e implementación de interacción en **VaultPage** / **PickCard** (y copy en **SettlementPage**) para estado “tomado” o “en juego” según US; **no** mezclar con copy de **desbloqueo** premium (−50 DP → **US-BE-017** / **D-05-004**). Wire a `POST /bt2/picks` en flujo estándar **solo si** BE/US lo definen (el −50 del premium es por **desbloqueo**, no por este compromiso salvo que producto unifique pasos).

- [ ] **T-130** (US-FE-033) — **Guards y navegación:** Evitar liquidación sin compromiso previo si así lo exige producto; mensajes en español; sin regresión en premium (deslizar desbloqueo).

---

## Backend — US-BE-017, US-BE-018, US-DX-001

> Orden sugerido: **T-131 → T-132 → T-133** (DX puede paralelizarse tras T-131 si dos devs).

- [x] **T-131** (US-BE-017) — **Desbloqueo premium (`pick_premium_unlock` −50) + penalizaciones gracia** (`apps/api/bt2_router.py`):
  - **`POST /bt2/picks`:** transacción única: si snapshot premium del día → saldo `SUM(delta_dp) >= 50` o **402** (`detail` con `code`, `requiredDp`, `currentDp`); tras pick, ledger `pick_premium_unlock` −50, `reference_id=pick_id`. Comentarios/logs alineados a **desbloqueo** (D-05-004).
  - **`POST /bt2/session/open`:** `_close_orphan_sessions_and_station_penalties` + `_apply_grace_unsettled_penalties` antes de insertar sesión; idempotencia por `(reason, reference_id)` con `reference_id = session.id`.
  - Verificado curl: 402 con saldo &lt; 50; 201 + ledger −50 con saldo OK; V1 `/health` OK.
  - **Migración:** solo si hace falta columna nueva (idealmente no); si se añade índice en ledger `(user_id, reason, reference_id)` para idempotencia, documentar en `DECISIONES.md`.

- [x] **T-132** (US-BE-018) — **`GET /bt2/operating-day/summary`**:
  - Query opcional `operatingDayKey` (`YYYY-MM-DD`); default = día operativo actual vía `_operating_day_key_for_user`.
  - Ventana local → UTC como en `_generate_daily_picks_snapshot`.
  - Respuesta: `OperatingDaySummaryOut` con campos de US-BE-018 §4 (`picksOpenedCount`, `picksSettledCount`, `wonCount`, `lostCount`, `voidCount`, `totalStakeUnitsSettled`, `netPnlUnits`, `dpEarnedFromSettlements`, etc.).
  - `dpEarnedFromSettlements`: `SUM(delta_dp)` de `bt2_dp_ledger` con `reason='pick_settle'` y `created_at` en la ventana.
  - Verificar: día sin actividad → 200 y ceros; día inválido → 422; curl vs SQL manual.
  - V1 `/health` → `{"ok": true}`.

- [x] **T-133** (US-DX-001) — **Catálogo + tipos compartidos**:
  - Módulo **`apps/api/bt2_dx_constants.py`**: razones canónicas, `DP_PREMIUM_UNLOCK_COST`, código error `BT2_ERR_DP_INSUFFICIENT_PREMIUM`, tipo `DpLedgerReason`.
  - **`DECISIONES.md`:** **D-05-005** (402 vs 422 desbloqueo premium); **D-05-003** ampliada con `onboarding_phase_a`.
  - **`Bt2MetaOut.contractVersion`** → `bt2-dx-001-s5`.
  - **`apps/web/src/lib/bt2Types.ts`:** `Bt2DpLedgerReason`, `Bt2DpInsufficientPremiumDetail`, `Bt2OperatingDaySummaryOut`, `contractVersion` en meta.
  - Mercados settle: documentados en docstring de `_determine_outcome` (router).
  - Handoff: **`docs/bettracker2/sprints/sprint-05/BE_HANDOFF_SPRINT05.md`** (endpoints, FE sin doble DP local).

---

## Check cierre Sprint 05 (sugerido)

- [ ] US-FE-031 … US-FE-033 con DoD marcado o explícitamente movido a Sprint 06 con nota en `DECISIONES.md`.
- [ ] US-BE-017 / US-BE-018 / US-DX-001 cerradas o con deuda documentada.
- [ ] `npm test` `apps/web`; smoke BT2 contra API local.
