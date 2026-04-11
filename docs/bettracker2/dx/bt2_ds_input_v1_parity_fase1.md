# BT2 — Whitelist `ds_input` fase 1 (paridad v1 / CDM)

> **Sprint:** 06.1 · **US:** US-DX-003 · **Decisiones:** D-06-021, D-06-002 (anti-fuga), **D-06-024**, **D-06-025** (pool valor, premium, fallback transparente).  
> **Referencia v1:** [`DSR_V1_FLUJO.md`](../DSR_V1_FLUJO.md) §4.  
> **Estado:** contrato de **entrada** hacia el lote DeepSeek; T-172 endurece validación Pydantic + `assert_no_forbidden_ds_keys` según esta lista.

## 1. Alcance fase 1

- **Solo fútbol** (`sport = "football"`).
- **Datos construibles desde Postgres CDM:** `bt2_events`, `bt2_leagues`, `bt2_teams`, `bt2_odds_snapshot`, y (para resumen de alineaciones) `raw_sportmonks_fixtures.payload` cuando exista fila para el `sportmonks_fixture_id` del evento. **Refinement S6.1 (D-06-028):** H2H, forma y rachas se derivan de `bt2_events` terminados; `team_season_stats` sigue sin tabla agregada dedicada en BT2.
- **Identificador de evento en el lote:** `event_id` = **`bt2_events.id`** (entero interno BT2). No usar `sportmonks_fixture_id` en el JSON del modelo salvo campo opcional de trazabilidad interna fuera de `ds_input` si un job lo necesita (no forma parte de la whitelist pública del ítem).
- **Objetivo:** misma **forma lógica** que v1 §4 (`selection_tier`, `schedule_display`, `event_context`, `processed`, `diagnostics`) para que prompts y post-proceso puedan evolucionar como en v1 sin otro dialecto intermedio.
- **Mercados:** el modelo elige el mercado con **mejor relación valor/datos** entre los **presentes en snapshot** para ese evento (**D-06-025**). No hay par 1X2+O/U 2.5 obligatorio en producto; BE amplía ingestión y `MarketCanonical` según API.

## 2. Envelope del lote (`batch`)

Estructura enviada dentro del mensaje `user` (además de instrucciones de tarea). Campos de primer nivel del objeto `batch`:

| Campo | Obligatorio | Origen | Notas |
|--------|-------------|--------|--------|
| `operating_day_key` | Sí | Parámetro job / sesión | `YYYY-MM-DD`, misma semántica que hoy. |
| `pipeline_version` | Sí | Constante servidor | Ej. `s6-rules-v0` o sucesor acordado con T-173. |
| `sport` | Sí | Constante `"football"` fase 1 | Alineado a v1 `job.sport`. |
| `ds_input` | Sí | Builder | Array de ítems; **no vacío** para invocación DSR (misma regla que `DsrProductionBatchIn.candidates`). |

**Prohibido** en cualquier rama del `batch`: claves que impliquen resultado final o marcador (lista en §6 y en `bt2_dsr_contract.py`).

## 3. Ítem `ds_input[]` — tabla campo a campo

### 3.1 Raíz del ítem

| Campo | Obl. | Tipo | Fuente BT2 / regla |
|--------|------|------|---------------------|
| `event_id` | Sí | `int` | `bt2_events.id`. |
| `sport` | Sí | `string` | `"football"`. |
| `selection_tier` | Sí | `"A"` \| `"B"` | **A:** evento en **pool principal** tras filtros de calidad (ligas prioritarias, frescura, al menos **un** mercado canónico **completo** en snapshot con selección ≥ cuota mínima **D-06-024**). **B:** candidato extendido / datos más delgados; el prompt debe permitir menor confianza o `motivo_sin_pick`. |
| `schedule_display` | Sí | `object` | Ver §3.2. |
| `event_context` | Sí | `object` | Ver §3.3. |
| `processed` | Sí | `object` | Ver §3.4. |
| `diagnostics` | Sí | `object` | Ver §3.5. |

**No** se permiten claves extra en el ítem en validación estricta (T-172: `extra="forbid"`).

### 3.2 `schedule_display`

