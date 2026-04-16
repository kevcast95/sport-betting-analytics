# Sprint 06.4 — TASKS

> **Sprint:** Fase 2 del programa / frente **F3** — frescura vs coste; ingesta SM/CDM vs llamadas DSR.  
> **Numeración:** continúa desde **T-267** (post **T-266** en [`../sprint-06.3/TASKS_CIERRE_F2_S6_3.md`](../sprint-06.3/TASKS_CIERRE_F2_S6_3.md)). Rango S6.4: **T-267 … T-288**. **Medición/discovery:** solo **US-BE-061** (**T-287**) + **US-BE-062** (**T-288**); **US-BE-060** sin tareas (**D-06-065**).  
> **US:** [`US.md`](./US.md). **Decisiones:** [`DECISIONES.md`](./DECISIONES.md). **Plan:** [`PLAN.md`](./PLAN.md).  
> **Orden BE sugerido:** [`HANDOFF_BE_EJECUCION_S6_4.md`](./HANDOFF_BE_EJECUCION_S6_4.md).  
> **Verdad madre programa:** [`../sprint-06.3/ROADMAP_PO_NORTE_Y_FASES.md`](../sprint-06.3/ROADMAP_PO_NORTE_Y_FASES.md).  
> **Prohibido en esta tabla:** tareas cuyo objetivo principal sea F4 (mix mercados / Post-DSR), F5 (UX conductual), o reapertura normativa F2/S6.3.

* * *

## Apto para ejecución (Definition of Ready)

| Qué se confirma | Quién (típico) |
|-----------------|----------------|
| [ ] `ROADMAP_PO_NORTE_Y_FASES.md` (§ Fase 2 / F3) + `PLAN.md` S6.4 leídos; equipo distingue **CDM** vs **DSR**. | TL / PO |
| [ ] `DECISIONES.md` S6.4 con **D-06-062 … D-06-068** aceptadas para kickoff de implementación. | PO / TL |
| [ ] Acta de **US-BE-058** en borrador revisable **antes** de merge de lógica que fije cupos o disparadores DSR. | PO / TL / BE |

* * *

## Checklist de cobertura F3 (capas)

| Capa | US | Tareas |
|------|-----|--------|
| Política escrita y congelación referencia | US-BE-058 | T-267, T-268 |
| Implementación desacoplada SM vs DSR | US-BE-059 | T-269, T-270, T-271 |
| Observabilidad / runbooks | US-OPS-003 | T-272, T-273 |
| Validación integrada / no regresión F3 | transversal | T-274, T-275 |
| Medición intradía SM | US-BE-061 | T-280, T-287, T-281, T-282 |
| Benchmark SM vs SofaScore (discovery) | US-BE-062 | T-283, T-288, T-284, T-285, T-286 |
| Cierre documental sprint | transversal | T-278, T-279 |

* * *

## US-BE-058

- [ ] **T-267 (US-BE-058)** — Redactar y mergear **acta de política de frescura F3**: tabla o matriz *dato/job × frecuencia o disparador × capa persistida (raw/CDM/snapshot) × ¿invoca DSR?*; referencia explícita a `ROADMAP_PO_NORTE_Y_FASES.md` § Fase 2; delimitación F4/F5 fuera de alcance.
- [ ] **T-268 (US-BE-058)** — Enlazar el acta desde `DECISIONES.md` (enmienda o anexo `refs/` si el repo usa esa convención) y desde `PLAN.md`; versión y fecha de la política visibles para operación.

* * *

## US-BE-059

- [ ] **T-269 (US-BE-059)** — Inventariar puntos de código donde hoy se **dispara DSR** o regeneración de insumo costoso; mapear contra la política T-267 y documentar brechas en `HANDOFF_BE_EJECUCION_S6_4.md` § brecha.
- [ ] **T-270 (US-BE-059)** — Implementar **guardas o configuración** mínima para que la ingesta SM/CDM pueda ejecutarse según política **sin** re-DSR automático salvo condiciones explícitas (feature flag, ventana temporal o hash de insumo — según diseño acordado en kickoff).
- [ ] **T-271 (US-BE-059)** — Añadir **contadores o logs estructurados** defendibles: al menos separación *ingesta/jobs SM* vs *runs DSR* (o métricas proxy acordadas); no mezclar con métricas de F2 elegibilidad salvo reutilización read-only.

* * *

## US-OPS-003

- [ ] **T-272 (US-OPS-003)** — Crear o actualizar **runbook** BT2 para operación F3: comandos de corrida, env vars relevantes, “qué revisar si no hay frescura”, enlaces a scripts existentes bajo `scripts/bt2_cdm/` cuando apliquen.
- [ ] **T-273 (US-OPS-003)** — Definir **checklist post-deploy** F3 (3–7 ítems) y ubicarlo en `EJECUCION.md` o en el runbook con enlace bidireccional desde este sprint.

