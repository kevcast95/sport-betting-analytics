# Refinement — feedback S1–S5 (decisiones)

**Fuente de ítems:** [`../feedback_s1_s5.md`](../feedback_s1_s5.md) (checklist de notas).  
**Propósito:** cerrar **punto por punto** en el hilo BA/PM, registrar **decisión** aquí y luego abrir **US de refinement** (FE/BE/DX) con referencia `RFB-##`.

**Leyenda de estado:** `Pendiente` · `Acordado` · `Descartado` · `Diferido S6+`

---

## Alcance del hilo BA/PM y código ya modificado (trazabilidad)

- **Mandato:** en chats gobernados por [`../agent_roles/ba_pm_agent.md`](../agent_roles/ba_pm_agent.md) **no** se implementa código en `apps/web/`, `apps/api/`, tests ni migraciones salvo petición explícita del owner y cambio de contexto.
- **Hecho constatable (sesión previa, fuera de ese mandato):** para **RFB-11 … RFB-13** / **US-FE-045** alguien aplicó cambios **directamente** en:
  - `apps/web/src/pages/LedgerPage.tsx`
  - `apps/web/src/components/ledger/LedgerTable.tsx`
  - `apps/web/src/pages/PerformancePage.tsx`
  - `apps/web/src/components/tours/tourScripts.ts`
- **Backlog doc:** **T-180 … T-182** en [`../sprints/sprint-05.1/TASKS.md`](../sprints/sprint-05.1/TASKS.md) describen ese trabajo; el equipo marca los checkboxes según su **Definition of Done** (revisión en hilo ejecutor, PR, QA). La **decisión de producto** sigue en **D-05.1-006 … D-05.1-008**; no confundir “código presente en working tree” con “cerrado administrativamente en TASKS”.

**Orden de discusión:** **⑤** **RFB-05** + **RFB-06** — **cerrados** en **[`../sprints/sprint-05.2/`](../sprints/sprint-05.2/TASKS.md)** (**T-188–T-195**). **⑥** **RFB-02 … RFB-04, RFB-14, RFB-15** — cerrados en **sprint-05.1** (**US-FE-046 … US-FE-049**).

---

## Índice rápido

| ID | Tema | Estado |
|----|------|--------|
| RFB-01 | “Actualizado ahora” + CTA “Cómo funciona” (layout, icono) | Acordado |
| RFB-02 | Label “SANTUARIO ZURICH” solo en Santuario | Acordado |
| RFB-03 | Recuadro “Estado del entorno” (Santuario) | Acordado |
| RFB-04 | Glosario: barra de búsqueda | Acordado |
| RFB-05 | Bóveda: política post–kickoff (bloqueo inmediato vs ventana) | **Cerrado** — [`sprint-05.2`](../sprints/sprint-05.2/TASKS.md) (**T-190**, **T-194**, **D-05.2-001**) |
| RFB-06 | Bóveda: franjas + **~15 candidatos** en vault + cupo 3+2 | **Cerrado** — [`sprint-05.2`](../sprints/sprint-05.2/TASKS.md) (**T-188–T-193**, **D-05.2-002** §6) |
| RFB-07 | Bóveda: copy largo evento ya iniciado (opacidad, tag, tooltip) | Acordado |
| RFB-08 | Bóveda: premium bloqueado — superficie mínima (mercado, hora, **cuota**, slider) | Acordado |
| RFB-09 | Bóveda: desbloqueo premium **no** debe marcar pick como tomado | Acordado |
| RFB-10 | Header superior unificado entre vistas V2 | Acordado |
| RFB-11 | Ledger: “Filtrar por protocolo” + “Eficiencia del protocolo” | Acordado |
| RFB-12 | Rendimiento: card “Protocolo alpha” y checks | Acordado |
| RFB-13 | Rendimiento: “Nivel de protección” y “sentimiento global” | Acordado |
| RFB-14 | Sidebar: botón “Sincronizar DP” (+ feedback y semántica) | Acordado |
| RFB-15 | Doble fetch al cargar vistas (consultas duplicadas) | Acordado |

*(RFB-05 cubre el ítem vault duplicado de “Actualizado ahora” en la fuente; RFB-01 aplica a vault y al resto.)*

