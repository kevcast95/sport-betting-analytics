# Resumen técnico BetTracker 2.0 — Hilo de avances (S1 en adelante)

**Audiencia:** agente o persona nueva (BA/PM, FE, BE) que necesita **contexto técnico** y **rumbo** sin leer todos los `US.md`.  
**Fuente de verdad operativa:** `sprints/sprint-XX/US.md` + `TASKS.md` + `DECISIONES.md` de cada sprint. Si algo contradice este resumen, **mandan los archivos del sprint**.

**Hilo único de avances (macro):** este archivo concentra el **relato y el estado** sprint a sprint. Al **cerrar** un sprint (p. ej. S5), el BA/PM **actualiza** aquí: marca el sprint como cerrado en su sección, resume entregables y deudas conocidas, ajusta **«Pendiente de cierre»** / **«Hacia dónde vamos»**, y cuando arranque el siguiente añade (o adelanta) su **sección resumida** más **§8**. No sustituye `US.md` ni `TASKS.md`; evita depender solo del historial de chat. Reinicio de contexto en el hilo BA/PM: [`agent_roles/ba_pm_agent.md`](./agent_roles/ba_pm_agent.md).

---

## 1. Producto y arquitectura (estable)

- **BetTracker 2.0** es un protocolo de **gestión conductual y riesgo** (no “solo picks”). Ver [`00_IDENTIDAD_PROYECTO.md`](./00_IDENTIDAD_PROYECTO.md): API-first, capa anti-corrupción (CDM), UI en **español**, métricas traducibles a lenguaje humano.
- **V1** (scraper + SQLite + flujos legacy) y **V2** conviven: rutas V2 bajo **`/v2/*`**. Ver [`03_RUTAS_PARALELAS_V1_V2.md`](./03_RUTAS_PARALELAS_V1_V2.md).
- **Stack:** `apps/web` (React, Vite, Tailwind, Zustand, Framer Motion) · `apps/api` (FastAPI) · PostgreSQL para dominio BT2 (tras S2/S3).
- **Contrato HTTP BT2:** prefijo **`/bt2`** (independiente del API del scrapper). Tipos TS alineados a OpenAPI donde aplique (`bt2Types.ts`, etc.).
- **Arranque local:** [`LOCAL_API.md`](./LOCAL_API.md) (FastAPI + SQLite Copa + `/bt2` en Postgres según configuración).

---

## 2. Sprint 01 — Shell V2 + stub API

| Capa | Entregado (documentado) |
|------|-------------------------|
| **FE** | **US-FE-001 … US-FE-024:** Auth búnker (login/signup mock), contrato de disciplina, layout (`BunkerLayout`), flujo guardas → diagnóstico → bóveda, liquidación (mock), bankroll local, ledger/rendimiento/cierre del día en **modo demo**, tours, identidad visual “Zurich Calm” ([`04_IDENTIDAD_VISUAL_UI.md`](./04_IDENTIDAD_VISUAL_UI.md)). |
| **BE** | **US-BE-001:** API **`/bt2/*` en stub** (sin persistencia BT2 real): esquemas Pydantic + GET de lectura alineados a **US-DX-001** para que el FE pueda sustituir mocks después. Código: `apps/api/bt2_schemas.py`, `bt2_router.py`, registro en `main.py`. |

**Estado doc:** FE Sprint 01 **Done** (2026-04-04 en `sprints/sprint-01/US.md`).

---

## 3. Sprint 02 — Datos e infraestructura (“sprint de datos”)

| Enfoque | Contenido |
|---------|-----------|
| **OPS / BE** | PostgreSQL local (Docker), settings BT2 (`bt2_settings.py`), ingesta masiva histórica (**Atraco**) desde proveedores (Sportmonks Pro + The-Odds-API según plan), tablas raw, workers — **preparación para CDM**. |

**Nota:** En el repo, S02 está planteado como ventana de ingesta; el detalle vive en `sprints/sprint-02/US.md` / `TASKS.md`. El **dominio canónico servido por API** se consolida en **Sprint 03**.

---

## 4. Sprint 03 — Conexión backend (CDM + auth + API real)

| Enfoque | Contenido |
|---------|-----------|
| **BE** | Normalización **CDM** (`bt2_leagues`, `bt2_teams`, `bt2_events`, `bt2_odds_snapshot`, job `normalize_fixtures.py`), usuarios **`bt2_users`**, **JWT**, sustitución progresiva de stubs en `bt2_router` por lectura **PostgreSQL** (orden doc: meta → session → vault → metrics). |
| **FE** | Documentado como **no objetivo S3**; conexión cliente planificada en **Sprint 04**. |

