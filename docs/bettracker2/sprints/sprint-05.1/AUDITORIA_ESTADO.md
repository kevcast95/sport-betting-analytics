# Sprint 05.1 — Auditoría de estado (código vs backlog)

**Fecha revisión:** 2026-04-09.  
**Método:** inspección estática del repo (`apps/api`, `apps/web`) + `npm test` en `apps/web`.  
**No sustituye:** checkboxes en [`TASKS.md`](./TASKS.md) ni cierre formal PO/QA.

**Qué ejecutar ahora:** [`PENDIENTES_EJECUCION.md`](./PENDIENTES_EJECUCION.md) (05.1) · [`../sprint-05/PENDIENTES_CIERRE.md`](../sprint-05/PENDIENTES_CIERRE.md) (S5).

---

## Backend (US-BE-029 / T-170)

| Criterio | Estado |
|----------|--------|
| `POST /bt2/vault/premium-unlock` | **Hecho** (`bt2_router.py`, tabla `bt2_vault_premium_unlocks`, migración Alembic) |
| `premiumUnlocked` en `GET /bt2/vault/picks` | **Hecho** (schemas + router) |
| `POST /bt2/picks` sin doble −50 si ya hubo unlock | **Hecho** (lógica `already_premium_unlocked` / `charge_premium_unlock`) |
| T-173 DX | **Revisar** si `contractVersion` / OpenAPI quedaron alineados con el último bump esperado |

**Conclusión BE 05.1:** implementación **presente**; cerrar **T-170** en doc tras revisión del ejecutor + curl/QA.

---

## Frontend (05.1)

| Tarea | Estado revisión código | Notas |
|-------|-------------------------|--------|
| **T-171–T-172** (US-FE-040) | **Hecho** | `unlockPremiumVaultPick`, `POST premium-unlock`, `premiumUnlocked` en store/tests |
| **T-174** (cabecera) | **Hecho** | `BunkerViewHeader.tsx` existe |
| **T-175** (migrar vistas) | **Parcial** | `BunkerViewHeader` solo en **`VaultPage`**. Ledger, Performance, Profile, Sanctuary, Daily review, Settlement siguen con cabecera propia |
| **T-176** | **No verificado** | §8 identidad + grep «Actualizado ahora» — el grep en `apps/web` da **0** coincidencias |
| **T-177–T-179** (US-FE-044) | **Mayormente hecho** | `PickCard`: tag post-inicio, opacidad, premium bloqueado mínimo, sin párrafo largo en el tramo revisado |
| **T-180–T-182** (US-FE-045) | **Hecho** | Ledger «Clase de mercado» / tasa segmento; Performance «Chequeo operativo», banda DP, sin sentimiento fijo |
| **T-183** (RFB-02) | **Hecho** | No hay string «Santuario Zurich» |
| **T-184** (RFB-03) | **Parcial** | Tarjeta **«Día operativo (protocolo)»** con `operatingDayKey`, estación, CTA cierre — **correcto**. Sigue existiendo abajo el recuadro **«Estado del entorno»** con copy placeholder (**duplicado / deuda D-05.1-010**) |
| **T-185** (glosario) | **Hecho** | `GlossaryModal`: búsqueda + debounce + filtro |
| **T-186** (sync DP) | **Hecho** | `IconRestart`, «Sincronizando…», `dpSyncError` visible; `syncDpBalance` retorna boolean |
| **T-187** (doble fetch) | **No cerrado en esta auditoría** | `useAppInit` usa `syncedRef`; hace falta **Network** en build producción según **D-05.1-013** |

**Tests:** `npm test` en `apps/web` → **84 tests OK** (2026-04-09).

---

## Sprint 05 (cola previa a “cerrar capítulo”)

En [`../sprint-05/TASKS.md`](../sprint-05/TASKS.md) siguen **abiertas** (checkbox `[ ]`):

- **T-145** (US-FE-036) — Detalle pick liquidado → settlement  
- **T-147** (US-FE-037) — Copy/UI cierre día  
- **T-149** (US-FE-038) — Liquidación dual FE  
- **T-151** (US-FE-039) — Bankroll emulado UI  

Hasta que el equipo las **cierre**, **difiera con decisión en `DECISIONES.md`**, o las **mueva explícitamente a S6** en plan/US, **no** se puede afirmar “Sprint 05 cerrado”.

---

## RFB-05 / RFB-06 (bóveda franjas / post–kickoff)

**No implementado** en esta revisión (esperado: spec en refinement; US de implementación pendientes o S6+).

---

## ¿Se puede pasar a Sprint 06?

**No automáticamente**, por:

1. **Deuda Sprint 05** (T-145, T-147, T-149, T-151 o decisión documentada de aplazo).  
2. **05.1 FE incompleto:** **T-175** (cabecera en todas las vistas V2) y cierre de **T-184** (eliminar o fusionar el segundo bloque «Estado del entorno»).  
3. **T-187** sin evidencia de auditoría en producción.  
4. **TASKS.md** de 05.1 aún con checkboxes sin marcar (cierre administrativo).

**Cuando:** S5 + 05.1 cerrados según criterios de [`TASKS.md`](./TASKS.md) de cada sprint + [`PLAN.md`](./PLAN.md) (aviso renumeración S6).

---

*Generado en auditoría asistida; el owner humano confirma cierre.*