---

## RFB-01 — “Actualizado ahora” y “Cómo funciona” (global)

**Contexto (fuente):** En casi todas las vistas aparece “Actualizado ahora”; si se quita, “Cómo funciona” debe alinearse a la **izquierda**, con **icono** o signo **en círculo**, a la **izquierda** del texto (no a la derecha).

**Estado:** **Acordado** (2026-04-08) — **Sprint 05.1**

**Decisión:** Incorporada en **D-05.1-003** y **US-FE-043**: eliminar «Actualizado ahora» decorativo; ayuda con **icono en círculo** a la **izquierda** de «Cómo funciona»; patrón de cabecera unificado (**RFB-10**).

**US derivadas:** **US-FE-043** — [`../sprints/sprint-05.1/US.md`](../sprints/sprint-05.1/US.md); tareas **T-174–T-176** en [`../sprints/sprint-05.1/TASKS.md`](../sprints/sprint-05.1/TASKS.md).

---

## RFB-02 — Label “SANTUARIO ZURICH”

**Contexto:** Solo en `/sanctuary`, sobre el hero (`SanctuaryPage`).

**Estado:** **Acordado** (2026-04-09) — **Sprint 05.1**

**Decisión:** **Eliminar** el rótulo decorativo **«Santuario Zurich»** (línea tipo eyebrow sobre el `<h1>`). La jerarquía de la vista queda en el **título principal** y en la **cabecera unificada** (**RFB-10** / **US-FE-043**): no replicar el patrón “Zurich” en otras pantallas salvo decisión futura de marca en **`04_IDENTIDAD_VISUAL_UI.md`**. **D-05.1-009**.

**US derivadas:** **US-FE-046** — [`../sprints/sprint-05.1/US.md`](../sprints/sprint-05.1/US.md); **T-183** (este ítem) y **T-184** (RFB-03, mismo US) en [`../sprints/sprint-05.1/TASKS.md`](../sprints/sprint-05.1/TASKS.md).

---

## RFB-03 — “Estado del entorno” (Santuario)

**Contexto:** Recuadro con copy genérico (“panel conductual… sin datos de proveedor”) sin acción clara.

**Estado:** **Acordado** (2026-04-09) — **Sprint 05.1**

**Decisión:** **Redefinir** el bloque como **resumen operativo del día** usando **solo** datos ya disponibles en **`useSessionStore`** / hidratación existente (sin inventar métricas): **día operativo** (`operatingDayKey` legible), **estación** (cerrada para el día vs pendiente — reglas ya documentadas en comentarios del store y **`GET /bt2/session/day`**), **gracia** / pendientes cuando aplique (`graceActiveUntilIso`, `previousDayPendingItems`); **CTA** explícito a **Cierre del día** (`/v2/daily-review`). Si aún no hay datos hidratados, **—** + microcopy honesto (misma línea que **D-05-006–008**). Título sugerido: **«Día operativo»** o **«Estado operativo»** (elegir uno en implementación). **D-05.1-010**.

**US derivadas:** **US-FE-046**; **T-184** en [`../sprints/sprint-05.1/TASKS.md`](../sprints/sprint-05.1/TASKS.md).

---

## RFB-04 — Glosario: búsqueda

**Contexto:** Search bar para filtrar términos sin scroll infinito.

**Estado:** **Acordado** (2026-04-09) — **Sprint 05.1**

**Decisión:** Añadir en **`GlossaryModal`** un **campo de búsqueda** visible al abrir el modal; filtrar entradas por **coincidencia de texto** (título, etiqueta, cuerpo) en cliente; **debounce** corto (p. ej. 150–250 ms); **sin** nuevas peticiones HTTP; accesibilidad: `label` / `aria-label`, foco al abrir opcional. **D-05.1-011**.

**US derivadas:** **US-FE-047** — [`../sprints/sprint-05.1/US.md`](../sprints/sprint-05.1/US.md); **T-185** en [`../sprints/sprint-05.1/TASKS.md`](../sprints/sprint-05.1/TASKS.md).

---

## RFB-05 — Bóveda: bloqueo si el evento ya inició

