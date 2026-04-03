# Copa Foxkids — Scrapper (SQLite)

Persistencia determinista para el pipeline Copa Foxkids y el agente **juapi-tartara** (SQLite + jobs CLI).

**Guía amplia (propósito, arquitectura, ejecución, parámetros, auditoría SQL, fútbol vs tenis):** [`docs/GUIA_OPERACION_Y_ARQUITECTURA.md`](docs/GUIA_OPERACION_Y_ARQUITECTURA.md).

**BetTracker 2.0 (reestructuración API-first, US y sprints):** [`docs/bettracker2/README.md`](docs/bettracker2/README.md).

**OpenClaw / agentes:** el **contrato** está en **`openclaw.md`** (raíz). El **heartbeat** (pulso, plantilla, qué es) **vive en OC** y en el repo se versiona en **`openclaw/heartbeat.md`** — cárgalo en el contexto/reglas de OpenClaw; valores en vivo en `out/heartbeat.md`. Guardrails de evidencia y coste: **`openclaw/PROMPT_ANTI_ALUCINACION_COSTOS.md`**. Índice: **`openclaw/README.md`**.

## Requisitos
- Python 3.9+
- Playwright con navegadores descargados (si faltan, ejecuta `npx playwright install chromium` o el equivalente para tu entorno)

## Variables
- `DB_PATH` (opcional): ruta del SQLite. Si no se define, `--db` manda; si tampoco, usa `./db/sport-tracker.sqlite3`.
- `INCLUDE_FINISHED` (opcional): `1`/`true` para persistir partidos ya terminados (backtesting). Legado: `ALTEA_INCLUDE_FINISHED` también se acepta.

## Flujo E2E manual

Cada job imprime en consola la estructura de lo que entrega. Para prueba de principio a fin:

**Reset:** `reset_db.py` es **solo para uso humano** en terminal (pruebas desde cero). OpenClaw **no** lo ejecuta; ver `openclaw.md`.

```bash
# 0) Opcional — solo tú en terminal: empezar de 0 (no lo ejecuta OC)
python3 jobs/reset_db.py --db ./db/sport-tracker.sqlite3 -y

# 1) Ingesta (fetch scheduled + persist bundles)
python3 jobs/ingest_daily_events.py --sport football --date 2026-03-20 --db ./db/sport-tracker.sqlite3 --limit 3

# 2) Select candidates (filtra + payload para juapi-tartara)
python3 jobs/select_candidates.py --db ./db/sport-tracker.sqlite3 --daily-run-id 1 -o out/candidates_2026-03-22_select.json

# 3) DS devuelve picks → persist
echo '{"picks":[{"event_id":123,"market":"1X2","selection":"1","picked_value":2.1}]}' > picks.json
python3 jobs/persist_picks.py --daily-run-id 1 --db ./db/sport-tracker.sqlite3 --input-json picks.json

# 4) Validar
python3 jobs/validate_picks.py --db ./db/sport-tracker.sqlite3 --daily-run-id 1
```

O: `./jobs/run_e2e_manual.sh` (incluye reset al inicio; **solo operador local**, no OC — `openclaw.md`).

## Jobs individuales

Los jobs inicializan el esquema automáticamente si no existe.

### 0) Reset DB — solo terminal humana (no OC)
```bash
python3 jobs/reset_db.py --db ./db/sport-tracker.sqlite3 -y
```
No forma parte del pipeline que sigue OpenClaw; ver `openclaw.md`.

### 1) Ingesta diaria (crea `daily_runs`, y persiste snapshots/features)
```bash
python3 jobs/ingest_daily_events.py --sport football --date 2026-03-20 --db ./db/sport-tracker.sqlite3 --limit 3
```

### 2) Select candidates (payload juapi-tartara + inventario del run)
```bash
python3 jobs/select_candidates.py --db ./db/sport-tracker.sqlite3 --daily-run-id 1 -o out/candidates_2026-03-22_select.json
# Hora local de referencia (default America/Bogota): --timezone America/Bogota o env COPA_FOXKIDS_TZ
```
El JSON incluye `run_inventory` (todos los eventos persistidos del run vs `in_ds_input`) y cada ítem de `ds_input` trae `schedule_display` (UTC + local).

