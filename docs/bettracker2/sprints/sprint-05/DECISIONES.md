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
| `pick_settle` | Liquidación de pick — disciplina de cierre |
| `session_close_discipline` | Recompensa por cerrar la estación |
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

## D-05-FE-001 — Implementación FE Sprint 05 (US-FE-031 … 033)

**Contexto:** Ledger DP, `POST /bt2/picks` con 402 premium, `operating-day/summary`, compromiso estándar vs desbloqueo premium.

**Decisión (FE):**

- **`GET /bt2/user/dp-ledger`:** sección en **Perfil** (`DpLedgerSection.tsx`); `reason` → copy vía `dpLedgerLabels.ts` (onboarding unificado D-05-003).
- **`POST /bt2/picks`:** `bt2PostPickRegister` parsea 402 + `detail`; sin `incrementDisciplinePoints` local por −50; `syncDpBalance` tras éxito o 402.
- **Penalizaciones gracia:** el cliente **no** aplica −25/−50 en `checkDayBoundary`; solo registra `penaltiesApplied` y `syncDpBalance`; cargos en `session/open` (BE).
- **Hidratación:** `useTradeStore.hydrateLedgerFromApi` en `useAppInit`, al cargar bóveda y tras liquidación API; **Daily Review** muestra bloque **servidor** con `GET /bt2/operating-day/summary` además de tarjetas **Local** (ledger persistido).
- **US-FE-033:** estándar y premium exigen fila en `takenApiPicks` antes de ver contenido; slide premium = desbloqueo (−50 servidor); slide estándar = compromiso sin DP; liquidación bloqueada sin `POST` previo (redirect a bóveda).

---

## D-05-006 — Santuario: crecimiento patrimonial y caída máxima sin datos ficticios (US-FE-034)

**Contexto:** La tarjeta “Patrimonio total” mostraba **+14.2%** y **−4.2%** como literales, sugiriendo historial que el usuario podría no tener.

**Decisión:** Esos indicadores **solo** pueden mostrarse si hay **fuente calculable** (p. ej. serie desde ledger + bankroll confirmado, o endpoint agregado acordado). Si no hay datos suficientes (definición mínima: **cero liquidaciones** en ledger persistido / API, o bankroll sin variación registrada — ajustar en implementación con comentario en código), mostrar **“—”** o **0%** con microcopy del tipo *“Sin historial aún”* / *“Se calculará con tus liquidaciones”*. **Prohibido** reintroducir constantes decorativas en UI.

---

## D-05-007 — Misiones diarias y tarjeta de “estado” sin simulación (US-FE-034)

**Contexto:** Barra al **84%** y viñetas con colores eran **mock**; no existía definición de “misión” ni API.

**Decisión:** Hasta que exista **US-BE** / contrato de misiones (si aplica), el bloque debe (a) **no** mostrar porcentaje inventado; (b) usar **barra 0%** + texto *“Misiones en definición”* o **ocultar** el bloque dejando solo “Riqueza de carácter”; (c) la tarjeta “Estado: óptimo…” **no** debe afirmar salud conductual fija: usar copy **neutral** (*“Completa el diagnóstico y tu primera sesión para ver tu estado.”*) o enlazar a diagnóstico si `hasCompletedDiagnostic` es false.

---

## D-05-008 — Perfil: “posición global” sin fórmula decorativa (US-FE-034)

**Contexto:** `Top (100 − DP/50)%` imitaba un ranking global sin datos reales.

**Decisión:** Eliminar la fórmula. Sustituir por **“—”** o copy *“Ranking global no disponible en MVP”*. Si en el futuro BE expone percentil, la UI debe consumir **solo** ese campo y documentar el contrato en **US-DX**.

---

## D-05-009 — Bóveda: preview, CTAs y hora del evento (US-FE-034)

**Contexto:** Placeholder “Contenido conductual protegido” ocultaba la lectura del modelo; faltaba hora local de kickoff en contrato; se pidieron **Detalle** + **Tomar** y **Liquidar** cuando el pick está tomado.