**Contexto:** ¿Bloqueo **en cuanto** pasa `kickoffUtc` o existe una **ventana de gracia** (p. ej. “aún puedo tomar hasta X minutos después”)? El feedback del PO cita explícitamente *“10:30 y el partido empezó hace 10 min”*.

**Estado:** Backlog ejecutable — **[`../sprints/sprint-05.2/`](../sprints/sprint-05.2/PLAN.md)**; ratificar **D-05.2-001** antes de merge **US-BE-031**.  

**Decisión operativa:** ver **[`D-05.2-001`](../sprints/sprint-05.2/DECISIONES.md)** *(default propuesto: kickoff estricto salvo PO elija gracia en BE)*.  

**Marco ya documentado:** [**D-05-010**](../sprints/sprint-05/DECISIONES.md) — si el partido **ya inició**, no ofrecer “Tomar” como pre-partido sin fricción; **`isAvailable`** del BE es regla canónica con el **POST**; el FE puede añadir comparación temporal **solo** si hay instante de inicio (**`kickoffUtc`**) y **política cerrada** con BE. **RFB-07** ya cubrió **presentación** (opacidad, tag, tooltip), **no** la regla numérica de negocio.

**Trade-offs BE / FE**

| Enfoque | Pros | Contras |
|--------|------|--------|
| **A — Estricto al kickoff (0 min)** | Coherencia simple; alinear FE con `kickoffUtc`; menos sorpresas si el POST ya rechaza eventos no programados. | Cero flexibilidad operativa; puede chocar con casos reales de retraso de datos o mercados que aún aceptan apuesta en casas externas (el producto **no** las ejecuta, pero el usuario puede pedir “ventana”). |
| **B — Ventana solo en FE** | UX rápida sin migración BE. | **Riesgo de mentira:** usuario ve “Tomar” y el servidor responde **422/409**; hace falta mensaje de error alineado o el FE debe **ocultar** Tomar igual que el BE. |
| **C — Ventana en BE** (`isAvailable` o regla router) | **Una sola fuente de verdad**; el cliente solo refleja el contrato. | Requiere **US-BE** (reloj servidor, deporte, reglas de mercado); posible parametría (`grace_minutes`) y tests; más trabajo en **05.1** o **S6**. |
| **D — Diferido S6+** | No frena cierre de **05.1**; se documenta “hoy = comportamiento actual hasta decisión”. | Deuda explícita; PO debe aceptar estado interino. |

**Propuesta de cortar alcance (para acordar en PO):**

1. **05.2 (MVP):** elegir **A o C con X minutos fijos** en **D-05.2-001**; **US-BE-031** + **US-FE-051** (**T-190**, **T-194**).
2. **S6+ (fuerte):** ventana por deporte/liga, telemetría “intentos bloqueados”, o política distinta estándar vs premium.

**US derivadas:** **US-BE-031**, **US-FE-051** — [`../sprints/sprint-05.2/US.md`](../sprints/sprint-05.2/US.md); tareas **T-190**, **T-194**.

---

## RFB-06 — Bóveda: franja del día / fetch bajo demanda / picks libres

**Contexto:** El PO plantea: usuario que **prefiere tarde** frente a picks de la mañana; **límite de picks libres** (p. ej. 3) con consumo escalonado; ¿**refetch** bajo demanda? ¿**Elegir** partidos antes de que el vault “mande” el snapshot? ¿Carga en sistema?

**Estado:** Backlog ejecutable — **[`../sprints/sprint-05.2/`](../sprints/sprint-05.2/PLAN.md)**; decisión de producto consolidada en **D-05.2-002** (gaps PO explícitos allí).  

**Decisión (producto — borrador cerrado en hilo, 2026-04-08; traslado **D-05.2-002**):**

1. **Franjas horarias** (todas en **zona horaria del usuario**; límites en reloj local del dispositivo / settings cuando existan):
   - **Mañana:** 08:00–12:00  
   - **Tarde:** 12:00–18:00  
   - **Noche:** 18:00–23:00  
   - **Hueco 23:00–08:00:** sin franja nombrada en esta versión — **pendiente PO:** o bien se trata como “solo relleno desde franja más cercana”, o se define cuarta franja / extensión de Noche. Los límites **12:00** y **18:00** son contiguos (criterio de asignación de `kickoff` en el borde: documentar en US-BE si hace falta exclusividad estricta).

