# Mapa técnico: endpoints SofaScore (referencia v1) → pipeline v1 → gap BT2 / Postgres

**Rol:** referencia BA/PM + handoff BE ([`ba_pm_agent.md`](../agent_roles/ba_pm_agent.md)).  
**Objetivo:** enlazar los `.txt` de endpoints (capturas Network SofaScore) con **código v1** y con **qué existe hoy en BT2**, para planear paridad de `ds_input` sin replicar scrap en prod.

**Nota:** los archivos de ejemplo del PO viven hoy fuera del repo, p. ej.  
`/Users/kevcast/Documents/Projects/endpoints/futbol/*.txt` — se pueden copiar a  
`docs/bettracker2/refs/sofascore_endpoints/` cuando se quiera versionarlos en git.

---

## 1. Equivalencia endpoint SofaScore ↔ scraper v1 ↔ `processed` v1

El scraper unificado es **`core/event_bundle_scraper.py`** (`fetch_event_bundle`). Las URLs coinciden con las de tus `.txt`:

| Tu archivo / concepto | URL API SofaScore (v1) | Clave en bundle | Processor (`processors/`) | Salida en `processed` (v1) |
|------------------------|-------------------------|-----------------|---------------------------|-----------------------------|
| `event_id.txt` | `GET /api/v1/event/{id}` | `event` + derivados | (contexto en bundle, no processor separado típico) | `event_context` en `features_json` |
| `event_id_lineups.txt` | `GET .../event/{id}/lineups` | `lineups` | `lineups_processor.process_lineups` | `processed.lineups` → `lineup_summary` (formación, missing, key_player, avg_rating, …) |
| `event_id_statistics.txt`, `stats_test.txt` | `GET .../event/{id}/statistics` | `statistics` | `statistics_processor.process_statistics` | `processed.statistics` → `match_performance` (xG, shots, big chances, GK saves, possession, …) |
| `h2h_id.txt` | `GET .../event/{id}/h2h` | `h2h` | `h2h_processor.process_h2h` | `processed.h2h` (p. ej. `team_duel`, `manager_duel`) |
| (bundle) | `GET .../event/{id}/team-streaks` | `team_streaks` | `team_streaks_processor` | `processed.team_streaks` |
| `event_id_odds_feature.txt` | `GET .../event/{id}/odds/1/featured` | `odds_featured` | `odds_feature_processor` | `processed.odds_featured` |
| `event_id_odds_all.txt` | `GET .../event/{id}/odds/1/all` | `odds_all` | `odds_all_processor` | `processed.odds_all` |
| (bundle) | `.../team/{id}/.../statistics/overall` (temporada) | `team_season_*` | `team_season_stats_processor` | `processed.team_season_stats` |

**Persistencia v1:** `jobs/persist_event_bundle.py` → `event_snapshots` (crudo por tipo) + **`event_features.features_json`** (JSON ya con `event_context`, `processed`, `diagnostics`).  
**Armado `ds_input`:** `jobs/select_candidates.py` copia ese `features_json` al array `ds_input[]` por evento candidato (ver comentarios ~L575–579).

**Diagnósticos v1** (ej. `statistics_ok`, `lineups_ok`, `h2h_ok`): se calculan en el bundle scraper según errores HTTP y validez del processor (`core/event_bundle_scraper.py` ~L407–450).

---

## 2. Qué hay hoy en Postgres BT2 (modelo mental)

Tablas CDM principales en código (`apps/api/bt2_models.py`):

