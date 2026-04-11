# Sprint 06.1 — Ejecución y evidencia de cierre

> **Uso:** rellenar durante el sprint. **Check cierre:** [`TASKS.md`](./TASKS.md) § *Check cierre Sprint 06.1*.  
> **Escenarios obligatorios:** **US-BE-036** (tres casos) + **D-06-022** / **D-06-026** §6.

## Estado

| Campo | Valor |
|--------|--------|
| Cierre Sprint 06.1 | **2026-04-10** — sprint declarado cerrado en [`PLAN.md`](./PLAN.md); backlog incremento en [`../sprint-06.2/PLAN.md`](../sprint-06.2/PLAN.md). |
| Rama / PR principal | *Consolidación en rama de trabajo del equipo* |
| Última actualización | 2026-04-10 |

## Escenarios US-BE-036 (evidencia)

Para cada fila: método de prueba (test automatizado, manual, fixture) y enlace a PR o commit.

| # | Escenario | Resultado | Evidencia (PR, test, nota) |
|---|-----------|-----------|----------------------------|
| 1 | Post-DSR produce picks DSR → persisten con fuente/lineage coherente | ☑ OK | `postprocess_dsr_pick` + snapshot inserta `dsr_source=dsr_api` tras `postprocess_dsr_pick` (`bt2_dsr_postprocess_test.py`, `bt2_router._generate_daily_picks_snapshot`). |
| 2 | DSR vacío + CDM con candidatos SQL válidos → fallback + mensaje/disclaimer + lineage | ☑ OK | Si no hay ningún pick DSR post-procesado válido → `global_sql_fallback` + `suggest_sql_stat_fallback_from_consensus` (`dsr_source=sql_stat_fallback`), metadata `dsr_signal_degraded` + `fallback_disclaimer_es` expuesto en `GET /bt2/vault/picks`. |
| 3 | Vacío duro (**D-06-026** §6: **0** filas pool elegible) → **cero** picks, API/mensaje operativo claro | ☑ OK | `build_value_pool_for_snapshot` vacío → sin INSERT daily_picks, `_upsert_vault_day_metadata` con `operational_empty_hard=true` y mensaje; vault devuelve `operationalEmptyHard` + `vaultOperationalMessageEs`. |

## Post-DSR (T-181–T-182)

- Casos borde: **sí** — `apps/api/bt2_dsr_postprocess_test.py` (omisión sin cobertura, cap confianza si odds modelo > 15); desvío ±15% registra log en `postprocess_dsr_pick` (cuota persistida anclada al input vía reconciliación en pick canónico).

## Contrato / FE

- **T-173:** `contractVersion` default `bt2-dx-001-s6.1r1` en `Bt2MetaOut` (refinement **T-189–T-193**); `Bt2VaultPicksPageOut` + `Bt2VaultPickOut.dataCompletenessScore`; `apps/web/src/lib/bt2Types.ts` alineado.
- **T-183:** `GET /bt2/admin/analytics/vault-pick-distribution?operatingDayKey=YYYY-MM-DD` + tipos `Bt2AdminVaultPickDistributionOut` en OpenAPI / `bt2Types.ts`.

## Notas

*(Decisiones tomadas en implementación que no cambian DECISIONES — si cambian contrato, actualizar **DECISIONES.md** antes de merge, **D-06-023**.)*

---

## REFINEMENT_S6_1

> **Criterio:** [`REFINEMENT_S6_1.md`](./REFINEMENT_S6_1.md); **decisiones:** **D-06-027** … **D-06-030**; **tareas:** **T-189–T-194**.

### Evidencia (rellenar al cerrar refinement)

| Tarea | Qué probar | Resultado | Evidencia (PR, test, nota) |
|-------|------------|-----------|----------------------------|
| **T-189** | Builder pobla histórico cuando hay datos en Postgres | ☑ OK | `apply_postgres_context_to_ds_item` + `bt2_dsr_context_queries.py`; `unittest` `bt2_dsr_context_queries_test`, `bt2_sprint06_test.test_ds_input_accepts_s6_1r1_context_blocks`. |
| **T-190** | Cuotas históricas / serie o documento de gap + plan DX | ☑ OK | `odds_featured.ingest_meta` (ventana en `bt2_odds_snapshot`); **gap:** serie temporal por mercado/selección no está en schema — ver `docs/bettracker2/dx/bt2_ds_input_v1_parity_fase1.md` §3.4.1. |
| **T-191** | Prompt alineado **D-06-030**; tests verdes | ☑ OK | `_SYSTEM_BATCH` / `_user_prompt_batch` en `apps/api/bt2_dsr_deepseek.py` (D-06-027 / D-06-030). |
| **T-192** | Post-DSR omite pick con **selection** vs **razon** contradictorios | ☑ OK | `narrative_contradicts_ft_1x2` + log `reason=incoherent_razon`; `apps/api/bt2_dsr_postprocess_test.py`. |
| **T-194** | Copy FE coherente con **D-06-027** | ☑ OK | Bóveda (`VaultPage`, `BunkerLayout`, `SanctuaryPage`, tour `tourScripts`), `PickCard` (tooltip edge), `vaultModelReading` (`RULES_FALLBACK…`), admin `AdminDsrAccuracyPage` (leyenda), `GlossaryModal` (+EV / Edge / CDM / cuota sugerida). `npm test` + `npm run build` en `apps/web`. |
| **T-193** | Handoff tablas ↔ bloques; pytest módulos tocados | ☑ OK | `HANDOFF_EJECUCION_S6_1.md` § tabla `processed`; `unittest` módulos `bt2_dsr_*` tocados. |

### Notas de merge / PO

- Texto final de prompt aprobado (PR o fecha): **Pendiente validación PO/BA** sobre redacción en `apps/api/bt2_dsr_deepseek.py` (`_SYSTEM_BATCH`, `_user_prompt_batch`) — criterio **D-06-030**.
- Excepciones a **D-06-028** (si algún bloque sigue vacío por falta de tabla): **`team_season_stats`** permanece `{available: false}` hasta tabla agregada temporada; mensaje en `diagnostics.fetch_errors`. Serie completa de cuotas históricas: no hay camino en CDM salvo `ingest_meta`; ampliación vía **US-DX-003** si se define almacenamiento.

---

*Plantilla: 2026-04-09 — S6.1 apto ejecución. Actualizado: **REFINEMENT_S6_1**.*