2. **Vista por defecto:** **mezcla** de picks de varias franjas (no una sola franja), con **priorización** hacia la franja **más cercana al instante actual** en TZ usuario (ej. por la mañana, sesgar hacia mañana + algo de tarde/premium coherente con el pool).

3. **Switcher (percepción de opción):** el usuario puede acotar la vista a **solo mañana**, **solo tarde** o **solo noche** (u alternar de vuelta a la mezcla). **No** aumenta el cupo: es **filtrado / rotación** sobre el mismo snapshot del día.

4. **Cupo diario total (día operativo):** **3 tomas estándar (libres)** + **2 tomas premium** = **5 tomas máximo** por día operativo (**techo global**, no por franja). El switcher **no** consume cupo; **Tomar** / compromiso operativo sí. Ejemplo: si por la mañana tomó **1** estándar, le quedan **2** estándar para el resto del día; si además tomó **1** premium, le queda **1** premium; la UI debe reflejar **restantes** por tier coherentemente entre franjas.

5. **Relleno si una franja viene escasa:** si no hay suficientes candidatos en la franja activa o en la mezcla, **completar** con picks de la **franja horaria más cercana** (por tiempo de `kickoff` respecto al usuario o por orden mañana ↔ tarde ↔ noche según regla que fije la US-BE).

6. **Backend vs frontend (dirección acordada):** el **BE** puede devolver un **pool mayor** que lo mostrado (p. ej. hasta **N** candidatos **por franja**, con **objetivo** de composición tipo 3 estándar + 2 premium **por franja** cuando el CDM lo permita — *objetivo de generación, no garantía*). El **FE** muestra a la vez solo un **subconjunto** (p. ej. 5 visibles) según modo **mezcla** o **franja**, sin exigir **reconsulta** solo por cambiar el filtro de franja. Sigue siendo necesario **refetch** en cambio de **día operativo** o cuando el producto exija datos frescos (`isAvailable`, kickoff).

**Gaps explícitos para US/DX:** (a) definición del hueco **23:00–08:00**; (b) si **desbloqueo premium** (sin tomar) cuenta o no contra el cupo de **2 premium** del día — alinear con **US-FE-040** / **US-BE-029**; (c) tamaño máximo del pool y payload.

**Desglose de sub-problemas** (referencia; no sustituye el bloque anterior):

1. **Refresh / segundo fetch del mismo día:** hoy el vault está anclado a **`operating_day_key`** y snapshot diario (**D-05-019** anti-stale ya cubre cambio de **día**). Un “traer de nuevo” **el mismo día** puede implicar nuevo **GET** idempotente o endpoint de **invalidación** / nueva generación — impacto **BE** (coste CDM, idempotencia, fairness entre usuarios).
2. **Filtrar por franja horaria en UI:** si la lista ya trae `kickoffUtc`, un filtro **solo cliente** no cambia el universo del snapshot (solo oculta). Es **FE barato** pero no sustituye “quiero otros eventos”.
3. **Curación / elección de candidatos por el usuario:** modelo distinto al **snapshot automático** (inventario tipo “catálogo del día” + cupos). Toca definir: ¿cuántas veces puede “volver a sortear”? ¿consume cupo al **ver** o al **tomar**? — reglas de producto y probable **US-BE** + cambio de contrato vault.
4. **Cupos “3 libres” ya tomados en la mañana, picks restantes por la tarde:** es coherente **si** el cupo es diario y los eventos siguen en el mismo snapshot; no requiere fetch nuevo si los ítems **ya están** en la respuesta. Si el snapshot **solo** traía mañana, entonces el problema vuelve a (1).

**Trade-off resumido**

| Opción | Capa | Nota |
|--------|------|------|
| Copy educativo (“el snapshot refleja el día operativo…”) | FE | **05.1** posible sin BE. |
| Filtro local por hora (ocultar cards) | FE | Bajo riesgo; no cambia elegibilidad servidor. |
| Botón “Actualizar bóveda” = nuevo GET mismo día | FE + BE | Confirmar idempotencia y si el servidor **regenera** o solo relee. |
| Nuevo contrato (franja, refresh limitado, elección de fixture) | BE + DX + FE | Candidato **Diferido S6+** salvo MVP muy acotado. |

