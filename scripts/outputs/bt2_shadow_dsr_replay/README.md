# BT2 — replay shadow con DSR (`shadow_dsr_replay`)

Directorio de artefactos para validar el **motor predictivo real (DSR API)** sobre el mismo universo que el baseline shadow **no-DSR**, sin mezclar interpretaciones de ROI.

## Artefactos

| Archivo | Descripción |
|---------|-------------|
| `dsr_selection_source_contract.md` | Contrato `dsr_api_only`, exclusiones y estados de fallo. |
| `dsr_pilot_sample.csv` | Muestra estratificada (liga × mes) generada desde Postgres. |
| `dsr_pilot_summary.json` | Resumen de la última ejecución del preparador. |
| `dsr_pilot_run_details.json` | Solo si se ejecutó con `--run-dsr` (detalle por evento). |
| `dsr_pilot_summary_after_fix.json` | Rerun con muestra fija + parser reforzado + modelo forzado. |
| `dsr_pilot_run_details_after_fix.json` | Detalle por evento del rerun `after_fix`. |
| `dsr_parser_autopsy.md` | Autopsia de causa raíz y patrones por `response_id`. |
| `dsr_output_contract_v2.md` | Contrato de salida v2 para `deepseek-v4-pro` (JSON canónico mínimo). |
| `dsr_pilot_summary_contract_v2.json` | Métricas del rerun con contrato v2 (misma muestra fija). |
| `dsr_pilot_run_details_contract_v2.json` | Detalle por evento del rerun `contract_v2`. |
| `dsr_output_contract_v3.md` | Contrato minimalista v3 (5 campos, salida robusta). |
| `dsr_pilot_summary_contract_v3.json` | Métricas del rerun con contrato v3 sobre la misma muestra fija. |
| `dsr_pilot_run_details_contract_v3.json` | Detalle por evento del rerun `contract_v3`. |
| `dsr_batching_experiment.md` | Experimento de batching (`v2` batch 15 vs `v3` batch 1). |
| `dsr_empty_signal_autopsy.md` | Clasificación de `dsr_empty_signal` (v3) y dictamen por patrón. |
| `dsr_pilot_summary_contract_v4.json` | Rerun v4 (misma muestra, foco en reducir `dsr_empty_signal`). |
| `dsr_pilot_run_details_contract_v4.json` | Detalle por evento v4 con campos raw para autopsia. |
| `dsr_empty_signal_diff.csv` | Diff evento a evento de los 22 `dsr_empty_signal` v3 contra v4. |
| `dsr_abstention_policy_v5.md` | Política explícita de abstención legítima vs excesiva. |
| `dsr_pilot_summary_contract_v5.json` | Rerun v5 final (misma muestra, foco en abstención excesiva). |
| `dsr_pilot_run_details_contract_v5.json` | Detalle por evento v5. |
| `dsr_abstention_diff.csv` | Diff evento a evento v4 vs v5 (estado y abstención). |
| `dsr_prompt_v6_spec.md` | Prompt shadow-native **v6** (analista + JSON estricto); código en `bt2_dsr_shadow_native_prompt_v6.py`. |
| `dsr_prompt_v6_sample_summary.json` | Prueba controlada muestra 32 — métricas parse / sesgo favorito (generado por script v6). |
| `dsr_prompt_v6_sample_details.json` | Detalle por evento (rationale, `prob_coherence`, estado parse). |
| `dsr_prompt_v6_favorite_bias_check.csv` | Tier cuota vs consensus + si el pick coincide con el favorito implícito. |
| `ds_input_shadow_native_current_audit.md` | Auditoría de bloques `processed.*` / `diagnostics` (muestra 32) legacy vs enriquecido. |
| `ds_input_shadow_native_vs_original_gap.md` | Brecha builder original vs carril native + qué corrige el enrichment. |
| `ds_input_shadow_native_enrichment_design.md` | Diseño de `apply_shadow_native_enriched_context` y fuentes. |
| `ds_input_shadow_native_enriched_sample.json` | Muestra enriquecida (32) con resumen y excerpts `blind`. |
| `dsr_full_replay_summary.json` | Replay completo sobre universo DSR-ready (sin fallback). |
| `dsr_full_replay_by_run.csv` | Métricas operativas/predictivas del run completo. |
| `dsr_full_replay_by_league.csv` | Desglose predictivo por liga del run completo. |
| `dsr_full_vs_non_dsr_eligible_slice.csv` | Comparación justa vs no-DSR en el mismo slice elegible. |
| `pending_settlement_policy.md` | Política operativa de cierre y pending/recheck/manual en shadow DSR. |
| `dsr_ready_gap_278_to_41.csv` | Radiografía fila a fila del gap universo shadow → DSR-ready. |
| `dsr_ready_gap_summary.json` | Resumen por causa (conteo y porcentaje) del gap 278→41. |
| `dsr_pick_visibility_contract.md` | Contrato de visibilidad por pick DSR en UI/admin shadow. |
| `dsr_contract_diff.md` | Diff métrico `after_fix` vs `contract_v2`. |
| `previous_vs_current_dsr_radiography.md` | Radiografía comparativa flujo previo vs `shadow_dsr_replay`. |
| `previous_vs_current_dsr_waterfall.csv` | Embudo/waterfall lado a lado de volumen y pérdidas. |
| `previous_vs_current_dsr_sample_diff.csv` | Diff por fixture (muestra fija) entre selección previa y estado actual. |
| `shadow_native_dsr_ready_contract.md` | Definición operativa de **DSR-ready shadow-native** (SM + TOA T-60, sin depender de CDM local). |
| `shadow_native_dsr_input_adapter.md` | Adapter `shadow → dsr_input` (fuentes TOA / opcional contexto CDM). |
| `shadow_native_dsr_ready_gap_comparison.csv` | Fila a fila: embudo **legacy** vs **shadow-native** (mismo universo 278). |
| `shadow_native_pilot_summary.json` | Conteos globales + muestra fija 32 + sonda opcional `--call-deepseek`. |
| `dsr_pending_audit.csv` | Auditoría de `pending_result` + columnas local vs SportMonks (instantánea pre-reconciliación). |
| `dsr_pending_summary.json` | Conteos y causas; puede incluir bloque `after_shadow_evaluate_performance` tras recheck. |
| `dsr_settlement_strategy.md` | Política de cierre aterrizada a los casos reales de la auditoría. |
| `dsr_sportmonks_historical_reliability_check.csv` | Muestra control hit+miss: acuerdo `bt2_events` vs SM refrescada. |
| `dsr_vs_non_dsr_fair_comparison.csv` | DSR native liquidado vs baseline no-DSR (mismo slice, misma lógica de eval). |
| `dsr_vs_non_dsr_fair_summary.json` | Métricas + delta + `by_league_compare`; reglas de comparación explícitas. |
| `dsr_vs_non_dsr_fair_by_league.csv` | Hit rate y ROI % por liga (DSR vs no-DSR). |
| `dsr_native_re_read_by_league.csv` | Solo DSR: KPI por `league_name`. |
| `dsr_native_re_read_by_run.csv` | Solo DSR: KPI por `source_run_key` (subset5 / backfills). |
| `dsr_native_re_read_by_selection_side.csv` | Solo DSR: KPI por lado canónico. |
| `dsr_native_re_read_by_odds_band.csv` | Solo DSR: KPI por banda de cuota decimal. |
| `dsr_native_re_read_by_month.csv` | Solo DSR: KPI por mes (`YYYY-MM` desde `operating_day_key`). |
| `dsr_v6_request_probe_requests.json` | Sonda caja negra: request HTTP real (system + user + `batch_json_exact`) por caso, generado por `scripts/bt2_shadow_dsr_prompt_v6_request_probe.py`. |
| `dsr_v6_request_probe_responses.json` | Respuesta cruda + parseo + `final_pick_fields` por caso (misma sonda). |
| `dsr_v6_request_probe_summary.json` | Resumen mínimo (`parse_status`, chequeo de que el user prompt incluye el batch JSON). |
| `dsr_vs_always_favorite_summary.json` | DSR vs benchmark trivial «always favorite» + baseline no-DSR (misma verdad). |
| `dsr_vs_always_favorite_full_run.csv` | Comparación fila a fila run native completo vs favorito / baseline. |
| `dsr_vs_always_favorite_sample32.csv` | Misma comparación sobre muestra fija 32. |