| Campo | Obl. | Fuente / regla |
|--------|------|----------------|
| `utc_iso` | Sí | `bt2_events.kickoff_utc` en ISO 8601 con offset/Z. |
| `local_iso` | No | Opcional fase 1; si no hay TZ de negocio, `null` omitido o explícito `null`. |
| `timezone_reference` | No | Default sugerido `"UTC"` si no hay otra política. |

### 3.3 `event_context`

| Campo | Obl. | Fuente / regla |
|--------|------|----------------|
| `league_name` | Sí | `bt2_leagues.name` vía `event.league_id`. Si falta liga: `"unknown"`. |
| `country` | No | `bt2_leagues.country` o `null`. |
| `league_tier` | No | `bt2_leagues.tier` (S/A/B/unknown). Usado por reglas premium (D-06-024). |
| `home_team` | Sí | `bt2_teams.name` para `home_team_id`. |
| `away_team` | Sí | `bt2_teams.name` para `away_team_id`. |
| `start_timestamp_unix` | No | Derivado de `kickoff_utc` (entero segundos UTC) para paridad con scrapers v1 que usan epoch. |
| `match_state` | Sí | Derivado de `bt2_events.status` mapeado a un conjunto **cerrado** de strings pre-partido: p. ej. `scheduled`, `postponed`, `cancelled`, `unknown`. **No** incluir marcadores numéricos ni claves tipo `result_*`. Si el evento está `live` en CDM, fase 1 puede enviar `live` **solo** si PO confirma que el pipeline sigue siendo pre-partido para ese día; si no, tratar como `unknown` y marcar en `diagnostics`. |

**Prohibido** en `event_context` y sub-árbol: cualquier clave que contenga subcadenas listadas en §6.

### 3.4 `processed` (fase 1)

Solo subcampos **whitelisteados**:

| Campo | Obl. | Contenido |
|--------|------|-----------|
| `odds_featured` | Sí | Objeto descrito en §3.4.1. Construido **solo** desde `bt2_odds_snapshot` agregado por mercado/selección/libro. |
| `lineups` | Sí | `{}`, `{ "available": false }`, o `{ "available": true, … }` con agregados seguros (p. ej. `raw_sportmonks_fixtures`); prohibido filtrar marcadores (§6). |
| `h2h` | Sí | Vacío / no disponible, o `{ "available": true, … }` con agregados de duelo desde `bt2_events` terminados (sin claves prohibidas). |
| `statistics` | Sí | Forma reciente (p. ej. cadena W/D/L) por equipo desde `bt2_events`. |
| `team_streaks` | Sí | Rachas derivadas en servidor a partir de la forma. |
| `team_season_stats` | Sí | Sin tabla agregada BT2 hoy: `{ "available": false }` + causa en `fetch_errors`. |
| `odds_all` | No | Omitir en fase 1 o `{}` si el builder unifica; si se omite del whitelist estricto, T-172 no lo espera. **Recomendación:** omitir hasta fase 2. |

#### 3.4.1 Forma de `odds_featured`

Objeto con dos vistas complementarias (paridad con “odds estructurados” v1, pero **catálogo extensible**):

1. **`consensus`** — diccionario **clave = código canónico de mercado** (mismo namespace que ampliará `MarketCanonical` / módulo hermano). Solo aparecen claves para mercados **con al menos una selección** con datos. Ejemplos de forma (medianas por selección, definición T-174):

   - `FT_1X2`: `{ "home": float, "draw": float, "away": float }`
   - `DOUBLE_CHANCE_1X` / `DOUBLE_CHANCE_X2` / `DOUBLE_CHANCE_12` (o un objeto `DOUBLE_CHANCE` con subclaves acordadas en código)
   - `OU_GOALS_2_5`: `{ "over_2_5": float, "under_2_5": float }` (otras líneas goles, p. ej. `OU_GOALS_1_5`, cuando existan en CDM)
   - `OU_CORNERS_*`, `OU_CARDS_*`: estructura análoga over/under por línea acordada
   - `BTTS`: `{ "yes": float, "no": float }` (nombres finales = los que fije el mapeo)

2. **`by_bookmaker`** (opcional): lista de filas `{ "bookmaker", "market_canonical", "selection_canonical", "decimal", "fetched_at" }`. El recorte por evento es **técnico** (tokens/latencia), no regla PO fija — documentar default en runbook BE.

