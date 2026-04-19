# BT2 — Evaluación oficial ampliada + capa de coherencia (spec para ejecución)

**Audiencia:** agente / desarrollador que implemente en el repo `scrapper`.  
**Estado:** especificación de trabajo (no historial de sprint cerrado).

---

## Estado de implementación (última revisión)

| Área | Estado |
|------|--------|
| **§1.2 / Objetivo A** — Settlement BTTS, doble oportunidad, O/U goles por línea canónica | **Hecho** (`bt2_official_truth_resolver.py`, `bt2_market_canonical.py`, tests) |
| **§3.1** — Criterios de aceptación evaluación oficial | **Cumplidos en tests** |
| **§1.3 / Objetivo B** — Coherencia probabilística MVP | **En `ds_input`:** `diagnostics.prob_coherence` (contrato `DsProbCoherenceDiagnostics`) + prompt DSR actualizado |
| **§3.2** — Job recálculo post-deploy | Operativo manual (no automatizado en repo) |

---

## 1. Contexto y objetivos

### 1.1 Problema visible (producto)

- ~~El **monitor de resultados** y la tabla `bt2_pick_official_evaluation` marcan **N.E.** (*no evaluable*) para picks de mercados como **BTTS**, **doble oportunidad**, etc., **aunque el partido esté terminado y el marcador exista en `bt2_events`**.~~ → **Mitigado:** el resolver oficial acepta BTTS, DC y toda la familia **`OU_GOALS_*_*`** con reglas determinísticas.
- ~~La documentación interna del resolver declara **mercados v1 = solo `FT_1X2` y `OU_GOALS_2_5`**.~~ → **Actualizado:** soporte ampliado; mercados fuera de las familias soportadas siguen con `OUTSIDE_SUPPORTED_MARKET_V1` (código histórico; significa “fuera del conjunto soportado para evaluación con marcador CDM”).

### 1.2 Objetivo A (obligatorio en esta entrega)

**Extender la evaluación oficial** para que, con **solo** `result_home`, `result_away` y `event_status` del CDM (`bt2_events`), el sistema pueda resolver **hit / miss** (y los void ya definidos) para los mercados que la bóveda ya publica con códigos canónicos estables.

Mercados mínimos a cubrir en esta spec (alineados a `apps/api/bt2_market_canonical.py`):

| Mercado canónico | Selección canónica esperada | Regla de settlement (determinística) |
|------------------|-----------------------------|----------------------------------------|
| `BTTS` | `yes` / `no` | **yes**: `result_home > 0` y `result_away > 0`. **no**: en caso contrario. |
| `DOUBLE_CHANCE_1X` | `yes` | Cubre **local o empate** → gana si **no** gana solo el visitante: `result_home >= result_away`. |
| `DOUBLE_CHANCE_X2` | `yes` | Cubre **empate o visitante** → gana si **no** gana solo el local: `result_home <= result_away`. |
| `DOUBLE_CHANCE_12` | `yes` | Cubre **local o visitante** → gana si **no** hay empate: `result_home != result_away`. |

Además: **familia O/U goles** — cualquier `OU_GOALS_{int}_{frac}` (p. ej. `OU_GOALS_4_5`); la línea sale del código del mercado, no de una lista blanca fija.

**Notas:**

- Si en DB aparecen variantes (`YES`/`NO`, mayúsculas), normalizar en el mismo punto que ya se normaliza FT/O/U (selection lower-case).
- Partidos **void** del acta (cancelados / aplazados / abandonados según status ya contemplados) siguen igual.

### 1.3 Objetivo B — Coherencia probabilística (importante)

**Capa MVP** entre mercados del mismo fixture **sin** sustituir DSR:

- **Input:** `consensus` agregado (misma forma que `AggregatedOdds.consensus` tras `aggregate_odds_for_event` en `bt2_dsr_odds_aggregation.py`).
- **Output:** metadatos de calidad por evento; en **`ds_input`** van como `diagnostics.prob_coherence` (`flag`, métricas numéricas compactas, `notes`). Flags: `coherence_ok` \| `coherence_warning` \| `coherence_na` — no bloquean picks por defecto.

#### Implementación v0 (`apps/api/bt2_fixture_prob_coherence.py`)

| Pieza | Descripción |
|-------|-------------|
| Devig proporcional | Tres implícitas 1X2 → probabilidades que **suman 1** (`proportional_devig_three_way`). |
| Suma implícita cruda 1X2 | `ft_1x2_implied_sum_raw` (típicamente > 1); umbral configurable `max_raw_overround_1x2`. |
| Spread implícito | Reutiliza **`ft_1x2_book_spread_ratio`** (`bt2_dsr_odds_aggregation.py`), misma semántica que premium D-06-024. |
| O/U 2.5 | Si hay `over_2_5` y `under_2_5`, revisa overround del mercado (`ou_25_implied_sum_raw`). |
| **Envelope `ds_input`** | `build_ds_input_item` rellena `diagnostics.prob_coherence`; whitelist `DsProbCoherenceDiagnostics` (`bt2_dsr_contract.py`). |

#### Roadmap (siguientes incrementos — no obligatorio para cerrar spec A)

