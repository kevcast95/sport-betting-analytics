# Handoff: Pre-contexto Sprint 04 para BA/PM Frontend

**Audiencia:** Agente en rol Business Analyst / Product Owner Frontend — BetTracker 2.0.
**Fecha:** 2026-04-07
**Estado:** Pre-handoff anticipado — Sprint 03 Backend en ejecución.

---

## Por qué este documento existe ahora y no al cerrar Sprint 03

Este documento se entrega **mientras Sprint 03 está en ejecución** (no al final) por una razón concreta: el agente Frontend ya está activo, haciendo preguntas y preparando el terreno para Sprint 04.

Esperar a que Sprint 03 termine para compartir este contexto sería equivalente a no mostrarle los planos al carpintero hasta que la estructura esté levantada. El FE PM puede diseñar sus US-FE-025 a 028, revisar sus stores de Zustand actuales e identificar gaps **en paralelo** con la ejecución del backend — sin bloquear ni ser bloqueado.

**Lo que este documento es:**
- Contratos de API que el backend entregará en Sprint 03 y Sprint 04
- Schema del dominio conductual que Sprint 04 BE construirá
- Mapa de qué stores de Zustand se conectan a qué endpoint
- Numeración acordada para las US-FE de Sprint 04

**Lo que este documento NO es:**
- No sustituye la **fuente de verdad** de US: las historias formales viven en **`docs/bettracker2/sprints/sprint-04/US.md`** (US-FE-025 … US-FE-029 redactadas allí). Este handoff es contexto y contratos; `TASKS.md` / `QA_CHECKLIST.md` del sprint se derivan de ese `US.md`.

---

## 1. Qué entrega Sprint 03 Backend (contratos disponibles para FE)

Sprint 03 termina con estos endpoints reales en producción local:

### Auth JWT

```
POST /bt2/auth/register
  body: { email: string, password: string, display_name?: string }
  200: { access_token: string, user_id: string, display_name: string }
  409: email ya registrado

POST /bt2/auth/login
  body: { email: string, password: string }
  200: { access_token: string, user_id: string }
  401: credenciales inválidas

GET /bt2/auth/me
  header: Authorization: Bearer {token}
  200: { user_id: string, email: string, display_name: string, created_at: string }
  401: token inválido o ausente
```

**Para el FE:** `useUserStore` deja de usar el mock de usuario hardcodeado. El token JWT se guarda en `localStorage` o `sessionStorage` y se envía en cada request protegido.

### Endpoints de dominio (Sprint 03, datos reales)

```
GET /bt2/meta
  200: { settlementVerificationMode: "trust" | "verified" }
  — alinear con US-DX / Sprint 01 (`verified` = vNext con resultado canónico); no usar `"verify"` si el contrato global dice `verified`.

GET /bt2/session/day    [protegido]
  200: { operatingDayKey: string, userTimeZone: string,
         graceUntilIso: string | null,
         pendingSettlementsPreviousDay: number,
         stationClosedForOperatingDay: boolean }

GET /bt2/vault/picks    [protegido]
  200: { picks: Bt2VaultPickOut[], generatedAtUtc: string }
  — picks vacíos si no hay partidos en las próximas 24h (no mock)

GET /bt2/events/upcoming?hours=48    [protegido]
  200: { events: [{ eventId, league, homeTeam, awayTeam, kickoffUtc, odds1x2 }] }

GET /bt2/metrics/behavioral    [protegido]
  200: { roiPct, roiHumanEs, maxDrawdownUnits, maxDrawdownHumanEs,
         behavioralBlockCount, estimatedLossAvoidedCop,
         behavioralHumanEs, hitRatePct, hitRateHumanEs,
         isDemo: boolean }
  — isDemo: true si el usuario no tiene historial de picks aún

POST /bt2/user/bankroll    [protegido]
  body: { amount: number, currency: string }
  200: { bankrollAmount: number, currency: string, updatedAt: string }

GET /bt2/user/profile    [protegido]
  200: { userId, email, displayName, bankrollAmount, bankrollCurrency, createdAt }
```

**Schema de `Bt2VaultPickOut` — sin cambios en Sprint 03:**
Los picks de la Bóveda mantienen exactamente el mismo contrato que el frontend V2 ya consume. Solo cambia la fuente: de hardcodeado a `bt2_events` + `bt2_odds_snapshot` de PostgreSQL.

