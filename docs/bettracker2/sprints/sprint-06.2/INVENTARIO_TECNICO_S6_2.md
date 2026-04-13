# Inventario técnico — Sprint 6.2 (entregables y auditoría pre-ejecución)

**Versión:** 2026-04-11  
**Para:** dueño técnico / auditoría antes de codificar  
**Jerarquía:** la **ley de reglas y definiciones** sigue siendo [`FUENTE_VERDAD_CONSOLIDADO_S6_1_Y_PLAN_S6_2.md`](./FUENTE_VERDAD_CONSOLIDADO_S6_1_Y_PLAN_S6_2.md) (§1–§3, §1.12, §1.13, §6). **Este archivo** es el **inventario de salidas esperadas**: lo que aparece aquí como entrega S6.2 es **decisión de alcance** para US / TASKS / `DECISIONES.md` cuando se redacten.  
**Regla anti-sorpresa:** si algo **no** está en este inventario (o en el consolidado) como esperado, **no** se asume hecho al cierre del sprint; un comentario en chat o en un `.md` histórico **no** sustituye una línea aquí.

**Artefactos de ejecución (creados 2026-04-11):** [`DECISIONES.md`](./DECISIONES.md), [`US.md`](./US.md), [`TASKS.md`](./TASKS.md), [`HANDOFF_EJECUCION_S6_2.md`](./HANDOFF_EJECUCION_S6_2.md) — trazabilidad **1:1** con el inventario §3 y el consolidado.

---

## 1. En una frase — qué debe lograr S6.2

**S6.2** cierra la brecha **BT2 vs v1** en **insumo real** (CDM / SportMonks / `ds_input`), **operabilidad** (snapshot global, cuotas, franjas, Regenerar), **superficie usuario** (copy **Vektor**, layout §1.11, settlement coherente), **admin** (auditoría CDM + refresh snapshot) y **gobernanza** (prompt aprobado, legal Vektor, jerarquía spec vs TASKS 06.1).

---

## 2. En este sprint se espera que… (lista de salidas — narrativa)

- **Ingesta y CDM:** el pipeline de datos que alimenta DSR sea **materialmente más rico y honesto** que el estado previo: includes SportMonks ampliados donde toque (**cubo A**), persistencia que **no deje el `raw` congelado** (UPSERT / política de refresh), mapper de **`statistics[]`** hacia `processed.*` donde haya datos, **lineups** solo con datos reales o `available: false` + diagnostics, tratamiento explícito del gap **429 sin raw** (backfill o diagnostics en builder).
- **`ds_input` vs v1:** se acerque a la **paridad de tipo de bloques** v1 con **Postgres**, no placeholders inventados; whitelist DX ampliada **solo** donde nuevos caminos vayan al LLM (**US-DX-003** sigue vigente como mecanismo).
- **DSR / Post-DSR:** sigan las reglas ya cerradas del consolidado (cuota input, ±15 %, cap odds > 15, omisión por contradicción texto vs selección, etc.); no es “nuevo objetivo” salvo que el inventario cite una **evidencia** o métrica adicional acordada en US.
- **Producto snapshot:** exista decisión implementada sobre **snapshot global (~20/día)**, **5 tomables/día**, **slate 5**, **franjas** 06:00–11:59 / 12:00–17:59 / 18:00–23:59, **madrugada fuera de alcance**, y **job nocturno vs disparo por `session/open`** — con modelo de datos/API acorde.
- **Regenerar:** exista **FSM** documentada (US producto + backend con ADR/comentario enlazado en TASKS S6.2), **una sola** definición de reset, **sin** IDs de máquina de estados en UI.
- **Front bóveda:** muestre copy y estructura **Vektor** según **§1.11** (preview ~2 líneas, detalle completo, cuota siempre visible, orden fijo, prohibidos de superficie); **GlossaryModal** y glosario alineados; **disclaimer** visible arriba en lista y en detalle de pick (**D-06-041**, **US-FE-060**); fallback SQL con copy que **no** suene a “mismo tono que DSR por API”.
- **Admin:** existan **vista auditoría CDM** por `operating_day_key` con motivos únicos en español **alineados a la query real del snapshot**, y **POST refresh snapshot** (día/usuario o contrato cerrado en US).
- **Cubo B (`team_season_stats`):** siga la regla **available: false** + diagnostics hasta fuente; si en S6.2 se **implementa** fuente, será **US dedicada** y diseño de endpoint documentado — no se mezcla con el PR del cubo A.
- **Cubo C (serie temporal de cuotas):** **US dedicada** + schema + índices + lecturas acotadas en builder; hasta implementado, **no** prometer al LLM o mantener `available: false` + diagnostics.
- **Documentación y actas:** existan **`DECISIONES.md` S6.2** con cierre **prompt batch** (aprobado / cambios / sin cambios vs vX) y acta **legal Vektor** cuando corresponda; **`TASKS.md` S6.2** como lista de trabajo viva; jerarquía explícita: **TASKS 06.1 = histórico**, verdad de producto = **consolidado + código** (**§1.13.4**).
- **Pipeline (orden §3.E):** cuando el bloque producto **A** esté escrito, se avance hacia **pool global + vista por usuario** (refactor acordado en plan S6.2).

