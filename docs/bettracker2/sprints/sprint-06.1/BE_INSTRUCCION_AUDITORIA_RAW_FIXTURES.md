# Instrucción BE — Auditoría `raw_sportmonks_fixtures` para paridad `ds_input`

**Para:** ejecutor backend / datos.  
**Objetivo:** que BA/PM o el agente puedan **concluir** qué caminos hay para rellenar `processed.statistics`, `lineups`, etc. sin acceso directo a tu Postgres.  
**Salida:** pegar en el chat (o adjuntar archivo) los **bloques indicados abajo**, en el **formato pedido**.

---

## 0. Conexión

Usar la misma `BT2_DATABASE_URL` que el API. Cliente: `psql`, DBeaver, o:

```bash
psql "$BT2_DATABASE_URL" -v ON_ERROR_STOP=1
```

---

## 1. Conteo y frescura

**Query A — existencia y rango de fechas**

```sql
SELECT
  COUNT(*) AS total_rows,
  COUNT(DISTINCT fixture_id) AS distinct_fixture_ids,
  MIN(fixture_date) AS min_fixture_date,
  MAX(fixture_date) AS max_fixture_date,
  MAX(fetched_at) AS last_fetched_at
FROM raw_sportmonks_fixtures;
```

**Formato de salida para el chat:** un único **bloque markdown** con tabla o JSON:

```json
{ "total_rows": ..., "distinct_fixture_ids": ..., "min_fixture_date": "...", "max_fixture_date": "...", "last_fetched_at": "..." }
```

---

## 2. Claves de primer nivel en `payload` (agregado)

**Query B — frecuencia de keys top-level** (ajustar si `payload` no es objeto en alguna fila)

```sql
SELECT
  key,
  COUNT(*) AS occurrences
FROM raw_sportmonks_fixtures,
     LATERAL jsonb_object_keys(payload) AS key
GROUP BY key
ORDER BY occurrences DESC, key;
```

**Formato de salida:** tabla markdown **completa** (todas las filas) o CSV pegable. Si hay >80 keys, pegar **top 40** + línea `"(... N keys más)"` y adjuntar CSV al PR o archivo en `out/` del repo.

---

## 3. Muestra de estructura (2 fixtures recientes + 2 aleatorios)

**Query C — fixture reciente**

```sql
(SELECT fixture_id, fixture_date, fetched_at, payload
 FROM raw_sportmonks_fixtures
 WHERE payload IS NOT NULL AND jsonb_typeof(payload) = 'object'
 ORDER BY fetched_at DESC NULLS LAST
 LIMIT 2)
UNION ALL
(SELECT fixture_id, fixture_date, fetched_at, payload
 FROM raw_sportmonks_fixtures
 WHERE payload IS NOT NULL AND jsonb_typeof(payload) = 'object'
 ORDER BY random()
 LIMIT 2);
```

**Formato de salida (importante para análisis):**

- **No** pegar el `payload` completo si supera ~15 KB por fila.
- Para cada una de las **4** filas, pegar un objeto JSON con esta forma:

```json
{
  "fixture_id": 12345678,
  "fixture_date": "2026-04-01",
  "fetched_at": "...",
  "payload_top_level_keys": ["participants", "scores", "..."],
  "payload_json_types": { "participants": "array", "scores": "object" },
  "payload_sample_redacted": { "...": "solo 1-2 niveles de ejemplo, sin PII innecesaria" }
}
```

Cómo generar `payload_json_types` en SQL (ejemplo para una fila; el BE puede hacerlo con script Python si es más fácil):

```sql
SELECT fixture_id,
       jsonb_object_keys(payload) AS k,
       jsonb_typeof(payload -> jsonb_object_keys(payload)) AS t
FROM raw_sportmonks_fixtures
WHERE fixture_id = <REEMPLAZAR>;
```

Si es más rápido: **script Python** que lea las 4 filas y imprima el JSON de arriba (`payload.keys()`, tipos, y `json.dumps(payload, indent=2)[:4000]` truncado).

---

## 4. Cobertura cruzada con `bt2_events`

**Query D — fixtures con fila raw vs evento CDM**

```sql
SELECT
  COUNT(*) AS bt2_events_total,
  COUNT(r.fixture_id) AS events_with_raw_row
FROM bt2_events e
LEFT JOIN raw_sportmonks_fixtures r ON r.fixture_id = e.sportmonks_fixture_id;
```

**Formato de salida:** JSON de una línea con los dos números.

---

## 5. Entrega al BA / agente

1. Ejecutar **A, B, D** siempre.  
2. Ejecutar **C** (o script equivalente) y entregar los **4 resúmenes JSON** compactos.  
3. Si Query B devuelve muchas keys: adjuntar **`out/raw_sportmonks_payload_keys.csv`** en el repo o zip y mencionar la ruta en el mensaje.

**Título sugerido del mensaje al PO/BA:**  
`Auditoría raw_sportmonks_fixtures — <entorno> — <fecha ISO>`

Con eso se puede mapear rápido qué bloques de v1 (`statistics`, `lineups`, …) tienen análogo en `payload` y qué hay que derivar solo desde `bt2_events` histórico.

---

## Resultado ejecutado (2026-04-09)

Ver registro completo + conclusiones BA + **instrucción fase lineups**:

- [`AUDITORIA_RAW_SPORTMONKS_2026-04-09.md`](./AUDITORIA_RAW_SPORTMONKS_2026-04-09.md)
- Checklist siguiente: [`SIGUIENTES_PASOS_POST_AUDITORIA_RAW_SPORTMONKS.md`](./SIGUIENTES_PASOS_POST_AUDITORIA_RAW_SPORTMONKS.md)
