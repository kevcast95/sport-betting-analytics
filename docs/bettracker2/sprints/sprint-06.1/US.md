# Sprint 06.1 — US

> **Estado:** listo para kickoff tras marcar el **DoR** (sección **Apto 100% para ejecución**) en [`TASKS.md`](./TASKS.md); reglas operativas **D-06-024** … **D-06-026** (KPI “% acierto” >70% = dirección PO; medición formal con settlement → US posterior).  
> **Contrato de formato:** [`../../01_CONTRATO_US.md`](../../01_CONTRATO_US.md).  
> **Decisiones:** [`DECISIONES.md`](./DECISIONES.md) **D-06-021** … **D-06-026**.  
> **Tareas:** [`TASKS.md`](./TASKS.md) **T-171+**.  
> **Handoff ejecución:** [`HANDOFF_EJECUCION_S6_1.md`](./HANDOFF_EJECUCION_S6_1.md).

### Convención con desarrollo (**D-06-023**)

Cambios de alcance durante código → nueva US / refinement / DECISIÓN **antes** de merge.

---

## Contratos

### US-DX-003 — Contrato `ds_input` BT2 en paridad con v1 (lista cerrada + anti-fuga)

#### 1) Objetivo de negocio

Que el insumo que recibe DeepSeek en BT2 sea **auditable y estable**: mismos **bloques semánticos** que v1 (`DSR_V1_FLUJO.md` §4), con **lista cerrada** de claves permitidas en producción y validación que impida fugas **D-06-002**.

#### 2) Alcance

- Incluye: documento de **campos permitidos** por entorno (prod vs dev); actualización de **`assert_no_forbidden_ds_keys`** / contrato Pydantic asociado; **bump `contractVersion`** en `GET /bt2/meta` (valor sugerido: `bt2-dx-001-s6.1`); alineación **OpenAPI** y **`bt2Types.ts`** para cada campo nuevo expuesto al cliente (vacío operativo, lineage, flags de degradación acordados en **T-173**).
- Excluye: implementar el builder de datos ( **US-BE-032** ); redefinir **US-DX-001** ledger.

#### 3) Contexto técnico actual

- `apps/api/bt2_dsr_contract.py`, `apps/api/bt2_dsr_deepseek.py`, `apps/api/bt2_router.py`, `apps/api/bt2_schemas.py`, `apps/web/src/lib/bt2Types.ts`, `GET /bt2/meta`.

#### 4) Contrato de entrada/salida (referencia)

- Entrada: whitelist **[`../../dx/bt2_ds_input_v1_parity_fase1.md`](../../dx/bt2_ds_input_v1_parity_fase1.md)** (T-171) + remisión **D-06-024** / **D-06-025**.
- Salida: versión contrato visible en meta + tipos cliente sincronizados.

#### 5) Reglas de dominio

- Ninguna clave prohibida por **D-06-002** en payloads hacia el LLM en prod.
- Campos opcionales deben degradar con **null** / omisión, no strings inventadas.

#### 6) Criterios de aceptación

1. Given lista cerrada aprobada por PO, When se serializa `ds_input` para un evento de prueba, Then el validador anti-fuga **no** rechaza y **rechaza** un payload de prueba con clave prohibida.
2. Given `GET /bt2/meta`, Then `contractVersion` refleja el bump S6.1.

#### 7) No-funcionales

- Documentación legible para BE que implementa **US-BE-032**.

#### 8) Riesgos

- Exceso de campos → coste tokens: mitigar con **fase 1 mínima** acordada con PO.

#### 9) Plan de pruebas

- Unitarias: validador contrato.
- Manual: meta + tipos generados / revisión TS.

#### 10) Definition of Done

- [ ] Whitelist documentada y enlazada desde DECISIONES o anexo DX.
- [ ] Código validador + meta + OpenAPI + **bt2Types.ts** cuando el contrato exponga campos al cliente.
- [ ] Sin romper **US-DX-001** / **US-DX-002** cerrados, excepto **bump** explícito acordado.

---

## Backend

### US-BE-032 — Builder `ds_input` rico desde CDM/Postgres

#### 1) Objetivo de negocio

Poblar cada candidato del lote DSR con **contexto comparable a v1** (equipos, torneo, odds estructurados, bloques `processed`/`diagnostics`/`event_context` **según US-DX-003**), usando datos **persistidos** BT2.

#### 2) Alcance

- Incluye: módulo o funciones dedicadas (nombre sugerido: `apps/api/bt2_dsr_ds_input_builder.py`); consultas a `bt2_events`, `bt2_odds_snapshot`, tablas/agregados acordados en whitelist; integración en el path **batch** DeepSeek (`DsrBatchCandidate` o sucesor).
- Excluye: cambiar proveedor SM; scraping v1; lógica de **orquestación** final del snapshot ( **US-BE-036** ).

#### 3) Contexto técnico actual

- `apps/api/bt2_dsr_deepseek.py`, `apps/api/bt2_router.py` (`_generate_daily_picks_snapshot`), `scripts/bt2_cdm/build_candidates.py` como referencia de forma JSON v1.

#### 5) Reglas de dominio

