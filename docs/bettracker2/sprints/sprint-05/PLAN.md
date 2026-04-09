# Sprint 05 — Planificación

> **Rama:** `sprint-05` · **Estado:** en planificación.  
> **Sprint 04:** cerrado (ver [`../sprint-04/US.md`](../sprint-04/US.md)).

## 1. Decisión de calendario (acuerdo PM + FE)

Lo que el **BA_PM_BE** posicionaba como **“Sprint 5 vs 6”** en el chat de motor/CDM se **corre una iteración**:

| Contenido (resumen BA) | Antes (etiqueta BA) | **Ahora (nuestro calendario)** |
|------------------------|---------------------|--------------------------------|
| DSR + CDM, cron `fetch_upcoming`, normalización mercados enum, US-DX/OpenAPI, analytics picks/bóveda | Sprint 5 motor | **Sprint 6** (planificar en `sprint-06/` cuando exista) |
| Parlays, 7 opciones, liquidación AND, milestones DP, límite 2 parlays/día | Sprint 6 | **Sprint 7** |
| **Cierre técnico V2:** dp-ledger UI, hidratar ledger desde API, estados de pick, coherencia DP/penalizaciones/**desbloqueo premium** en servidor | Mezclado con S5 BA | **Sprint 5 (este sprint)** |

**Sprint 05 = refacto + deuda API-first del Búnker V2 + contratos mínimos que BE debe cerrar en paralelo**, sin arrastrar el bloque completo DSR/cron/analytics a este sprint.

## 2. Objetivo del Sprint 05 (una frase)

Dejar **V2** con **fuente de verdad servidor** para picks abiertos/liquidados y movimientos DP visibles, más **UX de compromiso** con el pick; que BE complete **ledger en desbloqueo premium (−50) y penalizaciones** y, si aplica, **resumen día** o contratos (`US-DX`) **definidos en este mismo sprint** (placeholders en [`US.md`](./US.md)). **Ampliación Sprint 05:** **US-FE-034** elimina mocks creíbles en Santuario/Perfil/Bóveda y fija decisiones **D-05-006–009**; **US-BE-019** (borrador) para hora de evento en vault.

## 3. Alcance explícito **fuera** de Sprint 05

- Integración **DeepSeek Reasoner** con CDM y diseño anti-fuga en backtest → **Sprint 6**.
- **Cron** producción de `fetch_upcoming` + runbook → **Sprint 6** (u OPS en mismo hito).
- **Analytics** picks/bóveda (producto amplio) → **Sprint 6** salvo criterio explícito de “MVP analytics” que el equipo recorte.
- **Parlays** (tablas, reglas, DSR propone legs) → **Sprint 7**.
- **Recalibración automática** del diagnóstico con historial longitudinal → **Sprint 7** (más allá de US-BE-016).
- **unit_value_cop** por sesión (D-04-001) → backlog; no objetivo S5 salvo decisión contraria.

## 4. Proceso

1. **FE:** ejecuta US-FE-031 … US-FE-034 (tareas `T-126+`, incl. **T-134–T-139**) según [`TASKS.md`](./TASKS.md).  
2. **BE:** **US-BE-017 / 018** y **US-DX-001** (**T-131–T-133**); opcional en el mismo sprint **US-BE-019** (vault) si desbloquea hora en bóveda.  
3. **Orden típico:** contrato/BE donde bloquee FE; luego FE hidrata y pinta.

## 5. Próximos archivos

- [`US.md`](./US.md) — historias FE + stubs BE/DX.  
- [`TASKS.md`](./TASKS.md) — numeración global continúa en **T-126** (S5); **Sprint 06** continúa en **T-153** — ver [`../sprint-06/TASKS.md`](../sprint-06/TASKS.md).  
- [`DECISIONES.md`](./DECISIONES.md) — **D-05-001** calendario S5 vs S6/S7.

## 6. Sprint 06 (planificación adelantada)

- [`../sprint-06/PLAN.md`](../sprint-06/PLAN.md) — motor DSR + CDM, cron, enum mercados, DX, analytics.  
- [`../sprint-06/US.md`](../sprint-06/US.md), [`../sprint-06/TASKS.md`](../sprint-06/TASKS.md), [`../sprint-06/DECISIONES.md`](../sprint-06/DECISIONES.md).

---

*Última actualización: 2026-04-04 — alineación con BA_PM_BE y corrimiento motor → S6/S7.*