| Tabla / artefacto | Contenido relevante para “paridad SofaScore” |
|---------------------|---------------------------------------------|
| **`bt2_events`** | `sportmonks_fixture_id`, equipos (FK), `kickoff_utc`, `status`, resultado, liga, temporada (si se rellena). **Sustituye en parte** el núcleo de `event_id` (equipos, horario, estado). |
| **`bt2_teams` / `bt2_leagues`** | Nombres, `sportmonks_id`, tier. **Parcial** vs referee/manager/venue de SofaScore — depende de si SportMonks trae esos campos en otro flujo. |
| **`bt2_odds_snapshot`** | Filas por libro/mercado/selección. **Parcial** vs `odds_all` / `featured` (hay que **agregar** a `consensus` + forma canónica; ya lo hace `bt2_dsr_odds_aggregation` para el builder). |
| **`raw_sportmonks_fixtures`** | `fixture_id`, `payload` **JSONB** completo del fixture. **Aquí puede vivir** estadística agregada, alineaciones, etc. **si el job de ingesta los guarda** — **hay que validar el shape real** con consultas (`payload` keys). |
| **`raw_theoddsapi_snapshots`** | Otro proveedor de odds; útil cruzado, no sustituye lineups/H2H SofaScore. |
| **`bt2_daily_picks`** | Salida bóveda; `data_completeness_score` hoy es **heurística de cobertura de mercados en cuotas** (`data_completeness_score` en `bt2_dsr_odds_aggregation.py`), **no** xG/lineups. |

**Conclusión gap:** no existen (en el modelo SQLAlchemy actual) tablas dedicadas tipo `bt2_match_statistics`, `bt2_lineups`, `bt2_h2h`. Todo lo “rico” además de evento+cuotas debe venir de **`raw_sportmonks_fixtures.payload`** y/o **nuevas tablas/materializadas** + jobs.

---

## 3. Contraste por bloque de `ds_input` (calidad vs v1)

| Bloque `processed` (v1) | v1 | BT2 hoy (típico) | Para estar a la par |
|-------------------------|----|-------------------|----------------------|
| **`odds_featured` / consensus** | Processors SofaScore | **Sí** vía `bt2_odds_snapshot` + agregación | Afinar mapeo canónico / mercados (ya en marcha). |
| **`odds_all`** | Markets extendidos | **Parcial** — depende de qué mercados se ingesten en CDM | Ampliar ingestión + agregados multi-mercado si el whitelist lo pide. |
| **`statistics` / match_performance** | `statistics_processor` sobre `/statistics` | **Placeholder** en builder si no hay fuente | **Extraer** de `raw_sportmonks_fixtures.payload` **o** API SportMonks equivalente **o** tabla derivada; reutilizar **misma forma** que `statistics_processor` salida si es posible (menos sorpresa para prompts). |
| **`lineups`** | `lineups_processor` | **Placeholder** | Igual: payload SportMonks / endpoint lineup si existe en API; mapear a `lineup_summary`. |
| **`h2h`** | `h2h_processor` | **Placeholder** | Calcular desde **histórico `bt2_events`** (40k+ fixtures): W/D/L entre pares `home_team_id`/`away_team_id` **o** campo en payload. |
| **`team_streaks`** | Endpoint team-streaks | **Placeholder** | Serie de resultados desde histórico o API. |
| **`team_season_stats`** | Temporada liga | **Placeholder** | Stats de temporada si SportMonks las expone en payload o endpoint dedicado persistido. |
| **`diagnostics`** | Flags reales scrape | Mixto / genérico en BT2 | **Un flag por fuente** (`statistics_ok`, …) según **disponibilidad real en DB**, no `false` por defecto si hay datos. |

---

## 4. Uso de los ~40k fixtures históricos

**Objetivo:** emular **parte** de lo que SofaScore da en **post-partido** (`event_id_statistics.txt` = stats del encuentro ya jugado), y sobre todo alimentar **H2H, forma, rachas** para **pre-partido** en BT2.

**Pasos conceptuales (BE / datos):**

1. **Auditoría `raw_sportmonks_fixtures.payload`:**  
   `SELECT fixture_id, jsonb_object_keys(payload) ... LIMIT N` y documentar qué claves existen (lineups, statistics, scores, incidents, etc.).
2. **Para eventos futuros:** no habrá “statistics del partido actual”; usar **últimos N partidos** por equipo desde `bt2_events` + resultados para construir **forma** y métricas proxy (goles a favor/en contra, over rate, etc.) en Python.
3. **H2H:** query sobre eventos **terminados** entre dos `team_id` internos (o `sportmonks` team ids vía join).
4. **Normalizar salida** hacia la **misma forma** que espera el contrato whitelist (`../../dx/bt2_ds_input_v1_parity_fase1.md`) para no romper validadores.
5. **Tests:** fixtures JSON reales (anonimizados) en `apps/api` que prueben el builder.

