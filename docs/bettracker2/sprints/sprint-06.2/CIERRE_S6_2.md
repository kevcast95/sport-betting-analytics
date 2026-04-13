# Sprint 06.2 — Acta de cierre

**Fecha de cierre:** 2026-04-09  
**Estado:** **cerrado** (alcance ejecutado acordado; ítems no completados quedan **traspasados explícitamente** a Sprint 06.3).

**Evidencia técnica detallada:** [`EJECUCION.md`](./EJECUCION.md) (fases 1–2, contrato, tests).  
**Handoff original:** [`HANDOFF_EJECUCION_S6_2.md`](./HANDOFF_EJECUCION_S6_2.md).  
**Siguiente sprint:** [`../sprint-06.3/PLAN.md`](../sprint-06.3/PLAN.md).

---

## 1. Intención del sprint (recordatorio)

Cerrar la brecha **BT2 frente a v1** en **insumo** (CDM / SportMonks / `ds_input`), **operabilidad** del snapshot bóveda (**D-06-032** / **D-06-033**), **superficie** (Vektor **§1.11**, glosario **D-06-036**, disclaimer **D-06-041**), y bases de **admin** (analytics DSR, distribución vault, regeneración de snapshot bajo clave admin), sin confundir “éxito de usuario” con “calidad del modelo” en métricas que aún dependen del flujo de picks — tema ya acotado para **S6.3** (véase §4).

---

## 2. Lo que quedó hecho (resumen ejecutivo)

| Área | Entrega |
|------|---------|
| **DX / contrato** | Paridad fase 1 documentada en `docs/bettracker2/dx/bt2_ds_input_v1_parity_fase1.md`; validador + whitelist; **`contractVersion`** pública alineada a **`bt2-dx-001-s6.2r2`** (vault 20/5/5 + `valuePoolUniverseMax` en API). |
| **Ingesta cubo A (SM)** | Includes ampliados, **UPSERT** / refresh de `raw_sportmonks_fixtures`, mapa `type_id`, JSON de referencia en `refs/`. |
| **Builder `ds_input`** | Mapper `statistics`, lineups cuando hay datos, diagnostics (`raw_fixture_missing`, etc.), tests asociados. |
| **Cubo B** | `team_season_stats` honesto: `available: false` + causa en diagnostics (**D-06-038** / **T-208**). |
| **Snapshot bóveda** | Universo **≤ 20**, tomables/slate **5**, franjas locales **06–12 / 12–18 / 18–24 / 00–06** en BE y `vaultTimeBand.ts` (**D-06-032**); job de materialización de snapshot (`job_vault_snapshot_materialize.py`); integración con disparadores de sesión según **D-06-033**. |
| **FE bóveda / settlement** | **PickCard** y settlement alineados a **§1.11**; disclaimer **D-06-041** en lista y detalle; glosario Vektor en `GlossaryModal`; lectura modelo / etiquetas protocolo (`vaultModelReading`, `bt2ProtocolLabels`). |
| **Admin API** | `GET /bt2/admin/analytics/dsr-day`, `dsr-range`, `vault-pick-distribution`; `POST /bt2/admin/vault/regenerate-daily-snapshot` (clave **X-BT2-Admin-Key**). |
| **QA transversal** | **T-225** referenciado en handoff: `pytest` módulos BT2 tocados + `npm test` / `npm run build` en `apps/web` según entregas. |

Detalle por tarea numerada: ver casillas **[x]** en [`TASKS.md`](./TASKS.md) y tablas en [`EJECUCION.md`](./EJECUCION.md).

---

## 3. Lo que no se completó en S6.2 (traspaso a S6.3)

Queda **fuera del cierre ejecutado** y se aborda en **S6.3** (refinamiento, feedback y definición fina), salvo nueva decisión de alcance:

