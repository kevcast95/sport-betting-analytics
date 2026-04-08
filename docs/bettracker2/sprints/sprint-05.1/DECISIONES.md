# Sprint 05.1 — Decisiones

## D-05.1-001 — RFB-09: desbloqueo premium y toma del pick son dos actos

**Contexto:** En código actual, el slider premium llama a `takeApiPick` → `POST /bt2/picks`, que en servidor crea fila en `bt2_picks` y aplica `pick_premium_unlock` −50 DP en la **misma** transacción (**US-BE-017**). `VaultPage` usa `takenApiPicks` como “desbloqueado”, y `PickCard` muestra badge **“En juego”** en ese estado. El PO requiere que el usuario **desbloquee** (paga visión premium) y **luego decida** si **toma** el pick.

**Decisión (producto):**

1. **Desbloquear** = autorización de contenido premium del snapshot + cargo **`pick_premium_unlock`** (−50 DP o coste vigente), **sin** equivaler a compromiso operativo “pick en juego”.
2. **Tomar** = acción explícita posterior que crea el registro operativo (**`POST /bt2/picks`** o equivalente) y habilita liquidación según reglas ya definidas (**US-FE-033**, **D-05-004**).
3. El servidor debe poder **auditar** ambos momentos (ledger + existencia o no de `bt2_picks` para ese evento/selección según reglas de idempotencia acordadas).

**Consecuencia técnica:** El diseño actual (un solo POST) es **insuficiente**; hace falta **US-BE-029** (nuevo endpoint o transacción desacoplada + persistencia de “unlocked sin pick”) y **US-FE-040** (estado UI y store: `premiumUnlockedIds` vs `takenApiPicks`). *(El id **US-BE-024** del S5 histórico está absorbido en **US-BE-018 §9**.)*

**Trazabilidad:** [`../../refinement_feedback_s1_s5/DECISIONES.md`](../../refinement_feedback_s1_s5/DECISIONES.md) **RFB-09**; **D-05-004** (significado contable del desbloqueo).

---

## D-05.1-002 — Forma técnica preferida: endpoint dedicado + flag en vault

**Contexto:** Para implementar **D-05.1-001** hace falta separar HTTP y persistencia sin ambigüedad.

**Decisión (PM + arquitectura ejecutable):**

1. Exponer **`POST /bt2/vault/premium-unlock`** con cuerpo mínimo (`vaultPickId` o id estable acordado con el CDM de ítems de bóveda).
2. Persistir en servidor el hecho de desbloqueo (tabla dedicada o diseño equivalente) para idempotencia y para **`GET /bt2/vault/picks`**: cada ítem premium lleva **`premiumUnlocked: boolean`** (nombre final en **US-DX-001-R1** / OpenAPI).
3. Ajustar **`POST /bt2/picks`** para no aplicar un segundo cargo `pick_premium_unlock` cuando ya exista unlock válido para ese ítem/día.

**Plan B (no preferido):** un solo `POST /bt2/picks` con flag `unlock_only` — solo si BE estima menor riesgo de regresión; en ese caso actualizar esta decisión en mismo archivo.

**Trazabilidad:** **US-BE-029**, **US-FE-040**, **T-170**; **D-05-005** (402).

---

## D-05.1-003 — Cabecera V2: sin «Actualizado ahora» decorativo; ayuda a la izquierda *(RFB-01, RFB-10)*

**Contexto:** Varias vistas repiten el label **«Actualizado ahora»** sin semántica clara y colocan **«Cómo funciona»** / tours con alineación distinta; los títulos y subtítulos redundan entre vistas.

**Decisión (producto):**

1. **Eliminar** el texto fijo **«Actualizado ahora»** (y equivalentes) en todas las vistas V2 del Búnker. No se introduce sustituto global salvo que en el futuro exista **timestamp real** ligado a un evento de sync explícito (fuera de alcance de esta decisión).
2. **Unificar** la zona superior de cada vista con un patrón común: **título** (y **subtítulo** opcional si aporta); fila de acciones con **bloque ayuda alineado a la izquierda** del contenedor de contenido y acciones secundarias de la vista a la **derecha** cuando existan.
3. **«Cómo funciona»:** control único reutilizable: **icono en círculo** (o `HelpCircle` equivalente) **a la izquierda** del texto **«Cómo funciona»**; área táctil adecuada; mismo componente en todas las vistas que abren tour/modal de ayuda.
4. **Identidad:** refuerzo en [`../../04_IDENTIDAD_VISUAL_UI.md`](../../04_IDENTIDAD_VISUAL_UI.md) §8 (tokens de cabecera).

