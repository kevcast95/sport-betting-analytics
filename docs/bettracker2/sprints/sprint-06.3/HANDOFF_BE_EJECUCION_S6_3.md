# Handoff — Ejecución Backend Sprint 06.3 (Fase 1)

> Orden óptimo, división en PRs y reglas duras para BE.  
> Backlog detallado: [`TASKS.md`](./TASKS.md). US: [`US.md`](./US.md). Decisiones: [`DECISIONES.md`](./DECISIONES.md).  
> **Acta T-244 (contrato congelado):** [`ACTA_T244_CONTRATO_TECNICO_FASE_1.md`](./ACTA_T244_CONTRATO_TECNICO_FASE_1.md) · norma **D-06-050**.

---

## 0. Congelar el contrato técnico antes de picar código

### Por qué esto va primero (y qué significa “lo último”)

En el flujo ideal, **después** de escribir este handoff el **siguiente paso operativo** no es abrir `bt2_models.py`, sino **rellenar y congelar** la mini acta de Fase 1 (**T-244**). Eso es lo que en la conversación se llamó “el último paso”: no es una tarea nueva misteriosa, sino **cerrar el kickoff técnico en papel** para que el código no improvisé nombres de estados, mercados o fuentes.

Si BE implementa sin acta:

- aparecen enums distintos entre migración, job y admin;
- el “hit rate” se redefine a mitad de sprint;
- FE recibe contratos que cambian cada PR.

Por eso **T-244 se adelanta al inicio** del orden de ejecución (aunque en `TASKS.md` siga numerada como tarea de gobernanza): es el **candado** antes de **PR-BE-1**.

**Quién la rellena:** típicamente **TL + BE** con validación **PO** en las partes de producto (mercados soportados, motivos de descarte entendibles).  
**Cuándo:** antes del merge del primer PR de dominio (**PR-BE-1**).  
**Dónde (cerrado):** el contenido normativo vive en **[`ACTA_T244_CONTRATO_TECNICO_FASE_1.md`](./ACTA_T244_CONTRATO_TECNICO_FASE_1.md)**; este handoff solo resume y ordena el trabajo. La decisión de repo es **D-06-050**.

### Qué debe cerrar la mini acta (T-244)

Equivale a **cuatro** decisiones explícitas:

1. **Fuente oficial de verdad** — qué sistema o tabla alimenta el “resultado oficial” del evento/mercado (p. ej. adapter a API X, tabla `raw_*`, regla de lectura post-partido). Sin esto no hay trazabilidad de `truth_source`.
2. **Subconjunto inicial de mercados soportados** — lista cerrada v1 (p. ej. 1X2 + O/U goles 2.5). Fuera de lista → `no_evaluable` por diseño, no por bug.
3. **Estados de evaluación del pick** — nombres finales y significado (p. ej. `pending_result`, `evaluated_hit`, …) alineados a **T-228**; mismos strings en DB, job y métricas.
4. **Catálogo canónico de motivos de descarte** — códigos estables para elegibilidad (pool), alineados a **T-237** y a lo que verá el admin/FE en **coverage**.

Sin esto congelado, **no** se abren PRs de implementación de dominio.

### Estado de la acta (T-244)

| Ítem | Estado |
|------|--------|
| Documento | **[`ACTA_T244_CONTRATO_TECNICO_FASE_1.md`](./ACTA_T244_CONTRATO_TECNICO_FASE_1.md)** — texto completo, criterios de interpretación, nota `EVENT_NOT_SETTLED`, resolución. |
| Norma en `DECISIONES.md` | **D-06-050** — enlaza el acta; fija literales de estado v1 (`void` vs variante genérica `evaluated_void_or_push` de D-06-044). |
| PO | Aprobado en acta (2026-04-14). |
| TL | **OK** — literales del acta acordados para implementación (migración/job/admin/FE). |

**Resumen ejecutivo para codificar (no sustituye el acta):**

1. **Verdad:** SportMonks / CDM BT2; base `raw_sportmonks_fixtures` hacia normalización BT2; nunca liquidación usuario.
2. **Mercados v1:** `1X2`, `TOTAL_GOALS_OU_2_5`; resto → `no_evaluable` (o descarte elegibilidad).
3. **Estados:** `pending_result`, `evaluated_hit`, `evaluated_miss`, `void`, `no_evaluable` — **sin alias** en DB/job/API/FE.
4. **Motivos descarte:** catálogo en tabla del acta (`MISSING_FIXTURE_CORE`, …).