- Sin PII; sin resultados futuros; coherencia con anti-fuga **D-06-002**.
- Si falta un bloque opcional, el builder omite o marca `diagnostics` según contrato **US-DX-003**.

#### 6) Criterios de aceptación

1. Given evento con odds y metadatos CDM mínimos, When se arma `ds_input`, Then incluye al menos los campos **obligatorios** de la whitelist fase 1.
2. Given evento sin sub-bloque opcional, When se arma `ds_input`, Then no rompe el batch y refleja ausencia según contrato.

#### 9) Plan de pruebas

- Unitarias: fixtures SQLite/Postgres de prueba o mocks de filas.
- Integración: un lote pequeño con `BT2_DSR_PROVIDER=rules` o mock HTTP.

#### 10) Definition of Done

- [ ] Builder integrado al flujo batch.
- [ ] Tests verdes.
- [ ] Documentado en handoff qué tablas alimentan cada clave.

---

### US-BE-033 — Pool candidatos: valor por mercado, umbrales y premium más exigente

#### 1) Objetivo de negocio

Reducir ruido **antes** del LLM con filtros por **ligas prioritarias del producto**, **cuota mínima** y universo de mercados **según lo disponible en CDM** (sin par obligatorio fijo 1X2 + O/U 2.5 — **D-06-024**, **D-06-025**, **D-06-026**). **Premium** solo para candidatos que pasen **barra adicional** definida en **D-06-024** § premium (implementación cuantitativa T-178).

#### 2) Alcance

- Incluye: query / post-filtro de candidatos; parámetros configurables (env o settings) con default **cuota mín 1.30** (**D-06-024**); extensión de mapeos canónicos según la ingestión aporte 1X2, doble oportunidad, O/U goles/corners/tarjetas, BTTS, etc.; reglas **premium vs standard**.
- Excluye: post-proceso de **salida** del LLM (**US-BE-034**); KPI agregados (**US-BE-035**).

#### 5) Reglas de dominio

- **Fuente de verdad:** **DECISIONES** **D-06-024** … **D-06-026**, **D-06-025** y whitelist **US-DX-003**. **No** aplicar reglas de pool que contradigan esas decisiones (véase también **OBJETIVO** §3.1, alineado a las mismas fuentes).
- El modelo elige **entre mercados presentes** en snapshot; el pool excluye eventos que **no** tengan al menos **un** mercado canónico **completo** utilizable con línea ≥ cuota mínima (definición en builder/pool compartida con T-177).
- Premium **nunca** menos estricto que standard.

#### 6) Criterios de aceptación

1. Given evento **sin ningún** mercado canónico completo en CDM que cumpla cuota mín **D-06-024**, When pool del día, Then **no** entra al lote DSR.
2. Given evento con solo corners O/U completo (sin 1X2), When pool, Then **puede** entrar si pasa filtros de liga/cuota (**D-06-025** filosofía valor).
3. Given candidato que no pasa barra premium **D-06-024**, When se compone pool, Then **no** se le asigna tier premium.

#### 10) Definition of Done

- [ ] Reglas y números acordados reflejados en código y en **DECISIONES** (**D-06-024** … **D-06-026**); `.env.example` comentado si hay toggles.
- [ ] Tests regresión pool.

---

### US-BE-034 — Post-DSR: reconciliación input/output y pick persistido

#### 1) Objetivo de negocio

**Lo que se guarda en BT2** es el **pick canónico** tras Post-DSR, no el JSON crudo del modelo: cuotas persistidas ancladas al **input**, discrepancias registradas, confianza acotada según reglas; si mercado/selección **no** existen en el lote → **omitir pick** del evento (**D-06-024** § post-DSR, **D-06-026** §2).

#### 2) Alcance

- Incluye: pipeline **después** del parse de `picks_by_event` y **antes** de INSERT: ajuste de **parámetros** (cuota desde `consensus`/CDM si desvío > ±15%), cap `dsr_confidence_label` si odds modelo > 15, logs/métricas; omisión de filas inválidas (**T-181**–**T-182**).
- Excluye: **sustituto automático** “otra selección desde Post-DSR” en fase 1 (**D-06-026**); orquestación global DSR vs fallback (**US-BE-036**).

#### 5) Reglas de dominio

- Matriz numérica y matiz implementación: **D-06-024** tabla post-DSR + párrafo *Matiz implementación* + **D-06-025** §3.
- Fallback SQL / implícita por evento **después** de DSR vacío es responsabilidad de **US-BE-036**, no de sustituir picks DSR inválidos en silencio.

#### 6) Criterios de aceptación

1. Given salida LLM con cuota **desalineada** del input (> umbral **D-06-024**), When post-proceso, Then el valor **persistido** es el del input para **ese** mercado/selección canónica y queda **log/métrica** de discrepancia.
2. Given salida con mercado/selección **ausentes** del input, When post-proceso, Then **no** se persiste pick DSR para ese evento (fase 1).
3. Given salida coherente, When post-proceso, Then persistencia con misma elección DSR y parámetros alineados al input.

#### 10) Definition of Done

