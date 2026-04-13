# Sprint 06.1 — Plan (calidad de señal DSR + edge medible)

> **Estado:** **cerrado** (2026-04-10) — evidencia en [`EJECUCION.md`](./EJECUCION.md). El plan de incremento “BT2 > v1” (snapshot global 20, mix bóveda, ingesta SM, recuadre de US) continúa en **[`../sprint-06.2/PLAN.md`](../sprint-06.2/PLAN.md)**.

**Orden de lectura recomendado (dev / agente):** Intro de este PLAN → [`DECISIONES.md`](./DECISIONES.md) (**D-06-021** … **D-06-030**) → [`REFINEMENT_S6_1.md`](./REFINEMENT_S6_1.md) (si aplica refinement) → [`US.md`](./US.md) → [`TASKS.md`](./TASKS.md) (DoR + **T-171–T-187** + **T-189–T-194**) → [`HANDOFF_EJECUCION_S6_1.md`](./HANDOFF_EJECUCION_S6_1.md). Contexto de negocio: [`OBJETIVO_SENAL_Y_EDGE_DSR.md`](./OBJETIVO_SENAL_Y_EDGE_DSR.md).

> **Nota histórica:** al abrir el sprint, el estado era “definición — a ejecutar **después** del núcleo Sprint 06”.  
> **Decisión puente S6:** **D-06-020** en [`../sprint-06/DECISIONES.md`](../sprint-06/DECISIONES.md).  
> **Recalibración 2026-04-09:** **D-06-021** … **D-06-026** en [`DECISIONES.md`](./DECISIONES.md) (pool, post-DSR, KPI v0, vacío duro — **D-06-026**).

## Modo de trabajo (entrada a ejecución)

- **D-06-023:** no “validación por pasos” durante el sprint como sustituto de definición. **Cualquier** gap que afecte **core** o sea **bache** se escribe **antes** de ejecutar como **US**, **refinement** o **DECISIÓN** en esta carpeta.
- Objetivo: al empezar desarrollo, **[`TASKS.md`](./TASKS.md)** cubre **integralmente** el alcance S6.1 (BE orquestación bóveda, `ds_input` rico, umbrales, FE, DX, tests) y el cierre del sprint = esas tareas + DoD de US — **estamos alineados** con ese criterio.

## Apto 100% para ejecución (Definition of Ready)

Checklist operativa: sección **«Apto 100% para ejecución»** en [`TASKS.md`](./TASKS.md). Cierre documentado de escenarios: plantilla en [`EJECUCION.md`](./EJECUCION.md).

## Objetivo (una frase)

**Menos picks con mejor señal**, apoyados en **criterios medibles** (SQL, umbrales, edge en servidor), **paridad de insumo DSR con v1** respetando anti-fuga **D-06-002**, y **separación clara de semánticas** (confianza del LLM vs calidad de datos vs edge numérico), sin que el prompt sustituya reglas de negocio.

## Documento maestro

| Documento | Contenido |
|-----------|-----------|
| [`OBJETIVO_SENAL_Y_EDGE_DSR.md`](./OBJETIVO_SENAL_Y_EDGE_DSR.md) | Resumen BE/PO, líneas de trabajo, entregable BA, **anexo** |
| [`DECISIONES.md`](./DECISIONES.md) | **D-06-021** … **D-06-030** — núcleo S6.1 + **REFINEMENT_S6_1** (**D-06-027** … **D-06-030**) |
| [`REFINEMENT_S6_1.md`](./REFINEMENT_S6_1.md) | Fuente narrativa PO/BA del refinement (criterio mercado, `ds_input`, prompt, coherencia salida) |
| [`HANDOFF_EJECUCION_S6_1.md`](./HANDOFF_EJECUCION_S6_1.md) | Orden de implementación, cesiones por capa, sincronía PO/BE/FE |
| [`EJECUCION.md`](./EJECUCION.md) | Evidencia escenarios **US-BE-036** y notas de cierre (rellenar durante el sprint) |
| [`../sprint-06.2/PLAN.md`](../sprint-06.2/PLAN.md) | **Sprint 06.2** — incremento BT2 > v1 y realineación de US (post cierre 06.1) |
| [`../sprint-06.2/FUENTE_VERDAD_CONSOLIDADO_S6_1_Y_PLAN_S6_2.md`](../sprint-06.2/FUENTE_VERDAD_CONSOLIDADO_S6_1_Y_PLAN_S6_2.md) | **Consolidado único:** decisiones, pipeline, ingesta, UI Vektor, US conceptuales, plan S6.2, pendientes explícitos |

## Archivos del sprint

- [`US.md`](./US.md) — US completas (**US-DX-003**, **US-BE-032–036**, **US-BE-035**, **US-FE-055**) + **REFINEMENT_S6_1** (**US-BE-037–039**, **US-FE-056**).  
- [`TASKS.md`](./TASKS.md) — **T-171–T-187** (+ **T-188** diferido) + **REFINEMENT_S6_1** **T-189–T-194**; **DoR** y check cierre.  
- [`DECISIONES.md`](./DECISIONES.md) — **D-06-021** … **D-06-030**; whitelist/umbrales vía **T-171** / **D-06-024**.  
- [`EJECUCION.md`](./EJECUCION.md) — evidencia escenarios y cierre (rellenar en sprint).

## Relación con otras notas

- [`../../DSR_V1_FLUJO.md`](../../DSR_V1_FLUJO.md) — contrato v1 `ds_input` vs BT2 §8.  
- [`../../notas/BACKTESTING_RECONCILIACION_CDM.md`](../../notas/BACKTESTING_RECONCILIACION_CDM.md) — reconciliación odds / backtest.  
- [`../../notas/VISTA_AUDITORIA_EVENTOS_CDM_ADMIN.md`](../../notas/VISTA_AUDITORIA_EVENTOS_CDM_ADMIN.md) — propuesta admin (**T-188**, diferido).

---

## REFINEMENT_S6_1 — Plan de ejecución (dev)

**Cuándo:** después del núcleo **T-171–T-187** o en paralelo donde no haya conflicto de archivos (coordinar con **TL**). **No** sustituye el DoR del núcleo; añade criterios en **DoR** (fila refinement en [`TASKS.md`](./TASKS.md)).

| Paso | Tareas | Notas |
|------|--------|--------|
| 1 | **T-189** → **T-190** | Enriquecer builder (**US-BE-037**); si nuevos campos hacia LLM, encadenar **T-172** / **T-171** en el mismo PR o PR previo. |
| 2 | **T-191** | Prompt (**US-BE-038**) cuando exista `ds_input` representativo o en paralelo si solo toca strings/tests. |
| 3 | **T-192** | Post-DSR coherencia (**US-BE-039**) — idealmente tras **T-182** estable en rama. |
| 4 | **T-194** | Copy FE (**US-FE-056**) tras texto de **D-06-027** fijado en **T-191** (o stub acordado con PO). |
| 5 | **T-193** | Cierre documental + pytest + **EJECUCION.md** § REFINEMENT_S6_1. |

**Handoff detallado:** [`HANDOFF_EJECUCION_S6_1.md`](./HANDOFF_EJECUCION_S6_1.md) § REFINEMENT_S6_1.

---

*Creado: 2026-04-08 — backlog explícito post–D-06-020. Actualizado: 2026-04-10 — **cierre 06.1**; incremento → [`../sprint-06.2/`](../sprint-06.2/).*
