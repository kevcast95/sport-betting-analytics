# Sprint 06 — US

> **Convención:** Tras **US-FE-049** (Sprint 05.1), las US FE de **bóveda franjas / post–kickoff** viven en **[`../sprint-05.2/US.md`](../sprint-05.2/US.md)** (**US-FE-050**, **US-FE-051**). **Este sprint (S6)** usa **US-FE-052+** para DSR / analytics / mercados canónicos. BE continúa en **US-BE-025+** (Sprint 05: **US-BE-017…024**; 05.2 añade **US-BE-030…031**). DX: **US-DX-002**. OPS: **US-OPS-001**.  
> **Calendario:** [`DECISIONES.md`](./DECISIONES.md) **D-06-001**; parlays/diagnóstico avanzado/**D-04-001** → **Sprint 07**.

## Estado del sprint

- Fecha inicio / fin: *(definir al arrancar S6)*  
- Estado: **En definición** (documentación y criterios de arranque en [`PLAN.md`](./PLAN.md) §6 y [`EJECUCION.md`](./EJECUCION.md)).  
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

- [ ] Tareas **US-FE-052** en [`TASKS.md`](./TASKS.md).
- [ ] `npm test` sin regresión rutas V2.

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

- [ ] Tareas **US-FE-053** en [`TASKS.md`](./TASKS.md).

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

- [ ] Tareas **US-FE-054** en [`TASKS.md`](./TASKS.md).

---

## Backend

### US-BE-025 — Integración **DeepSeek Reasoner (DSR)** con CDM (anti-fuga)

#### 1) Objetivo de negocio

Generar **justificación y ranking** de señales usando el razonador con **barreras documentadas** entre entrenamiento/backtest y producción diaria (**D-06-002**).

#### 2) Alcance

- Incluye: contrato de **entrada** a DSR por día operativo; **salida** estructurada persistida (tablas o JSON versionado); integración con `build_candidates` o sucesor; logs/huella de versión pipeline.
- Excluye: parlays; recalibración diagnóstico.

#### 3) Contexto técnico *(orientativo)*

- Scripts `scripts/bt2_cdm/`, jobs existentes S3/S4; claves API y límites en config secreta.

#### 4) Reglas de dominio

- **Regla 1:** Ningún campo prohibido por **D-06-002** en el payload de producción.
- **Regla 2:** Idempotencia: re-ejecutar día **D** no duplica picks publicados sin política explícita.

#### 5) Criterios de aceptación *(mínimos)*

1. Given candidatos día **D**, When corre pipeline, Then se persiste salida vinculable a `operating_day_key` y `pipeline_version`.
2. Given intento de incluir resultado futuro en input producción, When valida esquema, Then **422** o rechazo en job.

#### 6) Definition of Done

- [ ] Tareas **US-BE-025** en [`TASKS.md`](./TASKS.md).
- [ ] Documento de **fase A/B** en `DECISIONES.md` o anexo citado en **D-06-002**.

---

### US-BE-026 — **Cron / job programado** `fetch_upcoming`

#### 1) Objetivo de negocio

Ingesta de fixtures **sin intervención manual** diaria, con reintentos y señal de fallo (**D-06-005**).

#### 2) Alcance

- Incluye: empaquetado del job (mismo comportamiento idempotente S4); scheduling; métricas mínimas (última corrida, conteo inserts); coordinación **US-OPS-001**.
- Excluye: DSR (va en **US-BE-025**).

#### 3) Definition of Done

- [ ] Tareas **US-BE-026** en [`TASKS.md`](./TASKS.md).
- [ ] Runbook **US-OPS-001** enlazado y revisado.

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

- [ ] Tareas **US-BE-027** en [`TASKS.md`](./TASKS.md).

---

### US-BE-028 — **Analytics** servidor (MVP picks / bóveda)

#### 1) Objetivo de negocio

Exponer **agregados** para **US-FE-053** sin lógica de negocio en cliente (**D-06-004**).

#### 2) Alcance

- Incluye: 1–2 endpoints `GET` bajo `/bt2/...` (nombres a fijar en DX) con filtros por `operating_day_key` / rango; respuesta con campos `*_human_es` donde aplique identidad proyecto.
- Excluye: warehouse analítico separado en S6 salvo decisión PM.

#### 3) Definition of Done

- [ ] Tareas **US-BE-028** en [`TASKS.md`](./TASKS.md).

---

## Contratos

### US-DX-002 — Catálogo ampliado: mercados canónicos, DSR, operatorProfile, OpenAPI

#### 1) Objetivo

Un único lugar para **mercados canónicos**, **shape DSR** entrada/salida, valores **operatorProfile**, y **OpenAPI** generado alineado a **ledger `reason`** donde aún falte explícitamente.

#### 2) Alcance

- Incluye: `bt2_dx_constants.py` + `bt2Types.ts` + tabla en **DECISIONES** **D-06-006**; bump **`contractVersion`**.
- Excluye: redefinir razones ledger ya cerradas en **US-DX-001** sin enmienda.

#### 3) Definition of Done

- [ ] Tareas **US-DX-002** en [`TASKS.md`](./TASKS.md).

---

## Operación

### US-OPS-001 — Runbook: cron CDM + alertas

#### 1) Objetivo

Operación **reproducible** de ingesta diaria y escalación si falla.

#### 2) Alcance

- Incluye: horario, variables entorno, comando, qué revisar si 0 eventos, contacto/on-call si aplica.
- Excluye: implementación del job ( **US-BE-026** ).

#### 3) Definition of Done

- [ ] Documento en repo (ruta acordada) enlazado desde [`PLAN.md`](./PLAN.md) y **D-06-005**.

---

## Sprint 07 — Recordatorio (no parte de US ejecutables S6)

| Tema | Referencia |
|------|------------|
| Parlays, 7 opciones, DSR combina legs | **D-04-012**, **D-04-013** (`../sprint-04/DECISIONES.md`) |
| Diagnóstico longitudinal / recalibración | US-BE-016 exclusión S4; planificar **Sprint 07** |
| Bankroll COP sesión | **D-04-001** |

*Las US de Sprint 07 se redactan al cerrar alcance S6.*