**Propuesta de cortar alcance (para acordar en PO):**

- Tratar **RFB-06** como **epic**: desglosar en **US-06-A** (solo UX/filtro local + copy) vs **US-06-B** (refresh/regeneración) vs **US-06-C** (curación usuario) y **colocar B/C en S6+** si el equipo necesita cerrar **05.1** sin motor nuevo.

**US derivadas:** **US-BE-030**, **US-FE-050** — [`../sprints/sprint-05.2/US.md`](../sprints/sprint-05.2/US.md); tareas **T-188–T-193** (+ **T-191** DX opcional).

---

## RFB-07 — Bóveda: copy invasivo “evento ya inició”

**Contexto:** Preferencia por card opaca + tag o **tooltip** en hover, texto corto.

**Estado:** **Acordado** (2026-04-08) — **Sprint 05.1**

**Decisión:** **D-05.1-004** en [`../sprints/sprint-05.1/DECISIONES.md`](../sprints/sprint-05.1/DECISIONES.md): sin párrafo largo; opacidad reforzada; **tag** corto; **tooltip / `title`** solo como complemento en desktop; móvil sin depender de hover.

**US derivadas:** **US-FE-044** (tramo RFB-07); **T-177** en [`../sprints/sprint-05.1/TASKS.md`](../sprints/sprint-05.1/TASKS.md).

---

## RFB-08 — Bóveda: premium bloqueado sin detalle de modelo

**Contexto:** Solo mercado/selección (h vs a), fecha/hora, **cuota sugerida**, slider; el usuario decide si desbloquear; **sin** narrativa del modelo ni edge como señal antes del pago.

**Estado:** **Acordado** (2026-04-08) — **Sprint 05.1**

**Decisión:** **D-05.1-005** en [`../sprints/sprint-05.1/DECISIONES.md`](../sprints/sprint-05.1/DECISIONES.md): ocultar preview `traduccionHumana` y **edge**; mostrar **cuota sugerida** en mono; reglas para `titulo` en US.

**US derivadas:** **US-FE-044** (tramo RFB-08); **T-178**; pruebas **T-179** — [`../sprints/sprint-05.1/TASKS.md`](../sprints/sprint-05.1/TASKS.md).

---

## RFB-09 — Bóveda: desbloqueo premium ≠ tomar pick

**Contexto:** Hoy al desbloquear se marca como tomado; **error**: usuario desbloquea y **luego** decide tomar o no.

**Estado:** **Acordado** (2026-04-08) — implementación **Sprint 05.1**

**Decisión:** Ver **D-05.1-001** y **D-05.1-002** en [`../sprints/sprint-05.1/DECISIONES.md`](../sprints/sprint-05.1/DECISIONES.md): dos actos de producto; forma técnica **`POST /bt2/vault/premium-unlock`** + **`premiumUnlocked`** en vault + `POST /bt2/picks` sin doble −50.

**Causa técnica (auditoría):** `VaultPage` pasa `isUnlocked={isApiPickCommitted}` donde “committed” = entrada en `takenApiPicks` tras **`takeApiPick` → `POST /bt2/picks`**. En BE, **US-BE-017** aplica `pick_premium_unlock` en el **mismo** commit que crea el pick (`bt2_router.py`). Por tanto no es solo copy: requiere **US-BE-029** + **US-FE-040** en [`../sprints/sprint-05.1/US.md`](../sprints/sprint-05.1/US.md). *(**US-BE-024** en S5 era otra historia, hoy fusionada en **US-BE-018 §9**.)*

**US derivadas:** **US-BE-029**, **US-FE-040** (tareas **T-170–T-172** en [`../sprints/sprint-05.1/TASKS.md`](../sprints/sprint-05.1/TASKS.md)).

---

## RFB-10 — Header superior unificado (todas las vistas V2)

**Contexto:** Títulos, subtítulos, labels y CTA repetidos con **ligera** variación entre vistas.

