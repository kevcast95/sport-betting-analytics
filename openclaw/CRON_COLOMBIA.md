# Cron — producción (America/Bogota)

Horario acordado para **prueba de campo real**:

| Hora | Qué hace |
|------|-----------|
| **00:00** | Ingesta del **día calendario** que acaba de empezar (todos los partidos del día en el `daily_run`). |
| **08:00** | Análisis **ventana mañana** + Telegram (kickoff local `[00:00, 16:00)` en ese día). |
| **16:00** | Análisis **ventana tarde** + Telegram (kickoff local `[16:00, 24:00)` en ese día). |

Zona: **`America/Bogota`**. El host que ejecute `cron` debe usar esa TZ **o** cada línea debe exportar `TZ=America/Bogota` para que `date` y las horas coincidan.

---

## Secuencia por job (cada día)

Variables de ejemplo (ajusta rutas):

```bash
REPO=/ruta/a/scrapper
DB=$REPO/db/sport-tracker.sqlite3
export TZ=America/Bogota
DATE=$(date +%Y-%m-%d)
```

### 00:00 — Daily run (inventario)

```bash
cd "$REPO" && python3 jobs/ingest_daily_events.py --sport football --date "$DATE" --db "$DB"
# Guardar daily_run_id del log o consulta SQLite → variable DAILY_RUN_ID
```

Luego (mismo día, cuando tengas `DAILY_RUN_ID`):

```bash
python3 jobs/select_candidates.py --db "$DB" --daily-run-id "$DAILY_RUN_ID" -o out/candidates_${DATE}_select.json
```

### 08:00 — Ventana mañana

```bash
python3 jobs/event_splitter.py -i out/candidates_${DATE}_select.json -o out/candidates_${DATE}_exec_08h.json \
  --date "$DATE" --slot morning --timezone America/Bogota
```

**Antes del modelo (recomendado, evita timeout / quema de tokens):** partir en lotes:

```bash
python3 jobs/split_ds_batches.py -i out/candidates_${DATE}_exec_08h.json \
  -o out/batches/candidates_${DATE}_exec_08h --chunk-size 4 --slim
```

OC / modelo: por cada `*_batchNNofMM.json`, generar un **parcial** `telegram_payload` (solo `events` de ese lote); al terminar todos:

```bash
python3 jobs/merge_telegram_payload_parts.py -i out/payload_${DATE}_exec_08h_part*.json -o out/telegram_payload.json
python3 jobs/render_telegram_payload.py -i out/telegram_payload.json -o out/telegram_message.txt
```

Envío a Telegram = **texto** de `telegram_message.txt`. Ver **`openclaw/OPTIMIZACION_TOKENS.md`** y **`openclaw/NAMING_ARTIFACTS.md`**.

### 16:00 — Ventana tarde

```bash
python3 jobs/event_splitter.py -i out/candidates_${DATE}_select.json -o out/candidates_${DATE}_exec_16h.json \
  --date "$DATE" --slot afternoon --timezone America/Bogota
```

Mismo flujo que la mañana: **mismo** `candidates_${DATE}_select.json` de entrada al splitter; salida `exec_16h`; `split_ds_batches` con prefijo `out/batches/candidates_${DATE}_exec_16h`, etc.

---

## Ejemplo `crontab` (el servidor debe tener `python3` y el repo)

```cron
TZ=America/Bogota
0 0 * * * cd /ruta/a/scrapper && /usr/bin/python3 jobs/ingest_daily_events.py --sport football --date "$(date +\%Y-\%m-\%d)" --db ./db/sport-tracker.sqlite3 >> out/cron_ingest.log 2>&1
```

Las líneas de **08:00** y **16:00** suelen invocar un **wrapper** que: lee el último `daily_run_id`, ejecuta `select_candidates` si aún no existe el JSON del día, luego `event_splitter` y llama a OC o a tu orquestador. No hardcodeamos `DAILY_RUN_ID` en crontab sin script; conviene `jobs/run_slot.sh` (ver abajo).

---

## Wrapper en el repo

Tras tener `out/candidates_YYYY-MM-DD_select.json`:

```bash
FECHA=2026-03-21 ./scripts/run_slot_window.sh morning
FECHA=2026-03-21 ./scripts/run_slot_window.sh afternoon
```

OC no configura el `cron` del sistema por sí solo: **instala las líneas** en el host o usa el scheduler de OpenClaw con las mismas horas y `TZ=America/Bogota`.