**Trazabilidad:** [`../../refinement_feedback_s1_s5/DECISIONES.md`](../../refinement_feedback_s1_s5/DECISIONES.md) **RFB-01**, **RFB-10**; **US-FE-043** (`US.md`); **T-174–T-176**.

---

## D-05.1-004 — Bóveda: pick con toma bloqueada por inicio de evento *(RFB-07)*

**Contexto:** Cuando `takeBlockedAfterStart` es verdadero, `PickCard` muestra un párrafo largo que satura la card; el PO prefiere **opacidad reforzada**, **etiqueta corta** y, en escritorio, **tooltip** opcional en lugar de texto multilínea.

**Decisión (producto):**

1. **No** mostrar el copy largo actual (*«El evento ya inició según la hora del protocolo…»*) en cuerpo de card.
2. Aplicar **atenuación visual clara** a la card (p. ej. opacidad menor que el resto de picks no bloqueados; coherente con **D-05-009 / D-05-019**).
3. Mostrar una **etiqueta breve** visible siempre (p. ej. *«Tomar no disponible»* o reutilizar semántica de `eventUi.statusLabel` si ya comunica “en juego” / post-inicio sin duplicar).
4. **Tooltip / `title`:** en **pointer hover** (escritorio), un texto corto de ayuda (una frase) que sustituya la explicación eliminada; en **móvil** no depender del hover — solo tag + opacidad.
5. **Estándar:** sigue existiendo **Detalle** para revisión; no exigir nuevo endpoint.

**Trazabilidad:** **RFB-07**; **US-FE-044**; **T-177**.

---

## D-05.1-005 — Bóveda: premium **bloqueado** — superficie mínima *(RFB-08)*

**Contexto:** En premium no desbloqueado hoy se muestra bloque “Vista previa · lectura del modelo”, extracto de `traduccionHumana`, badge de **edge**, etc. El PO quiere que el usuario decida el desbloqueo con **datos mínimos**: enfrentamiento / mercado y selección, **fecha y hora** de inicio, **cuota sugerida** y **slider**; sin narrativa ni “sugerencias” del modelo antes de pagar DP.

**Decisión (producto):**

1. Con **`accessTier === 'premium'`** y **`!isUnlocked`**, **ocultar:** bloque de vista previa / extracto de **`traduccionHumana`**; **curva de equity** no aplica en esta fase; **badge `edgeBps`** (se interpreta como señal del modelo, no como dato de cotización puro).
2. **Mostrar obligatoriamente:** `marketLabel` + `selectionSummaryEs` (o equivalente h vs a / mercado), `eventLabel`, **inicio en TZ usuario** (`kickoffUtc` formateado), **`suggestedDecimalOdds`** (cuota sugerida en mono), **coste DP** en el slider, badges de tier/estado evento que ya expone el CDM (`eventStatus`, `isAvailable`) si no revelan lectura del modelo.
3. **`titulo`** del pick: **solo** si el equipo lo considera dato factual del evento (no narrativa del modelo); si duda, **ocultar** en premium bloqueado hasta aclarar en implementación *(por defecto en US: permitir **una** línea corta tipo fixture si viene del CDM sin ser `traduccionHumana`)*.
4. Tras **desbloqueo** (flujo **US-FE-040**), el contenido completo del modelo sigue las reglas ya acordadas para premium desbloqueado.

**Trazabilidad:** **RFB-08**; **D-05-004**; **US-FE-044**; **T-178**.

---

## D-05.1-006 — Ledger: “protocolo” → clase de mercado; bloque lateral honesto *(RFB-11)*

**Contexto:** El `<select>` y la columna etiquetaban “protocolo”, pero el dato es **`marketClass`** (CDM). El bloque “Eficiencia del protocolo” mostraba en realidad **tasa de acierto** (`protocolWinRate`) + DP sumados en vista, con redacción que sugería una métrica formal inexistente.

**Decisión (producto):**

1. **Filtro:** primera opción y microcopy como **“Todas las clases”** / **clase de mercado**; no “filtrar por protocolo”.
2. **Tabla:** cabecera de columna **“Clase de mercado”** (valor sigue siendo `marketClass`).
3. **Bloque lateral:** título **“Tasa de acierto en el segmento”**; texto que diga explícitamente **% de liquidaciones positivas sobre el ledger filtrado** y DP en vista, sin “eficiencia del protocolo”.

**Trazabilidad:** [`../../refinement_feedback_s1_s5/DECISIONES.md`](../../refinement_feedback_s1_s5/DECISIONES.md) **RFB-11**; **US-FE-045**; **T-180**.

