# Sprint 05.2 — US

> **Decisiones:** [`DECISIONES.md`](./DECISIONES.md) **D-05.2-001** … **D-05.2-003**.  
> **Tareas:** [`TASKS.md`](./TASKS.md) **T-188+**.  
> **Refinement:** **RFB-05**, **RFB-06** — [`../../refinement_feedback_s1_s5/DECISIONES.md`](../../refinement_feedback_s1_s5/DECISIONES.md).

## Resumen

| ID | Capa | Título |
|----|------|--------|
| US-BE-030 | BE | Bóveda: **pool diario** amplio, **franjas** (`timeBand`) y composición por TZ usuario (**RFB-06**) |
| US-BE-031 | BE | Bóveda: **post–kickoff** canónico en `isAvailable` + validación **`POST /bt2/picks`** (**RFB-05**) |
| US-FE-050 | FE | Bóveda: **switcher franja / mezcla**, lista filtrada en cliente, **cupo** 3+2 visible (**RFB-06**) |
| US-FE-051 | FE | Bóveda: UX alineada a **política D-05.2-001** (sin “Tomar” fantasma) (**RFB-05**) |
| US-DX-001-R2 | DX | *(Opcional)* `timeBand`, tope de lista, bump **`contractVersion`** si el BE cambia el contrato vault |

---

## Backend

### US-BE-030 — Pool diario y metadatos de franja *(RFB-06)*

#### 1) Objetivo de negocio

El operador recibe en **`GET /bt2/vault/picks`** un conjunto **suficiente** de candidatos del **día operativo** para poder usar el **switcher** de franja **sin** nuevo round-trip, con priorización y relleno descritos en **D-05.2-002**.

#### 2) Alcance

- **Incluye:** ampliar o sustituir la lógica de selección desde CDM / `bt2_daily_picks` (o capa actual) para el **`operatingDayKey`** activo; respetar reglas **`accessTier`** / premium existentes.
- **Incluye:** calcular **`timeBand`** por ítem usando **`kickoffUtc`** + **TZ usuario** (`userTimeZone` en meta o campo ya persistido).
- **Incluye:** documentar **tope máximo** de ítems y semántica de bordes de franja en OpenAPI.
- **Excluye:** regeneración bajo demanda mismo día salvo **D-05.2-003** explícita; narrativa DSR (**S6**).

#### 3) Dependencias

- **US-BE-019** (`kickoffUtc`, `eventStatus`); **D-05.2-002**.

#### 4) Criterios de aceptación *(mínimos)*

1. Given día operativo con stock CDM suficiente, When `GET /bt2/vault/picks`, Then la lista tiene **≈15 candidatos** (target **D-05.2-002** §6), salvo documentación explícita de pool reducido por falta de eventos.
2. Given día operativo con picks en varias franjas, When `GET /bt2/vault/picks`, Then la lista incluye **varios** ítems por franja cuando el CDM tiene stock (sin garantizar número fijo si no hay eventos).
3. Given `kickoffUtc` válido, When respuesta vault, Then cada ítem incluye **`timeBand`** acordado o documentado como omitido solo si PO aprobó excepción.
4. Given escasez en una franja, When composición del pool, Then el servidor **rellena** desde franja adyacente según **D-05.2-002**.

#### 5) Definition of Done

- [x] **T-188**, **T-189** en [`TASKS.md`](./TASKS.md).
- [x] Tests y/o curl reproducibles; migración solo si el modelo lo exige.

---

### US-BE-031 — Post–kickoff: una sola verdad *(RFB-05)*

#### 1) Objetivo de negocio

Que **no** sea posible “Tomar” en UI y recibir error opaco si el servidor **ya considera** el evento no disponible — alineando **`isAvailable`**, mensajes de error y **D-05.2-001**.

#### 2) Alcance

- **Incluye:** actualizar cálculo de **`isAvailable`** en serialización vault y/o regla en **`POST /bt2/picks`** según **D-05.2-001** (estricto o gracia **N** minutos en BE).
- **Incluye:** mensajes **422/409** claros y estables para el FE (**sin** textos inventados en cliente como única fuente).
- **Excluye:** políticas distintas por deporte/liga (**S6+** salvo PO acote).

#### 3) Dependencias

- **D-05.2-001** ratificada; **D-05-010** (S5).

#### 4) Definition of Done

- [x] **T-190** en [`TASKS.md`](./TASKS.md).
- [x] Tests que cubren “antes del kickoff / en kickoff / después” según opción **A** o **C**.

---

## Frontend

### US-FE-050 — Franjas, mezcla y cupo en bóveda *(RFB-06)*

#### 1) Objetivo de negocio

El operador **entiende** en qué “momento del día” están las señales y puede **acotar la vista** sin creer que gana más tomas; ve **cuántas** tomas estándar/premium le quedan en el **día operativo**.

#### 2) Alcance

- **Incluye:** switcher **Mezcla | Mañana | Tarde | Noche** (labels ES); filtrado por **`timeBand`** + modo mezcla con prioridad según **D-05.2-002** (ordenación en cliente).
- **Incluye:** contadores **restantes** 3 std / 2 prem coherentes con stores/API existentes; copy si hay gap **unlock vs tomar** (honesto).
- **Incluye:** **`VaultPage`** + componentes asociados; accesibilidad básica (roles/aria en switcher).
- **Excluye:** segundo GET al cambiar franja.

#### 3) Dependencias

- **US-BE-030** desplegado o contrato mockeado tras **T-188**; **US-FE-040**; **D-05.2-002**.

#### 4) Definition of Done

- [x] **T-192**, **T-193** en [`TASKS.md`](./TASKS.md).
- [ ] `npm test` + smoke bóveda.

---

### US-FE-051 — Coherencia visual post–kickoff *(RFB-05)*

#### 1) Objetivo de negocio

Reflejar en **PickCard** / bóveda la **misma** regla que el servidor tras **D-05.2-001** (CTA deshabilitado, tag, tooltip corto — coherente con **US-FE-044**).

#### 2) Alcance

- **Incluye:** consumir **`isAvailable`** y, si aplica, comparación temporal solo como **refuerzo** si PO lo pide y **no** contradice BE.
- **Incluye:** mensajes de error alineados a códigos del **POST** cuando el usuario intente tomar tarde.
- **Excluye:** ventana de gracia **solo** en FE si **D-05.2-001** = **C** en BE (el cliente **debe** reflejar contrato).

#### 3) Dependencias

- **US-BE-031**; **US-FE-044**.

#### 4) Definition of Done

- [x] **T-194** en [`TASKS.md`](./TASKS.md).

---

## DX *(opcional)*

### US-DX-001-R2 — Contrato vault ampliado

Solo si **T-188** añade campos (**`timeBand`**, límites, códigos de error nuevos): actualizar **`bt2Types.ts`**, constantes DX, **`contractVersion`**, nota en handoff FE.

**DoD:** [x] **T-191** en [`TASKS.md`](./TASKS.md) (`contractVersion` **s5.4**, `timeBand`, meta pool, código **pick_event_kickoff_elapsed**).

---

*Última actualización: 2026-04-09.*
