# Sprint 06.3 — DECISIONES

> Jerarquía: norte y fases en `ROADMAP_PO_NORTE_Y_FASES.md`; backlog maestro del sprint en `PLAN.md`.
> Cierre previo: `../sprint-06.2/DECISIONES.md` D-06-031 … D-06-042 siguen vigentes salvo contradicción explícita aquí.
> Base aprobada de Fase 0: `CIERRE_FASE_0_MODELO_Y_METRICA_DATOS.md`.
> Convención alcance: D-06-023 (cambio en código → nueva US / decisión antes de merge).

* * *

## D-06-043 — Verdad oficial de evaluación del modelo en S6.3 (2026-04-14)

Contexto: Fase 0 cerró que el éxito del modelo se mide contra resultado oficial, no contra la liquidación del usuario en app. El `PLAN.md` de S6.3 deja como tema prioritario “Admin precisión DSR — premisa” y explicita que la vista debe monitorizar y validar al modelo usando resultado oficial por evento, sin depender solo de `bt2_picks` liquidados por usuario.

Decisión:
  1. Toda métrica de precisión del modelo en S6.3 se calculará contra **resultado oficial** del evento / mercado evaluado.
  2. `bt2_picks` liquidado por usuario podrá seguir existiendo como dato operacional o UX, pero **no** será la fuente normativa de verdad para evaluar desempeño del modelo.
  3. Si un pick no tiene resultado oficial trazable o no existe mapeo reproducible entre pick emitido y verdad oficial del mercado, ese pick no contará como `hit` ni `miss`; quedará en estado `no_evaluable` hasta que exista criterio implementado.
  4. La vista admin o reporte de precisión deberá leer de esta capa de evaluación oficial, no de apuestas tomadas/liquidadas por el usuario.

Trazabilidad: US-BE-049, US-BE-050, US-FE-061.

* * *

## D-06-044 — Unidad base de evaluación y estados mínimos del pick (2026-04-14)

Contexto: Fase 0 fijó que la unidad base de evaluación v0 es el **pick sugerido**. S6.3 necesita cerrar esa semántica para que admin, reporting y jobs no mezclen niveles de agregación.

Decisión:
  1. La unidad base de evaluación en S6.3 será el **pick sugerido**.
  2. A partir del pick sugerido se permitirán agregaciones por evento, día, semana, mes, mercado, liga y bucket de confianza, pero la persistencia base y la auditoría se harán a nivel pick.
  3. Todo pick emitido deberá poder quedar en uno de estos estados mínimos de evaluación (lista genérica; **literales exactos v1** en **D-06-050** / [`ACTA_T244_CONTRATO_TECNICO_FASE_1.md`](./ACTA_T244_CONTRATO_TECNICO_FASE_1.md), p. ej. `void` en lugar de `evaluated_void_or_push`):
     - `pending_result`
     - `evaluated_hit`
     - `evaluated_miss`
     - `evaluated_void_or_push` *(v0 / genérico; v1 → ver acta)*
     - `no_evaluable`
  4. Está prohibido agregar métricas globales de precisión mezclando picks evaluados con picks aún pendientes o no evaluables sin separarlos explícitamente.

Trazabilidad: US-BE-050, US-FE-061.

* * *

## D-06-045 — Regla mínima operativa de elegibilidad v1 del pool analizable (2026-04-14)

Contexto: Fase 0 aprobó `pool_eligibility_rate` como métrica operativa base y dejó una regla mínima v0 de elegibilidad. S6.3 debe materializar esa regla para que el pool sea medible con criterio reproducible y sin LLM.

Decisión:
  1. Un evento solo entra al pool analizable si cumple, como mínimo:
     - fixture consistente y utilizable,
     - cuotas válidas para análisis,
     - al menos **2 familias de mercado** disponibles para consenso o análisis equivalente,
     - ausencia de faltantes críticos en `ds_input`.
  2. La evaluación de elegibilidad deberá ser **determinística, reproducible y sin LLM**.
  3. `pool_eligibility_rate` se calculará como:
     - `eventos_elegibles / eventos_candidatos`
  4. Ningún evento no elegible podrá ser tratado como parte del universo válido para medir desempeño del modelo.
  5. Cualquier cambio a esta regla mínima requerirá nueva decisión o enmienda explícita con fecha en este documento.

Trazabilidad: US-BE-051, US-BE-052, US-FE-061.

* * *

## D-06-046 — Persistencia de auditoría de elegibilidad y motivos de descarte (2026-04-14)

Contexto: No basta con calcular elegibilidad “al vuelo”. Para que `pool_eligibility_rate` sea defendible, el sistema debe poder reconstruir por qué un evento entró o no al pool.

Decisión:
  1. Por cada evento candidato evaluado para entrar al pool, el sistema deberá persistir como mínimo:
     - identificador del evento,
     - timestamp de evaluación,
     - versión de la regla de elegibilidad,
     - resultado de elegibilidad (`eligible` / `ineligible`),
     - motivo o motivos canónicos de descarte cuando no sea elegible.
  2. Los motivos de descarte deberán ser semánticamente útiles para producto y técnica; no basta con un booleano opaco.
  3. `pool_eligibility_rate` y sus métricas derivadas deberán calcularse desde esta auditoría persistida, no desde conteos ad hoc no trazables.
  4. La vista admin o reporte deberá poder mostrar desglose de descarte por causa principal.