---

## 2. Schema del dominio conductual — Sprint 04 Backend

Estas tablas las construye Sprint 04 BE. El FE PM necesita conocerlas para diseñar los contratos de sus US.

```sql
-- Picks del usuario
bt2_picks
  id (serial PK)
  user_id (uuid FK bt2_users)
  event_id (int FK bt2_events)
  market (varchar)         -- "1X2", "Over/Under 2.5", etc.
  selection (varchar)      -- "1", "X", "2", "Over 2.5", etc.
  odds_taken (decimal)     -- cuota en el momento de tomar el pick
  stake_units (decimal)    -- unidades apostadas
  status (varchar)         -- open | won | lost | void | cancelled
  opened_at (timestamptz)
  settled_at (timestamptz, nullable)
  result_home (int, nullable)
  result_away (int, nullable)
  pnl_units (decimal, nullable)  -- calculado al settlement

-- Sesiones conductales del día (distinto a bt2_sessions de auth)
bt2_operating_sessions
  id (serial PK)
  user_id (uuid FK)
  operating_day_key (varchar)   -- "2026-04-07"
  station_opened_at (timestamptz)
  station_closed_at (timestamptz, nullable)
  status (varchar)              -- open | closed | force_closed
  grace_until_iso (timestamptz, nullable)  -- 24h de gracia para liquidar

-- Historial de bankroll (snapshots por evento)
bt2_bankroll_snapshots
  id (serial PK)
  user_id (uuid FK)
  snapshot_date (date)
  balance_units (decimal)
  event_type (varchar)   -- deposit | withdrawal | pick_win | pick_loss | session_close

-- Ledger de Discipline Points
bt2_dp_ledger
  id (serial PK)
  user_id (uuid FK)
  delta_dp (int)               -- positivo o negativo
  reason (varchar)             -- "pick_premium_unlock" | "session_closed" | "win_bonus" | etc.
  reference_id (int, nullable) -- pick_id o session_id
  created_at (timestamptz)
  balance_after_dp (int)       -- saldo acumulado tras esta transacción

-- Intervenciones conductales (bloqueos de impulso)
bt2_behavioral_blocks
  id (serial PK)
  user_id (uuid FK)
  trigger_type (varchar)   -- impulse | overlimit | tilt
  blocked_at (timestamptz)
  context_json (jsonb)     -- datos del intento bloqueado
  estimated_loss_avoided_units (decimal)

-- Configuración por usuario
bt2_user_settings
  user_id (uuid PK FK bt2_users)
  bankroll_units (decimal)
  risk_per_pick_pct (decimal)        -- % del bankroll por pick (default 2%)
  dp_unlock_premium_threshold (int)  -- DP requeridos para picks premium (default 50)
  timezone (varchar)                 -- "America/Bogota"
  display_currency (varchar)         -- "COP"
```

---

## 3. Mapa de vistas ↔ tablas ↔ stores de Zustand

| Vista (Sprint 01) | Tabla principal Sprint 04 | Store Zustand actual |
|-------------------|--------------------------|---------------------|
| Vault / La Bóveda | `bt2_picks` (open) + `bt2_dp_ledger` | `useVaultStore`, `useTradeStore` |
| Settlement Terminal | `bt2_picks` (pending) + `bt2_operating_sessions` | `useTradeStore`, `useSessionStore` |
| After-Action Review | `bt2_picks` (día cerrado) + `bt2_operating_sessions` | `useSessionStore` |
| Strategic Ledger | `bt2_bankroll_snapshots` + `bt2_picks` (histórico) | `useSessionStore` |
| Strategy & Performance | Agregados sobre `bt2_picks` | (sin store dedicado aún) |
| Elite Progression Path | `bt2_dp_ledger` (saldo) + `bt2_behavioral_blocks` | `useUserStore` |
| Diagnostic | `bt2_user_settings` + métricas calculadas | `useUserStore` |
| Behavioral Metrics | `bt2_behavioral_blocks` + `bt2_dp_ledger` | `useUserStore` |

---

## 4. Flujo conductual completo (referencia para criterios de aceptación)