---

## 3. Inventario por capa (checklist de entregables)

Cada ítem es candidato a **US / task / criterio de aceptación** cuando generes los artefactos formales.

### 3.1 Datos e ingesta (SportMonks / CDM / `raw`)

| # | Entregable esperado | Ref. consolidado |
|---|---------------------|------------------|
| D1 | Ampliar `include` en jobs que alimentan fixture (lineups, formations, sidelined, statistics según diseño) — **cubo A** | §1.9, §1.12-A |
| D2 | **UPSERT** o tablas derivadas para no dejar payload `raw` obsoleto por `DO NOTHING` | §1.9, §1.12 |
| D3 | Volcar **1–2** JSON referencia (programado vs terminado) y **mapper** `statistics[]` → `processed.*` + exclusiones pre-partido (anti-fuga) | §1.9 |
| D4 | **429** / eventos sin fila `raw`: **backfill** o `diagnostics.raw_fixture_missing` en builder | §1.9 |
| D5 | Cache local **type_id → nombre** (p. ej. corners = 34) sin depender de anidar type en cada request | §1.9 |
| D6 | **Cubo B:** mantener honestidad hasta US/schema propia | §1.12-B, §1.13.6 |
| D7 | **Cubo C:** schema + índices + job + builder por rango; o explícitamente diferido con `available: false` | §1.12-C, §1.13.5 |

### 3.2 Backend / API / DSR

| # | Entregable esperado | Ref. consolidado |
|---|---------------------|------------------|
| B1 | Builder `ds_input` coherente con whitelist; ampliación solo con validador | §1.2, §1.12 |
| B2 | Pool: cuota ≥ 1.30, ligas activas, mercados canónicos, premium ≥ standard | §1.4 |
| B3 | Post-DSR y persistencia pick canónico según §1.5 | §1.5 |
| B4 | Orquestación DSR → fallback → vacío duro + flags; ingesta rota sin “disfrazar” día normal | §1.3, §1.8 |
| B5 | Endpoint **POST refresh snapshot** (contrato en US) | §1.10, §1.13.3 |
| B6 | APIs/admin para **vista auditoría CDM** (motivos §1.10) | §1.10, §1.13.3 |
| B7 | FSM **Regenerar** implementada y documentada (backend) | §1.13.1, §3.A |

### 3.3 Frontend (bóveda, settlement, glosario)

| # | Entregable esperado | Ref. consolidado |
|---|---------------------|------------------|
| F1 | Copy y layout **Vektor** §1.11 en `PickCard` / flujos bóveda + **settlement** con criterios QA | §3.B |
| F2 | **GlossaryModal** + entrada glosario Vektor alineada | §1.11, §1.13.7 |
| F3 | Copy fallback / vacío / cobertura baja según §1.3, §1.8 | §1.3, §1.8 |
| F4 | Coherencia dura: mercado + cuota + texto Vektor = misma selección | §1.11 |
| F5 | Disclaimer **D-06-041** arriba en Bóveda + en detalle pick | D-06-041, US-FE-060 |

### 3.4 Producto y modelo snapshot

| # | Entregable esperado | Ref. consolidado |
|---|---------------------|------------------|
| P1 | Snapshot global ~**20**/día, **5** tomables, slate **5** | §3.A |
| P2 | Franjas horarias y exclusión madrugada | §3.A |
| P3 | Job nocturno vs `session/open` — decisión + implementación | §3.A |
| P4 | **Regenerar** con FSM y reset único | §1.13.1, §3.A |

