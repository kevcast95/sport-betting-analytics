# Sprint 05.2 — TASKS

> Numeración global: continúa desde **T-188** (Sprint 05.1 llega a **T-187**).  
> **Decisiones:** [`DECISIONES.md`](./DECISIONES.md).  
> **US:** [`US.md`](./US.md).  
> **Ejecución por rol:** [`EJECUCION.md`](./EJECUCION.md).

## Reglas

- **PO:** ratificar **D-05.2-001** (y gaps de **D-05.2-002**) antes de merge de **T-190** y cierre **T-194**.
- Orden sugerido: **T-188** → **T-189** → (**T-191** si aplica) → **T-190** → **T-192** → **T-193** → **T-194** → **T-195**.

---

## Backend — US-BE-030 *(RFB-06)*

- [x] **T-188** (US-BE-030) — **Pool (~15 candidatos) + `timeBand`:** composición diaria ampliada (**target 15** ítems en vault cuando CDM permite, **D-05.2-002** §6); derivar `timeBand` desde `kickoffUtc` + TZ usuario; tope duro documentado; wire desde tablas/CDM actuales; tests unitarios de franja/borde horario y de “pool por debajo del target”.

- [x] **T-189** (US-BE-030) — **OpenAPI + curl + regresión:** documentar `timeBand` y límites de lista; casos curl mínimos; no romper **GET /bt2/vault/picks** consumidores existentes sin bump coordinado.

---

## DX — US-DX-001-R2 *(opcional)*

- [x] **T-191** (US-DX-001-R2) — **Tipos + `contractVersion`:** `bt2Types.ts`, `bt2_dx_constants` / meta; solo si **T-188** cambia contrato visible.

---

## Backend — US-BE-031 *(RFB-05)*

- [x] **T-190** (US-BE-031) — **Post–kickoff canónico:** aplicar **D-05.2-001** en cálculo `isAvailable` y/o validación `POST /bt2/picks`; mensajes de error estables; tests tiempo/kickoff.

---

## Frontend — US-FE-050 *(RFB-06)*

- [x] **T-192** (US-FE-050) — **Switcher + ordenación:** Mezcla / Mañana / Tarde / Noche; filtrado y sort en cliente; integración `VaultPage` + `PickCard` según contrato.

- [x] **T-193** (US-FE-050) — **Cupo 3+2 + copy + tests:** contadores restantes; textos ES; tests de store/componente según patrón del repo; smoke manual.

---

## Frontend — US-FE-051 *(RFB-05)*

- [x] **T-194** (US-FE-051) — **Alineación UX a BE:** CTA, tags y errores de `POST` coherentes con **T-190**; sin ventana solo-FE si BE es estricto.

---

## Cierre sprint

- [x] **T-195** — **`npm test` apps/web** + smoke V2 bóveda + checklist **D-05.2-001/002** *(tests automatizados **100/100** 2026-04-08; smoke manual bóveda/post–kickoff según criterio PO en entrega).*

---

## Check trazabilidad refinement

- [x] **RFB-06** → **US-BE-030**, **US-FE-050**, **D-05.2-002** (índice refinement: **Cerrado** sprint-05.2).
- [x] **RFB-05** → **US-BE-031**, **US-FE-051**, **D-05.2-001** (índice refinement: **Cerrado** sprint-05.2).

---

*Última actualización: 2026-04-08 — **Sprint 05.2 cerrado formalmente en documentación** (T-188–T-195).*
