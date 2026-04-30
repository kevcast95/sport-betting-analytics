# BT2 v1/core audit - cierre de tramo

Fecha: 2026-04-30

## Alcance

Este tramo audito el sistema previo/paralelo a BT2 asociado a `core/`, `jobs/`, `processors/`, `db/sport-tracker.sqlite3` y artefactos `out/`.

Importante: en estos reportes `v1` no significa una version formal de BT2. Significa el sistema previo no-BT2 que seguia operativo durante la migracion.

## Fuentes usadas

- `docs/bettracker2/00_IDENTIDAD_PROYECTO.md`
- Docs de Fase 4 bajo `docs/bettracker2/fase4/`
- `docs/GUIA_OPERACION_Y_ARQUITECTURA.md`
- `openclaw.md`
- Codigo en `core/` y `jobs/`
- SQLite historico `db/sport-tracker.sqlite3`

## Ventana auditada

`2026-03-23` a `2026-04-10`, usando `daily_runs.run_date` como fecha base.

## Artefactos

- `v1_core_identity_map.md`: separacion conceptual BT2 vs sistema previo y rutas auditadas.
- `v1_core_flow_audit.md`: reconstruccion del flujo real de picks.
- `v1_daily_activity.csv`: actividad diaria, mercados, ligas, estados y ROI flat stake.
- `v1_prompt_and_input_audit.md`: prompt, input y criterio de decision.
- `v1_vs_bt2_current_comparison.md`: comparacion metodologica con shadow v6 y selective FT_1X2.
- `v1_audit_summary.json`: resumen estructurado de metricas.

## Veredicto resumido

El sistema previo estaba mas alineado con el objetivo de producto como picker: dado un grupo de eventos, producir picks publicables o explicar ausencia de valor. Sin embargo, no queda probado que fuera mejor en performance real, porque el universo, mercados, evaluacion y setup no son comparables contra BT2 shadow v6.

Lo rescatable para pruebas futuras es el framing de picker, el input contextual simple/rico, el soporte multi-mercado y los filtros de publicabilidad. No se recomienda usar sus resultados como prueba directa contra BT2 sin un benchmark same-slice.

## Restricciones respetadas

- No se tocaron tablas productivas.
- No se ejecutaron scrapers.
- No se llamaron LLMs externos.
- No se cambio el flujo BT2 ni el flujo previo.
