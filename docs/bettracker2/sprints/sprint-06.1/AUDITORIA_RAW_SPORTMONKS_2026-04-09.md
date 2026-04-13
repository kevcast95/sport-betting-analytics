# Auditoría `raw_sportmonks_fixtures` — 2026-04-09

**Tipo de documento:** registro de **salida BE** + **conclusiones BA** (no sustituye `TASKS.md`; informa diseño de paridad `ds_input`).  
**Relacionado:** [`BE_INSTRUCCION_AUDITORIA_RAW_FIXTURES.md`](./BE_INSTRUCCION_AUDITORIA_RAW_FIXTURES.md), [`V1_SOFASCORE_A_BT2_DS_INPUT_MAPA.md`](./V1_SOFASCORE_A_BT2_DS_INPUT_MAPA.md).  
**Checklist ejecutable:** [`SIGUIENTES_PASOS_POST_AUDITORIA_RAW_SPORTMONKS.md`](./SIGUIENTES_PASOS_POST_AUDITORIA_RAW_SPORTMONKS.md).

---

## 1. Respuesta BE (texto entregado por ejecutor)

### Query A (JSON una línea)

```json
{"total_rows":55222,"distinct_fixture_ids":55222,"min_fixture_date":"2023-08-01","max_fixture_date":"2025-05-31","last_fetched_at":"2026-04-06T16:33:59.547237-05:00"}
```

### Query D (JSON una línea)

```json
{"bt2_events_total":43926,"events_with_raw_row":43497}
```

*(429 eventos CDM sin fila `raw` para su `sportmonks_fixture_id`.)*

### Query B

- CSV: `out/raw_sportmonks_payload_keys.csv` (26 claves).
- **Hallazgo BE:** en todas las filas con `payload` objeto, el conjunto de claves de primer nivel es **idéntico** (cada key con `occurrences = 55222`). No aparece `lineups` en el nivel raíz del JSON; sí `statistics` (array), `participants`, `scores`, `odds`, etc.

**Tabla markdown (key + occurrences):**

| key | occurrences |
|-----|---------------|
| aggregate_id | 55222 |
| details | 55222 |
| events | 55222 |
| group_id | 55222 |
| has_odds | 55222 |
| has_premium_odds | 55222 |
| id | 55222 |
| league | 55222 |
| league_id | 55222 |
| leg | 55222 |
| length | 55222 |
| name | 55222 |
| odds | 55222 |
| participants | 55222 |
| placeholder | 55222 |
| result_info | 55222 |
| round_id | 55222 |
| scores | 55222 |
| season_id | 55222 |
| sport_id | 55222 |
| stage_id | 55222 |
| starting_at | 55222 |
| starting_at_timestamp | 55222 |
| state_id | 55222 |
| statistics | 55222 |
| venue_id | 55222 |

### Query C (4 fixtures: 2 recientes + 2 aleatorias)

No se pegó el payload completo. `payload_json_types` es el **mismo esquema** en las 4 muestras (objeto con las 26 claves: `odds` / `events` / `scores` / `statistics` / `participants` → array; `league` → object; `details` / `aggregate_id` / `group_id` → null en muestras; `has_odds` / `placeholder` / `has_premium_odds` → boolean; resto numérico o string según campo).

| # | fixture_id | fixture_date | fetched_at (ISO) |
|---|------------|--------------|------------------|
| 1 (reciente) | 19348514 | 2025-05-31 | 2026-04-06T16:33:59.547237-05:00 |
| 2 (reciente) | 19348516 | 2025-05-31 | 2026-04-06T16:33:59.547237-05:00 |
| 3 (random) | 19145009 | 2025-03-22 | 2026-04-06T15:52:39.115119-05:00 |
| 4 (random) | 19375110 | 2025-03-30 | 2026-04-06T15:52:39.115119-05:00 |

**Ejemplo compacto (fixture 19348514)** — `payload_sample_redacted` en script: `json.dumps(payload)[:4000]` + truncado; incluye `name`, inicio de `odds[]`, etc.

