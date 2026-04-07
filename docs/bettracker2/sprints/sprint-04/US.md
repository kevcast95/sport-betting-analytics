# Sprint 04 — US (fuente de verdad)

> **Sprint híbrido:** incluye **US-BE** (persistencia, API conductual, settle, etc.) y **US-FE** (integración cliente), más **US-DX** si se versionan contratos compartidos. **Todas las US del sprint viven en este archivo** (convención del proyecto).  
> Numeración **global** por capa: FE continúa en **US-FE-025+** (Sprint 01 cerró en US-FE-024); BE continúa tras **US-BE-008** del Sprint 03 (**US-BE-009+** aquí).  
> Contexto complementario: [`../../HANDOFF_BA_PM_FRONTEND_SPRINT04.md`](../../HANDOFF_BA_PM_FRONTEND_SPRINT04.md), [`../../agent_roles/back_end_agent.md`](../../agent_roles/back_end_agent.md), pie de [`../sprint-03/US.md`](../sprint-03/US.md).

## Estado del sprint

- Fecha inicio: (definir)
- Fecha fin: (definir)
- Owner: (definir)
- Estado: Planned / In Progress / Done

## Resumen — US Frontend

| ID | Título |
|----|--------|
| US-FE-025 | Desacoplar stores de mocks: bóveda y ledger/picks → API real |
| US-FE-026 | Auth real: login, registro y JWT (`useUserStore`) |
| US-FE-027 | Bankroll y sesión conductual persistentes vía API |
| US-FE-028 | Liquidación con resultados reales y bankroll en BD |
| US-FE-029 | Lenguaje claro y glosario; marco para sizing futuro |

## Resumen — US Backend *(redactar en este mismo archivo)*

Sprint 03 entregó **US-BE-005 … US-BE-008** (CDM, auth JWT, endpoints reales stub→BD, job candidatos). Sprint 04 BE cubre típicamente: tablas conductuales (`bt2_picks`, `bt2_operating_sessions`, snapshots, DP ledger, etc.), **`POST` de sesión / picks / settle / close** (ver handoff §4), resultados desde `bt2_events`, e idempotencia de liquidación. Cuando BA/PM backend las numeré, deben aparecer como **### US-BE-009 — …** (y siguientes) **debajo de la sección Backend**, no solo en el handoff.

| ID | Título *(placeholder hasta redacción)* |
|----|--------|
| US-BE-009+ | *(A definir: migraciones, routers, reglas de dominio, tests API)* |

---

## Backend

> Orden de ejecución obligatorio: US-BE-009 → US-BE-010 → US-BE-011 → US-BE-012.
> US-BE-009 es bloqueante de todo lo demás. US-BE-010 desbloquea US-FE-025 y US-FE-028.

---

### US-BE-009 — Schema del dominio conductual (Alembic + modelos)

#### 1) Objetivo de negocio

Crear las tablas de persistencia que hacen al usuario el centro del sistema: sus picks, su sesión diaria, su bankroll histórico, sus Discipline Points y su configuración. Sin este schema, ningún endpoint conductual puede existir.

#### 2) Alcance

- Incluye:
  - Migración Alembic con 6 tablas nuevas:
    - `bt2_picks`: `id (serial PK)`, `user_id (uuid FK bt2_users)`, `event_id (int FK bt2_events)`, `market (varchar 50)`, `selection (varchar 50)`, `odds_taken (decimal 6,4)`, `stake_units (decimal 6,2)`, `status (varchar 20, default 'open')`, `opened_at (timestamptz default now())`, `settled_at (timestamptz, nullable)`, `result_home (int, nullable)`, `result_away (int, nullable)`, `pnl_units (decimal 8,2, nullable)`.
    - `bt2_operating_sessions`: `id (serial PK)`, `user_id (uuid FK)`, `operating_day_key (varchar 10)`, `station_opened_at (timestamptz default now())`, `station_closed_at (timestamptz, nullable)`, `status (varchar 20, default 'open')`, `grace_until_iso (timestamptz, nullable)`. Unique `(user_id, operating_day_key)`.
    - `bt2_bankroll_snapshots`: `id (serial PK)`, `user_id (uuid FK)`, `snapshot_date (date)`, `balance_units (decimal 10,2)`, `event_type (varchar 30)`, `reference_id (int, nullable)`, `created_at (timestamptz default now())`.
    - `bt2_dp_ledger`: `id (serial PK)`, `user_id (uuid FK)`, `delta_dp (int)`, `reason (varchar 50)`, `reference_id (int, nullable)`, `created_at (timestamptz default now())`, `balance_after_dp (int)`.
    - `bt2_behavioral_blocks`: `id (serial PK)`, `user_id (uuid FK)`, `trigger_type (varchar 30)`, `blocked_at (timestamptz default now())`, `context_json (jsonb)`, `estimated_loss_avoided_units (decimal 8,2, nullable)`.
    - `bt2_user_settings`: `user_id (uuid PK FK bt2_users)`, `risk_per_pick_pct (decimal 5,2, default 2.0)`, `dp_unlock_premium_threshold (int, default 50)`, `timezone (varchar 50, default 'America/Bogota')`, `display_currency (varchar 10, default 'COP')`.
  - Índices: `bt2_picks(user_id, status)`, `bt2_picks(event_id)`, `bt2_operating_sessions(user_id, status)`, `bt2_dp_ledger(user_id)`, `bt2_bankroll_snapshots(user_id, snapshot_date)`.
  - Modelos SQLAlchemy en `apps/api/bt2_models.py` para las 6 tablas.
- Excluye:
  - Endpoints — los crean US-BE-010 y US-BE-011.
  - Lógica de negocio — va en los endpoints.

#### 3) Reglas de dominio

- Regla 1: `bt2_picks.status` solo puede ser: `open | won | lost | void | cancelled`.
- Regla 2: `bt2_operating_sessions` tiene unique `(user_id, operating_day_key)` — un solo registro por usuario por día.
- Regla 3: `bt2_user_settings` es 1:1 con `bt2_users`. Se crea automáticamente con defaults al registrar un usuario nuevo (modificar `POST /bt2/auth/register`).
- Regla 4: `bt2_dp_ledger.balance_after_dp` se calcula en la capa de servicio — nunca en el cliente.

