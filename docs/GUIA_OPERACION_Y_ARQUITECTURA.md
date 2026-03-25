# ALTEA / Copa Foxkids — Guía de arquitectura y operación

Documento para **dueño de producto y operadores**: qué es el sistema, cómo está armado, cómo se ejecuta y cómo **auditarlo sin depender de un agente de IA**. Actualizado al estado del repo (marzo 2026).

---

## 1. Propósito y meta

- **Qué hace:** ingesta calendario y datos de partidos (principalmente desde SofaScore vía Playwright), guarda un **snapshot por día y deporte** en SQLite, filtra **candidatos** aptos para análisis, envía contexto a un **modelo (DeepSeek)** y materializa **picks** con cuotas y metadatos. Opcionalmente **Telegram** entrega el mensaje formateado; la **API + web** permiten tablero, seguimiento por usuario y combinadas sugeridas.
- **Meta operativa:** decisiones **pre-partido** en ventanas definidas (p. ej. mañana / tarde en hora Colombia), con trazabilidad en DB y validación posterior de resultados (`validate_picks`, `pick_results`).
- **No es:** un bookmaker; la fuente de verdad del mercado en vivo sigue siendo el proveedor externo y el momento exacto del análisis importa (ver §6).

---

## 2. Respuesta directa: ¿tenis y fútbol al mismo tiempo?

**No automáticamente.**

| Aspecto | Fútbol | Tenis |
|--------|--------|--------|
| Fila en `daily_runs` | `(run_date, sport='football')` | `(run_date, sport='tennis')` — **otra fila el mismo día** |
| Ingesta | `ingest_daily_events.py --sport football` → API scheduled-events | `ingest_daily_events.py --sport tennis` → lógica en `core/tennis_daily_schedule.py` |
| Artefactos `out/` | `candidates_{FECHA}_select.json`, etc. | Mismo patrón pero con sufijo **`_tennis`** (p. ej. `candidates_2026-03-25_tennis_select.json`) para no pisar fútbol |
| Cron / `runner_tick.sh` | Llama `independent_runner.py` **sin** `--sport` → **solo `football`** | Hay que invocar explícitamente `--sport tennis` (mismo `independent_runner.py`) en otro horario o script |

Conclusión: en la **máquina con launchd** tal como está el repo, solo corre el pipeline **fútbol**. Tenis es **paralelo en datos** pero **manual o con cron adicional** que pases `--sport tennis`.

---

## 3. Mapa del repositorio

| Ruta | Rol |
|------|-----|
| `jobs/` | CLI del pipeline: ingest, select, splitter, batches, DeepSeek, merge, render, persist picks, validar, reportes, runner |
| `core/` | HTTP SofaScore, extracción de payloads, scraper de bundles, reglas de schedule tenis, contratos |
| `processors/` | Transforman snapshots crudos → fragmentos que acaban en `event_features` |
| `db/` | `schema.sql`, migraciones, repos SQLite, `config.py` |
| `apps/api/` | FastAPI: lectura/escritura tracking, board, dashboard |
| `apps/web/` | React (Vite): tablero de runs/picks, tracking |
| `openclaw/` | Contrato para agentes, cron Colombia, naming de artefactos, prompts |
| `openclaw.md` (raíz) | **Fuente de verdad** de lo que un agente (OpenClaw) debe y no debe ejecutar |
| `scripts/` | `runner_tick.sh`, wrappers midnight/window/full_day, reportes |
| `out/` | JSON de candidatos, batches, payloads, mensajes Telegram, estado del tick (`out/state/`) |

---

## 4. Modelo de datos (mínimo imprescindible)

- **`daily_runs`:** un run por `(run_date, sport)`. `created_at_utc` es la **clave** que alinea todas las filas de `event_features` de ese run (`captured_at_utc` = ese timestamp).
- **`event_snapshots`:** JSON bruto por `event_id`, dataset (event, odds, statistics, …) y `captured_at_utc`.
- **`event_features`:** JSON ya procesado (contexto + diagnostics) que consume `select_candidates`.
- **`picks`:** apuesta sugerida persistida; `idempotency_key` evita duplicados al re-ejecutar `persist_picks`.
- **`pick_results`:** resultado tras `validate_picks` (win/loss/pending, evidencia).
- **Tracking:** `users`, `user_pick_decisions`, `suggested_combos`, etc. (tablero en web).

Auditar un día concreto: siempre identifica **`daily_run_id`** y **`sport`**.

---

## 5. Pipeline end-to-end (orden lógico)

### 5.1 Medianoche — inventario + candidatos base (runner “midnight”)

1. **`ingest_daily_events.py`**  
   Crea/completa el `daily_run`, lista `event_id` del día, persiste bundles (`persist_event_bundle` → snapshots + features).

2. **`select_candidates.py`**  
   Lee `event_features` con el `captured_at_utc` del run; aplica contrato Tier A/B, exclusiones (partido terminado, ya iniciado, reglas tenis, etc.); escribe JSON con `ds_input` + `run_inventory`.

