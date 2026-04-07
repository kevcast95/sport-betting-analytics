# Sprint 04 — DECISIONES

> Trade-offs arquitectónicos tomados durante la implementación.

---

## D-04-001: PnL en unidades, bankroll_amount como unidades numéricas

**Decisión:** `bt2_picks.pnl_units` se calcula en unidades (stake × (odds-1) para won, -stake para lost). `bt2_users.bankroll_amount` se actualiza sumando `pnl_units` directamente.

**Razón:** La conversión unidades → COP requiere conocer el valor de la unidad en el momento del pick (bankroll × risk_pct / 100), pero ese valor cambia con cada operación. Para Sprint 04, bankroll_amount funciona como "balance en unidades de referencia". El FE es responsable de mostrar la representación en COP si tiene el contexto del bankroll inicial y el stake%.

**Trade-off:** No es conversión fiel a COP en la BD. Corrección en Sprint 05 si se define `unit_value_cop` fijo por sesión.

---

## D-04-002: Determinación de outcome por market/selection con strings

**Decisión:** `_determine_outcome` usa matching de strings (`MATCH WINNER`, `1X2`, `OVER`, `UNDER`) para soportar los mercados del CDM. Selecciones: `1/Home/home`, `X/Draw/Empate`, `2/Away/away`, `Over N.N`, `Under N.N`.

**Razón:** El CDM usa nomenclatura Sportmonks libre (`"Match Winner"`, `"Goals Over/Under"`). No hay enum cerrado aún.

**Trade-off:** Fragil si Sportmonks cambia nombres. Mitigación: US-DX-Sprint05 para normalizar mercados a enum cerrado en bt2_picks.

---

## D-04-003: pick.status='scheduled' requerido para crear pick

**Decisión:** `POST /bt2/picks` valida que `bt2_events.status = 'scheduled'`. El CDM tiene 79 eventos scheduled (del rango 2023-2025). Para pruebas reales se pueden usar esos eventos.

**Razón:** Regla de dominio del protocolo conductual — solo se pueden tomar picks en partidos que aún no han ocurrido.

**Trade-off:** Los eventos del CDM son históricos (casi todos finished). Sprint 05 debe agregar ingesta de fixtures futuros vía atraco incremental o API en tiempo real.

---

## D-04-004: operating_day_key basado en timezone del usuario

**Decisión:** `operating_day_key` se calcula como `date.today()` en la timezone configurada en `bt2_user_settings.timezone` (default `America/Bogota`).

**Razón:** Un usuario en Bogotá y uno en Madrid tienen días operativos diferentes. La clave del día es la fecha local del usuario.

**Trade-off:** Si el usuario cambia su timezone, las sesiones anteriores quedan con claves de la timezone antigua. Aceptable para MVP.

---

## D-04-005: bt2_user_settings auto-creado en register y en GET /user/settings

**Decisión:** Los settings se crean con defaults en dos momentos: (a) al registrar el usuario y (b) si llaman `GET /user/settings` y aún no existe la fila (`_ensure_user_settings`).

**Razón:** Doble safety net. Si un usuario pre-Sprint04 nunca llama register de nuevo, igual obtiene sus settings al primer acceso.

**Trade-off:** Doble insert con ON CONFLICT DO NOTHING es idempotente, sin costo.

---

## D-04-006: Grace period como timestamptz en BD

**Decisión:** `bt2_operating_sessions.grace_until_iso` se guarda como `TIMESTAMPTZ` en PostgreSQL (no como string). En la respuesta JSON se serializa como ISO 8601.

**Razón:** Permite comparaciones de tiempo nativas en SQL para futuros checks de gracia.

---

## D-04-007: picks sin evento scheduled en CDM actual

**Decisión:** Para testing de picks en el entorno actual (fixtures todos históricos), se acepta usar eventos con status='scheduled' (79 disponibles en CDM). En producción el atraco incremental alimentará eventos futuros reales.

**Trade-off:** No es posible testear el flujo completo pick→settle con datos 100% reales hasta que haya fixtures scheduled recientes. Mitigación documentada en QA_CHECKLIST.md.

---

## D-04-008: fetch_upcoming — single-pass paginado, filtro en Python

**Decisión:** `fetch_upcoming.py` descarga TODOS los fixtures del rango en una sola pasada paginada (`/v3/football/fixtures/between/{start}/{end}`) y filtra por `active_league_ids` en Python, en lugar de hacer 1 request por liga con el parámetro `filters=leagueIds:{id}`.

