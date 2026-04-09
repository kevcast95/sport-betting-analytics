# Sprint 06.1 — TASKS

> **Numeración global:** **T-171** … (Sprint 06 termina en **T-168** en [`../sprint-06/TASKS.md`](../sprint-06/TASKS.md)).  
> **Modo de trabajo:** **D-06-023** — definición completa antes de ejecutar.

## Apto 100% para ejecución (Definition of Ready)

Son **estos cuatro ítems** (checkboxes de Markdown en este archivo). No sustituyen las tareas T-### de abajo: son un **cierre de kickoff** (“sí, el equipo entendió igual el contrato antes del primer merge”).

Quién los marca (puede ser la misma persona si cumple varios roles):

| ✓ | Qué se confirma | Quién marca (típico) |
|---|-----------------|----------------------|
| [ ] | **D-06-021** … **D-06-026** leídas; **D-06-026** §6 (0 filas en pool fallback → vacío duro, sin fallback estadístico) **reflejado en el diseño** que implementará **T-179–T-180**. | **BE** (orquestación **T-179–T-180**); **PO/BA** firman lectura en kickoff si el proceso del equipo lo exige. |
| [ ] | **US.md**, este **TASKS** y **HANDOFF** coherentes con **D-06-024** / **D-06-026** (sin dos verdades). | **PO/BA** o **TL** (auditoría rápida de docs). |
| [ ] | **T-171** lista (whitelist) — ver checkbox **T-171** más abajo; **T-188** fuera de alcance hasta **decisión explícita de PO**. | **DX** (cierre **T-171**) + **PO** si redefine alcance. |
| [ ] | **Contrato BE → FE:** lista de campos nuevos vault/admin (vacío operativo, lineage, `limited_coverage` / degradación) **publicada en OpenAPI** (**T-173**) o en el cuerpo del PR de **T-173**; **FE** (**T-184**) confirma cobertura **antes** del merge final FE. |

## Reglas

- Cada tarea referencia **US-###** de [`US.md`](./US.md).
- Orden sugerido de implementación: [`HANDOFF_EJECUCION_S6_1.md`](./HANDOFF_EJECUCION_S6_1.md).

---

## Contratos — US-DX-003

- [x] **T-171** (US-DX-003) — **Whitelist fase 1** en [`../../dx/bt2_ds_input_v1_parity_fase1.md`](../../dx/bt2_ds_input_v1_parity_fase1.md) (actualizada con mercados valor / `market_coverage`). Política PO: **D-06-024** + **D-06-025** en [`DECISIONES.md`](./DECISIONES.md).
- [ ] **T-172** (US-DX-003) — Actualizar validación anti-fuga / esquemas Pydantic en `bt2_dsr_contract.py` (y aliados) para reflejar whitelist; tests que fallen si se añade clave no permitida.
- [ ] **T-173** (US-DX-003) — Bump **`contractVersion`** en `GET /bt2/meta` (valor sugerido: `bt2-dx-001-s6.1`); regenerar/actualizar OpenAPI y **`bt2Types.ts`** para todos los campos nuevos expuestos al cliente (vacío operativo, lineage, degradación; **score** solo si **T-183** lo expone al cliente).

## Backend — US-BE-032

- [ ] **T-174** (US-BE-032) — Implementar **builder** `ds_input` rico conforme whitelist (nuevo módulo recomendado bajo `apps/api/`), sin acoplar aún al router si hace falta TDD puro.
- [ ] **T-175** (US-BE-032) — Sustituir/ampliar `_build_ds_input_item` / `DsrBatchCandidate` para usar builder; mantener compatibilidad con `deepseek_suggest_batch`.
- [ ] **T-176** (US-BE-032) — Tests unitarios builder + fixture mínima evento/odds/CDM.

## Backend — US-BE-033

- [ ] **T-177** (US-BE-033) — **Pool valor:** candidatos desde ligas prioritarias; cuota mín **1.30**; **sin** mercados obligatorios fijos — incluir en CDM/mapeo canónico 1X2, doble oportunidad, O/U goles/corners/tarjetas, BTTS según **D-06-024** / **D-06-025**; lotes dimensionados por técnica (tokens/coste), no tope PO arbitrario.
- [ ] **T-178** (US-BE-033) — **Premium vs standard** según intención **D-06-024** § premium + **D-06-025** §2 (standard meta >70% ventana; premium “casi seguro” / reglas más estrictas en servidor).

