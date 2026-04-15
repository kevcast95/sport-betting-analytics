# Handoff — Cierre real Sprint 06.3

> Orden óptimo de ejecución para cerrar honestamente S6.3.
> Backlog de cierre: `TASKS_CIERRE_S6_3.md`.
> US: `US_CIERRE_S6_3.md`.
> Decisiones: `DECISIONES_CIERRE_S6_3.md`.
> Base de contexto: `CIERRE_RESTANTE_S6_3.md`.
> Este handoff no redefine el sprint: solo ordena la operación final y la evidencia.

* * *

## 0. Regla madre de este cierre

Lo pendiente ya no es construir nuevas capacidades principales.

Lo que falta es:

1. operar la capacidad ya construida con datos reales,
2. evidenciarla,
3. validar el admin con datos no vacíos,
4. y cerrar el mínimo paralelo de F2 sin convertirlo en otro sprint.

Si durante la ejecución aparece una brecha operativa real, debe quedar documentada; no se maquilla el cierre.

* * *

## 1. Orden óptimo BE

### Paso 1 — Confirmar entorno real de validación
Tareas: T-246.

Qué debe quedar claro:
* qué entorno se usará,
* qué ventana real se validará,
* qué `operating_day_key` o rango se tomará como muestra.

Salida mínima:
* entorno identificado,
* ventana identificada,
* acceso a BD/job confirmado.

### Paso 2 — Demostrar loop oficial real
Tareas: T-247, T-248.

Objetivo:
* correr el job/backfill de official evaluation sobre picks reales,
* confirmar filas reales en `bt2_pick_official_evaluation`,
* documentar estados observados.

Reglas duras:
* no usar fixtures de test como evidencia principal,
* no depender de liquidación usuario,
* si solo hay `pending_result`, eso sirve como evidencia mínima si está bien trazado.

Salida mínima:
* SQL o salida de job,
* subconjunto real procesado,
* evidencia anexable a `EJECUCION.md`.

### Paso 3 — Demostrar elegibilidad/auditoría real
Tareas: T-249, T-250, T-251.

Objetivo:
* correr auditoría sobre eventos reales,
* confirmar filas en `bt2_pool_eligibility_audit`,
* validar summary admin contra BD.

Reglas duras:
* el patrón “sin auditoría reciente” no puede seguir siendo la lectura dominante en la ventana validada,
* no basta con decir “la lógica existe”; debe haber filas reales.

Salida mínima:
* coverage real observado,
* descarte por causa principal,
* consistencia BD ↔ endpoint documentada.

### Paso 4 — Cerrar mínimo paralelo F2
Tareas: T-252, T-253.

Objetivo:
* validar si la regla mínima actual de elegibilidad sirve con datos reales.

Reglas duras:
* esto no abre F2 completo,
* no se rediseña `ds_input`,
* no se abre tiers,
* no se mete snapshot/frescura.

Salida permitida:
* o “la regla actual se sostiene”,
* o “requiere un único ajuste puntual”.

* * *

## 2. Orden óptimo FE

### Paso 1 — Esperar backend con datos reales
FE no debe validar la vista final usando solo mocks en este cierre.
El punto de arranque real FE es cuando BE ya tenga:
* evidence de loop,
* evidence de auditoría,
* y summary/backend con datos no vacíos.

### Paso 2 — Validar `/v2/admin/fase1-operational`
Tareas: T-254, T-255.

Checklist visual mínimo:
* candidatos > 0,
* con auditoría reciente > 0,
* con fila evaluación oficial > 0,
* picks reales visibles al menos en `pending_result` cuando aplique,
* consistencia con summary/backend.

Reglas duras:
* no mezclar pendientes o no evaluables dentro del hit rate,
* no corregir números en frontend,
* no bloquear el cierre por polish visual.

Salida mínima:
* evidencia funcional y/o screenshots útiles,
* consistencia UI ↔ endpoint ↔ BD reportada.

* * *

## 3. Orden conjunto de ejecución

### Secuencia recomendada

1. **BE**
   * T-246
   * T-247
   * T-248

2. **BE**
   * T-249
   * T-250
   * T-251

3. **BE**
   * T-252
   * T-253

4. **FE**
   * T-254
   * T-255

5. **Cierre conjunto**
   * T-256
   * T-257

* * *

## 4. Qué debe quedar en `EJECUCION.md`

`EJECUCION.md` debe salir de este cierre con cuatro bloques explícitos:

1. evidencia de loop oficial real,
2. evidencia de auditoría/elegibilidad real,
3. evidencia de vista admin con datos no vacíos,
4. resultado de validación mínima del paralelo F2.

Si falta uno de esos cuatro, S6.3 no queda cerrado realmente.

* * *

## 5. Qué NO debe pasar ahora

No hacer en este cierre:

* rediseño completo de F2,
* snapshot/frescura,
* CLV,
* costo,
* UX futura,
* expansión fuerte de mercados,
* megaproyecto de completitud.

Este handoff existe para **cerrar S6.3 honestamente**, no para agrandarlo.

* * *

## 6. Resolución esperada

La salida correcta de este handoff debe terminar en una de estas dos conclusiones:

### A. S6.3 cerrado realmente
Con evidencia operativa real, admin validado, paralelo F2 mínimo cerrado y documentación actualizada.

### B. S6.3 implementado pero no cerrado operativamente
Con brecha explícita documentada y sin fingir cierre.

* * *

Creación: 2026-04-14 — handoff de ejecución para cierre restante de S6.3.