### Sonda de request DSR shadow-native v6 (inspección, no replay masivo)

Para verificar que el endpoint recibe **system + user completo** (incl. schema, reglas y bloque `BATCH:` con `ds_input` embebido) y el `request_body_final` idéntico al cliente `deepseek_suggest_batch_shadow_native_v6_with_trace`:

```bash
# Solo artefactos + stdout (sin HTTP)
PYTHONPATH=. python3 scripts/bt2_shadow_dsr_prompt_v6_request_probe.py --dry-run --all

# Un caso por `source_shadow_pick_id` (= `event_id` en ds_input blind)
PYTHONPATH=. python3 scripts/bt2_shadow_dsr_prompt_v6_request_probe.py --source-shadow-pick-id 149

# Lista corta o todos con llamada real a DeepSeek (requiere `deepseek_api_key` en settings)
PYTHONPATH=. python3 scripts/bt2_shadow_dsr_prompt_v6_request_probe.py --pick-ids 149,157
PYTHONPATH=. python3 scripts/bt2_shadow_dsr_prompt_v6_request_probe.py --all
```

Entrada por defecto: `dsr_native_full_replay_v6_sample_audit.json` (`ds_input_blind` por caso).

### Benchmark «always favorite» vs DSR (misma verdad, sin replay)