### 2b) Event splitter (ventana de kickoff — producción)

Filtra el JSON de `select_candidates` por franja horaria local. **Un** `candidates_{DATE}_select.json` por día; **dos** salidas `exec_08h` / `exec_16h` para las analíticas. Convención: **`openclaw/NAMING_ARTIFACTS.md`**.

```bash
python3 jobs/event_splitter.py -i out/candidates_2026-03-22_select.json -o out/candidates_2026-03-22_exec_08h.json \
  --date 2026-03-22 --slot morning --timezone America/Bogota
```

Atajo: `FECHA=2026-03-22 ./scripts/run_slot_window.sh morning`

### 2c) Lotes para el LLM (timeout / coste)

Con muchos eventos, **no** mandar todo el JSON en una sola llamada. Ver `openclaw/OPTIMIZACION_TOKENS.md`.

```bash
python3 jobs/split_ds_batches.py -i out/candidates_2026-03-22_exec_08h.json \
  -o out/batches/candidates_2026-03-22_exec_08h --chunk-size 4 --slim
# Tras analizar cada batch → merge → render
python3 jobs/merge_telegram_payload_parts.py -i out/payload_morning_batch*.json -o out/telegram_payload.json
```

### 3) Persist picks (idempotente)
```bash
python3 jobs/persist_picks.py --daily-run-id 1 --db ./db/sport-tracker.sqlite3 --input-json picks.json
```

### 4) Validar picks (crea `pick_results` y actualiza `picks.status`)
```bash
python3 jobs/validate_picks.py --db ./db/sport-tracker.sqlite3 --daily-run-id 1
```

### Fuera del pipeline — Mensaje Telegram desde JSON
Detalle y reglas estrictas para OC: **`openclaw.md`** §2 y §3.

```bash
python3 jobs/render_telegram_payload.py -i out/telegram_payload.json -o out/telegram_message.txt
```

El envío a Telegram debe ser **solo** el contenido de `out/telegram_message.txt` (sin reescritura por LLM). Ver `openclaw.md`.

## Contratos

- **OC → DS**: Array de objetos `{ event_id, event_context, processed, diagnostics }` (ver output de select_candidates).
- **DS → OC**: `{ "picks": [ { "event_id", "market", "selection", "picked_value"?, "odds_reference"? } ] }`.

## Notas
- `persist_event_bundle` y `persist_picks` usan constraints e `INSERT OR IGNORE` para evitar duplicados.
- `validate_picks` solo valida picks `pending` que todavía no tengan fila en `pick_results`.

## Scheduler (launchd, macOS)

Atajo: `./run.sh start|stop|restart|status|logs|tick` (ver `./run.sh help`).

1. **Ejecutar un ciclo ahora (sin esperar el reloj):**
   ```bash
   cd /ruta/al/repo
   ./run.sh run-now midnight              # FECHA por defecto = hoy (TZ local del script)
   ./run.sh run-now morning 2026-03-23
   ./run.sh run-now afternoon 2026-03-23
   ./run.sh run-now report                # informe; opcional: días como 3er arg
   ```
2. **Dejar el automático corriendo:** `./run.sh start` (instala `com.copafoxkids.independent.runner` y dispara `scripts/runner_tick.sh` cada 60 s).
3. **Solo horarios de producción por defecto:** `00:00` midnight, `08:00` morning, `16:00` afternoon, `23:55` report (TZ: `COPA_FOXKIDS_TZ` o `America/Bogota`).
4. **Pruebas — cambiar solo los disparos del tick:** en `.env` (mismo formato `HH:MM`):
   ```bash
   COPA_FOXKIDS_TZ=America/Bogota
   COPA_TICK_SLOT_MIDNIGHT=09:05
   COPA_TICK_SLOT_MORNING=09:12
   COPA_TICK_SLOT_AFTERNOON=09:18
   COPA_TICK_SLOT_REPORT=09:24
   ```
   Tras editar `.env`, no hace falta reinstalar launchd; el tick lee `.env` en cada minuto. **Vuelve a comentar o borra estas líneas** cuando termines las pruebas.
5. **Estado y logs:** `./run.sh status` y `./run.sh logs`.
6. **Forzar un tick manual (respeta “una vez por día” por slot):** `./run.sh tick`.