---

## D-05.1-007 — Rendimiento: card sin “Alpha”; checklist sin ítem siempre verde *(RFB-12)*

**Contexto:** La tarjeta “Protocolo Alpha” mezclaba señales condicionales con **“Recalibración de tamaño de unidad”** siempre marcada; el subtítulo del header hablaba de “protocolo Alpha” sin definición de producto.

**Decisión (producto):**

1. **Subtítulo** de la vista: indicadores **desde el ledger registrado** (sin marca “Alpha”).
2. **Tarjeta:** título **“Chequeo operativo”**; mantener los tres ítems con lógica actual (liquidez, varianza, cierre/psique); **eliminar** la fila con check permanente.
3. **Pie de tarjeta:** una línea que indique que el **tamaño de unidad** se gestiona en **tesorería** (modal de capital), sin simular estado completado.
4. **Tour** `performance`: paso alineado al nuevo nombre y al significado real de cada señal.

**Trazabilidad:** **RFB-12**; **US-FE-045**; **T-181**.

---

## D-05.1-008 — Rendimiento: banda DP honesta; sin “sentimiento” inventado *(RFB-13)*

**Contexto:** “Nivel de protección” sugería cobertura o producto desbloqueado; en código es solo **umbrales de DP en cliente**. “Sentimiento global” era **texto fijo** sin fuente ni API.

**Decisión (producto):**

1. **Banda DP:** título **“Nivel por DP (ilustrativo)”** (o equivalente corto); microcopy que aclare **derivación en cliente**, sin prometer módulos ni gestión de riesgo real hasta definición **BE**.
2. **Sentimiento global:** **no** mostrar narrativa inventada; **ocultar** el bloque en esta versión (reintroducir solo con **fuente servidor** acordada, p. ej. **S6+**).

**Trazabilidad:** **RFB-13**; alineado al criterio honesto de **D-05-006–008** del refinement S5; **US-FE-045**; **T-182**.

---

## D-05.1-009 — Santuario: quitar label «Santuario Zurich» *(RFB-02)*

**Decisión:** Eliminar el rótulo decorativo **«Santuario Zurich»** en `SanctuaryPage`; la sección se identifica por el **título principal** y la **cabecera V2** (**D-05.1-003**). No replicar el patrón en otras vistas salvo revisión de marca en identidad visual.

**Trazabilidad:** [`../../refinement_feedback_s1_s5/DECISIONES.md`](../../refinement_feedback_s1_s5/DECISIONES.md) **RFB-02**; **US-FE-046**; **T-183**.

---

## D-05.1-010 — Santuario: recuadro «Estado del entorno» → resumen operativo del día *(RFB-03)*

**Decisión:** Sustituir el copy placeholder por un bloque **accionable**: día operativo (`operatingDayKey`), estado de estación / cierre según `useSessionStore` e hidratación **`GET /bt2/session/day`**, gracia o pendientes cuando existan; **CTA** a **`/v2/daily-review`**. Sin métricas inventadas; si no hay datos, **—** + microcopy honesto (**D-05-006**).

**Trazabilidad:** **RFB-03**; **US-FE-046**; **T-184**.

---

## D-05.1-011 — Glosario: campo de búsqueda en modal *(RFB-04)*

**Decisión:** Filtrado en cliente de términos del glosario con debounce y accesibilidad; sin nuevas rutas API.

**Trazabilidad:** **RFB-04**; **US-FE-047**; **T-185**.

---

## D-05.1-012 — Sidebar: «Sincronizar DP» — semántica y feedback *(RFB-14)*

**Decisión:** La acción ejecuta **`syncDpBalance`** (`GET /bt2/user/dp-balance`); **loading** visible; **éxito** con toast breve opcional; **error** con mensaje visible (no catch silencioso en esta CTA); icono **distinto de `+`** (refresh/sync). Cooldown opcional.

**Trazabilidad:** **RFB-14**; **US-FE-048**; **T-186**.

---

## D-05.1-013 — Vistas V2: evitar doble fetch en carga *(RFB-15)*

**Decisión:** Auditar en build de **producción**; si duplicado es solo Strict Mode en dev, documentar; si no, consolidar una sola invocación por recurso en primer montaje. Criterio: ≤1 request por endpoint lógico en primera carga (lista de rutas en tarea).

**Trazabilidad:** **RFB-15**; **US-FE-049**; **T-187**.

---

*Última actualización: 2026-04-09 — D-05.1-009 … D-05.1-013 (RFB-02, 03, 04, 14, 15).*
