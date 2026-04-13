# Incremento: BT2 mejor que v1 (plan técnico + notas PO)

**Sprint:** **06.2** (definición y ejecución pendiente de recuadrar US).  
**Contexto narrativo (06.1):** [`../sprint-06.1/REFINEMENT_S6_1.md`](../sprint-06.1/REFINEMENT_S6_1.md) · [`../sprint-06.1/feedback.md`](../sprint-06.1/feedback.md).  
**Contrato v1 vs BT2:** [`../../DSR_V1_FLUJO.md`](../../DSR_V1_FLUJO.md).

Este documento conserva el hilo: **qué falta ejecutar** para superar a v1, **preguntas de producto** abiertas, y **referencia futura** a la forma de datos SofaScore (scrap v1).

---

## 1. Definición / preguntas abiertas (PO — antes de cerrar parámetros de fases)

### 1.1 ¿Cuándo se generan los picks y cuántas veces corre DSR?

**Diseño de producto acordado (PO — práctico en coste y coherencia):**

1. **Un solo conjunto de señal por día operativo:** el sistema genera **un snapshot global** (misma corrida DSR / mismo pool procesado para el día), **no** un pipeline distinto por usuario. Evita **N× consumo** de API modelo y consultas pesadas si cada usuario viera picks distintos generados al abrir sesión.
2. **Generación autónoma (~medianoche / ventana nocturna):** el lote de **hasta 20** picks del día (snapshot global) se materializa por **job/cron** (o worker), no como efecto colateral del primer `session/open` de cada usuario. La medianoche debe alinearse a la **definición de día operativo** (TZ producto; puede requerir un `operating_day_key` de referencia o reglas explícitas en **DECISIONES**).
3. **Cupo “tomables” y composición del slate:** en el día operativo el usuario puede **tomar como máximo 5 picks** elegidos entre los **20** del snapshot (**3 estándar + 2 premium** en el grupo de 5 mostrado). La lógica de compromiso / ledger encaja con la economía ya descrita en Sprint 05 (p. ej. contexto de hasta **5 picks** en un día en **D-05-012** en [`../sprint-05/DECISIONES.md`](../sprint-05/DECISIONES.md)). Los **premium** siguen atados a **DP** / desbloqueo según decisiones vigentes.
4. **Misma canasta, distinta hora de consulta:** una sola generación de **20** para toda la plataforma (**no** otra corrida DSR por usuario). Dos usuarios que entren **a la misma hora** deberían ver la **misma** selección inicial coherente con esa hora; quien entre **más tarde** ve el slate alineado a su **franja** y a partidos aún **no empezados / no terminados**. Detalle de UI (sin tabs “mezcla” confusos) y botón **Regenerar** en el bloque **Mix** siguiente.
5. **Preview y detalle de picks (jerarquía antidummies):** acordado PO/BA. **Anexo canónico** (wireframes, reglas, tabla preview vs detalle): [`../sprint-06.1/incremento_mejora_a_v1_bt2.md`](../sprint-06.1/incremento_mejora_a_v1_bt2.md) §5. En resumen: partido **A vs B** primero; luego mercado + lectura; **cuota siempre visible** (no solo bajo acciones); **Vektor** sustituye “DSR” en copy usuario; preview acota Vektor a ~2 líneas, detalle párrafo completo; sin metadatos técnicos en superficie; evento iniciado = chip + CTA off sin muros ni citas D-05/US; coherencia titular/cuota/texto; fallback = mayor probabilidad implícita cuando falte señal.

6. **Mix de picks del día (objetivo UX):** Hoy la UI muestra **tabs** por franja y “mezcla” con totales que confunden. **Objetivo:** **20** picks en el snapshot global, repartidos en **tres franjas** (definidas en TZ del usuario); **sin tabs** para filtrar; una **vista** que muestra **como mucho 5** candidatos a la vez (**3 estándar + 2 premium**), priorizando **franja actual** y **kickoff** en hora local; botón **Regenerar** que **baraja solo las ranuras no tomadas** dentro de los elegibles del pool de 20 (ver aclaraciones).

**Reglas (mix):**

1. No mostrar más de **5** picks candidatos a la vez en el slate.
2. **20** picks generados por día (global), equilibrados entre franjas lo más posible; si un día falta densidad en una franja, completar con el resto elegible.
3. **Regenerar** opera sobre el **mismo** lote de 20; **no** es otra generación por usuario.
4. Franjas y kickoffs en **TZ del usuario** (ver cortes en aclaraciones).
5. Si ya pasaron eventos de la franja cercana, **rellenar** hacia adelante (solo partidos **por empezar**, ver aclaración 6).
6. Dentro de una franja, **premium vs estándar** como ya está definido en sprint / decisiones.
7. **Borde:** priorizar **calidad** sobre rellenar a 5; si hay pocos elegibles, **mostrar menos**.