**Decisión:**

| Tema | Decisión |
|------|----------|
| Preview | Mostrar **extracto** de `traduccionHumana` (p. ej. 2–3 líneas) en estado bloqueado; **Detalle** abre vista completa (modal o ruta dedicada). |
| CTAs | **Seleccionar/Tomar** + **Detalle** antes de tomar; con pick **tomado**, mostrar **Liquidar** (y mantener acceso a detalle si producto lo quiere). |
| Etiqueta | Badge visible **“En juego”** / **“Tomado”** cuando corresponda al store/API. |
| `isAvailable` | Si `false`, card **apagada** y **sin** CTA de tomar. |
| Hora | **US-BE-019 cerrado:** en cada ítem de bóveda el BE expone **`kickoffUtc`** (ISO UTC; `""` si NULL en CDM). El FE **debe** mostrar en **preview de card** la hora legible en **TZ del usuario** (p. ej. `America/Bogota` hasta settings); si `kickoffUtc` está vacío, mostrar **“—”** y no inferir desde título. |
| Estado evento (bandera) | El BE expone **`eventStatus`** (crudo CDM, p. ej. `scheduled`, `inplay`, `finished`) y **`isAvailable`** (`true` solo si evento programado disponible para reglas actuales). El FE debe **identificar a simple vista** no tomable / terminado: card **apagada** + **etiqueta** explícita (*No disponible*, *Finalizado*, *En juego* según `eventStatus` + `isAvailable`) — **D-05-019** refuerza si la opacidad sola no basta. |

---

## D-05-010 — Bóveda: hora como filtro, CTAs en línea, **Detalle** = settlement en dos fases (US-FE-034)

**Contexto:** El PO reforzó que sin hora no se puede decidir si el pick sigue vigente; la disposición vertical de **Detalle** y **Tomar pick** genera jerarquía visual indeseada; “Detalle” no debe ser un modal genérico sino el **mismo flujo de liquidación** en otro momento del ciclo de vida.

**Decisión:**

1. **Hora y vigencia del evento**  
   - La **hora de inicio** en TZ del usuario es **dato obligatorio** en la experiencia (cuando **US-BE-019** lo exponga; hasta entonces, máximo esfuerzo con lo que devuelva el API sin inventar).  
   - **Filtro de producto:** si el partido **ya inició**, no debe ofrecerse “Tomar” como si fuera pre-partido sin fricción: o **bloqueo** con mensaje claro, o **solo revisión/liquidación** según regla cerrada en implementación (documentar en comentario de código). Si el evento **ya terminó** (servidor `is_available === false` y/o estado explícito de evento cuando exista), la card debe verse **apagada/opaca** y **sin** tomar nuevo pick.  
   - Coherencia: **`isAvailable`** del BE manda; el FE añade comparación temporal **solo** si el contrato define instante de inicio y política acordada con BE.

2. **Layout de botones en la card**  
   - **Detalle** y **Tomar pick** (o **Seleccionar pick**) van en la **misma fila**, mismo peso visual (p. ej. grid 1fr 1fr o flex), **sin** apilar uno encima del otro en viewport móvil estándar. Solo en breakpoint muy estrecho se puede permitir wrap si queda documentado en US/TASK.

3. **Detalle = ruta de settlement, dos momentos**  
   - **Una sola pantalla / flujo** (misma ruta que hoy usa liquidación, p. ej. `/v2/settlement/:id`), con **fase** explícita en UI o por query/state:  
     - **Momento A — Revisión (pre-toma):** el operador valida si el pick tiene sentido. Debe mostrarse **toda la información necesaria** que permita el contrato: **hora de inicio**, **mercado** y **selección** (1X2 / home-away, over/under goles, corners, etc. **según campos disponibles** en `Bt2VaultPickOut` o ampliación **US-BE-019**), **cuota sugerida**, **texto del modelo** y **justificación** (`traduccionHumana` + cualquier campo BE añada). En esta fase la pantalla incluye CTA **Tomar** (misma acción que en la card).  
     - **Momento B — Liquidación (post-toma, evento cerrado):** misma pantalla orientada a **registrar resultado** cuando el evento haya terminado (flujo de liquidación actual).  
   - No duplicar una “vista detalle” paralela al settlement: **un solo código de pantalla** con variantes de copy y CTAs según fase.

