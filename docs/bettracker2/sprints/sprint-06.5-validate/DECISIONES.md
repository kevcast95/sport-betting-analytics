# Sprint 06.5 — Validate SFS — DECISIONES

> Definición madre: [`cursor_prompt_s6_5_validate_sfs.md`](./cursor_prompt_s6_5_validate_sfs.md).  
> Jerarquía programa: [`../sprint-06.3/ROADMAP_PO_NORTE_Y_FASES.md`](../sprint-06.3/ROADMAP_PO_NORTE_Y_FASES.md).  
> Convención cambio código: **D-06-023** (sprint-06.3) — cambio normativo en repo → nueva **D-06-0xx** o US antes de merge.  
> Numeración: primera decisión de este sprint **D-06-062** (continúa tras cierre F2 S6.3 **D-06-061**).

* * *

## D-06-062 — Naturaleza experimental; sin FE; sin fallback productivo (2026-04-17)

1. **Sprint 06.5 — Validate SFS** es solo **laboratorio** en staging/experimental: métricas, fetch dedicado BT2, persistencia experimental, shadow path.
2. **No** aprueba fallback productivo, **no** sustituye automáticamente a SportMonks, **no** cambia el truth source oficial productivo (acta T-244 / capas ya cerradas en S6.3).
3. **Prohibido** abrir FE/UI, `US-FE-*` o vistas admin nuevas para este sprint; cierre por docs, queries, JSON/CSV y `EJECUCION.md`.

Trazabilidad: `PLAN.md`, todas las US del sprint.

* * *

## D-06-063 — Cohorte BT2/Postgres; V1 solo bootstrap auxiliar (2026-04-17)

1. La cohorte base del experimento es la definida en **Postgres BT2** (staging) a partir del modelo **SM/CDM** vigente.
2. **V1/SQLite** no es dependencia operativa ni truth source ni pipeline del sprint. Solo: revisión de shapes/endpoints, discovery histórico, y **seed opcional** de `sofascore_event_id` u refs si ya existen en SQLite.
3. Fetch, mapping, persistencia y métricas del experimento son **BT2**, no el job legacy V1.

Trazabilidad: US-BE-060, US-BE-061, US-OPS-003.

* * *

## D-06-064 — Provider propio BT2-SFS; endpoints obligatorios (2026-04-17)

1. La línea SofaScore vive en estructura propia BT2, p. ej. `apps/api/bt2/providers/sofascore/`, separada del legacy V1 como base operativa.
2. Endpoints **obligatorios** para cerrar el sprint: únicamente **`odds/1/featured`** y **`odds/1/all`**. Ningún otro endpoint SFS es obligatorio de cierre.
3. El provider documentado en US/TASKS incluye como mínimo: resolución de eventos / join SFS, fetch de odds, `source_scope`, mapeo canónico, persistencia experimental, reportes comparativos, shadow hacia `ds_input`.

Trazabilidad: US-BE-059, `TASKS.md`.

* * *

## D-06-065 — `featured` vs `all`: raw separado; KPI sin mezcla cruda (2026-04-17)

1. En plano **raw** persistido, `featured` y `all` se almacenan y reportan **por separado** (`source_scope` distinto).
2. La unificación ocurre **solo después** del mapeo canónico, deduplicada y trazable con `source_scope` en metadatos.
3. **Prohibido** publicar un KPI crudo único que mezcle `featured` y `all` sin **breakdown** explícito.

Trazabilidad: US-DX-005, US-BE-058, US-BE-063.

* * *

## D-06-066 — Canónico v0 pequeño; definición de “evento útil” (2026-04-17)

**Familias canónicas v0 obligatorias (solo estas cuatro):**

- `FT_1X2`
- `OU_GOALS_2_5`
- `BTTS`
- `DOUBLE_CHANCE`

**Definición oficial de evento útil (texto único para PLAN/US/EJECUCION):**

> Un evento es **útil** para este sprint si tiene **`FT_1X2` completo** y **al menos una familia core adicional completa** entre `OU_GOALS_2_5`, `BTTS`, `DOUBLE_CHANCE`.

Trazabilidad: US-DX-005, US-BE-063, `EJECUCION.md`.

* * *

## D-06-067 — `% match` (match_rate) y estrategia oficial de join (2026-04-17)

**Fórmula:**

`match_rate = (eventos_BT2_en_cohorte_ejecutada_con_join_SFS_válido) / (total_eventos_BT2_en_cohorte_ejecutada)`

- Denominador: cohorte BT2/SM **ejecutada** en esa corrida.  
- Numerador: subconjunto con **join SFS válido** resuelto por BT2.  
- **No** es la unión de todos los eventos SM y SFS ni “todos los existentes”.

**Estrategia oficial de join (orden fijo, no alternativas abiertas):**

1. Match directo por metadata o IDs si existe en BT2 o seed auxiliar aceptado bajo D-06-063.  
2. Matching **determinista** por competición + equipos + kickoff UTC.  
3. Tabla de **overrides manuales** para excepciones.

