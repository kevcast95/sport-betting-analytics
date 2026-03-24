# openclaw.md — Contrato operativo para OpenClaw (OC) en este repo

Este archivo es la **fuente de verdad** para lo que OC debe hacer aquí: jobs, órdenes, Telegram. No añadas pasos no listados, no reinterpretes salidas con el LLM para Telegram, no improvises comandos.

**No es** el registro de salud en tiempo real; para pulso / estado ver **`openclaw/heartbeat.md`** (documentación que **vive en OpenClaw**; el repo la copia ahí para versionar) y, en ejecución, `out/heartbeat.md` en el workspace.

**Diagnósticos y coste (OC):** no declarar “ban / API bloqueada” sin evidencia; lotes y tokens — **`openclaw/PROMPT_ANTI_ALUCINACION_COSTOS.md`**.

**Directorio de trabajo:** raíz del repositorio `scrapper` (donde están `jobs/`, `db/`, `out/`).

---

## 1. Pipeline núcleo (orden fijo)

Ejecuta **solo** estos jobs, en este orden, cuando el flujo diario lo requiera. Los argumentos (`--db`, `--date`, `--daily-run-id`, etc.) deben alinearse con el run actual; si no los tienes, pídelos explícitamente al usuario **antes** de ejecutar — no inventes IDs ni fechas.

**No incluye vaciado de base de datos.** La DB ya debe existir con el estado que el operador quiera; OC **no** ejecuta `reset_db.py` (ver §1 bis).

| Paso | Comando (plantilla; ajusta `--db`, fechas e IDs) |
|------|--------------------------------------------------|
| 1 | `python3 jobs/ingest_daily_events.py --sport football --date YYYY-MM-DD --db ./db/sport-tracker.sqlite3` (+ `--limit` si aplica) |
| 2 | `python3 jobs/select_candidates.py --db ./db/sport-tracker.sqlite3 --daily-run-id N -o out/candidates_YYYY-MM-DD_select.json` |
| 2b | `event_splitter`: de `candidates_DATE_select.json` → `exec_08h` o `exec_16h` — **`openclaw/NAMING_ARTIFACTS.md`**. |
| 3 | *(análisis / DS sobre el JSON de la ventana; resultado → `picks.json`)* |
| 4 | `python3 jobs/persist_picks.py --daily-run-id N --db ./db/sport-tracker.sqlite3 --input-json picks.json` |
| 5 | `python3 jobs/validate_picks.py --db ./db/sport-tracker.sqlite3 --daily-run-id N` |

### 1 bis) Prohibido para OC — reset y E2E con reset

- **No ejecutes** `python3 jobs/reset_db.py` (ni con `-y` ni sin él). Eso queda **solo para el humano en terminal** cuando quiera pruebas desde cero.
- **No ejecutes** `./jobs/run_e2e_manual.sh`: al inicio hace reset de la DB; es un flujo de **prueba local del operador**, no del agente.

**Contratos de datos:** ver sección «Contratos» en `README.md` (OC → DS, DS → OC).

---

## 2. Jobs fuera del pipeline (no reemplazan al §1)

Estos **no** van entre ingest y select como sustitutos del flujo anterior. Se usan **cuando corresponda**, después de tener los insumos indicados.

| Job | Cuándo | Comando (plantilla) |
|-----|--------|----------------------|
| `event_splitter.py` | Tras `select_candidates`, por cada ventana del día (ver `openclaw/SCHEDULE.md` y `openclaw/CRON_COLOMBIA.md`) | Ver §1 paso 2b |
| `split_ds_batches.py` | Antes del LLM: divide `ds_input` en lotes (`--slim`, `--chunk-size`); evita timeouts y coste con muchos eventos | Ver `openclaw/OPTIMIZACION_TOKENS.md` |
| `merge_telegram_payload_parts.py` | Tras analizar cada lote: une `events` en un solo `telegram_payload` | Ver `openclaw/OPTIMIZACION_TOKENS.md` |
| `render_telegram_payload.py` | Existe `out/telegram_payload.json` válido (esquema abajo) | `python3 jobs/render_telegram_payload.py -i out/telegram_payload.json -o out/telegram_message.txt` |
| `backtest_runner.py` | El usuario pide métricas históricas sobre `pick_results` | `python3 jobs/backtest_runner.py --db ./db/sport-tracker.sqlite3 --range-start YYYY-MM-DD --range-end YYYY-MM-DD --strategy-version V` |

**Esquema de `out/telegram_payload.json`:** objeto JSON único; campos exactos documentados en el docstring de `jobs/render_telegram_payload.py` (líneas de ejemplo al inicio del archivo). Si falta el archivo o el JSON no es un objeto válido, **no** ejecutes el render: corrige el JSON primero.

---

## 3. Telegram — cierre obligatorio y único

**Ventanas diarias:** si operas con franjas (`openclaw/SCHEDULE.md`), hay **un ciclo render + envío por cada franja**: el `telegram_payload` de esa pasada debe contener **solo** los picks de esa franja; el mensaje enviado es **ese** archivo renderizado (típicamente **3 mensajes/día**). No mezclar en un solo envío las franjas ni reescribir con el LLM.

Cuando deba enviarse el resumen de **una** franja a Telegram:

1. Asegúrate de que exista `out/telegram_message.txt` generado **únicamente** por:
   ```bash
   python3 jobs/render_telegram_payload.py -i out/telegram_payload.json -o out/telegram_message.txt
   ```
2. **Envía a Telegram el contenido de `out/telegram_message.txt` tal cual** (UTF-8, sin modificaciones).

**Prohibido:**

- Enviar texto generado por el LLM en lugar del archivo.
- Resumir, «mejorar», añadir introducción o despedida al mensaje.
- Volver a formatear o explicar lo que ya está en `telegram_message.txt`.

Con eso el flujo termina. No añadas tareas de redacción ni pasos extra «para ayudar».

---

## 4. Resumen de reglas

| Hacer | No hacer |
|-------|----------|
| Ejecutar los jobs del §1 en orden cuando toque el pipeline | Inventar fechas, `daily_run_id` o rutas |
| Ejecutar el render solo con JSON válido en `out/telegram_payload.json` | Ejecutar el render sin el archivo o con JSON inválido |
| Enviar solo `out/telegram_message.txt` al canal | Parafrasear o enriquecer el mensaje con el modelo |
| — | Ejecutar `reset_db.py` o `./jobs/run_e2e_manual.sh` |

Para detalles técnicos adicionales del proyecto: `README.md`.