#### 4) Contexto técnico

- Depende de: `bt2_users` (Sprint 03), `bt2_events` (Sprint 03).
- Archivo: `apps/api/bt2_models.py` (ya existe — añadir los nuevos modelos).
- Migración: nueva revisión Alembic. Ejecutar `alembic upgrade head`.

#### 5) Criterios de aceptación

1. Given `alembic upgrade head`, When se aplica, Then las 6 tablas existen con todas sus columnas e índices.
2. Given `alembic downgrade -1`, When se aplica, Then las 6 tablas desaparecen sin afectar tablas de Sprint 03.
3. Given `POST /bt2/auth/register` con email nuevo, When se registra el usuario, Then existe fila en `bt2_user_settings` con defaults.

#### 6) Definition of Done

- [ ] T-088: Migración Alembic con 6 tablas aplicada y verificada (`alembic current`).
- [ ] T-089: Modelos SQLAlchemy en `bt2_models.py`. `bt2_user_settings` creada automáticamente en register.
- [ ] `alembic downgrade -1 && alembic upgrade head` sin error.

---

### US-BE-010 — API de picks: crear, consultar y liquidar

#### 1) Objetivo de negocio

Permitir que el usuario tome picks, los consulte y los liquide con un resultado real. Es el núcleo del protocolo conductual y el desbloqueante de US-FE-025 y US-FE-028.

#### 2) Alcance

- Incluye:
  - `POST /bt2/picks` — registra un pick abierto.
    - Body: `{ eventId, market, selection, oddsAccepted, stakeUnits }`.
    - Respuesta `201`: `{ pickId, status, openedAt, stakeUnits, oddsAccepted, eventLabel, titulo }`.
    - Validación: `event_id` existe en `bt2_events` con `status='scheduled'`. `odds_accepted > 1.0`. `stake_units > 0`.
    - Retorna `409` si el usuario ya tiene un pick abierto para el mismo evento y mercado.
  - `GET /bt2/picks` — lista picks del usuario autenticado.
    - Query params: `status` (open|won|lost|void|cancelled|all, default all), `date` (YYYY-MM-DD).
    - Respuesta: `{ picks: [{ pickId, eventId, eventLabel, market, selection, oddsAccepted, stakeUnits, status, openedAt, settledAt, pnlUnits, earnedDp }] }`.
  - `GET /bt2/picks/{id}` — detalle de un pick.
  - `POST /bt2/picks/{id}/settle` — liquida un pick.
    - Body: `{ resultHome, resultAway }`.
    - Lógica: determina outcome según `market`/`selection`. Calcula `pnl_units`. Inserta en `bt2_bankroll_snapshots`. Acredita DP en `bt2_dp_ledger`.
    - Respuesta `200`: `{ pickId, status, pnlUnits, bankrollAfterUnits, earnedDp, dpBalanceAfter }`.
    - Retorna `404` si el pick no existe o no pertenece al usuario. `409` si ya está liquidado.
- Excluye:
  - Lógica de bloqueo conductual por impulso (Sprint 05).
  - Picks de tenis.

#### 3) Reglas de dominio

- Regla 1: Solo se puede liquidar si `status='open'`.
- Regla 2: PnL: `won → stake_units * (odds_accepted - 1)`. `lost → -stake_units`. `void → 0`.
- Regla 3: DP al liquidar: `won → +2`, `lost → +1` (disciplina de registrar), `void → 0`. Registrar en `bt2_dp_ledger` con `reason='pick_settle'`, `reference_id=pick_id`.
- Regla 4: `bt2_bankroll_snapshots` recibe una entrada por settle con `event_type='pick_win'|'pick_loss'|'pick_void'`.
- Regla 5: El campo `bankrollAfterUnits` en la respuesta = `bt2_users.bankroll_amount` actualizado tras el PnL.

#### 4) Contexto técnico

- Depende de: US-BE-009, `get_current_bt2_user` (Sprint 03), `bt2_events`.
- Archivos: `apps/api/bt2_router.py`, `apps/api/bt2_schemas.py`.

#### 5) Criterios de aceptación

1. Given token válido y `eventId` con `status='scheduled'`, When `POST /bt2/picks`, Then `201` y pick en BD con `status='open'`.
2. Given pick `open`, When `POST /bt2/picks/{id}/settle` con resultado válido, Then `200` con `pnlUnits` correcto, `status='won'|'lost'`, entrada en `bt2_bankroll_snapshots` y `bt2_dp_ledger`.
3. Given pick ya liquidado, When `POST /bt2/picks/{id}/settle` de nuevo, Then `409`.
4. Given `GET /bt2/picks?status=open`, When usuario tiene 3 picks abiertos, Then retorna exactamente 3.
5. Given settle exitoso, When `GET /bt2/user/profile`, Then `bankroll_amount` refleja el PnL.

#### 6) Definition of Done

- [ ] T-090: `POST /bt2/picks` y `GET /bt2/picks` + `GET /bt2/picks/{id}` implementados y verificados con curl.
- [ ] T-091: `POST /bt2/picks/{id}/settle` con PnL, snapshot y DP implementado y verificado.
- [ ] V1 `/health` → `{"ok": true}`.

---

### US-BE-011 — Sesión operativa real: abrir, cerrar, gracia 24h

#### 1) Objetivo de negocio

El día operativo es la unidad de disciplina del protocolo. El usuario abre la estación al comenzar a operar y la cierra al terminar. El sistema otorga 24h de gracia para liquidar picks pendientes. Sin estos endpoints, `GET /bt2/session/day` retorna datos estáticos — con ellos, retorna el estado real del usuario.

#### 2) Alcance