Script: `scripts/bt2_shadow_dsr_vs_always_favorite.py`. Construye la selección trivial FT_1X2 = pierna de **menor decimal** en `consensus` TOA agregado igual que shadow-native; empates en el mínimo → desempate fijo **home → draw → away**. Evalúa DSR, baseline no-DSR y benchmark con `EvalRow` + `_evaluate_one` y la misma fusión de marcador (CDM + SportMonks).

| Archivo | Descripción |
|---------|-------------|
| `dsr_vs_always_favorite_summary.json` | Métricas agregadas (run completo + muestra 32), alineación DSR vs favorito, deltas hit-rate / ROI%. |
| `dsr_vs_always_favorite_full_run.csv` | Fila a fila 259 picks (`shadow-dsr-native-full-20260429-033425`). |
| `dsr_vs_always_favorite_sample32.csv` | Subconjunto `dsr_pilot_sample.csv`. |

```bash
PYTHONPATH=. python3 scripts/bt2_shadow_dsr_vs_always_favorite.py
```

## Comparación justa DSR vs no-DSR (baseline liquidado)

Tras cerrar pending con `bt2_shadow_evaluate_performance.py`, regenerar la comparación sobre los mismos `source_shadow_pick_id`:

```bash
PYTHONPATH=. python3 scripts/bt2_shadow_dsr_fair_comparison.py
```

- **DSR:** lectura desde `bt2_shadow_pick_eval` del run native.
- **No-DSR:** recomputo con `EvalRow` / `_evaluate_one` / `_fetch_sm_truth_map` (mismo código que el evaluador shadow).

## Auditoría de pending DSR native (sin replay)

Solo DB local y carril shadow. El script consulta SportMonks (mismo patrón que el evaluador de performance).

```bash
PYTHONPATH=. python3 scripts/bt2_shadow_dsr_native_pending_audit.py
```

Reconciliación mínima (solo tablas shadow, reescribe `bt2_shadow_pick_eval`):

```bash
PYTHONPATH=. python3 scripts/bt2_shadow_evaluate_performance.py --run-key <run_key_del_baseline_native>
```

## Puerta shadow-native (experimento DSR)

Embudo alineado al stack auditado (cuotas desde snapshot TOA persistido, no `bt2_odds_snapshot`). Genera los artefactos anteriores:

