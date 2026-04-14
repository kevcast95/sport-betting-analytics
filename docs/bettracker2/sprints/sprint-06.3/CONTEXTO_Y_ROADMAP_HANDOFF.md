# BetTracker 2.0 — contexto preciso + roadmap (handoff para nuevo chat)

**Propósito:** entrar a una conversación nueva con **poca carga contextual**. No duplica el detalle de US/TASKS; remite a fuentes canónicas.

---

## 1. Identidad del producto

**Fuente normativa:** [`../../00_IDENTIDAD_PROYECTO.md`](../../00_IDENTIDAD_PROYECTO.md).

- **Qué es:** protocolo de **gestión conductual y riesgo** deportivo (no “solo picks”). Objetivo declarado: **proteger bankroll y comportamiento**; la UI traduce métricas a lenguaje humano y accionable.
- **Principios clave:** API-first, capa anti-corrupción hacia un **CDM canónico**, frontend y motor de IA **agnósticos al proveedor**, migración incremental con **V1** (SQLite / rutas legacy) coexistiendo con **V2** (`/v2/*` en web, `/bt2/*` en API).
- **Idioma:** español en producto hasta traducciones explícitas.
- **Norte de negocio (PO, S6.3):** además del marco conductual, se busca **rigor en dato y señal** para apoyar decisiones con mejor información; ver roadmap §2–3 en el archivo enlazado abajo (conducta + motor de datos no se contradicen).

---

## 2. Arquitectura e integraciones (resumen)

| Capa | Qué es |
|------|--------|
| **API** | `apps/api/main.py` — **un** proceso: rutas V1/scrapper (SQLite) + prefijo **`/bt2/*`** (PostgreSQL `bt2_*`). |
| **Web V2** | `apps/web` — React; rutas bóveda, ledger, admin BT2 bajo `/v2/...`. |
| **CDM BT2** | Tablas `bt2_events`, `bt2_odds_snapshot`, `bt2_daily_picks`, `bt2_picks`, `raw_sportmonks_fixtures`, etc. |
| **SportMonks** | Ingesta histórica (**atraco** `scripts/bt2_atraco/`) y operación diaria (**`scripts/bt2_cdm/fetch_upcoming.py`** y afines). Clave natural típica: `sportmonks_fixture_id`. |
| **TheOddsAPI** | Opcional; odds alternativas/complemento según workers. |
| **DSR (señal)** | Lotes con insumo **`ds_input`** (whitelist + builder desde Postgres); proveedor LLM configurable (**DeepSeek** en prod típico; contrato tipo OpenAI). Reglas locales como fallback. |
| **Variables** | Raíz `.env` — obligatorias mínimas para BT2: `SPORTMONKS_API_KEY`, `BT2_DATABASE_URL`, etc. Guía: [`../../LOCAL_API.md`](../../LOCAL_API.md). |

**Lectura operativa local:** [`../../LOCAL_API.md`](../../LOCAL_API.md) (uvicorn, migraciones Alembic, refresh snapshot admin).

---

## 3. Estado de trabajo (abril 2026)

- **Sprint 06.2:** cerrado por acta técnica; entregas y traspasos explícitos en [`../sprint-06.2/CIERRE_S6_2.md`](../sprint-06.2/CIERRE_S6_2.md). Quedó deuda documentada (cubo C, FSM Regenerar completo, pool global, admin precisión alineada a “modelo en bóveda”, etc.).
- **Sprint 06.3:** **refinement** — feedback, premisa de producto, acotación de huecos (datos, snapshot, coste DSR, conducta bóveda, admin global). Documentos vivos en esta carpeta.

---

## 4. Roadmap PO (orden mental y frentes)

**Documento maestro:** [`ROADMAP_PO_NORTE_Y_FASES.md`](./ROADMAP_PO_NORTE_Y_FASES.md).

Resume:

- **Capas:** ingesta/CDM → `ds_input` → DSR/snapshot → UX/conducta → **medición admin**.
- **Frentes F1–F6:** admin/verdad de resultado, uso real de SM + completitud, frescura snapshot vs coste, variedad mercados, DP/bóveda, deuda S6.2.
- **Fases 0–4:** primero definir éxito del modelo y métricas de datos; luego cerrar loop de medición; después política de refresco; luego señal/UX; al final deuda listada.

**Satélites útiles:**

| Doc | Uso |
|-----|-----|
| [`Plan_mejora_base.md`](./Plan_mejora_base.md) | Propuestas y preguntas (snapshot, DSR, coste, pool). |
| [`premnisa_6.3.md`](./premnisa_6.3.md) | Notas PO: mercados, bóveda, admin global + respuestas BA borrador. |
| [`../../notas/BACKTESTING_RECONCILIACION_CDM.md`](../../notas/BACKTESTING_RECONCILIACION_CDM.md) | Atraco vs tiempo real; odds en CDM sin historial de línea por defecto. |
| [`../../notas/CONVERSACION_MERCADOS_VARIEDAD_DSR.md`](../../notas/CONVERSACION_MERCADOS_VARIEDAD_DSR.md) | Variedad 1X2 vs O/U/BTTS y límites del código actual. |

---

## 5. Cómo continuar en un chat nuevo (sin ruido)

1. Abrir este archivo + [`ROADMAP_PO_NORTE_Y_FASES.md`](./ROADMAP_PO_NORTE_Y_FASES.md).  
2. Si el tema es **código BT2:** `apps/api/bt2_*.py`, `apps/web/src/.../vault`, `docs/bettracker2/LOCAL_API.md`.  
3. Si el tema es **producto/prioridad:** empezar por **Fase 0** del roadmap (definición de éxito del modelo + una métrica de completitud de datos).  
4. No asumir que “sprint cerrado” = todas las preguntas de producto resueltas; ver §2 del roadmap.

---

*2026-04-12 — handoff liviano; actualizar si cambia el norte o el stack.*