- Incluye:
  - `POST /bt2/session/open` — abre la sesión del día.
    - Sin body. Calcula `operating_day_key` según `bt2_user_settings.timezone`.
    - Respuesta `201`: `{ sessionId, operatingDayKey, stationOpenedAt, graceUntilIso }`.
    - Retorna `409` si ya hay sesión abierta hoy.
  - `POST /bt2/session/close` — cierra la sesión del día.
    - Sin body. Marca `status='closed'`, registra `station_closed_at`, calcula `grace_until_iso = closed_at + 24h`.
    - Respuesta `200`: `{ sessionId, status, graceUntilIso, pendingSettlements }`.
  - Actualizar `GET /bt2/session/day` para leer de `bt2_operating_sessions` (no valores estáticos). Retornar `stationClosedForOperatingDay`, `graceUntilIso` y `pendingSettlementsPreviousDay` reales.
- Excluye:
  - Bloqueo automático de picks al cerrar sesión (Sprint 05).

#### 3) Reglas de dominio

- Regla 1: Una sola sesión `open` por usuario por `operating_day_key`.
- Regla 2: `grace_until_iso = station_closed_at + 24h`.
- Regla 3: `pendingSettlementsPreviousDay` = picks `open` del día operativo anterior al actual.
- Regla 4: Si no hay sesión para hoy, `GET /bt2/session/day` retorna `stationClosedForOperatingDay=false` y `graceUntilIso=null`.

#### 4) Contexto técnico

- Depende de: US-BE-009, `bt2_user_settings.timezone`, `get_current_bt2_user`.
- Actualizar endpoint `GET /bt2/session/day` existente en `bt2_router.py`.

#### 5) Criterios de aceptación

1. Given usuario sin sesión hoy, When `POST /bt2/session/open`, Then `201` y fila en `bt2_operating_sessions`.
2. Given sesión ya abierta hoy, When `POST /bt2/session/open` de nuevo, Then `409`.
3. Given `POST /bt2/session/close`, When se ejecuta, Then `grace_until_iso = closed_at + 24h` en BD.
4. Given sesión cerrada ayer con 2 picks `open`, When `GET /bt2/session/day`, Then `pendingSettlementsPreviousDay=2` y `graceUntilIso` real.

#### 6) Definition of Done

- [ ] T-092: `POST /bt2/session/open` y `POST /bt2/session/close` implementados.
- [ ] T-093: `GET /bt2/session/day` actualizado — sin valores hardcodeados.
- [ ] V1 `/health` → `{"ok": true}`.

---

### US-BE-012 — Settings de usuario y DP Ledger

#### 1) Objetivo de negocio

Exponer la configuración conductual del usuario (stake %, timezone, umbral DP para picks premium) y su saldo de Discipline Points, para que el frontend muestre el estado real de progresión y permita ajustes.

#### 2) Alcance

- Incluye:
  - `GET /bt2/user/settings` — retorna configuración actual.
    - Respuesta: `{ riskPerPickPct, dpUnlockPremiumThreshold, timezone, displayCurrency }`.
  - `PUT /bt2/user/settings` — actualiza configuración (todos los campos opcionales).
    - Body: `{ riskPerPickPct?, dpUnlockPremiumThreshold?, timezone? }`.
  - `GET /bt2/user/dp-balance` — saldo DP y contexto conductual.
    - Respuesta: `{ dpBalance, pendingSettlements, behavioralBlockCount }`.
    - `dpBalance = SUM(delta_dp)` de `bt2_dp_ledger`. `pendingSettlements` = picks `open` de días anteriores. `behavioralBlockCount` = COUNT de `bt2_behavioral_blocks`.
  - `GET /bt2/user/dp-ledger` — historial de movimientos DP.
    - Query param: `limit=20` (default). Ordenado `created_at DESC`.
    - Respuesta: `{ entries: [{ id, deltaDP, reason, referenceId, createdAt, balanceAfterDP }] }`.
- Excluye:
  - Lógica de desbloqueo de picks premium basada en DP (Sprint 05).

#### 3) Reglas de dominio

- Regla 1: `risk_per_pick_pct` entre 0.5 y 10.0. Fuera de rango → `422`.
- Regla 2: `dp_unlock_premium_threshold` entre 10 y 500. Fuera de rango → `422`.
- Regla 3: `dpBalance` mínimo 0 en la respuesta — si la suma es negativa, retornar 0.
- Regla 4: Si no existe fila en `bt2_user_settings`, crearla con defaults antes de retornar.

#### 4) Contexto técnico

- Depende de: US-BE-009 (`bt2_user_settings`, `bt2_dp_ledger`, `bt2_behavioral_blocks`).
- Archivos: `bt2_router.py`, `bt2_schemas.py`.

#### 5) Criterios de aceptación

1. Given usuario recién registrado, When `GET /bt2/user/settings`, Then `riskPerPickPct=2.0` y `timezone='America/Bogota'`.
2. Given `PUT /bt2/user/settings` con `{ "riskPerPickPct": 3.5 }`, Then retorna settings actualizados y persiste.
3. Given `PUT /bt2/user/settings` con `{ "riskPerPickPct": 15 }`, Then `422`.
4. Given 2 picks ganados y 1 perdido liquidados, When `GET /bt2/user/dp-balance`, Then `dpBalance=5`.
5. Given `GET /bt2/user/dp-ledger`, Then entradas ordenadas por `createdAt DESC`.

#### 6) Definition of Done

- [ ] T-094: `GET /bt2/user/settings` y `PUT /bt2/user/settings` implementados.
- [ ] T-095: `GET /bt2/user/dp-balance` y `GET /bt2/user/dp-ledger` implementados.
- [ ] V1 `/health` → `{"ok": true}`.

---

## Frontend

### US-FE-025 — Desacoplar stores de mocks: bóveda y ledger/picks → API real

#### 1) Objetivo de negocio

Que La Bóveda y el flujo de picks **dejen de depender** de datos hardcodeados (`vaultMockPicks` y derivados) y consuman la **misma forma de dominio (CDM)** desde la API, manteniendo la UX del Sprint 01 (tiers abierto/premium, copy en español, `selectionSummaryEs`, etc.).

#### 2) Alcance