```bash
PYTHONPATH=. python3 scripts/bt2_shadow_native_dsr_pilot.py
PYTHONPATH=. python3 scripts/bt2_shadow_native_dsr_pilot.py --call-deepseek   # un lote DSR sobre la muestra de 32 (coste API)
```

Implementación: `apps/api/bt2_dsr_shadow_native_adapter.py`.

### Replay completo shadow-native (`shadow_dsr_replay_native`)

Universo: solo filas **DSR-ready shadow-native** (sin gating `bt2_odds_snapshot` legacy). Nuevo run en DB cada ejecución (`run_key` con timestamp).

```bash
PYTHONPATH=. python3 scripts/bt2_shadow_dsr_full_replay_native.py
```

| Artefacto | Contenido |
|-----------|-----------|
| `dsr_native_full_replay_summary.json` | Conteos universo / elegibles / ejecutados, métricas DSR, baseline no-DSR mismo slice, tokens |
| `dsr_native_full_replay_by_run.csv` | Una fila por run native |
| `dsr_native_full_replay_by_league.csv` | KPIs por liga |
| `dsr_native_vs_non_dsr_same_slice.csv` | DSR native vs picks fuente shadow (no DSR) sobre los mismos `source_shadow_pick_id` |
| `dsr_native_full_replay_v6_summary.json` | Igual + **`operational_snapshot`** (parse_status, tiers cuota, sesgo favorito) y **`observability`**; prompt **v6** + enrichment |
| `dsr_native_full_replay_v6_by_run.csv` / `_by_league.csv` | Copias homónimas del run para archivo separado v6 |
| `dsr_native_full_replay_v6_sample_audit.json` | **10 eventos** estratificados: `ds_input_blind` completo, respuesta **cruda** del modelo (string JSON), fila `picks_by_event` tal cual API, flags `processed.*`, eval |
| `dsr_native_full_replay_v6_sample_audit.csv` | Vista tabular (rationale truncado; JSON grande solo en `.json`) |

**Batching:** `bt2_dsr_batch_size` (típ. 15) — lotes por límites prácticos de tokens/timeout DeepSeek.

## Comandos

Desde la raíz del repo (`PYTHONPATH=.`):

```bash
# Solo CSV + summary (sin coste API)
python3 scripts/bt2_shadow_dsr_replay_prepare.py --sample-size 32 --seed 42

# Piloto técnico con llamadas DeepSeek reales
python3 scripts/bt2_shadow_dsr_replay_prepare.py --run-dsr --sample-size 32

# Rerun controlado sobre la MISMA muestra fija y modelo explícito actual
python3 scripts/bt2_shadow_dsr_replay_prepare.py \
  --run-dsr \
  --sample-size 32 \
  --model deepseek-v4-pro \
  --fixed-sample-csv scripts/outputs/bt2_shadow_dsr_replay/dsr_pilot_sample.csv \
  --output-tag after_fix

# Microiteración v3: contrato minimal + microbatch 1x1
python3 scripts/bt2_shadow_dsr_replay_prepare.py \
  --run-dsr \
  --sample-size 32 \
  --model deepseek-v4-pro \
  --fixed-sample-csv scripts/outputs/bt2_shadow_dsr_replay/dsr_pilot_sample.csv \
  --dsr-batch-size 1 \
  --output-tag contract_v3

# Microiteración v4: autopsia/reducción de empty_signal (misma muestra)
python3 scripts/bt2_shadow_dsr_replay_prepare.py \
  --run-dsr \
  --sample-size 32 \
  --model deepseek-v4-pro \
  --fixed-sample-csv scripts/outputs/bt2_shadow_dsr_replay/dsr_pilot_sample.csv \
  --dsr-batch-size 1 \
  --output-tag contract_v4

# Microiteración v5: política final de abstención (misma muestra)
python3 scripts/bt2_shadow_dsr_replay_prepare.py \
  --run-dsr \
  --sample-size 32 \
  --model deepseek-v4-pro \
  --fixed-sample-csv scripts/outputs/bt2_shadow_dsr_replay/dsr_pilot_sample.csv \
  --dsr-batch-size 1 \
  --output-tag contract_v5

# Prompt v6 shadow-native (analista + JSON estricto; misma muestra 32; sin INSERT masivo)
python3 scripts/bt2_shadow_dsr_prompt_v6_controlled.py

# Auditoría + JSON de `ds_input` enriquecido shadow-native (misma muestra 32)
python3 scripts/bt2_shadow_native_ds_input_audit.py

# Replay completo del universo DSR-ready en carril separado (shadow_dsr_replay)
python3 scripts/bt2_shadow_dsr_full_replay.py

# Radiografía del gap universo shadow -> DSR-ready (sin backtest)
python3 scripts/bt2_shadow_dsr_gap_radiography.py
```

