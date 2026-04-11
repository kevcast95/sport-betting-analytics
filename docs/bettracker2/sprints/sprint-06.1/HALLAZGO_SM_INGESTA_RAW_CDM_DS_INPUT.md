# Hallazgo — SportMonks: `raw` vs CDM, lineups y enriquecimiento de `ds_input`

**Propósito:** síntesis única para **barridos futuros** de documentación S6.1 (limpieza, alinear DECISIONES/US/TASKS con la realidad técnica).  
**Estado del doc:** consolidación PO/BE — 2026-04-10.  
**No sustituye** la auditoría ni el mapa v1; **enlaza** y resume.

---

## 1. Qué es qué (dos “mundos” en Postgres)

| Concepto | Qué **es** | Qué **no** es |
|----------|------------|----------------|
| **`bt2_events` (+ `bt2_odds_snapshot`, equipos, ligas)** | Fila **normalizada** del partido en el modelo BT2: IDs, kickoff, estado, cuotas persistidas según parsers del job. | No es el JSON crudo de SportMonks. |
| **`raw_sportmonks_fixtures`** | **Snapshot JSON** tal como lo devolvió la API en el momento del guardado (`payload`), útil para auditoría y para el **builder** que hoy lee lineups desde ahí. | No se actualiza con el job diario `fetch_upcoming`; no es “la misma fila” que `bt2_events`. |

**Regla mental:** el **día a día** puede tener el calendario **fresco** en **`bt2_events`** y, a la vez, un **`raw.payload` viejo o incompleto** si nadie reescribe `raw` con un `include` más rico.

---

## 2. Matriz — flujos que llaman a `api.sportmonks.com` (repo)

| Flujo / script | Endpoint (v3) | `include=` en código | Efecto en Postgres |
|----------------|---------------|----------------------|-------------------|
| Atraco `scripts/bt2_atraco/sportmonks_worker.py` | `GET /football/fixtures/date/{YYYY-MM-DD}` (paginado) | `participants;odds;statistics;events;league;scores` | **`raw_sportmonks_fixtures`** — `INSERT … ON CONFLICT (fixture_id) DO NOTHING` → **no actualiza** si el `fixture_id` ya existe. |
| Ingesta diaria `scripts/bt2_cdm/fetch_upcoming.py` | `GET /football/fixtures/between/{start}/{end}` (paginado) | `participants;odds;scores;league` | **`bt2_leagues`, `bt2_teams`, `bt2_events`, `bt2_odds_snapshot`**. **No** escribe `raw_sportmonks_fixtures`. |
| Smoke `scripts/bt2_smoke_test.py` | leagues / fixtures/date | parcial (`participants;odds` en fixtures) | Sin persistencia (solo comprobación). |
| `normalize_fixtures.py` | *(no API)* | — | Lee **`raw`** → upsert CDM. |

*(Verificación: no hay más hosts `api.sportmonks.com` en `.py` del repo salvo los anteriores.)*

---

## 3. Hallazgo principal — lineups (auditoría + API)

- **Auditoría §4** sobre el corpus en `raw`: sin estructura tipo v1 de lineups en el JSON **guardado**; conteo alto de `injur` era **ruido** (subcadena en `injured` bajo `events[]`).
- **Causa raíz cerrada:** ningún job usa `include` con **`lineups`**, **`formations`**, **`sidelined`**, etc. Por eso **no aparecen** en el payload persistido.
- **Prueba API** (`fixture_id` 19348514, misma clave que `.env`): con  
  `include=…;lineups;sidelined;formations` (además del bloque habitual) → HTTP 200 con listas **estructuradas** (`lineups` ~40 filas con `player_id`, `formation_field`, …; `formations`; `sidelined`). **Material usable** para acercarse a resumen v1, sujeto a **mapeo + whitelist US-DX-003 + anti-fuga**.

**Decisión vigente hasta US:** en builder, `processed.lineups` **`available: false`** + `diagnostics.fetch_errors` explícito — ver **`V1_SOFASCORE_A_BT2_DS_INPUT_MAPA.md` §7** y código en `apps/api/bt2_dsr_ds_input_builder.py`.

---

## 4. Desincronización diario ↔ raw ↔ builder

1. **`fetch_upcoming`** mantiene CDM al día en su ventana; **no** toca `raw`.
2. **Atraco** llenó `raw` histórico con un `include` **sin** lineups; **`DO NOTHING`** impide refrescar payload si el id ya existe.
3. **Builder** lee **`raw`** para lineups → puede ver JSON **antiguo / pobre** aunque `bt2_events` esté actualizado.