```json
{
  "fixture_id": 19348514,
  "fixture_date": "2025-05-31",
  "fetched_at": "2026-04-06T16:33:59.547237-05:00",
  "payload_top_level_keys": ["id","leg","name","odds","events","league","length","scores","details","group_id","has_odds","round_id","sport_id","stage_id","state_id","venue_id","league_id","season_id","statistics","placeholder","result_info","starting_at","aggregate_id","participants","has_premium_odds","starting_at_timestamp"],
  "payload_json_types": { "id": "number", "leg": "string", "name": "string", "odds": "array", "events": "array", "league": "object", "length": "number", "scores": "array", "details": "null", "group_id": "null", "has_odds": "boolean", "round_id": "number", "sport_id": "number", "stage_id": "number", "state_id": "number", "venue_id": "number", "league_id": "number", "season_id": "number", "statistics": "array", "placeholder": "boolean", "result_info": "string", "starting_at": "string", "aggregate_id": "null", "participants": "array", "has_premium_odds": "boolean", "starting_at_timestamp": "number" }
}
```

Las otras tres filas comparten las mismas `payload_top_level_keys` y el mismo mapa de tipos.

### Notas del BE (para BA)

- **Lineups:** no hay clave `lineups` en la raíz; habría que inspeccionar `participants`, `statistics` u otros paths.
- **`processed.statistics`:** existe `statistics` (array) en el payload; auditar JSON completos para compatibilidad con **D-06-002** (no filtrar resultado prohibido al LLM en pre-partido).
- **Cruce CDM:** ~98,8% de `bt2_events` con fila raw.

### §4 — Resultados BE (lineups en payload) — 2026-04-10

**§4.1 — Conteos subcadena** (equivalente ILIKE por fila; **muestra aleatoria n=250** sobre 55 222 filas; JSON truncado a 6 MiB/fila si aplica; proyección `round(total×hits/n)`). Conteos **globales** con `payload::text ILIKE` en tabla completa no se ejecutaron aquí: orden de **horas** en este volumen; SQL listo en `out/lineup_probe_paths.json` → `section_4_1.runbook_exact_sql` o `RUN_EXACT_ILIKE=1` en `scripts/bt2_lineup_payload_probe.py`.

| patrón | hits en muestra (n=250) | proyección ~corpus |
|--------|-------------------------|---------------------|
| `%lineup%` (lineup) | 0 | 0 |
| `%formation%` (formation) | 0 | 0 |
| `%sidelined%` (sidelined) | 0 | 0 |
| `%injur%` (injur) | 230 | ~50 804 |
| `%missing%` (missing) | 0 | 0 |

La coincidencia `injur` se explica por subcadena en **`injured`** (p. ej. `events[i].injured`), no por texto tipo “injury report” útil para XI.

**§4.2 — Probe recursivo** (`scripts/bt2_lineup_payload_probe.py`): salida `out/lineup_probe_paths.json` — 10 `fixture_id` (3 upcoming, 3 finished, 4 random). Rutas útiles para **lineup_summary v1:** ninguna con titulares/formación; lo detectado son claves **`events[n].injured`** (típicamente `null` en la muestra).

**Conclusión (2 párrafos):**

1. **No construible** un `lineup_summary` análogo a v1 (`lineups_processor` / SofaScore) desde **`raw_sportmonks_fixtures.payload` tal como está ingestado:** no hay claves top-level ni ramas con `lineup`, `formation`, `sidelined`, `missing` en la muestra global; la única señal masiva es el prefijo **`injur` → `injured`** en el timeline `events[]`, insuficiente para 11 titulares, formación o bajas estructuradas como en v1.

2. **Path más prometedor (parcial y débil):** `events[*].injured` podría, si en otros fixtures tuviera datos no nulos, aportar una pista de lesionados; no sustituye endpoint/dataset de alineaciones. Hasta nueva ingesta o API SportMonks dedicada, el builder debe mantener **`lineups.available: false`** y **diagnostics** con causa explícita (**§4.3** / `V1_SOFASCORE_A_BT2_DS_INPUT_MAPA.md` §7).

**§4.3 — Gap documentado:** ver mapa v1 §7; **no** inventar datos en el builder.

---

## 2. Conclusiones BA (síntesis para diseño)

- **Corpus sólido:** ~55k filas, esquema **homogéneo** (26 keys siempre) → ETL predecible.
- **Odds:** `odds[]` en raw **y** `bt2_odds_snapshot`; definir **fuente de verdad** y evitar contradicciones en el builder.
- **Estadísticas:** `statistics` en raíz permite acercarse al shape de `process_statistics` / `match_performance` tras inspección interna y reglas anti-fuga.
- **Lineups estilo SofaScore:** **no demostrado** en raíz; depende de **búsqueda en profundidad** o de **otra fuente** (ver instrucción §4 y checklist).
- **H2H / forma:** seguir usando **`bt2_events`** histórico + resultados; el raw refuerza contexto de fixture.
- **429 sin raw:** backfill o `diagnostics.raw_fixture_missing` en builder.