**Alcance:** Los `POST` de esta sección (`/bt2/session/open`, `/bt2/picks`, `/bt2/picks/{id}/settle`, `/bt2/session/close`) son **Sprint 04 Backend** (persistencia conductual). **No** figuran en el cierre de Sprint 03 descrito en §1; el FE PM debe tratarlos como contratos a formalizar en `US.md` / `US-DX` cuando abra Sprint 04.

```
1. Usuario abre sesión del día
   → POST /bt2/session/open
   → bt2_operating_sessions (status: open)

2. Consulta picks disponibles
   → GET /bt2/vault/picks  (picks del CDM, próximas 24h)

3. Toma un pick premium (cuesta DP)
   → POST /bt2/picks  { eventId, market, selection, oddsAccepted, stakeUnits }
   → bt2_picks (status: open)
   → bt2_dp_ledger (-DP si es premium)

4. Al día siguiente, liquida resultados
   → POST /bt2/picks/{id}/settle  { resultHome, resultAway }
   → bt2_picks (status: won | lost)
   → bt2_bankroll_snapshots (actualiza balance)
   → bt2_dp_ledger (+DP si comportamiento disciplinado)

5. Cierra la sesión del día
   → POST /bt2/session/close
   → bt2_operating_sessions (status: closed)
   → Gracia de 24h para picks pendientes de liquidar
```

---

## 5. Numeración US-FE para Sprint 04

Sprint 01 cerró en **US-FE-024**. Sprint 04 FE comienza en **US-FE-025** y continúa secuencialmente. No usar saltos (201+) ni prefijos de sprint — el namespace es global.

| ID reservado | Contenido previsto |
|--------------|-------------------|
| US-FE-025 | Desacoplar stores de mocks: vault + picks → API real |
| US-FE-026 | Auth flow real (login/register con JWT del backend) |
| US-FE-027 | Bankroll y sesión conductual persistente desde BD |
| US-FE-028 | Settlement con resultados reales desde `bt2_events` |
| US-FE-029 | Lenguaje claro, glosario (bankroll / unidad / resultado en dinero), marco sizing futuro |

**Formalización:** cuerpo completo de **US-FE-025 … US-FE-029** en [`sprints/sprint-04/US.md`](sprints/sprint-04/US.md).

---

## 6. Qué puede hacer el FE PM ahora (mientras Sprint 03 corre)

- Revisar `useVaultStore`, `useTradeStore`, `useSessionStore`, `useUserStore` e identificar qué campos están hardcodeados y cuáles mapean a los contratos de §1 y §2.
- Las US-FE-025 … 029 con criterios Given/When/Then están en [`sprints/sprint-04/US.md`](sprints/sprint-04/US.md); contrastar con contratos §1.
- Identificar qué vistas del Sprint 01 necesitan cambios de schema cuando los datos sean reales (p.ej. ¿`curvaEquidad` real vs. calculada? ¿cómo se renderiza un pick sin odds todavía?).
- Marcar gaps: si algún contrato de §1 no cubre lo que el frontend necesita, documentarlo como `US-DX-###` pendiente de validación con el backend.

**No ejecutar código hasta que Sprint 03 esté verificado y se abra Sprint 04 formalmente.**

---

## 7. Referencias

| Documento | Ruta |
|-----------|------|
| Sprint 02 — Atraco Masivo (datos) | `docs/bettracker2/sprints/sprint-02/US.md` |
| Sprint 03 — CDM + Auth + Endpoints | `docs/bettracker2/sprints/sprint-03/US.md` |
| Sprint 03 — TASKS (estado de ejecución) | `docs/bettracker2/sprints/sprint-03/TASKS.md` |
| Rol BA/PM Frontend | `docs/bettracker2/agent_roles/front_end_agent.md` |
| Rol BA/PM Backend | `docs/bettracker2/agent_roles/back_end_agent.md` |
| Identidad visual Zurich Calm | `docs/bettracker2/04_IDENTIDAD_VISUAL_UI.md` |
| Contrato de US | `docs/bettracker2/01_CONTRATO_US.md` |
| Handoff backend (stub → CDM, contexto API) | `docs/bettracker2/HANDOFF_BA_PM_BACKEND.md` |
| Numeración US-FE-025…028 (coordinación) | `docs/bettracker2/sprints/sprint-03/US.md` (pie del documento) |