- Incluye:
  - `useVaultStore` / vistas de bóveda: lista de picks desde **`GET /bt2/vault/picks`** (o ruta final documentada en OpenAPI), con estados **carga, vacío, error** (lista vacía legítima si no hay eventos en ventana; no reintroducir mock como fallback silencioso).
  - Uso de **`GET /bt2/events/upcoming`** (p. ej. `hours=48`) donde el producto requiera calendario o contexto de eventos; alineación de **naming** con el contrato publicado (camelCase vs snake: fuente de verdad **OpenAPI**).
  - `useTradeStore` (ledger, picks liquidados, IDs): hidratar desde API cuando exista endpoint de lectura acordado en Sprint 04 BE/US-DX, o transición documentada (p. ej. solo escritura local hasta endpoint listo — explicitar en `DECISIONES.md` si aplica).
  - Eliminación de imports de mock en rutas de usuario autenticado **salvo** modo desarrollo/feature flag explícito acotado.
- Excluye:
  - Implementación de **auth** (US-FE-026) — pero esta US **asume** llamadas autenticadas; el orden de entrega puede ser 026 → 025.
  - Cambios de identidad visual no solicitados.

#### 3) Contexto técnico actual

- `apps/web/src/store/useVaultStore.ts`, `useTradeStore.ts`
- `apps/web/src/pages/VaultPage.tsx`, `SettlementPage.tsx` (fuente del pick), componentes `PickCard`, etc.
- `apps/web/src/data/vaultMockPicks.ts` (dejar de ser fuente en producción).
- Referencia de contrato: esquema **`Bt2VaultPickOut`** / tipos TS compartidos si existen.

#### 4) Contrato de entrada/salida

- Entrada: JWT en requests protegidos (tras US-FE-026).
- Salida: UI renderiza picks y metadatos compatibles con el cliente actual; campos obligatorios acordados con backend (p. ej. `id`, `marketClass` o equivalente, `eventLabel`, `selectionSummaryEs`, `accessTier`, cuotas sugeridas según CDM).

#### 5) Reglas de dominio

- Regla 1: **Sin nombres de proveedor** en payloads mostrados al usuario; solo CDM.
- Regla 2: **401** → flujo de re-login o sesión expirada (coordinado con US-FE-026).
- Regla 3: Lista vacía ≠ error de servidor; copy claro al usuario.

#### 6) Criterios de aceptación (Given / When / Then)

1. Given usuario autenticado con token válido, When abre `/v2/vault`, Then la lista de picks proviene de la API, no de `vaultMockPicks`.
2. Given día sin eventos en ventana, When `GET /bt2/vault/picks` retorna lista vacía, Then la UI muestra estado vacío sin romper ni mostrar datos ficticios.
3. Given error de red o 5xx, When falla la carga, Then la UI muestra error recuperable (reintento o mensaje claro).
4. Given OpenAPI vigente, When se comparan campos de pick, Then el mapeo TS ↔ JSON está alineado (sin drift no documentado).

#### 7) No funcionales

- No duplicar lógica de negocio que deba vivir solo en servidor (p. ej. elegibilidad de pick) sin acuerdo US-DX.

#### 8) Riesgos y mitigación

- Riesgo: contrato aún en movimiento durante Sprint 04. Mitigación: US-DX + versionado menor o feature flag.

#### 9) Plan de pruebas

- Manual: vault con API real; tests de integración FE si el repo los tiene (fetch mockeado con contrato).

#### 10) Definition of Done

- [ ] Sin dependencia de mock en flujo principal de bóveda.
- [ ] Estados vacío/error/carga cubiertos.
- [ ] `DECISIONES.md` Sprint 04 anota cualquier transición temporal del ledger.

---

### US-FE-026 — Auth real: login, registro y JWT (`useUserStore`)

#### 1) Objetivo de negocio

Sustituir el **usuario mock** por autenticación real contra el backend BT2: registro, login, persistencia segura del **token JWT** y perfil desde **`GET /bt2/auth/me`**, habilitando el resto de llamadas protegidas del sprint.

#### 2) Alcance

- Incluye:
  - Pantallas o flujos **login / registro** contra `POST /bt2/auth/login` y `POST /bt2/auth/register` (cuerpos y códigos **409** / **401** según OpenAPI).
  - Almacenamiento del token (`localStorage` o `sessionStorage` según decisión en `DECISIONES.md`) y envío **`Authorization: Bearer`** en cliente HTTP compartido (interceptor/fetch wrapper).
  - `useUserStore`: persistir identidad relevante (ids, email, display name) tras `me`; limpiar estado en logout y en 401 global si se acuerda política.
  - Manejo de **sesión expirada** y errores de credenciales con copy en español.
- Excluye:
  - Refresh tokens (puede ser sprint posterior salvo US explícita).
  - OAuth terceros.

#### 3) Contexto técnico actual

- `apps/web/src/pages/AuthPage.tsx`, layouts/guards V2 (`V2ProtectedLayout`, etc.).
- `apps/web/src/store/useUserStore.ts`
- CORS y `VITE_*` base URL ya configurados según entorno.

#### 4) Contrato de entrada/salida

```json
{
  "register": {
    "body": { "email": "string", "password": "string", "display_name": "string?" },
    "200": { "access_token": "string", "user_id": "string", "display_name": "string" },
    "409": "email duplicado"
  },
  "login": {
    "body": { "email": "string", "password": "string" },
    "200": { "access_token": "string", "user_id": "string" },
    "401": "credenciales inválidas"
  },
  "me": {
    "headers": { "Authorization": "Bearer <token>" },
    "200": { "user_id": "string", "email": "string", "display_name": "string", "created_at": "string" }
  }
}
```

*(Ajustar nombres de campos al OpenAPI definitivo.)*

#### 5) Reglas de dominio

- Regla 1: No persistir contraseña en cliente.
- Regla 2: Email normalizado como acuerde el backend (p. ej. lowercase).
- Regla 3: Tras login exitoso, **refrescar perfil** con `me` antes de asumir campos completos.

#### 6) Criterios de aceptación (Given / When / Then)

