# Sprint 06.1 — Plan (calidad de señal DSR + edge medible)

**Orden de lectura recomendado (dev / agente):** Intro de este PLAN → [`DECISIONES.md`](./DECISIONES.md) (**D-06-021** … **D-06-026**) → [`US.md`](./US.md) → [`TASKS.md`](./TASKS.md) (DoR + **T-171–T-187**) → [`HANDOFF_EJECUCION_S6_1.md`](./HANDOFF_EJECUCION_S6_1.md). Contexto de negocio: [`OBJETIVO_SENAL_Y_EDGE_DSR.md`](./OBJETIVO_SENAL_Y_EDGE_DSR.md).

> **Estado:** definición — a ejecutar **después** del núcleo Sprint 06 (DSR en BT2, vault, admin).  
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
| [`DECISIONES.md`](./DECISIONES.md) | **D-06-021** … **D-06-026** — paridad v1, precedencia bóveda, pool/post-DSR, KPI v0, **vacío duro (§6)** |
| [`HANDOFF_EJECUCION_S6_1.md`](./HANDOFF_EJECUCION_S6_1.md) | Orden de implementación, cesiones por capa, sincronía PO/BE/FE |
| [`EJECUCION.md`](./EJECUCION.md) | Evidencia escenarios **US-BE-036** y notas de cierre (rellenar durante el sprint) |

## Archivos del sprint

- [`US.md`](./US.md) — US completas (**US-DX-003**, **US-BE-032–036**, **US-BE-035**, **US-FE-055**).  
- [`TASKS.md`](./TASKS.md) — **T-171–T-187** (+ **T-188** diferido); **DoR** y check cierre.  
- [`DECISIONES.md`](./DECISIONES.md) — **D-06-021** … **D-06-026**; whitelist/umbrales vía **T-171** / **D-06-024**.  
- [`EJECUCION.md`](./EJECUCION.md) — evidencia escenarios y cierre (rellenar en sprint).

## Relación con otras notas

- [`../../DSR_V1_FLUJO.md`](../../DSR_V1_FLUJO.md) — contrato v1 `ds_input` vs BT2 §8.  
- [`../../notas/BACKTESTING_RECONCILIACION_CDM.md`](../../notas/BACKTESTING_RECONCILIACION_CDM.md) — reconciliación odds / backtest.  
- [`../../notas/VISTA_AUDITORIA_EVENTOS_CDM_ADMIN.md`](../../notas/VISTA_AUDITORIA_EVENTOS_CDM_ADMIN.md) — propuesta admin (**T-188**, diferido).

---

*Creado: 2026-04-08 — backlog explícito post–D-06-020. Actualizado: 2026-04-09 — D-06-021…026, DoR, `EJECUCION.md`, check cierre TASKS.*
