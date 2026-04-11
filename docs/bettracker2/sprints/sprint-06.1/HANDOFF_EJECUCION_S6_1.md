# Handoff ejecución — Sprint 06.1

> **Para:** BE, FE, DX (mismo repo).  
> **Fuente de verdad:** [`US.md`](./US.md), [`TASKS.md`](./TASKS.md), [`DECISIONES.md`](./DECISIONES.md); refinement narrativo [`REFINEMENT_S6_1.md`](./REFINEMENT_S6_1.md). Evidencia de cierre: [`EJECUCION.md`](./EJECUCION.md).

## Cesiones por capa (responsable primario)

| Capa | US | Entrega principal |
|------|-----|-------------------|
| **DX** | US-DX-003 | Whitelist + validador + meta + tipos/OpenAPI (**T-171–T-173**). |
| **BE** | US-BE-032 | Builder `ds_input` (**T-174–T-176**). |
| **BE** | US-BE-033 | Pool + premium (**T-177–T-178**). |
| **BE** | US-BE-034 | Post-proceso LLM (**T-181–T-182**). |
| **BE** | US-BE-036 | Flags cobertura + orquestación snapshot / fallback (**T-179–T-180**). |
| **BE** | US-BE-035 | Admin agregados (**T-183**). |
| **FE** | US-FE-055 | Vault + admin copy (**T-184–T-186**). |
| **Todos** | — | **T-187** QA final. |

**Lectura del bloque BE:** el pipeline del día es **pool (T-177)** → **DSR + batch (T-175)** → **Post-DSR (T-181–T-182)** → **orquestación + fallback + flags (T-179–T-180)**. En la tabla, **US-BE-034** va antes que **US-BE-036** para reflejar ese orden lógico (aunque las US conservan su numeración).

## Orden recomendado (dependencias)

1. **T-171** (whitelist) — **bloqueante** para builder y validador. Umbrales y políticas: **D-06-024** … **D-06-026**.
2. **T-172–T-173** en paralelo tras T-171.
3. **T-174–T-176** (builder) — puede arrancar cuando los campos **obligatorios** fase 1 de la whitelist (**T-171**) estén cerrados.
4. **T-177–T-178** (pool) — puede paralelizarse con builder si no tocan mismas líneas; si hay conflicto en `bt2_router`, secuencial: pool primero o después según diff.
5. **T-181–T-182** (post-DSR) — puede arrancar en **paralelo** en cuanto exista el parse de salida DSR (`picks_by_event` o equivalente). **Regla de cableado:** **T-182** vive **dentro** del path que arma el snapshot (mismo servicio/router que terminará en **T-180**): parse → **Post-DSR** → INSERT pick DSR (no persistir JSON crudo).
6. **T-179–T-180** (flags + orquestación) — **después** de **T-175** (builder en batch), preferible **después** de **T-177–T-178** (pool real), y **con T-182 ya integrado** en el flujo que persiste picks, de modo que **T-180** encadena DSR → post-proceso → fallback → flags (**D-06-022**, **D-06-026** §6). Si se divide en PRs: **T-181** + tests primero → **T-182** en el pipeline → **T-179–T-180** cierran comportamiento día completo.
7. **T-183** (admin) — BE lógicamente independiente del flujo de bóveda; **`bt2Types.ts`** es compartido: coordinar con FE en el mismo PR o PRs consecutivos si ambos capas lo modifican. Alinear el JSON de respuesta admin con **OpenAPI** antes de que **FE** cierre **T-186**.
8. **FE — T-184–T-185** (bóveda) — **después** de **T-173** (OpenAPI + `bt2Types.ts` con los campos nuevos) **y** de que **T-179–T-180** expongan esos campos en la API de bóveda (si no hay stub acordado, la integración FE contra API real queda bloqueada). Referencia de contrato: **T-173**; referencia de comportamiento: **US-BE-036**.
9. **FE — T-186** (admin) — **después** de **T-183** (forma del JSON admin) **y** de que el contrato admin figure en **OpenAPI** / tipos que consuma la web. Puede solaparse con **T-184–T-185** si dos devs distintos y el contrato admin ya está fijado en PR de BE.
10. **Evitar** mocks FE más allá de un spike breve: **OpenAPI** y tipos generados/actualizados son la fuente de verdad para **T-184** y **T-186**.
11. **T-187** — cierre QA transversal (`pytest` sobre módulos BT2 tocados, `npm test`, `npm run build` en `apps/web`) cuando **T-171–T-186** del alcance estén integradas en la rama de cierre.

## Puntos de sincronía (evitar retrabajo)

