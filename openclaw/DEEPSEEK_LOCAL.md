# Ejecución local (sin OpenClaw) — DeepSeek + Telegram

Objetivo: emular el flujo de OpenClaw para probar 08:00 / 16:00 sin Gateway/OC.

### Requisitos
- `DEEPSEEK_API_KEY` (env var)
- `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` (env vars)

### Flujo para una ventana (ej. morning/exec_08h)

Supón `DATE=YYYY-MM-DD` y ejecuta desde la raíz del repo `scrapper`:

1) `select_candidates` (usa la `daily_run_id` que corresponda):
```bash
python3 jobs/select_candidates.py --db ./db/sport-tracker.sqlite3 --daily-run-id N -o "out/candidates_${DATE}_select.json"
```

2) `event_splitter`:
```bash
python3 jobs/event_splitter.py -i "out/candidates_${DATE}_select.json" -o "out/candidates_${DATE}_exec_08h.json" \
  --date "${DATE}" --slot morning --timezone America/Bogota
```

3) Lotes (tokens):
```bash
python3 jobs/split_ds_batches.py -i "out/candidates_${DATE}_exec_08h.json" \
  -o "out/batches/candidates_${DATE}_exec_08h" --chunk-size 4 --slim
```

4) DeepSeek → parciales `telegram_payload`:
```bash
python3 jobs/deepseek_batches_to_telegram_payload_parts.py \
  --input-glob "out/batches/candidates_${DATE}_exec_08h_batch*.json" \
  --date "${DATE}" --exec-id exec_08h \
  --model deepseek-chat
```

5) Merge + render:
```bash
python3 jobs/merge_telegram_payload_parts.py \
  -i out/payload_${DATE}_exec_08h_part*.json -o out/telegram_payload.json

python3 jobs/render_telegram_payload.py -i out/telegram_payload.json -o out/telegram_message.txt
```

6) Enviar a Telegram:
```bash
python3 jobs/send_telegram_message.py --message-file out/telegram_message.txt
```

### 00:00 (ingest + mensaje de conteo)
Para el ingest, usa `ingest_daily_events.py` como siempre, y luego calcula el conteo con un query sobre `event_features` (si quieres lo agrego como job).

