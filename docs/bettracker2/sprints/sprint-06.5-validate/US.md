# Sprint 06.5 — Validate SFS — US

> Definición madre: [`cursor_prompt_s6_5_validate_sfs.md`](./cursor_prompt_s6_5_validate_sfs.md).  
> Contrato de formato: [`../../01_CONTRATO_US.md`](../../01_CONTRATO_US.md).  
> Decisiones: [`DECISIONES.md`](./DECISIONES.md).  
> **Sin `US-FE-*`**, **sin UI** en este sprint.

**Numeración continua:** BE **US-BE-058** … **US-BE-065**; DX **US-DX-005**; OPS **US-OPS-003**.

* * *

## Matriz decisión → US

| Decisión | US |
|----------|-----|
| D-06-062 … D-06-065 | US-DX-005, US-BE-058, US-BE-059 |
| D-06-066 | US-DX-005 |
| D-06-067 | US-BE-062 |
| D-06-068 | US-BE-063, US-BE-065 |
| D-06-069 | US-BE-058 |
| D-06-070 | US-BE-064 |
| D-06-073 | US-OPS-003 |
| D-06-071, D-06-072 | US-BE-065 |

* * *

## Contratos / DX

### US-DX-005 — Canónico v0 (4 familias) y alias por `source_scope` / proveedor

#### 1) Objetivo de negocio

Fijar un vocabulario **pequeño y cerrado** para mapear `featured` / `all` de SFS (y lecturas SM equivalentes) a claves canónicas, sin catálogo gigante.

#### 2) Alcance

- Incluye: documento bajo `docs/bettracker2/dx/` (nombre acordado en PR) con `FT_1X2`, `OU_GOALS_2_5`, `BTTS`, `DOUBLE_CHANCE`; tabla alias **por proveedor** y por `source_scope`; regla de deduplicación post-mapeo.
- Excluye: bump de contrato productivo hacia vault/FE; ampliar mercados T-244.

#### 3) Contexto técnico actual

- `apps/api/bt2_market_canonical.py`, whitelist DX existente, **D-06-065** / **D-06-066**.

#### 4) Contrato de entrada/salida (si aplica)

- Entrada: JSON raw `featured` / `all` + `provider` + `source_scope`.  
- Salida: lista de selecciones canónicas `{ family, selection, price, provenance }` trazable a raw hash o puntero.

#### 5) Reglas de dominio

- No unificar `featured` y `all` en raw; solo tras mapeo (**D-06-065**).  
- “Evento útil” = **D-06-066**.

#### 6) Criterios de aceptación

1. Cada familia v0 tiene al menos un ejemplo de mapeo desde SFS documentado.  
2. La definición textual de **evento útil** aparece **idéntica** a **D-06-066** en el doc DX o enlace estable.

#### 7) No-funcionales

- Versionado explícito `canonical_version` string en artefactos generados.

#### 8) Riesgos y mitigación

- **Riesgo:** shape SFS cambia → **Mitigación:** tests con fixture congelado + `canonical_version` bump.

#### 9) Plan de pruebas

- Tests unitarios de mapeo sobre fixtures JSON mínimos (featured + all separados).

#### 10) Definition of Done

- Doc mergeado + referencia en `EJECUCION.md` bajo un `run_id` de smoke.

Madre: **D-06-066**, prompt §Modelo canónico.

* * *

## Backend

### US-BE-058 — Persistencia experimental `bt2_provider_odds_snapshot` + retención e idempotencia

#### 1) Objetivo de negocio

Persistir odds multi-proveedor en staging con trazabilidad por `run_id` y `source_scope`, alineado a **D-06-069**.

#### 2) Alcance

- Incluye: migración Alembic (o script solo-staging hasta migración) para `bt2_provider_odds_snapshot`; columnas mínimas: `bt2_event_id`, `provider`, `source_scope`, `run_id`, `ingested_at_utc`, `raw_payload` o externalización JSONB, `canonical_version`; índice único lógico **D-06-069**.
- Excluye: retención > sprint+30d automatizada si no hay job; documentar manual hasta T-xxx.

#### 3) Contexto técnico actual

- `apps/api/bt2_models.py`, `apps/api/alembic/`.

#### 4) Contrato de entrada/salida (si aplica)

- Upsert por clave **D-06-069**; lectura por `run_id` + `bt2_event_id`.

#### 5) Reglas de dominio

- `provider = sofascore_experimental` (literal acordado) para filas SFS del sprint salvo decisión contraria explícita.

#### 6) Criterios de aceptación

1. Insert + re-run mismo `run_id` no duplica filas lógicas.  
2. Consulta SQL documentada en `EJECUCION.md` devuelve conteos por `source_scope`.

