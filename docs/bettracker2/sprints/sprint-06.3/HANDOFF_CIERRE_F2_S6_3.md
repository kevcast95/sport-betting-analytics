# Handoff — Cierre normativo F2 (post–core S6.3)

> **Cuándo usar este handoff:** después de tener el **cierre operativo core** cerrado o explícitamente pausado (ver [`HANDOFF_CIERRE_S6_3.md`](./HANDOFF_CIERRE_S6_3.md), tasks T-246…T-257).  
> **Objetivo:** implementar y medir [`DECISIONES_CIERRE_F2_S6_3_FINAL.md`](./DECISIONES_CIERRE_F2_S6_3_FINAL.md).  
> **Tasks:** [`TASKS_CIERRE_F2_S6_3.md`](./TASKS_CIERRE_F2_S6_3.md) · **US:** [`US_CIERRE_F2_S6_3.md`](./US_CIERRE_F2_S6_3.md).

* * *

## 0. Relación con otros documentos

| Documento | Rol |
|-----------|-----|
| [`DECISIONES_CIERRE_S6_3.md`](./DECISIONES_CIERRE_S6_3.md) | Cierre **evidencia** loop/admin (ya ejecutado en línea principal). |
| [`PROPUESTA_INTEGRADA_CIERRE_EXTENDIDO_F2_S6_3.md`](./PROPUESTA_INTEGRADA_CIERRE_EXTENDIDO_F2_S6_3.md) | Propuesta larga (GPT/remoto): útil para **texto** y decisiones D-06-055+; **validar** contra repo antes de fusionar decisiones en `DECISIONES.md`. |
| [`DECISIONES_CIERRE_F2_S6_3_FINAL.md`](./DECISIONES_CIERRE_F2_S6_3_FINAL.md) | **Fuente normativa** del backlog T-258…T-266. |

* * *

## 1. Orden recomendado de implementación

1. **T-258–T-259** — Datos y tier: sin esto, las reglas §2–3 no son aplicables de forma uniforme.
2. **T-260–T-261** — Regla de elegibilidad refinada y refuerzo Tier A (backend puro).
3. **T-262** — Auditoría con matices (puede requerir migración JSON/códigos).
4. **T-263–T-264** — Métricas y reporte de cierre (puede depender de datos históricos suficientes).
5. **T-265** — FE cuando el contrato T-263 esté estable.
6. **T-266** — Evidencia en `EJECUCION.md`.

* * *

## 2. Riesgos y candados

- **No** mezclar KPI “oficial” con modo `BT2_POOL_ELIGIBILITY_MIN_FAMILIES=1` sin etiquetar (§6 y §5 del final F2).
- Cambios en **ACTA T-244** / códigos de descarte: coordinar con PO antes de merge.
- El reporte 30d × 5 ligas puede dar **bajo** hasta mejorar ingest; eso es **dato**, no fallo de handoff.

* * *

## 3. Definición de “hecho” para este frente

- Tasks T-258…T-266 marcadas con evidencia en repo + doc T-266.
- Anexo final de [`DECISIONES_CIERRE_F2_S6_3_FINAL.md`](./DECISIONES_CIERRE_F2_S6_3_FINAL.md) revisado (sustituir “Parcial/No” por estado actual o nueva tabla).

* * *

*Creación: 2026-04-15 — handoff F2 normativo extendido.*
