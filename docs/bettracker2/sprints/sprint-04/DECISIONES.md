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
