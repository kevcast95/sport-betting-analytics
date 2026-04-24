# Sprint 06.5 — Validate SFS — EJECUCION

> Definición madre: [`cursor_prompt_s6_5_validate_sfs.md`](./cursor_prompt_s6_5_validate_sfs.md).  
> **TASKS:** [`TASKS.md`](./TASKS.md) · **Decisiones:** [`DECISIONES.md`](./DECISIONES.md).

---

## 1) Kickoff — parámetros cerrados (no ambiguos)

| Campo | Valor cerrado |
|--------|----------------|
| **Ancla primera corrida (`anchor_date_utc`)** | **2026-04-17** (referencia inicial; corridas posteriores añaden filas con su propia ancla en §3–4). |
| **Ventana historical (6 días UTC cerrados)** | **2026-04-11** 00:00 UTC → **2026-04-16** 23:59:59.999 UTC (días completos D-6 … D-1 respecto a ancla). |
| **Ventana daily (día actual respecto ancla)** | **2026-04-17** 00:00 UTC → **2026-04-18** 00:00 UTC (corte job; no reintenta solo salvo runbook). |
| **Cohorte base** | Eventos **BT2** en **Postgres staging** modelados desde **SM/CDM**, misma ventana calendario que cada modo. |
| **Cap eventos por corrida (`max_events_per_run`)** | **500** eventos máx. procesados por ejecución daily o por día en histórico salvo **ampliación escrita PO** en este archivo. |
| **HTTP SFS** | Solo **`odds/1/featured`** y **`odds/1/all`** por evento con join válido → **2** requests máx. por evento y pasada completa. |
| **Throttle** | **4** req/s máx. agregado SFS (ajuste solo por TL con registro de fecha/motivo aquí). |
| **V1 SQLite** | **Opcional**, solo flag `--allow-v1-seed` para capa 1; path configurable por env `BT2_SFS_V1_SQLITE_PATH`; **nunca** destino de persistencia del experimento. |
| **Estrategia join** | **D-06-067** orden fijo: (1) IDs/metadata/seed, (2) competición+equipos+kickoff UTC, (3) overrides manuales. |
| **Accountable presupuesto** | **PO** |
| **Responsible técnico caps/throttle** | **TL** |

---

## 2) Definiciones normativas (copia operativa)

### 2.1 Evento útil ( = **D-06-066**)

> Evento **útil** ⇔ **`FT_1X2` completo** y **≥1** entre **`OU_GOALS_2_5`**, **`BTTS`**, **`DOUBLE_CHANCE`** completo (según reglas de completitud en doc DX / mapeo).

### 2.2 `% match` ( = **D-06-067**)

`match_rate = (# eventos BT2 de la cohorte ejecutada con join SFS válido) / (# total eventos BT2 en la cohorte ejecutada)`

- **Join válido:** `provider_event_ref` no nulo y capa documentada (1/2/3).  
- **No** incluye unión SM∪SFS ni universo global.

### 2.3 Bucket `no_comparable`

Evento en cohorte ejecutada pero **excluido** del denominador del **KPI principal comparado** (p. ej. sin datos SM o sin snapshot SFS pese a join, o reglas DX impiden comparar), según catálogo en `metrics.json` campo `reason`.

`no_comparable_rate = N_no_comparable / N_cohorte_ejecutada`

- Si **> 0.15** → **bloquea `GO`** (**D-06-068**).

### 2.4 Umbrales `match_rate`

| Rango | Lectura |
|--------|---------|
| **≥ 85%** | Comparación válida para `GO` (sujeto a resto). |
| **70%–84%** | Diagnóstico útil; **no `GO`**. |
| **< 70%** | Problema de **matching**; **no `GO`**. |

### 2.5 KPI principal (comparativo SM vs SFS)

**Denominador (`N_comparable`):** eventos con join SFS **válido** y con lectura SM **y** SFS disponibles en el `run_id` para las familias v0.

**Numerador por proveedor:** entre esos eventos, cuenta los que cumplen **evento útil** §2.1 usando solo datos de ese proveedor mapeados al canónico.

`kpi_principal_pct(provider) = 100 * (eventos_utiles(provider) / N_comparable)`

**Reglas `GO` sobre gap (D-06-068):**

- Si `kpi_principal_pct(SFS) < kpi_principal_pct(SM) - 10` → **`NO-GO`** (SFS materialmente peor).  
- Para `GO`: se exige además `kpi_principal_pct(SFS) >= kpi_principal_pct(SM) - 5` (no más de **5 pp** peor).

*(Secundarios: solo SM / solo SFS / ambos / ninguno; por liga si volumen; descartes join.)*

### 2.6 Raw `featured` vs `all`