3. **Telegram (opcional):** mensaje corto con conteo (runner independiente).

### 5.2 Mañana / tarde — ventana de kickoff + modelo (runner “window”)

4. **`event_splitter.py`**  
   Filtra candidatos por **franja local** (`morning` / `afternoon`) y fecha calendario.

5. **`split_ds_batches.py`**  
   Parte el JSON en lotes (`--slim`, `--chunk-size`) para no saturar al LLM.

6. **`deepseek_batches_to_telegram_payload_parts.py`**  
   Llama a DeepSeek por lote; genera partes de payload.

7. **`merge_telegram_payload_parts.py`**  
   Une en un solo `telegram_payload.json`.

8. **`allocate_bankroll.py`**  
   Enriquece el payload con montos sugeridos (bankroll / exposición).

9. **`render_telegram_payload.py`**  
   Produce `telegram_message.txt` (lo que debe ir a Telegram **sin reescritura**).

10. **`persist_picks.py --telegram-payload ...`**  
    Inserta picks en SQLite (idempotente).

11. **`send_telegram_message.py`**  
    Envía el archivo de texto (requiere credenciales en `.env`).

### 5.3 Después (operación / cierre)

- **`validate_picks.py`:** cuando el partido cerró, actualiza resultados.
- **`suggest_combos_for_run.py`** o la API “regenerar combinadas”: parlays sugeridos.
- **`report_effectiveness.py`:** métricas agregadas (el cron nocturne puede disparar `run_effectiveness_report.sh`).

### 5.4 Modo manual útil en pruebas

- **`independent_runner.py --mode full_day`:** analiza el día completo (slot `full_day`), suele persistir picks salvo `--skip-persist`.
- Comandos sueltos: ver `README.md` y `openclaw.md`.

---

## 6. Cómo se ejecuta en la práctica

### 6.1 Automático (macOS launchd)

- **`./run.sh start`** instala el servicio que cada minuto ejecuta **`scripts/runner_tick.sh`**.
- A la hora configurada (por defecto **00:00**, **08:00**, **16:00**, **23:55** en `America/Bogota`):
  - `00:00` → `run_independent_midnight.sh` → ingest + select + aviso (**fútbol**).
  - `08:00` / `16:00` → `run_independent_window.sh` → ventana + DeepSeek + merge + render + persist + Telegram (**fútbol**, `--persist-picks`).
- **Pruebas:** en `.env`, `COPA_TICK_SLOT_MIDNIGHT=09:05` (etc.) desplaza los disparos sin cambiar código.

### 6.2 Manual (una línea típica)

Desde la raíz del repo, con `.env` cargado (`set -a; source .env; set +a`) para DeepSeek/Telegram:

```bash
# Fútbol, hoy
python3 jobs/independent_runner.py --mode midnight --date "$(date +%Y-%m-%d)"

# Tenis mismo día (segundo pipeline)
python3 jobs/independent_runner.py --mode midnight --sport tennis --date "$(date +%Y-%m-%d)"
python3 jobs/independent_runner.py --mode window --slot morning --sport tennis --date "$(date +%Y-%m-%d)" --persist-picks
```

Ajusta `--db` si no usas la ruta por defecto (§7).

---

## 7. Parametrización (variables y flags)

### 7.1 Rutas y zona horaria

| Variable / flag | Uso |
|-----------------|-----|
| `DB_PATH` o `jobs/* --db` | SQLite (default histórico en docs: `db/sport-tracker.sqlite3`; en tu máquina puede ser `db/app.sqlite` — **usa la misma ruta que la API y la web**) |
| `COPA_FOXKIDS_TZ` | Zona para ticks y textos locales (default `America/Bogota`) |
| `COPA_TICK_SLOT_*` | Horas de prueba para launchd |

### 7.2 Ingesta

| Variable / flag | Uso |
|-----------------|-----|
| `--include-finished` / `INCLUDE_FINISHED=1` | Persiste partidos ya terminados (backtest; no operativo típico) |
| `ALTEA_ALLOW_DIVERGENT_INGEST_DATE=1` | Permite `--date` muy lejana del día actual (anti typo) |

### 7.3 Selección de candidatos (`select_candidates.py`)

| Variable / flag | Uso |
|-----------------|-----|
| `--analysis-at-utc ISO` | Hora de referencia para “ya empezó” / lead time (producción: alinear ~08:00 local) |
| `--allow-started` / `--allow-finished` | Solo depuración o backtest |
| `--timezone` / `COPA_FOXKIDS_TZ` | `schedule_display` local en el JSON |
| `ALTEA_TENNIS_MIN_LEAD_MINUTES` | Margen mínimo antes del inicio (default 45) |
| `ALTEA_TENNIS_EXCLUDE_LOW_ITF` | Excluye ITF bajo por regex (default activo) |
| `ALTEA_TENNIS_EXCLUDE_TOURNAMENT_REGEX` | Regex de torneos a excluir |

