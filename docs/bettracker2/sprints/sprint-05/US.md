# Sprint 05 — US

> **Convención:** FE continúa en **US-FE-031+** (Sprint 04 cerró en US-FE-030). BE continúa en **US-BE-017+** (Sprint 04 cerró en US-BE-016).  
> **Calendario motor:** DSR, cron CDM, analytics amplio → **Sprint 06**; parlays y diagnóstico longitudinal → **Sprint 07** — ver [`DECISIONES.md`](./DECISIONES.md) **D-05-001** y [`PLAN.md`](./PLAN.md).

## Estado del sprint

- Fecha inicio / fin: *(definir)*  
- Estado: **Planned**  
- **US-BE-017, US-BE-018, US-DX-001:** cuerpo completo redactado (BA/PM BE); tareas **T-131–T-133** en [`TASKS.md`](./TASKS.md).

## Resumen — US Frontend

| ID | Título | Notas |
|----|--------|--------|
| US-FE-031 | UI de movimientos DP (`GET /bt2/user/dp-ledger`) | Arrastra intención de **T-124** (Sprint 04). |
| US-FE-032 | Hidratar ledger y métricas V2 desde `GET /bt2/picks` | Libro mayor, rendimiento, cierre del día alineados a servidor. |
| US-FE-033 | Compromiso explícito con pick en bóveda y liquidación | Estados tomado/seleccionado; alinear con `POST /bt2/picks` en estándar si producto lo exige. |

## Resumen — US Backend / contrato

| ID | Título | Notas |
|----|--------|--------|
| US-BE-017 | Ledger DP: **desbloqueo** premium + penalizaciones de gracia en servidor | **−50 DP** al **desbloquear** señal **premium** del snapshot (`pick_premium_unlock`); penalizaciones D-04-011 tras gracia; idempotencia por `reference_id`. |
| US-BE-018 | Resumen del día operativo (`GET /bt2/operating-day/summary`) | Agregados por `operating_day_key` y TZ usuario; sustituye heurísticas locales en Daily Review. |
| US-DX-001 | Catálogo canónico: `reason` del ledger + mercados API + perfiles operador | Desbloquea copy FE en `dp-ledger` y validaciones; enum mercados **documentado** (normalización CDM dura → Sprint 06). |

---

## Frontend

### US-FE-031 — Lista de movimientos DP en UI (`dp-ledger`)

#### 1) Objetivo de negocio

Que el operador vea **trazabilidad** de sus Discipline Points (acreditaciones y cargos) desde el **servidor**, no solo el saldo agregado.

#### 2) Alcance *(refinar)*

- Incluye: vista acordada (p. ej. Perfil o Ajustes); `GET /bt2/user/dp-ledger`; estados carga / vacío / error; formato legible de `reason` (mapeo copy si hace falta tras **US-DX-001**).
- Excluye: editar movimientos; lógica de negocio nueva en servidor (va en **US-BE-017** u otras).

#### 3) Dependencias

- Contrato estable de entradas ledger (**US-DX-001** / OpenAPI actual).

#### 10) Definition of Done

- [ ] Criterios verificables acordados con BE tras cerrar **US-DX-001**.
- [ ] Tareas **T-126+** en [`TASKS.md`](./TASKS.md).

---

### US-FE-032 — Ledger y métricas V2 desde API (`GET /bt2/picks`)

#### 1) Objetivo de negocio

**Una sola fuente de verdad** para picks del usuario: abiertos, liquidados, PnL y DP por liquidación reflejados desde BD, con persistencia local solo como caché o transición.

#### 2) Alcance *(refinar)*

- Incluye: hidratar `useTradeStore` (o equivalente) al iniciar sesión y tras mutaciones; `LedgerPage`, `PerformancePage`, `DailyReviewPage` consumiendo datos derivados del servidor donde aplique; manejo de usuario sin picks.
- Excluye: motor DSR o cambios al snapshot diario CDM (**Sprint 06**).

#### 3) Dependencias

