# Sprint 06 — US

> **Convención:** Tras **US-FE-049** (Sprint 05.1), las US FE de **bóveda franjas / post–kickoff** viven en **[`../sprint-05.2/US.md`](../sprint-05.2/US.md)** (**US-FE-050**, **US-FE-051**). **Este sprint (S6)** usa **US-FE-052+** para DSR / analytics / mercados canónicos. BE continúa en **US-BE-025+** (Sprint 05: **US-BE-017…024**; 05.2 añade **US-BE-030…031**). DX: **US-DX-002**. OPS: **US-OPS-001**.  
> **Calendario:** [`DECISIONES.md`](./DECISIONES.md) **D-06-001**; parlays/diagnóstico avanzado/**D-04-001** → **Sprint 07**.

## Estado del sprint

- Fecha inicio: **2026-04-08** · Fecha fin: **2026-04-08**  
- Estado: **Cerrado (alcance acordado)** — núcleo **T-157–T-170**, **T-159–T-168** y **T-154**, **T-156** completados en código y verificación FE (`npm test`, `npm run build`). **T-153**, **T-155** (US-DX-002) y validación formal runbook en staging/on-call (**D-06-011**) quedan explícitas en [`TASKS.md`](./TASKS.md) checklist de cierre y Sprint 07 / operación.  
- Dependencia: **Sprints 05 / 05.1 / 05.2** cerrados en documentación (2026-04-08).

## Resumen — US Frontend

| ID | Título | Notas |
|----|--------|--------|
| US-FE-052 | Bóveda / picks con **narrativa DSR** y señales del modelo | Consume contratos **US-DX-002** / **US-BE-025**; sin exponer proveedor crudo. |
| US-FE-053 | **Analytics** picks y bóveda en V2 (MVP) | **D-06-004**; **US-BE-028**; datos reales únicamente. |
| US-FE-054 | UI alineada a **mercados canónicos** + copy legible | **D-06-003**; mapas `marketCanonical` → texto español desde API. |

## Resumen — US Backend

| ID | Título | Notas |
|----|--------|--------|
| US-BE-025 | **DSR + CDM:** pipeline razonador sobre candidatos con **anti-fuga** | **D-06-002**; fases A/B; persistencia outputs auditables. |
| US-BE-026 | **Cron / job** `fetch_upcoming` + robustez 429 + métricas mínimas | **D-06-005**; complementa script S4. |
| US-BE-027 | **Enum / mercado canónico** en picks y snapshot (evolución **D-04-002**) | **D-06-003**; settle alineado. |
| US-BE-028 | **Analytics** servidor: agregados picks/bóveda (MVP) | **D-06-004**; endpoints acotados. |

## Resumen — Contratos y operación

| ID | Título | Notas |
|----|--------|--------|
| US-DX-002 | Catálogo ampliado: **mercados canónicos**, DSR I/O, **operatorProfile**, OpenAPI | No romper **US-DX-001**; bump `contractVersion`. |
| US-OPS-001 | **Runbook** cron CDM + alertas + entorno | **D-06-005**; puede vivir en `docs/bettracker2/runbooks/`. |

---

## Frontend

### US-FE-052 — Bóveda: picks con **narrativa DSR** (edge / selección modelo)

#### 1) Objetivo de negocio

Que el operador vea **por qué** el protocolo propone cada señal: criterio del **modelo** (DSR) sobre edge y selección, en español legible y **sin** filtrar JSON de proveedor ni prompts.

#### 2) Alcance

- Incluye: campos de UI acordados en **US-DX-002** (p. ej. resumen modelo, nivel de confianza simbólico, etiquetas de riesgo) consumidos desde **US-BE-025** vía API vault o extensión snapshot.
- Excluye: parlays (**Sprint 07**); editor de prompts DSR en UI.

#### 3) Dependencias

- **US-BE-025**, **US-DX-002**; **Sprint 05** bóveda base estable.

#### 4) Criterios de aceptación *(mínimos)*

1. Given snapshot con salida DSR, When abre bóveda, Then ve bloque de **narrativa modelo** alineado al contrato.
2. Given evento sin DSR (fallback regla), When abre pick, Then copy honesto “señal por reglas” o equivalente — sin inventar texto DSR.

#### 5) Definition of Done

- [x] Tareas **US-FE-052** en [`TASKS.md`](./TASKS.md) (**T-165**).
- [x] `npm test` sin regresión rutas V2; **T-168** incluye `npm run build` en `apps/web`.

---

### US-FE-053 — Analytics picks / bóveda (MVP)

#### 1) Objetivo de negocio

Visibilidad **conductual y de calidad** del snapshot (distribuciones, tendencias por día operativo) acotada a **MVP D-06-004**.

#### 2) Alcance

- Incluye: una o dos vistas/secciones V2 acordadas (p. ej. ampliación **Performance** o bloque **Santuario**) consumiendo **US-BE-028**.
- Excluye: exportaciones, BI completo, rankings globales ficticios.

#### 3) Dependencias

- **US-BE-028**, **D-06-004**.

#### 4) Definition of Done

- [x] Tareas **US-FE-053** en [`TASKS.md`](./TASKS.md) (**T-166**).

---

### US-FE-054 — Mercados **canónicos** en UI (labels español)

#### 1) Objetivo de negocio

Coherencia visual y semántica cuando el backend expone **`marketCanonical`** (u homólogo): el usuario ve **texto humano** estable, no strings crudos Sportmonks.

#### 2) Alcance

- Incluye: **PickCard**, **Settlement**, **Ledger** según exponga el API; fallback “—” si falta mapa.
- Excluye: lógica de settle en cliente.

#### 3) Dependencias

- **US-BE-027**, **US-DX-002** (`marketLabelEs` o tabla en DX).

#### 4) Definition of Done

- [x] Tareas **US-FE-054** en [`TASKS.md`](./TASKS.md) (**T-167**).

---

## Backend

### US-BE-025 — Integración **DeepSeek Reasoner (DSR)** con CDM (anti-fuga)

#### 1) Objetivo de negocio

Generar **justificación y ranking** de señales usando el razonador con **barreras documentadas** entre entrenamiento/backtest y producción diaria (**D-06-002**), con **trazabilidad** de si la señal vino de **reglas locales** o de **API DeepSeek** (**D-06-018**).

#### 2) Alcance

- Incluye: contrato de **entrada** a DSR por día operativo; **salida** estructurada persistida (tablas o JSON versionado); integración con `build_candidates` o sucesor; logs/huella de versión pipeline; campo **`dsr_source`** (`rules_fallback` \| `dsr_api`).
- Incluye (**T-169** + **T-170**): DeepSeek en vivo (**D-06-018**) y **orquestación por lotes v1-equivalentes** (`picks_by_event` / candidatos comparados en el mismo prompt cuando aplique) — **D-06-019**; referencia [`jobs/deepseek_batches_to_telegram_payload_parts.py`](../../../../jobs/deepseek_batches_to_telegram_payload_parts.py).
- Excluye: parlays; recalibración diagnóstico; cola async **desacoplada** de `session/open` y dashboard de coste (backlog / S6.1 salvo decisión contraria).

#### 3) Léxico *(BE / PO)*

- **`rules_fallback`:** mercado, selección y narrativa generados **sin** LLM en ese camino (`bt2_dsr_suggest.py`). Válido para dev/CI y **degradación** si la API falla (**D-06-018**).
- **`dsr_api`:** señal atribuible a **respuesta DeepSeek** (HTTP) mapeada a los mismos campos persistidos.

#### 4) Contexto técnico *(orientativo)*

- Scripts `scripts/bt2_cdm/`, jobs existentes S3/S4; credenciales **`DEEPSEEK_API_KEY`** en `.env` (equipo); variables **`BT2_DSR_*`** — lista en **D-06-018** y [`.env.example`](../../../../.env.example).

#### 5) Reglas de dominio

- **Regla 1:** Ningún campo prohibido por **D-06-002** en el payload de producción (ni al LLM).
- **Regla 2:** Idempotencia: re-ejecutar día **D** no duplica picks publicados sin política explícita.
- **Regla 3:** Sin **PII** en prompts (**D-06-014**).

#### 6) Criterios de aceptación *(mínimos)*

1. Given candidatos día **D**, When corre pipeline, Then se persiste salida vinculable a `operating_day_key` y `pipeline_version`.
2. Given intento de incluir resultado futuro en input producción, When valida esquema, Then **422** o rechazo en job.
3. Given **`BT2_DSR_PROVIDER=rules`** (o sin key), When genera snapshot, Then `dsr_source` es `rules_fallback` y el FE puede mostrar narrativa coherente.
4. Given **`BT2_DSR_PROVIDER=deepseek`** y **`DEEPSEEK_API_KEY`** válida, When genera snapshot, Then al menos un flujo de prueba produce **`dsr_source=dsr_api`** y canónicos persistidos; Given la API falla, When política default **D-06-018**, Then degradación documentada.
5. Given **T-170** cerrada, When genera snapshot, Then el modelo recibe **lotes** alineados a **D-06-019** (no solo 1 evento por request como diseño final, salvo excepción PO firmada).

#### 7) Definition of Done

- [x] Tareas **US-BE-025** en [`TASKS.md`](./TASKS.md) (**T-157**, **T-158**, **T-169**, **T-170**).
- [x] **D-06-018** y **D-06-019** aplicadas por BE; env en **`.env.example`**; handoff [`BE_HANDOFF_SPRINT06.md`](./BE_HANDOFF_SPRINT06.md).
- [x] Marco **fase A/B** y anti-fuga en [`DECISIONES.md`](./DECISIONES.md) (**D-06-002**).

---

### US-BE-026 — **Cron / job programado** `fetch_upcoming`

#### 1) Objetivo de negocio

Ingesta de fixtures **sin intervención manual** diaria, con reintentos y señal de fallo (**D-06-005**).

#### 2) Alcance

- Incluye: empaquetado del job (mismo comportamiento idempotente S4); scheduling; métricas mínimas (última corrida, conteo inserts); coordinación **US-OPS-001**.
- Excluye: DSR (va en **US-BE-025**).

#### 3) Definition of Done

- [x] Tareas **US-BE-026** en [`TASKS.md`](./TASKS.md) (**T-159**).
- [x] Runbook **US-OPS-001** en repo y enlazado (**T-160** / [`../../runbooks/bt2_fetch_upcoming_cron.md`](../../runbooks/bt2_fetch_upcoming_cron.md)); validación staging/prod + on-call → **D-06-011** (operación).

---

### US-BE-027 — **Normalización mercados** (enum canónico) — evolución D-04-002

#### 1) Objetivo de negocio

Eliminar fragilidad de **strings** en settle y en vault: un **código canónico** por mercado con mapeo desde Sportmonks en ACL (**D-06-003**).

#### 2) Alcance

- Incluye: migración o backfill; actualización **`POST /bt2/picks`** / snapshot vault; `_determine_outcome` leyendo canónico; tests regresión settle.
- Excluye: nuevos deportes fuera fútbol salvo decisión PM.

#### 3) Dependencias

- Coordinar con **Sprint 05** **US-BE-023** si ambos tocan `market` — una sola línea de migración.

#### 4) Definition of Done

- [x] Tareas **US-BE-027** en [`TASKS.md`](./TASKS.md) (**T-161**, **T-162**).

---

### US-BE-028 — **Analytics** servidor (MVP picks / bóveda)

#### 1) Objetivo de negocio

Exponer **agregados** para **US-FE-053** sin lógica de negocio en cliente (**D-06-004**).

#### 2) Alcance

- Incluye: 1–2 endpoints `GET` bajo `/bt2/...` (nombres a fijar en DX) con filtros por `operating_day_key` / rango; respuesta con campos `*_human_es` donde aplique identidad proyecto.
- Excluye: warehouse analítico separado en S6 salvo decisión PM.

#### 3) Definition of Done

- [x] Tareas **US-BE-028** en [`TASKS.md`](./TASKS.md) (**T-163**, **T-164**).

---

## Contratos

### US-DX-002 — Catálogo ampliado: mercados canónicos, DSR, operatorProfile, OpenAPI

#### 1) Objetivo

Un único lugar para **mercados canónicos**, **shape DSR** entrada/salida, valores **operatorProfile**, y **OpenAPI** generado alineado a **ledger `reason`** donde aún falte explícitamente.

#### 2) Alcance

- Incluye: `bt2_dx_constants.py` + `bt2Types.ts` + tabla en **DECISIONES** **D-06-006**; bump **`contractVersion`**.
- Excluye: redefinir razones ledger ya cerradas en **US-DX-001** sin enmienda.

#### 3) Definition of Done

- [ ] Cierre **parcial:** **T-154**, **T-156** hechas; **T-153**, **T-155** diferidas a Sprint 07 (ver [`TASKS.md`](./TASKS.md) checklist cierre y [`../sprint-07/PLAN.md`](../sprint-07/PLAN.md)).

---

## Operación

### US-OPS-001 — Runbook: cron CDM + alertas

#### 1) Objetivo

Operación **reproducible** de ingesta diaria y escalación si falla.

#### 2) Alcance

- Incluye: horario, variables entorno, comando, qué revisar si 0 eventos, contacto/on-call si aplica.
- Excluye: implementación del job ( **US-BE-026** ).

#### 3) Definition of Done

- [x] Documento en repo enlazado desde [`PLAN.md`](./PLAN.md) y **D-06-005** (**T-160**).
- [ ] Runbook **validado** en staging/prod y canal on-call real cuando la org lo asigne (**D-06-011**).

---

## Sprint 07 — Recordatorio (no parte de US ejecutables S6)

| Tema | Referencia |
|------|------------|
| Parlays, 7 opciones, DSR combina legs | **D-04-012**, **D-04-013** (`../sprint-04/DECISIONES.md`) |
| Diagnóstico longitudinal / recalibración | US-BE-016 exclusión S4; planificar **Sprint 07** |
| Bankroll COP sesión | **D-04-001** |

*Las US de Sprint 07 se redactan al cerrar alcance S6.*
