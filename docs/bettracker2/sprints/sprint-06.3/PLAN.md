# Sprint 06.3 — Plan (borrador)

**Estado:** definición inicial — **feedback, refinement y acotación de detalles** tras el cierre de **S6.2**.

**Rama Git de trabajo:** `sprint-06.3` (creada desde el commit de cierre S6.2 en `sprint-06.1`).

**Cierre del sprint anterior:** [`../sprint-06.2/CIERRE_S6_2.md`](../sprint-06.2/CIERRE_S6_2.md).

**Plan mejora base (datos / snapshot / DSR / coste — borrador + preguntas):** [`Plan_mejora_base.md`](./Plan_mejora_base.md).  
**Roadmap PO (norte, capas, frentes F1–F6, fases 0–4 — cuando hay “mucho en el aire”):** [`ROADMAP_PO_NORTE_Y_FASES.md`](./ROADMAP_PO_NORTE_Y_FASES.md).  
**Handoff liviano (contexto + identidad + integraciones + enlace al roadmap — nuevo chat):** [`CONTEXTO_Y_ROADMAP_HANDOFF.md`](./CONTEXTO_Y_ROADMAP_HANDOFF.md).

---

## 1. Objetivo

Bajar a **US y criterios de aceptación cerrados** los temas que quedaron como “casi listos” o ambiguos al cerrar S6.2: copy, flujos admin, datos, y **alineación explícita entre instrumentación y premisa de producto** (qué mide cada vista).

---

## 2. Temas iniciales (backlog de arranque)

Prioridad y orden los fija PO/BA en kickoff; esta lista **no** sustituye `US.md` cuando exista.

| Tema | Notas |
|------|--------|
| **Admin precisión DSR — premisa** | La vista debe poder **monitorizar y validar al modelo** sobre las **sugerencias de bóveda del día** (o unidad acordada), con **histórico** (tabla existente + opcional torta/barras/progreso), usando **resultado oficial** por evento (p. ej. SportMonks u otra fuente) donde aplique — **sin depender** solo de `bt2_picks` liquidados por usuario. Requiere US BE/FE y posible tabla o job de evaluación. |
| **Cubo C** | Historial de cuotas (**D-06-039**, **US-BE-042**) si entra en alcance. |
| **Regenerar (FSM)** | Cerrar **D-06-034** (opción reset), **US-BE-045**, **T-212–T-213** si producto lo prioriza. |
| **Pool global / vista usuario** | **US-BE-048**, **T-216** cuando el snapshot esté estable. |
| **Operación** | **T-220** runbooks; completar acta **D-06-035** si faltaba fecha/responsable. |
| **Regresión** | **T-223** documentada (pipeline §1.3–§1.5). |
| **Higiene backlog** | Reconciliar casillas de [`../sprint-06.2/TASKS.md`](../sprint-06.2/TASKS.md) con código (**opcional**, **D-06-031**). |

---

## 3. Artefactos a crear en S6.3

- [`US.md`](./US.md) — historias por capa cuando se acote alcance.
- [`TASKS.md`](./TASKS.md) — numeración continua desde el último ID acordado (p. ej. post **T-226**).
- [`DECISIONES.md`](./DECISIONES.md) — nuevas **D-06-0xx** solo cuando haya regla normativa nueva.
- [`EJECUCION.md`](./EJECUCION.md) — registro de avance y cierre S6.3.

---

*2026-04-09 — creado al actar cierre S6.2.*