**Estado:** **Acordado** (2026-04-08) — **Sprint 05.1**

**Decisión:** Misma **D-05.1-003** / **US-FE-043**: slots de cabecera comunes; ayuda a la **izquierda**; acciones secundarias a la **derecha**; §8 en [`../04_IDENTIDAD_VISUAL_UI.md`](../04_IDENTIDAD_VISUAL_UI.md).

**US derivadas:** **US-FE-043** — [`../sprints/sprint-05.1/US.md`](../sprints/sprint-05.1/US.md); **T-174–T-176**.

---

## RFB-11 — Ledger: “protocolo” en filtros y eficiencia

**Contexto:** No hay definición de “protocolo” ni de “eficiencia del protocolo”; ¿placeholder?

**Estado:** **Acordado** (2026-04-08) — **Sprint 05.1**

**Decisión:** El filtro y la columna del ledger operan sobre **`marketClass`** (clase de mercado del CDM), no sobre un “protocolo” abstracto. **Renombrar** copy de UI a **clase de mercado**; el bloque lateral pasa a **tasa de acierto en el segmento** (win rate sobre filas filtradas + DP en vista), sin rotularlo “eficiencia del protocolo”. Detalle en **D-05.1-006**.

**US derivadas:** **US-FE-045** — [`../sprints/sprint-05.1/US.md`](../sprints/sprint-05.1/US.md); **T-180** en [`../sprints/sprint-05.1/TASKS.md`](../sprints/sprint-05.1/TASKS.md).

---

## RFB-12 — Rendimiento: card “Protocolo alpha”

**Contexto:** Checks no interactivos; tour lo explica; utilidad dudosa.

**Estado:** **Acordado** (2026-04-08) — **Sprint 05.1**

**Decisión:** **Conservar** las tres señales **derivadas de datos** (liquidez vía bankroll, varianza vía ledger no vacío, preparación psicológica vía cierre reciente). **Quitar** el ítem **siempre** en verde (“Recalibración…”) del checklist; sustituir por **nota** al pie que remite a tesorería. **Renombrar** la tarjeta y el tour a **Chequeo operativo** (sin “Alpha” vacío). **D-05.1-007**.

**US derivadas:** **US-FE-045**; **T-181** (`TASKS.md` 05.1).

---

## RFB-13 — Rendimiento: “Nivel de protección” y “sentimiento global”

**Contexto:** Definición e intención óptima dudosa.

**Estado:** **Acordado** (2026-04-08) — **Sprint 05.1**

**Decisión:** **Nivel de protección:** renombrar y **aclarar** que la banda (MÁXIMO / ALTO / ESTÁNDAR) es **ilustrativa en cliente** a partir de umbrales de DP; **no** implica garantía de riesgo ni módulos reales hasta definición **BE**. **Sentimiento global:** el texto fijo no tiene fuente; **ocultar** el bloque en esta versión (misma línea que **D-05-006–008**: sin inventar señales). **D-05.1-008**.

**US derivadas:** **US-FE-045**; **T-182** (`TASKS.md` 05.1).

---

## RFB-14 — Sidebar: “Sincronizar DP” *(punto ⑥ del orden BA/PM)*

**Contexto:** Poco feedback; icono `+`; comportamiento poco claro.

**Estado:** **Acordado** (2026-04-09) — **Sprint 05.1**

**Decisión:**

1. **Semántica:** la acción es **reconciliar el saldo DP** con el servidor llamando a la función existente del store (**`syncDpBalance`** → `GET /bt2/user/dp-balance`) y actualizando **`disciplinePoints`**. **No** se exige, en esta US, refetch masivo de ledger/vault salvo que el ejecutor detecte inconsistencia documentada.
2. **Feedback:** estado **loading** en el control durante la promesa; **toast o mensaje breve** en éxito (p. ej. “Saldo actualizado”); en error de red o **401**, mensaje **visible** (toast o banner) — hoy el catch es silencioso; debe dejar de serlo para esta CTA explícita.
3. **Iconografía:** **sustituir** el icono **`+`** por uno de **actualizar / sincronizar** acorde al design system V2; el copy **«Sincronizar DP»** se mantiene salvo ajuste menor de longitud en sidebar.
4. **Opcional (PO permite omitir en primera entrega):** **cooldown** de p. ej. 10–15 s entre pulsaciones para reducir martilleo al API.