1. ~~**Ingesta en ds_input**~~ — **Hecho** (builder + contrato + instrucciones en prompt DSR).
2. **Persistencia opcional:** columna JSON `prob_coherence_json` en snapshot de evento o tabla auxiliar `bt2_fixture_prob_coherence` (event_id, run_id, flag, métricas).
3. ~~**Poisson cruzado (v1)**~~ — **Hecho:** Poisson **independiente** `(λ_home, λ_visitante)` ajustado al 1X2 deviguado; compara `over 2.5` y BTTS vs modelo → `cross_delta_*`, notas `cross_market_*`, flag si diverge (umbrales en código). Skellam explícito / Dixon–Coles **fuera** (siguiente iteración si hace falta).

Esta capa **no** duplica narrativa LLM; solo **validación numérica reproducible** en Python.

---

## 2. Estado del código relevante (auditar antes de codificar)

1. **`apps/api/bt2_official_truth_resolver.py`** — **Hecho** (BTTS, DC, O/U por línea).
2. **`apps/api/bt2_market_canonical.py`** — **Hecho** (`determine_settlement_outcome`, `canonical_to_settle_strings`, helpers OU genéricos).
3. **Decisión:** Opción 1 — ramas explícitas en `determine_settlement_outcome`.
4. **Job de evaluación:** `bt2_official_evaluation_job.py` — sin cambios necesarios salvo validación regresión.
5. **Tests:** `bt2_official_truth_resolver_test.py` ampliado.

---

## 3. Criterios de aceptación

### 3.1 Evaluación oficial ampliada

- [x] Pick `BTTS` + `yes` con marcador `2-2` → **hit** (no N.E.).
- [x] Pick `BTTS` + `yes` con `0-0` → **miss**.
- [x] Pick `DOUBLE_CHANCE_X2` + `yes` con `2-2` → **hit** (empate cubre X2).
- [x] Pick `DOUBLE_CHANCE_X2` + `yes` con `3-1` local → **miss**.
- [x] Estados void/cancelled sin cambiar comportamiento previo.
- [x] Mercados **aún no soportados** siguen en `no_evaluable` con código explícito (no silenciar).

### 3.2 Migración / datos existentes

- [ ] Tras deploy, ejecutar el job habitual de evaluación oficial (`run_evaluate_pending_rows` / script `scripts/bt2_cdm/job_official_pick_evaluation.py`) para **recalcular** filas que estaban `pending_result` o incorrectamente `no_evaluable` por soporte ausente. *(Operación de despliegue / ops.)*

### 3.3 Coherencia (Objetivo B)

- [x] Función pura testeada con fixtures de odds sintéticas (`bt2_fixture_prob_coherence_test.py`).
- [x] **No rompe contrato:** campo nuevo explícito en `DsDiagnosticsF1` (`prob_coherence`); `extra=forbid` intacto.
- [x] **Mejora `ds_input`:** cada ítem incluye `diagnostics.prob_coherence` cuando se construye con `build_ds_input_item` / `build_ds_input_item_from_db`; el system prompt DSR indica cómo usar `flag` / notas.
- [ ] Persistencia histórica en tabla/columna (opcional, producto).

---

## 4. Fuera de alcance (explícito)

- No cambiar contrato DSR ni prompts DeepSeek en esta entrega salvo decisión explícita posterior.
- No garantizar rentabilidad ni “edge”; solo **correctitud de settlement** y, en B, **checks de consistencia**.

---

## 5. Referencias rápidas de archivos

| Archivo | Rol |
|---------|-----|
| `apps/api/bt2_official_truth_resolver.py` | Resolver hit/miss oficial |
| `apps/api/bt2_market_canonical.py` | Settlement strings / helpers |
| `apps/api/bt2_official_evaluation_job.py` | Batch UPDATE evaluaciones |
| `apps/api/bt2_dsr_odds_aggregation.py` | Consensus + `ft_1x2_book_spread_ratio` |
| `apps/api/bt2_dsr_contract.py` | `DsProbCoherenceDiagnostics` bajo `diagnostics` |
| `apps/api/bt2_dsr_ds_input_builder.py` | Inyecta `prob_coherence` en cada ítem |
| `apps/api/bt2_dsr_deepseek.py` | Prompt interpreta `diagnostics.prob_coherence` |
| `apps/api/bt2_fixture_prob_coherence.py` | **Coherencia probabilística MVP (§1.3)** |
| `scripts/bt2_cdm/job_official_pick_evaluation.py` | Job CLI |
| Monitor UI | Consume `evaluation_status` ya mapeado a badges |

---

## 6. Checklist del agente ejecutor

1. [ ] Confirmar en BD desarrollo ejemplos reales de `model_market_canonical` / `model_selection_canonical` para BTTS y DC (mayúsculas/espacios).
2. [x] Implementar settlement + tests.
3. [x] Ejecutar `pytest` en módulos tocados + `compileall`.
4. [x] Documentar códigos `no_evaluable_reason` nuevos — **ninguno nuevo** (se reutiliza catálogo).
5. [x] Módulo coherencia `bt2_fixture_prob_coherence.py` + tests aislados.
6. [x] Integrar coherencia en `diagnostics` del `ds_input` (contrato + builder + prompt).
7. [ ] Persistir coherencia en BD *(opcional).*