---

## 5. Pasos de backlog sugeridos (alineados a sprint)

1. **T-189** — Inventario SQL + script de inspección `payload` + diseño de mapeo por bloque.  
2. **Ampliar builder** — rellenar `processed.*` desde Postgres cuando `available`.  
3. **T-171 / T-172** — si nuevos caminos al LLM.  
4. **T-191 / T-192** — prompt y Post-DSR con insumo ya rico.  
5. Documentar en **[`../sprint-06.2/incremento_mejora_a_v1_bt2.md`](../sprint-06.2/incremento_mejora_a_v1_bt2.md)** cualquier decisión nueva (p. ej. snapshot global vs por usuario).

---

## 6. Referencias rápidas en repo

- Scraper y URLs: `core/event_bundle_scraper.py` (~L281–289).  
- Processors: `processors/statistics_processor.py`, `lineups_processor.py`, `h2h_processor.py`, `odds_*`.  
- Persistencia: `jobs/persist_event_bundle.py`.  
- `ds_input` v1: `jobs/select_candidates.py`.  
- Builder BT2: `apps/api/bt2_dsr_ds_input_builder.py`.  
- Contrato / whitelist: `docs/bettracker2/dx/bt2_ds_input_v1_parity_fase1.md`.  
- Refinement PO: [`REFINEMENT_S6_1.md`](./REFINEMENT_S6_1.md), [`../sprint-06.2/incremento_mejora_a_v1_bt2.md`](../sprint-06.2/incremento_mejora_a_v1_bt2.md).

---

## 7. Gap `lineups` — post auditoría raw SportMonks (2026-04-10)

**Evidencia:** [`AUDITORIA_RAW_SPORTMONKS_2026-04-09.md`](./AUDITORIA_RAW_SPORTMONKS_2026-04-09.md) §4, `out/lineup_probe_paths.json`, script `scripts/bt2_lineup_payload_probe.py`.

En el **corpus actual** (`raw_sportmonks_fixtures`, ~55k filas, 26 claves top-level homogéneas) **no** aparece estructura tipo SofaScore `/event/{id}/lineups` (formación, XI, missing players, ratings, etc.). Búsqueda por subcadena (runbook §4.1): sin `lineup` / `formation` / `sidelined` / `missing` en muestra proyectable; `injur` coincide masivamente con la clave **`injured`** bajo `events[]`, no con informe médico ni titulares.

**Causa raíz (2026-04-10, verificación API):** la documentación v3 de SportMonks lista **`include=lineups`**, **`formations`**, **`sidelined`** (y `expectedLineups`, etc.) en el endpoint de fixtures. Una llamada real `GET /v3/football/fixtures/19348514?include=…;lineups;sidelined;formations` devolvió **`lineups` (40 filas)** con `player_id`, `team_id`, `formation_field`, `jersey_number`, `type_id`, etc.; **`formations`** (2); **`sidelined`** (3). El gap en `raw_sportmonks_fixtures` no es “el plano no trae alineaciones”, sino que **los jobs actuales no incluyen `lineups` en el parámetro `include`** y por tanto **no se persisten** en el JSON guardado.

**Decisión BE hasta nueva US:** `processed.lineups` permanece **`available: false`** con causa en `diagnostics.fetch_errors` (p. ej. `lineups:gap_no_v1_lineup_summary_in_raw_payload_see_AUDITORIA_RAW_SPORTMONKS_2026-04-09_sec4`). Próximo paso de producto: ampliar `include` en ingesta (y/o job dedicado) + **UPSERT** o política de refresco de `raw` (hoy `ON CONFLICT DO NOTHING` en atraco no actualiza filas existentes) — coordinar **US-DX-003** si el JSON al LLM cambia.

---

*2026-04-09 — elaborado a partir de endpoints SofaScore documentados por PO y lectura de código en repo. §7 añadido 2026-04-10.*
