# Sprint 06 — Instrucciones de ejecución (por rol)

> **Estado del sprint:** **en ejecución** — backlog **T-153–T-170** (**D-06-017**; **D-06-018** + **D-06-019** lotes v1-equivalentes); paralelismo **FE ∥ BE** (y DX/OPS) según dependencias por tarea.  
> **Precedente:** Sprints **05 / 05.1 / 05.2** cerrados en doc; numeración FE **US-FE-052+** en este sprint (**US-FE-050/051** viven en [`../sprint-05.2/US.md`](../sprint-05.2/US.md)).

## Lectura por rol

| Rol | Ir a |
|-----|------|
| **Backend** | [Bloque 1 — Backend](#bloque-1--backend) (**§1.1–1.4** = paquetes por US-BE) |
| **Frontend** | [Bloque 2 — Frontend](#bloque-2--frontend) (**§2.1–2.4** = paquetes por US-FE) |
| **DX / contratos** | [Bloque 3 — DX](#bloque-3--dx-openapi--tipos) |
| **Operación** | [Bloque 4 — OPS](#bloque-4--ops-runbook) |

**Fuentes de verdad:** [`US.md`](./US.md), [`TASKS.md`](./TASKS.md), [`DECISIONES.md`](./DECISIONES.md).

**Ejecución de punta a punta (una sola guía, orden cerrado):** [`EJECUCION_COMPLETA_PUNTA_A_PUNTA.md`](./EJECUCION_COMPLETA_PUNTA_A_PUNTA.md) — incluye **`BT2_ADMIN_API_KEY`**, snapshot al abrir sesión, y criterios de “todo corre”.

---

## Corroboración: ¿ya está contemplado el orden FE después de BE?

**Sí.** Este archivo ya lo decía en **Coordinación** (puntos 3–4: **T-163–T-164** antes de **T-166**; **T-165** tras contrato **T-158** + DX DSR; **T-167** tras mercados + DX). **`TASKS.md`** repite la regla en su cabecera (“**US-BE-028** antes de **US-FE-053**”). Lo que faltaba era **dejarlo explícito por bloque** para que cada agente vea *su* paquete y *qué espera del otro*: eso vive en la **matriz** y en **§1.x / §2.x** siguientes.

---

## Matriz dependencias (FE consume BE / DX)

| Tarea FE | No intentar cerrar sin (mínimo) | Nota |
|----------|----------------------------------|------|
| **T-165** (bóveda DSR) | **T-158** + **T-154** (o shapes acordados en vault/snapshot) | UI contra API real o stub alineado a contrato. |
| **T-166** (admin precisión DSR) | **T-163** (+ **T-164** si aplica copy `*_human_es`) | Ver [`TASKS.md`](./TASKS.md) T-166 y ref [`refs/us_fe_055_admin_dsr_accuracy.html`](./refs/us_fe_055_admin_dsr_accuracy.html). |
| **T-167** (labels canónicos) | **T-161–T-162** + **T-153** (catálogo / tipos) | PickCard, settlement, ledger. |
| **T-168** | Resto estable o en rama integrada | `npm test` + smoke manual S6. |

| Tarea BE | Convive en paralelo con | Bloquea principalmente a |
|----------|---------------------------|---------------------------|
| **T-157–T-158** | **T-154**, **T-153** | **T-165** |
| **T-161–T-162** | **T-153** | **T-167** |
| **T-163–T-164** | Núcleo picks/settle persistido (DSR + canónico según diseño) | **T-166** |
| **T-159** | **T-160** (documentación OPS) | Ingesta programada, no bloquea FE salvo dependencia de datos |

---

## Coordinación (orden sugerido entre equipos)

1. **DX** (**T-153–T-156**) **desde día 1** en paralelo con **BE** y con **FE** solo en trabajo que no asuma JSON final (shell, rutas, estados vacío).
2. **BE** **T-159** + **OPS** **T-160** en el mismo sprint; entorno prod/staging según **T-160**.
3. **BE** **T-163–T-164** antes de **cerrar** **FE** **T-166**; **FE** **T-165** cuando haya **T-158** + contrato DSR mínimo (**T-154**).
4. **FE** **T-167** cuando **T-161–T-162** y catálogo **T-153** estén alineados en API.
5. **T-168** — cierre transversal.

**Dos devs BE:** repartir **DSR** (**T-157–T-158**) vs **mercados** (**T-161–T-162**) vs **cron** (**T-159**); **analytics** (**T-163–T-164**) cuando el modelo de datos lo permita.  
**Dos devs FE:** repartir **T-165** / **T-166** / **T-167** según prerequisitos de la matriz.

---

## Bloque 1 — Backend

Paquetes independientes **entre sí en lo posible**; el orden crítico para el FE está en la **matriz** arriba.

### 1.1 US-BE-025 — DSR + CDM (**D-06-002**, **D-06-018**, **D-06-019**)

| | |
|--|--|
| **Tareas** | **T-157** / **T-158** (contrato + vault), **T-169** (DeepSeek en vivo), **T-170** (**lotes v1-equivalentes** — obligatorio producto PO; no sustituir por “1 evento/request” sin excepción firmada) |
| **DX recomendable** | **T-154** (DSR I/O); **T-153** en paralelo si toca mercado en salida |
| **Referencia v1** | [`jobs/deepseek_batches_to_telegram_payload_parts.py`](../../../../jobs/deepseek_batches_to_telegram_payload_parts.py) — **picks_by_event** / lotes; **D-06-019** |
| **Desbloquea FE** | **T-165** (narrativa bóveda); el FE debe tratar ambos `dsrSource` sin asumir siempre LLM |

### 1.2 US-BE-026 — Cron `fetch_upcoming` (**D-06-005**)

| | |
|--|--|
| **Tareas** | **T-159** |
| **OPS** | Coordinar con **T-160** |
| **Desbloquea** | Ingesta programada; impacto indirecto en datos del día para CDM/DSR |

### 1.3 US-BE-027 — Mercados canónicos (**D-06-003**)

| | |
|--|--|
| **Tareas** | **T-161** (migración + ACL), **T-162** (settle + vault exponen canónico) |
| **DX recomendable** | **T-153** (`MarketCanonical` + tipos) |
| **Desbloquea FE** | **T-167** |

### 1.4 US-BE-028 — Analytics MVP (**D-06-004**)

| | |
|--|--|
| **Tareas** | **T-163** (endpoints agregados), **T-164** (`*_human_es` donde aplique) |
| **Precisa** | Picks/snapshot con lógica de medición alineada a **D-06-015** (hit/miss/void persistidos o calculables en servidor según diseño) |
| **Desbloquea FE** | **T-166** |

### Handoff mínimo al FE (consolidado)

- Vault/snapshot: campos DSR acordados en **US-DX-002** (sin JSON crudo de proveedor).
- **`marketCanonical`** (o homólogo) + labels humanos donde aplique.
- Analytics: contrato estable para **T-166** (paths, query params, shapes de KPIs y filas de auditoría).

---

## Bloque 2 — Frontend

Cada subapartado = un paquete para el agente FE; **prerrequisitos** = criterio de “done” integrado.

### 2.1 US-FE-052 — Bóveda narrativa DSR

| | |
|--|--|
| **Tarea** | **T-165** |
| **Prerrequisitos BE/DX** | **T-158**; contrato DSR en API (**T-154** / OpenAPI) |
| **Entregable** | Componentes + copy; loading/error; sin datos proveedor crudos |

### 2.2 US-FE-053 — Vista analytics / admin precisión DSR

| | |
|--|--|
| **Tarea** | **T-166** |
| **Prerrequisitos BE/DX** | **T-163**; **T-164** si el FE consume `*_human_es` |
| **Referencia visual** | [`refs/us_fe_055_admin_dsr_accuracy.html`](./refs/us_fe_055_admin_dsr_accuracy.html) |
| **Alcance** | Solo ítem sidebar + contenido de página (ver texto completo en [`TASKS.md`](./TASKS.md)); sin CSV S6 (**D-06-010**) |

### 2.3 US-FE-054 — Labels mercado canónico

| | |
|--|--|
| **Tarea** | **T-167** |
| **Prerrequisitos BE/DX** | **T-161–T-162**; **T-153** (tipos/enum alineados) |
| **Entregable** | Mapa desde API; settlement + ledger + `PickCard` |

### 2.4 Cierre transversal

| | |
|--|--|
| **Tarea** | **T-168** |
| **Qué es** | `npm test` + smoke manual S6 tras integrar **T-165–T-167** según ramas |

---

## Bloque 3 — DX (OpenAPI + tipos)

### US

| US | Tema |
|----|------|
| **US-DX-002** | Catálogo mercados, DSR I/O, `operatorProfile`, `contractVersion` — **D-06-006** |

### Paquetes por tarea (agente DX / quien lleve contrato)

| Tarea | Contenido | Desbloquea principalmente |
|-------|-----------|----------------------------|
| **T-153** | `MarketCanonical` + `bt2_dx_constants.py` + `bt2Types.ts` | **T-161**, **T-167** |
| **T-154** | Schemas DSR I/O, `pipeline_version`, checklist **D-06-002** | **T-157**, **T-158**, **T-165** |
| **T-155** | `operatorProfile` + alinear `reason` ledger vs OpenAPI | FE/BE según exposición en API |
| **T-156** | Bump `contractVersion` en `GET /bt2/meta` + nota handoff | Todos los consumidores FE |

---

## Bloque 4 — OPS (runbook)

### US

| US | Tema |
|----|------|
| **US-OPS-001** | Runbook cron CDM + alertas — **D-06-005** |

### Tarea

- **T-160** — Documentación operativa enlazada desde **D-06-005** y [`PLAN.md`](./PLAN.md); baseline **D-06-013** hasta canal/on-call real (**D-06-011**).

---

*Última actualización: 2026-04-08 — S6 en ejecución (**D-06-017**); matriz FE/BE y §1.x/2.x para agentes.*
