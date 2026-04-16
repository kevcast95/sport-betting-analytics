# Sprint 06.4 — US

> **Base normativa:** [`PLAN.md`](./PLAN.md), [`DECISIONES.md`](./DECISIONES.md), **[`../sprint-06.3/ROADMAP_PO_NORTE_Y_FASES.md`](../sprint-06.3/ROADMAP_PO_NORTE_Y_FASES.md)**.  
> **Sprint anterior:** [`../sprint-06.3/US.md`](../sprint-06.3/US.md) — **no** reabrir US de cierre F2/Fase 1 aquí.  
> **Contrato de formato US:** [`../../01_CONTRATO_US.md`](../../01_CONTRATO_US.md).  
> **Numeración continua:** BE **US-BE-058 … US-BE-062**; OPS desde **US-OPS-003** (tras US-OPS-002 en Sprint 02).  
> **Convención:** cambios de alcance en código → nueva US o nueva decisión en `DECISIONES.md`.

### Convención de alcance S6.4

**Fase 2 / F3:** política de frescura (SM/CDM vs DSR), observabilidad de coste y **medición/discovery** en **US-BE-061** + **US-BE-062** (**D-06-065**), con parámetros de ejecución en **D-06-068**. **Persistencia:** **T-287**, **T-288** (**D-06-067** §3). **SofaScore:** solo discovery (**D-06-066**).

**Fuera de alcance:** F4, F5, reapertura normativa F2/S6.3.

* * *

## Matriz de trazabilidad (decisiones → US)

| Decisión | US |
|----------|-----|
| D-06-062 Fase 2 / F3 | US-BE-058, US-BE-059, US-OPS-003 |
| D-06-063 verdad madre roadmap | transversal — todas |
| D-06-064 SM vs DSR | US-BE-058, US-BE-059 |
| D-06-065 una sola vía medición tiempo hasta lineup/O-U | US-BE-061, US-BE-062 |
| D-06-066 benchmark SofaScore solo discovery | US-BE-062 |
| D-06-067 medición intradía SM insumo política | US-BE-061 |
| D-06-068 congelación operativa 061/062 | US-BE-061, US-BE-062 |

* * *

## Backend — política y desacoplamiento

### US-BE-058 — Acta de política de frescura: qué refresca, frecuencia, CDM/SM vs DSR

#### 1) Objetivo de negocio

Tener una **regla escrita y defendible** que responda: qué datos se mantienen frescos por **ingesta SM/CDM**, cada cuánto o bajo qué ventanas, qué vive solo en capa CDM/SM, y **cuándo** un refresh justifica **nueva invocación DSR**.

#### 2) Alcance

- Incluye: documento normativo en repo (o sección congelada en `DECISIONES.md` + anexo) con tabla o equivalente: entidad/tipo de dato, fuente, frecuencia o disparador, efecto en snapshot/`ds_input`, **¿DSR? sí/no y condición**.  
- Incluye: criterios de “cambio material” que autoricen DSR frente a “solo CDM”.  
- Excluye: diseño de mix de mercados en slate (F4); reglas de franjas usuario (F5).

#### 3) Criterios de aceptación

1. PO/TL reconocen el documento como **acta de política F3** enlazada desde `PLAN.md` o `DECISIONES.md`.  
2. Queda explícito qué **no** se resuelve en S6.4 (F4/F5) para evitar scope creep.  
3. Referencia explícita al roadmap PO **Fase 2 / F3**.

#### 4) Definition of Done

- Texto mergeado + enlace desde `TASKS.md` (tareas de documentación asociadas cerradas).  
- Revisión breve registrada en [`EJECUCION.md`](./EJECUCION.md) (fecha, participantes opcional).

* * *

### US-BE-059 — Implementación técnica mínima alineada a la política SM vs DSR

#### 1) Objetivo de negocio

Que el comportamiento del sistema **refleje** la política: jobs o flags que permitan refresco CDM sin re-disparar DSR salvo condiciones acordadas.

#### 2) Alcance

- Incluye: ajustes puntuales en jobs, orquestación o configuración (`settings`, cron, feature flags) según diseño del kickoff.  
- Incluye: hooks mínimos para contar **invocaciones DSR** y **ciclos de ingesta SM** (o proxies defendibles) si no existen.  
- Excluye: nuevo motor de señal; rediseño completo de snapshot salvo lo indispensable para cumplir la política.

#### 3) Dependencias

- Bloqueante: **US-BE-058** aprobada en contenido esencial (puede implementarse en paralelo el “scaffolding” solo si está claro que no contradice el acta final).

#### 4) Criterios de aceptación

1. En entorno de prueba se puede demostrar **al menos un** escenario “CDM refrescó sin DSR” y **al menos un** escenario “DSR autorizado por política”.  
2. Los límites o cupos acordados están **configurables** o documentados como fijos con justificación.  
3. Tests o smoke automatizado donde el repo ya tenga patrón equivalente.

#### 5) Definition of Done

- PR mergeado con referencia a US-BE-059 y a D-06-064.  
- Nota técnica corta (comentario en `HANDOFF_BE_EJECUCION_S6_4.md` o runbook) con orden de despliegue.

* * *

