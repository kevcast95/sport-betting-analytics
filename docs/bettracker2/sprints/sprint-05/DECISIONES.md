# Sprint 05 — Decisiones

## D-05-001 — Calendario: contenido “motor” del BA en Sprint 6 y 7

**Contexto:** El BA_PM_BE agrupó DSR + CDM + cron + normalización + analytics en un “Sprint 5” y parlays/diagnóstico avanzado en “Sprint 6”.

**Decisión:** En este repo, **Sprint 05** se reserva para **cierre técnico y deuda V2** (API-first, dp-ledger, hidratar picks, estados de compromiso, ledger BE en **desbloqueo premium** (−50 DP) y penalizaciones). El paquete **DSR + cron upcoming + enum mercados + US-DX amplio + analytics picks** pasa a planificarse como **Sprint 06**. **Parlays + recalibración diagnóstico longitudinal + D-04-001 bankroll COP** quedan orientados a **Sprint 07** (sujeto a repriorización).

**Consecuencia:** `sprint-05/US.md` no incluye US de motor DSR; el alcance BE/DX del S5 son los **mínimos** que desbloquean coherencia conductual y FE.

---

## D-05-002 — Cierre de sesión huérfana al abrir día nuevo (US-BE-017)

**Contexto:** Si el usuario nunca llamó `POST /bt2/session/close` en el día anterior, puede quedar una fila `bt2_operating_sessions` con `status = 'open'` y un `operating_day_key` pasado.

**Decisión:** Al ejecutar `POST /bt2/session/open` para el día `D`, si existe una sesión anterior del mismo usuario con `operating_day_key < D` (orden lexicográfico `YYYY-MM-DD`) y `status = 'open'`, el servidor **cierra** esa sesión: `status = 'closed'`, `station_closed_at = now()` (UTC), `grace_until_iso = now() + 24h` (misma política que cierre normal). Luego aplica **`penalty_station_unclosed`** (−50 DP) una sola vez por esa sesión (idempotencia vía `bt2_dp_ledger.reason` + `reference_id = session.id`).

**Trade-off:** No se distingue en MVP entre “olvidó cerrar” y “app cerrada abruptamente”; el producto prioriza integridad del protocolo.

---

## D-05-003 — Catálogo `reason` → copy UI (`reasonLabelEs`) — US-DX-001

**Uso:** el FE muestra movimientos de `GET /bt2/user/dp-ledger` con texto legible; la clave estable es `reason`.

| `reason` | `reasonLabelEs` (sugerido) |
|----------|----------------------------|
| `pick_settle` | Liquidación de pick |
| `pick_premium_unlock` | Desbloqueo pick premium |
| `onboarding_welcome` | Bienvenida — onboarding fase A |
| `onboarding_phase_a` | Bienvenida — onboarding fase A (valor persistido hoy por `POST /bt2/user/onboarding-phase-a-complete`) |
| `penalty_station_unclosed` | Penalización: estación sin cerrar |
| `penalty_unsettled_picks` | Penalización: picks sin liquidar (tras gracia) |
| `parlay_activation_2l` | *(reservado Sprint 07)* Activación parlay 2 eventos |
| `parlay_activation_3l` | *(reservado Sprint 07)* Activación parlay 3 eventos |

**Nota:** Si el BE añade una razón nueva, debe actualizarse esta tabla y `US-DX-001` / `bt2Types.ts` en el mismo PR.

**FE — onboarding:** Pueden aparecer en ledger **`onboarding_welcome`** o **`onboarding_phase_a`** según versión de flujo/API; el **copy en UI debe ser el mismo** para ambas claves (p. ej. “Bienvenida — onboarding fase A”). Mapear las dos al mismo `reasonLabelEs` en el cliente.

---

## D-05-004 — Desbloqueo premium vs “tomar el pick”

**Contexto:** En UI el usuario **desbloquea** la señal premium (gesto tipo deslizar / confirmar) y eso cuesta **−50 DP**; eso **no** es lo mismo que decir “me comprometo con este pick” en flujo estándar o el registro operativo del pick.

**Decisión:** El movimiento de ledger `pick_premium_unlock` (**−50 DP**) corresponde siempre al **desbloqueo** de la señal premium del snapshot, no a un cargo genérico por “tomar” el pick. El contrato técnico actual puede aplicar ese cargo en el mismo `POST /bt2/picks` que crea la fila cuando el desbloqueo y la creación van unidos en un paso de producto; si en el futuro se separan en dos acciones, el **significado contable** del `reason` no cambia.

**Consecuencia para copy FE:** alinear mensajes de bóveda con “desbloquear” para el coste en DP; reservar “tomar / en juego” para **US-FE-033** (compromiso) sin confundirlo con el descuento −50.

---

## D-05-005 — HTTP 402 vs 422 en desbloqueo premium (`POST /bt2/picks`)

**Contexto:** El FE debe distinguir “saldo DP insuficiente para **desbloquear** señal premium” de errores de validación de body o de estado del evento.

**Decisión:**

| Código | Cuándo | Cuerpo |
|--------|--------|--------|
| **402** | El `event_id` califica como premium en `bt2_daily_picks` del día y `SUM(delta_dp)` del usuario **< 50** antes del cargo. | Objeto JSON en `detail`: `code` = `dp_insufficient_for_premium_unlock`, `message`, `requiredDp`, `currentDp`. |
| **422** | `odds_accepted` ≤ 1, `stake_units` ≤ 0, evento no `scheduled`, u otros errores de reglas de negocio no monetarios. | Detalle FastAPI estándar (`detail` string o lista de errores de validación). |
| **404** | Evento inexistente. | `detail` string. |
| **409** | Pick duplicado abierto mismo evento/mercado/selección. | `detail` string. |

**Nota:** El **−50 DP** sigue siendo `reason = pick_premium_unlock` (D-05-004); no usar copy de “toma” para este cargo.

---

*Más entradas D-05-00n según cierre de implementación.*
