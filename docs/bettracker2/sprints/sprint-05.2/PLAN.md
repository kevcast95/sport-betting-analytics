# Sprint 05.2 — Bóveda: franjas, cupo y post–kickoff *(RFB-05, RFB-06)*

> **Tipo:** backlog ejecutable tras cierre operativo de **Sprint 05.1** (cabecera, santuario, doble fetch, etc.).  
> **Fuente refinement:** [`../../refinement_feedback_s1_s5/DECISIONES.md`](../../refinement_feedback_s1_s5/DECISIONES.md) **RFB-05**, **RFB-06**.

## Objetivo (una frase)

Que la bóveda del **día operativo** exponga un **pool amplio** clasificable por **franja horaria** (TZ usuario), con **cupo 3 estándar + 2 premium** reflejado en UI, y que la **política post–kickoff** sea **una sola fuente de verdad** entre BE y FE (**`isAvailable`** + validación de **`POST /bt2/picks`**).

## Alcance

| Pilar | Contenido |
|-------|-----------|
| **RFB-06** | Franjas 08:00–12:00 / 12:00–18:00 / 18:00–23:00 (TZ usuario); vista **mezcla** por defecto + **switcher** (filtro cliente, sin aumentar cupo); **BE: ~15 candidatos** en `GET /bt2/vault/picks` cuando haya stock (**D-05.2-002** §6) + campo **`timeBand`** por ítem; relleno desde franja cercana en **generación** servidor. |
| **RFB-05** | Cierre PO de **D-05.2-001**: kickoff estricto **o** ventana de gracia **en BE** (no solo FE). |
| **Hueco 23:00–08:00** | Pendiente explícito en **D-05.2-002** hasta ratificación PO. |

## Fuera de alcance (dejar explícito en DECISIONES si se difiere)

- **Refresh bajo demanda** el mismo día operativo con **regeneración** CDM (nuevo sorteo) — spike o **Sprint 06+** salvo acotar MVP en **D-05.2-003**.
- **Curación** “el usuario elige fixture antes del snapshot” — **S6+** (refinement **RFB-06** ítem 3).
- Narrativa **DSR** en cards — **Sprint 06** (`US-BE-025` / `US-FE-052+`).

## Dependencias

- **Sprint 05.1** estable: **US-FE-040** (unlock), **US-BE-029**, cabecera **US-FE-043**, **PickCard** **US-FE-044**.
- TZ usuario: hoy existe **`userTimeZone`** en meta/perfil BT2 — la US-BE-030 debe anclarse a ese contrato o proponer extensión mínima documentada.

## Archivos del sprint

| Archivo | Uso |
|---------|-----|
| [`DECISIONES.md`](./DECISIONES.md) | **D-05.2-001** … **D-05.2-003** |
| [`US.md`](./US.md) | **US-BE-030**, **US-BE-031**, **US-FE-050**, **US-FE-051**, **US-DX-001-R2** *(opcional)* |
| [`TASKS.md`](./TASKS.md) | **T-188+** (continúa tras **T-187** de 05.1) |
| [`EJECUCION.md`](./EJECUCION.md) | **Bloque Backend** y **Bloque Frontend** (cada dev lee su bloque) |

## Numeración — conflicto con Sprint 06

- **US-FE-050** y **US-FE-051** quedan reservadas en **esta carpeta**.  
- **Sprint 06** FE (DSR/analytics/mercados) usa **US-FE-052+** (ya renumerado en [`../sprint-06/US.md`](../sprint-06/US.md)).

---

*Última actualización: 2026-04-09 — backlog RFB-05/06 promovido desde refinement.*
