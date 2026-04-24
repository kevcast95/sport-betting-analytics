# Sprint 06.5 — Validate SFS — TASKS

> Definición madre: [`cursor_prompt_s6_5_validate_sfs.md`](./cursor_prompt_s6_5_validate_sfs.md).  
> US: [`US.md`](./US.md) · Decisiones: [`DECISIONES.md`](./DECISIONES.md) · Plan: [`PLAN.md`](./PLAN.md).  
> Numeración: **T-267** … **T-302** (continúa tras **T-266** S6.3).  
> **Sin tareas FE.**

**Orden sugerido:** US-OPS-003 (runbook + env) → US-DX-005 → US-BE-058 → US-BE-062 → US-BE-059 → US-BE-060 → US-BE-063 → US-BE-061 → US-BE-064 → US-BE-065.

* * *

## DoR (Definition of Ready)

- [ ] Prompt maestro leído por TL y PO.  
- [ ] **D-06-062 … D-06-073** aceptadas para el corte de implementación.  
- [ ] Postgres **staging** y URL distintas de prod verificadas (checklist US-OPS-003).  
- [ ] `EJECUCION.md` § kickoff revisado y fechado para la primera `anchor_date_utc`.

* * *

## Reframing y estructura

- [x] **T-267** — Releer solo prompt + `ROADMAP_PO_NORTE_Y_FASES.md` §F3; anotar en `EJECUCION.md` enlace a acta sin reabrir cierres S6.3.  
- [x] **T-268** — Crear árbol `apps/api/bt2/providers/sofascore/` (`__init__.py`, README interno de límites y no-objetivos).

* * *

## US-OPS-003

- [x] **T-269 (US-OPS-003)** — Runbook: caps, `kill_switch`, accountable PO / responsible TL, checklist apagado, control job daily hasta `00:00 UTC` día siguiente.  
- [x] **T-270 (US-OPS-003)** — Definir env vars (`BT2_SFS_EXPERIMENT_ENABLED`, `BT2_SFS_EXPERIMENT_MAX_EVENTS_PER_RUN`, `BT2_SFS_HTTP_MAX_RPS`, etc.) y valores alineados a `EJECUCION.md`.  
- [x] **T-271 (US-OPS-003)** — Drill de apagado documentado en `EJECUCION.md` con fecha.

* * *

## US-DX-005

- [x] **T-272 (US-DX-005)** — Documento DX canónico v0 + alias por proveedor y `source_scope`; incluir definición **evento útil** idéntica a **D-06-066**.  
- [x] **T-273 (US-DX-005)** — Implementar módulo Python de mapeo (p. ej. `bt2/providers/sofascore/canonical_map.py`) + tests fixtures `featured`/`all` separados.

* * *

## US-BE-058

- [x] **T-274 (US-BE-058)** — Migración `bt2_provider_odds_snapshot` con unique `(bt2_event_id, provider, source_scope, run_id)` + timestamps.  
- [x] **T-275 (US-BE-058)** — Repositorio/servicio de escritura idempotente + test de re-run.  
- [x] **T-276 (US-BE-058)** — Nota de retención sprint+30d (job delete o ticket follow-up) enlazada en runbook.

* * *

## US-BE-062

- [x] **T-277 (US-BE-062)** — Implementar resolución capa 1 (IDs/metadata/seed V1 opcional vía flag).  
- [x] **T-278 (US-BE-062)** — Implementar capa 2 determinista (competición + equipos + kickoff UTC).  
- [x] **T-279 (US-BE-062)** — Tabla overrides manuales + seed mínimo de ejemplo o vacío documentado.  
- [x] **T-280 (US-BE-062)** — Export join: por evento, capa ganadora, `no_comparable` razonado.

* * *

## US-BE-059

- [x] **T-281 (US-BE-059)** — Cliente HTTP SFS con throttling **T-270** y timeouts.  
- [x] **T-282 (US-BE-059)** — Fetcher `featured` → persist raw con `source_scope=featured`.  
- [x] **T-283 (US-BE-059)** — Fetcher `all` → persist raw con `source_scope=all`.  
- [x] **T-284 (US-BE-059)** — Wire a `bt2_provider_odds_snapshot` + logs con `run_id`.

* * *

## US-BE-060

- [x] **T-285 (US-BE-060)** — CLI historical: `--anchor-date`, `--run-id`, `--seed-json` opcional; manifest en `out/s65_historical_manifest_{run_id}.json`.  
- [x] **T-286 (US-BE-060)** — Selección cohorte SM por día UTC cerrado desde Postgres staging.  
- [x] **T-287 (US-BE-060)** — Corrida histórica completa 6d + artefacto CSV/JSON en repo bajo `out/` o `docs/bettracker2/recon_results/` + enlace `EJECUCION.md`.

* * *

## US-BE-063

- [x] **T-288 (US-BE-063)** — Implementar cálculo `match_rate` y `no_comparable_rate` según **D-06-067**/**D-06-068**.  
- [x] **T-289 (US-BE-063)** — KPI principal: % eventos **útiles** (D-06-066) por proveedor sobre **eventos comparables** (definición en `EJECUCION.md` § fórmulas).  
- [x] **T-290 (US-BE-063)** — Secundarios: solo SM / solo SFS / ambos / ninguno + breakdown join.  
- [x] **T-291 (US-BE-063)** — Comparación pp SM vs SFS para umbral `GO`/`NO-GO` + `metrics.json` versionado.

* * *

## US-BE-061

- [x] **T-292 (US-BE-061)** — Job daily staging: cohorte día actual, mismo pipeline, corte documentado.  
- [x] **T-293 (US-BE-061)** — Entrada `EJECUCION.md` sección Daily con `run_id` y métricas.

* * *

## US-BE-064

- [x] **T-294 (US-BE-064)** — Migración `bt2_dsr_ds_input_shadow` + columnas metadata mínimas **D-06-070**.  
- [x] **T-295 (US-BE-064)** — Writer shadow desde canónico + 1 fixture E2E.  
- [x] **T-296 (US-BE-064)** — Mini cohorte 20 eventos + query de verificación en `EJECUCION.md`.

* * *

## US-BE-065

- [x] **T-297 (US-BE-065)** — Consolidar números finales y aplicar reglas **D-06-068** → etiqueta **GO|PIVOT|NO-GO**.  
- [x] **T-298 (US-BE-065)** — Párrafo salida F3 (**D-06-071**).  
- [x] **T-299 (US-BE-065)** — Insertar frase seam The Odds API (**D-06-072**).  
- [x] **T-300 (US-BE-065)** — Decisión explícita “¿1 semana más operable?” con referencia a coste observado **T-271**.

* * *

## Cierre técnico sprint

- [x] **T-301** — `pytest` / tests tocados en verde + revisión TL.  
- [x] **T-302** — Lista de archivos tocados en PR + enlace a este `TASKS.md` casillas marcadas.

* * *

*Documento derivado exclusivamente del prompt maestro del sprint.*