1. Given credenciales válidas, When el usuario inicia sesión, Then obtiene token, se persiste según política y accede a rutas `/v2/*` protegidas.
2. Given registro con email nuevo, When completa el flujo, Then recibe token y perfil coherente.
3. Given email ya registrado, When intenta registrar de nuevo, Then ve feedback **409** comprensible.
4. Given token inválido o ausente en ruta protegida, When navega, Then es redirigido a auth o se solicita login.

#### 7) No funcionales

- Consideraciones mínimas de seguridad: no loguear token completo en consola en producción.

#### 8) Riesgos y mitigación

- Riesgo: XSS y robo de token. Mitigación: política de storage y CSP revisada en US-OPS si aplica.

#### 9) Plan de pruebas

- Manual login/register/me; tests de store si existen patrones en repo.

#### 10) Definition of Done

- [ ] Flujo E2E auth mínimo verificado contra API local.
- [ ] Guards V2 respetan sesión real.

---

### US-FE-027 — Bankroll y sesión conductual persistentes vía API

#### 1) Objetivo de negocio

Que **capital de trabajo**, **porcentaje de unidad (stake)** y **estado del día operativo** (gracia, cierre de estación, pendientes, etc.) **persistan en servidor** y el cliente los **sincronice** al iniciar sesión y tras mutaciones, en lugar de confiar solo en almacenamiento local cifrado.

#### 2) Alcance

- Incluye:
  - `useBankrollStore`: lectura inicial desde **`GET /bt2/user/profile`** (u otro contrato acordado que incluya `bankrollAmount` / moneda) y persistencia de cambios vía **`POST /bt2/user/bankroll`** cuando el usuario confirma tesorería; alinear **stake %** si el backend expone ajuste en perfil/settings (si no existe endpoint, documentar en US-DX + `DECISIONES.md` y mantener stake local hasta US posterior).
  - `useSessionStore`: hidratar **`GET /bt2/session/day`** (`operatingDayKey`, `userTimeZone`, `graceUntilIso`, `pendingSettlementsPreviousDay`, `stationClosedForOperatingDay`, etc.) según OpenAPI.
  - `GET /bt2/meta` para **`settlementVerificationMode`** (`trust` | `verified`) coherente con UI existente.
  - Comportamiento offline o desincronización: mensaje claro y reintento (sin corromper estado).
- Excluye:
  - Implementación servidor (US-BE); esta US es consumo y sincronización FE.
  - Migración masiva de histórico local antiguo salvo criterio explícito.

#### 3) Contexto técnico actual

- `useBankrollStore.ts`, `useSessionStore.ts`
- Páginas: tesorería, `DailyReviewPage`, guards que lean `stationLocked`, etc.
- `GET /bt2/metrics/behavioral` opcional en mismo bloque si el equipo acopla carga de métricas al arranque (o US aparte).

#### 4) Contrato de entrada/salida

- Entrada/salida según esquemas Sprint 03/04 en OpenAPI; campos camelCase o snake según documento único **US-DX**.

#### 5) Reglas de dominio

- Regla 1: **Fuente de verdad** post-login: servidor para bankroll confirmado en BD; evitar sobrescribir con valores stale locales sin merge explícito.
- Regla 2: Zona horaria del usuario debe coincidir con la usada en `operatingDayKey` (validar con backend).

#### 6) Criterios de aceptación (Given / When / Then)

1. Given usuario con bankroll guardado en BD, When abre la app tras login, Then ve el mismo capital que en servidor (tras sync).
2. Given usuario actualiza bankroll en tesorería, When confirma, Then `POST /bt2/user/bankroll` persiste y la UI refleja la respuesta.
3. Given `GET /bt2/session/day`, When la app carga sesión, Then locks y avisos de día/gracia respetan payload real.
4. Given `GET /bt2/meta`, When se muestra modo de liquidación en UI, Then coincide con valor servidor.

#### 7) No funcionales

- Evitar tormentas de requests: consolidar fetch de arranque cuando sea razonable.

#### 8) Riesgos y mitigación

- Riesgo: stake % solo local. Mitigación: US-DX para `bt2_user_settings` expuesto en API.

#### 9) Plan de pruebas

- Manual con usuario de prueba; casos borde: bankroll 0, sesión cerrada, gracia activa.

#### 10) Definition of Done

- [ ] Bankroll y sesión/día operativo sincronizados con API en flujo feliz.
- [ ] Gaps documentados en `DECISIONES.md` si algún campo sigue local temporalmente.

---

### US-FE-028 — Liquidación con resultados reales y bankroll en BD

#### 1) Objetivo de negocio

Que el **terminal de liquidación** use **resultados reales** del evento (p. ej. marcador o estado final expuesto vía CDM / `bt2_events` o pick enlazado) cuando el modo del producto lo permita, y que el **impacto en bankroll** quede reflejado en **servidor** (no solo `applyBankrollDelta` local), alineado al protocolo de disciplina y reflexión ya existente en Sprint 01.

#### 2) Alcance

- Incluye:
  - Sustituir dependencia exclusiva de mock en settlement por **datos de API**: pick/evento con campo de **resultado** o estado que permita prellenar o validar la liquidación según **`settlementVerificationMode`** (`trust` vs `verified`).
  - Flujo **trust**: el operador sigue declarando resultado; el cliente envía **liquidación al servidor** (p. ej. `POST /bt2/picks/{id}/settle` o contrato final US-DX) con payload acordado; servidor actualiza pick, bankroll y ledger server-side.
  - Flujo **verified** (si activo en el sprint): UI muestra resultado canónico y reduce ambigüedad según reglas US-DX.
  - Mantener **cuota casa vs sugerida**, reflexión mínima, y trazas `[BT2]` donde aplique.
- Excluye:
  - Definición de motor de odds o scraping (BE).
  - Cambios de copy educativo (US-FE-029).

#### 3) Contexto técnico actual

- `SettlementPage.tsx`, `useTradeStore.finalizeSettlement`, `settlementPnL`, `useBankrollStore.applyBankrollDelta`
- Eventos/picks: contratos Sprint 04 BE; ver [`HANDOFF_BA_PM_FRONTEND_SPRINT04.md`](../../HANDOFF_BA_PM_FRONTEND_SPRINT04.md) §4.

#### 4) Contrato de entrada/salida