**Razón:** La API de Sportmonks ignora el parámetro `filters=leagueIds` en el endpoint `between`, devolviendo siempre todos los fixtures del rango sin importar el filtro. Hacer 27 requests con filtros ignorados consumiría 27× los créditos sin beneficio. El enfoque del `sportmonks_worker.py` (fetch-all + filter-Python) es el correcto para esta API.

**Consecuencia:** El costo por ejecución es ~9-15 requests (páginas del rango 48h) en lugar de 27.

---

## D-04-009: bt2_daily_picks snapshot — ventana del día local del usuario

**Decisión:** El snapshot de picks diarios (`_generate_daily_picks_snapshot`) busca eventos con `kickoff_utc` entre `hoy 00:00 tz_usuario` y `mañana 00:00 tz_usuario` (convertido a UTC), no en UTC directo.

**Razón:** Un usuario en Bogotá (UTC-5) espera ver los partidos de "su día", no los del día UTC. Si hay un partido a las 23:00 UTC (18:00 Bogotá), es un partido de hoy para él. Si es a las 02:00 UTC del día siguiente (21:00 Bogotá del día anterior), también es su partidos del día operativo previo.

**Trade-off:** Requiere convertir fechas con `ZoneInfo`. Fallback a UTC si el timezone del usuario es inválido.

---

## D-04-010: labels de odds — normalización multi-formato en vault/picks

**Decisión:** Las consultas de odds en `GET /bt2/vault/picks` usan `lower(o.market) IN ('1x2', 'match winner', 'full time result', 'fulltime result')` y selecciones `IN ('1', 'Home')` / `IN ('X', 'Draw')` / `IN ('2', 'Away')` con LIKE como fallback.

**Razón:** El CDM histórico (Atraco) almacena market como `'1X2'` y selections como `'1'`, `'X'`, `'2'`. Los fixtures nuevos de `fetch_upcoming.py` pueden tener market_description `'Match Winner'` o `'Full Time Result'` con selections `'Home'`, `'Draw'`, `'Away'`. El query debe soportar ambos formatos para no mostrar odds vacíos.

**Trade-off:** Query más verboso. Normalización completa en Sprint 05 si se unifica market/selection en el CDM.

---

## D-04-011: Economía de Discipline Points (DP) — escala UX y proporciones canónicas

**Decisión:** Los movimientos de DP que se persisten en `bt2_dp_ledger` usan **enteros múltiplos de 5 o de 10** (según el tipo de evento), manteniendo las **mismas proporciones relativas** que la primera implementación de settle en Sprint 04 (**ganar la jugada : perder la jugada = 2 : 1** en DP de recompensa por registrar el proceso).

**Valores canónicos acordados para alinear BE + FE + copy:**

| Evento (concepto) | `reason` sugerido | Δ DP | Nota |
|-------------------|-------------------|------|------|
| Liquidación pick — resultado **won** | `pick_settle` | **+10** | Múltiplo de 10; **2×** el de lost (misma razón 2:1 que +2/+1 inicial). |
| Liquidación pick — resultado **lost** | `pick_settle` | **+5** | Múltiplo de 5. Recompensa por **disciplina de registro**, no por acierto. |
| Liquidación pick — **void** / push | `pick_settle` | **0** | Sin cambio. |
| Desbloqueo / toma pick **premium** (coste) | `pick_premium_unlock` *(o nombre cerrado en US-DX)* | **−50** | Múltiplo de 10; el coste debe **doler** frente a ganancias típicas +5/+10 por liquidación. |
| Onboarding fase A (abono único) | `onboarding_welcome` *(servidor cuando exista)* | **+250** | Múltiplo de 10; hoy solo FE; BE debe reflejarlo en ledger cuando se centralice. |
| Penalización — estación sin cerrar (tras gracia) | `penalty_station_unclosed` *(servidor cuando exista)* | **−50** | Alineado a FE actual; múltiplo de 10. |
| Penalización — picks sin liquidar (tras gracia) | `penalty_unsettled_picks` *(servidor cuando exista)* | **−25** | Múltiplo de 5. |

