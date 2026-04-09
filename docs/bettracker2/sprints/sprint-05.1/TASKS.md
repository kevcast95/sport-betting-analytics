# Sprint 05.1 — TASKS

> **Handoff:** [`EJECUCION.md`](./EJECUCION.md). **Si hay duda de orden o deuda residual:** [`PENDIENTES_EJECUCION.md`](./PENDIENTES_EJECUCION.md).

> Numeración global: continúa desde **T-170** (Sprint 05 llegó a **T-169**).  
> **Decisiones:** [`DECISIONES.md`](./DECISIONES.md) **D-05.1-001** … **D-05.1-013**.  
> **US:** [`US.md`](./US.md).

## Backend — US-BE-029

- [x] **T-170** (US-BE-029) — **`POST /bt2/vault/premium-unlock`** (**D-05.1-002**): schema body/response; persistencia idempotente; ledger `pick_premium_unlock`; **`GET /bt2/vault/picks`** con **`premiumUnlocked`** por ítem; ajuste **`POST /bt2/picks`** sin doble −50; migración Alembic; tests/curl; bump **`contractVersion`** si aplica.

## Frontend — US-FE-040

- [x] **T-171** (US-FE-040) — **Store + VaultPage + PickCard:** separar estado “premium desbloqueado” vs “pick tomado”; wire slider → API unlock; CTA **Tomar** → `POST /bt2/picks`; badges y copy; guards liquidación coherentes con **US-FE-033**.
- [x] **T-172** (US-FE-040) — **Tests** (`useVaultStore`, flujo premium) + smoke manual checklist en `US.md`.

## DX *(opcional, si T-170 lo exige)*

- [x] **T-173** (US-DX-001-R1) — **Tipos TS + `contractVersion`** (`s5.3`) + campo vault; sin nuevos `reason` en ledger.

---

## Frontend — US-FE-043 *(RFB-01, RFB-10)*

- [x] **T-174** (US-FE-043) — **Componente cabecera V2** (`BunkerViewHeader` o equivalente): slots título / subtítulo opcional / ayuda (icono en círculo + «Cómo funciona» a la izquierda) / `rightActions`; **sin** «Actualizado ahora». Alineación **D-05.1-003**.

- [x] **T-175** (US-FE-043) — **Migrar vistas** V2: Sanctuary, Vault, Ledger, Performance, Profile, Daily review, Settlement (+ cualquier `/v2/*` con cabecera duplicada); eliminar strings legacy; un solo patrón de ayuda.

- [x] **T-176** (US-FE-043) — **Doc + verificación:** actualizar [`../../04_IDENTIDAD_VISUAL_UI.md`](../../04_IDENTIDAD_VISUAL_UI.md) §8; `npm test`; grep «Actualizado ahora» en `apps/web`; smoke recorrido V2.

---

## Frontend — US-FE-044 *(RFB-07, RFB-08)*

- [x] **T-177** (US-FE-044) — **RFB-07 / D-05.1-004:** `PickCard` — quitar párrafo largo post-inicio; opacidad reforzada; tag corto; `title`/tooltip en desktop; estándar + premium coherente.

- [x] **T-178** (US-FE-044) — **RFB-08 / D-05.1-005:** `PickCard` — premium `!isUnlocked`: sin preview `traduccionHumana`, sin `edgeBps`; mostrar cuota sugerida + datos mínimos acordados; layout compacto antes del slider.

- [x] **T-179** (US-FE-044) — **Tests** (`PickCard` / vault) + smoke bóveda; sin regresión **D-05-010** (Detalle estándar).

---

## Frontend — US-FE-045 *(RFB-11, RFB-12, RFB-13)*

- [x] **T-180** (US-FE-045) — **RFB-11 / D-05.1-006:** `LedgerPage.tsx` + `LedgerTable.tsx` — filtro y columna **clase de mercado**; bloque **tasa de acierto en el segmento**; copy sin “eficiencia del protocolo”; tour `ledger` si hace falta.

- [x] **T-181** (US-FE-045) — **RFB-12 / D-05.1-007:** `PerformancePage.tsx` + `tourScripts.ts` — subtítulo desde ledger; tarjeta **Chequeo operativo**; quitar check falso; pie tesorería; tour performance.