#### 7) No-funcionales

- Migración reversible o plan de rollback documentado.

#### 8) Riesgos y mitigación

- **Riesgo:** mezclar staging con prod → **Mitigación:** DB URL solo staging; checklist **US-OPS-003**.

#### 9) Plan de pruebas

- Tests de modelo/repo o integración mínima con SQLite de test si Postgres no en CI.

#### 10) Definition of Done

- Migración o evidencia de tabla en staging + entrada `EJECUCION.md`.

Madre: **D-06-069**, prompt §Persistencia.

* * *

### US-BE-059 — Provider BT2-SFS: fetchers dedicados `featured` + `all`

#### 1) Objetivo de negocio

Implementar la línea **BT2** para SofaScore (no legacy V1 operativo), solo endpoints obligatorios.

#### 2) Alcance

- Incluye: paquete `apps/api/bt2/providers/sofascore/` (o ruta cerrada en PR) con cliente HTTP, throttling acorde **US-OPS-003**, fetch `odds/1/featured` y `odds/1/all` por `provider_event_ref` resuelto.
- Excluye: otros endpoints; dependencia de `processors/*` legacy como núcleo (solo referencia conceptual).

#### 3) Contexto técnico actual

- Mapa conceptual legacy solo lectura: [`../sprint-06.1/V1_SOFASCORE_A_BT2_DS_INPUT_MAPA.md`](../sprint-06.1/V1_SOFASCORE_A_BT2_DS_INPUT_MAPA.md) (no es runtime).

#### 4) Contrato de entrada/salida (si aplica)

- Input: `provider_event_ref`, `run_id`. Output: blobs raw etiquetados por `source_scope` `featured` / `all`.

#### 5) Reglas de dominio

- Separación estricta **D-06-065**; errores HTTP registrados sin mezclar scopes.

#### 6) Criterios de aceptación

1. Smoke: una corrida guarda dos filas o dos compartimentos distinguibles para el mismo evento y `run_id`.  
2. Logs estructurados con `run_id`, `bt2_event_id`, `source_scope`.

#### 7) No-funcionales

- Timeouts y retry limitados (números en **US-OPS-003** / `EJECUCION.md`).

#### 8) Riesgos y mitigación

- **Riesgo:** 429/ban → **Mitigación:** caps y kill switch **US-OPS-003**.

#### 9) Plan de pruebas

- Mock HTTP o VCR en tests.

#### 10) Definition of Done

- PR mergeado con estructura provider y README corto en carpeta del provider.

Madre: **D-06-064**, prompt §Arquitectura / scrapers dedicados.

* * *

### US-BE-060 — Historical bootstrap 6d (cohorte BT2, seed V1 opcional)

#### 1) Objetivo de negocio

Reconstruir y comparar **6 días UTC cerrados** según ventana en `EJECUCION.md`, acelerando join con seed opcional desde SQLite V1 (**D-06-063**).

#### 2) Alcance

- Incluye: job o script `scripts/` o comando bajo `apps/api` que seleccione cohorte SM por días ancla, opcionalmente lea SQLite solo para IDs, ejecute **US-BE-059** + persistencia **US-BE-058** + mapeo **US-DX-005**.
- Excluye: SQLite como destino de verdad o pipeline principal.

#### 3) Contexto técnico actual

- CDM/SM: `scripts/bt2_cdm/`, tablas `bt2_events`, etc.

#### 4) Contrato de entrada/salida (si aplica)

- CLI: `--anchor-date`, `--run-id`, flags `--allow-v1-seed`.

#### 5) Reglas de dominio

- Cada día cerrado genera métricas referenciadas al mismo `run_id` padre o `run_id` por día documentado.

#### 6) Criterios de aceptación

1. Al menos **una** corrida histórica completa documentada en `EJECUCION.md`.  
2. Si se usó V1 seed, el % de eventos resueltos por capa 1 vs 2 vs 3 exportado.

#### 7) No-funcionales

- Throttling global acorde ops.

#### 8) Riesgos y mitigación

- **Riesgo:** datos SM incompletos en histórico → **Mitigación:** bucket `no_comparable` **D-06-068**.

#### 9) Plan de pruebas

- Dry-run en subset (p. ej. 1 liga) antes de corrida completa.

#### 10) Definition of Done

- CSV/JSON en `out/` o `docs/bettracker2/recon_results/` enlazado desde `EJECUCION.md`.

Madre: prompt §Historical bootstrap.

* * *

### US-BE-061 — Daily experimental path (día actual UTC hasta 00:00 UTC día siguiente)

#### 1) Objetivo de negocio

Observar **día actual** en staging con job temporal controlado hasta corte **D-06-062** prompt.