## Backend — US-BE-060 (sin ejecución en S6.4)

**US-BE-060** se deja como **identificador reservado**; **no** hay tareas en `TASKS.md`. El contenido que antes se asociaba a “piloto tiempo hasta lineup/O-U” se hace solo vía **US-BE-061** (SM, día) y **US-BE-062** (5 ligas, SM vs SofaScore). Ver **D-06-065**.

* * *

## Backend — medición / discovery (prioritario)

### US-BE-061 — Medición intradía SportMonks: lineups y mercados relevantes en el día

#### 1) Objetivo de negocio

Disponer de series temporales defendibles sobre **cuándo** SportMonks expone **lineups** y las familias **FT_1X2**, **OU_GOALS_2_5**, **BTTS**, según **D-06-068**, para alimentar evidencia hacia **US-BE-058** (sin fijar aún la política final F3).

#### 2) Alcance

- Universo, cadencia, definiciones de disponible y familias: **solo** según **D-06-068** (implementar en **T-280**/**T-281** sin reabrir debate en código).  
- **Persistencia:** **T-287**; análisis EOD por SQL. Logs no sustitutos.  
- Excluye: verdad oficial BT2, F4, fallback no-SM, política DSR productiva (**D-06-067**).

#### 3) Referencia técnica (repo)

Revisar integración SM existente en CDM/BT2 (`scripts/bt2_cdm/`, includes SM) para no duplicar clientes; procesadores legacy de odds/lineups del monolito scraper **no** son obligatorios para SM salvo se reutilice código común.

#### 4) Criterios de aceptación

1. El job puede ejecutarse **manualmente** y, si aplica, bajo cron documentado sin tocar fallback productivo.  
2. **T-287** consultable por SQL por `sm_fixture_id` y día: primera observación con lineup según **D-06-068** §4; primera por familia **D-06-068** §3 y §5; frecuencia.  
3. Evidencia en [`EJECUCION.md`](./EJECUCION.md): tabla **T-287**, **2–3** queries, extracto; referencia explícita **D-06-068**.  
4. PR/runbook declaran TZ usada para `kickoff_at` y cadencia **D-06-068** §2.

#### 5) Definition of Done

- Migración **T-287** + job + runbook. **D-06-067**, **D-06-068**; tasks **T-280, T-287, T-281, T-282**.

* * *

### US-BE-062 — Benchmark SportMonks vs SofaScore (5 ligas): frescura y disponibilidad

#### 1) Objetivo de negocio

Comparar, para el **mismo universo** que **US-BE-061** (**D-06-068** §1), disponibilidad y orden temporal **SM** (desde **T-287**) vs **SofaScore** (**T-288**), mismas señales **D-06-068** §3 y reglas de disponible **§4–§5**.

#### 2) Alcance

- Mapeo SM ↔ SofaScore según **D-06-068** §6, persistido en **T-283** (`needs_review` donde aplique).  
- **T-288:** solo SofaScore; **T-287** = lado SM. Código referencia: `processors/lineups_processor.py`, `core/scraped_odds_anchor.py`, `processors/odds_all_processor.py`, `processors/odds_feature_processor.py`.  
- Informe = SQL sobre **T-287** ∪ **T-288** + **T-283** + export.  
- **Excluye:** fallback productivo (**D-06-066**).

#### 3) Criterios de aceptación

1. Informe desde **T-287** ∪ **T-288** (+ **T-283**), universo **D-06-068** §1.  
2. “Disponible” según **D-06-068** §4–§5 (SM en **T-287**, SofaScore en **T-288**).  
3. SQL de ejemplo: primera lineup y primera mercado relevante **por proveedor**; frecuencia; comparación temporal.  
4. Disclaimer benchmark en PR y artefacto (**D-06-066**).

#### 4) Definition of Done

- Migraciones **T-283**, **T-288** + jobs + evidencia en `EJECUCION.md`. **D-06-068**, **D-06-066**.  
- Gate: **T-286**.

* * *

## Operación

### US-OPS-003 — Observabilidad, coste y runbooks de frescura (F3)

#### 1) Objetivo de negocio

Operación puede **ver y auditar** coste y cadencia de refrescos sin mezclar frentes; runbook de “qué hacer si…” alineado a la política.

#### 2) Alcance

- Incluye: runbook o ampliación de runbook existente (p. ej. bajo `docs/bettracker2/runbooks/`) enlazado desde este sprint: métricas mínimas, alertas suaves, revisión manual.  
- Incluye: checklist de validación post-despliegue para cambios F3.  
- Excluye: diseño de producto F5; SLAs comerciales no acordados.

#### 3) Criterios de aceptación

1. Documento enlazado desde [`HANDOFF_BE_EJECUCION_S6_4.md`](./HANDOFF_BE_EJECUCION_S6_4.md) y desde [`PLAN.md`](./PLAN.md) o `EJECUCION.md`.  
2. Lista explícita de **métricas a validar** en cada corrida relevante (SM vs DSR).

#### 4) Definition of Done

- Runbook accesible en repo; evidencia de una corrida de validación en `EJECUCION.md`.

* * *

*2026-04-15 — US S6.4; **D-06-068** congelación operativa 061/062.*