**Razón de producto (UX + backend):**  
- **Múltiplos de 5 y 10:** el usuario percibe **progreso legible** (decenas, quincenas) sin “centavos de DP”; al mismo tiempo el **coste** de abrir premium (−50) y las **recompensas** por liquidar (+5 / +10) quedan en **la misma escala**, así la dimensión cambia respecto a +2/+1 pero **no la lógica económica** (premiar consistencia, cobrar decisiones caras).  
- **Proporción 2:1** se conserva respecto al diseño ya codificado en `bt2_router` (+2 won / +1 lost): es un **cambio de escala** (×5), no de política.

**Acción técnica:** Actualizar `POST /bt2/picks/{id}/settle` para usar **+10 / +5 / 0** en lugar de +2 / +1 / 0; documentar `reason` en OpenAPI; FE y textos de tours deben dejar de asumir **+25** plano por liquidación y reflejar **+10 / +5** según resultado (US-FE integración + US-FE-029 copy).

**Trade-off:** Saldo histórico de usuarios de prueba que ya tengan ledger con +2/+1 queda en escala vieja hasta migración o “reset” de entorno; aceptable en dev.

---

## D-04-FE-001: outcomeToScores en modo trust — limitación PUSH

**Decisión:** `settleApiPick` en `useTradeStore.ts` usa `outcomeToScores()` para derivar `result_home`/`result_away` del outcome local (PROFIT/LOSS/PUSH). Para PUSH → `{0, 0}`, que el backend puede interpretar como `lost` en mercados 1X2 o totales.

**Razón:** El FE no tiene los scores reales; en "trust mode" el usuario declara el outcome sin verificación externa. El mapeo PUSH→0:0 es la aproximación más segura (partido empatado o nulo).

**Limitación documentada:** Para mercados Over/Under, 0:0 puede no representar un void auténtico. Sprint 05 debe exponer un campo `result_type` en la API de settle (`'won'|'lost'|'void'`) para eliminar la ambigüedad.

---

## D-04-FE-002: Copy de DP — terminología en UI

**Decisión (US-FE-029):** Toda la UI usa "Resultado neto" en lugar de "PnL" en textos visibles al usuario (páginas, modales, confirmaciones). "PnL" se mantiene en código interno (variables, comentarios técnicos, libs). Los tours y modales de onboarding reflejan **+10 DP (ganancia) / +5 DP (pérdida)** — no "+25 DP" plano.

**Razón:** "PnL" es jerga financiera anglosajona; el producto está en español. La distinción +10/+5 comunica que el protocolo recompensa el proceso sin importar el resultado.

**Campos solo locales (sin sync BE en Sprint 04):** `reflection` (campo libre en settlement), `bookDecimalOdds` (cuota capturada en casa). Ambos se persisten en el ledger local pero no se envían al servidor. Sprint 05 puede añadir estos campos a `POST /bt2/picks/{id}/settle`.

---

## D-04-FE-003: Drift de DP entre FE y BD en flujos sin soporte backend aún

**Decisión (US-FE-030, T-121):** Las siguientes detracciones de DP se aplican **localmente** en el FE con `incrementDisciplinePoints()` pero **no se registran en `bt2_dp_ledger` del servidor** hasta que el BE las implemente:

| Evento | Δ DP local | Backend pendiente |
|--------|-----------|------------------|
| Desbloqueo pick premium (`takeApiPick`) | −50 | `reason: 'pick_premium_unlock'` — Sprint 05 |
| Penalización estación sin cerrar | −50 | `reason: 'penalty_station_unclosed'` — Sprint 05 |
| Penalización picks sin liquidar | −25 | `reason: 'penalty_unsettled_picks'` — Sprint 05 |

**Comportamiento actual:** Tras la deducción local, el FE llama `syncDpBalance()` (GET /bt2/user/dp-balance). Como el servidor no registró la deducción, retorna el saldo pre-deducción, restaurando el valor en pantalla. El usuario ve el saldo del servidor (más alto) en lugar del localmente penalizado.

**Trade-off:** El chip de DP muestra siempre el saldo del servidor (fuente de verdad), no una estimación local potencialmente errónea. Cuando el BE implemente los tres eventos anteriores, el `syncDpBalance()` post-deducción devolverá el valor ya reducido por el servidor y todo coincidirá.

**Acción pendiente BE:** Implementar `POST /bt2/session/close` con cálculo de penalización por estación sin cerrar, y `POST /bt2/picks/penalize-unsettled` (o integrar en `checkDayBoundary`). Para premium unlock: añadir registro en `bt2_dp_ledger` cuando se crea el pick (en `POST /bt2/picks`).

---