**Aclaraciones (mix):**

1. **Madrugada (00:00–05:59):** **fuera de alcance** de este diseño. La experiencia asume **día operativo** en horario activo (**desde 06:00** en TZ usuario); no se diseña que el operador deba estar pendiente de picks desde la plataforma fuera de ese marco.
2. **Cinco tomados por día:** de los **20** del snapshot, el usuario solo puede **tomar** (**comprometerse con**) **5** en el día operativo. El botón **Regenerar** sigue mostrando **5** slots de candidatos, pero un pick **ya tomado** queda **fijo**; al regenerar solo se **barajan los demás** (p. ej. si tomó 1, se barajan **4** huecos entre el resto elegible no tomado).
3. **Prioridad por franja y Regenerar:** en la **primera** presentación se prioriza **siempre la franja actual** (p. ej. si es mañana y hay 5 picks de mañana elegibles, los **5** son de mañana). Cada pulsación de **Regenerar** aplica **2** de la franja ancla + **3** de la **siguiente**; pulsaciones siguientes **desplazan** el ancla hacia la siguiente franja hasta **completar un ciclo** y volver al comportamiento tipo **primera carga**. (Estado finito exacto: cerrar en US/BE.)
4. **Misma hora, misma vista inicial;** distinta hora o franja → slate coherente con esa consulta. **Regenerar** excluye partidos **ya iniciados** y **terminados**.
5. **Cortes de franja (TZ usuario):** mañana **06:00–11:59**, tarde **12:00–17:59**, noche **18:00–23:59**.
6. Hasta decisión de producto sobre **live**, solo candidatos **pre-partido** (no empezados ni terminados).

**Comportamiento actual del código** (`apps/api/bt2_router.py`) — **deuda respecto al diseño anterior:**

- `POST /bt2/session/open` llama a `_generate_daily_picks_snapshot`.
- Idempotencia por **`(user_id, operating_day_key)`**: si ya hay filas en `bt2_daily_picks` para **ese** usuario y día, no se vuelve a correr el pipeline.
- La **primera** apertura de sesión del día **por usuario** sin filas **sí** dispara pool + DSR + inserts → **hasta N corridas** para N usuarios (mismo día, mismos eventos posibles).

**Acción (Sprint 06.2):** trasladar el diseño acordado a **DECISIONES** / **US-BE/FE** / **TASKS** en **esta** carpeta cuando el alcance esté recuadrado; refactor de `bt2_daily_picks` o tabla intermedia “pool del día” + API de vista por usuario según diseño BE.

### 1.2 Premisa 20 en snapshot vs 5 tomables y slate de 5

**Premisa (alineada a §1.1, incl. Mix):** **20** picks generados **una vez** para el día (global); el usuario puede **tomar** como máximo **5** en el día operativo; en pantalla se muestra un **slate** de **hasta 5** candidatos (**3 estándar + 2 premium**) con reglas de franja y **Regenerar** descritas arriba.  
**Problema reportado:** tabs + “Mezcla” muestran totales que **no** reflejan ese modelo.

**Acción:** auditar UI (`VaultPage`, `vaultTimeBand`, filtros) y contrato API frente a **US/DECISIONES**; implementar modelo objetivo o actualizar decisión documentada.

---

## 2. Criterio de éxito

| Criterio | Descripción |
|----------|-------------|
| **`ds_input`** | Misma **riqueza útil** que v1 (o mayor): `event_context` + `processed` poblado donde la DB lo permita + `diagnostics` veraces. |
| **Señal** | Salida **DeepSeek** (no reglas) como camino por defecto en entornos “producto”, con **Post-DSR** que normalice y corte incoherencias. |
| **Medición** | Admin/logs: `dsr_source`, completitud, omisiones Post-DSR, sin mezclar KPIs con la etiqueta simbólica del LLM. |

---

## 3. Fases técnicas

### Fase 1 — Ingesta y persistencia (API = reemplazo del scraper)

- Inventario **CDM/Postgres** (`bt2_*`): eventos, odds, ligas; stats / H2H / lineups / agregados si existen.
- **Jobs / pipelines:** lo que el producto necesita debe **persistirse** antes del snapshot (frescura, ventana del día operativo).
- **Gaps:** donde no haya tabla, documentar “no disponible” y **no** simular `available: true` sin datos.

*Sin esto, el builder no tiene de dónde leer.*

### Fase 2 — Builder `ds_input` (corazón de “superar a v1”)