#### 2) Alcance

- Incluye: job scheduling manual o cron staging únicamente; cohorte SM del día; join; fetch; persist; snapshot de métricas intra-día opcional (configurable, documentado).
- Excluye: FE; prod.

#### 3) Contexto técnico actual

- Misma base que US-BE-060 con ventana 1d.

#### 4) Contrato de entrada/salida (si aplica)

- CLI/Cron con `RUN_ID`, `ANCHOR_DATE_UTC=today`.

#### 5) Reglas de dominio

- Corte estricto 00:00 UTC día siguiente; job no relanza solo salvo runbook **US-OPS-003**.

#### 6) Criterios de aceptación

1. Una corrida daily documentada con timestamps de inicio/corte.  
2. Mismo esquema de métricas que histórico para comparabilidad.

#### 7) No-funcionales

- Kill switch env desactiva fetch.

#### 8) Riesgos y mitigación

- **Riesgo:** solapamiento con otro run → **Mitigación:** `run_id` único por activación manual.

#### 9) Plan de pruebas

- Simulación con reloj mockeado o corrida en día de bajo volumen.

#### 10) Definition of Done

- Sección “Daily path” rellenada en `EJECUCION.md`.

Madre: prompt §Daily experimental path.

* * *

### US-BE-062 — Join BT2 ↔ SFS: 3 capas + overrides manuales

#### 1) Objetivo de negocio

Implementar la **única** estrategia priorizada **D-06-067** y tabla de overrides.

#### 2) Alcance

- Incluye: resolución capa 1→3, persistencia de resultado de join (`valid` / `failed` / `override`), tabla `bt2_sfs_event_override` o nombre cerrado en migración.
- Excluye: ML matching; heurísticas fuera del orden fijo.

#### 3) Contexto técnico actual

- `bt2_events`, equipos, ligas, kickoff UTC.

#### 4) Contrato de entrada/salida (si aplica)

- API interna o función: `(bt2_event_id) -> provider_event_ref | null`.

#### 5) Reglas de dominio

- Determinismo: misma entrada misma salida; overrides ganan a capa 2.

#### 6) Criterios de aceptación

1. Export de `match_rate` reproducible desde SQL.  
2. Overrides documentados (sin PII innecesario) en `EJECUCION.md` si se usan.

#### 7) No-funcionales

- Latencia aceptable para batch (documentada).

#### 8) Riesgos y mitigación

- **Riesgo:** homónimos equipos → **Mitigación:** competición+kickoff obligatorios en capa 2.

#### 9) Plan de pruebas

- Tests unitarios de matching con fixtures de 2 equipos + liga + kickoff.

#### 10) Definition of Done

- Migración si hay tabla nueva + tests verdes.

Madre: **D-06-067**.

* * *

### US-BE-063 — Job de métricas comparativas SM vs SFS (KPI principal y secundarios)

#### 1) Objetivo de negocio

Calcular `match_rate`, `no_comparable_rate`, KPI principal (evento útil **D-06-066**) por proveedor, y tabla solo SM / solo SFS / ambos / ninguno, según **D-06-068**.

#### 2) Alcance

- Incluye: script/job post-`run_id`; salida JSON/CSV; comparación SFS vs SM en **pp** para regla `GO` (≤5 pp peor, >10 pp → `NO-GO` material).
- Excluye: dashboards.

#### 3) Contexto técnico actual

- Snapshots SM existentes (`bt2_odds_snapshot` o agregados); nuevas tablas SFS.

#### 4) Contrato de entrada/salida (si aplica)

- Input: `run_id`. Output: `metrics.json` esquema versionado documentado en `EJECUCION.md`.

#### 5) Reglas de dominio

- Denominadores y exclusiones **exactamente** como **D-06-068** y fórmulas en `EJECUCION.md`.

#### 6) Criterios de aceptación

1. Para al menos un `run_id` histórico y uno daily, métricas completas generadas.  
2. Ningún KPI mezcla raw `featured`+`all` sin breakdown.

#### 7) No-funcionales

- Runtime acotado (documentado).

#### 8) Riesgos y mitigación

- **Riesgo:** SM sin datos en ventana → **Mitigación:** bucket explícito.

#### 9) Plan de pruebas

- Golden file pequeño para `metrics.json`.

#### 10) Definition of Done

- Archivos métricos enlazados en `EJECUCION.md`.

Madre: **D-06-068**.

* * *

### US-BE-064 — Shadow `bt2_dsr_ds_input_shadow` + metadata obligatoria

#### 1) Objetivo de negocio

Demostrar path shadow hacia `ds_input` **sin prod**, con trazabilidad **D-06-070**.