- [x] **T-182** (US-FE-045) — **RFB-13 / D-05.1-008:** `PerformancePage.tsx` — card banda DP con título/copy ilustrativo; **ocultar** bloque sentimiento; microcopy KPI (ROI / tasa) sin afirmaciones vacías de “protocolo”.

---

## Frontend — US-FE-046 *(RFB-02, RFB-03)*

- [x] **T-183** (US-FE-046) — **RFB-02 / D-05.1-009:** `SanctuaryPage.tsx` — quitar rótulo **«Santuario Zurich»**; coherente con **US-FE-043** al migrar cabecera si aplica.

- [x] **T-184** (US-FE-046) — **RFB-03 / D-05.1-010:** `SanctuaryPage.tsx` — recuadro **día operativo**: `operatingDayKey`, estación/cierre, gracia/pendientes desde `useSessionStore`; CTA **`/v2/daily-review`**; sin placeholder genérico.

---

## Frontend — US-FE-047 *(RFB-04)*

- [x] **T-185** (US-FE-047) — **D-05.1-011:** `GlossaryModal.tsx` — barra de búsqueda, filtro cliente, debounce, a11y; `npm test` si hay tests del modal.

---

## Frontend — US-FE-048 *(RFB-14)*

- [x] **T-186** (US-FE-048) — **D-05.1-012:** `BunkerLayout.tsx` + `useUserStore` — botón sync DP: **loading**, error **visible**, icono **≠ +**, toast éxito opcional; revisar interacción con **RFB-15**.

---

## Frontend — US-FE-049 *(RFB-15)*

- [x] **T-187** (US-FE-049) — **D-05.1-013:** Auditar **producción** (preview build); documentar Strict Mode si aplica; consolidar fetches en rutas V2 listadas; criterio ≤1 GET por endpoint en primera carga. *(Notas en [`EJECUCION.md`](./EJECUCION.md) § T-187; `VaultPage` sin `hydrateLedgerFromApi` en montaje.)*

---

## Check cierre 05.1

- [x] **D-05.1-001** y **D-05.1-002** reflejadas en comportamiento real FE+BE *(cierre formal doc 2026-04-08)*.
- [x] **D-05.1-003** reflejada en UI V2 (**T-174–T-176**).
- [x] **D-05.1-004** y **D-05.1-005** reflejadas en `PickCard` (**T-177–T-179**).
- [x] **D-05.1-006**, **D-05.1-007** y **D-05.1-008** reflejadas en ledger/rendimiento (**T-180–T-182**).
- [x] **D-05.1-009** … **D-05.1-013** reflejadas (**T-183–T-187**).
- [x] [`../../refinement_feedback_s1_s5/DECISIONES.md`](../../refinement_feedback_s1_s5/DECISIONES.md) **RFB-09** → **Acordado** + US **US-BE-029** / **US-FE-040** + tareas **T-170–T-172** (`US.md`, este archivo).
- [x] **RFB-01** y **RFB-10** → **Acordado** + **US-FE-043** + **T-174–T-176** cerradas.
- [x] **RFB-07** y **RFB-08** → **Acordado** + **US-FE-044** + **T-177–T-179** (mismo archivo refinement).
- [x] **RFB-11**, **RFB-12** y **RFB-13** → **Acordado** + **US-FE-045** + **T-180–T-182** ([`../../refinement_feedback_s1_s5/DECISIONES.md`](../../refinement_feedback_s1_s5/DECISIONES.md)).
- [x] **RFB-02**, **RFB-03**, **RFB-04**, **RFB-14**, **RFB-15** → **Acordado** en refinement + **US-FE-046 … US-FE-049**; implementación **T-183–T-187** cerrada en código/doc de cierre.
- [x] **Handoff siguiente oleada:** **US-FE-052+** en [`../sprint-06/US.md`](../sprint-06/US.md); **RFB-05/06** implementados en [`../sprint-05.2/`](../sprint-05.2/PLAN.md) (**US-FE-050/051**).

---

*Última actualización: 2026-04-08 — **Sprint 05.1 cerrado formalmente en documentación**; `npm test` apps/web **100/100** al validar cierre.*