**Implicación:** enriquecer `ds_input` desde SM en operación diaria **exige decisión explícita**: ampliar `include`, **persistir** (UPSERT / job de refresh de `raw` o **tablas derivadas** con FK a `sportmonks_fixture_id`), y luego extender builder + contrato DX.

---

## 5. Corners y `statistics` (sin include aparte)

- Con **`include=statistics`** ya vienen muchas filas de estadísticas de equipo; **corners** aparecen como **`type_id: 34`** (home/away), alineado al catálogo de tipos SportMonks.
- No hace falta un include distinto “solo corners”; opcional **cache local** de `type_id → nombre` (la doc desaconseja anidar `statistics.type` en cada request en producción).

---

## 6. Cómo enriquecer “al máximo” por partido (orientación BE)

- Combinar includes según negocio y plan: **participants, league, season, scores, odds, statistics, lineups, lineups.details, formations, sidelined, events, venue, state**, add-ons (**xG**, **pressure**, …) si el contrato lo permite.
- **Límite:** ~**3 niveles** de anidación en includes (p. ej. `lineups.details.type`).
- **Peso / coste:** usar **`filters=`** (p. ej. `fixtureStatisticTypes`, `lineupDetailTypes`) y **`select=`** para recortar bytes y créditos; odds con filtros de mercados/bookmakers si aplica.

*(Detalle en respuesta BE al PO; este archivo solo fija el criterio.)*

---

## 7. Triaje del gap (producto / ingeniería)

| Hipótesis | ¿Aplica? |
|-----------|----------|
| “No lo pedimos” | **Sí** — ningún job actual pide `lineups` en `include`. |
| “No viene en la API” | **No** — verificado con fixture by ID + includes. |
| “Viene pero no lo persistimos” | **Sí** — el `raw` refleja solo lo pedido; además el diario no escribe `raw`. |

---

## 8. Próximos pasos sugeridos (backlog, no ejecutados aquí)

1. **US producto + BE:** `include` ampliado (mínimo viable vs “máximo enriquecido”), ventana de fixtures a refrescar, coste API.
2. **Persistencia:** **UPSERT** sobre `raw` o tabla **`lineups` / stats derivadas** + FK a fixture; revisar **quitar o sustituir `DO NOTHING`** donde haga falta refresh.
3. **DX:** si cambia el JSON hacia el LLM → **US-DX-003**, whitelist, validador.
4. **Builder:** mapear `lineups` / `sidelined` / formations a `processed.lineups` tipo v1 cuando haya datos reales.
5. **Barrido S6.2:** alinear [`../sprint-06.2/incremento_mejora_a_v1_bt2.md`](../sprint-06.2/incremento_mejora_a_v1_bt2.md), `SIGUIENTES_PASOS_POST_AUDITORIA_RAW_SPORTMONKS.md`, `AUDITORIA_*`, y nuevas `TASKS.md` / `DECISIONES.md` en 06.2 para no duplicar ni contradecir este hallazgo.

---

## 9. Referencias en repo

| Documento / artefacto | Contenido relacionado |
|----------------------|------------------------|
| [`V1_SOFASCORE_A_BT2_DS_INPUT_MAPA.md`](./V1_SOFASCORE_A_BT2_DS_INPUT_MAPA.md) §7 | Gap lineups, decisión BE, próximo paso include + UPSERT. |
| [`AUDITORIA_RAW_SPORTMONKS_2026-04-09.md`](./AUDITORIA_RAW_SPORTMONKS_2026-04-09.md) §4 | Metodología muestra, conclusiones sobre corpus sin lineups en raíz. |
| [`SIGUIENTES_PASOS_POST_AUDITORIA_RAW_SPORTMONKS.md`](./SIGUIENTES_PASOS_POST_AUDITORIA_RAW_SPORTMONKS.md) | Checklist (lineups hecho; statistics mapper, 429 sin raw pendientes). |
| `scripts/bt2_lineup_payload_probe.py`, `out/lineup_probe_paths.json` | Probe §4. |
| `scripts/bt2_cdm/fetch_upcoming.py`, `scripts/bt2_atraco/sportmonks_worker.py` | `SM_INCLUDES` y tablas tocadas. |
| [`../sprint-06.2/incremento_mejora_a_v1_bt2.md`](../sprint-06.2/incremento_mejora_a_v1_bt2.md) | Plan “BT2 > v1” y fases de datos/builder (S6.2). |
| [`../../dx/bt2_ds_input_v1_parity_fase1.md`](../../dx/bt2_ds_input_v1_parity_fase1.md) | Whitelist contrato `ds_input`. |

---

*Última actualización: 2026-04-10.*