- **PO/BA:** fuente de verdad **D-06-024** … **D-06-026**; **US.md** alineado — cambios solo vía enmienda explícita en **DECISIONES** / **TASKS** (**D-06-023**).
- **BE ↔ FE (bóveda):** campos nuevos acordados en **US-DX-003** / **T-173** (vacío operativo, lineage, degradación / `limited_coverage`, etc.) deben existir en **OpenAPI**, en la **respuesta real** del endpoint de bóveda tras **T-179–T-180**, y en **`bt2Types.ts` + consumo** en **T-184–T-185**.
- **BE ↔ FE (admin):** forma del JSON del endpoint admin de **T-183** documentada en **OpenAPI**; **T-186** consume esa forma (leyendas y métricas **US-BE-035** sin mezclar semánticas).
- **No** implementar **T-188** (auditoría CDM) en S6.1 hasta **decisión explícita de PO** y nueva entrada en **DECISIONES** / **TASKS**.

## Rollback

- Revertir bump `contractVersion` y flags nuevos si falla integración; mantener `BT2_DSR_PROVIDER=rules` en entornos afectados según runbook.

---

## REFINEMENT_S6_1

> **Fuente narrativa:** [`REFINEMENT_S6_1.md`](./REFINEMENT_S6_1.md). **Decisiones:** **D-06-027** … **D-06-030**. **US:** **US-BE-037–039**, **US-FE-056**. **Plan resumido:** [`PLAN.md`](./PLAN.md) § REFINEMENT_S6_1.

### Cesiones (refinement)

| Capa | US | Entrega principal |
|------|-----|-------------------|
| **BE** | **US-BE-037** | **T-189–T-190** — histórico duelo + cuotas históricas si existen; builder. |
| **BE** | **US-BE-038** | **T-191** — prompt batch `bt2_dsr_deepseek.py` ↔ **D-06-027** / **D-06-030**. |
| **BE** | **US-BE-039** | **T-192** — Post-DSR coherencia `selection` / `razon`. |
| **FE** | **US-FE-056** | **T-194** — copy bóveda/admin. |
| **Todos** | — | **T-193** — doc handoff + pytest + filas en **EJECUCION.md** § REFINEMENT_S6_1. |

### Orden recomendado (dependencias)

1. **T-189** → **T-190** — Sin nuevas claves hacia el LLM sin pasar por **T-171** / **T-172** (DX). Si **T-171** debe ampliarse, PR DX antes o en el mismo bundle con revisión explícita.
2. **T-191** — Puede ir en paralelo al builder si solo cambia texto y tests; validar con PO antes de merge (**D-06-030**).
3. **T-192** — Tras pipeline Post-DSR estable (**T-182**); no reintroducir JSON crudo.
4. **T-194** — Después de redacción final de **T-191** (o copy provisional acordado con PO).
5. **T-193** — Último: documentación de tablas ↔ `processed`, regresión `pytest`, completar tabla en **EJECUCION.md**.

### Sincronía

- **BE ↔ DX:** ampliaciones de whitelist por **T-190** coordinadas con **T-172** / bump meta si el cliente ve nuevos campos (**T-173**).
- **PO/BA:** aprobación explícita del texto del prompt (**T-191**) y de copy FE (**T-194**).

### REFINEMENT_S6_1 — Tabla fuente Postgres ↔ bloques `processed` (T-193)

| Bloque `processed` | Tabla(s) / origen | Notas |
|--------------------|-------------------|--------|
| `odds_featured.consensus` (+ `by_bookmaker`) | `bt2_odds_snapshot` vía `aggregate_odds_for_event` | Sin cambio Sprint 06. |
| `odds_featured.ingest_meta` | `bt2_odds_snapshot` (`MIN`/`MAX` `fetched_at`, `COUNT(DISTINCT date_trunc('minute', …))`) | **T-190:** ventana de ingesta; no es serie histórica por selección. |
| `h2h` | `bt2_events` (`status='finished'`, `result_*` no expuestos en JSON; solo agregados duelo) | **T-189** |
| `statistics` | `bt2_events` (forma reciente W/D/L por equipo, hasta 5 partidos) | **T-189** |
| `team_streaks` | Derivado en memoria desde la forma | **T-189** |
| `lineups` | `raw_sportmonks_fixtures.payload` → resumen (`lineup_rows_observed`, `teams_distinct`, …) | Si no hay fila raw o sin array `lineups`, `available` sigue false y causa en `diagnostics.fetch_errors`. |
| `team_season_stats` | *Sin tabla agregada temporada en BT2* | `{available: false}` + `fetch_errors` documentando gap (**D-06-028** / coordinación DX). |

`diagnostics.h2h_ok`, `statistics_ok`, `lineups_ok` reflejan si se pudo poblar el bloque correspondiente con datos consultables.

---

*2026-04-09 — Orden BE Post-DSR → orquestación; FE bóveda vs admin; sync DoR, **EJECUCION.md**, D-06-026 §6. **REFINEMENT_S6_1** añadido mismo día.*