- Respuesta `GET /bt2/picks` con campos suficientes (`earned_dp`, fechas, estado); posible **US-BE-018** para agregados del día.

#### 10) Definition of Done

- [ ] Documentado en `TASKS.md`; smoke manual vs BD.

---

### US-FE-033 — Compromiso explícito con pick (bóveda + liquidación)

#### 1) Objetivo de negocio

Evitar que la bóveda sea solo “catálogo → liquidación” sin **marca operativa** de qué pick está en juego; alinear con protocolo de disciplina.

#### 2) Alcance *(refinar)*

- Incluye: interacción UI (p. ej. “Tomar señal” en estándar si producto exige paridad con premium); estados visibles; reglas con **POST /bt2/picks** según decisión conjunta.
- Excluye: parlays (**Sprint 07**).

#### 3) Dependencias

- **US-BE-017** cubre el **cargo −50 por desbloqueo premium**, no el compromiso estándar; si el flujo estándar debe registrar pick en servidor al “comprometer”, se define aparte (mismo o otro endpoint).

#### 10) Definition of Done

- [ ] Criterios Given/When/Then acordados con PM + BE; tareas en `TASKS.md`.

---

## Backend

### US-BE-017 — Ledger DP en **desbloqueo** premium y penalizaciones de gracia (servidor)

#### 1) Objetivo de negocio

Que **toda mutación de saldo DP** relevante para el protocolo conductual quede en `bt2_dp_ledger`, de modo que `GET /bt2/user/dp-balance` y `GET /bt2/user/dp-ledger` sean la única fuente de verdad y el FE deje de compensar con `incrementDisciplinePoints` en flujos que ya pasan por API.

#### 2) Alcance

- Incluye:
  - **Nomenclatura (ver D-05-004):** el **−50 DP** es por **desbloquear** la señal premium del snapshot (`reason = pick_premium_unlock`), no por el acto abstracto de “tomar el pick”. En MVP el desbloqueo puede ir en el mismo paso técnico que crea la fila en `bt2_picks`.
  - **`POST /bt2/picks`:** si el `event_id` del cuerpo coincide con una fila de `bt2_daily_picks` para el mismo `user_id` y `operating_day_key` actual del usuario con `access_tier = 'premium'`, entonces **antes** de confirmar el pick: validar que `SUM(delta_dp)` del usuario sea **≥ 50** (coste canónico **D-04-011** para `pick_premium_unlock`; ver **D-05-002** si se parametriza en settings en el futuro). Tras insertar la fila en `bt2_picks`, insertar en `bt2_dp_ledger`: `delta_dp = -50`, `reason = 'pick_premium_unlock'`, `reference_id = id del pick recién creado`, `balance_after_dp` coherente con `_get_dp_balance` + esta fila.
  - Si el evento **no** está en el snapshot del día como premium (p. ej. pick manual / otro día), **no** aplicar cargo; el pick sigue siendo válido si el resto de reglas lo permiten.
  - **`POST /bt2/session/open`:** tras crear la sesión del día y el snapshot, ejecutar rutina **`_apply_grace_penalties`** (nombre interno libre) **idempotente**:
    - **`penalty_unsettled_picks` (−25):** para cada fila en `bt2_operating_sessions` del usuario con `status = 'closed'` y `grace_until_iso < now()` (UTC) para la que **aún no** exista en `bt2_dp_ledger` una fila con `reason = 'penalty_unsettled_picks'` y `reference_id = id de esa sesión`: si en el momento de evaluar existe **al menos un** `bt2_picks` con `status = 'open'` para ese usuario cuya `opened_at` es **anterior o igual** a `station_closed_at` de esa sesión, insertar una fila −25 con `reference_id = session.id`.
    - **`penalty_station_unclosed` (−50):** si el usuario abre sesión el día `D` (`operating_day_key = D`) y existe una sesión **previa** (mismo usuario) con `operating_day_key < D` (orden lexicográfico de fecha ISO) y `status = 'open'` (nunca cerrada), entonces: (1) cerrar esa sesión huérfana (`status = 'closed'`, `station_closed_at = now()`, `grace_until_iso = now()+24h` o `now()` según **D-05-002**); (2) insertar **una sola vez** por sesión huérfana un ledger `penalty_station_unclosed` −50 con `reference_id = id de esa sesión`, si no existe ya esa combinación reason+reference_id.
  - Transacciones DB: pick + ledger premium en la misma transacción; penalizaciones en la misma transacción que el `commit` de `session/open` o sub-transacción clara.
