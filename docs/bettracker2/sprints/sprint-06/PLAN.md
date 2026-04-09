# Sprint 06 — Planificación (motor CDM + DSR + operación + analytics)

> **Estado:** **En ejecución** — arranque autorizado (**D-06-017**, 2026-04-08); backlog completo **T-153–T-168** en curso con paralelismo FE ∥ BE según dependencias por tarea.  
> **Precedentes cerrados en doc (2026-04-08):** Sprints **05**, **05.1**, **05.2** — ver [`../sprint-05/TASKS.md`](../sprint-05/TASKS.md), [`../sprint-05.1/TASKS.md`](../sprint-05.1/TASKS.md), [`../sprint-05.2/TASKS.md`](../sprint-05.2/TASKS.md).  
> **Calendario repo:** Este sprint absorbe el **“Sprint 5 motor”** histórico — [`../sprint-05/DECISIONES.md`](../sprint-05/DECISIONES.md) **D-05-001**.

## 1. Objetivo (una frase)

Pasar de **picks por regla estadística** (tier + margen + odd mínima) a **criterio del modelo (DeepSeek Reasoner)** con **justificación de selección y tipo de mercado** explícitos, **composición diaria objetivo (15 picks / franjas / 2 premium + 3 libres de alta calidad)** según **D-06-008**, **ingesta CDM programada**, **mercados normalizados** (multi-deporte, fútbol primero), **DX por hitos** (`contractVersion` por entrega) y **analytics** mínimos (picks atribuibles a DSR) — ver **D-06-007 … D-06-011** y [`pregts_definiciones.md`](./pregts_definiciones.md).

## 2. Alcance Sprint 06

### 2.1 Núcleo (prioridad — **D-06-015**)

| Qué | Para qué |
|-----|----------|
| **DSR en lotes** | Candidatos solo desde backend; **prompt/contrato en Python**; **cero PII**; revisar patrón **v1**. |
| **Persistencia** | Saber qué predijo el modelo por pick + versión pipeline. |
| **Medición al settle** | Contar cuántos del snapshot **cerraron alineados** con esa predicción. |
| **Vista admin** | Solo admin al inicio: análisis **15 (o N) del día** vs aciertos; datos **persistidos** vía API. |
| **Bóveda** | Mínimo viable si hace falta: picks del pipeline DSR; pulir narrativa puede ir a **S6.1**. |

### 2.2 Mismo sprint — pilares en paralelo (orden por `TASKS` / `EJECUCION`)

Todo lo siguiente forma parte del **mismo Sprint 06**; **no** es un recorte global “para después”. El **núcleo D-06-015** define prioridad de **valor** y cierre mínimo; la ejecución técnica cubre el backlog completo.

| Pilar | Contenido |
|-------|-----------|
| **DSR + CDM** | Integración DeepSeek Reasoner con el flujo de candidatos CDM; diseño **por fases** con barreras (**D-06-002**). |
| **Ingesta** | `fetch_upcoming` → **cron** + **US-OPS-001** (**T-159**, **T-160**). |
| **Normalización** | Enum mercados (**US-BE-027** / **US-FE-054**, **T-161–T-162**, **T-167**). |
| **US-DX** | Catálogo, DSR I/O, **operatorProfile**, bump `contractVersion` (**T-153–T-156**). |
| **Analytics** | Endpoints **US-BE-028** + vista **US-FE-053** (admin precisión DSR, **D-06-015** / **D-06-004**). |
| **Bóveda / empty states** | Narrativa DSR **US-FE-052**; UI **“no hay picks ahora”** (**D-06-009**). |

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
- [`DECISIONES.md`](./DECISIONES.md) — **D-06-001 … D-06-019** (… **D-06-018** proveedor DeepSeek; **D-06-019** lotes v1-equivalentes); cuestionario [`pregts_definiciones.md`](./pregts_definiciones.md).  
- [`EJECUCION.md`](./EJECUCION.md) — bloques **Backend / Frontend / DX / OPS** y orden sugerido.  
- [`EJECUCION_COMPLETA_PUNTA_A_PUNTA.md`](./EJECUCION_COMPLETA_PUNTA_A_PUNTA.md) — checklist **inicio → fin** (admin key, sesión → snapshot, DSR).  
- [`BE_HANDOFF_SPRINT06.md`](./BE_HANDOFF_SPRINT06.md) — contrato vault/picks/admin → FE.  
- Runbook cron: [`../runbooks/bt2_fetch_upcoming_cron.md`](../runbooks/bt2_fetch_upcoming_cron.md) (**T-160** / **D-06-005**).

## 6. Criterio de “listo para arrancar S6”

- [x] **PO ratifica D-06-004** (MVP analytics) y el **marco D-06-002** para arranque — ver **D-06-017** (2026-04-08). Detalle Fase B (lista de campos) puede cerrarse durante el sprint en **US-DX-002** / **T-154**.
- [x] **US-DX-002** (**T-153–T-156**): alcance en [`US.md`](./US.md) + [`TASKS.md`](./TASKS.md); ejecución en paralelo desde día 1. **Merge masivo** de FE dependiente de contratos se gobierna **por hito** (`contractVersion`), no como bloqueo de arranque (**D-06-017**).
- [x] **US-OPS-001:** baseline **D-06-013** + **T-160**; canal/on-call concreto sustituye placeholders cuando la org lo asigne (**D-06-017**).

**Green light formal:** **D-06-017**.

---

*Última actualización: 2026-04-08 — S6 en ejecución; §6 cerrado vía **D-06-017**.*