- Depende de **US-DX** para el body exacto de settle (p. ej. `resultHome`, `resultAway`, outcome enum, `reflection`, cuotas, `stakeCop`).
- Respuesta esperada: pick actualizado, saldo bankroll coherente, entrada de ledger en servidor si aplica.

#### 5) Reglas de dominio

- Regla 1: **Idempotencia** o manejo de doble envío acordado con BE (no liquidar dos veces el mismo pick).
- Regla 2: PnL mostrado al usuario debe coincidir con **respuesta servidor** tras confirmar.
- Regla 3: Si servidor rechaza, el cliente no debe aplicar delta local optimista irreversible sin rollback.

#### 6) Criterios de aceptación (Given / When / Then)

1. Given pick abierto en BD con evento ya con resultado canónico (modo verified si disponible), When el usuario abre liquidación, Then ve datos alineados al servidor según reglas de producto.
2. Given liquidación confirmada en modo trust, When el servidor acepta el settle, Then el bankroll en **BD** y la UI coinciden tras refresco o respuesta.
3. Given error de servidor en settle, When falla el POST, Then el usuario ve error y el bankroll local no queda inconsistente con el servidor.
4. Given pick ya liquidado en servidor, When intenta liquidar de nuevo, Then el flujo evita duplicado (mensaje o redirección).

#### 7) No funcionales

- Latencia: feedback de carga en botón de confirmación.

#### 8) Riesgos y mitigación

- Riesgo: BE settle no listo al inicio del sprint FE. Mitigación: orden de tareas BE antes de FE o contrato mock servidor.

#### 9) Plan de pruebas

- Integración contra API; casos win/loss/push; verified vs trust si ambos existen.

#### 10) Definition of Done

- [ ] Liquidación persistida en servidor; bankroll coherente.
- [ ] Comportamiento documentado en `DECISIONES.md` para modos trust/verified.

---

### US-FE-029 — Lenguaje claro y glosario: bankroll, unidad, resultado en dinero (PnL)

#### 1) Objetivo de negocio

Que el operador **entienda sin jerga opaca** qué es su capital, qué es una **unidad de apuesta**, cómo se calcula en COP y qué significa el **resultado en dinero** de cada liquidación (hoy equivalente a PnL en producto). Reducir fricción cognitiva y alinear expectativas antes de que el volumen de métricas crezca con datos reales.

Además, **documentar en esta US** el marco de producto para una evolución posterior: **unidades de apuesta mayores a 1 como “recompensa” acotada** (sin implementar obligatoriamente el multiplicador en el mismo entregable si el sprint prioriza solo copy + glosario).

#### 2) Alcance

- Incluye:
  - Sustituir o complementar en UI las siglas **“PnL”** (u otros anglicismos crudos) por etiquetas en **español claro** (p. ej. *resultado en dinero*, *impacto en bankroll*, *ganancia o pérdida de esta jugada*) donde el contexto sea liquidación, ledger o rendimiento.
  - Un **punto de entrada al glosario** accesible desde el entorno V2 (p. ej. enlace en Ajustes, modal “Cómo leer tus números”, o sección dedicada) con definiciones breves y consistentes:
    - **Bankroll:** capital de trabajo total confirmado (COP).
    - **Porcentaje de unidad / stake %:** fracción del bankroll que define el valor de **una unidad** en COP.
    - **Unidad:** tamaño estándar de exposición por jugada; hoy **1 unidad = bankroll × (stake % / 100)**.
    - **Resultado en dinero (liquidación):** cambio en COP del bankroll atribuible a esa jugada, dado stake, cuota y resultado declarado.
  - Microcopy de apoyo (una línea) en **liquidación** y, si aplica, en **tesorería** que conecte unidad ↔ COP.
  - **Marco escrito** (sección “Principios para evolución” en esta US o entrada en `DECISIONES.md` al implementar): reglas no negociables para una futura **sugerencia de 1,5 u / 2 u** como recompensa: **techo máximo**, **opt-in o explicación explícita**, **protección al principiante (default 1 u)**, separación entre **recompensa narrativa (DP)** y **aumento de riesgo en dinero**.

- Excluye:
  - Implementación del **multiplicador de unidades** en liquidación o del motor de “mejor pick → más unidades” (queda para **US-FE-030** o US de sizing, salvo que el equipo decida explícitamente ampliar alcance).
  - Cambiar la fórmula matemática actual de 1 unidad sin nueva US de tesorería.
  - Contenido legal o fiscal; solo educación de producto.

#### 3) Contexto técnico actual

- Módulos típicos a revisar:
  - `apps/web/src/pages/SettlementPage.tsx`
  - `apps/web/src/pages/LedgerPage.tsx`, `PerformancePage.tsx`, `DailyReviewPage.tsx` (donde aparezca jerga o “PnL”).
  - Flujo de tesorería / modal de bankroll (`Treasury` / componentes asociados a `useBankrollStore`).
  - `apps/web/src/lib/treasuryMath.ts` (solo referencia conceptual en copy; no obligatorio tocar código numérico).
- Identidad verbal: [`../../04_IDENTIDAD_VISUAL_UI.md`](../../04_IDENTIDAD_VISUAL_UI.md), tono [`../../00_IDENTIDAD_PROYECTO.md`](../../00_IDENTIDAD_PROYECTO.md).

#### 4) Contrato de entrada/salida

No aplica API nueva. Opcional: claves i18n o constantes de copy centralizadas si el proyecto ya usa un patrón para textos compartidos.

#### 5) Reglas de dominio

- Regla 1: **Una unidad en COP** siempre debe poder explicarse como derivada de **bankroll** y **stake %**; el glosario no contradice `computeUnitValue`.
- Regla 2: El término **PnL** no debe ser la única etiqueta visible al usuario final en pantallas principales; si se conserva, debe ir acompañado o sustituido por texto en español.
- Regla 3: Cualquier mención futura a **más de 1 unidad** como recompensa debe explicitar que **aumenta exposición** y no es solo “premio gratuito”.

#### 6) Criterios de aceptación (Given / When / Then)