---

## 3. Siguientes pasos técnicos (resumen)

Detalle y checkboxes: [`SIGUIENTES_PASOS_POST_AUDITORIA_RAW_SPORTMONKS.md`](./SIGUIENTES_PASOS_POST_AUDITORIA_RAW_SPORTMONKS.md).

1. **Búsqueda recursiva** en el JSON (lineup, formation, sidelined, injur, missing) para 5–10 `fixture_id` → informe `path → tipo → snippet`. **Hecho** — ver §4 y `out/lineup_probe_paths.json`.
2. **Volcar 1–2 payloads completos** (fixture programado vs terminado) en `out/` redactados → diseño mapper `statistics[]` → shape tipo `process_statistics`. **Pendiente** (checklist ítem 3 en `SIGUIENTES_PASOS_…`).
3. **429 eventos sin raw:** lista `sportmonks_fixture_id` + job backfill o marca en builder. **Pendiente** (checklist ítem 4 en `SIGUIENTES_PASOS_…`).

---

## 4. Instrucción BE — Validar si se puede construir `lineups` desde este `payload`

**Objetivo:** responder **sí/no/partial** con evidencia: ¿existe en `raw_sportmonks_fixtures.payload` información suficiente para poblar un **`lineup_summary`** análogo a `processors/lineups_processor.py` (formación, titulares, bajas, etc.)?

### 4.1 Enfoque A — SQL + `jsonb_path_query` / texto (exploratorio rápido)

PostgreSQL no busca recursiva “fácil” en SQL puro; sirve para **primer filtro**:

```sql
-- ¿Algún payload contiene la subcadena 'lineup' (case insensitive)?
SELECT COUNT(*) AS rows_with_lineup_substring
FROM raw_sportmonks_fixtures
WHERE payload::text ILIKE '%lineup%';

-- Igual para otras palabras
SELECT COUNT(*) FROM raw_sportmonks_fixtures WHERE payload::text ILIKE '%formation%';
SELECT COUNT(*) FROM raw_sportmonks_fixtures WHERE payload::text ILIKE '%sidelined%';
SELECT COUNT(*) FROM raw_sportmonks_fixtures WHERE payload::text ILIKE '%injur%';
SELECT COUNT(*) FROM raw_sportmonks_fixtures WHERE payload::text ILIKE '%missing%';
```

**Entregable:** tabla markdown con los 5 conteos. Si **todos 0**, la probabilidad de lineups en JSON es baja (o con nombres distintos).

### 4.2 Enfoque B — Script Python (obligatorio si A no basta)

1. Cargar **10 `fixture_id`** variados: 3 futuros (`state_id` típico no terminado si se puede filtrar), 3 recientes terminados, 4 aleatorios del corpus.
2. Para cada uno, recorrer **recursivamente** el `payload` (dict/list) y registrar cada **path** (p. ej. `participants.0.meta.lineups`) donde:
   - el **nombre de clave** contiene (case insensitive): `lineup`, `formation`, `squad`, `sidelined`, `injur`, `missing`, `suspension`;
   - o el **valor string** contiene esas subcadenas (longitud &lt; 500 para no explotar).
3. **Salida:** archivo `out/lineup_probe_paths.json` (array de `{fixture_id, path, value_type, snippet}`) + **2 párrafos** en markdown: conclusión **construible / no / solo parcial** y ejemplo de path más prometedor.

**Criterio “construible”:** al menos un path estable que permita extraer **bajas** o **11 titulares** por lado con tasa razonable en muestra de 50 fixtures (ampliar muestra si hace falta).

### 4.3 Si el resultado es “no”

Documentar en [`V1_SOFASCORE_A_BT2_DS_INPUT_MAPA.md`](./V1_SOFASCORE_A_BT2_DS_INPUT_MAPA.md) § gap y abrir decisión: **endpoint SportMonks aparte**, **tabla nueva**, o **`lineups.available: false`** con causa real en `diagnostics` hasta nueva ingesta.

---

*Documento generado a partir de la entrega BE y análisis BA en el mismo día.*