## Backend — US-BE-036

- [ ] **T-179** (US-BE-036) — Flags de **cobertura / degradación** (`dsr_signal_degraded`, vacío duro, opcional heurística “pocos eventos”) según **D-06-024** § cobertura + **D-06-025** §4 + **D-06-026** §4–§6 (incl. **vacío duro** = 0 filas elegibles en pool SQL de fallback con filtros **T-177**); exponer en contrato vault (**US-DX-003** / T-173) para copy + disclaimer.
- [ ] **T-180** (US-BE-036) — **Orquestación snapshot:** DSR primero; si vacío **y** hay datos SQL utilizables → **fallback** con lineage + mensaje/disclaimer (**D-06-025**); solo **vacío duro** sin candidatos CDM; persistencia idempotente.

## Backend — US-BE-034

- [ ] **T-181** (US-BE-034) — **Post-DSR** (ver **D-06-025** §3, **D-06-024** tabla): reconciliar input vs salida modelo; **persistir solo el pick canónico** (cuota desde input si desvío; reglas si mercado inválido; cap confianza si odds &gt; 15; logs/métricas); tests casos borde.
- [ ] **T-182** (US-BE-034) — Integrar post-proceso en el pipeline **después** de parse `picks_by_event` y **antes** de INSERT `bt2_daily_picks`.

## Backend — US-BE-035

- [ ] **T-183** (US-BE-035) — Endpoint admin agregados (conteos por `dsr_confidence_label`, `dsr_source`, y **score** cuando el modelo de datos lo permita) filtrados por `operating_day_key`; auth admin key existente.

## Frontend — US-FE-055

- [ ] **T-184** (US-FE-055) — Actualizar **`bt2Types`** + consumo API vault para nuevos campos (mensaje vacío operativo, lineage).
- [ ] **T-185** (US-FE-055) — **PickCard** / `vaultModelReading`: copy que separa confianza simbólica, fallo ingesta vs sin señal DSR, y score si BE lo envía.
- [ ] **T-186** (US-FE-055) — Admin DSR (o sección existente): leyenda/métricas **US-BE-035** sin mezclar KPIs en un solo rótulo.

## Cierre transversal

- [ ] **T-187** (S6.1 cierre) — `pytest` módulos BT2 tocados + `npm test` + `npm run build` en `apps/web`.

---

## Diferido (no cuenta para cierre S6.1)

- [ ] **T-188** *(diferido S7+ / decisión PO)* — Vista admin **auditoría CDM** según [`../../notas/VISTA_AUDITORIA_EVENTOS_CDM_ADMIN.md`](../../notas/VISTA_AUDITORIA_EVENTOS_CDM_ADMIN.md).

---

## Checklist de cobertura sprint (mapeo rápido)

| Bloque | Tareas |
|--------|--------|
| Paridad `ds_input` / DX | T-171–T-173 |
| Builder CDM (US-BE-032) | T-174–T-176 |
| Pool / premium | T-177–T-178 |
| Orquestación D-06-022 | T-179–T-180 |
| Post-DSR | T-181–T-182 |
| Admin medición v0 | T-183 + T-186 (leyenda) |
| FE semántica vault | T-184–T-185 |
| Cierre QA | T-187 |

---

## Check cierre Sprint 06.1

- [ ] **D-06-021** satisfecha en código (o enmienda DECISIONES).
- [ ] **D-06-022** satisfecha + pruebas de los **tres** escenarios en **US-BE-036** (evidencia: PR y/o [`EJECUCION.md`](./EJECUCION.md) § escenarios).
- [ ] **D-06-023:** al inicio del sprint la definición estaba completa; al cierre, **T-171–T-187** marcadas según alcance (**T-188** excluido hasta inclusión explícita por PO en **TASKS** / **DECISIONES**).
- [ ] **D-06-024** y **D-06-025** reflejadas en pool, post-DSR y copy (código + tests o nota de excepción en DECISIONES).
- [ ] **D-06-026** (incl. §6 vacío duro / 0 filas pool) reflejada en **T-179–T-180** y pruebas o `EJECUCION.md`.

---

*Actualizado: 2026-04-09 — DoR, check cierre D-06-024…026, T-179 §6.*
