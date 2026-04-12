# Handoff ejecución — Sprint 06.2

> **Para:** DX, BE (datos / core / admin), FE (bóveda / admin), PO/BA, operación.  
> **Backlog vivo de este sprint:** **[`TASKS.md`](./TASKS.md)** en **esta carpeta** (`sprint-06.2`). **No** usar [`../sprint-06.1/TASKS.md`](../sprint-06.1/TASKS.md) como lista de trabajo: por **D-06-031** es **histórico** (solo referencia o **T-221** opcional).  
> **Fuentes:** [`US.md`](./US.md), [`TASKS.md`](./TASKS.md), [`DECISIONES.md`](./DECISIONES.md), [`FUENTE_VERDAD_CONSOLIDADO_S6_1_Y_PLAN_S6_2.md`](./FUENTE_VERDAD_CONSOLIDADO_S6_1_Y_PLAN_S6_2.md), [`INVENTARIO_TECNICO_S6_2.md`](./INVENTARIO_TECNICO_S6_2.md).  
> **Evidencia de cierre:** [`EJECUCION.md`](./EJECUCION.md) en esta carpeta (crear/actualizar con escenarios probados y **diferidos** explícitos).

---

## 0. Objetivo de cierre del sprint (no negociable en intención)

**Cerrar S6.2 con DSR integrado de punta a punta y coherente con la fuente de verdad**, y con **insumo BT2 materialmente más rico y honesto que el “mínimo” previo** — en la línea **v1** (bloques `ds_input`, diagnostics reales, **sin** inventar datos), según **§1.1–§1.2**, **§1.9**, **§1.12-A** y **§1.13** del consolidado.

**Comprueba al cierre (TL / PO):**

| # | Comprobación |
|---|----------------|
| C1 | **Pipeline:** pool → `ds_input` (whitelist) → batch DSR → Post-DSR **§1.5** → persistencia pick → respuesta bóveda (**§1.1**). |
| C2 | **Ingesta / builder:** cubo **A** avanzado (includes + `raw` usable + mapper hacia `processed.*` donde haya datos); gap **sin raw** con **diagnostics**, no silencio (**§1.9**). |
| C3 | **Orquestación:** precedencia **§1.3** + vacío duro / ingesta rota / fallback con lineage; regresión **T-223** documentada. |
| C4 | **Superficie:** **Vektor** **§1.11** + glosario (**D-06-036**) + disclaimer (**D-06-041** / **T-226**) donde el alcance del sprint incluya FE. |
| C5 | **Gates:** **T-225** verde; actas **D-06-034** / **D-06-035** cerradas según reglas en **DECISIONES**. |

Si el tiempo apremia, **no** se “suaviza” C1–C3: se **recorta alcance** por US acordado y se **deja por escrito** en **EJECUCION.md** + nota en **DECISIONES** o siguiente **PLAN** (véase §8).

---

## 1. Validación previa (TL / PO — 15 min)

1. [`US.md`](./US.md) matriz + [`TASKS.md`](./TASKS.md) § “Checklist de cobertura inventario”: cada fila **D\*/B\*/P\*/F\*/E/X/G** con US/tarea o **explícitamente diferida** (§8).
2. **D-06-034:** opción reset **(a)/(b)** antes del merge final de **US-BE-045**.
3. **D-06-035:** fecha + responsable en acta (además de estado).
4. **Vektor:** **D-06-036** / **D-06-041** en texto; implementación FE según **T-218** / **T-226** si entran en alcance.

Cambios de alcance durante el sprint → **D-06-023** (US o **DECISIONES** antes de merge).

---

## 2. Cesiones por rol (responsable primario)

| Rol | US principales | Tareas |
|-----|----------------|--------|
| **DX** | **US-DX-004** | **T-195–T-196** |
| **BE — datos / SM** | **US-BE-040** | **T-197–T-200** |
| **BE — builder** | **US-BE-041**, **US-BE-043** | **T-201–T-204**, **T-208** |
| **BE — historial cuotas** | **US-BE-042** | **T-205–T-207** |
| **BE — snapshot / pipeline** | **US-BE-044**, **US-BE-048** | **T-209–T-211**, **T-216** |
| **BE — Regenerar** | **US-BE-045** | **T-212–T-213** |
| **BE — admin API** | **US-BE-046**, **US-BE-047** | **T-214–T-215** |
| **FE — bóveda** | **US-FE-057**, **US-FE-058**, **US-FE-060** | **T-217–T-218**, **T-226** |
| **FE — admin** | **US-FE-059** | **T-219** |
| **PO/BA** | — | **D-06-032/033**; actas **034/035**; **T-224**; copy **036/041** |
| **Todos** | — | **T-223**, **T-225**; **T-220** runbooks |

---

## 3. Prioridad sugerida (P0 = núcleo “DSR > v1”; P1 = producto/ops; P2 = refinamiento o siguiente sprint)

