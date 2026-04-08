# Sprint 05.1 — Instrucciones de ejecución (BE / FE)

## Handoff único

**A todos los ejecutores:** el mismo archivo (**`EJECUCION.md`** en esta carpeta). No hace falta un documento distinto por persona: **cada rol lee y ejecuta solo su bloque** (BE → Bloque 1; FE → Bloque 2).

**Frase para el equipo:** un solo enlace — este **`EJECUCION.md`** del 05.1; **el BE solo el Bloque 1**, **el FE solo el Bloque 2**; si hay dudas de orden con tareas abiertas, **[`PENDIENTES_EJECUCION.md`](./PENDIENTES_EJECUCION.md)**.

### Mensaje tipo — Backend (copiar / pegar)

> Abrí **`EJECUCION.md`** del 05.1 y seguí **solo** la sección **«Bloque 1 — Backend»**. Objetivo: **US-BE-029** → tareas **T-170** (obligatoria) y **T-173** (solo si cambió el contrato). Criterios y payloads: **`US.md`** + **`DECISIONES.md`** **D-05.1-001** / **D-05.1-002**. Handoff al FE: lo que lista el propio Bloque 1 — **`POST /bt2/vault/premium-unlock`**, **`premiumUnlocked`** en vault y **`POST /bt2/picks`** sin doble −50.
>
> *Si en la práctica **T-170** / **T-173** ya están hechas:* revisá que el **Bloque 1** esté cumplido en [`TASKS.md`](./TASKS.md) y avisá al FE si falta algo.

### Mensaje tipo — Frontend (copiar / pegar)

> Mismo **`EJECUCION.md`**; seguí **solo** **«Bloque 2 — Frontend»** y el **orden sugerido** (**T-174** → … → **T-187**). Detalle por historia: **`US.md`**; checkboxes: **`TASKS.md`**. Si todavía hay cierre pendiente, sumá el enlace a **[`PENDIENTES_EJECUCION.md`](./PENDIENTES_EJECUCION.md)** como orden concreto (p. ej. T-175, T-184, T-176, T-187). Cierre: **`npm test`**, smoke que lista el propio doc, checklist **Check cierre 05.1** en **`TASKS.md`**.

| Quién | Qué hace |
|-------|----------|
| **Backend** | Solo **Bloque 1**. Criterios en [`US.md`](./US.md) **US-BE-029** y [`DECISIONES.md`](./DECISIONES.md) **D-05.1-001/002**; tareas **T-170**, **T-173**. |
| **Frontend** | Solo **Bloque 2**. Detalle en [`US.md`](./US.md); checkboxes en [`TASKS.md`](./TASKS.md) **T-174 … T-187**. |

**Coordinación:** el FE asume **T-171–T-172** cuando **T-170** ya esté en el entorno compartido; el BE avisa cuando eso ocurra. El resto del FE puede avanzar en paralelo siguiendo el orden del Bloque 2.

**Contexto PO (opcional):** [`../../refinement_feedback_s1_s5/DECISIONES.md`](../../refinement_feedback_s1_s5/DECISIONES.md).

**Dos devs FE:** repartir dentro del **Bloque 2** como arriba (p. ej. uno **cabecera + bóveda + PickCard**, otro **ledger + rendimiento + santuario + glosario + sync**); **T-187** al final o con quien tocó **`useAppInit`** / stores.

---

**Fuente de verdad complementaria:** [`US.md`](./US.md), [`TASKS.md`](./TASKS.md), [`DECISIONES.md`](./DECISIONES.md).

---

## Bloque 1 — Backend (y DX ligado al contrato)

### US a ejecutar

| US | Tema |
|----|------|
| **US-BE-029** | `POST /bt2/vault/premium-unlock`, `premiumUnlocked` en vault, `POST /bt2/picks` sin doble −50 DP (**RFB-09**, **D-05.1-001**, **D-05.1-002**) |
| **US-DX-001-R1** *(opcional)* | Tipos TS / `contractVersion` / `bt2_dx_constants` **solo si** **T-170** cambia el contrato visible |

### Tareas

- **T-170** (US-BE-029) — única tarea BE obligatoria del sprint 05.1.
- **T-173** (US-DX-001-R1) — solo si **T-170** introduce campos o códigos nuevos.

### Orden sugerido

1. **T-170** primero: sin esto, el FE no puede cerrar el flujo desbloqueo ≠ tomar contra API real.
2. **T-173** enseguida si aplica (mismo PR o PR siguiente alineado con FE), para no bloquear tipos en el cliente.

### Handoff mínimo al FE

- Endpoint **`POST /bt2/vault/premium-unlock`** documentado y probado (curl/tests).
- **`GET /bt2/vault/picks`** con **`premiumUnlocked`** por ítem.
- Comportamiento **`POST /bt2/picks`** sin segundo cargo `pick_premium_unlock` cuando ya hubo unlock válido.

---

## Bloque 2 — Frontend

### US a ejecutar (todas las de refinement 05.1 en FE)

| US | Tema (RFB / D) |
|----|----------------|
| **US-FE-043** | Cabecera V2, sin «Actualizado ahora», ayuda a la izquierda (**RFB-01, RFB-10**, **D-05.1-003**) |
| **US-FE-040** | Bóveda: unlock premium y tomar pick en dos pasos (**RFB-09**; depende de **US-BE-029**) |
| **US-FE-044** | `PickCard`: post-inicio + premium bloqueado mínimo (**RFB-07, RFB-08**, **D-05.1-004/005**) |
| **US-FE-045** | Ledger + Rendimiento: copy honesto (**RFB-11 … RFB-13**, **D-05.1-006 … 008**) |
| **US-FE-046** | Santuario: quitar «Zurich» + recuadro día operativo (**RFB-02, RFB-03**, **D-05.1-009/010**) |
| **US-FE-047** | Glosario: búsqueda (**RFB-04**, **D-05.1-011**) |
| **US-FE-048** | Sidebar: sincronizar DP con feedback (**RFB-14**, **D-05.1-012**) |
| **US-FE-049** | Doble fetch en carga V2 (**RFB-15**, **D-05.1-013**) |

