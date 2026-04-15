# Sprint 06.3 — US_CIERRE

> Base normativa: `PLAN.md`, `DECISIONES.md`, `DECISIONES_CIERRE_S6_3.md`, `ROADMAP_PO_NORTE_Y_FASES.md`.
> Base vigente del sprint: `US.md`, `TASKS.md`, `EJECUCION.md`.
> Documento base de cierre: `CIERRE_RESTANTE_S6_3.md`.
> Contrato de formato US: `../../01_CONTRATO_US.md`.
> Numeración continua: BE desde `US-BE-053`; FE desde `US-FE-062`.
> Convención: cambios de alcance en código → nueva US o nueva DECISIÓN.

### Convención

Este documento no redefine Fase 0 ni abre F2 completo.
Solo baja el cierre restante de S6.3 a ejecución real, separando:

* pendiente operativo de Fase 1,
* validación mínima paralela de F2 dentro de S6.3,
* y cierre documental honesto del sprint.

* * *

## Matriz de trazabilidad (decisiones → US)

Decisión | US
--- | ---
D-06-051 evidencia operativa real del loop | US-BE-053, US-BE-054, US-FE-062
D-06-052 elegibilidad + admin con datos reales | US-BE-054, US-FE-062
D-06-053 paralelo mínimo F2 | US-BE-055
D-06-054 cierre formal documentado | US-BE-053, US-BE-054, US-BE-055, US-FE-062

* * *

## Backend — cierre operativo real de Fase 1

### US-BE-053 — Operación real del loop oficial con picks reales

#### 1) Objetivo de negocio

Demostrar que la capacidad ya implementada de evaluación oficial por pick y cierre de loop funciona con picks reales del sistema, no solo con tests o fixtures.

#### 2) Alcance

* Incluye: validación de migraciones/tablas en entorno real; ejecución de job o backfill sobre uno o más `operating_day_key`; confirmación de filas en `bt2_pick_official_evaluation`; evidencia SQL o salida de job; documentación del subconjunto real procesado.
* Incluye: confirmación de estados reales al menos en `pending_result` y, cuando exista verdad oficial disponible, también estados evaluados.
* Excluye: rediseñar la lógica de evaluación; ampliar mercados fuera del subconjunto v1; recalcular PnL o settlement usuario.

#### 3) Dependencias

* Requiere que el slice principal de Fase 1 ya esté desplegado o disponible en el entorno validado.
* Requiere acceso a picks reales en `bt2_daily_picks`.

#### 4) Criterios de aceptación

1. Existe evidencia de un subconjunto real de picks identificado por `operating_day_key`.
2. Esos picks generan filas reales en `bt2_pick_official_evaluation`.
3. La evidencia muestra estados reales (`pending_result` y/o evaluados) sin depender de liquidación del usuario.
4. Queda documentado el comando/job/SQL utilizado para producir y verificar esa evidencia.

#### 5) Definition of Done

* Evidencia operativa real del loop anexada en `EJECUCION.md`.
* SQL o salida de job documentada.
* Estado del cierre reflejado en `TASKS_CIERRE_S6_3.md`.

Madre: US-BE-049, US-BE-050.

* * *

### US-BE-054 — Operación real de elegibilidad/auditoría y validación backend del summary admin

#### 1) Objetivo de negocio

Demostrar que la capa de elegibilidad, su auditoría persistida y el summary admin funcionan con datos reales y producen lectura útil del sistema.

#### 2) Alcance

* Incluye: correr la auditoría de elegibilidad sobre eventos reales del día o ventana validada.
* Incluye: confirmación de filas reales en `bt2_pool_eligibility_audit` con `is_eligible` o `primary_discard_reason`.
* Incluye: validación del endpoint summary contra BD con datos no vacíos.
* Incluye: documentación del coverage real y de los motivos de descarte observados.
* Excluye: rediseño de la regla mínima; sistema avanzado de tiers; nueva arquitectura de datos.

#### 3) Dependencias