1. Given un usuario en **liquidación** con bankroll configurado, When ve el resumen de riesgo/retorno, Then encuentra al menos una etiqueta en español que explique el **monto en COP** como **una unidad** (o equivalente claro), sin depender solo de “PnL” en inglés.
2. Given un usuario en **Ajustes** (o ruta acordada), When abre el **glosario** (o “Cómo leer tus números”), Then ve definiciones de **bankroll**, **stake % / unidad** y **resultado en dinero** alineadas a las reglas de dominio.
3. Given **Ledger** o **Rendimiento**, When el listado o KPIs muestran resultado monetario, Then el copy no usa solo siglas opacas; el usuario puede inferir “ganancia/pérdida en COP respecto al stake”.
4. Given el cierre de implementación de US-FE-029, When se revisa `DECISIONES.md` (o anexo en esta US), Then constan **principios acordados** para la futura US de **unidades variables como recompensa** (techos, default 1 u, transparencia).

#### 7) No funcionales

- Accesibilidad: el glosario debe ser navegable por teclado y legible en modo actual del tema.
- No incrementar bundle con dependencias nuevas solo por esta US.

#### 8) Riesgos y mitigación

- Riesgo: textos demasiado largos en mobile. Mitigación: definiciones en modal o página dedicada; en cards solo una línea + enlace “¿Qué es esto?”.
- Riesgo: inconsistencia entre pantallas. Mitigación: tabla de términos canónicos en un solo archivo de copy o constantes.

#### 9) Plan de pruebas

- Revisión manual en `/v2/settlement`, `/v2/ledger`, `/v2/performance`, flujo tesorería.
- Test de UI opcional si el proyecto ya testea copy en componentes críticos.

#### 10) Definition of Done

- [ ] Copy actualizado según criterios §6; glosario accesible desde V2.
- [ ] `DECISIONES.md` (Sprint 04) u sección vinculada con principios para sizing-recompensa futuro.
- [ ] Sin regresión en tests existentes de `apps/web`.

---

---

### US-BE-013 — Ingesta diaria de eventos futuros desde Sportmonks (Addendum Sprint 04)

> **Tipo:** Addendum — cubre un gap identificado post-ejecución de US-BE-009 a US-BE-012.
> **Contexto:** El CDM tiene datos históricos hasta mayo 2025. Sin esta US, `GET /bt2/vault/picks` retorna lista vacía para fechas actuales. Es bloqueante de US-BE-014.

#### 1) Objetivo de negocio

Que el CDM tenga siempre fixtures de las próximas 48 horas con sus odds actuales, para que la bóveda del usuario muestre picks reales del día — no datos históricos.

#### 2) Alcance

- Incluye:
  - Script `scripts/bt2_cdm/fetch_upcoming.py`:
    - Lee `bt2_leagues` donde `is_active=true` (27 ligas: Tier S/A/B).
    - Para cada liga activa, llama a Sportmonks API endpoint `/v3/fixtures` con filtro `date_range` = hoy hasta hoy + 2 días, con includes `participants,odds,scores,league`.
    - Upsert en `bt2_events` (idempotente por `sportmonks_fixture_id`) y en `bt2_odds_snapshot`.
    - Log de progreso y reporte en `docs/bettracker2/recon_results/upcoming_{fecha}.md`.
  - CLI args: `--hours-ahead 48` (default), `--dry-run`.
  - Estimación de créditos: ~27 requests por ejecución (1 por liga activa). Corre una vez al día.
  - Ejecución manual por ahora. Cron job en Sprint 05.
- Excluye:
  - Ligas `unknown` o `is_active=false`.
  - Automatización (scheduler/cron) — Sprint 05.
  - The-Odds-API — solo Sportmonks.

#### 3) Reglas de dominio

- Regla 1: Si el fixture ya existe en `bt2_events` por `sportmonks_fixture_id`, actualiza `status` y odds — no duplica.
- Regla 2: Solo se ingestan fixtures de ligas con `is_active=true` en `bt2_leagues`.
- Regla 3: El script no toca `raw_sportmonks_fixtures` — escribe directo al CDM (`bt2_events` + `bt2_odds_snapshot`).
- Regla 4: Si Sportmonks retorna 429, esperar 60 segundos y reintentar una vez. Si falla de nuevo, loguear y continuar con la siguiente liga.

#### 4) Contexto técnico

- Usa `SPORTMONKS_API_KEY` del `.env`.
- Depende de: `bt2_leagues` (Sprint 03), `bt2_events`, `bt2_odds_snapshot` (Sprint 03).
- Reutilizar la lógica de parseo de `normalize_fixtures.py` (`_parse_kickoff`, `_parse_status`, `_extract_odds`).
- Archivo nuevo: `scripts/bt2_cdm/fetch_upcoming.py`.

#### 5) Criterios de aceptación

1. Given `python scripts/bt2_cdm/fetch_upcoming.py`, When se ejecuta, Then `bt2_events` contiene fixtures con `kickoff_utc` en las próximas 48h y `status='scheduled'`.
2. Given el script ejecutado dos veces seguidas, When se consulta `SELECT COUNT(*) FROM bt2_events`, Then el conteo no crece (idempotencia).
3. Given liga con `is_active=false`, When el script corre, Then no se ingestan fixtures de esa liga.
4. Given reporte generado, When se abre `upcoming_{fecha}.md`, Then muestra ligas procesadas, fixtures nuevos y actualizados, créditos consumidos.

#### 6) Definition of Done

- [ ] T-104: `fetch_upcoming.py` implementado con upsert idempotente, manejo de 429 y reporte.
- [ ] `SELECT COUNT(*) FROM bt2_events WHERE kickoff_utc > now()` retorna > 0 tras ejecución.
- [ ] V1 `/health` → `{"ok": true}`.

---

### US-BE-014 — Pick snapshot diario: 5 fijos al abrir sesión (Refinement de US-BE-010)

> **Tipo:** Refinement de US-BE-010.
> **Contexto:** US-BE-010 implementó `GET /bt2/vault/picks` como ventana deslizante de 24h. Esta US reemplaza ese comportamiento por un snapshot fijo de 5 picks generado al abrir la sesión del día — mismo set para todas las consultas del día, 3 estándar + 2 premium.
> **Depende de:** US-BE-013 (necesita fixtures futuros en `bt2_events`).