---

## 5. Sprint 04 — Dominio conductual + integración FE

| Capa | Entregado (núcleo) |
|------|---------------------|
| **BE** | **US-BE-009+:** tablas conductuales (`bt2_picks`, `bt2_operating_sessions`, `bt2_bankroll_snapshots`, `bt2_dp_ledger`, `bt2_user_settings`, …), **POST/GET** picks, **settle** con resultados desde `bt2_events`, sesión operativa, idempotencia donde aplica. |
| **FE** | **US-FE-025 … US-FE-030:** desacople de mocks hacia **API real** (bóveda, auth JWT, bankroll/sesión persistentes vía API, liquidación con BD), copy/glosario, alineación DP/métricas V2 tras auditoría. |

**Estado doc:** Sprint 04 **Done** (cierre administrativo 2026-04-04); puede quedar backlog puntual (p. ej. UI dp-ledger opcional → arrastrado a S5).

---

## 6. Sprint 05 — Cierre API-first del Búnker V2 (en curso / planned)

**Objetivo (una frase):** coherencia **servidor** para ledger DP, bóveda con metadatos de evento, liquidación/copy **+10 gestión**, resumen de día, y ampliaciones de contrato (pick liquidado, cierre sesión, liquidación dual, bankroll emulado) **sin** meter en este sprint el **motor DSR + cron CDM + analytics amplio** (eso va a **Sprint 06**).

| Pilar | Contenido técnico |
|-------|-------------------|
| **BE** | Ledger **desbloqueo premium** y penalizaciones (**US-BE-017**); **`GET /bt2/operating-day/summary`** (**US-BE-018**); bóveda con **`kickoffUtc`**, **`eventStatus`**, **`isAvailable`** (**US-BE-019**); settle **+10 DP** won/lost/void (**US-BE-020**); recompensa cierre sesión (**US-BE-021**); liquidación dual / `settlement_source` (**US-BE-022** fases); normalización mercado en **`POST /bt2/picks`** (**US-BE-023**); **PickOut ampliado** en lista/detalle (**US-BE-018 §9**, tarea **T-152**). |
| **FE** | DP ledger UI (**US-FE-031**), hidratar trade/ledger/métricas desde API (**US-FE-032**), compromiso explícito con pick (**US-FE-033**), integridad Santuario/Perfil/Bóveda (**US-FE-034**), copy +10 liquidación (**US-FE-035**), detalle pick liquidado → settlement (**US-FE-036**), copy cierre día (**US-FE-037**), liquidación dual UI (**US-FE-038**), bankroll emulado UI (**US-FE-039**). **T-169:** bóveda anti-stale (persist Zustand + día operativo), preview hora, etiquetas de estado. |
| **DX** | **US-DX-001:** catálogo `reason` ledger, mercados, perfiles; refinamiento con **T-144** y bump **`contractVersion`** coordinado. |

**Calendario explícito del repo:** motor DSR, cron `fetch_upcoming`, enum mercados “duro”, analytics amplio → **`sprints/sprint-06/`**; parlays y diagnóstico longitudinal → **Sprint 07**. Ver `sprints/sprint-05/PLAN.md`, `DECISIONES.md` **D-05-001**, `sprints/sprint-06/PLAN.md`.

**Pendiente de cierre S5:** ver checkboxes abiertos en `sprints/sprint-05/TASKS.md` (**T-142 … T-152**, **T-169**, checklist `npm test` / smoke).

### 6.1 Sprint 05.1 — Refinement (paralelo / tras S5)

Carpeta **`sprints/sprint-05.1/`**: **RFB-09** — premium desbloqueo vs tomar (**US-BE-029**, **US-FE-040**, **T-170–T-173**, **D-05.1-001/002**); **RFB-01/10** — cabecera V2 (**US-FE-043**, **T-174–T-176**, **D-05.1-003**); **RFB-07/08** — `PickCard` post-inicio + premium bloqueado (**US-FE-044**, **T-177–T-179**, **D-05.1-004/005**); **RFB-11/12/13** — ledger/rendimiento copy honesto (**US-FE-045**, **T-180–T-182**, **D-05.1-006–008**); **RFB-02/03/04/14/15** — Santuario, glosario, sync DP, doble fetch (**US-FE-046 … US-FE-049**, **T-183–T-187**, **D-05.1-009–013**). **RFB-05/06** — bóveda post–kickoff y franjas: backlog **[`sprints/sprint-05.2/`](./sprints/sprint-05.2/PLAN.md)** (**US-BE-030/031**, **US-FE-050/051**, **T-188+**). Índice refinement: [`refinement_feedback_s1_s5/DECISIONES.md`](./refinement_feedback_s1_s5/DECISIONES.md).