- Excluye:
  - Cambiar reglas de settle (+10/+5/0) — ya cerradas en Sprint 04.
  - Jobs cron; la aplicación de penalizaciones es **síncrona** al `session/open` (o al primer request que el equipo acuerde documentar en **D-05-002**).
  - Parlays y costes −25/−50 de parlay — Sprint 07.

#### 3) Contexto técnico actual

- Módulos: `apps/api/bt2_router.py` (`bt2_create_pick`, `bt2_session_open`), helpers `_get_dp_ledger_sum`, `_get_dp_balance`, `_operating_day_key_for_user`, `_append_dp_ledger_move`, `_close_orphan_sessions_and_station_penalties`, `_apply_grace_unsettled_penalties`; constantes `apps/api/bt2_dx_constants.py` (US-DX-001).
- Tablas: `bt2_picks`, `bt2_daily_picks`, `bt2_dp_ledger`, `bt2_operating_sessions`.
- **`POST /bt2/picks`:** si el `event_id` está en `bt2_daily_picks` como **premium** para el `operating_day_key` del usuario, en la **misma transacción** que el `INSERT` en `bt2_picks` se inserta en `bt2_dp_ledger` el movimiento **`pick_premium_unlock`** (`delta_dp = -50`, `reference_id = pick_id`). Saldo insuficiente → **402** con `detail` estructurado (**D-05-005**); el FE **no** debe compensar ese −50 en local.
- **`POST /bt2/session/open`:** antes de crear la sesión del día, aplica penalizaciones idempotentes (sesión huérfana abierta de día anterior → `penalty_station_unclosed`; gracia vencida con picks abiertos al cierre → `penalty_unsettled_picks`). Ver **D-05-002** y código en router.

#### 4) Contrato de entrada/salida

- **`POST /bt2/picks`:** sin cambio de shape del body. Códigos HTTP:
  - **402:** saldo DP insuficiente para **desbloquear** pick premium del snapshot (antes del cargo; ver **D-05-005**).
  - **422:** validación de body o reglas de evento (no “fondos”).
- **`POST /bt2/session/open`:** sin cambio de `SessionOpenOut` en MVP; opcional **Improvement** documentado en TASKS: campo `penaltiesApplied: []` en respuesta.

#### 5) Reglas de dominio

- Regla 1: El coste de **desbloqueo** premium es **−50** DP por cada desbloqueo que califique (en MVP: cada `POST /bt2/picks` exitoso sobre fila snapshot premium que dispare `pick_premium_unlock`).
- Regla 2: Idempotencia penalizaciones: **única** fila ledger por par (`reason`, `reference_id`) donde `reference_id` es el `id` de `bt2_operating_sessions` afectada.
- Regla 3: `balance_after_dp` en cada insert debe ser el saldo **después** de aplicar ese movimiento (mismo patrón que settle).
- Regla 4: Si falla el insert del pick, **no** debe quedar movimiento de ledger premium huérfano.

#### 6) Criterios de aceptación (Given / When / Then)

1. Given usuario con saldo DP &lt; 50 y pick premium en snapshot, When `POST /bt2/picks` para ese `event_id` (flujo que incluye desbloqueo), Then **402** con mensaje claro (**D-05-005**) y **no** se crea pick.
2. Given saldo ≥ 50 y evento premium en snapshot, When `POST /bt2/picks` (desbloqueo + creación de pick), Then pick 201 y ledger con `pick_premium_unlock` −50 y `reference_id = pick_id`.
3. Given evento no está en `bt2_daily_picks` premium hoy, When `POST /bt2/picks`, Then no cargo −50 aunque el FE marque premium en UI (servidor manda).
4. Given sesión cerrada con gracia vencida y pick abierto anterior al cierre, When `POST /bt2/session/open` siguiente, Then una fila `penalty_unsettled_picks` −25 con `reference_id = session_id` y segunda ejecución no duplica.
5. Given sesión día anterior aún `open`, When `POST /bt2/session/open` hoy, Then sesión huérfana cerrada y a lo sumo un −50 `penalty_station_unclosed` por esa sesión.
6. Given JWT ausente en cualquier endpoint, Then 401 (regresión).

