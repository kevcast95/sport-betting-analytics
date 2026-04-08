# Sprint 05 — TASKS

> **Tareas abiertas ordenadas para ejecutar:** [`PENDIENTES_CIERRE.md`](./PENDIENTES_CIERRE.md) (T-145, T-147, T-149, T-151 + checklist final).

> Numeración global: continúa desde **T-126** (Sprint 04 terminó en **T-125**).  
> **Sprint 06/07:** motor DSR, cron, analytics — planificados en [`../sprint-06/`](../sprint-06/PLAN.md) (**T-153+**). Parlays / diagnóstico avanzado → **Sprint 07** (ver [`../sprint-07/PLAN.md`](../sprint-07/PLAN.md) si existe).

## Reglas

- Cada tarea referencia **US-FE-###**, **US-BE-###** o **US-DX-###**.
- Las tareas **US-BE-*** y **US-DX-*** deben alinearse al cuerpo de la US en [`US.md`](./US.md) (paquete D-05-012 … D-05-016: contratos cerrados en documentación; implementación código pendiente según checkboxes).

---

## Frontend — US-FE-031 … US-FE-033

- [x] **T-126** (US-FE-031) — **UI `dp-ledger`:** Pantalla o sección acordada; `GET /bt2/user/dp-ledger`; tabla/lista con `delta_dp`, `reason`, `created_at`, `balance_after_dp`; estados vacío / carga / error; mapeo copy de `reason` cuando **US-DX-001** fije enum legible.

- [x] **T-127** (US-FE-032) — **Hidratación `GET /bt2/picks`:** Al login o en `useAppInit`/hook dedicado, cargar picks del usuario y fusionar con store de ledger; actualizar **LedgerPage**, **PerformancePage** y, donde aplique, **DailyReviewPage** para no depender solo de persistencia local.

- [x] **T-128** (US-FE-032) — **Tests / regresión:** `npm test` en `apps/web`; casos borde lista vacía, pick abierto vs liquidado, coherencia `earned_dp` con D-04-011 *(post **T-142**: alinear a **D-05-012**)*.

- [x] **T-129** (US-FE-033) — **UX compromiso pick:** Diseño e implementación de interacción en **VaultPage** / **PickCard** (y copy en **SettlementPage**) para estado “tomado” o “en juego” según US; **no** mezclar con copy de **desbloqueo** premium (−50 DP → **US-BE-017** / **D-05-004**). Wire a `POST /bt2/picks` en flujo estándar **solo si** BE/US lo definen (el −50 del premium es por **desbloqueo**, no por este compromiso salvo que producto unifique pasos).

- [x] **T-130** (US-FE-033) — **Guards y navegación:** Evitar liquidación sin compromiso previo si así lo exige producto; mensajes en español; sin regresión en premium (deslizar desbloqueo).

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
  - **`Bt2MetaOut.contractVersion`** → `bt2-dx-001-s5` → **`s5.1`** (T-141) → **`s5.2`** (T-144 / economía + PickOut).
  - **`apps/web/src/lib/bt2Types.ts`:** `Bt2DpLedgerReason`, `Bt2DpInsufficientPremiumDetail`, `Bt2OperatingDaySummaryOut`, `contractVersion` en meta.
  - Mercados settle: documentados en docstring de `_determine_outcome` (router).
  - Handoff: **`docs/bettracker2/sprints/sprint-05/BE_HANDOFF_SPRINT05.md`** (endpoints, FE sin doble DP local).

- [x] **T-141** (US-BE-019) — **`GET /bt2/vault/picks` — hora y estado del evento:**
  - Añadir a **`Bt2VaultPickOut`** (`bt2_schemas.py`): `kickoffUtc: str` (ISO 8601 UTC, alias JSON `kickoffUtc`), `eventStatus: str` (alias `eventStatus`, valor crudo `bt2_events.status`).
  - En **`bt2_vault_picks`**, mapear desde filas existentes (`kickoff_utc` → ISO string; `event_status` → string).
  - Si `kickoff_utc` es `NULL`, enviar `kickoffUtc: ""` y documentar.
  - Verificar curl: respuesta incluye ambos campos; coherencia `isAvailable` con `eventStatus == 'scheduled'`.
  - Actualizar **`bt2Types.ts`** (`VaultPickCdm` / `Bt2VaultPickOut`).
  - V1 `/health` → `{"ok": true}`. `contractVersion` → **`bt2-dx-001-s5.1`** (campos bóveda).

