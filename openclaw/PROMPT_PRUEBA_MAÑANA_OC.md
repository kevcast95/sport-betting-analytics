# Prompt completo para OC — prueba mañana + Telegram (anti-alucinación)

Copiar el bloque entre \`\`\`text y \`\`\` y pegarlo a OpenClaw.

```text
Contexto: repo local `scrapper` (raíz con carpetas `jobs/`, `db/`, `out/`). Sigue `openclaw.md` en la raíz: NO ejecutes `python3 jobs/reset_db.py` ni `./jobs/run_e2e_manual.sh`.

Objetivo: prueba operativa con partidos de MAÑANA (fecha calendario en zona America/Bogota o la que use el proyecto). Si no tienes la fecha exacta en YYYY-MM-DD, PÍDELA al usuario antes de continuar; no inventes la fecha.

Alcance de esta tarea:
1) Traer datos del día objetivo y listar candidatos.
2) Generar el JSON del formatter, renderizar a texto y que Telegram reciba ESE TEXTO como mensaje.
3) NO persistir picks en la base de datos en esta prueba.

Pasos obligatorios (en orden, desde la raíz del repo):

A) ingest:
   python3 jobs/ingest_daily_events.py --sport football --date YYYY-MM-DD --db ./db/sport-tracker.sqlite3
   (ajusta --limit si hace falta; usa la misma --db que el proyecto.)

B) Obtén el `daily_run_id` del run que acaba de crear (logs del comando o consulta razonable a la DB). No inventes el ID.

C) select:
   python3 jobs/select_candidates.py --db ./db/sport-tracker.sqlite3 --daily-run-id <ID> -o out/candidates_YYYY-MM-DD_select.json

D) NO ejecutes: persist_picks, validate_picks.

E) Con la información de `out/candidates_YYYY-MM-DD_select.json` (o ventana `exec_*`), el modelo debe producir UN SOLO artefacto: un archivo JSON válido en UTF-8 en `out/telegram_payload.json` cuyo esquema sea EXACTAMENTE el documentado en el docstring al inicio de `jobs/render_telegram_payload.py` (objeto con `header`, `events[]` con `picks[]`, opcional `db_1x2_line`). Sin markdown alrededor del JSON, sin comentarios, sin texto antes o después del JSON en ese archivo.

F) Render (obligatorio):
   python3 jobs/render_telegram_payload.py -i out/telegram_payload.json -o out/telegram_message.txt

G) Telegram — CRÍTICO, lee literal:
   - Abre `out/telegram_message.txt` y lee su contenido completo como texto UTF-8.
   - Ese contenido es el CUERPO del mensaje que debe enviarse al canal/bot de Telegram.
   - NO adjuntes el archivo .txt como documento.
   - NO envíes la ruta del archivo como mensaje.
   - NO reescribas, resumas, expliques ni "mejores" el texto con el modelo: debe ser el mismo string que está en el archivo (emojis y saltos de línea incluidos).

Si algún paso falla (ingest vacío, sin daily_run_id, JSON inválido para el render), DETENTE, informa el error concreto y no inventes datos para "salvar" la prueba.

Al final, confirma: fecha usada, daily_run_id, que ejecutaste render, y que el envío a Telegram fue el TEXTO del archivo (cuerpo del mensaje), no un adjunto.
```