#### 7) No funcionales

- Misma latencia objetivo que otros `POST` BT2 (< 300 ms local).
- Logs estructurados opcionales para auditoría de penalizaciones.

#### 8) Riesgos y mitigación

- **Riesgo:** orden de días y TZ — usar siempre `_operating_day_key_for_user` y comparaciones en UTC para `grace_until_iso`. **Mitigación:** pruebas manuales con TZ distinta a Bogotá.
- **Riesgo:** doble penalización si `session/open` se reintenta — **Mitigación:** comprobar ledger antes de insertar.

#### 9) Plan de pruebas

- Curl / script: escenarios §6; verificar `GET /bt2/user/dp-balance` y `dp-ledger` tras cada acción.
- `GET /health` V1 → `{"ok": true}`.

#### 10) Definition of Done

- [x] T-131 (US-BE-017) completada en [`TASKS.md`](./TASKS.md).
- [x] Entrada **D-05-002** en [`DECISIONES.md`](./DECISIONES.md) alineada al cierre de sesión huérfana implementado.

---

### US-BE-018 — Resumen del día operativo para UI

#### 1) Objetivo de negocio

Exponer **un agregado oficial por día operativo** (PnL, conteos, stake, DP ganado por liquidaciones ese día) para que **Daily Review**, **Performance** y **Ledger** no dependan de heurísticas solo locales.

#### 2) Alcance

- Incluye:
  - Nuevo endpoint **`GET /bt2/operating-day/summary`** protegido (JWT).
  - Query opcional **`operatingDayKey`** (`YYYY-MM-DD`). Si se omite, usar el día operativo actual del usuario (`_operating_day_key_for_user`).
  - Cálculo en **zona horaria del usuario** (`bt2_user_settings.timezone`): ventana `[day_start_utc, day_end_utc)` igual que en `_generate_daily_picks_snapshot`.
  - Campos de salida (camelCase en JSON):
    - `operatingDayKey`, `userTimeZone`
    - `picksOpenedCount` — picks con `opened_at` en la ventana
    - `picksSettledCount` — picks con `settled_at` en la ventana
    - `wonCount`, `lostCount`, `voidCount` — entre los liquidados en la ventana
    - `totalStakeUnitsSettled` — suma `stake_units` de picks liquidados en la ventana
    - `netPnlUnits` — suma `pnl_units` de esos picks
    - `dpEarnedFromSettlements` — suma `delta_dp` de `bt2_dp_ledger` donde `reason = 'pick_settle'` y `created_at` en la ventana (alineado a liquidaciones registradas ese día)
- Excluye:
  - ROI % derivado en servidor (el FE puede calcular `netPnl / stake` si lo necesita).
  - Agregados multi-día o series temporales — Sprint 06 analytics si aplica.
  - Incluir movimientos DP que no sean `pick_settle` en `dpEarnedFromSettlements`.

#### 3) Contexto técnico

- Módulos: `apps/api/bt2_router.py`, `apps/api/bt2_schemas.py` (o modelos Pydantic inline en router si es el patrón actual).
- Reutilizar lógica de conversión TZ ya usada en snapshot diario.

#### 4) Contrato de salida (ejemplo)

```json
{
  "operatingDayKey": "2026-04-10",
  "userTimeZone": "America/Bogota",
  "picksOpenedCount": 2,
  "picksSettledCount": 2,
  "wonCount": 1,
  "lostCount": 1,
  "voidCount": 0,
  "totalStakeUnitsSettled": 4.0,
  "netPnlUnits": 0.5,
  "dpEarnedFromSettlements": 15
}
```