---

## Frontend — US-FE-034 (integridad datos V2)

> Decisiones: **D-05-006** a **D-05-010** en [`DECISIONES.md`](./DECISIONES.md). Gap contrato bóveda: **US-BE-019** en [`US.md`](./US.md).

- [x] **T-134** (US-FE-034) — **`SanctuaryPage.tsx` patrimonio secundario:** Quitar literales +14.2% / −4.2%; implementar cálculo desde fuentes acordadas (**D-05-006**) o **“—”** / 0% + microcopy “sin historial”; comentario en código con umbral usado.

- [x] **T-135** (US-FE-034) — **`SanctuaryPage.tsx` misiones + estado:** Eliminar `DAILY_MISSIONS_PROGRESS_PCT` y checklist simulado; aplicar **D-05-007** (barra 0 / copy “en definición” u ocultar bloque); tarjeta “Estado…” condicionada a diagnóstico/sesión o copy neutral.

- [x] **T-136** (US-FE-034) — **`ProfilePage.tsx` posición global:** Eliminar `rankTopPct = 100 - dp/50`; sustituir por **D-05-008** (— o “no disponible en MVP”).

- [x] **T-137** (US-FE-034) — **Bóveda disponibilidad:** En `PickCard` / `VaultPage`, si `isAvailable === false`, UI apagada + sin tomar; copy opcional “No disponible” (**D-05-009**). Verificar respuesta real del API.

- [x] **T-138** (US-FE-034) — **Bóveda preview + CTAs + badge:** Preview `traduccionHumana` sustituyendo placeholder único; botón **Detalle** (modal/ruta); **Tomar/Seleccionar**; tras tomado → **Liquidar** + badge “En juego” (**D-05-009**). Coherencia con premium/desbloqueo (**D-05-004**).

- [x] **T-139** (US-FE-034) — **Hora evento + tests:** Fallback / `titulo` hasta merge **T-141**; con **`kickoffUtc`** + **`eventStatus`** en API, formatear hora local en TZ usuario (card + fase revisión **D-05-010**). `npm test` + smoke.

- [x] **T-140** (US-FE-034) — **D-05-010 bóveda / settlement:** (1) **Detalle** + **Tomar pick** en **una fila** en `PickCard` (mismo ancho visual, sin stack vertical en móvil estándar). (2) **Detalle** → `NavLink`/`navigate` a **misma ruta settlement** que liquidación, con **fase=revisión** (query `?phase=review` o state): mostrar hora inicio, mercado, selección, cuota, `traduccionHumana` completa; CTA **Tomar** en esa pantalla. (3) Pick **tomado** → misma ruta en fase **liquidación** (comportamiento actual). (4) **Filtro temporal:** si evento **terminado** o `isAvailable === false`, card apagada; si **ya inició** y política lo exige, bloquear o advertir **Tomar** (comentar regla en código). (5) Coordinar con **US-BE-019** para campos O-U / corners si el CDM los expone. `npm test` + smoke.

- [x] **T-169** (US-FE-034) — **D-05-019 bóveda — hora + flags + anti-stale:** (1) **Preview:** mostrar **hora local** desde **`kickoffUtc`** cuando no sea `""`. (2) **Etiquetas:** rótulo visible según **`eventStatus`** y **`isAvailable`** (*Finalizado* / *En juego* / *No disponible* / *Programado* — copy PO) además de opacidad. (3) **`VaultPage` / `useVaultStore`:** si cambia **día operativo** del usuario respecto a **`operatingDayKey`** guardado en última respuesta (o `picksLoadStatus === 'loaded'` con datos de ayer), **forzar** `loadApiPicks()` (reset `idle` o `vaultFetchKey`); documentar en comentario. (4) Opcional: badge **Liquidado** cuando el vault pick esté en ledger/settled. Smoke: DevTools muestra **nuevo** GET al abrir bóveda tras cambio de día.