**Trazabilidad:** **D-05.1-012**; **US-FE-048**; **T-186** en `sprint-05.1/TASKS.md`. Auditar conjuntamente con **RFB-15** en DevTools (sync manual + hidratación).

---

## RFB-15 — Doble fetch al cargar vistas *(punto ⑥ del orden BA/PM)*

**Contexto:** Consultas **duplicadas** al entrar a varias vistas.

**Estado:** **Acordado** (2026-04-09) — **Sprint 05.1**

**Decisión:**

1. **Diagnóstico obligatorio:** reproducir en **`npm run build` + preview** (o entorno equivalente a **producción**). Si el doble GET **solo** aparece en **Strict Mode** de desarrollo, **documentarlo** en la US y no “arreglar” comportamiento esperado de React 18.
2. **Si en producción hay duplicado real:** consolidar **una** llamada por recurso lógico en el **primer montaje** de cada vista V2 (`useAppInit`, `useEffect` en página, layout, stores) mediante **guard** con `ref`, **deduplicación** en el store, o eliminación del segundo hook; priorizar **`useAppInit`** / hidratación central vs duplicados en hijos.
3. **Criterio de aceptación:** para una lista cerrada de rutas V2 acordada en la tarea, **≤1** request HTTP por endpoint lógico en la primera carga (salvo prefetch justificado documentado).

**Trazabilidad:** **D-05.1-013**; **US-FE-049**; **T-187** en `sprint-05.1/TASKS.md`.

---

## Registro de cierre (para el BA/PM)

Al marcar **Acordado**, añadir una línea:

| Fecha | ID | Resumen decisión | US creada |
|-------|-----|------------------|-----------|
| 2026-04-08 | RFB-09 | Desbloqueo premium ≠ tomar; BE desacoplado + FE dos pasos | US-BE-029, US-FE-040 (`sprint-05.1`) |
| 2026-04-08 | RFB-01 | Sin «Actualizado ahora»; ayuda izquierda + icono | US-FE-043, D-05.1-003 |
| 2026-04-08 | RFB-10 | Cabecera V2 unificada | US-FE-043, D-05.1-003 |
| 2026-04-08 | RFB-07 | Post-inicio: opacidad + tag + tooltip; sin párrafo largo | US-FE-044, D-05.1-004, T-177 |
| 2026-04-08 | RFB-08 | Premium bloqueado: mínimo + cuota; sin preview modelo | US-FE-044, D-05.1-005, T-178 |
| 2026-04-08 | RFB-11 | Ledger: filtro = clase de mercado; bloque = tasa acierto segmento | US-FE-045, D-05.1-006, T-180 |
| 2026-04-08 | RFB-12 | Rendimiento: “Chequeo operativo”; sin check falso; tour alineado | US-FE-045, D-05.1-007, T-181 |
| 2026-04-08 | RFB-13 | DP ilustrativo con copy honesto; ocultar “sentimiento” sin fuente | US-FE-045, D-05.1-008, T-182 |
| 2026-04-09 | RFB-02 | Quitar «Santuario Zurich»; cabecera unificada | US-FE-046, D-05.1-009, T-183 |
| 2026-04-09 | RFB-03 | Recuadro = resumen día operativo + CTA cierre | US-FE-046, D-05.1-010, T-184 |
| 2026-04-09 | RFB-04 | Glosario: buscar términos en modal | US-FE-047, D-05.1-011, T-185 |
| 2026-04-09 | RFB-14 | Sync DP: feedback, icono, errores visibles | US-FE-048, D-05.1-012, T-186 |
| 2026-04-09 | RFB-15 | Doble fetch: diagnóstico prod + consolidación | US-FE-049, D-05.1-013, T-187 |

---

*Creado: 2026-04-08. **RFB-05+06** → **[`sprint-05.2`](../sprints/sprint-05.2/EJECUCION.md)** (**D-05.2-xxx**, **T-188+**). Última actualización: 2026-04-09.*