### Tareas (por US)

| Tareas | US |
|--------|-----|
| **T-174, T-175, T-176** | US-FE-043 |
| **T-171, T-172** | US-FE-040 |
| **T-177, T-178, T-179** | US-FE-044 |
| **T-180, T-181, T-182** | US-FE-045 |
| **T-183, T-184** | US-FE-046 |
| **T-185** | US-FE-047 |
| **T-186** | US-FE-048 |
| **T-187** | US-FE-049 |

### Orden sugerido (dependencias)

1. **T-174** → **T-175** → **T-176** (**US-FE-043**): componente de cabecera antes de migrar vistas; **T-176** cierra con doc §8 + tests + grep.
2. **T-171** → **T-172** (**US-FE-040**): **después** de que **T-170** (BE) esté disponible en el entorno que use el FE (o feature flag acordado); incluye store, `VaultPage`, `PickCard`.
3. **T-177** → **T-178** → **T-179** (**US-FE-044**): encaja bien a continuación de la bóveda (**PickCard**).
4. **T-180** → **T-181** → **T-182** (**US-FE-045**): ledger y rendimiento; pueden ir en paralelo al bloque anterior si hay dos desarrolladores.
5. **T-183** → **T-184** (**US-FE-046**): Santuario; ideal **después** de **T-175** en esa página para no duplicar trabajo de cabecera (o rebase cuando **T-175** toque `SanctuaryPage`).
6. **T-185** (**US-FE-047**): glosario; independiente.
7. **T-186** (**US-FE-048**): sidebar / `syncDpBalance`; conviene tener **T-175** estable en layout si el control vive en `BunkerLayout`.
8. **T-187** (**US-FE-049**) **al final** (o tras los bloques que cambian hidratación: **T-171**, `useAppInit`, etc.): auditar doble fetch en build tipo producción y consolidar.

### Nota sobre **T-180 … T-182**

Parte del diff puede **ya existir** en el repo (sesión previa fuera del hilo BA/PM); el ejecutor marca **DoD** en [`TASKS.md`](./TASKS.md) tras revisión y `npm test`, no solo por presencia de cambios.

### Cierre global FE

- `npm test` en `apps/web`.
- Smoke V2: bóveda (unlock + tomar), Santuario, ledger, rendimiento, glosario, sync DP.
- Checklist de cierre en [`TASKS.md`](./TASKS.md) (sección **Check cierre 05.1**).
- Si quedan ítems abiertos fuera de este orden, seguir **[`PENDIENTES_EJECUCION.md`](./PENDIENTES_EJECUCION.md)**.

### Registro de ejecución (automática / local)

| Fecha | Qué se ejecutó | Resultado |
|-------|----------------|-----------|
| **2026-04-07** | `apps/web`: `npm test -- --run` | **84/84** OK |
| **2026-04-07** | `apps/web`: `npm run build` | **OK** (`tsc -b` + `vite build`) |
| **2026-04-07** | `rg 'Actualizado ahora' apps/web` | **0** coincidencias |
| **2026-04-07** | API local `GET /openapi.json` (si corre en `127.0.0.1:8000`) | Ruta **`premium-unlock`** presente en spec |

*Smoke navegador (unlock premium + tomar pick contra API) sigue siendo el criterio humano para tickear **D-05.1-001** / **D-05.1-002** en [`TASKS.md`](./TASKS.md).*

### T-187 — Red (primera carga) y React Strict Mode (dev)

- **Strict Mode (`<React.StrictMode>` en `main.tsx`):** en **desarrollo** React puede **montar efectos dos veces** para detectar efectos impuros. Eso puede mostrar **pares de GET** idénticos en Network **solo en dev**; en **build preview/prod** (sin doble montaje de desarrollo) la expectativa es **≤1 GET por endpoint** en la primera carga tras login, salvo rutas que disparen refrescos explícitos (p. ej. invalidación de bóveda al cambiar `operatingDayKey`).
- **Consolidación:** la hidratación inicial compartida vive en **`useAppInit`** (`apps/web/src/hooks/useAppInit.ts`): `refreshMe` (si falta `userId`), `syncFromApi`, `syncDpBalance`, `hydrateFromApi`, `hydrateLedgerFromApi`. **`VaultPage`** no debe volver a llamar a `hydrateLedgerFromApi` en el montaje solo por entrar a la ruta; reservar esa llamada para **acciones** que mutan picks/ledger (unlock, tomar, etc.).

---

## Cuando terminen 05.1 — siguiente oleada

**RFB-05 / RFB-06** ya están en backlog **[`../sprint-05.2/`](../sprint-05.2/PLAN.md)**: **franjas** (mañana/tarde/noche + switcher en FE), **~15 candidatos** en **`GET /bt2/vault/picks`** cuando haya stock (**T-188**, **D-05.2-002** §6), **`timeBand`** por ítem, **post–kickoff** canónico en BE (**T-190**). Handoff: **[`../sprint-05.2/EJECUCION.md`](../sprint-05.2/EJECUCION.md)** — **Bloque Backend** / **Bloque Frontend**, **T-188+** en [`../sprint-05.2/TASKS.md`](../sprint-05.2/TASKS.md).

---

*Última actualización: 2026-04-07 — directrices BA + registro de ejecución FE (tests/build); puntero 05.2.*