---

## Economía DP — liquidación (+10 gestión) — **D-05-012**

> **US:** **US-FE-035**, **US-BE-020** en [`US.md`](./US.md). **Decisión:** [`DECISIONES.md`](./DECISIONES.md) **D-05-012** (enmienda **D-04-011**). **Paridad BE:** ver matriz y §11 en [`US.md`](./US.md); handoff BA BE: [`HANDOFF_BA_PM_BACKEND_SPRINT05.md`](./HANDOFF_BA_PM_BACKEND_SPRINT05.md).

| Tarea FE | Par BE (rectificar BA Backend) |
|----------|--------------------------------|
| **T-142** | **T-143** + **T-144** (DX) |

- [x] **T-142** (US-FE-035) — **Copy + cliente FE:** Alinear toasts **SettlementPage**, tours (**EconomyTourModal** u otros), strings “+10 / +5” y mocks/tests (`ledgerAnalytics`, `useTradeStore` / `finalizeSettlement` local si aplica, `pickSettlementMock`, `SETTLEMENT_DP_REWARD_*`) con **+10** como recompensa de gestión al liquidar (independiente de won/lost/void en servidor). No cambiar reglas de PnL ni penalizaciones. `npm test` en `apps/web`.

- [x] **T-143** (US-BE-020) — **`POST /bt2/picks/{id}/settle`:** En `bt2_router.py`, `dp_earned = 10` para **`won`**, **`lost`** y **`void`**; insertar `bt2_dp_ledger` `pick_settle` +10 en los tres casos; comentarios que citaban D-04-011 +10/+5/+0. Tests o script curl: settle lost → `earned_dp=10`; settle void → `earned_dp=10`; idempotencia 409 sin doble fila. Verificar `GET /bt2/operating-day/summary` (`dpEarnedFromSettlements`) con escenarios de pérdida/void.

- [x] **T-144** (US-DX-001 refinamiento + regresión) — **DX y cierre documental:** (1) **D-05-003:** `pick_settle` y **`session_close_discipline`** (`reasonLabelEs`). (2) **`bt2_dx_constants.py`**, **`DpLedgerReason`**, **`bt2Types.ts`**, **`dpLedgerLabels.ts`**. (3) Bump **`contractVersion`** a **`bt2-dx-001-s5.2`** al cerrar **T-152** / **T-146** (coordinar un solo bump). (4) Tabla **D-04-011** en `sprint-04/DECISIONES.md` (+10/+10/+10). (5) QA_CHECKLIST sprint 05: criterios +5 en lost → +10.

---

## UX img / cierre día / liquidación dual / bankroll — **D-05-013 … D-05-016**

> **US:** **US-FE-036 … US-FE-039**, **US-BE-021 … US-BE-023** + **US-BE-018 §9** en [`US.md`](./US.md). **Proceso:** **D-05-017**; [`HANDOFF_BA_PM_BACKEND_SPRINT05.md`](./HANDOFF_BA_PM_BACKEND_SPRINT05.md).

| Tarea FE | Par BE |
|----------|--------|
| **T-145** | **T-152** (**US-BE-018 §9**) |
| **T-147** | **T-146** |
| **T-149** | **T-148** |
| **T-151** | **T-150** |

- [x] **T-145** (US-FE-036) — **Detalle en card → settlement (pick liquidado):** En **`PickCard`**, el CTA **Detalle** debe ir a la **misma ruta settlement** (`/v2/settlement/:id` o canónica) **aunque** el pick esté liquidado. En **`SettlementPage`**, modo **solo lectura** (ficha completa); **no** usar como comportamiento por defecto **`Navigate` a `/v2/vault`** en lugar de mostrar la ficha (**D-05-013**). **Ledger** y deep links alineados. **Depende de contrato T-152** para datos servidor completos. `npm test` + smoke.