* * *

## Transversal — validación

- [ ] **T-274 (US-BE-059 / US-OPS-003)** — Ejecutar escenario de prueba documentado: **solo CDM** + verificación de que insumo/snapshot refleja datos nuevos sin contar DSR adicional según política.
- [ ] **T-275 (US-BE-059)** — Regresión acotada: tests BT2 afectados + smoke manual mínimo descrito en `EJECUCION.md` (sin expandir alcance a F4).

* * *

## US-BE-061

- [ ] **T-280 (US-BE-061)** — Documentar en PR/runbook la mecánica de **D-06-068** (universo §1, cadencia §2 respecto a `kickoff_at`, familias §3, reglas §4–§5), **TZ** usada para `kickoff_at`, y el **esquema** de **T-287** (append-only). Sin renegociar §1–§5 en código. **Prohibido** como única fuente analítica: solo logs sin tablas.
- [ ] **T-287 (US-BE-061)** — **Migración + modelo** append-only: `sm_fixture_id`, `observed_at`, flags o columnas para **lineups** y familias **FT_1X2**, **OU_GOALS_2_5**, **BTTS** (**D-06-068** §3–§5); índices `(sm_fixture_id, observed_at)`; nombre no productivo.
- [ ] **T-281 (US-BE-061)** — Job/cron que, para cada fixture del universo **D-06-068** §1, dispare polls SM según **cadencia D-06-068** §2 y persista en **T-287** las señales **§3** con flags según **§4–§5**; **sin** DSR productivo ni fallback no-SM.
- [ ] **T-282 (US-BE-061)** — Evidencia en [`EJECUCION.md`](./EJECUCION.md) § US-BE-061: **T-287**, queries EOD, día + conteo fixtures; TZ y cadencia **D-06-068**; nota hacia **US-BE-058**.

* * *

## US-BE-062

- [ ] **T-283 (US-BE-062)** — Mapeo SM ↔ SofaScore según **D-06-068** §6 (liga + kickoff + nombres normalizados; `needs_review` si ambigüedad; no bloquear corrida); persistir en tabla auxiliar **T-283**; marcar `benchmark` / no productivo.
- [ ] **T-288 (US-BE-062)** — **Migración + modelo** append-only solo SofaScore: mismas dimensiones que **T-287** para **D-06-068** §3–§5; `JOIN`/`UNION ALL` con **T-287** por `sm_fixture_id` y `observed_at`. Sin filas SM aquí.
- [ ] **T-284 (US-BE-062)** — Sobre el universo **D-06-068** §1 (fixtures con mapeo no bloqueante; omitir o `needs_review` según **T-283**), ejecutar SofaScore con **misma cadencia D-06-068** §2 e **insertar** observaciones en **T-288**; no re-pollar SM (**T-287**). Referencia código: `processors/lineups_processor.py`, `core/scraped_odds_anchor.py`, `processors/odds_all_processor.py`, `processors/odds_feature_processor.py`.
- [ ] **T-285 (US-BE-062)** — Informe leyendo **T-287** + **T-288** + **T-283**, criterios **D-06-068** §4–§6; export + resumen en `EJECUCION.md`.
- [ ] **T-286 (US-BE-062)** — **Gate de no-productivo:** checklist en PR y en `EJECUCION.md`: **no** feature flag de fallback; **no** consumo SofaScore en rutas CDM/BT2 productivas; **no** sustitución de verdad SM; tablas benchmark **no** referenciadas por pipeline productivo; referencia **D-06-066**. Código compartido solo en módulos aislados benchmark.

* * *

## Cierre sprint

- [ ] **T-278 (transversal)** — Completar [`EJECUCION.md`](./EJECUCION.md) con evidencia de cierre F3 dentro de S6.4 (métricas, corridas, enlaces a PRs).
- [ ] **T-279 (transversal)** — Revisar `HANDOFF_BE_EJECUCION_S6_4.md` vs implementación real; marcar desviaciones y deuda explícita **solo** si cae dentro de F3.

* * *

## Check cierre Sprint 06.4

- [ ] Política **US-BE-058** aprobada y enlazada normativamente.
- [ ] Al menos un flujo **CDM sin DSR** y uno **DSR autorizado** evidenciados (**T-274**).
- [ ] Runbook **US-OPS-003** enlazado y checklist post-deploy ejecutado una vez.
- [ ] Ninguna tarea cerrada mezcla objetivos **F4/F5** ni reabre **F2/S6.3** sin decisión explícita fuera de este sprint.
- [ ] Si se cierran **US-BE-061 / US-BE-062**: evidencia en `EJECUCION.md` (tablas + queries), **T-286** verificado (sin fallback SofaScore productivo), **T-287 / T-288** mergeadas.

* * *

*2026-04-15 — TASKS S6.4; T-276–T-277 eliminadas; vía única 061/062 (**D-06-065**).*
