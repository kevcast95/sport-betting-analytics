# Sprint 05 — Tareas aún abiertas (orden sugerido para ejecutar)

**Fuente:** [`TASKS.md`](./TASKS.md).  
**Objetivo:** T-145, T-147, T-149, T-151 cerradas en código; checklist `npm test` marcado tras ejecución local.

---

## 1. Tareas numeradas (producto / código)

| Orden | ID | US | Qué es (resumen) | Par BE / nota |
|-------|-----|-----|------------------|----------------|
| **1** | **T-145** | US-FE-036 | **Detalle** en `PickCard` → misma ruta **settlement** aunque el pick esté **liquidado**; `SettlementPage` en modo **solo lectura**; no redirigir por defecto a vault (**D-05-013**). Ledger / deep links alineados. | **T-152** ya **[x]** — contrato listo. |
| **2** | **T-147** | US-FE-037 | **Copy/UI cierre del día:** toasts, Daily Review, comunicar **recompensa por cerrar** + evitar −50; consumir respuesta **T-146** sin hardcodear N. | **T-146** ya **[x]**. |
| **3** | **T-149** | US-FE-038 | **Liquidación dual (FE):** `settlementVerificationMode` desde meta; badges/copy; stubs discrepancia sin inventar estados. | **T-148** ya **[x]**. |
| **4** | **T-151** | US-FE-039 | **Bankroll emulado:** reconciliación UI, copy void/mercado; si el contrato expone reserva/comprometido, mostrarlo. | **T-150** ya **[x]**. |

**Racional del orden:** **T-145** desbloquea navegación coherente vault ↔ settlement (muy visible). **T-147** aprovecha API de cierre ya existente. **T-149** y **T-151** son capas de pulido / modo dual / bankroll.

---

## 2. Checklist de cierre del propio `TASKS.md` (Sprint 05)

Siguen **sin marcar** al final de [`TASKS.md`](./TASKS.md):

- [x] **`npm test`** en `apps/web` (2026-04-07); **smoke BT2** manual contra API local sigue siendo responsabilidad del operador.
- [ ] Bloque **D-05-012 … D-05-019:** confirmar alineación PO; [`BE_HANDOFF_SPRINT05.md`](./BE_HANDOFF_SPRINT05.md) actualizado.

---

## Alternativa PM: diferir a S6

Si el PO acepta **postponer** alguna de **T-145 / T-147 / T-149 / T-151**:

1. Añadir línea en [`DECISIONES.md`](./DECISIONES.md) del sprint activo (05 o 06).  
2. Renumerar o copiar la tarea en [`../sprint-06/TASKS.md`](../sprint-06/TASKS.md).  
3. Marcar en S5 como **Diferido S6** (no dejar `[ ]` sin explicación).

---

*Última actualización: 2026-04-09.*