4. **Gaps de contrato**  
   - Si faltan campos estructurados (p. ej. corners) para la fase A, **US-BE-019** debe ampliarse; el FE no rellena con texto libre inventado.

---

## D-05-FE-002 — US-FE-034 en FE (Santuario, Perfil, Bóveda)

**Contexto:** Cierre T-134–T-139 sin reintroducir mocks creíbles.

**Implementación:**

- **Santuario:** ROI y drawdown desde `ledgerAggregateMetrics` + `useTradeStore.ledger` si `ledger.length > 0`; si no, **—** y microcopy D-05-006. Misiones: barra **0%**, texto **en definición** D-05-007. Tarjeta estado: título/copy según `hasCompletedDiagnostic` + enlace a diagnóstico si aplica.
- **Perfil:** posición global **—** + “Ranking global no disponible en MVP” (D-05-008).
- **Bóveda:** `PickCard` — preview `traduccionHumana`, **Detalle** navega a **settlement** modo revisión (**D-05-010**); **Tomar** y **Detalle** **en la misma línea**; slide premium = desbloqueo; tomado → **Liquidar** vía mismo flujo settlement modo liquidación; badge **En juego**. `isAvailable === false` o evento terminado → apagado. Hora de inicio: contrato **`kickoffUtc`** + **`eventStatus`** (**US-BE-019**, **T-141**); el FE formatea en TZ usuario (T-139 / T-140).

---

## D-05-011 — Nombre canónico del instante de inicio en bóveda (US-BE-019)

**Decisión:** En JSON de `GET /bt2/vault/picks`, el campo es **`kickoffUtc`** (camelCase), string ISO 8601 en UTC. No se usa `eventStartsAtUtc` en el contrato para evitar duplicar semántica; cualquier referencia previa en texto FE a “eventStartsAtUtc” se interpreta como el mismo concepto que **`kickoffUtc`**.

**Razón:** Alineación con columna `bt2_events.kickoff_utc` y convención de datos deportivos.

---

## D-05-012 — DP por liquidación: **+10 por gestión** (won, lost y void) — enmienda D-04-011

**Contexto:** El PO reforzó que el valor del producto es **disciplina y gestión**, no premiar o castigar al operador según si el **modelo** acertó el resultado. La tabla **D-04-011** (`sprint-04/DECISIONES.md`) asignaba **+10** si `won`, **+5** si `lost` y **0** si `void`, manteniendo proporción 2:1 respecto a una escala anterior; en la práctica el usuario percibe **menos DP al perder** como un castigo por el acierto del modelo, no por su conducta.

**Decisión (producto):**

1. **Una sola recompensa de gestión al liquidar** un pick (registro honesto del cierre): **`pick_settle` → +10 DP** cuando el servidor clasifica el pick como **`won`**, **`lost`** o **`void`** (push / nulo contable), **siempre que** se inserte el movimiento de liquidación en `bt2_dp_ledger` con `reason = 'pick_settle'` (misma transacción que hoy).
2. **No** se introduce DP adicional “por tomar” el pick en esta decisión: el **+10** sigue ligado al **hecho de liquidar** (cerrar el ciclo operativo), no al stake ni a la apertura en `POST /bt2/picks`.
3. **Palanca conductual** que compensa el “regalo” percibido: las **penalizaciones por incumplimiento de protocolo** se mantienen (**D-04-011 / US-BE-017**): p. ej. **−50** `penalty_station_unclosed`, **−25** `penalty_unsettled_picks`, **−50** `pick_premium_unlock` donde aplique. El operador puede **perder neto** si no cierra el día o no liquida a tiempo. La **simetría positiva** al cerrar el día (**+15 o +20 DP**) se define en **D-05-014** / **US-BE-021** — hasta aprobarla e implementarla, la economía diaria puede seguir sintiéndose desbalanceada frente a **dos desbloqueos premium el mismo día** (−50 cada uno, p. ej. **−100 en total**).