Trazabilidad: US-BE-051, US-BE-052, US-FE-061.

* * *

## D-06-047 — Cierre de loop obligatorio para picks emitidos en S6.3 (2026-04-14)

Contexto: Fase 0 habilitó explícitamente “definir y materializar el cierre de loop contra resultado oficial”. Sin este cierre, la precisión del modelo sigue siendo parcial o ambigua.

Decisión:
  1. Todo pick sugerido emitido en S6.3 deberá poder cerrar su loop con una evaluación persistida.
  2. La persistencia mínima por pick deberá permitir reconstruir:
     - id del pick,
     - id del evento,
     - mercado / selección sugerida o su clave canónica equivalente,
     - confianza emitida si aplica,
     - timestamp de emisión,
     - timestamp de evaluación,
     - estado final de evaluación,
     - verdad oficial usada.
  3. El cierre de loop deberá ejecutarse por backend de forma independiente a que el usuario abra la app o liquide manualmente algo.
  4. Los picks que no logren cerrar loop por falta de verdad, mapeo o integridad deberán quedar visibles como brecha operativa; no podrán esconderse dentro del hit rate.

Trazabilidad: US-BE-049, US-BE-050, US-FE-061.

* * *

## D-06-048 — Alcance mínimo de la salida admin / reporte en Fase 1 (2026-04-14)

Contexto: S6.3 necesita una salida usable para validación del modelo, pero no hace falta cerrar todavía un dashboard final sofisticado.

Decisión:
  1. El entregable mínimo de Fase 1 podrá ser una **vista admin** o un **reporte operativo**; no se exige dashboard final pulido.
  2. Esa salida mínima deberá mostrar, como piso:
     - cantidad de eventos candidatos,
     - cantidad de eventos elegibles,
     - `pool_eligibility_rate`,
     - motivos de descarte,
     - cantidad de picks emitidos,
     - cantidad de picks evaluados,
     - cantidad de picks no evaluables,
     - hit rate global sobre picks evaluados,
     - hit rate por mercado,
     - hit rate por bucket de confianza, si la señal existe.
  3. La salida deberá separar explícitamente:
     - cobertura / completitud del pool,
     - estado de cierre de loop,
     - desempeño del modelo.
  4. Está prohibido presentar una métrica agregada que mezcle esas tres capas sin distinguirlas.

Trazabilidad: US-BE-052, US-FE-061.

* * *

## D-06-049 — Fuera de alcance normativo de Fase 1 en S6.3 (2026-04-14)

Contexto: Fase 0 dejó claro que todavía no es requisito cerrar PnL, CLV, edge temporal, stake óptimo ni rentabilidad comercial definitiva. S6.3 necesita blindaje contra scope creep.

Decisión:
  1. No son criterio de cierre de Fase 1 en S6.3:
     - PnL final del usuario,
     - CLV,
     - edge temporal fino,
     - stake óptimo,
     - protocolo económico definitivo,
     - rentabilidad comercial final.
  2. Si alguno de esos temas entra al sprint, deberá hacerlo como exploración explícita o backlog posterior, no como bloqueo para cerrar verdad oficial, loop y elegibilidad.
  3. El foco normativo del sprint seguirá siendo:
     - verdad oficial,
     - cierre de loop,
     - elegibilidad reproducible,
     - lectura admin/reporte defendible.

Trazabilidad: US.md S6.3 (alcance), TASKS.md S6.3.

* * *

## D-06-050 — Acta T-244: contrato técnico Fase 1 congelado (2026-04-14)

Contexto: el handoff BE exige **T-244** antes de PR-BE-1. **D-06-044** listó estados genéricos incluyendo `evaluated_void_or_push`; la implementación v1 requiere literales únicos acordados en acta.

Decisión:

1. Queda normativa la mini acta [`ACTA_T244_CONTRATO_TECNICO_FASE_1.md`](./ACTA_T244_CONTRATO_TECNICO_FASE_1.md): fuente **SportMonks / CDM BT2**, mercados v1 **`1X2`** y **`TOTAL_GOALS_OU_2_5`**, estados y catálogo de motivos tal como en ese documento.
2. En **código, migraciones, jobs y APIs v1**, los estados de evaluación serán exactamente: `pending_result`, `evaluated_hit`, `evaluated_miss`, **`void`**, `no_evaluable`. Si hubiera conflicto con el listado genérico de **D-06-044** §3, prevalece el literal **`void`** de esta acta para la fase actual (no usar en paralelo `evaluated_void_or_push` salvo decisión explícita posterior).
3. Fuera de los mercados v1 del acta, el pick se trata como **`no_evaluable`** por diseño, según reglas allí descritas.

Trazabilidad: **T-244**, **PR-BE-1**, US-BE-049, US-BE-051.

* * *

Creación: 2026-04-14 — borrador inicial de decisiones normativas para bajar Fase 1 a backlog ejecutable en S6.3.
Pendiente de amarre en siguiente artefacto: `US.md` con IDs definitivos, criterios de aceptación y reparto BE/FE.