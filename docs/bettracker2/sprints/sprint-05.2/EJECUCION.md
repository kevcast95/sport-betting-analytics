# Sprint 05.2 — Instrucciones de ejecución (Backend / Frontend)

## Lectura por rol

Cada desarrollador ejecuta **solo su bloque**. El orden **entre** bloques está en la sección **Coordinación**.

| Rol | Bloque |
|-----|--------|
| **Backend** | [Bloque 1 — Backend](#bloque-1--backend) |
| **Frontend** | [Bloque 2 — Frontend](#bloque-2--frontend) |

**Fuentes de verdad:** [`US.md`](./US.md), [`TASKS.md`](./TASKS.md), [`DECISIONES.md`](./DECISIONES.md), [`PLAN.md`](./PLAN.md).

**Contexto refinement:** [`../../refinement_feedback_s1_s5/DECISIONES.md`](../../refinement_feedback_s1_s5/DECISIONES.md) **RFB-05**, **RFB-06**.

---

## Coordinación (orden entre equipos)

1. **PO** ratifica **D-05.2-001** y cierra gaps de **D-05.2-002** (hueco 23:00–08:00, unlock vs cupo premium) — ver [`DECISIONES.md`](./DECISIONES.md).
2. **Backend** entrega **T-188** + **T-189** (y **T-191** si hay cambio de contrato) en entorno compartido.
3. **Frontend** arranca **T-192** / **T-193** cuando el contrato vault incluya **`timeBand`** (o acuerdo temporal de mock tipado).
4. **Backend** **T-190** puede desarrollarse **en paralelo** con **T-188** si no hay dependencia de esquema; **merge** recomendado antes de **T-194** para pruebas integradas.
5. **Frontend** **T-194** después de **T-190** estable.
6. **T-195** (cierre) — responsable acordado (QA/FE lead): tests + smoke + checklist PO.

**Dos devs FE:** repartir **T-192** (UI switcher + página) vs **T-193** (cupo/copy/tests); **T-194** quien tenga **PickCard** / bóveda más reciente.

**Dos devs BE:** repartir **T-188** (lógica pool + franjas) vs **T-189** (OpenAPI/curl) + **T-190** (disponibilidad post–kickoff).

---

## Bloque 1 — Backend

### US a ejecutar

| US | Tema |
|----|------|
| **US-BE-030** | Pool **~15 candidatos** + **`timeBand`** + relleno por franja (**RFB-06**, **D-05.2-002** §6) |
| **US-BE-031** | `isAvailable` + **`POST /bt2/picks`** según **D-05.2-001** (**RFB-05**) |
| **US-DX-001-R2** | *(Opcional)* tipos / `contractVersion` si cambia el JSON vault |

### Tareas (orden sugerido)

1. **T-188** — implementación núcleo **US-BE-030**.
2. **T-189** — contrato y pruebas manuales/automáticas.
3. **T-191** — solo si **T-188** añade o renombra campos en la API pública.
4. **T-190** — **US-BE-031** (tras ratificación **D-05.2-001**).

### Handoff mínimo al Frontend

- **`GET /bt2/vault/picks`:** lista suficiente para filtrar franjas en cliente; campo **`timeBand`** (o documentación explícita si PO difiere).
- Documentación **tope** de ítems y semántica de franjas.
- Comportamiento **`isAvailable`** y errores de **`POST /bt2/picks`** alineados a **D-05.2-001**.
- Curl mínimo (T-189): [`CURL_VAULT_052.md`](./CURL_VAULT_052.md).

---

## Bloque 2 — Frontend

### US a ejecutar

| US | Tema |
|----|------|
| **US-FE-050** | Switcher mezcla/franjas, ordenación, cupo visible (**RFB-06**) |
| **US-FE-051** | UX post–kickoff y errores de tomar pick (**RFB-05**) |

### Tareas (orden sugerido)

1. **T-192** — **US-FE-050** UI + filtrado.
2. **T-193** — **US-FE-050** cupo, copy, tests.
3. **T-194** — **US-FE-051** tras **T-190** disponible.

### Cierre Frontend (incluido en **T-195**)

- `npm test` en `apps/web`.
- Smoke: cambiar franjas sin recargar lista; verificar contadores; intento de tomar tras kickoff según entorno.

---

## Cierre global (**T-195**)

- Checklist [`TASKS.md`](./TASKS.md) (sección **Check trazabilidad refinement**).
- Actualizar índice en [`../../refinement_feedback_s1_s5/DECISIONES.md`](../../refinement_feedback_s1_s5/DECISIONES.md) cuando PO confirme cierre funcional.

---

*Última actualización: 2026-04-09 — Sprint 05.2 RFB-05 / RFB-06.*
