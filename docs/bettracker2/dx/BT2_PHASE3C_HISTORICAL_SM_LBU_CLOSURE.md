# BT2 Fase 3C — Cierre formal (`historical_sm_lbu`)

Fecha de cierre: 2026-04-26  
Estado: **CERRADA**

## 1) Pregunta que resolvió Fase 3C

Determinar si existe una vía técnicamente defendible para reconstruir un flujo histórico exploratorio usando raw de SportMonks para 2025, sin depender de `bt2_odds_snapshot.fetched_at` backfilleado, y con contrato temporal explícito.

## 2) Qué NO resolvió Fase 3C

- No validó parity live.
- No reemplaza ni modifica el bounded replay actual.
- No es evidencia final para decisiones de Fase 4.
- No abrió ni ejecutó Fase 3D.
- No convierte esta cohorte en truth operativa productiva.

## 3) Contrato temporal congelado (no modificar)

- **T-60**: `latest_bookmaker_update <= kickoff_utc - 60 minutos`
- Fallback permitido en la definición ya aprobada: usar `created_at` cuando falte `latest_bookmaker_update`.
- Este contrato queda congelado para el modo histórico exploratorio de 3C.

## 4) Definición de modo y banderas de contrato

- `mode = historical_sm_lbu`
- `live_parity = false`
- `exploratory_only = true`

Interpretación contractual:
- Es un modo histórico reconstruido y explícitamente separado del bounded replay.
- No se mezclan métricas ni conclusiones con live parity.

## 5) Cohortes definidas en 3C

- Cohorte principal **A**: `2025-01..2025-05`
- Benchmark **B**: `2024-Q4`

Regla de no mezcla:
- A y B se comparan como cohortes separadas para lectura de estabilidad/robustez.
- No se fusionan en un agregado único para inferencias finales.

## 6) Hallazgo de outliers por liga (cohorte A completa)

Fuente:
- `scripts/outputs/bt2_historical_sm_lbu_cohort_A_league_outliers/league_outliers_A.csv`
- `scripts/outputs/bt2_historical_sm_lbu_cohort_A_league_outliers/summary.json`

Parámetro de ruido:
- Umbral mínimo aplicado: `n_fixtures >= 30` por liga.

Resultado de concentración:
- `top1_cumulative_share = 0.133672`
- `top3_cumulative_share = 0.216582`
- `top5_cumulative_share = 0.282572`
- `top10_cumulative_share = 0.414552`
- Etiqueta: `distribuida_mas_homogeneamente`

Lectura:
- Existen ligas outlier, pero la fragilidad de no usable en A no queda explicada por un puñado mínimo de ligas.
- La contribución está más repartida entre múltiples ligas (sin señal de colapso sistémico único).
- El patrón dominante de no usable se mantiene: `vp_false_dcs0_agregado_sin_consenso_util`.

## 7) Veredicto final de Fase 3C

Fase 3C queda formalmente cerrada con estos contratos y hallazgos:

1. El modo `historical_sm_lbu` es técnicamente viable para exploración histórica.
2. El contrato temporal T-60 queda congelado y documentado.
3. La cohorte A muestra estabilidad suficiente para uso exploratorio, con fragilidad más distribuida que concentrada en pocos outliers.
4. Esta línea queda cerrada como exploratoria y separada de live parity/bounded replay.

## 8) Qué fase sigue después del cierre 3C

Siguiente fase correcta: **Fase 3D** (si y solo si se decide avanzar), manteniendo:

- T-60 sin cambios.
- bounded replay actual sin tocar.
- separación contractual entre modo exploratorio histórico y flujos operativos.
