# Sprint 06 — TASKS

> Numeración global: continúa desde **T-153** (Sprint 05 termina en **T-152** en [`../sprint-05/TASKS.md`](../sprint-05/TASKS.md)).  
> **Parlays / diagnóstico avanzado / D-04-001:** **Sprint 07** — no listar aquí salvo spike explícito.

## Reglas

- Cada tarea referencia **US-FE-###**, **US-BE-###**, **US-DX-###** o **US-OPS-###**.
- Orden sugerido: **US-DX-002** (contratos) en paralelo con **US-BE-027** (mercados) y **US-BE-025** (DSR); **US-BE-026** + **US-OPS-001**; **US-BE-028** antes de **US-FE-053**.

---

## Contratos — US-DX-002

- [ ] **T-153** (US-DX-002) — **Catálogo mercados canónicos:** definir enum/tabla `MarketCanonical`, mapeo desde strings Sportmonks, documentar en **DECISIONES D-06-003/D-06-006**; actualizar `bt2_dx_constants.py` + `bt2Types.ts`.

- [ ] **T-154** (US-DX-002) — **Contrato DSR I/O:** schemas Pydantic (input diario producción, output persistido); prohibiciones **D-06-002** reflejadas en validadores o checklist CI; `pipeline_version` acordado.

- [ ] **T-155** (US-DX-002) — **operatorProfile + OpenAPI:** valores cerrados, `label_es`, alias camelCase; revisar `reason` ledger vs OpenAPI (**sin duplicar** definiciones contradictorias con **US-DX-001**).

- [ ] **T-156** (US-DX-002) — **contractVersion:** bump en `GET /bt2/meta` y nota en handoff FE.

---

## Backend — US-BE-025 (DSR + CDM)

- [ ] **T-157** (US-BE-025) — **Pipeline DSR día D:** integrar reasoner con salida de `build_candidates` (o flujo sustituto); persistir resultado estructurado + versión; tests con fixtures **sin** datos fugados.

- [ ] **T-158** (US-BE-025) — **Wire a snapshot/bóveda:** publicar picks del día con campos que consuma **US-FE-052** (vía `bt2_daily_picks` / endpoint vault — definir en US al implementar).

---

## Backend — US-BE-026 + OPS — US-OPS-001

- [ ] **T-159** (US-BE-026) — **Job programado `fetch_upcoming`:** empaquetar script existente; exit codes; logging; idempotencia conservada.

- [ ] **T-160** (US-OPS-001) — **Runbook:** documentar schedule, env vars, alertas, troubleshooting; enlace desde **D-06-005** y [`PLAN.md`](./PLAN.md).

---

## Backend — US-BE-027 (mercados canónicos)

- [ ] **T-161** (US-BE-027) — **Migración + ACL:** columna o tabla canónica; mapeo en ingesta/snapshot; backfill controlado.

- [ ] **T-162** (US-BE-027) — **Settle + vault:** `_determine_outcome` / rutas settle consumen canónico; `GET /bt2/vault/picks` expone canónico + label; regresión curl.

---

## Backend — US-BE-028 (analytics MVP)

- [ ] **T-163** (US-BE-028) — **Endpoint(s) analytics MVP:** implementar agregados acordados en **D-06-004**; auth usuario; tests.

- [ ] **T-164** (US-BE-028) — **`*_human_es`:** copy métricas según [`../../00_IDENTIDAD_PROYECTO.md`](../../00_IDENTIDAD_PROYECTO.md) §B donde aplique.

---

## Frontend — US-FE-052 … 054

- [ ] **T-165** (US-FE-052) — **Bóveda narrativa DSR:** componentes y copy; loading/error; sin datos proveedor crudos.

- [ ] **T-166** (US-FE-053) — **Vista analytics MVP:** wire a **T-163**; estados vacío; Zurich Calm.

- [ ] **T-167** (US-FE-054) — **Labels mercado canónico:** mapa desde API; settlement + ledger + card.

- [ ] **T-168** (US-FE-052–054) — **`npm test` + smoke** manual S6.

---

## Check cierre Sprint 06 (sugerido)

- [ ] **D-06-002 … D-06-006** ratificadas o enmendadas con PO.
- [ ] **US-DX-002** cerrada antes de merge masivo FE dependiente.
- [ ] Runbook **US-OPS-001** válido en staging/prod según entorno.
- [ ] Deuda explícita movida a **Sprint 07** en `sprint-07/PLAN.md` cuando exista.