### 3.5 DX

| # | Entregable esperado | Ref. consolidado |
|---|---------------------|------------------|
| X1 | Whitelist actualizada en repo + validador si nuevos caminos al LLM | §1.2, §3.D |

### 3.6 Documentación, actas y gobernanza

| # | Entregable esperado | Ref. consolidado |
|---|---------------------|------------------|
| G1 | **`DECISIONES.md` S6.2**: prompt batch §1.13.2 | §1.13.2, §3.G |
| G2 | **`DECISIONES.md` S6.2**: legal / claims Vektor §1.13.7 | §1.13.7, §3.G |
| G3 | **`TASKS.md` S6.2** como backlog ejecutable (TASKS 06.1 = histórico) | §1.13.4, §3.G |
| G4 | Runbooks / enlaces operativos para admin (cron, fetch, revisión) | §3.F |
| G5 | (Opcional) Pasada TASKS 06.1 vs código con etiquetas, **sin** sustituir jerarquía §1.13.4 | §1.13.4 |

### 3.7 Pipeline / refactor

| # | Entregable esperado | Ref. consolidado |
|---|---------------------|------------------|
| E1 | Tras cierre definición **§3.A**: refactor hacia **pool global + vista por usuario** | §3.E |

---

## 4. Explícitamente no es “comentario suelto”: compromisos duros S6.2

Estos vienen de **§1.13** del consolidado; deben aparecer reflejados en US/TASKS o en `DECISIONES.md` al ejecutar:

- FSM **Regenerar** + documentación backend.  
- Aprobación o registro de **prompt batch**.  
- **Dos** US backend: auditoría CDM + refresh snapshot.  
- **Cubo C** y **cubo B** con US/schema propias si se tocan; no colapsar en un solo PR mezclado con cubo A sin decisión.  
- **Vektor:** legal + glosario + UI §1.11.

---

## 5. Qué no se promete como “hecho S6.2” sin línea en §3 / inventario

- **SLA numérico** de acierto (>70 % / >80 %): es **dirección PO**, no entregable de build hasta settlement instrumentado (**§1.4, §1.7**).  
- **Paridad campo a campo** con v1 sin revisar `bt2_ds_input_v1_parity_fase1.md`: el consolidado remite a ese archivo como lista de claves.  
- Cualquier mejora **no** listada en las tablas de la **sección 3** de este inventario: **fuera de alcance tácito** hasta que se **añada una fila** aquí y se versione la fecha de cabecera.

---

## 6. Cómo auditar antes de la primera ejecución

1. Recorrer la **sección 2** y **3**: ¿cada fila tiene dueño (BE/FE/Datos/PO) previsto?  
2. Para cada pregunta “¿ya se hizo X?”: buscar **fila en §3** o **§1.13** en el consolidado; si no está, la respuesta correcta es **“no estaba en alcance documentado”**, no “se olvidó en código”.  
3. Al cerrar el sprint, idealmente cada fila de §3 pasa a **estado** `[ ] pendiente` → `[x] hecho` en `TASKS.md` cuando exista (o equivalente en board).

---

## 7. Artefactos generados (S6.2)

- [`DECISIONES.md`](./DECISIONES.md) — **D-06-031** … **D-06-040** + actas kickoff (D-06-034 … D-06-036).  
- [`US.md`](./US.md) — **US-DX-004**, **US-BE-040** … **US-BE-048**, **US-FE-057** … **US-FE-059** + matriz inventario → US.  
- [`TASKS.md`](./TASKS.md) — **T-195** … **T-225** + checklist de cobertura §3.  
- [`HANDOFF_EJECUCION_S6_2.md`](./HANDOFF_EJECUCION_S6_2.md) — orden, dependencias e instrucciones por rol.
- [`CIERRE_S6_2.md`](./CIERRE_S6_2.md) — acta de cierre (2026-04-09), **D-06-042**; traspasos a [`../sprint-06.3/PLAN.md`](../sprint-06.3/PLAN.md).

---

*Al cambiar el alcance S6.2, actualizar la **Versión** arriba y las tablas §3; si cambian reglas normativas, actualizar primero el consolidado y luego reflejar aquí. El sprint 06.2 está **cerrado**; no reabrir alcance aquí — usar S6.3.*