| Prioridad | Bloque | Tareas / US | Notas |
|-----------|--------|-------------|--------|
| **P0** | Contrato + datos + builder | **T-195–T-204**, **US-DX-004**, **US-BE-040**, **US-BE-041** | Sin esto no hay paridad de insumo creíble hacia DSR. |
| **P0** | Regresión pipeline | **T-223** | Tras **T-209–T-211** cuando snapshot toque el router; valida **§1.3–§1.5**. |
| **P1** | Snapshot / franjas / disparo | **T-209–T-211**, **US-BE-044** | **D-06-032** / **D-06-033**. |
| **P1** | Regenerar | **T-212–T-213**, **US-BE-045** | Acta **D-06-034** obligatoria. |
| **P1** | Bóveda + Vektor + disclaimer | **T-217**, **T-218**, **T-226** | Alineado **§1.11**, **D-06-036**, **D-06-041**. |
| **P1** | Admin API + (UI si hay tiempo) | **T-214–T-215**, **T-219** | **§1.10** / **§1.13.3**. |
| **P1** | Gobernanza | **T-224**, **T-220** | Prompt + runbooks. |
| **P2** | Pool global + vista usuario | **T-216**, **US-BE-048** | **§3.E**; si no entra en tiempo → **deuda S6.3** (documentar). |
| **P2** | Cubo C (historial cuotas) | **T-205–T-207**, **US-BE-042** | Puede ser **mínimo** `available: false` + schema/job en sprint siguiente si PO acuerda **DECISIONES** + **EJECUCION.md**. |
| **P2** | Opcional | **T-221** | Auditoría TASKS 06.1 vs código. |

El **orden técnico detallado** sigue en §4 (dependencias entre PRs).

---

## 4. Orden recomendado (dependencias)

1. **T-195** → **T-196** (**US-DX-004**).
2. **T-197–T-200** (**US-BE-040**); **T-201–T-204** tras datos/whitelist listos.
3. **T-205–T-207** en paralelo si no chocan migraciones; si no hay capacidad → **P2** y acta en **EJECUCION.md**.
4. **T-208** (**US-BE-043**) — mínimo diagnostics/documentación.
5. **T-209–T-211** antes de **T-216** (si **T-216** se ejecuta este sprint).
6. **T-212–T-213** tras base **T-209+** estable.
7. **T-214** / **T-215**; **T-219** (FE admin) después de API estable.
8. **T-217** → **T-218** / **T-226** (mismo PR bóveda si conviene).
9. **T-216** solo si **US-BE-044** cerrada o subconjunto acordado.
10. **T-224** en paralelo al código cuando sea posible.
11. **T-223** antes de **T-225**.
12. **T-220** antes del cierre operativo.
13. **T-225** — gate final.

---

## 5. Instrucciones explícitas — Backend (BE)

**Ámbito:** `apps/api/`, scripts `scripts/bt2_cdm/`, `scripts/bt2_atraco/`, migraciones Alembic bajo `apps/api/alembic/`. **US:** **US-DX-004** (si el mismo dev hace DX+BE, empezar por whitelist), **US-BE-040** … **US-BE-048**. **Tareas:** **T-195–T-216**, **T-223**, **T-224** (si tocás prompt), **T-225** (pytest BT2).

1. **Leer antes de codear:** [`DECISIONES.md`](./DECISIONES.md) **D-06-032**, **D-06-033**, **D-06-037**, **D-06-038**, **D-06-039**, **D-06-040**; consolidado **§1.1**, **§1.3–§1.5**, **§1.9**, **§1.12–§1.13** en [`FUENTE_VERDAD_CONSOLIDADO_S6_1_Y_PLAN_S6_2.md`](./FUENTE_VERDAD_CONSOLIDADO_S6_1_Y_PLAN_S6_2.md).
2. **Whitelist / contrato (US-DX-004):** **T-195** — actualizar `docs/bettracker2/dx/bt2_ds_input_v1_parity_fase1.md` con las claves que el builder enviará al LLM; **T-196** — validador (`bt2_dsr_contract.py` o equivalente), bump `contractVersion` en `GET /bt2/meta`, OpenAPI y lo que el cliente necesite. **Regla:** ningún merge a prod con claves nuevas hacia el LLM sin **T-195** acordado (**D-06-002**).
3. **Ingesta cubo A (US-BE-040):** **T-197** — `include` en `sportmonks_worker.py` / `fetch_upcoming.py` según **D-06-037**; **T-198** — UPSERT o refresh para `raw_sportmonks_fixtures` (evitar `raw` congelado inútil); **T-199** — `type_id → nombre`; **T-200** — JSON referencia en `docs/bettracker2/sprints/sprint-06.2/refs/` (o ruta del PR).
4. **Builder (US-BE-041):** **T-201** — mapper `statistics[]` → `processed.*`; **T-202** — lineups solo con datos reales; **T-203** — diagnostic si hay evento sin `raw`; **T-204** — tests. **No** marcar bloques disponibles con datos inventados.
5. **Cubo C (US-BE-042), si aplica:** **T-205–T-207** — schema, índices, job, lectura por rango (**D-06-039**). Si se difiere: anotar en **EJECUCION.md** § diferidos.
6. **Cubo B (US-BE-043):** **T-208** — mínimo diagnostics + documentación de fuente; implementación opcional si PO lo pide.
7. **Snapshot (US-BE-044):** **T-209–T-211** — **20 / 5 / 5** (**D-06-032**), franjas, job + **D-06-033**; tocar router/servicio del día. Cambio de números → enmendar **D-06-032**.
8. **Regenerar (US-BE-045):** **T-212–T-213** — FSM + API interna; **antes del merge final** acta **D-06-034** **(a)/(b)**; enlace **ADR** en [`TASKS.md`](./TASKS.md) (**T-213**). No exponer IDs de máquina de estados al usuario final.
9. **Admin API (US-BE-046 / 047):** **T-214** — auditoría CDM, motivos = misma lógica que pool (**D-06-040**); **T-215** — POST refresh, idempotencia en OpenAPI + tests.
10. **Pool global (US-BE-048), P2:** **T-216** tras **US-BE-044** estable; si no entra, **§8**.
11. **Regresión:** **T-223** — **§1.3–§1.5** con snapshot nuevo; evidencia en **EJECUCION.md**.
12. **Prompt:** **T-224** si aplica — `bt2_dsr_deepseek.py` vs acta **D-06-035**.
13. **Cierre:** **T-225** — pytest BT2; avisar a FE si cambia JSON de bóveda/admin.

