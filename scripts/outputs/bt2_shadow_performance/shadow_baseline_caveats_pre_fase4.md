# Baseline shadow pre-Fase 4 — caveats consolidados

Generado tras iteración de saneamiento (reevaluación pendientes, auditoría por `source_path`, semántica `value_pool`).

## Qué quedó resuelto / acotado

| Tema | Estado |
|------|--------|
| Solo dos runs con `pending_result`: backfill abril + daily 2026-04-27 | Documentado; re-ejecución del evaluador no reduce pendientes sin cambio de datos fuente. |
| Pendientes abril backfill | CDM local: evento `finished` sin `result_home`/`result_away`; SportMonks API (plan actual): sin marcador usable en muestras → **deuda de datos / acceso**, no bug de enlace único del evaluador. |
| Pendientes daily 2026-04-27 | Sin `bt2_event_id`; fixtures en muestra con estado SM **NS** y scores vacíos → **settlement natural** hasta que exista resultado final en fuentes. |
| Comparabilidad 2026-01..03 vs 2026-04 por carril | `sportmonks_between_subset5_fallback` vs cohorte mayormente CDM (`cdm_shadow`) estratificado en `shadow_source_path_audit.*`; ver porcentajes y ROC por path. |
| `value_pool_pass_rate = 0` en meses fallback | Semántica documentada en `shadow_value_pool_semantics_2026.md`: métrica no aplicable donde no hay VP recomputado; picks siguen política TOA histórico T-60 — **no contradicción obligatoria**. |

## Qué queda abierto (explícito)

| Tema | Impacto en baseline | ¿Bloquea abrir Fase 4A? |
|------|---------------------|--------------------------|
| **14** picks `pending_result` hasta que CDM/SM publiquen marcador final | Hit/ROI globales pueden mover levemente al cerrar | No bloquea por defecto si Fase 4A acepta «scored − pending» como definición operativa |
| **8** `no_evaluable` | Ya excluidos del numerador scored | No |
| Mezcla semántica VP vs meses solo-SM vs CDM si se usa un solo KPI VP global | Comparabilidad de métricas de auditoría VP, no de selección TOA | No si se estratifica o se etiqueta VP solo donde computable |

## Veredicto operativo

- Baseline shadow **cerrado como narrativa reproducible**: artefactos en esta carpeta + evidencia de pendientes (`shadow_pending_resolution_audit.json`).
- Abrir **Fase 4A** es decisión de producto: los caveats residuales son **acotados y documentados**; no hay contradicción técnica bloqueante conocida tras esta iteración.