### 7.4 DeepSeek / tenis en merge

| Variable | Uso |
|----------|-----|
| `DEEPSEEK_*` / `DS_*` | Credenciales y modelo (ver `.env` de ejemplo en el equipo) |
| `ALTEA_TENNIS_REQUIRE_SCRAPED_ODDS` | Exigir cuota scrapeada para pick tenis |
| `ALTEA_TENNIS_ALLOWED_MARKETS` | Mercados permitidos |

### 7.5 Tenis — ingesta y catálogo

| Variable | Uso |
|----------|-----|
| `ALTEA_TENNIS_MVP_FILTER` | Filtra eventos MVP en schedule tenis |
| `ALTEA_TENNIS_PRIORITY_COUNTRY` | País para torneos por defecto en registry |
| `ALTEA_TENNIS_REGISTRY_CACHE` | Cache del catálogo global |

Detalle de endpoints tenis: `openclaw/TENNIS_ENDPOINTS_ROADMAP.md`.

---

## 8. Auditoría sin IA — checklist

### 8.1 “¿Qué run es hoy?”

```sql
SELECT daily_run_id, run_date, sport, status, created_at_utc
FROM daily_runs
ORDER BY daily_run_id DESC
LIMIT 20;
```

### 8.2 “¿Cuántos eventos ingresó ese run?”

Sustituye `CAPTURED` por `created_at_utc` del run y `SPORT` por `football` o `tennis`:

```sql
SELECT COUNT(*) FROM event_features
WHERE captured_at_utc = 'CAPTURED' AND sport = 'SPORT';
```

### 8.3 “¿Qué archivo de candidatos corresponde?”

En `out/`:

- Fútbol: `candidates_{YYYY-MM-DD}_select.json`
- Tenis: `candidates_{YYYY-MM-DD}_tennis_select.json`

Abre el JSON y revisa `run_inventory` vs `ds_input`.

### 8.4 “¿Se generaron picks?”

```sql
SELECT pick_id, event_id, market, selection, status, created_at_utc
FROM picks
WHERE daily_run_id = ?
ORDER BY pick_id;
```

### 8.5 “¿El tick ya corrió hoy?”

Archivos en `out/state/`: `last_midnight.txt`, `last_08h.txt`, `last_16h.txt` (contienen la fecha del último run exitoso por slot).

### 8.6 Logs launchd

`./run.sh logs` o `out/logs/launchd_runner.*.log`.

### 8.7 Efectividad

`out/reports/effectiveness_latest.json` tras `report_effectiveness.py` o el script shell de reporte.

---

## 9. Dónde cambiar qué (mapa para desarrollo)

| Necesidad | Dónde tocar |
|-----------|-------------|
| Más/menos eventos en ingesta tenis | `core/tennis_daily_schedule.py`, `jobs/ingest_daily_events.py` |
| Filtros pre-modelo (ITF, empezado, vivo, terminado) | `jobs/select_candidates.py` |
| Ventanas horarias mañana/tarde | `jobs/event_splitter.py`, `scripts/run_slot_window.sh` |
| Contrato hacia el LLM / limpieza de salida | `jobs/deepseek_batches_to_telegram_payload_parts.py`, `core/*contract*` |
| Formato Telegram | `jobs/render_telegram_payload.py` |
| Inserción / idempotencia de picks | `jobs/persist_picks.py`, `db/repositories/picks_repo.py` |
| Validación contra marcador | `jobs/validate_picks.py` |
| API REST | `apps/api/main.py`, `apps/api/schemas.py` |
| UI tablero / tracking | `apps/web/src/pages/`, `apps/web/src/components/` |
| Reglas para agentes externos | `openclaw.md` |

---

## 10. Documentos que ya existían (no duplicar esfuerzo)

- **`README.md`** — flujo E2E, lista de jobs, scheduler.
- **`openclaw.md`** — contrato estricto para OpenClaw.
- **`openclaw/CRON_COLOMBIA.md`** — tabla horaria y ejemplos cron.
- **`openclaw/NAMING_ARTIFACTS.md`** — nombres de archivos en `out/`.
- **`openclaw/OPTIMIZACION_TOKENS.md`** — lotes y coste LLM.

---

## 11. Inconsistencias a tener en cuenta

- La documentación histórica cita `db/sport-tracker.sqlite3`; tu entorno puede usar **`db/app.sqlite`**. Lo importante es **una sola ruta** para jobs, API y web.
- El **cron documentado en `openclaw/CRON_COLOMBIA.md`** es conceptual; la implementación local concreta es **`runner_tick.sh` + `independent_runner.py`** (solo fútbol salvo que añadas líneas para tenis).

Si quieres un siguiente paso de producto, lo más útil suele ser: **duplicar en `runner_tick.sh` (o un segundo plist) las dos ventanas para `--sport tennis`**, con los mismos horarios o otros acordados.
