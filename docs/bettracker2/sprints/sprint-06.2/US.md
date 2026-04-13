# Sprint 06.2 — US

> **Fuente normativa:** [`FUENTE_VERDAD_CONSOLIDADO_S6_1_Y_PLAN_S6_2.md`](./FUENTE_VERDAD_CONSOLIDADO_S6_1_Y_PLAN_S6_2.md).  
> **Inventario ↔ US:** [`INVENTARIO_TECNICO_S6_2.md`](./INVENTARIO_TECNICO_S6_2.md) §3.  
> **Decisiones:** [`DECISIONES.md`](./DECISIONES.md) **D-06-031** … **D-06-041**.  
> **Tareas:** [`TASKS.md`](./TASKS.md) **T-195** … **T-226**.  
> **Handoff:** [`HANDOFF_EJECUCION_S6_2.md`](./HANDOFF_EJECUCION_S6_2.md).  
> **Contrato de formato US:** [`../../01_CONTRATO_US.md`](../../01_CONTRATO_US.md).  
> **Madre S6.1:** US **US-DX-003**, **US-BE-032** … **US-BE-039**, **US-FE-055**, **US-FE-056** — S6.2 **extiende** sin romper anti-fuga **D-06-002**.

### Convención

Cambios de alcance en código → nueva US o **DECISIONES** (**D-06-023**).

---

## Matriz de trazabilidad (inventario §3 → US)

| Inventario | US |
|------------|-----|
| D1, D2, D5 + JSON ref parcial D3 | **US-BE-040** |
| D3 mapper, D4, D6 honestidad (con **US-BE-043**), B1 | **US-BE-041** (+ **US-DX-004**) |
| D7 cubo C | **US-BE-042** |
| D6 cubo B dedicado | **US-BE-043** |
| P1–P3 | **US-BE-044** |
| P4, B7 | **US-BE-045** |
| B6 | **US-BE-046** |
| B5 | **US-BE-047** |
| E1 | **US-BE-048** |
| X1 | **US-DX-004** |
| F1, F4 | **US-FE-057** |
| F2, F3 | **US-FE-058** |
| Admin UI auditoría | **US-FE-059** |
| Disclaimer Bóveda (lista + detalle) | **US-FE-060** |
| G1 prompt | Acta **D-06-035** + **T-224** |
| G2 legal Vektor | Acta **D-06-036** |
| B2–B4 regresión | **T-223** (snapshot nuevo) |

---

## Contratos — US-DX-004

### US-DX-004 — Whitelist fase 1 S6.2: nuevas claves hacia el LLM (cubo A / cubo C)

#### 1) Objetivo de negocio

Permitir que el builder (**US-BE-041**, **US-BE-042**) envíe al batch DSR **solo** claves explícitamente whitelisteadas, con **anti-fuga** y **bump** de contrato visible al cliente.

#### 2) Alcance

- Incluye: actualizar **[`../../dx/bt2_ds_input_v1_parity_fase1.md`](../../dx/bt2_ds_input_v1_parity_fase1.md)** con claves nuevas acordadas con PO; validador **`assert_no_forbidden_ds_keys`** / Pydantic; **`contractVersion`** en `GET /bt2/meta`; OpenAPI + **`bt2Types.ts`** para cualquier campo nuevo expuesto al cliente.
- Excluye: implementar ingesta SM (**US-BE-040**); implementar tablas cubo C (**US-BE-042**) salvo coordinación de nombres de claves.

#### 3) Contexto técnico

- `apps/api/bt2_dsr_contract.py`, `bt2_router.py`, `bt2_schemas.py`, `apps/web/src/lib/bt2Types.ts`.

#### 4) Reglas de dominio

- **Ninguna** clave hacia el LLM en prod fuera de la whitelist (**D-06-002**).
- Ampliación coordinada con **US-BE-041** / **US-BE-042** antes de merge a prod.

#### 5) Criterios de aceptación

1. Payload de prueba con clave nueva **permitida** pasa validador; payload con clave no listada **falla** en prod.
2. `GET /bt2/meta` refleja bump S6.2 (valor versionado en PR).

#### 6) Definition of Done

- [ ] Documento parity actualizado y enlazado desde **DECISIONES** o PR.
- [ ] Tests validador + tipos cliente si el API expone campos nuevos al front.

**Madre:** **US-DX-003** — tareas **T-195–T-196**.

---

## Backend — ingesta y datos

### US-BE-040 — SportMonks cubo A: `include`, persistencia `raw` fresca, artefactos de diseño

#### 1) Objetivo de negocio

