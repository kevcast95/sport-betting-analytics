# Sprint 06 — Planificación (motor CDM + DSR + operación + analytics)

> **Estado:** **En definición** — documentación lista para refinamiento PO/BE; ejecución tras arranque formal.  
> **Precedentes cerrados en doc (2026-04-08):** Sprints **05**, **05.1**, **05.2** — ver [`../sprint-05/TASKS.md`](../sprint-05/TASKS.md), [`../sprint-05.1/TASKS.md`](../sprint-05.1/TASKS.md), [`../sprint-05.2/TASKS.md`](../sprint-05.2/TASKS.md).  
> **Calendario repo:** Este sprint absorbe el **“Sprint 5 motor”** histórico — [`../sprint-05/DECISIONES.md`](../sprint-05/DECISIONES.md) **D-05-001**.

## 1. Objetivo (una frase)

Pasar de **picks por regla estadística** (tier + margen + odd mínima) a **criterio del modelo (DSR)** sobre edge/selección **sin fuga de información** en backtesting, con **ingesta CDM programada**, **mercados normalizados** (enum), **contratos DX/OpenAPI** explícitos y **analytics** de picks/bóveda acordados.

## 2. Alcance Sprint 06

| Pilar | Contenido |
|-------|-----------|
| **DSR + CDM** | Integración DeepSeek Reasoner con el flujo de candidatos CDM; diseño **por fases** con barreras (el modelo no “ve” resultados futuros en backtest sin protocolo documentado). |
| **Ingesta** | `fetch_upcoming` (hoy manual en S4) → **cron o job programado** + documentación operativa (**US-OPS**). |
| **Normalización** | Deuda **D-04-002**: strings frágiles en settle → **enum cerrado** (o capa canónica) en picks / snapshot; alinear `_determine_outcome` / FE. |
| **US-DX** | OpenAPI alineado a `reason` ledger donde falte; alias **`operatorProfile`** si se expone en métricas conductuales; `contractVersion` por hito DSR. |
| **Analytics** | Producto: agregados picks/bóveda (lo pospuesto tras snapshot diario en S4) — acotar **MVP analytics** en **D-06-004**. |

## 3. Fuera de Sprint 06 (Sprint 07)

- Parlays (`bt2_parlays`, liquidación AND, límite 2/día, DSR propone combinaciones) — **D-04-012 / D-04-013**.
- Recalibración automática diagnóstico longitudinal — más allá de **US-BE-016**.
- **D-04-001** `unit_value_cop` por sesión (bankroll COP fiel) — backlog orientado S7 salvo repriorización.

## 4. Dependencias

- **Sprints 05 / 05.1 / 05.2:** cerrados formalmente en documentación; coherencia API-first (ledger, vault, settle, bóveda franjas/post–kickoff) estable antes de tocar enum mercados y DSR.
- **Código existente:** `scripts/bt2_cdm/fetch_upcoming.py`, `build_candidates.py`, pipeline DSR (S3/S4).

## 5. Archivos del sprint

- [`US.md`](./US.md) — **US-FE-052+** (DSR/analytics/mercados; **US-FE-050…051** en [`../sprint-05.2/US.md`](../sprint-05.2/US.md)), US-BE-025+, US-DX-002, US-OPS-001.  
- [`TASKS.md`](./TASKS.md) — **T-153+** (continúa tras Sprint 05).  
- [`DECISIONES.md`](./DECISIONES.md) — **D-06-001 … D-06-006** (+ ampliaciones con PO).  
- [`EJECUCION.md`](./EJECUCION.md) — bloques **Backend / Frontend / DX / OPS** y orden sugerido.

## 6. Criterio de “listo para arrancar S6”

- [ ] PO ratifica **D-06-004** (MVP analytics) y cualquier gap en **D-06-002** (fases DSR).
- [ ] **US-DX-002** (**T-153–T-156**) definida antes de merge masivo FE dependiente de contratos.
- [ ] Runbook **US-OPS-001** acordado con entorno real (staging/prod).

---

*Última actualización: 2026-04-08 — cierre 05.x en doc; S6 en definición + `EJECUCION.md`.*
