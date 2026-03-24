# Sistema independiente (sin OpenClaw) — Semana 1

Objetivo: probar eficacia real 7 días con DeepSeek + Telegram, reduciendo variables de OC/Gateway.

## Variables de entorno

Ruta recomendada para secretos locales:

```text
/Users/kevcast/Documents/Projects/scrapper/.env
```

Contenido esperado en `.env`:

```bash
DEEPSEEK_API_KEY="..."
DS_CHAT_MODEL="deepseek-chat"
DS_ANALYSIS_MODEL="deepseek-reasoner"
TELEGRAM_BOT_TOKEN="..."
TELEGRAM_CHAT_ID="..."
COPA_FOXKIDS_TZ="America/Bogota"
DS_MAX_TOKENS="1200"
DS_TIMEOUT_SEC="180"
DS_MAX_RETRIES="1"
```

Cargar variables antes de correr scripts:

```bash
cd /Users/kevcast/Documents/Projects/scrapper
./scripts/bootstrap_env.sh
```

También puedes exportarlas manualmente:

```bash
export DEEPSEEK_API_KEY="..."
export TELEGRAM_BOT_TOKEN="..."
export TELEGRAM_CHAT_ID="..."
export COPA_FOXKIDS_TZ="America/Bogota"
```

Opcionales para coste/tiempo:

```bash
export DS_MODEL="deepseek-chat"
export DS_MAX_TOKENS="1200"
export DS_TIMEOUT_SEC="180"
export DS_MAX_RETRIES="1"
```

## Cron recomendado (host local)

```cron
TZ=America/Bogota
0 0 * * * cd /ruta/a/scrapper && ./scripts/run_independent_midnight.sh >> out/cron_midnight.log 2>&1
0 8 * * * cd /ruta/a/scrapper && ./scripts/run_independent_window.sh morning >> out/cron_08h.log 2>&1
0 16 * * * cd /ruta/a/scrapper && ./scripts/run_independent_window.sh afternoon >> out/cron_16h.log 2>&1
```

## Qué hace el runner

- `midnight`:
  - `ingest_daily_events`
  - `select_candidates` -> `out/candidates_{DATE}_select.json`
  - mensaje Telegram de conteo: `Partidos obtenidos: N`

- `window morning/afternoon`:
  - `event_splitter` -> `exec_08h` / `exec_16h`
  - `split_ds_batches --slim --chunk-size 4`
  - DeepSeek por lote (`deepseek_batches_to_telegram_payload_parts.py`)
  - merge + render + envío Telegram

## Dry-run (sin API ni Telegram)

```bash
python3 jobs/independent_runner.py --mode midnight --date 2026-03-23 --dry-run
python3 jobs/independent_runner.py --mode window --slot morning --date 2026-03-23 --dry-run
```

## KPIs semana 1 (mínimo)

- Picks por franja (`08h`, `16h`)
- Win rate global y por mercado
- ROI unitario simple (si usas validación y odds persistidas)
- Coste tokens diario (DeepSeek dashboard)
- Latencia total por corrida

## Reporte automático (bloque 3 base)

Generar reporte rolling de 7 días (JSON + CSV):

```bash
./scripts/run_effectiveness_report.sh
```

Archivos de salida:

- `out/reports/effectiveness_latest.json`
- `out/reports/effectiveness_latest.csv`
- `out/reports/effectiveness_{START}_to_{END}.json`
- `out/reports/effectiveness_{START}_to_{END}.csv`

Sugerencia cron (23:55 CO):

```cron
55 23 * * * cd /ruta/a/scrapper && ./scripts/run_effectiveness_report.sh >> out/cron_report.log 2>&1
```