**Implicaciones BE:** `POST /bt2/picks/{id}/settle` debe asignar `dp_earned = 10` para los tres outcomes (`won`, `lost`, `void`) e insertar ledger cuando `dp_earned > 0` (o siempre +10 con idempotencia ya garantizada por “pick ya liquidado” → 409). Ajustar tests, OpenAPI si documenta valores, y comentarios que citaban +5/+0.

**Implicaciones FE:** Copy de tours, toasts de liquidación, agregados locales (`ledgerAnalytics`, mocks, tests que asumían +5 en pérdida) y cualquier texto que dijera “+10 / +5 según resultado” → **+10 por completar la liquidación** (opcional: microcopy que distinga “gestión” vs “resultado del mercado” sin prometer más DP por ganar).

**Implicaciones DX:** El `reason` sigue siendo `pick_settle`; puede actualizarse **`reasonLabelEs`** en **D-05-003** / **US-DX-001** a algo del tipo *“Liquidación de pick — disciplina de cierre”* si producto lo aprueba.

**Trazabilidad:** **US-BE-020**, **US-FE-035**, tareas **T-142–T-144** en `TASKS.md`.

**Enmienda explícita:** Al cerrar implementación, actualizar la **tabla D-04-011** en `docs/bettracker2/sprints/sprint-04/DECISIONES.md` (filas de liquidación won/lost/void) para que coincida con esta decisión y no queden dos fuentes contradictorias.

**Relación con otras decisiones del mismo paquete:** La **simetría recompensa / penalización** al **cerrar el día operativo** se trata en **D-05-014** (pendiente numerario PO). El **detalle de pick ya liquidado** y la **liquidación dual** + **bankroll emulado** enlazan con **D-05-013**, **D-05-015** y **D-05-016**.

---

## D-05-013 — Revisión visual (img): **ficha / Detalle** del pick **liquidado** → **settlement** (lectura), no rebote a bóveda

**Contexto:** En la revisión de pantallas (img5–7) el PO dejó claro que la **ficha completa** del pick no debe “desaparecer” tras liquidar: desde la **card en bóveda**, el CTA **Detalle** (o equivalente “ver ficha completa”) debe llevar al operador al **mismo destino de navegación** que antes del cierre — es decir, la **ruta de settlement** acordada (p. ej. `/v2/settlement/:pickId`) — donde ya se mostraban revisión y liquidación, **aunque el pick esté liquidado**. Eso **no** es una pantalla distinta y opaca a la bóveda: es **la misma pantalla / mismo flujo**, en **modo solo lectura** (sin re-liquidar salvo **US-BE-022**).

**Problema actual:** **`SettlementPage`** puede tratar el pick liquidado como “cerrado” y forzar **`Navigate` a `/v2/vault`**, de modo que quien pulsa **Detalle** en la card **no** ve la ficha: solo vuelve a la lista. Lo mismo afecta deep links y enlaces desde ledger.

**Decisión (producto):** Para picks **ya liquidados**, la ruta de **settlement** debe renderizar la **ficha completa** (mercado, selección, cuota, resultado, PnL, reflexión si aplica en cliente) en **solo lectura**; **prohibido** como comportamiento por defecto sustituir eso por un salto único a **`/v2/vault`**. La bóveda (**`PickCard`**) y el libro mayor deben enlazar a esa misma ruta.

**Trazabilidad:** **US-FE-036**, **T-145**.

---

## D-05-014 — Recompensa DP por **cerrar el día** (estación) — propuesta +15 / +20 *(pendiente aprobación PO)*

