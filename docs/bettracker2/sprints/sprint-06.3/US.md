# Sprint 06.3 — US

> Base normativa: `PLAN.md`, `DECISIONES.md`, `ROADMAP_PO_NORTE_Y_FASES.md`.
> Cierre previo: `../sprint-06.2/US.md` y `../sprint-06.2/TASKS.md`.
> Base aprobada de Fase 0: `CIERRE_FASE_0_MODELO_Y_METRICA_DATOS.md`.
> Contrato de formato US: `../../01_CONTRATO_US.md`.
> Numeración continua: BE desde `US-BE-049`; FE desde `US-FE-061`.
> Convención: cambios de alcance en código → nueva US o nueva DECISIÓN.

### Convención

S6.3 baja a ejecución la Fase 1 ya acotada:
- verdad oficial del modelo,
- cierre de loop por pick,
- elegibilidad reproducible del pool,
- lectura admin/reporte defendible.

No entra aquí:
- PnL usuario,
- CLV,
- stake,
- edge temporal fino,
- rentabilidad comercial,
- ni dashboard final sofisticado.

* * *

## Matriz de trazabilidad (decisiones → US)

Decisión | US
--- | ---
D-06-043 verdad oficial | US-BE-049, US-BE-050, US-FE-061
D-06-044 unidad base = pick | US-BE-049, US-BE-050, US-FE-061
D-06-045 elegibilidad v1 | US-BE-051, US-BE-052, US-FE-061
D-06-046 auditoría de elegibilidad | US-BE-051, US-BE-052, US-FE-061
D-06-047 cierre de loop obligatorio | US-BE-049, US-BE-050, US-FE-061
D-06-048 salida mínima admin/reporte | US-BE-052, US-FE-061
D-06-049 fuera de alcance Fase 1 | alcance transversal S6.3

* * *

## Backend — verdad oficial y evaluación

### US-BE-049 — Evaluación oficial por pick: modelo base, estados y persistencia

#### 1) Objetivo de negocio

Tener una capa base de evaluación por pick que permita medir precisión del modelo contra resultado oficial, sin depender de la liquidación del usuario en app.

#### 2) Alcance

- Incluye: modelo persistido o tabla equivalente para registrar evaluación por pick; claves mínimas del pick; estado de evaluación; verdad oficial utilizada; timestamps de emisión y evaluación; soporte para los estados v1 del acta T-244 (`pending_result`, `evaluated_hit`, `evaluated_miss`, `void`, `no_evaluable` — ver **D-06-050**).
- Incluye: criterio de mapeo reproducible entre pick emitido y resultado oficial del mercado, al menos para el subconjunto inicial acordado en kickoff.
- Excluye: UI admin; visualización de métricas; PnL y settlement económico del usuario.

#### 3) Reglas de dominio

- La unidad base de evaluación es el pick sugerido.
- Ningún pick sin verdad oficial trazable puede computarse como `hit` o `miss`.
- Está prohibido mezclar en una misma métrica picks evaluados con picks pendientes o no evaluables sin separarlos.

#### 4) Criterios de aceptación

1. Existe persistencia auditable por pick con estado de evaluación y verdad oficial usada.
2. Un pick de prueba puede quedar explícitamente en `hit`, `miss`, `void` o `no_evaluable` según inputs controlados (literales de evaluación según acta T-244).
3. Si falta mapeo o verdad oficial, el sistema deja evidencia explícita de `no_evaluable` en vez de asumir resultado.

#### 5) Definition of Done

- Migración/modelo y contrato interno implementados.
- Tests de estados mínimos y de caso no evaluable.
- Nota de mapeo inicial documentada en PR o anexo técnico.

Madre: nueva en S6.3.

* * *

### US-BE-050 — Cierre de loop contra resultado oficial: job o servicio de evaluación

#### 1) Objetivo de negocio

Cerrar el loop real del sistema evaluando picks emitidos contra resultado oficial de forma backend, sin depender de que el usuario abra la app o liquide algo manualmente.

#### 2) Alcance

- Incluye: job, comando o servicio backend que tome picks pendientes y los evalúe cuando exista resultado oficial disponible.
- Incluye: política mínima de reintento o reevaluación segura para picks aún sin resultado.
- Incluye: métricas base derivadas sobre picks evaluados.
- Excluye: refresh manual admin si no es estrictamente necesario; dashboard final; detalle económico.

#### 3) Dependencias

- Bloqueante: US-BE-049.
- Requiere fuente oficial de resultado ya accesible o un adapter mínimo reproducible.

#### 4) Criterios de aceptación

1. Un lote de picks pendientes puede pasar a evaluado mediante ejecución backend reproducible.
2. El proceso no depende de `bt2_picks` liquidados por usuario para declarar `hit` o `miss`.
3. El sistema puede reportar al menos: picks emitidos, picks evaluados, picks pendientes, picks no evaluables, hit rate sobre evaluados.

#### 5) Definition of Done

- Job/servicio implementado.
- Tests o dry-run documentado con evidencia de transición `pending_result` → estado final.
- Runbook mínimo de ejecución/manual fallback si aplica.

Madre: nueva en S6.3.

* * *

## Backend — elegibilidad y cobertura del pool