---

## 7. Mapa rápido de código

| Área | Ubicación habitual |
|------|---------------------|
| API BT2 | `apps/api/bt2_router.py`, `bt2_schemas.py`, `bt2_models.py`, migraciones Alembic bajo `apps/api/` |
| Web V2 | `apps/web/src/pages/*`, `layouts/*`, `store/*` (Zustand + persist cifrada), `components/vault/*`, settlement, ledger, etc. |
| Roles de agente | **BA/PM (este hilo):** [`agent_roles/ba_pm_agent.md`](./agent_roles/ba_pm_agent.md) · **Analistas por capa:** [`agent_roles/front_end_agent.md`](./agent_roles/front_end_agent.md), [`agent_roles/back_end_agent.md`](./agent_roles/back_end_agent.md) |
| Handoff backend histórico | [`HANDOFF_BA_PM_BACKEND.md`](./HANDOFF_BA_PM_BACKEND.md); S5: `sprints/sprint-05/HANDOFF_BA_PM_BACKEND_SPRINT05.md`, `BE_HANDOFF_SPRINT05.md` |
| Refinement S5.x | [`sprints/sprint-05.1/PLAN.md`](./sprints/sprint-05.1/PLAN.md), [`US.md`](./sprints/sprint-05.1/US.md), [`TASKS.md`](./sprints/sprint-05.1/TASKS.md) |

---

## 8. Hacia dónde vamos (después de S5)

1. **Cerrar S5** con contratos y UI alineados (ledger, vault, settle, operating-day, extensiones pick/settlement/bankroll según `TASKS.md`).
2. **Sprint 06:** DSR + CDM operativo, ingesta programada, normalización de mercados en serio, OpenAPI/DX, MVP analytics — ver `sprints/sprint-06/US.md` y `TASKS.md` (**T-153+**).
3. **Sprint 07:** parlays, límites diarios, evolución diagnóstico, deudas tipo `unit_value_cop` si se priorizan.

---

## 9. Cómo usar este archivo

- Para **planificar un sprint:** empezar por `README.md` → `sprints/sprint-XX/US.md` → `TASKS.md`.
- Para **decisiones ya tomadas:** `DECISIONES.md` del sprint (p. ej. S5: **D-05-019** bóveda anti-stale y etiquetas de estado).
- Este resumen **no sustituye** las US; sirve para **onboarding**, para el **hilo macro de avances** y para orientar al BA/PM que deriva trabajo a ejecutores FE/BE.

## 10. Alimentar este archivo (cierre / arranque de sprint)

1. **Cierre:** en la sección del sprint que termina, pasar a **Done** (con fecha si quieres), borrar o actualizar **«Pendiente de cierre»** con lo que quedó en `TASKS.md` (o enlazar tareas remanentes al sprint siguiente).
2. **Apertura del siguiente:** documentar el sprint nuevo con objetivo en una frase y tabla breve BE/FE/DX (según `PLAN.md` / US), enlace a `sprints/sprint-0N/`. **Dos convenciones válidas:** (A) insertar **`## 7. Sprint 06 — …`** (etc.) **entre** §6 y el antiguo «Mapa rápido», y **renumerar** en +1 desde Mapa hasta el final del doc; (B) **sin renumerar:** añadir al final **`## 11. Historial — sprints posteriores`** y debajo `### Sprint 06`, `### Sprint 07`, …
3. **§8 «Hacia dónde vamos»:** desplazar el foco (siguiente milestone tras el recién cerrado).
4. **Puntero BA/PM:** si cambia el sprint activo por convención del equipo, una línea en §6/§10 o en el encabezado basta; el detalle sigue en `TASKS.md` abierto.
5. **Pie del documento:** actualizar *Última actualización* y el alcance entre paréntesis (p. ej. `… sprint-06`).

---

*Última actualización: 2026-04-08 — hilo de avances; alineado a `sprints/sprint-01` … `sprint-05`, `sprint-06/PLAN.md`. Tras cerrar S5: §6 en Done, §8 al siguiente hito, bloque del sprint nuevo según §10 (puntos 2 y 5), pie actualizado.*