- Ampliar `bt2_dsr_ds_input_builder`: consultas por evento/equipos — H2H, forma, estadísticas agregadas, alineaciones o equivalentes según schema (**T-189**, **D-06-028**).
- **Cuotas históricas / series** si el modelo de datos lo permite (**T-190**); solo vía whitelist + validador (**T-171** / **T-172**).
- **`diagnostics`:** fallos reales de ingesta, no flags genéricos.
- **Tests** con fixtures que acoten paridad de forma y contenido frente a v1 en bloques acordados.

*Esto convierte “API conectada” en el mismo tipo de insumo que `event_features.features_json`.*

### Fase 3 — Modelo y contrato de salida

- `BT2_DSR_PROVIDER=deepseek` + `DEEPSEEK_API_KEY` donde se espere producto; reglas solo CI/degradación.
- Prompt batch alineado a **D-06-027** (**T-191**).
- Mantener contrato JSON de salida + parse robusto; tests de regresión al cambiar prompt.

### Fase 4 — Post-DSR y calidad publicada

- Reglas existentes: cuota anclada al input, omisión sin cobertura, cap de confianza.
- Coherencia **selection / razon** (**T-192**, **D-06-029**); ampliar heurísticas con casos reales.
- **Telemetría:** logs / métricas de `omit reason`.

### Fase 5 — Pool y orquestación

- Pool valor **D-06-024** / **D-06-025**; orquestación **US-BE-036**; revisión `BT2_PRIORITY_LEAGUE_IDS` y ventanas.

### Fase 6 — Frontend y operación

- Copy acorde a fuente (**US-FE-056**, **T-194**).
- Sincronización bóveda ↔ servidor tras regenerar snapshot ([`../../LOCAL_API.md`](../../LOCAL_API.md)).
- Runbooks: regenerar snapshot, comprobar `dsr_source` en DB, checklist de env.

---

## 4. Orden recomendado de implementación

**Ingesta (lo que falte) → Builder (Fase 2) → DeepSeek + prompt (Fase 3) → Post-DSR (Fase 4) → Pool/orquestación (Fase 5) → FE/copy (Fase 6).**

Sin **Fase 2**, las fases 3–4 mejoran poco: el modelo sigue con poco contexto útil.

---

## 5. Trazabilidad en el repo

| Bloque | Documento |
|--------|-----------|
| Narrativa PO + gap técnico | [`../sprint-06.1/REFINEMENT_S6_1.md`](../sprint-06.1/REFINEMENT_S6_1.md) |
| Decisiones ejecutables (06.1) | [`../sprint-06.1/DECISIONES.md`](../sprint-06.1/DECISIONES.md) **D-06-027** … **D-06-030** |
| US / tareas 06.1 (hasta recuadre 06.2) | [`../sprint-06.1/US.md`](../sprint-06.1/US.md), [`../sprint-06.1/TASKS.md`](../sprint-06.1/TASKS.md) |
| Orden dev 06.1 | [`../sprint-06.1/PLAN.md`](../sprint-06.1/PLAN.md) / [`../sprint-06.1/HANDOFF_EJECUCION_S6_1.md`](../sprint-06.1/HANDOFF_EJECUCION_S6_1.md) |
| Ingesta SM / raw vs CDM | [`../sprint-06.1/HALLAZGO_SM_INGESTA_RAW_CDM_DS_INPUT.md`](../sprint-06.1/HALLAZGO_SM_INGESTA_RAW_CDM_DS_INPUT.md) |
| Contrato v1 | [`../../DSR_V1_FLUJO.md`](../../DSR_V1_FLUJO.md) |

---

## 6. Anexo — Referencia SofaScore (scrap v1)

**Mapa técnico detallado (endpoints ↔ processors v1 ↔ tablas BT2 ↔ pasos):**  
[`../sprint-06.1/V1_SOFASCORE_A_BT2_DS_INPUT_MAPA.md`](../sprint-06.1/V1_SOFASCORE_A_BT2_DS_INPUT_MAPA.md).

**Archivos .txt del PO** (ej. `event_id.txt`, `event_id_lineups.txt`, `event_id_statistics.txt`, `event_id_odds_all.txt`, `event_id_odds_feature.txt`, `h2h_id.txt`, `ejemplofutbol.txt`, `stats_test.txt`): capturas del Network tab; alineados 1:1 con las URLs que usa `fetch_event_bundle` en `core/event_bundle_scraper.py`.

**Ubicación opcional en git:** `docs/bettracker2/refs/sofascore_endpoints/` + `README` que indexe cada `.txt`.

**Nota:** SofaScore es **referencia semántica** de v1; BT2 debe poblar el **mismo tipo de slots** en `ds_input` desde **Postgres/CDM licenciado**, no depender del scrap SofaScore en producción.

---

*Última actualización: 2026-04-10 — documento trasladado desde sprint-06.1; backlog del incremento en 06.2.*