Que CDM disponga de payloads fixture **suficientes** para lineups y estadísticas de partido según **§1.9** / **§1.12-A**, sin depender de `raw` congelado por **DO NOTHING**.

#### 2) Alcance

- Incluye: ampliar **`include`** en `scripts/bt2_atraco/sportmonks_worker.py` y/o `scripts/bt2_cdm/fetch_upcoming.py` (y jobs relacionados) con **lineups**, **formations**, **sidelined**, **statistics** según diseño; **UPSERT** o política de refresh documentada (**D-06-037**); **cache local type_id → nombre** (p. ej. corners **34**) sin anidar `statistics.type` en cada request; volcar **1–2 JSON** de referencia (programado vs terminado) bajo `docs/bettracker2/` o `docs/bettracker2/sprints/sprint-06.2/refs/` para el mapper.
- Excluye: mapper a `processed.*` (**US-BE-041**); schema cubo C (**US-BE-042**).

#### 3) Reglas

- No exponer PII ni fugas proveedor en logs de usuario (**D-06-002**).

#### 4) Criterios de aceptación

1. Tras job, fixture de prueba tiene en `raw` (o tabla derivada) los nodos necesarios para alimentar lineups/statistics cuando SM los devuelve.
2. Política **DO NOTHING** queda sustituida o complementada según **D-06-037** con evidencia en PR.
3. Existen JSON referencia versionados en repo citados por **US-BE-041**.

#### 5) Definition of Done

- [ ] Scripts + migración si aplica + README o nota operativa (runbook **T-220**).
- [ ] Tests o job dry-run documentado.

**Tareas:** **T-197–T-200**.

---

### US-BE-041 — Builder `ds_input`: `statistics`, lineups, diagnostics `raw` / 429

#### 1) Objetivo de negocio

Poblar **`processed`** con datos **reales** desde Postgres/`raw` alineados a v1; **honestidad** si falta raw (**§1.9**).

#### 2) Alcance

- Incluye: mapper **`statistics[]`** → shape `processed.statistics` (o equivalente whitelist); **lineups** desde payload cuando exista; **`diagnostics.raw_fixture_missing`** (u homólogo) cuando `bt2_events` exista sin fila `raw_sportmonks_fixtures`; exclusiones **pre-partido** anti-fuga; **`team_season_stats`** permanece **`available: false`** + diagnostics hasta **US-BE-043** salvo que 043 implemente fuente en el mismo sprint.
- Excluye: cubo C tiempo completo (**US-BE-042**); cambiar Post-DSR (**US-BE-034** salvo regresión).

#### 3) Reglas

- **US-DX-004** debe aprobar claves nuevas antes de enviar al LLM.

#### 4) Criterios de aceptación

1. Evento con `raw` enriquecido produce bloques poblados o `available: false` con causa real, nunca datos inventados.
2. Evento sin `raw` refleja diagnostic explícito en builder/tests.

#### 5) Definition of Done

- [ ] Tests unitarios/fixtures **T-201–T-204**.
- [ ] Handoff actualizado: tabla fuente → bloque `processed`.

**Madre:** **US-BE-032**, **US-BE-037** — **T-201–T-204**.

---

### US-BE-042 — Cubo C: historial de cuotas (schema + job + lectura acotada)

#### 1) Objetivo de negocio

Habilitar **serie temporal** de cuotas por mercado/selección con **queries acotadas** (**§1.13.5**, **D-06-039**).

#### 2) Alcance

- Incluye: migración Alembic; índices; job o política de snapshots; lectura en builder por **rango**; integración whitelist **US-DX-004**.
- Excluye: UI de gráficos (fuera de alcance salvo decisión); cubo A (**US-BE-040**).

#### 3) Criterios de aceptación

1. No hay query de historial sin **límite temporal** o **paginación** en path del builder.
2. Sin datos históricos, bloque no va al LLM o `available: false` + diagnostics.

#### 4) Definition of Done

- [ ] **T-205–T-207** + tests.

---

### US-BE-043 — Cubo B: `team_season_stats` (fuente o cierre explícito de gap)

#### 1) Objetivo de negocio

Cerrar ambigüedad entre estadísticas **de partido** y **de temporada** (**§1.12-B**, **D-06-038**).

#### 2) Alcance

- **Mínimo S6.2:** documentar en PR + **DECISIONES** acta breve qué endpoint/agregación SM alimentaría el bloque; **`available: false`** + diagnostics estables.
- **Opcional:** implementar tabla + job + builder si el esfuerzo cabe en sprint (misma US, criterios adicionales en **T-208**).