#### 1) Objetivo de negocio

Que el usuario vea siempre sus mismos 5 picks del día sin importar a qué hora entre — eliminando el FOMO de "entrar tarde y perder picks". El sistema selecciona los 5 de mayor valor estadístico disponibles al momento de abrir la sesión y los congela para ese día operativo.

#### 2) Alcance

- Incluye:
  - Nueva tabla `bt2_daily_picks` vía migración Alembic:
    - `id (serial PK)`, `user_id (uuid FK bt2_users)`, `event_id (int FK bt2_events)`, `operating_day_key (varchar 10)`, `access_tier (varchar 10)` — `standard` | `premium`, `is_available (bool, default true)`, `suggested_at (timestamptz default now())`.
    - Unique constraint `(user_id, event_id, operating_day_key)`.
    - Índice `(user_id, operating_day_key)`.
  - Modificar `POST /bt2/session/open` (US-BE-011): al abrir sesión, si no existe snapshot para el `operating_day_key` actual, generarlo:
    - Consulta `bt2_events` con `kickoff_utc` entre `hoy 00:00` y `hoy 23:59` (zona horaria del usuario), `status='scheduled'`, con al menos 1 odd en `bt2_odds_snapshot`.
    - Ordena por: Tier S primero, luego A, luego B; dentro de cada tier por odds más balanceadas (menor margen de casa).
    - Toma los 3 mejores como `standard` y los 2 siguientes como `premium`.
    - Inserta en `bt2_daily_picks`. Si hay menos de 5 eventos disponibles, inserta los que haya.
  - Modificar `GET /bt2/vault/picks`: leer de `bt2_daily_picks` en lugar de `bt2_events` directamente. Marcar `is_available=false` si el evento ya tiene `status != 'scheduled'` al momento de la consulta.
  - Añadir a la respuesta de cada pick:
    - `isAvailable (bool)` — si el partido aún no empezó.
    - `accessTier (string)` — `standard` | `premium`.
    - `externalSearchUrl (string)` — `https://www.google.com/search?q={home}+vs+{away}+{fecha_iso}` construido con los nombres reales del evento.
- Excluye:
  - Picks distintos por usuario (mismo pool base para todos) — personalización en Sprint 05.
  - Picks de ligas `unknown` — solo `is_active=true`.
  - Desbloqueo de picks premium (lógica de DP) — ya existe en `bt2_user_settings.dp_unlock_premium_threshold`; esta US solo clasifica el tier, no bloquea.

#### 3) Reglas de dominio

- Regla 1: El snapshot se genera una sola vez por `(user_id, operating_day_key)`. Consultas posteriores de `GET /bt2/vault/picks` leen el snapshot existente — nunca regeneran.
- Regla 2: `is_available` se recalcula en tiempo real en cada GET (no se persiste el cambio). Un pick es unavailable si `bt2_events.status != 'scheduled'` al momento de la consulta.
- Regla 3: Si no hay eventos futuros en `bt2_events` para el día (US-BE-013 no corrió aún), `GET /bt2/vault/picks` retorna lista vacía con mensaje `"No hay eventos disponibles para hoy. El sistema actualiza la cartelera cada mañana."`.
- Regla 4: `externalSearchUrl` se construye como `https://www.google.com/search?q={homeTeam}+vs+{awayTeam}+{kickoffDate}` donde `kickoffDate` es `YYYY-MM-DD`. Los espacios se reemplazan por `+`.
- Regla 5: `premium` picks aparecen en la lista siempre — el FE decide si mostrarlos bloqueados según el DP del usuario (usando `GET /bt2/user/dp-balance` y `bt2_user_settings.dp_unlock_premium_threshold`). El backend no los oculta.

#### 4) Contexto técnico

- Depende de: US-BE-013 (`bt2_events` con fechas futuras), US-BE-011 (`POST /bt2/session/open`), `bt2_leagues.tier` y `bt2_leagues.is_active`.
- Modificar: `apps/api/bt2_router.py` (session/open + vault/picks), `apps/api/bt2_schemas.py` (añadir campos a `Bt2VaultPickOut`).
- Nueva migración Alembic para `bt2_daily_picks`.

#### 5) Criterios de aceptación

1. Given `POST /bt2/session/open` por primera vez hoy con eventos disponibles, When se ejecuta, Then `bt2_daily_picks` tiene hasta 5 filas para ese `(user_id, operating_day_key)`.
2. Given `POST /bt2/session/open` por segunda vez en el mismo día, When se ejecuta, Then `bt2_daily_picks` no cambia — mismo snapshot.
3. Given `GET /bt2/vault/picks` con snapshot generado, When se llama, Then retorna los picks del snapshot con `isAvailable`, `accessTier` y `externalSearchUrl` en cada pick.
4. Given partido que inició (status cambió a `inplay`), When `GET /bt2/vault/picks`, Then ese pick aparece con `isAvailable=false`.
5. Given día sin eventos en `bt2_events`, When `GET /bt2/vault/picks`, Then retorna lista vacía con mensaje informativo — no error 5xx.
6. Given `externalSearchUrl` en la respuesta, When se abre en browser, Then redirige a búsqueda Google con los equipos y fecha del evento.

#### 6) Definition of Done

- [ ] T-105: Migración Alembic con `bt2_daily_picks` aplicada.
- [ ] T-106: `POST /bt2/session/open` genera snapshot de hasta 5 picks en `bt2_daily_picks`.
- [ ] T-107: `GET /bt2/vault/picks` lee de `bt2_daily_picks`, incluye `isAvailable`, `accessTier`, `externalSearchUrl`.
- [ ] Idempotencia verificada: doble apertura de sesión no duplica picks.
- [ ] V1 `/health` → `{"ok": true}`.

---

## Contratos

*(US-DX del Sprint 04: OpenAPI compartido, tipos TS, etc.)*

## Operación

*(US-OPS del Sprint 04 si aplica.)*