## D-04-012: Modelo de 7 opciones diarias — picks + parlays (backlog Sprint 06)

**Decisión de producto acordada en Sprint 04:**

La bóveda del usuario expone hasta **7 opciones por día operativo**:

| # | Tipo | Acceso | Sprint |
|---|------|--------|--------|
| 1–3 | Picks simples `standard` | Libre | Sprint 04 ✅ |
| 4–5 | Picks simples `premium` | Requiere saldo ≥ `dp_unlock_premium_threshold` (default 50 DP) | Sprint 04 ✅ |
| P1 | Parlay 2-legs | Milestone permanente + costo diario −25 DP | Sprint 06 |
| P2 | Parlay 3-legs | Milestone permanente + costo diario −50 DP | Sprint 06 |

**Reglas de los parlays (a implementar en Sprint 06):**
- Los parlays se construyen combinando picks del snapshot del día. P1 usa 2 picks, P2 usa 3. DSR elige cuáles combinan estadísticamente mejor (Sprint 05 = DSR genera picks con edge; Sprint 06 = DSR propone combinaciones).
- Máximo 2 parlays activos por día (1 de 2-legs + 1 de 3-legs). Sin excepción aunque el usuario tenga DP de sobra.
- Los legs de parlay se limitan a **2 y 3 máximo** en MVP. 4+ legs queda fuera del alcance inicial (varianza excesiva, contraria al protocolo conductual).

**Razón:** La bóveda no debe ser un casino de combinaciones infinitas. El límite diario duro es parte del protocolo conductual — el acceso a herramientas más potentes requiere demostrar disciplina, no solo tener saldo DP.

---

## D-04-013: Milestone de desbloqueo de parlays + tabla canónica DP extendida (backlog Sprint 06)

**Desbloqueo permanente (una sola vez):**

El feature de parlays se activa para un usuario cuando se cumplen **ambas condiciones simultáneamente** al abrir sesión (`POST /bt2/session/open`):

| Condición | Umbral |
|-----------|--------|
| DP lifetime acumulados (`SUM(delta_dp)` histórico) | ≥ 200 DP |
| Días operativos activos (`COUNT DISTINCT operating_day_key`) | ≥ 10 días |

Al cumplirse: `bt2_user_settings.parlays_unlocked = true`, `parlays_unlocked_at = now()`. La respuesta de `POST /bt2/session/open` incluye `parlays_just_unlocked: true` (solo la primera vez). El FE muestra modal explicativo con reglas de parlays.

**Costo diario por uso:**

| Acción | `reason` en ledger | Δ DP |
|--------|-------------------|------|
| Activar parlay 2-legs | `parlay_activation_2l` | −25 |
| Activar parlay 3-legs | `parlay_activation_3l` | −50 |

Si el usuario no tiene saldo suficiente, el parlay aparece visualmente bloqueado en la bóveda con mensaje "Necesitas X DP para activar este parlay hoy".

**Tablas nuevas requeridas en Sprint 06:**
- `bt2_parlays`: `id, user_id, operating_day_key, status, total_odds, stake, pnl, created_at, settled_at`.
- `bt2_parlay_legs`: `id, parlay_id FK, event_id FK, market, selection, odd_value, leg_order`.
- `bt2_user_settings` — nuevas columnas: `parlays_unlocked bool default false`, `parlays_unlocked_at timestamptz null`, `dp_cost_parlay_2legs int default 25`, `dp_cost_parlay_3legs int default 50`.

**Tabla canónica DP completa (D-04-011 extendida con parlays):**

| Evento | `reason` | Δ DP |
|--------|---------|------|
| Liquidación won | `pick_settle` | +10 |
| Liquidación lost | `pick_settle` | +5 |
| Liquidación void | `pick_settle` | 0 |
| Activar parlay 2-legs | `parlay_activation_2l` | −25 |
| Activar parlay 3-legs | `parlay_activation_3l` | −50 |
| Desbloqueo pick premium | `pick_premium_unlock` | −50 |
| Onboarding único | `onboarding_welcome` | +250 |
| Penalización estación sin cerrar | `penalty_station_unclosed` | −50 |
| Penalización picks sin liquidar | `penalty_unsettled_picks` | −25 |

**Razón:** Documentar ahora evita contradicciones entre FE (tours, copy de DP), BE y el motor DSR cuando se implemente en Sprint 05-06. Todo movimiento futuro al ledger debe referenciar esta tabla.