**Checklist de salida §0:** [x] acta en repo; [x] D-06-050; [x] T-244 en TASKS; [x] **TL OK** — listo para **PR-BE-1**.

---

## 1. Fundar la capa normativa de evaluación

**Tareas:** **T-227** + **T-228**.

**Objetivo:** persistencia y estados del pick listos.

**Entregable mínimo:** tabla/modelo donde ya existan, como mínimo: `pick_id`, `event_id`, claves canónicas de mercado/selección, timestamps, `evaluation_status`, `truth_source` (y ref a payload de verdad si aplica).

---

## 2. Resolver el mapeo pick → verdad oficial

**Tareas:** **T-229** + **T-230**.

- No intentar soportar **todos** los mercados: solo el subconjunto mínimo acordado en kickoff (acta §0).
- **Regla dura:** si no hay mapeo reproducible, ese pick cae en **`no_evaluable`**; no se inventa resultado.

---

## 3. Cerrar el loop de verdad

**Tareas:** **T-231** + **T-232**.

- Job/comando/servicio que toma `pending_result` y resuelve contra resultado oficial.
- Prioridad: **vertical slice real** en batch manual reproducible; scheduling después si hace falta.
- No bloquear el sprint en un orquestador “bonito” antes de demostrar el cierre.

---

## 4. Exponer contadores operativos del loop

**Tareas:** **T-233** + **T-234**.

Debe poder responder ya:

- cuántos picks fueron emitidos;
- cuántos cerraron;
- cuántos siguen pendientes;
- cuántos quedaron no evaluables;
- **hit rate solo sobre evaluados** (ver reglas abajo).

El **runbook** mínimo conviene documentarlo **aquí**, no al final: ayuda a QA y a FE.

---

## 5. Implementar elegibilidad v1 del pool

**Tareas:** **T-235** + **T-236** + **T-237**.

Orden interno recomendado:

1. Evaluador **determinístico** (sin heurísticas blandas ni LLM).
2. **Persistencia** de auditoría.
3. **Catálogo de descarte** + tests.

Regla mínima ya cerrada desde Fase 0: fixture utilizable, cuotas válidas, al menos **2 familias** de mercado y ausencia de faltantes críticos en `ds_input`.

---

## 6. Lectura admin (contrato limpio para FE)

**Tareas:** **T-238** + **T-239** + **T-240**.

Recomendación: **endpoint resumen** + **endpoint detalle**, o un solo payload con secciones **claramente separadas**.

Estructura lógica (no mezclar):

| Sección | Contenido típico |
|--------|-------------------|
| **coverage** | Pool / elegibilidad / descartes |
| **loop** | Emitidos, pendientes, cerrados, no evaluables |
| **performance** | Hit rate y desgloses sobre **evaluados** |

No publicar contrato FE hasta **congelar** nombres de estados y shape del payload.

---

## 7. Cierre técnico

**Tarea:** **T-245**.

Regresión, build, evidencia y checklist final.

---

## División sugerida en PRs BE

| PR | Contenido |
|----|-----------|
| **PR-BE-1** | T-244 adelantado (acta Fase 1) + **T-227** + **T-228** |
| **PR-BE-2** | **T-229** + **T-230** + **T-231** + **T-232** |
| **PR-BE-3** | **T-233** + **T-234** + **T-235** + **T-236** + **T-237** |
| **PR-BE-4** | **T-238** + **T-239** + **T-240** + **T-245** |

---

## Reglas duras (BE)

| Regla | Detalle |
|--------|---------|
| Hit rate | **No** calcular sobre picks pendientes. |
| `no_evaluable` | **No** esconder; debe ser visible y contable aparte. |
| Verdad del modelo | **No** usar liquidación del usuario como verdad oficial. |
| Contrato FE | **No** publicar hasta congelar estados y shape. |
| Alcance mercados | **No** cubrir todos los mercados en esta fase; solo subconjunto defendible. |

**Premisa Fase 0:** el éxito se mide contra **resultado oficial**, con unidad base en el **pick sugerido**, sobre universo **elegible** y **trazable**.

---

*Creación: 2026-04-14 — alineado a instrucciones de ejecución BE para S6.3 Fase 1. §0: acta en [`ACTA_T244_CONTRATO_TECNICO_FASE_1.md`](./ACTA_T244_CONTRATO_TECNICO_FASE_1.md) + D-06-050.*