#### 3) Criterios de aceptación

1. Ningún caso mezcla `statistics[]` de fixture con temporada sin etiquetar.
2. Diagnostics explican el gap al operador/DX.

#### 4) Definition of Done

- [ ] **T-208** cumplida según rama mínima u extendida acordada en kickoff.

---

## Backend — producto snapshot y pipeline

### US-BE-044 — Snapshot global, tomables, slate, franjas y disparo (D-06-032 / D-06-033)

#### 1) Objetivo de negocio

Implementar parámetros **§3.A** consolidado: ~**20** global, **5** tomables, slate **5**, franjas y exclusión madrugada; convivencia **job** / sesión según **D-06-033**.

#### 2) Alcance

- Incluye: modelo de datos y/o settings; `_generate_daily_picks_snapshot` (o servicio sucesor); coherencia con pool **US-BE-033** y orquestación **US-BE-036**; flags API para FE.
- Excluye: FSM Regenerar (**US-BE-045**); admin audit (**US-BE-046**).

#### 3) Reglas

- No contradecir **D-06-022**, **D-06-025**, **D-06-026**.

#### 4) Criterios de aceptación

1. Tests o escenarios documentados para límites 20/5/5 y franjas TZ.
2. Comportamiento job vs `session/open` acorde a **D-06-033** y acta.

#### 5) Definition of Done

- [ ] **T-209–T-211**; regresión **T-223** planificada tras integración.

---

### US-BE-045 — Regenerar: FSM y API (sin IDs internos en UI)

#### 1) Objetivo de negocio

Cumplir **§1.13.1** y **D-06-034**: usuario puede regenerar snapshot/picks según reglas de producto con **reset único** documentado.

#### 2) Alcance

- Incluye: estados persistidos necesarios; transiciones; endpoint(s) o acciones servidor; **ADR** o documento enlazado desde **TASKS**; contrato para FE sin exponer IDs de máquina internos.
- Excluye: copy Vektor (**US-FE-057**).

#### 3) Criterios de aceptación

1. Tabla/diagrama FSM en US o anexo + enlace en **TASKS**.
2. Opción de reset **(a)/(b)** reflejada en **D-06-034** acta kickoff.

#### 4) Definition of Done

- [ ] **T-212–T-213** + tests transición prohibida/válida.

---

### US-BE-046 — Admin API: auditoría CDM por `operating_day_key`

#### 1) Objetivo de negocio

Exponer conteos y lista paginada con **motivo único** en español alineado a la query real del snapshot (**§1.10**, **D-06-040**, nota VISTA_AUDITORIA).

#### 2) Alcance

- Incluye: `GET` (u homólogo) bajo prefijo admin existente; auth **X-BT2-Admin-Key**; motivos mínimos §1.10; paginación.
- Excluye: UI (**US-FE-059**).

#### 3) Criterios de aceptación

1. Para cada código de motivo, existe test o assert que lo amarra a la misma condición SQL que el pool/snapshot.
2. OpenAPI actualizado; **bt2Types** si el cliente admin consume la respuesta.

#### 4) Definition of Done

- [ ] **T-214**.

---

### US-BE-047 — Admin API: POST refresh snapshot

#### 1) Objetivo de negocio

Permitir refrescar snapshot **día/usuario** tras ingesta tardía (**§1.10**, **§1.13.3**).

#### 2) Alcance

- Incluye: contrato request/response; idempotencia; auth admin; integración con pipeline **US-BE-044**.
- Excluye: sustituir cron obligatorio (**D-06-033**).

#### 3) Criterios de aceptación

1. Llamada válida reprocesa snapshot según reglas sin duplicar picks de forma incorrecta (definir idempotencia en PR).
2. Errores operativos devuelven mensaje accionable (sin PII).

#### 4) Definition of Done

- [ ] **T-215** + tests.

---

### US-BE-048 — Pool global y vista por usuario (post §3.A)

#### 1) Objetivo de negocio

Ejecutar **§3.E** consolidado: tras modelo snapshot **US-BE-044**, refactor hacia **pool global** + **vista por usuario**.

#### 2) Alcance

- Incluye: separación datos compartidos vs personalización tomables/slate; migraciones si aplica; actualización orquestación.
- Excluye: redefinir reglas pool valor sin **DECISIONES**.

#### 3) Dependencias

- **Bloqueante:** criterios de aceptación **US-BE-044** estables (o subconjunto acordado en kickoff).

#### 4) Criterios de aceptación

1. Un solo cómputo pesado reutilizable entre usuarios del mismo día (o documentar por qué no aplica).
2. Tests de regresión **T-223** / **T-225** pasan.