**Contexto:** Con **D-05-012** (+10 por pick liquidado en won/lost/void), un día “bueno” con **5 picks** liquidados aporta **hasta +50 DP** de gestión de picks. En paralelo, el snapshot diario contempla **hasta 2 picks premium**; **cada** desbloqueo cuesta **−50 DP** (**D-05-004** / `pick_premium_unlock`). **Ejemplo ilustrativo:** si el operador desbloquea **los dos premium el mismo día**, el coste acumulado es **−50 + −50 = −100 DP** — no existe un cargo único de “100”; es la **suma de dos cargos de 50**. **No cerrar** la estación dispara **−50** (`penalty_station_unclosed`). Esa asimetría percibida (mucho gasto en premium frente a techo de +50 por liquidaciones + ausencia de premio explícito al cerrar) motiva compensar con **D-05-014**.

**Decisión (producto — borrador):** Introducir una **recompensa explícita por cierre correcto del día** (`POST /bt2/session/close` exitoso, sin sustituir otras reglas): **+15 o +20 DP** (el PO puede fijar un valor único distinto del default de implementación), con `reason` canónico **`session_close_discipline`** (**US-DX-001** / **D-05-003**), **idempotente por sesión** (`reference_id = session.id`).

**Implementación Sprint 05 (valor y elegibilidad — D-05-018):** hasta que el PO sustituya explícitamente esta entrada, el BE usa **+20 DP** y **sí acredita** aunque existan picks abiertos al cerrar; la penalización por picks sin liquidar sigue el flujo de **gracia** y **`penalty_unsettled_picks`** ya definido (**US-BE-017**), no se mezcla con el acto de cerrar la estación.

**Implicaciones:** Tabla **D-04-011** / economía global; tours y **Daily Review** deben mencionar el cierre como **ganancia potencial**, no solo como ausencia de multa.

**Trazabilidad:** **US-BE-021** (persistencia + reglas), **US-FE-037** (copy, Daily Review, tours, toasts tras cierre), **T-146**, **T-147**.

---

## D-05-015 — **Liquidación dual:** validador automático vs declaración del operador

**Contexto:** El producto requiere **dos caminos** hacia el **mismo estado contable** de un pick: (a) un **validador periódico** (cron / feed oficial) que **propone o cierra** resultado según fuentes acordadas; (b) el **operador** que **gestiona y declara** el resultado cuando revisa en otro momento o cuando **no coincide** la ejecución del validador con su lectura.

**Estado técnico hoy:** `POST /bt2/picks/{id}/settle` recibe **marcador**; el servidor **recalcula** `won`/`lost`/`void` con `_determine_outcome`. **`GET /bt2/meta`** expone `settlementVerificationMode` (`trust` / `verified`) pero **no** hay modelo de **disputa**, **bitácora de fuente** (quién cerró: sistema vs usuario), **ventana de revisión** ni **reglas de precedencia** si ambos difieren.

**Decisión (producto — alcance a cerrar en US-BE-022):**

1. Documentar **fuentes de verdad** posibles: `system` | `user_trust` | `user_override` *(nombres internos a validar en DX)*.
2. Definir **quién gana** si el validador y el usuario discrepan (p. ej. override solo en modo trust, o flujo de “disputa” con auditoría).
3. **Trazabilidad en ledger / pick:** campos o tabla de eventos sin duplicar PnL hasta que producto cierre reglas (evitar doble movimiento de bankroll).
4. **Impacto en bankroll:** cualquier cierre (automático o manual) debe seguir el **modelo contable** de **D-05-016**; si el validador cierra primero y el usuario corrige, la **corrección** debe generar **ajuste** explícito (delta bankroll + delta DP si aplica), no solo sobrescritura silenciosa.

**Trazabilidad:** **US-BE-022**, **US-FE-038**, **US-DX** (ampliación catálogo `reason` / enums de fuente), **T-148** (BE), **T-149** (FE flujos / estados).

---