### US-BE-051 — Elegibilidad v1 del pool: regla reproducible y auditoría persistida

#### 1) Objetivo de negocio

Operativizar la regla mínima de elegibilidad aprobada en Fase 0 para que el pool analizable tenga un criterio reproducible y auditable.

#### 2) Alcance

- Incluye: evaluación determinística de elegibilidad por evento candidato.
- Incluye: persistencia de resultado `eligible` / `ineligible`, timestamp, versión de regla y motivo canónico de descarte.
- Incluye: chequeos mínimos sobre fixture utilizable, cuotas válidas, >= 2 familias de mercado y ausencia de faltantes críticos en `ds_input`.
- Excluye: refinamientos avanzados de calidad de dato; heurísticas con LLM; política avanzada de score de cobertura.

#### 3) Reglas de dominio

- La elegibilidad se calcula sin LLM.
- Ningún evento no elegible entra al universo válido para medir precisión del modelo.
- Los motivos de descarte deben ser semánticamente útiles y estables.

#### 4) Criterios de aceptación

1. Un evento de prueba que cumple la regla entra como `eligible`.
2. Eventos que fallan por fixture, cuotas, familias de mercado o faltantes críticos quedan como `ineligible` con motivo explícito.
3. La evaluación deja persistencia suficiente para reconstrucción posterior.

#### 5) Definition of Done

- Regla v1 implementada.
- Persistencia de auditoría implementada.
- Tests por cada causa principal de descarte.

Madre: nueva en S6.3.

* * *

### US-BE-052 — Admin API / reporte operativo: elegibilidad, cobertura y precisión oficial

#### 1) Objetivo de negocio

Exponer una lectura operativa mínima que separe claramente cobertura del pool, estado de cierre de loop y desempeño del modelo.

#### 2) Alcance

- Incluye: endpoint(s) o servicio(s) admin para consultar:
  - eventos candidatos,
  - eventos elegibles,
  - `pool_eligibility_rate`,
  - motivos de descarte,
  - picks emitidos,
  - picks evaluados,
  - picks no evaluables,
  - hit rate global sobre evaluados,
  - hit rate por mercado,
  - hit rate por bucket de confianza, si existe.
- Incluye: filtros básicos por día y/o unidad operativa acordada.
- Excluye: dashboard final sofisticado; gráficos avanzados; vistas usuario final.

#### 3) Dependencias

- Requiere US-BE-050 y US-BE-051 al menos en versión mínima.
- Si expone contrato consumido por FE, debe dejar esquema estable para cliente admin.

#### 4) Criterios de aceptación

1. La respuesta separa explícitamente cobertura del pool, loop y precisión.
2. `pool_eligibility_rate` sale de la auditoría persistida, no de conteos ad hoc.
3. El hit rate se calcula solo sobre picks evaluados.
4. Si existen picks no evaluables, aparecen como capa explícita y no se esconden dentro del hit rate.

#### 5) Definition of Done

- Endpoint(s) o reporte operativo implementado(s).
- OpenAPI / schema actualizado si aplica.
- Casos de prueba o checklist manual documentado sobre lectura mínima.

Madre: nueva en S6.3.

* * *

## Frontend

### US-FE-061 — Admin UI: verdad oficial, cierre de loop y elegibilidad del pool

#### 1) Objetivo de negocio

Dar al equipo una superficie admin mínima para leer el sistema con la premisa correcta: verdad oficial, no liquidación usuario; cobertura del pool separada de precisión del modelo.

#### 2) Alcance

- Incluye: vista admin o pantalla equivalente que consuma la salida de US-BE-052.
- Incluye: bloques mínimos visibles para:
  - eventos candidatos,
  - eventos elegibles,
  - `pool_eligibility_rate`,
  - motivos de descarte,
  - picks emitidos,
  - picks evaluados,
  - picks no evaluables,
  - hit rate global y por mercado,
  - bucket de confianza si aplica.
- Incluye: separación visual clara entre cobertura, loop y desempeño.
- Excluye: visualización perfecta; charts complejos; experiencia pública de usuario.

#### 3) Reglas de producto

- La vista no debe sugerir que la precisión viene de apuestas liquidadas por el usuario.
- Si hay picks pendientes o no evaluables, deben verse explícitamente.
- La lectura debe priorizar claridad operativa sobre estética final.

#### 4) Criterios de aceptación

1. Un usuario admin puede distinguir sin ambigüedad:
   - cobertura del pool,
   - estado del cierre de loop,
   - precisión del modelo.
2. La UI muestra `pool_eligibility_rate` y desglose de descarte.
3. La UI no mezcla picks pendientes/no evaluables dentro del hit rate.
4. La superficie es usable aunque sea austera.

#### 5) Definition of Done

- Vista admin conectada a contrato real.
- Estados vacíos / loading / error mínimos resueltos.
- QA manual con evidencia en `EJECUCION.md` cuando exista.

Madre: US-FE-059 como antecedente de UI admin, sin reutilizar su premisa de auditoría CDM.

* * *

Última actualización: 2026-04-14 — borrador inicial S6.3 orientado a Fase 1 (verdad oficial, loop, elegibilidad, admin).