#### 5) Reglas de dominio

- Regla 1: Si no hay actividad, contadores en 0 y `netPnlUnits` 0.0 — **200**, no 404.
- Regla 2: `operatingDayKey` mal formateado → **422**.

#### 6) Criterios de aceptación

1. Given usuario autenticado, When `GET /bt2/operating-day/summary` sin query, Then 200 y clave = día actual en su TZ.
2. Given `operatingDayKey=2026-01-15` con picks liquidados ese día local, When GET, Then contadores y sumas coinciden con consultas SQL manuales de verificación.
3. Given `operatingDayKey` inválido, When GET, Then 422.

#### 7) No funcionales

- Respuesta < 300 ms en local con volumen MVP.

#### 8) Definition of Done

- [ ] T-132 (US-BE-018) en [`TASKS.md`](./TASKS.md).
- [ ] Documentado en OpenAPI (`/docs`) al menos con descripción de campos.

---

## Contratos

### US-DX-001 — Catálogo canónico: ledger `reason`, mercados API, perfiles operador

#### 1) Objetivo

Un único **catálogo versionable** de strings que cruzan BE y FE: razones del ledger, valores de mercado aceptados en contratos de pick, y perfiles de operador expuestos en diagnóstico — para copy en español, tipos TS y validaciones Pydantic alineados.

#### 2) Alcance

- Incluye:
  - **Razones `bt2_dp_ledger.reason`:** lista cerrada documentada, alineada a **D-04-011** y extensiones Sprint 05:
    - `pick_settle`, `pick_premium_unlock`, `onboarding_welcome`, `penalty_station_unclosed`, `penalty_unsettled_picks`, `parlay_activation_2l`, `parlay_activation_3l` (últimas dos reservadas Sprint 07; documentar como *reserved*).
  - Para cada razón: **`reasonLabelEs`** sugerido para el FE (tabla en este documento o en `DECISIONES.md` **D-05-003**).
  - **Mercados (`bt2_picks.market` / CDM):** documentar conjunto **mínimo** soportado en settle (`_determine_outcome`) hoy: p. ej. variantes de Match Winner / 1X2 / Over Under — como **strings canónicos recomendados** y sinónimos aceptados (paso previo a enum único en BD, **Sprint 06**).
  - **`operatorProfile`:** ya listado en `OPERATOR_PROFILE_VALUES` en `bt2_schemas.py` — referenciar en US-DX y en tabla `reasonLabelEs` no aplica; es campo aparte.
  - Actualizar **`apps/web/src/lib/bt2Types.ts`** (y exports usados por `api.ts`) con tipos literales o uniones que reflejen el catálogo.
  - Bump opcional de `contractVersion` en `GET /bt2/meta` si el equipo acuerda señalizar DX-001.
- Excluye:
  - Migración que reescriba mercados en `bt2_events`/`bt2_odds_snapshot` — Sprint 06.
  - Generación automática de cliente OpenAPI desde repo (nice-to-have).

#### 3) Reglas

- Ningún valor nuevo de `reason` en código sin actualizar este catálogo y TS.
- El FE usa `reason` como clave estable; `reasonLabelEs` solo para UI.

#### 4) Criterios de aceptación

1. Given documento DX publicado en repo (esta US + DECISIONES), When FE mapea `dp-ledger`, Then no hay razones sin fila de copy o marcadas `reserved`.
2. Given `bt2Types.ts`, When compila el proyecto web, Then no hay desalineación con respuestas reales de `/user/dp-ledger` en smoke manual.

#### 5) Definition of Done

- [ ] T-133 (US-DX-001) en [`TASKS.md`](./TASKS.md).
- [ ] Entrada **D-05-003** en [`DECISIONES.md`](./DECISIONES.md) con tabla `reason` → `reasonLabelEs`.

---

*El ejecutor BE no debe marcar DoD de US-BE-017/018 sin pruebas curl y V1 `/health` OK.*