## D-05-016 — **Bankroll emulado:** modelo contable y fuente de verdad (trust / verified)

**Contexto:** El bankroll del protocolo es **emulado pero equivalente en intención** al patrimonio que el usuario gestiona en su casa de apuestas. Hoy el **ajuste servidor** ocurre **principalmente al liquidar** (`bankroll_amount += pnl`). El envío de **`marketClass`** (p. ej. `CDM`) como `market` en `POST /bt2/picks` puede hacer que `_determine_outcome` devuelva **void**, con **PnL y DP de liquidación en cero**, rompiendo la coherencia percibida con el riesgo real. No hay especificación cerrada de **reserva al tomar** el pick (stake comprometido) frente a **realización al liquidar**.

**Decisión (producto — marco a implementar en US-BE-023 + US-FE-039):**

1. **Momentos de mutación** del saldo emulado: p. ej. **(A)** opcional **reserva** al registrar pick tomado; **(B)** liquidación ajusta por PnL; **(C)** coherencia de **unidades** (stake_units vs COP en UI) documentada en un solo lugar.
2. **Mercado canónico en BT2:** el cuerpo de `POST /bt2/picks` debe transportar un **mercado settle-able** alineado a `_determine_outcome` **o** el settle debe aceptar **outcome declarado** en modo trust (**depende de US-BE-022**).
3. **Una sola fuente de verdad:** servidor manda para saldo y ledger; FE **reconcilia** (`syncFromApi`, `reconcileToExchangeBalance`) sin inventar deltas persistentes.
4. **Relación con validador (D-05-015):** un cierre automático debe usar el **mismo** modelo contable que el manual para no bifurcar bankroll.

**Trazabilidad:** **US-BE-023**, **US-FE-039**, **T-150**, **T-151** (desglose BE/FE en TASKS).

---

## D-05-017 — Coordinación **BA/PM Frontend** ↔ **BA/PM Backend** (Sprint 05, paquete D-05-012 … D-05-016)

**Contexto:** Las **US-FE-035 … US-FE-039** fueron redactadas con foco producto/UX; el **BA/PM Backend** **completó** la rectificación documental de **US-BE-020 … US-BE-023**, **US-BE-018 §9** (ex **US-BE-024**) y las **tareas T-143, T-146, T-148, T-150, T-152** en [`US.md`](./US.md) y [`TASKS.md`](./TASKS.md).

**Decisión (proceso):**

1. **Fuente de verdad conjunta:** [`US.md`](./US.md) — tabla **Matriz US-FE → US-BE** (bloque Economía / protocolo) + §**11** en cada US-FE + cuerpo completo **US-BE-020…023**.
2. **Documento de entrada para BA BE:** [`HANDOFF_BA_PM_BACKEND_SPRINT05.md`](./HANDOFF_BA_PM_BACKEND_SPRINT05.md) — checklist de revisión y orden sugerido.
3. **DECISIONES D-05-012 … D-05-016** definen **intención de producto**; el BA BE añade o ajusta **DECISIONES** solo si hay trade-off técnico (p. ej. idempotencia, ACL, límites de query) que el PO deba ratificar.
4. **Ex US-BE-024 (lectura pick liquidado):** fusionada en **US-BE-018** §9; la tarea **T-152** referencia **US-BE-018** (extensión `PickOut` + `GET` lista/detalle).

**Rol FE (mandato [`front_end_agent.md`](../agent_roles/front_end_agent.md)):** no implementar BE; solo mantener **US-FE**, **TASKS** etiquetadas FE y este puente documental hasta el handoff BE.

---

## D-05-018 — Cierre de estación: valor **N** implementable y elegibilidad con picks abiertos

**Contexto:** **D-05-014** deja abierto el numerario (+15 vs +20) y la política si hay **picks abiertos** al cerrar.

**Decisión técnica (implementación Sprint 05 — reversible por PO):**