3. **`ingest_meta`** (opcional, **T-190 / refinement**): objeto con `first_fetched_at_iso`, `last_fetched_at_iso`, `distinct_fetch_batches` (ventana de observación en `bt2_odds_snapshot`). **No** sustituye una serie histórica de cuotas por selección: persistir timelines por mercado requeriría diseño nuevo (tabla o job) + ampliación **US-DX-003** y validador **T-172**.

**Reglas si falta dato:**

- Un mercado no aparece en `consensus` si falta alguna pierna requerida para ese mercado.
- El modelo debe elegir **entre mercados presentes** cuál ofrece mejor lectura de valor; no se exige que todo evento tenga todos los mercados.

### 3.5 `diagnostics`

| Campo | Obl. | Tipo | Regla |
|--------|------|------|--------|
| `market_coverage` | Sí | `object` | Mapa `market_canonical` → `bool`: `true` si ese mercado está **completo** en snapshot (todas las selecciones requeridas). Sustituye el modelo rígido `odds_1x2_ok` / `odds_ou25_ok` únicamente. |
| `markets_available` | No | `string[]` | Lista de códigos presentes (aunque incompletos), útil para prompts. |
| `lineups_ok` | Sí | `bool` | `true` si hubo resumen de alineaciones desde raw SportMonks; si no, `false`. |
| `h2h_ok` | Sí | `bool` | `true` si hay agregados H2H consultables en Postgres. |
| `statistics_ok` | Sí | `bool` | `true` si hay forma reciente (W/D/L) para al menos un equipo. |
| `fetch_errors` | Sí | `string[]` | Lista humana corta de fallos de ensamblado; puede ser `[]`. |

## 4. Mapeo mercados CDM → canónico (builder)

- Cada fila `bt2_odds_snapshot` se normaliza a un **`market_canonical`** + **`selection_canonical`** estable (extensión de `normalized_pick_to_canonical` o tabla dedicada).
- Objetivo de ingestión: cubrir **1X2**, **doble oportunidad** (cuando la API lo provea), **O/U goles / corners / tarjetas** (líneas acordadas), **BTTS**, alineado a **D-06-024** / **D-06-025**.
- Hasta que existan filas reales, un mercado simplemente **no** entra en `consensus` y sale `false` en `market_coverage`.

## 5. Compatibilidad con el prompt batch actual

Hoy `_build_ds_input_item` expone un objeto plano (`tournament`, `home_team`, `away_team`, `odds`). **T-175** debe:

1. Sustituir por la forma §3; para retrocompatibilidad del **prompt**, el sistema puede seguir inyectando un resumen de cuotas 1X2 + O/U 2.5 **si existen** dentro de `odds_featured.consensus`, pero el texto del usuario debe instruir al modelo a **comparar mercados** presentes y elegir el de mayor valor.
2. Actualizar `_SYSTEM_BATCH` / `_user_prompt_batch` para referirse a `ds_input[].processed.odds_featured` y `event_context`, sin romper el esquema de salida `picks_by_event` (ampliar mercados permitidos en la salida en la misma US que amplíe canónicos).

## 6. Anti-fuga (D-06-002)

- Toda clave en el subárbol `ds_input[]` debe pasar `assert_no_forbidden_ds_keys` (y lista ampliada en T-172 si PO cierra más términos).
- **No** serializar columnas `result_home`, `result_away` ni derivados de marcador final en ningún campo del ítem.
- **No** usar nombres de clave que contengan (case-insensitive): `result_home`, `result_away`, `final_score`, `fulltime_score`, `match_winner`, `winner_team`, `goals_home`, `goals_away`, `score_ht`, `penalty_shootout`.

## 7. Criterios de aceptación (T-171)

- [ ] Builder (T-174) puede implementar la tabla anterior sin interpretación ambigua.
- [ ] T-172 puede generar un modelo Pydantic que refleje exactamente §3.1–3.5.
- [ ] Ningún campo obligatorio queda sin fuente Postgres o sin regla de relleno explícita arriba.

## 8. Evolución (fuera de fase 1)

- Sidecar SportMonks / scrapers para `lineups`, `h2h`, `statistics`: nuevas US + ampliación whitelist y `contractVersion`.
- Otros deportes: nuevo documento `bt2_ds_input_<sport>_fase1.md` o sección añadida con `sport` discriminador.