* Requiere US-BE-051 y US-BE-052 ya implementadas.
* Requiere ventana real con eventos candidatos suficientes para validar coverage.

#### 4) Criterios de aceptación

1. Existen eventos reales con filas en `bt2_pool_eligibility_audit`.
2. El patrón dominante “sin auditoría reciente” deja de ser la explicación principal en la ventana validada.
3. El summary admin refleja coverage real no vacío y consistente con BD.
4. Queda documentada la evidencia SQL y/o de endpoint usada para validar.

#### 5) Definition of Done

* Evidencia de auditoría real anexada en `EJECUCION.md`.
* Endpoint summary validado contra BD.
* Coverage y descarte real documentados para el cierre del sprint.

Madre: US-BE-051, US-BE-052.

* * *

## Backend — paralelo mínimo F2 dentro de S6.3

### US-BE-055 — Validación mínima de coverage real por liga/mercado y decisión corta si aplica

#### 1) Objetivo de negocio

Validar si la regla mínima actual de elegibilidad se sostiene con datos reales y producir, solo si hace falta, una enmienda corta para poder cerrar S6.3 honestamente.

#### 2) Alcance

* Incluye: medir coverage real por liga y por mercado piloto.
* Incluye: leer descarte por causa principal.
* Incluye: evaluar si la regla mínima actual produce un pool razonable para el corte actual.
* Incluye: nota de validación final y, solo si aplica, propuesta de una única decisión corta adicional.
* Excluye: rediseño completo de F2, tiers avanzados, snapshot/frescura, re-arquitectura de `ds_input`, expansión fuerte de mercados.

#### 3) Reglas de dominio

* Este frente no puede crecer para comerse el sprint.
* Si la regla actual sirve, la salida correcta es “se sostiene para este corte”.
* Si no sirve, la salida máxima permitida es una única enmienda corta.

#### 4) Criterios de aceptación

1. Existe lectura real de coverage por liga y mercado.
2. Existe lectura real de descarte por causa principal.
3. Se emite una conclusión explícita: “la regla actual se sostiene” o “requiere ajuste mínimo puntual”.
4. Si hubo ajuste mínimo, queda trazado en decisión/documento adicional corto.

#### 5) Definition of Done

* Validación mínima F2 documentada en `EJECUCION.md`.
* Recomendación final explícita emitida.
* Sin apertura de backlog grande nuevo dentro de S6.3.

Madre: D-06-045, D-06-046; nuevo cierre operativo.

* * *

## Frontend

### US-FE-062 — Validación operativa de la vista admin con datos reales no vacíos

#### 1) Objetivo de negocio

Confirmar que la vista `/v2/admin/fase1-operational` funciona correctamente con datos reales, no vacíos y consistentes con backend y BD.

#### 2) Alcance

* Incluye: validación de la vista con datos reales provenientes del summary/backend.
* Incluye: revisión de candidatos, auditoría reciente, evaluación oficial y estados reales visibles.
* Incluye: evidencia visual o funcional de consistencia con la capa backend validada.
* Excluye: cambios cosméticos grandes; nuevo dashboard; UX futura.

#### 3) Dependencias

* Requiere US-BE-053 y US-BE-054 al menos en versión operativa real.
* Requiere ruta admin desplegada o accesible en entorno validado.

#### 4) Criterios de aceptación

1. La vista muestra datos reales no vacíos.
2. La vista refleja al menos:
   * candidatos > 0,
   * con auditoría reciente > 0,
   * con fila evaluación oficial > 0,
   * y picks reales al menos en `pending_result` cuando aplique.
3. La lectura visual es consistente con endpoint y BD.
4. La evidencia funcional queda documentada para cierre del sprint.

#### 5) Definition of Done

* Validación visual/funcional anexada en `EJECUCION.md` o anexo asociado.
* Consistencia endpoint ↔ UI revisada.
* Estado final del frente reflejado en `TASKS_CIERRE_S6_3.md`.

Madre: US-FE-061.

* * *

Última actualización: 2026-04-14 — backlog final de cierre real para S6.3.