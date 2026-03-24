# Prueba: modelo + formatter + Telegram **sin persistir picks**

Objetivo: ver **efectividad del análisis** y el **mensaje final** como irá a Telegram, **sin** ejecutar `persist_picks` ni `validate_picks` (no quedan filas nuevas en tablas de picks del run).

**Nota sobre la DB:** hace falta **ingesta de eventos del día objetivo** para que `select_candidates` tenga datos (`event_features`, etc.). Eso **sí escribe** en SQLite (partidos, bundles). Lo que **no** haces en esta prueba es **guardar picks** en la DB.

---

## 1. Decide la fecha “mañana” (tu zona)

Usa la fecha **calendario** que quieras probar, en formato `YYYY-MM-DD` (ej. si son las 23:07 del 6, “mañana” puede ser `2026-03-07`). Todo en hora local de referencia del proyecto (`America/Bogota` si no cambiaste nada).

---

## 2. Comandos (desde la raíz del repo `scrapper`)

```bash
# A) Inventario del día objetivo (mañana)
python3 jobs/ingest_daily_events.py --sport football --date YYYY-MM-DD --db ./db/sport-tracker.sqlite3 --limit 50

# B) Anota el daily_run_id que creó el ingest (sale en logs o consulta la DB).
# C) Candidatos para el modelo
python3 jobs/select_candidates.py --db ./db/sport-tracker.sqlite3 --daily-run-id N -o out/candidates_YYYY-MM-DD_select.json
```

**Parar aquí respecto al pipeline completo:** **no** ejecutes `persist_picks` ni `validate_picks`.

---

## 3. Qué hace OC / el modelo

1. Lee `out/candidates_{DATE}_select.json` (o tras splitter: `exec_08h` / `exec_16h`; ver `NAMING_ARTIFACTS.md`).
2. Produce **solo JSON** con el esquema del formatter: ver docstring de `jobs/render_telegram_payload.py` → guardar en **`out/telegram_payload.json`**.
3. Render:
   ```bash
   python3 jobs/render_telegram_payload.py -i out/telegram_payload.json -o out/telegram_message.txt
   ```
4. **Telegram:** enviar el contenido de **`out/telegram_message.txt` tal cual** (UTF-8), sin reescritura por LLM — ver `openclaw.md` §3.

Para **una franja** (como en `SCHEDULE.md`), filtra antes del paso 2 los eventos cuyo kickoff cae en esa ventana; para una prueba “todo el día mañana”, puedes meter en el payload todos los que el modelo analice.

---

## 4. Texto que puedes pegarle a OpenClaw

> Prueba **sin persistir picks**: fecha objetivo `YYYY-MM-DD` (mañana).  
> 1) Ejecuta ingest + select_candidates como en `openclaw/PRUEBA_MODELO_TELEGRAM.md`.  
> 2) **No** ejecutes persist_picks ni validate_picks.  
> 3) Con los candidatos, genera **solo** `out/telegram_payload.json` válido para `render_telegram_payload.py`, luego render a `out/telegram_message.txt` y envía **ese archivo** a Telegram sin modificar.

---

## 5. Si no quieres tocar la DB en absoluto

Entonces no uses `select_candidates`: tendrías que **construir a mano** (o desde otro origen) un `telegram_payload.json` que cumpla el esquema del formatter y seguir solo el paso render + Telegram. Es válido para probar el formato, pero **no** prueba el pipeline de datos del scrapper.
