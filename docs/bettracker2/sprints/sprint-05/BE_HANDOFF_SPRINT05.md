# Handoff Backend → Frontend (Sprint 05 — contratos BT2)

> **T-143, T-144, T-146, T-148, T-150, T-152** implementadas en código (paquete D-05-012 … D-05-018). Ver [`TASKS.md`](./TASKS.md).

## Versionado

| Estado | `contractVersion` (`GET /bt2/meta`) |
|--------|--------------------------------------|
| Actual | **`bt2-dx-001-s5.2`** (economía settle +10, cierre sesión +20, `PickOut` ampliado, normalización POST picks) |

## Endpoints ya existentes (recordatorio)

| Método | Ruta | Notas |
|--------|------|-------|
| `GET` | `/bt2/vault/picks` | `kickoffUtc`, `eventStatus`, `isAvailable` (**US-BE-019**, **D-05-011**). |
| `GET` | `/bt2/operating-day/summary` | Query `operatingDayKey` opcional; **200** con ceros. Incluye **`dpEarnedFromSessionClose`** y **`dpEarnedFromSettlements`** (razones distintas en ledger). |
| `POST` | `/bt2/picks` | Premium → **402** si DP &lt; 50; ledger `pick_premium_unlock` (**D-05-004/005**). **422** si `market`/`selection` no normalizan (US-BE-023). Persiste mercado/selección **canónicos**. |
| `POST` | `/bt2/picks/{id}/settle` | **`earnedDp` = 10** won/lost/void; ledger **`pick_settle` +10** siempre; **`settlementSource`** = `user`. |
| `GET` | `/bt2/picks`, `/bt2/picks/{id}` | **`PickOut`** con alias camelCase en campos nuevos: `resultHome`, `resultAway`, `earnedDp`, `kickoffUtc`, `eventStatus`, `settlementSource`. **404** pick ajeno. |
| `POST` | `/bt2/session/close` | Ledger **`session_close_discipline` +20** (idempotente por `session.id`); respuesta **`earnedDpSessionClose`**, **`dpBalanceAfter`** (camelCase). |

## Catálogo `reason` (ledger)

Ver [`DECISIONES.md`](./DECISIONES.md) **D-05-003**. Entradas nuevas / relevantes al paquete:

- **`pick_settle`** — copy sugerido: *Liquidación de pick — disciplina de cierre* (+10 en los tres outcomes tras **T-143**).
- **`session_close_discipline`** — *Recompensa por cerrar la estación* (+**N**, default 20).

Onboarding: mapear **`onboarding_welcome`** y **`onboarding_phase_a`** al mismo texto en UI.

## FE: sin doble DP / bankroll

- Tras **`POST /bt2/picks`** con premium, no aplicar −50 local; sincronizar con **`dp-balance`** / **`dp-ledger`**.
- Tras settle, usar **`bankrollAfterUnits`** / **`dpBalanceAfter`** de la respuesta como fuente de verdad.

## Verificación manual (post-implementación)

1. Settle lost y void → **`earnedDp`** 10; ledger tres filas `pick_settle` +10; segundo settle mismo pick → **409**.
2. `session/close` → fila `session_close_discipline`; segundo close mismo día → **404**; sin doble acreditación.
3. `GET /bt2/picks/{id}` pick liquidado → marcador + `earnedDp` + `kickoffUtc` coherentes con evento.
4. `GET /bt2/operating-day/summary` → `dpEarnedFromSettlements` y `dpEarnedFromSessionClose` acordes a SQL.
5. V1 `GET /health` → `{"ok": true}`.
