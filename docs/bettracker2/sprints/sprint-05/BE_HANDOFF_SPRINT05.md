# Handoff Backend → Frontend (Sprint 05 — US-BE-017 / 018 / US-DX-001)

## Endpoints nuevos o con contrato relevante

| Método | Ruta | Notas |
|--------|------|--------|
| `GET` | `/bt2/operating-day/summary` | Query opcional `operatingDayKey=YYYY-MM-DD`; omisión = día operativo actual (TZ usuario). Siempre **200** con ceros si no hay actividad. **422** si la clave no es fecha válida. |
| `POST` | `/bt2/picks` | Si el evento está en `bt2_daily_picks` como **premium** para el `operating_day_key` actual: exige **≥ 50 DP**; si no, **402** con `detail` objeto (`code`, `message`, `requiredDp`, `currentDp`). En éxito: **una fila** `bt2_dp_ledger` con `reason=pick_premium_unlock`, `delta_dp=-50`, `reference_id=pick_id` (misma transacción que el pick). |
| `POST` | `/bt2/session/open` | Tras validar que no hay sesión abierta hoy: cierra sesiones **huérfanas** de días anteriores (`operating_day_key` &lt; hoy) con **−50** `penalty_station_unclosed` (idempotente por sesión). Aplica **−25** `penalty_unsettled_picks` por sesiones cerradas con gracia vencida y picks abiertos al cierre (idempotente). Luego crea sesión + snapshot como antes. |

## `GET /bt2/meta`

- `contractVersion` por defecto **`bt2-dx-001-s5`** (bump Sprint 05).

## Catálogo `reason` (US-DX-001 / D-05-003)

Ver `docs/bettracker2/sprints/sprint-05/DECISIONES.md` tabla `reason` → `reasonLabelEs`.

**Onboarding:** En el ledger pueden figurar **`onboarding_welcome`** o **`onboarding_phase_a`** (esta última es la que persiste el endpoint actual de onboarding). El FE debe **mapear ambas al mismo texto** de UI (mismo copy que una sola fila de catálogo), para no duplicar ni dejar una sin etiqueta.

## FE: evitar doble descuento de DP

Cuando el flujo ya llama **`POST /bt2/picks`** y el servidor registra **`pick_premium_unlock`**:

- **No** llamar a `incrementDisciplinePoints` (u otro ajuste local) por el mismo −50.
- La fuente de verdad es **`GET /bt2/user/dp-balance`** y **`GET /bt2/user/dp-ledger`** tras la respuesta del POST.

Penalizaciones de **`session/open`** solo existen en servidor; el FE no debe simular −25/−50 locales al abrir sesión.

## Verificación manual mínima (curl)

1. Usuario con DP &lt; 50 y pick premium en snapshot → `POST /bt2/picks` → **402** y sin fila nueva en `bt2_picks`.
2. Usuario con DP ≥ 50 → mismo → **201** y ledger `pick_premium_unlock` −50; `dp-balance` coherente con suma del ledger.
3. `POST /bt2/session/open` dos veces el mismo día → segunda **409**; no duplicar filas de penalización para el mismo `reference_id` (sesión).
4. `GET /bt2/health` (V1) → `{"ok": true}`.
