# Sprint 06 — Decisiones

## D-06-001 — Calendario: Sprint 06 = motor + datos; Sprint 07 = parlays + diagnóstico + D-04-001

**Contexto:** El equipo repitió la etiqueta “Sprint 5/6” en conversaciones; en repo ya vale **D-05-001** (S5 = cierre V2, S6 = motor, S7 = parlays/diagnóstico).

**Decisión:** **Sprint 06** implementa y documenta: **DSR+CDM**, **cron fetch_upcoming**, **enum/normalización mercados**, **US-DX/OpenAPI** asociado, **analytics picks/bóveda** (MVP acotado en **D-06-004**). **Sprint 07** acoge parlays, recalibración diagnóstico longitudinal y **D-04-001** salvo cambio explícito de PM.

---

## D-06-002 — DSR y backtesting: fases y anti-fuga de información

**Contexto:** Los picks deben incorporar **criterio del modelo** sobre edge/selección; un diseño ingenuo expone **resultados históricos** al razonador y contamina backtest.

**Decisión (marco):**

1. **Fase A — Offline / diseño:** definir qué features puede ver DSR en entrenamiento o evaluación y qué queda **bloqueado hasta kickoff** (lista cerrada por BA BE + DS).
2. **Fase B — Producción diaria:** el input a DSR para el día **D** solo incluye datos permitidos por el contrato **US-DX-002** (sin “resultado del partido” ni estadísticas post-match para eventos aún no jugados).
3. **Trazabilidad:** versionar `ds_input` / hash o `pipeline_version` en BD o artefacto para auditoría.

**Trade-off:** Más ingeniería upfront; menos riesgo de “edge fantasma” en informes al PO.

**Trazabilidad:** **US-BE-025**, **US-DX-002**, **T-154+** en [`TASKS.md`](./TASKS.md).

---

## D-06-003 — Mercados CDM: enum canónico en picks (evolución D-04-002)

**Contexto:** Hoy coexisten `'1X2'`, `'Match Winner'`, `'Full Time Result'`, etc.; **settle** y queries son frágiles (**D-04-002** Sprint 04).

**Decisión:** Introducir **valor canónico** persistido (enum o tabla de referencia) en **`bt2_picks`** / snapshot que alimenta vault, mapeado desde Sportmonks en **ingesta o en capa ACL**; `_determine_outcome` (o sucesor) consume **solo** canónicos. El FE recibe el canónico + `*_human_es` si hace falta copy.

**Consecuencia:** Migración o backfill controlado; coordinación con **Sprint 05** **US-BE-023** si ya tocó `market` (sin duplicar narrativas: una sola fuente tras merge de ramas).

**Trazabilidad:** **US-BE-027**, **US-DX-002**, **US-FE-054** *(o US-FE-052 si se unifica)*.

---

## D-06-004 — Analytics picks/bóveda: MVP vs ampliación

**Contexto:** El producto pide analytics; sin acotar se diluye el sprint.

**Decisión (borrador — PO cierra):**

- **MVP S6:** agregados servidor **leíbles en V2** (p. ej. conteos por tier, odd mínima cumplida, distribución outcomes snapshot, serie temporal por `operating_day_key`) expuestos en **uno o dos endpoints** + **una vista FE** (p. ej. ampliación Performance o sección Santuario con datos reales).
- **Fuera MVP S6:** dashboards BI completos, export CSV, segmentaciones avanzadas — backlog o S7.

**Trazabilidad:** **US-BE-028**, **US-FE-053**, **T-157+**.

---

## D-06-005 — Cron `fetch_upcoming`: responsabilidad y runbook

**Contexto:** En Sprint 04 el script es **ejecución manual**; producción requiere horario y observabilidad.

**Decisión:** El **job** corre en el entorno acordado (cron host, k8s CronJob, o GitHub Actions con secretos) con **runbook** **US-OPS-001**: hora UTC, reintentos 429, alerta si 0 fixtures en ventana esperada, logs estructurados.

**Trazabilidad:** **US-BE-026**, **US-OPS-001**, **T-159**, **T-160**.

---

## D-06-006 — operatorProfile y métricas conductuales en DX

**Contexto:** Si el diagnóstico u operador expone `operatorProfile` en métricas para UI, hace falta **catálogo estable** (alias camelCase, valores cerrados).

**Decisión:** Ampliar **US-DX-002** con tabla `operatorProfile` / valores permitidos y su **`label_es`**; ningún valor nuevo en JSON de API sin fila en catálogo.

**Trazabilidad:** **US-DX-002**, **US-FE-052** si el FE muestra perfil en analytics.

---

*Más entradas D-06-00n al cerrar refinamiento con PO/BE.*