| Bloque | Referencia |
|--------|------------|
| **Cubo C** — historial temporal de cuotas (**US-BE-042**, **T-205–T-207**, **D-06-039**) | Schema + job + builder por rangos acotados. |
| **FSM Regenerar** producto/backend completa (**US-BE-045**, **T-212–T-213**, **D-06-034** acta opción reset) | Documentación de máquina de estados + regla única de reset; hoy puede coexistir con regeneración admin y/o shuffle en cliente según lo desplegado. |
| **Pool global + vista por usuario** (**US-BE-048**, **T-216**, **§3.E** inventario) | Refactor tras snapshot estable. |
| **Gobernanza** | **T-220** runbooks operativos; **T-224** acta **D-06-035** (fecha + responsable PO/BA si aún pendiente); **T-221** opcional auditoría TASKS 06.1 vs código. |
| **Regresión documentada** | **T-223** — regresión explícita §1.3–§1.5 / orquestación con snapshot **US-BE-044**. |
| **Vista admin “precisión DSR” vs premisa de producto** | Hoy los KPI hit/miss del admin se basan en **`bt2_picks` liquidados** con `model_prediction_result` (liquidación vs modelo), no en “todas las sugerencias del día vs resultado oficial”. **S6.3** debe acotar US: monitoreo del **modelo** sobre filas de bóveda / evento + fuente de verdad de resultado (p. ej. SM), gráficos opcionales. |

---

## 4. Nota sobre `TASKS.md`

El archivo [`TASKS.md`](./TASKS.md) conserva checklists **históricos de planificación**. Si alguna casilla **[ ]** no coincide con el código actual (p. ej. endpoints admin ya existentes), prima esta **acta de cierre** + el **repositorio**. Actualizar casillas sueltas es trabajo de higiene opcional en S6.3 (**D-06-031** sigue vigente: TASKS 06.1 = histórico; verdad = consolidado + código + actas).

---

## 5. Decisión vinculada

**D-06-042** en [`DECISIONES.md`](./DECISIONES.md) — cierre formal S6.2 y encaje de S6.3.

---

## 6. Archivos de código y documentación tocados (entrega 2026-04-09)

Inventario tomado del árbol de trabajo al cerrar (commit de cierre). Sirve de índice para revisión y para **S6.3**.

### Backend (`apps/api`)

- `bt2_dsr_contract.py` — whitelist / contrato DSR.
- `bt2_dsr_deepseek.py` — prompt batch (bloques SM enriquecidos).
- `bt2_dsr_ds_input_builder.py` — builder `ds_input`.
- `bt2_dsr_ds_input_builder_s62_test.py` — tests builder S6.2.
- `bt2_dsr_ds_input_sm_fixture_blocks.py` — bloques opcionales SM en `ds_input` (**nuevo**).
- `bt2_dsr_suggest.py` — orquestación sugerencias.
- `bt2_dx_constants.py` — constantes DX / versión de contrato expuesta.
- `bt2_router.py` — rutas BT2 (admin analytics, vault, dev/reset, etc.).
- `bt2_schemas.py` — esquemas Pydantic.
- `bt2_sportmonks_includes.py` — includes SportMonks.
- `bt2_vault_pool.py` — pool / snapshot bóveda.
- `bt2_dev_sm_refresh.py` — utilidades refresh fixture SM en dev (**nuevo**).

### Frontend (`apps/web`)

- `src/components/GlossaryModal.tsx`
- `src/components/profile/DpLedgerSection.tsx`
- `src/components/vault/PickCard.tsx`
- `src/components/vault/VaultDevTools.tsx`
- `src/components/vault/VektorShortDisclaimer.tsx`
- `src/layouts/BunkerLayout.tsx`
- `src/lib/api.ts`
- `src/lib/bt2Types.ts`
- `src/lib/bt2VaultConstants.ts`
- `src/lib/dpLedgerLabels.ts`
- `src/lib/vaultModelReading.ts` · `vaultModelReading.test.ts`
- `src/lib/vaultTimeBand.ts` · `vaultTimeBand.test.ts`
- `src/pages/AdminDsrAccuracyPage.tsx` · `AdminDsrAccuracyPage.test.tsx`
- `src/pages/SettlementPage.tsx`
- `src/pages/VaultPage.tsx`
- `src/store/useSessionStore.ts` · `useSessionStore.test.ts`
- `src/store/useVaultStore.ts` · `useVaultStore.test.ts`

### Documentación y raíz

- `docs/bettracker2/sprints/sprint-06.2/` — acta **CIERRE_S6_2**, **DECISIONES** (**D-06-042**), **EJECUCION**, **PLAN**, **TASKS**, **HANDOFF**, **INVENTARIO**.
- `docs/bettracker2/sprints/sprint-06.3/PLAN.md` — arranque S6.3.
- `docs/bettracker2/notas/CONVERSACION_MERCADOS_VARIEDAD_DSR.md` — nota de mercados / DSR.
- `.env.example` (raíz) — variables documentadas alineadas a dev/SM.
