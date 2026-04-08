# Sprint 06 — Instrucciones de ejecución (por rol)

> **Estado del sprint:** en **definición** — ver [`PLAN.md`](./PLAN.md) §6 antes de ejecutar código a escala.  
> **Precedente:** Sprints **05 / 05.1 / 05.2** cerrados en doc; numeración FE **US-FE-052+** en este sprint (**US-FE-050/051** viven en [`../sprint-05.2/US.md`](../sprint-05.2/US.md)).

## Lectura por rol

| Rol | Bloque |
|-----|--------|
| **Backend** | [Bloque 1 — Backend](#bloque-1--backend) |
| **Frontend** | [Bloque 2 — Frontend](#bloque-2--frontend) |
| **DX / contratos** | [Bloque 3 — DX](#bloque-3--dx-openapi--tipos) |
| **Operación** | [Bloque 4 — OPS](#bloque-4--ops-runbook) |

**Fuentes de verdad:** [`US.md`](./US.md), [`TASKS.md`](./TASKS.md), [`DECISIONES.md`](./DECISIONES.md).

---

## Coordinación (orden sugerido entre equipos)

1. **PO + BE:** cerrar gaps **D-06-002** (fases DSR / anti-fuga) y **D-06-004** (MVP analytics).
2. **DX** (**T-153–T-156**) en paralelo con **BE** mercados (**T-161–T-162**) y spike/pipeline **DSR** (**T-157–T-158**) según riesgo.
3. **BE** **T-159** (cron `fetch_upcoming`) + **OPS** **T-160** (runbook) antes de asumir ingesta diaria en prod.
4. **BE** **T-163–T-164** (analytics) antes de **FE** **T-166** (vista analytics).
5. **FE** **T-165** (narrativa DSR en bóveda) cuando exista contrato estable desde **T-158** + **US-DX-002**.
6. **FE** **T-167** (labels mercado canónico) tras **T-161** y catálogo DX.
7. **T-168** — cierre transversal tests + smoke.

**Dos devs BE:** repartir **DSR** (**T-157–T-158**) vs **mercados** (**T-161–T-162**) vs **cron** (**T-159**).  
**Dos devs FE:** repartir **bóveda DSR** (**T-165**) vs **analytics** (**T-166**) vs **labels** (**T-167**).

---

## Bloque 1 — Backend

### US

| US | Tema |
|----|------|
| **US-BE-025** | Pipeline DSR + CDM (anti-fuga) — **D-06-002** |
| **US-BE-026** | Job programado `fetch_upcoming` — **D-06-005** |
| **US-BE-027** | Mercados canónicos en picks / settle — **D-06-003** |
| **US-BE-028** | Endpoints analytics MVP — **D-06-004** |

### Tareas (ver orden en [`TASKS.md`](./TASKS.md))

- **T-157**, **T-158** — US-BE-025  
- **T-159** — US-BE-026  
- **T-161**, **T-162** — US-BE-027  
- **T-163**, **T-164** — US-BE-028  

### Handoff mínimo al FE

- Contrato vault/snapshot con campos DSR acordados en **US-DX-002** (sin JSON crudo de proveedor).
- **`marketCanonical`** (o homólogo) + labels humanos donde aplique.
- Analytics: shapes estables para **T-166**.

---

## Bloque 2 — Frontend

### US

| US | Tema |
|----|------|
| **US-FE-052** | Bóveda: narrativa / señales modelo (DSR) |
| **US-FE-053** | Vista analytics MVP |
| **US-FE-054** | Labels mercado canónico en UI |

### Tareas

- **T-165** — US-FE-052  
- **T-166** — US-FE-053  
- **T-167** — US-FE-054  
- **T-168** — cierre `npm test` + smoke S6  

---

## Bloque 3 — DX (OpenAPI + tipos)

### US

| US | Tema |
|----|------|
| **US-DX-002** | Catálogo mercados, DSR I/O, `operatorProfile`, `contractVersion` — **D-06-006** |

### Tareas

- **T-153** — `MarketCanonical` + constantes Python/TS  
- **T-154** — Schemas DSR I/O  
- **T-155** — `operatorProfile` + alinear `reason` ledger vs OpenAPI  
- **T-156** — Bump `contractVersion` + nota handoff  

---

## Bloque 4 — OPS (runbook)

### US

| US | Tema |
|----|------|
| **US-OPS-001** | Runbook cron CDM + alertas — **D-06-005** |

### Tareas

- **T-160** — Documentación operativa enlazada desde **D-06-005** y [`PLAN.md`](./PLAN.md)

---

*Última actualización: 2026-04-08 — definición inicial S6 en rama dedicada.*
