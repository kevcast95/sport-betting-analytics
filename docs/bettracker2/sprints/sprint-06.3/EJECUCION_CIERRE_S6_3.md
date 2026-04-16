# Sprint 06.3 — EJECUCION_CIERRE

> **Propósito:** bajar [`DECISIONES_CIERRE_S6_3.md`](./DECISIONES_CIERRE_S6_3.md) (D-06-051 … D-06-054) a **tareas ejecutables**, **evidencia enlazable** y **orden de operación**.  
> **No sustituye** [`EJECUCION.md`](./EJECUCION.md) (evidencia detallada del corte **2026-04-14**); **complementa** la trazabilidad decisión → task → artefacto.  
> **Norma F2 (producto/datos, otro alcance):** [`DECISIONES_CIERRE_F2_S6_3_FINAL.md`](./DECISIONES_CIERRE_F2_S6_3_FINAL.md) — no es el mismo checklist que D-06-051…054; define Tier Base/A, familias core y KPI de cierre F2.  
> **Handoff operativo:** [`HANDOFF_CIERRE_S6_3.md`](./HANDOFF_CIERRE_S6_3.md) · **Tasks cierre:** [`TASKS_CIERRE_S6_3.md`](./TASKS_CIERRE_S6_3.md) · **US cierre:** [`US_CIERRE_S6_3.md`](./US_CIERRE_S6_3.md).

* * *

## 1. Matriz decisión → tarea → evidencia

| Decisión | Qué exige | Tasks (cierre) | Evidencia principal |
|----------|-----------|----------------|---------------------|
| **D-06-051** — Loop real | Picks reales → filas en `bt2_pick_official_evaluation`; job/SQL trazado | T-246, T-247, T-248 | [`EJECUCION.md`](./EJECUCION.md) § T-246, § T-247 / T-248 |
| **D-06-052** — Elegibilidad + admin | Auditoría real; summary y UI no “vacíos”; BD ↔ endpoint ↔ vista | T-249, T-250, T-251, T-254, T-255 | [`EJECUCION.md`](./EJECUCION.md) § T-249–T-251, § T-250; UI: [`EJECUCION_UI_FASE1.md`](./EJECUCION_UI_FASE1.md) |
| **D-06-053** — Paralelo F2 mínimo | Coverage por liga/mercado; conclusión corta | T-252, T-253 | [`EJECUCION.md`](./EJECUCION.md) § T-252 / T-253 |
| **D-06-054** — Cierre documental | `EJECUCION.md` completo + tasks marcables + brecha explícita si falla | T-256, T-257 | Este archivo + checklist en [`TASKS_CIERRE_S6_3.md`](./TASKS_CIERRE_S6_3.md) |

* * *

## 2. Orden de ejecución recomendado (una pasada)

1. **Entorno** (T-246): misma `BT2_DATABASE_URL` que API y jobs; `alembic` en head (tablas `bt2_pick_official_evaluation`, `bt2_pool_eligibility_audit`).
2. **Loop** (T-247–T-248): `scripts/bt2_cdm/job_official_pick_evaluation.py` (métricas / corrida real); SQL en `EJECUCION.md`.
3. **Auditoría pool** (T-249, T-251): `scripts/bt2_cdm/job_pool_eligibility_audit.py --operating-day-key YYYY-MM-DD`.
4. **Summary** (T-250): `GET /bt2/admin/analytics/fase1-operational-summary?operatingDayKey=…` + cruce con SQL.
5. **Paralelo F2** (T-252–T-253): lecturas por liga/mercado documentadas en `EJECUCION.md`.
6. **FE** (T-254–T-255): `/v2/admin/fase1-operational` + checklist; evidencia en `EJECUCION_UI_FASE1.md`.
7. **Cierre documental** (T-256–T-257): actualizar `EJECUCION.md`, marcar `TASKS_CIERRE_S6_3.md`, y **este** `EJECUCION_CIERRE_S6_3.md` como mapa de trazabilidad.

* * *

## 3. Ampliaciones de operación (post-decisiones, código reciente)

No forman parte del texto original de D-06-051…054, pero **cierran brechas operativas** detectadas al validar el admin:

| Necesidad | Acción | Referencia |
|-----------|--------|------------|
| Ver **hit/miss** sin depender solo del snapshot de bóveda | `POST /bt2/admin/operations/refresh-cdm-from-sm-for-operating-day` (o botón en la vista Fase 1) | [`EJECUCION_UI_FASE1.md`](./EJECUCION_UI_FASE1.md) |
| **Observabilidad** del pool cuando domina `INSUFFICIENT_MARKET_FAMILIES` | `BT2_POOL_ELIGIBILITY_MIN_FAMILIES` (default `2`); re-ejecutar job de auditoría tras cambiar env | `.env.example`, runbook `docs/bettracker2/runbooks/bt2_pool_eligibility_audit_job.md` |

* * *

## 4. Criterio de “cierre formal” (D-06-054)

S6.3 queda **cerrado formalmente** respecto de `DECISIONES_CIERRE_S6_3.md` cuando:

- [`EJECUCION.md`](./EJECUCION.md) contiene los cuatro bloques (loop, auditoría, admin/F2 mínimo, referencia FE).
- [`TASKS_CIERRE_S6_3.md`](./TASKS_CIERRE_S6_3.md) tiene las casillas T-246…T-257 alineadas con evidencia.
- No queda contradicción entre “todo cubierto” en tasks y texto que hable de pendientes obsoletos en otros docs; **este archivo** actúa como índice.

Si aparece una **brecha bloqueante**, la resolución permitida es la de **D-06-054 §4**: “implementado pero no cerrado operativamente” con brecha explícita — no cierre fingido.

* * *

*Creación: 2026-04-15 — ejecución y trazabilidad de [`DECISIONES_CIERRE_S6_3.md`](./DECISIONES_CIERRE_S6_3.md).*