- [ ] Comportamiento acorde a **D-06-024** … **D-06-026**; tests unitarios casos borde (T-181).

---

### US-BE-036 — Orquestación snapshot bóveda (**D-06-022** + **D-06-024** / **D-06-025**)

#### 1) Objetivo de negocio

Orden fijo: **DSR primero** (picks ya pasados por **US-BE-034**). Si el conjunto publicable queda vacío **y** aún hay **filas utilizables** en CDM → **fallback** SQL / implícita con **lineage** no-DSR, copy y **disclaimer** de datos limitados (**D-06-024** § cobertura, **D-06-025** §4). Solo **vacío duro** → sin picks + mensaje operativo claro: criterio mínimo **D-06-026** §6 (**0** filas elegibles en pool SQL de fallback con filtros **T-177**); coherente con “sin candidatos utilizables” en CDM para el día. Flag opcional **`limited_coverage`** (**D-06-026** §4: &lt; 5 eventos futuros en ventana día operativo) para UX **sin** bloquear fallback.

#### 2) Alcance

- Incluye: refactor `_generate_daily_picks_snapshot` (o servicio); flags/mensajes API acordados con **US-DX-003**; idempotencia y sesión.
- Excluye: vista admin auditoría CDM completa (**TASKS** T-188).

#### 5) Reglas de dominio

- **D-06-022** + matiz **D-06-025** §4: fallback transparente cuando hay datos pero DSR no alcanza; no disfrazar fallback como salida del razonador.
- **D-06-026** §4–§6: cobertura baja ≠ prohibir fallback; **0** filas pool elegible ⇒ vacío duro, sin fallback estadístico.

#### 6) Criterios de aceptación

1. Given Post-DSR produce picks DSR, When snapshot, Then persisten con fuente/lineage coherente.
2. Given DSR vacío **y** CDM con candidatos SQL válidos, When snapshot, Then persisten picks fallback + mensaje/disclaimer según contrato.
3. Given **vacío duro** (**D-06-026** §6: **0** filas elegibles en pool fallback / sin candidatos utilizables para el día), When snapshot, Then **cero** picks y API indica causa operativa (no mezclar con “sin señal DSR”).

#### 9) Plan de pruebas

- Integración: los **tres** escenarios anteriores con DB de prueba o mocks; resultados registrados en [`EJECUCION.md`](./EJECUCION.md).

#### 10) Definition of Done

- [ ] Pruebas de los tres escenarios.
- [ ] Alineado a **DECISIONES** **D-06-022** … **D-06-026** (incl. §6 vacío duro).

---

### US-BE-035 — Admin: distribución calidad / confianza / fuente (MVP)

#### 1) Objetivo de negocio

Instrumentar **medición v0**: agregados por `operating_day_key` (conteos por `dsr_confidence_label`, `dsr_source`, **score** cuando BE lo exponga en el contrato admin) para alimentar revisión PO/BA. La hipótesis **>80%** “alta calidad” (**D-06-021**) y la meta **>70%** aciertos **standard** (**D-06-025** §2) son **dirección de producto**; el **% de acierto real** requiere definición con **settlement** + ventana (referencia típica **30 días** en **US de refinamiento**) — **D-06-026** §5.

#### 2) Alcance

- Incluye: **GET** admin acotado (`X-BT2-Admin-Key`); JSON agregado; sin BI externo.
- Excluye: KPI “alta calidad” como SLA numérico cerrado en este sprint (los **conteos** del endpoint sí entran en alcance).

#### 10) Definition of Done

- [ ] Endpoint documentado en OpenAPI.
- [ ] Test mínimo o verificación manual documentada.
- [ ] Comportamiento acorde a **D-06-026** §5.

---

## Frontend

### US-FE-055 — Bóveda y admin: semántica confianza vs datos vs edge

#### 1) Objetivo de negocio

El usuario **no confunde** “confianza simbólica del modelo” con “calidad de ingesta” ni con un **score numérico** si BE lo expone.

#### 2) Alcance

- Incluye: `PickCard` / bloque DSR: jerarquía de líneas o labels según campos **US-BE-036** / **US-BE-035**; copy en español **Zurich Calm**; admin: párrafo o leyenda bajo métricas nuevas de **US-BE-035**.
- Excluye: rediseño global del shell; export CSV.

#### 3) Contexto técnico actual

- `apps/web/src/components/vault/PickCard.tsx`, `apps/web/src/lib/vaultModelReading.ts`, `bt2Types.ts`, página admin DSR existente.

#### 6) Criterios de aceptación

1. Given pick con `dsr_source` fallback, When render, Then el copy **no** implica “razonador API” para esa fila.
2. Given nuevos campos de vacío operativo, When bóveda vacía, Then mensaje distingue **sin datos CDM** vs **sin señal DSR**.

#### 10) Definition of Done

- [ ] `npm test` + `npm run build`.
- [ ] Copy revisado con PO antes de merge **o** ítem de seguimiento explícito en **TASKS.md** si el merge es técnico previo.

---

*Última actualización: 2026-04-09 — Alineación US-BE-033/034/035/036 a **D-06-024** … **D-06-026** (auditoría BA).*
