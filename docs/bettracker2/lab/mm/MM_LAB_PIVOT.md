# BT2 MM Lab Pivot

Fecha: 2026-05-11
Rama: `phase3g/monitor-resultados-shadow-mode`

## Proposito

Esta rama queda como punto de pivote de laboratorio para el frente MM
(Multi-Market). No se considera una rama lista para merge directo a `main`.
Su valor es preservar la evidencia, los scripts reutilizables y las decisiones
metodologicas de MM-0, MM-1 y MM-2 sin arrastrar outputs crudos, prompts
manuales, logs, checkpoints ni runners exploratorios redundantes.

## Decision de cierre

- No continuar MM-3 sobre esta rama.
- No promover la rama completa a `main`.
- Mantener esta rama como lab consultable si hace falta recuperar contexto.
- Iniciar MM-3 desde una rama nueva basada en `main`.
- Tratar enriched SportMonks como contexto descriptivo, no como senal decisional.
- Tratar DSR y bake-offs de modelos como evidencia negativa: no hubo edge robusto.

## Estado metodologico

### MM-0: TOA totals y preservacion de lineas

Se audito el soporte de mercados multi-market y se identifico que OU2.5 requiere
preservar el valor de `point`/line para no mezclar totales incompatibles. La
correccion conceptual que si debe sobrevivir fuera del laboratorio es:

- mantener line/point en contracts, normalizacion y rows de mercado;
- corregir el sport key de Ligue 1 a `soccer_france_ligue_one`;
- validar que los backfills no colapsen mercados por selection sin line.

Scripts retenidos:

- `scripts/mm0_3_line_preservation_scaffold_audit.py`
- `scripts/mm2_8c2_fixture_universe_toa_match_audit.py`
- `scripts/mm2_8c4_toa_sport_key_repair_incremental_backfill.py`

### MM-1: prompt harness, normalizer y confiabilidad de schema

MM-1 construyo el harness two-stage y mostro que la salida del modelo necesitaba
normalizacion deterministica y validacion estricta. El aprendizaje estable es que
el pipeline debe separar:

- construccion del market board;
- rendering del prompt;
- parseo del modelo;
- normalizacion final;
- validacion por contrato antes de evaluar performance.

Scripts retenidos:

- `scripts/mm1_4_final_output_normalizer.py`
- `scripts/bt2_blind_scrubbed_replay.py`
- `scripts/bt2_blind_scrubbed_ab_market_context.py`

### MM-2: enriched context, gates y leakage control

MM-2 agrego contexto enriquecido, scanners y guardrails. La conclusion fue que el
contexto enriquecido puede servir como descripcion, auditoria y trazabilidad, pero
no debe usarse como senal decisional hasta demostrar valor temporal fuera de
muestra. Se conservaron los scripts que encapsulan timestamp gating, reparacion de
schema, analisis de falla y diseno de gates.

Scripts retenidos:

- `scripts/mm2_4_timestamp_gated_enriched_context_adapter.py`
- `scripts/mm2_6r1_stage1_schema_reliability_repair.py`
- `scripts/mm2_6r2_enriched_signal_failure_analysis.py`
- `scripts/mm2_7_enriched_directional_signal_gate_design.py`

### MM-2.8C: backtest baseline y bake-offs

El backtest DSR baseline 2025 cubrio 75 eventos con 47 picks settled. El resultado
fue ROI negativo y peor que benchmark. OU2.5 fue toxico en los slices revisados.
Los bake-offs Opus/GPT con prompts screenshot/minimal no produjeron edge robusto.

Conclusion:

- DSR no debe promoverse como policy de picks.
- FT_1X2 benchmark/policy parece mas prometedor que OU2.5 para el siguiente ciclo.
- La siguiente etapa debe ser Data Science / ML feasibility, no mas prompt tuning.

Scripts retenidos:

- `scripts/mm2_8c_baseline_multimarket_backtest_rebuild.py`
- `scripts/mm2_8c5_baseline_dsr_backtest_on_repaired_market_board.py`
- `scripts/mm2_8c6_baseline_backtest_postmortem.py`
- `scripts/mm2_8c7_evaluate_model_bakeoff_outputs.py`
- `scripts/mm2_x_consolidated_findings_and_integration_map.py`

### Shadow monitoring pre-MM

La rama tambien conserva parte de la superficie de shadow monitoring original:
modelos, schemas, router, migraciones, UI y adaptadores nativos. No se poda
automaticamente en este cierre porque es codigo runtime ya trackeado de la rama y
podria necesitar revision especifica antes de descartarlo.

Scripts retenidos:

- `scripts/bt2_phase4a_shadow_signal_diagnosis.py`
- `scripts/bt2_shadow_dsr_fair_comparison.py`
- `scripts/bt2_shadow_evaluate_performance.py`
- `scripts/bt2_shadow_source_path_audit.py`
- `scripts/bt2_live_field_audit.py`

## Que se elimino de la rama

La poda elimina artefactos que hacian dificil usar la rama como pivote:

- outputs crudos bajo `scripts/outputs/`;
- prompts renderizados y paquetes manuales bajo `prompts/`;
- logs, checkpoints y bundles de bake-off;
- docs dispersos de auditoria/decision/diseno que quedan condensados aqui;
- runners exploratorios redundantes o con side effects potenciales;
- stubs API selectivos no trackeados y no integrados.

La lista exacta queda registrada en:

- `docs/bettracker2/lab/mm/MM_LAB_CLEANUP_INVENTORY.csv`
- `docs/bettracker2/lab/mm/MM_LAB_DELETE_LIST.txt`

## Reglas para usar este lab despues

- No ejecutar scripts que llamen APIs externas sin revisar flags, costos y secrets.
- No ejecutar backfills ni writes contra DB desde esta rama sin una rama limpia y
  plan nuevo.
- No usar los outputs borrados como fuente canonica; las conclusiones canonicas
  estan condensadas en este documento.
- Si se necesita recuperar evidencia cruda, usar el historial de git o el backup
  local `mm-lab-backup/phase3g-monitor-resultados-shadow-mode-20260510`.

## Recomendacion MM-3

Crear MM-3 desde `main` como:

`phase4/mm3-data-science-feasibility`

Objetivo MM-3:

- auditar cobertura y calidad de datos de las 120 ligas;
- construir dataset sin leakage;
- entrenar modelos simples primero;
- validar temporalmente contra benchmark;
- simular ROI/policy con reglas conservadoras.

Fases sugeridas:

- MM-3.0 data coverage audit;
- MM-3.1 feature dataset;
- MM-3.2 baseline ML models;
- MM-3.3 temporal validation;
- MM-3.4 ROI/policy simulation.

## Respuesta corta de cierre

Que debe ir a `main` ahora: solo fixes pequenos y reutilizables, en especial
Ligue 1 `soccer_france_ligue_one`, preservacion de line/point OU2.5, contracts o
validadores deterministas que no dependan de outputs experimentales.

Que queda como laboratorio: DSR shadow, enriched context, bake-offs, backtests
negativos, scanners exploratorios y scripts retenidos en esta rama.

Que no debe mergearse: outputs crudos, raw payloads, prompts manuales, logs,
checkpoints, runners con side effects y la rama completa.

La rama actual debe mergearse completa: no.