**Con FE:** OpenAPI / `bt2Types.ts` actualizados antes de que integren bóveda.

---

## 6. Instrucciones explícitas — Frontend (FE)

**Ámbito:** `apps/web/` (Bóveda, `PickCard`, settlement, admin BT2, `GlossaryModal`). **US:** **US-FE-057**, **US-FE-058**, **US-FE-059**, **US-FE-060**. **Tareas:** **T-217–T-219**, **T-226**, **T-225** (web).

1. **Leer:** consolidado **§1.3**, **§1.8**, **§1.11**; **D-06-036**, **D-06-041** en [`DECISIONES.md`](./DECISIONES.md); cuerpo de **US-FE-057** … **US-FE-060** en [`US.md`](./US.md).
2. **Dependencia BE:** no integrar bóveda “a ciegas”; usar **T-196** + respuesta real post **T-209–T-211** / **T-223** salvo stub acordado con TL.
3. **Bóveda (T-217 / US-FE-057):** orden **§1.11**; cuota en bloque propio; Vektor + confianza; prohibidos de superficie (códigos internos, “Origen API”, etc.); settlement alineado con preview/detalle.
4. **Copy (T-218 / US-FE-058):** fallback SQL con tono distinto a DSR “por API”; vacío / cobertura baja según flags API.
5. **Glosario:** `GlossaryModal.tsx` — Vektor acorde a **D-06-036**.
6. **Disclaimer (T-226 / US-FE-060):** texto **literal** **D-06-041** §2 arriba del listado de Bóveda **y** en detalle de pick; legible sin abrir glosario.
7. **Admin (T-219 / US-FE-059):** consumir **T-214** + **T-215**; sin PII ni JSON crudo SM.
8. **Cierre:** `npm test` + `npm run build`; notas/capturas en **EJECUCION.md** si aplica.

**Con BE:** no asumir forma de JSON; basarse en contrato publicado.

---

## 7. DX / PO (transversal)

- **DX (si no sos BE):** **T-195** antes de claves nuevas al LLM (véase §5 punto 2).
- **PO/BA:** enmendar **D-06-032** solo si cambian 20/5/5 o franjas; acta **D-06-034** antes de cierre **US-BE-045**; **T-224** + **D-06-035** (fecha + responsable); alinear copy **036 / 041** con lo desplegado.

---

## 8. Pendientes → refinamiento o deuda (cómo cerrar el sprint sin sorpresas)

Si al final del sprint **no** se completan **T-216**, **T-205–T-207**, **T-219** u otras **P2**:

1. Anotar en **[`EJECUCION.md`](./EJECUCION.md)** tabla **“Diferido”**: ID tarea, US, motivo (tiempo / dependencia / riesgo), **sprint objetivo** sugerido (p. ej. S6.3).
2. Si el diferido **cambia** la promesa de producto, **enmienda** breve en [`DECISIONES.md`](./DECISIONES.md) o línea en el **PLAN** del siguiente sprint — **no** solo comentario en PR.
3. **No** marcar **T-225** verde ignorando **P0**; si se recorta **P0**, es **cambio de alcance** explícito (**D-06-023**).

**Refinamiento:** mejoras de copy, pulido visual, métricas PO, optimización de job — **después** de C1–C5.

---

## 9. Puntos de sincronía y rollback

- **BE ↔ DX:** whitelist antes de builder con claves nuevas.
- **BE ↔ FE:** OpenAPI / `bt2Types` antes de integrar bóveda/admin.
- **Pool ↔ auditoría:** mismo predicado SQL para motivos (**D-06-040**).

**Rollback:** revertir migraciones cubo C / snapshot; `BT2_DSR_PROVIDER=rules` según runbook si aplica.

---

*Versión: 2026-04-11 — §5 BE y §6 FE: instrucciones explícitas por capa. Handoff: cierre **DSR integrado**, **insumo > v1**, backlog **TASKS S6.2**.*