Trazabilidad: US-BE-062, US-BE-063.

* * *

## D-06-068 — Bucket `no comparable`; umbrales match; KPI principal; veredicto (2026-04-17)

**Bucket `no comparable`:** existe explícitamente; **fuera del denominador** del KPI principal de cobertura comparada; si **`no comparable` > 15%** de la cohorte ejecutada, **bloquea `GO`**.

**Umbrales `match_rate`:**

- **≥ 85%** → comparación válida para `GO` (sujeto a resto de condiciones).  
- **70%–84%** → diagnóstico útil; **insuficiente para `GO`**.  
- **< 70%** → el sprint se interpreta como **problema de matching**, no de cobertura de mercados; **no `GO`**.

**KPI principal del sprint:**  
**% de eventos comparables** (denominador: eventos con join SFS válido y no en bucket exclusión del KPI; ver `EJECUCION.md` fórmula alineada) con **`FT_1X2` completo + ≥1 familia core adicional completa**, medido **por proveedor** (SM vs SFS) y comparable en la misma definición canónica.

**Secundarios:** solo SM / solo SFS / ambos / ninguno; breakdown por liga si volumen; join miss / no comparable / descartes.

**Veredicto final (obligatorio, una sola etiqueta):**

- **`GO`** solo si: `match_rate ≥ 85%`, `no comparable ≤ 15%`, SFS en el KPI principal **no peor** que SM por más de **5 pp**, shadow `ds_input` probado, y coste/cupos **operables** para ≥1 semana experimental adicional.  
- **`PIVOT`:** join usable pero insuficiente para `GO`, o raw SFS prometedor pero cuello en mapping/processor/canónico/bootstrap.  
- **`NO-GO`:** `match_rate < 70%`, o SFS **materialmente peor** que SM por **>10 pp** en el KPI principal, o falla la prueba mínima de shadow, o coste/operación **no** sostiene una semana adicional razonable.

Trazabilidad: US-BE-063, US-BE-065, `EJECUCION.md`.

* * *

## D-06-069 — Persistencia experimental e idempotencia (2026-04-17)

1. Ruta principal: **Postgres BT2 staging/experimental**, no SQLite como base del experimento.
2. Tabla principal (nombre cerrado): **`bt2_provider_odds_snapshot`** (o prefijo equivalente si Alembic/repo impone otro, documentado en migración).
3. Shadow: **`bt2_dsr_ds_input_shadow`** (mismo criterio de ajuste de prefijo).
4. Retención: durante el sprint, hasta acta final, **+30 días**.
5. Idempotencia: clave lógica mínima `(bt2_event_id, provider, source_scope, run_id)`; re-ejecución mismo `run_id` → upsert/overwrite controlado; **toda métrica referencia un `run_id` concreto**.

Trazabilidad: US-BE-058, US-BE-064.

* * *

## D-06-070 — Shadow `ds_input`: metadata obligatoria (2026-04-17)

Todo registro shadow debe incluir al mínimo en payload o columnas asociadas:

- `experimental=true`
- `odds_provider`
- `truth_source`
- `provider_event_ref`
- `provider_snapshot_run_id`
- `ingested_at_utc`
- `canonical_version`

**Prueba mínima:** **1** fixture end-to-end + **mini cohorte 20** eventos comparables para compatibilidad de shape con `ds_input` actual; placeholders documentados no invalidan el experimento si el fragmento odds-driven funciona.

Trazabilidad: US-BE-064.

* * *

## D-06-071 — F3: solo tres salidas documentales al cierre (2026-04-17)

Sin cerrar F3 por decreto. Al cierre de S6.5 documentar exactamente una:

1. **F3 se simplifica** — evidencia de que el cuello dominante fue fuente/modelado, no refresh tardío.  
2. **F3 sigue pendiente con nueva premisa** — resultado mixto o condicionado por matching/cobertura parcial.  
3. **Se mantiene backlog previo con justificación** — evidencia de que el problema dominante sigue siendo refresh/completitud temporal.

Trazabilidad: US-BE-065, `EJECUCION.md` acta final.

* * *

## D-06-072 — The Odds API: sin implementación; seam explícito (2026-04-17)

No hay implementación de The Odds API en S6.5. Debe quedar esta conclusión explícita en el acta:

**“El seam quedó listo a nivel de contrato, metadatos, persistencia y path de integración; falta adapter específico para The Odds API.”**

Trazabilidad: US-DX-005, US-BE-058, US-BE-065.

* * *

## D-06-073 — Operación obligatoria (2026-04-17)

**US-OPS-003** es **obligatoria**, no opcional: presupuesto de llamadas, límites, responsable (accountable **PO** para presupuesto/aprobación; **TL** responsible de throttling/caps/diseño), checklist de apagado, control del job temporal del día actual.

Trazabilidad: US-OPS-003, `TASKS.md`.

* * *

*Documento derivado exclusivamente del prompt maestro del sprint.*