#### 2) Alcance

- Incluye: tabla `bt2_dsr_ds_input_shadow`, escritura desde canónico + contexto evento, **1** E2E + **20** eventos mini cohorte.
- Excluye: merge a builder productivo sin flag desactivado y decisión fuera de sprint.

#### 3) Contexto técnico actual

- `apps/api/bt2_dsr_ds_input_builder.py`, validadores contrato.

#### 4) Contrato de entrada/salida (si aplica)

- JSON column cumpliendo claves mínimas **D-06-070**.

#### 5) Reglas de dominio

- `experimental=true` obligatorio en payload.

#### 6) Criterios de aceptación

1. Veinte filas mínimo de cohorte + 1 E2E con queries de verificación en `EJECUCION.md`.  
2. Lista de placeholders aceptados documentada si aplica.

#### 7) No-funcionales

- No lectura desde rutas prod vault.

#### 8) Riesgos y mitigación

- **Riesgo:** divergencia contrato DSR → **Mitigación:** documentar gap; no bloquea si odds-driven OK **D-06-070**.

#### 9) Plan de pruebas

- Test que valida presencia de claves metadata.

#### 10) Definition of Done

- Evidencia SQL + extracto JSON en `EJECUCION.md`.

Madre: **D-06-070**, prompt §Shadow.

* * *

## Operación

### US-OPS-003 — Presupuesto, caps, responsables, kill switch, job temporal día actual

#### 1) Objetivo de negocio

Operar el piloto sin exceder límites aprobados y con apagado claro.

#### 2) Alcance

- Incluye: documento runbook en `docs/bettracker2/runbooks/` o `sprint-06.5-validate/` (ruta en PR); límites numéricos alineados a `EJECUCION.md`; accountable **PO**, responsible **TL**; checklist apagado; control job daily hasta 00:00 UTC+1.
- Excluye: negociación legal con SofaScore.

#### 3) Contexto técnico actual

- Variables env, cron staging.

#### 4) Contrato de entrada/salida (si aplica)

- Tabla env vars: `BT2_SFS_EXPERIMENT_*` (nombres finales en runbook).

#### 5) Reglas de dominio

- Sin aprobación PO por escrito (comentario PR o `EJECUCION.md`) no se elevan caps.

#### 6) Criterios de aceptación

1. Runbook enlazado desde `EJECUCION.md` § kickoff.  
2. Checklist apagado con owner PO verificado en cierre.

#### 7) No-funcionales

- Alerta mínima si se supera 80% del cap diario (manual o script).

#### 8) Riesgos y mitigación

- **Riesgo:** coste imprevisto → **Mitigación:** kill switch default OFF fuera ventana.

#### 9) Plan de pruebas

- Drill: togglear OFF y verificar que fetch no corre.

#### 10) Definition of Done

- Firma de revisión PO+TL en `EJECUCION.md` (fecha + nombres).

Madre: **D-06-073**, prompt §Gobernanza.

* * *

## Cierre

### US-BE-065 — Acta ejecutiva: veredicto GO / PIVOT / NO-GO + salida F3 + frase Odds API

#### 1) Objetivo de negocio

Cerrar el sprint con **una** etiqueta **D-06-068** y una de las tres salidas **D-06-071**, más frase **D-06-072**.

#### 2) Alcance

- Incluye: sección final `EJECUCION.md` + resumen de 1 página en `docs/...` si el equipo prefiere archivo separado enlazado.
- Excluye: re-plan detallado de F3 (solo etiqueta de salida).

#### 3) Contexto técnico actual

- Salidas de US-BE-063, US-BE-064, US-OPS-003.

#### 4) Contrato de entrada/salida (si aplica)

- Entrada: `metrics.json` final + shadow ok/fail + coste observado.

#### 5) Reglas de dominio

- Veredicto acorde umbrales **D-06-068**; sin contradicciones con números publicados.

#### 6) Criterios de aceptación

1. Texto único `GO|PIVOT|NO-GO` con bullets de evidencia numérica.  
2. Párrafo F3 (una de tres opciones **D-06-071**).  
3. Frase literal **D-06-072** o equivalente aprobado por TL.

#### 7) No-funcionales

- Fecha y firmantes PO+TL.

#### 8) Riesgos y mitigación

- **Riesgo:** datos incompletos → **Mitigación:** `PIVOT` explícito, no `GO` fingido.

#### 9) Plan de pruebas

- Revisión cruzada números vs SQL.

#### 10) Definition of Done

- `EJECUCION.md` sección “Acta final” completa.

Madre: prompt §Veredicto + §Impacto F3 + §The Odds API.

* * *

*Documento derivado exclusivamente del prompt maestro del sprint.*