Requisitos `--run-dsr`: `deepseek_api_key` en settings / `.env`, misma configuración que BT2 DSR.

## Resultado del rerun `contract_v2` (2026-04-28)

- Muestra fija conservada: 32/32 (`dsr_pilot_sample.csv`).
- Modelo: `deepseek-v4-pro` (sin fallback de selección).
- Métricas clave:
  - `prompts_built_ok`: 32
  - `dsr_failed`: 30
  - `dsr_empty_signal`: 0
  - `parseable_canonical`: 2
  - `evaluable_ft_1x2_after_postprocess`: 2
  - `ok`: 2

Lectura: el contrato estricto ya produjo picks canónicos reales, pero la parseabilidad batch sigue siendo el cuello de botella dominante.

## Resultado del rerun `contract_v3` (2026-04-28)

- Muestra fija conservada: 32/32 (`dsr_pilot_sample.csv`).
- Modelo: `deepseek-v4-pro` (sin fallback de selección).
- Batching: `--dsr-batch-size 1`.
- Métricas clave:
  - `prompts_built_ok`: 32
  - `dsr_failed`: 6
  - `dsr_empty_signal`: 22
  - `parseable_canonical`: 4
  - `evaluable_ft_1x2_after_postprocess`: 4
  - `ok`: 4

Lectura: mejora fuerte de robustez de parseo (`dsr_failed`), pero todavía baja conversión a picks útiles por volumen alto de `UNKNOWN`.

## Resultado del rerun `contract_v4` (2026-04-28)

- Muestra fija conservada: 32/32.
- Modelo: `deepseek-v4-pro`.
- Batching: `--dsr-batch-size 1`.
- Métricas clave:
  - `dsr_failed`: 2
  - `dsr_empty_signal`: 20
  - `ok`: 10
  - `evaluable_ft_1x2_after_postprocess`: 10

Lectura: el cuello `empty_signal` baja de 22 a 20 y suben picks utilizables; el patrón dominante restante es abstención explícita del modelo.

## Resultado del rerun `contract_v5` (2026-04-28)

- Muestra fija conservada: 32/32.
- Modelo: `deepseek-v4-pro`.
- Batching: `--dsr-batch-size 1` (sin cambios adicionales).
- Métricas clave:
  - `dsr_failed`: 3
  - `dsr_empty_signal`: 0
  - `ok`: 29
  - `evaluable_ft_1x2_after_postprocess`: 29
  - `truth_available`: 14
  - `truth_hit_preliminary`: 7
  - `truth_miss_preliminary`: 7

Lectura: la política de abstención v5 elimina la abstención excesiva en esta muestra y deja el picker en nivel operativo usable para shadow.

## Migración DB

Aplicar en entorno BT2 (no productivo):

```bash
cd apps/api && alembic upgrade head
```

Revisión: `s1t2u3v4w5x6_bt2_shadow_dsr_replay_lane`.

## Próximo paso

Tras revisar métricas del piloto (`prompts`, parseables, `FT_1X2` evaluables, tokens/coste, hit/miss preliminar), definir job de persistencia masiva con `run_key` dedicado y sin tocar runs del baseline no-DSR.