#### 5) Definition of Done

- [ ] **T-216**.

---

## Frontend

### US-FE-057 — Bóveda: Vektor §1.11 + coherencia mercado/cuota/texto + settlement

#### 1) Objetivo de negocio

Superficie usuario alineada a **§1.11**: orden fijo, **Vektor — por qué**, cuota siempre visible, chips, confianza en una línea, prohibidos; **coherencia dura** mercado + cuota + texto (**D-06-036** copy final).

#### 2) Alcance

- Incluye: `PickCard` / vault / **settlement** donde aplique el mismo contrato visual; preview ~2 líneas / detalle completo.
- Excluye: glosario modal profundo (**US-FE-058**).

#### 3) Criterios de aceptación

1. Ningún estado muestra códigos internos tipo `FT_1X2 · home` en UI usuario.
2. QA manual: misma selección en titular, cuota y párrafo Vektor.

#### 4) Definition of Done

- [ ] **T-217** + capturas o nota en **EJECUCION.md** cuando exista.

**Madre:** **US-FE-055**, **US-FE-056**.

---

### US-FE-058 — Glosario Vektor + copy fallback / vacío / cobertura baja

#### 1) Objetivo de negocio

**GlossaryModal** y entradas con definición aprobada (**D-06-036**); copy **fallback SQL** que no suene a “mismo tono que DSR API” (**§1.3**, **§1.8**, **§1.11**).

#### 2) Alcance

- Incluye: strings bóveda para `dsr_source` fallback, vacío duro, `limited_coverage` si existe flag; alineación con campos **US-BE-044**/**US-BE-036**.
- Excluye: cambiar lógica servidor.

#### 3) Criterios de aceptación

1. Entrada **Vektor** en `GlossaryModal` coincide semánticamente con **D-06-036** (texto canónico en `DECISIONES.md`).
2. Copy fallback / vacío / cobertura baja revisado (tests o checklist manual documentado).

#### 4) Definition of Done

- [ ] **T-218**; glosario Vektor verificable en código (`GlossaryModal.tsx`).

---

### US-FE-059 — Admin UI: auditoría CDM + acción refresh

#### 1) Objetivo de negocio

Pantalla **solo admin** consumiendo **US-BE-046** y **US-BE-047**; operador ve motivos y puede refrescar tras ingesta (**nota VISTA_AUDITORIA**).

#### 2) Alcance

- Incluye: ruta admin existente o nueva bajo mismas reglas de auth; tabla/lista paginada; CTA refresh; manejo errores.
- Excluye: exponer JSON crudo SM.

#### 3) Criterios de aceptación

1. Motivos mostrados = códigos API sin reinterpretación incorrecta.
2. Refresh llama **US-BE-047** y actualiza vista o mensaje de estado.

#### 4) Definition of Done

- [ ] **T-219**.

---

### US-FE-060 — Bóveda: disclaimer Vektor (lista arriba + detalle pick)

#### 1) Objetivo de negocio

Cumplir **D-06-041**: el usuario ve un **aviso fijo** de límites de la señal (no garantía de resultado, no asesoría financiera) en la **parte superior** de la vista Bóveda y otra vez en el **detalle** de cada pick, alineado semánticamente con **D-06-036**.

#### 2) Alcance

- Incluye: componente o bloque de copy reutilizable; `VaultPage` / layout bóveda; vista detalle pick (`PickCard` detalle, modal o ruta dedicada según implementación actual).
- Excluye: redactar nuevos términos legales globales; cambiar texto de **D-06-041** sin enmienda en **DECISIONES**.

#### 3) Reglas

- Texto **literal** de superficie: el de **D-06-041** §2 (salvo enmienda de esa D).
- Estilo: tipografía secundaria permitida; **no** ocultar detrás de un solo ícono sin texto (debe leerse sin interacción obligatoria).

#### 4) Criterios de aceptación

1. Entrar a Bóveda: el disclaimer aparece **arriba** del listado (o equivalente) sin abrir glosario.
2. Abrir detalle de un pick: el **mismo** disclaimer (misma redacción) aparece en el flujo de lectura del detalle.
3. QA: no contradice el bloque Vektor ni la línea de confianza (**§1.11**).

#### 5) Definition of Done

- [ ] **T-226**; captura o nota en **EJECUCION.md** cuando exista.

**Madre:** **US-FE-057** — complementa layout §1.11 sin sustituir orden de bloques obligatorios.

---

*Última actualización: 2026-04-11 — **US-FE-060** / **D-06-041** disclaimer superficie.*