- [x] **T-152** (**US-BE-018 §9**) — **PickOut ampliado + GET picks:** Implementar campos y joins de [`US.md`](./US.md) **US-BE-018 §9** en `GET /bt2/picks` y `GET /bt2/picks/{pick_id}`: `resultHome`/`resultAway`, `earnedDp` (agregado desde ledger `pick_settle` por `pick_id`), `kickoffUtc`, `eventStatus`, `settlementSource` (valor **`user`** hasta **T-148**; si **T-148** va en el mismo PR, persistir columna `settlement_source`). **404** ACL sin filtrar existencia a otros usuarios. Tests/curl. Actualizar OpenAPI / **`bt2Types.ts`**; bump **`contractVersion`** → **`bt2-dx-001-s5.2`** coordinado con **T-144**. Coordinar con **T-145**.

- [x] **T-146** (US-BE-021) — **Recompensa DP cierre sesión:** En `POST /bt2/session/close`, tras cerrar sesión: insertar **`bt2_dp_ledger`** con `reason=session_close_discipline`, `delta_dp=+N`, **`N=20`** por defecto (**D-05-018** / constante `SESSION_CLOSE_DISCIPLINE_REWARD_DP`), `reference_id=session.id`, idempotencia si ya existe fila. Ampliar **`SessionCloseOut`**: `earnedDpSessionClose`, `dpBalanceAfter`. Extender **`GET /bt2/operating-day/summary`** con **`dpEarnedFromSessionClose`** (suma `session_close_discipline` en ventana). **No** bonificar en cierre huérfano vía `session/open` salvo producto lo pida (**US-BE-021** §5). Tests/curl. **US-DX-001** / **D-05-003** / `bt2_dx_constants.py` / TS.

- [x] **T-147** (US-FE-037) — **Copy/UI cierre día:** Toasts, Daily Review y textos educativos que comuniquen la **recompensa por cerrar** además de evitar **−50**; consumir API **T-146** sin hardcode del valor N salvo constante compartida con BE. Revisión PO.

- [x] **T-148** (US-BE-022 **Fase A**) — **Columna `settlement_source` + exposición en PickOut:** Migración `bt2_picks.settlement_source NOT NULL DEFAULT 'user'`; en `POST .../settle` persistir `'user'`; asegurar **`settlementSource`** en respuesta pick (lista/detalle) según **US-BE-018 §9**. **Out of scope S5:** cron validador, PATCH override, razones ledger de ajuste (**US-BE-022** Fases B/C → Sprint 06).

- [x] **T-149** (US-FE-038) — **Liquidación dual (FE):** Consumo `settlementVerificationMode` desde meta; badges/copy modo; stubs UI para discrepancia cuando exista API (**T-148**). Sin inventar estados sin contrato.

- [x] **T-150** (US-BE-023 **Sprint 05**): **Normalización `market`/`selection` en `POST /bt2/picks`** hacia strings compatibles con `_determine_outcome`; **422** con mensaje claro si no hay mapeo. Documentar sinónimos en docstring. **Sin** reserva de stake al tomar en S5; bankroll sigue mutando solo en settle. Tests unitarios de normalización + smoke E2E mínimo.

- [x] **T-151** (US-FE-039) — **Bankroll emulado (FE):** Reconciliación UI, copy de error/ayuda si void por mercado; cuando **T-150** exponga reserva/comprometido, mostrar según contrato. `npm test` + smoke.

---

## Check cierre Sprint 05 (sugerido)

- [x] US-FE-031 … US-FE-033 con DoD marcado o explícitamente movido a Sprint 06 con nota en `DECISIONES.md`.
- [x] **US-FE-034:** **T-140** (**D-05-010**) cerrada; T-134–T-138 cerradas; **T-139** con **`kickoffUtc`** / **`eventStatus`** (T-141).
- [x] US-BE-017 / US-BE-018 / US-DX-001 / **US-BE-019 (T-141)** cerradas o con deuda documentada.
- [x] `npm test` `apps/web`; smoke BT2 contra API local.
- [x] **D-05-012 … D-05-019:** **T-142–T-152** y **T-169** cerradas en código; contratos en [`US.md`](./US.md). [`BE_HANDOFF_SPRINT05.md`](./BE_HANDOFF_SPRINT05.md) alineado al paquete **s5.2**.

---

*Última actualización: 2026-04-08 — **Sprint 05 cerrado formalmente en documentación** (checklist completo).*