1. **Constante servidor** `SESSION_CLOSE_DISCIPLINE_REWARD_DP = 20` hasta que el PO documente otro valor único en **D-05-014** (p. ej. +15); no hace falta migración de datos al cambiar solo la constante.
2. **Elegibilidad:** en el **primer** `POST /bt2/session/close` exitoso que pasa la sesión del día de `open` → `closed`, insertar **una** fila `bt2_dp_ledger` con `reason = session_close_discipline`, `delta_dp = +N`, `reference_id = session.id`, salvo que ya exista fila con ese par `(reason, reference_id)` (idempotencia).
3. **Picks abiertos:** **no** se bloquea la recompensa por `pending_settlements > 0`; el operador sigue sujeto a **`penalty_unsettled_picks`** según reglas de gracia ya implementadas al abrir día / cierre huérfano (**D-05-002**, **US-BE-017**).

**Trade-off:** Un usuario podría recibir **+N** por cerrar estación y, más tarde, **−25** por no liquidar tras gracia; el producto separa **gesto de cierre** de **cumplimiento de liquidaciones**. Si el PO prefiere **no** bonificar con picks abiertos, debe anular el punto 3 aquí y actualizar **US-BE-021**.

**Trazabilidad:** **US-BE-021**, **T-146**, **US-FE-037**.

---

## D-05-019 — Bóveda: datos del BE (hora + flags) y **refresco** al cambiar día operativo (persist FE)

**Contexto:** El backend filtra `GET /bt2/vault/picks` por **`operating_day_key` = hoy en TZ del usuario** y devuelve, por pick, entre otros: **`kickoffUtc`**, **`eventStatus`**, **`isAvailable`**, **`operatingDayKey`** (debe coincidir con el día del snapshot). La página incluye **`generatedAtUtc`**. Aun así, el **cliente** persiste `apiPicks` y `picksLoadStatus` en storage encriptado: si `picksLoadStatus !== 'idle'` al abrir la app un **nuevo día**, puede **no** ejecutarse `loadApiPicks()` y el usuario ve **picks del día anterior** aunque el API sería correcto.

**Contexto (producto):** La bóveda es **cartelera del snapshot** (`bt2_daily_picks`), **no** la lista de `bt2_picks` liquidados; **es esperable** que una ficha **siga visible** después de liquidar hasta que producto defina ocultarla o moverla — ver §4.

**Decisión:**

1. **Contrato BE (confirmado Sprint 05):** Hora de inicio = **`kickoffUtc`**; disponibilidad comercial = **`isAvailable`**; estado crudo del evento = **`eventStatus`**; coherencia esperada: `isAvailable === false` cuando el evento ya no admite “tomar” según reglas router (p. ej. no `scheduled`).  
2. **FE — obligatorio en preview:** mostrar **hora formateada** desde `kickoffUtc` cuando exista; badge o rótulo de **estado** derivado de **`eventStatus` + `isAvailable`** (no solo opacidad sin texto — cumplir pedido PO de “simple vista”).  
3. **FE — anti-stale:** al montar **`VaultPage`** (y opcional al recuperar foco de pestaña), si el **día operativo actual** del usuario (misma TZ que usa el BE, p. ej. vía util compartida o `operatingDayKey` esperado) **≠** `operatingDayKey` de los `apiPicks` persistidos (o lista vacía con `loaded`), **forzar** nueva petición `GET /bt2/vault/picks` (p. ej. reset de `picksLoadStatus` a `idle` o flag `vaultFetchKey`). Usar **`operatingDayKey`** del DTO o **`generatedAtUtc`** como señal; no confiar solo en “loaded”.  
4. **Cartelera vs liquidado:** mientras no exista US específica de “ocultar al liquidar”, el FE puede añadir badge **Liquidado** cuando el pick esté en **`settledPickIds`** / ledger y tomado, **sin** esperar que el BE quite la fila del vault.

**Trazabilidad:** **US-FE-034** (ampliación), **T-169** en [`TASKS.md`](./TASKS.md).

---

*Más entradas D-05-00n según cierre de implementación.*
