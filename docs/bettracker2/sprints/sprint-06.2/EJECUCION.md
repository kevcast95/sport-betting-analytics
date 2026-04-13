# Sprint 06.2 — EJECUCION (Backend / DX)

> Registro de avance **BE** alineado al handoff §5. Última actualización: **2026-04-09**.  
> **Cierre del sprint:** [`CIERRE_S6_2.md`](./CIERRE_S6_2.md) · **S6.3:** [`../sprint-06.3/PLAN.md`](../sprint-06.3/PLAN.md).

## Fase 1 — P0 cubo A + whitelist (T-195–T-204)

| Área | Detalle |
|------|---------|
| **T-195** | [`docs/bettracker2/dx/bt2_ds_input_v1_parity_fase1.md`](../../dx/bt2_ds_input_v1_parity_fase1.md) — `from_sm_fixture`, lineups, `raw_fixture_missing`, `team_season_stats_reason`. |
| **T-196** | Validador Pydantic + bump `contractVersion` (ver fase 2 para **s6.2r2**). |
| **T-197–T-200** | Includes SM, UPSERT `raw`, mapa `type_id`, refs JSON en `refs/`. |
| **T-201–T-204** | Mapper statistics, lineups, diagnostics, tests builder. |

## Fase 2 — P1 US-BE-044 / D-06-032–033 (T-208, T-209–T-211)

| Área | Detalle |
|------|---------|
| **T-208** | Cubo B: `team_season_stats` sigue `available: false`; `diagnostics.team_season_stats_reason` + mensaje en `fetch_errors` (**D-06-038**). Sin tabla agregada. |
| **T-209** | Universo valor **≤ 20** antes de `compose_vault_daily_picks` (`VAULT_VALUE_POOL_UNIVERSE_MAX`, recorte en `_generate_daily_picks_snapshot`). Slate persistido **5** (`VAULT_POOL_TARGET` / `VAULT_POOL_HARD_CAP` = 5). Campo API **`valuePoolUniverseMax`** en `Bt2VaultPicksPageOut`. |
| **T-210** | Franjas locales alineadas **D-06-032** en `bt2_vault_pool.py` y `vaultTimeBand.ts`: mañana [06:00,12:00), tarde [12:00,18:00), noche [18:00,24:00), overnight [00:00,06:00). |
| **T-211** | Script cron [`job_vault_snapshot_materialize.py`](../../../../scripts/bt2_cdm/job_vault_snapshot_materialize.py) — materializa snapshot idempotente por usuario (complementa `session/open`, **D-06-033**). |

**Contrato:** `CONTRACT_VERSION_PUBLIC` = **`bt2-dx-001-s6.2r2`** (vault 20/5/5 + campo `valuePoolUniverseMax`).

**Tests:** `python3 -m unittest apps.api.bt2_vault_pool_test`; `npx vitest run src/lib/vaultTimeBand.test.ts src/store/useVaultStore.test.ts`.

## Diferido

| Tareas | Motivo |
|--------|--------|
| **T-205–T-207** | Cubo C historial cuotas (**D-06-039**). |
| **T-212–T-216** | FSM Regenerar, admin audit/refresh, pool global (**US-BE-045**–**048**). |
| **T-223+** | Regresión §1.3–1.5 / acta prompt **D-06-035**. |

## OpenAPI

`apps/web/openapi.json` no incluye `/bt2/*`; contrato **`contractVersion`** y shapes vault en FastAPI (`Bt2MetaOut`, `Bt2VaultPicksPageOut`).

## Nota FE (resumen)

Ver sección final del mensaje de entrega de la fase 2 en el chat / handoff: `contractVersion`, `valuePoolUniverseMax`, franjas, textos Vault, fallbacks store.

**2026-04-09 — T-217–T-219, T-226, T-225 (web):** `PickCard` + `SettlementPage` alineados a §1.11 (Vektor, orden partido→cuota→Vektor→confianza); disclaimer **D-06-041 §2** (`VektorShortDisclaimer`) en `VaultPage` y settlement; glosario **D-06-036** en `GlossaryModal`; `vaultModelReading` / `bt2ProtocolLabels` (confianza sin “simbólica”, `dsrSourceDescriptionAdminEs` en admin); ruta **`/v2/admin/cdm-audit`** con regeneración vía `POST /bt2/admin/vault/regenerate-daily-snapshot` y aviso explícito hasta **T-214**. Verificación: `npm test -- --run` y `npm run build` en `apps/web` (OK). `pytest` BT2 no ejecutado en esta pasada (sin cambios en `apps/api` en el diff FE).

**Índice de archivos FE/BE del mismo día (cierre):** [`CIERRE_S6_2.md`](./CIERRE_S6_2.md) sección **§6** (incluye `bt2_dsr_ds_input_sm_fixture_blocks`, `bt2_dev_sm_refresh`, admin DSR accuracy, vault store/franjas, etc.).
