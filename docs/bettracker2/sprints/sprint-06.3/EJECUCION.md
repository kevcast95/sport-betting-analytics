# Sprint 06.3 — EJECUCION (cierre técnico / T-245)

> Registro de avance y **regresión transversal T-245**.  
> **TASKS:** [`TASKS.md`](./TASKS.md) · **US:** [`US.md`](./US.md) · **UI Fase 1:** [`EJECUCION_UI_FASE1.md`](./EJECUCION_UI_FASE1.md).

## T-245 — Comandos ejecutados (OK)

| Ámbito | Comando | Resultado |
|--------|---------|-----------|
| API BT2 | `python3 -m unittest discover -s apps/api -p '*_test.py'` (desde raíz del repo) | **78 tests**, OK |
| Web | `npm run test` en `apps/web` | **26 archivos / 127 tests**, OK |
| Web | `npm run build` en `apps/web` | `tsc -b && vite build`, OK |

**Ajuste en regresión:** `bt2_sprint06_test.TestDsrStub.test_stub_prefers_1x2` — la narrativa de `suggest_from_candidate_row` ya no contiene la palabra «Señal»; el test ahora exige presencia de **`1X2`** en el texto (copy vigente en `bt2_dsr_suggest.py`).

## DoD por US (alcance Fase 1 S6.3)

| US | Verificación breve |
|----|-------------------|
| **US-BE-049** | Tabla/modelo evaluación oficial, estados T-244, resolver + tests (`bt2_official_*`, migraciones). |
| **US-BE-050** | Job evaluación, idempotencia, métricas loop, runbook evaluador. |
| **US-BE-051** | Elegibilidad v1 determinística, auditoría persistida, catálogo motivos + tests. |
| **US-BE-052** | Endpoint resumen Fase 1, desglose, fixture/contrato ejemplo + tests admin summary. |
| **US-FE-061** | Vista admin tres bloques, KPIs, estados vacío/error/loading; tests + build (ver `EJECUCION_UI_FASE1.md`). |

## Check cierre Sprint 06.3 (estado documental)

| Ítem TASKS | Notas |
|------------|--------|
| Cobertura por capas (tabla en TASKS) | Tareas T-227–T-244 implementadas según casillas en `TASKS.md`. |
| Medición vs oficial sin depender de liquidación usuario | Alineado a acta **T-244** / **D-06-050** y código de evaluación oficial. |
| **Evidencia de loop con picks reales** | **Pendiente operación:** requiere corrida de jobs + entorno con datos (no cubierto solo por CI). |
| `pool_eligibility_rate` desde auditoría | Bloque pool del admin lee auditoría persistida (tests `bt2_admin_fase1_summary_test`, `bt2_pool_eligibility_v1_test`). |
| Admin: cobertura / loop / precisión sin mezclar pendientes en hit rate | Implementado en FE + copy explícito; QA manual en `EJECUCION_UI_FASE1.md`. |
| T-245 en entrega | Este archivo + enlace desde `TASKS.md`. |

---

*Última actualización: regresión T-245 cerrada en repo (tests + build + evidencia).*