Persistencia y KPIs: **siempre** etiquetados `source_scope`; **prohibido** mezclar en un solo número sin breakdown (**D-06-065**).

---

## 3) Registro — Historical bootstrap 6d

| `run_id` | Fecha ejecución (UTC) | Comando / job | Artefactos (paths) | Notas |
|----------|------------------------|---------------|---------------------|--------|
| | | | | |

---

## 4) Registro — Daily experimental path

| `run_id` | Inicio (UTC) | Corte (UTC) | Comando / job | Artefactos | Notas |
|----------|--------------|-------------|---------------|------------|--------|
| | | | | | |

---

## 5) Shadow `ds_input`

| Prueba | `run_id` / ids | Evidencia (query o path) | OK |
|--------|----------------|---------------------------|-----|
| 1 fixture E2E | | | [ ] |
| Cohorte 20 | | | [ ] |

---

## 6) Acta final — veredicto y salidas

**Veredicto (`GO` / `PIVOT` / `NO-GO`):** _pendiente hasta T-297_

**Números finales (pegar de `metrics.json`):**

- `match_rate`:  
- `no_comparable_rate`:  
- `kpi_principal_pct(SM)`:  
- `kpi_principal_pct(SFS)`:  

**¿1 semana experimental adicional operable?** _Sí / No — evidencia coste/cupos:_  

**Salida F3 (una):** _[ ] F3 simplifica · [ ] F3 pendiente nueva premisa · [ ] Backlog previo justificado_

**Frase seam The Odds API (**D-06-072**):**  
> El seam quedó listo a nivel de contrato, metadatos, persistencia y path de integración; falta adapter específico para The Odds API.

**Firmas:** PO ______________ fecha ______ | TL ______________ fecha ______

---

---

## 7) Evidencia implementación (T-301 / T-302) — sin reabrir §1–6

- **T-267:** Enlace programa §F3 (solo contexto, no reabre cierres S6.3): [`../sprint-06.3/ROADMAP_PO_NORTE_Y_FASES.md`](../sprint-06.3/ROADMAP_PO_NORTE_Y_FASES.md) — F3 queda para acta §6 tras corridas reales.
- **Migración:** `apps/api/alembic/versions/j4k5l6m7n8o9_bt2_s65_sfs_experiment_tables.py` → tablas `bt2_provider_odds_snapshot`, `bt2_sfs_event_override`, `bt2_sfs_join_audit`, `bt2_dsr_ds_input_shadow`; columna `bt2_events.sofascore_event_id`.
- **Modelos:** `apps/api/bt2_models.py` (clases ORM homónimas).
- **Provider BT2-SFS:** `apps/api/bt2/providers/sofascore/` (`client.py`, `canonical_map.py`, `join_resolve.py`, `snapshot_repo.py`, `http_headers.py`, `README.md`).
- **CLI:** `scripts/bt2_sfs/cli.py` (subcomandos `historical`, `daily`, `metrics`, `shadow`, `export-join`) + `_db.py`, `_sm_rows.py`, `_metrics_core.py`.
- **DX:** [`../../dx/bt2_odds_canonical_v0_s65.md`](../../dx/bt2_odds_canonical_v0_s65.md).
- **Runbook:** [`../../runbooks/bt2_sfs_experiment_s65.md`](../../runbooks/bt2_sfs_experiment_s65.md).
- **Settings:** `apps/api/bt2_settings.py` — `BT2_SFS_EXPERIMENT_*`, `BT2_SFS_HTTP_*`, `BT2_SFS_JOIN_SEED_JSON_PATH`, `BT2_SFS_V1_SQLITE_PATH` (opcional, no usado en pipeline por defecto).
- **Tests:** `apps/api/bt2_providers_sofascore_canonical_test.py`, `apps/api/bt2_providers_sofascore_snapshot_repo_test.py` — **4 passed** (`.venv/bin/python -m pytest …`).
- **T-287 artefactos:** tras `historical` / `daily`, manifest JSON bajo `out/s65_*_manifest_{run_id}.json`; enlazar en §3–4 al correr. `export-join` → CSV; `metrics` → `out/s65_metrics.json` (o ruta `--out-json`).
- **Corridas §3–4 / acta §6:** pendientes en **Postgres staging** con `alembic upgrade j4k5l6m7n8o9` + `BT2_SFS_EXPERIMENT_ENABLED=1` o `--force`; completar tablas §3–6 al ejecutar `historical`/`daily`/`metrics`/`shadow` y pegar `metrics.json` + firmas PO/TL.
- **T-271 (drill apagado):** checklist en runbook; marcar aquí fecha cuando se ejecute: _pendiente operador_.

---

*Documento derivado exclusivamente del prompt maestro del sprint.*
