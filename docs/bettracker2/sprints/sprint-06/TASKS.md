# Sprint 06 — TASKS

> Numeración global: continúa desde **T-153** (Sprint 05 termina en **T-152** en [`../sprint-05/TASKS.md`](../sprint-05/TASKS.md)).  
> **Parlays / diagnóstico avanzado / D-04-001:** **Sprint 07** — no listar aquí salvo spike explícito.

## Reglas

- Cada tarea referencia **US-FE-###**, **US-BE-###**, **US-DX-###** o **US-OPS-###**.
- Orden sugerido: **US-DX-002** (contratos) en paralelo con **US-BE-027** (mercados) y **US-BE-025** (DSR); **US-BE-026** + **US-OPS-001**; **US-BE-028** antes de **US-FE-053**.

---

## Contratos — US-DX-002

- [ ] **T-153** (US-DX-002) — **Catálogo mercados canónicos:** definir enum/tabla `MarketCanonical`, mapeo desde strings Sportmonks, documentar en **DECISIONES D-06-003/D-06-006**; actualizar `bt2_dx_constants.py` + `bt2Types.ts`.

- [x] **T-154** (US-DX-002) — **Contrato DSR I/O:** schemas Pydantic (`bt2_dsr_contract.py`); anti-fuga **D-06-002** en validador `assert_no_forbidden_ds_keys`; `pipeline_version` en snapshot. *(Tipos TS / OpenAPI exhaustivo: pendiente con FE.)*

- [ ] **T-155** (US-DX-002) — **operatorProfile + OpenAPI:** valores cerrados, `label_es`, alias camelCase; revisar `reason` ledger vs OpenAPI (**sin duplicar** definiciones contradictorias con **US-DX-001**).

- [x] **T-156** (US-DX-002) — **contractVersion:** bump **`bt2-dx-001-s6.0`** en `GET /bt2/meta`; handoff [`BE_HANDOFF_SPRINT06.md`](./BE_HANDOFF_SPRINT06.md).

---

## Backend — US-BE-025 (DSR + CDM)

- [x] **T-157** (US-BE-025) — **Pipeline DSR día D (hito contrato):** implementación **`rules_fallback`** sobre candidatos CDM al generar snapshot; hash input + persistencia; tests anti-fuga. **No** sustituye el objetivo de producto: **DSR con DeepSeek en vivo** = **T-169** (equivalente funcional v1 dentro de BT2).

- [x] **T-158** (US-BE-025) — **Wire a snapshot/bóveda:** `GET /bt2/vault/picks` expone narrativa DSR + canónicos modelo (`dsrNarrativeEs`, `modelMarketCanonical`, …).

- [x] **T-169** (US-BE-025) — **DSR DeepSeek en vivo (integración base):** HTTP + persistencia en snapshot. **`BT2_DSR_PROVIDER=deepseek`**, **`dsr_source=dsr_api`** cuando corresponde — **D-06-018**. *No sustituye la réplica del criterio v1 por **lotes**; eso es **T-170** (**D-06-019**).*

- [x] **T-170** (US-BE-025) — **DSR por lotes v1-equivalentes (**D-06-019**):** `deepseek_suggest_batch` + `ds_input` / `picks_by_event`; router parte en chunks `BT2_DSR_BATCH_SIZE` (default 15). Degradación por lote o por evento documentada en [`BE_HANDOFF_SPRINT06.md`](./BE_HANDOFF_SPRINT06.md). Tests: `apps/api/bt2_sprint06_test.py` (`TestDsrDeepseekBatchMock`).

---

## Backend — US-BE-026 + OPS — US-OPS-001

- [x] **T-159** (US-BE-026) — **Job programado `fetch_upcoming`:** `scripts/bt2_cdm/job_fetch_upcoming.py`; exit codes 0/1/2; `download_ok` en resultado.

- [x] **T-160** (US-OPS-001) — **Runbook:** [`../../runbooks/bt2_fetch_upcoming_cron.md`](../../runbooks/bt2_fetch_upcoming_cron.md); enlazar desde **D-06-005** / **PLAN** §5.

---

## Backend — US-BE-027 (mercados canónicos)

- [x] **T-161** (US-BE-027) — **Migración + ACL:** columnas `market_canonical` / modelo en `bt2_picks`; DSR en `bt2_daily_picks`; backfill SQL en migración.

- [x] **T-162** (US-BE-027) — **Settle + vault:** settle persiste `model_prediction_result` (hit/miss/void/n_a); vault + `PickOut` exponen canónicos + `marketCanonicalLabelEs`.

---

## Backend — US-BE-028 (analytics MVP)

- [x] **T-163** (US-BE-028) — **Endpoint(s) analytics MVP:** `GET /bt2/admin/analytics/dsr-day` + header `X-BT2-Admin-Key` / `BT2_ADMIN_API_KEY`.

- [x] **T-164** (US-BE-028) — **`*_human_es`:** `summaryHumanEs` en respuesta admin (copy operativo).

---

## Frontend — US-FE-052 … 054

- [x] **T-165** (US-FE-052) — **Bóveda narrativa DSR:** componentes y copy; loading/error; sin datos proveedor crudos.

- [x] **T-166** (US-FE-053) — **Vista admin Precisión DSR / auditoría (MVP):** referencia visual [`refs/us_fe_055_admin_dsr_accuracy.html`](./refs/us_fe_055_admin_dsr_accuracy.html); wire a **T-163**; KPIs **N**, hit, miss, void, tasa de acierto y tabla de auditoría por día operativo; estados vacío/error; Zurich Calm. **Alcance FE estricto:** solo **(1)** añadir el **ítem de navegación** en el sidebar que enlace a la nueva ruta y **(2)** implementar el **contenido de esa página** (maquetar el bloque equivalente al `<main>` del mock dentro del shell existente). **Prohibido** en esta tarea: modificar `BunkerLayout`, cabeceras globales, estructura del sidebar salvo registrar el nuevo link, top bar adicional, FAB, u otras rutas/pantallas. El mock incluye sidebar/topbar/búsqueda/notificaciones de ejemplo: **no replicarlos** — el producto ya tiene layout; tomar solo título, selector de día, tarjetas KPI, tabla y pie de página informativo si aplica. **D-06-010:** no implementar export **CSV** en S6 (omitir u ocultar el botón del mock).

- [x] **T-167** (US-FE-054) — **Labels mercado canónico:** mapa desde API; settlement + ledger + card.

- [x] **T-168** (US-FE-052–054) — **`npm test` + smoke** manual S6. *Automatizado: `npm test` + `npm run build` en `apps/web` sin regresiones. Smoke manual: guía [`EJECUCION_COMPLETA_PUNTA_A_PUNTA.md`](./EJECUCION_COMPLETA_PUNTA_A_PUNTA.md) §5 (no sustituye este checklist).*

---

## Check cierre Sprint 06 (sugerido)

- [x] **D-06-018** (**T-169**) + **D-06-019** (**T-170**) implementados en BE; **D-06-002 … D-06-017** coherentes salvo enmienda PO.
- [ ] **US-DX-002** — **T-153** / **T-155** pendientes: coordinación PO — **arrastradas a Sprint 07** (ver [`../sprint-07/PLAN.md`](../sprint-07/PLAN.md)); cierre FE masivo sigue gobernado por `contractVersion`.
- [ ] Runbook **US-OPS-001** válido en staging/prod según entorno; canal/on-call real si ya asignado (**D-06-011**).
- [x] Deuda DX explícita referenciada en **`sprint-07/PLAN.md`**.
