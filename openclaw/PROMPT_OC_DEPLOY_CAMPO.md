# Prompt para OC — despliegue prueba de campo (cron CO + event_splitter)

Copiar y ajustar rutas absolutas al host.

```text
Objetivo: dejar el proyecto listo para producción con este calendario (America/Bogota):
- 00:00: ingest de todos los partidos del día calendario (daily run) y persistencia en SQLite.
- 08:00: análisis ventana mañana + un mensaje Telegram (texto = salida del formatter).
- 16:00: análisis ventana tarde + un mensaje Telegram.

Reglas del repo (no negociar): openclaw.md — no ejecutar reset_db ni run_e2e_manual.sh.

Cambios esperados en el repositorio:
1) Documentación ya existe en openclaw/CRON_COLOMBIA.md y openclaw/SCHEDULE.md — alinéalas si hace falta con 2 ventanas (mañana/tarde), no 3.
2) El job jobs/event_splitter.py filtra `candidates_DATE_select.json` → `exec_08h` / `exec_16h` (ver openclaw/NAMING_ARTIFACTS.md). OC no inventa listas de event_id.
3) Añade o ajusta scripts/run_slot_window.sh si falta el ejecutable (chmod +x).
4) En el host del usuario, el cron o el scheduler de OpenClaw debe:
   - Usar TZ=America/Bogota o equivalente.
   - A medianoche: ingest + select_candidates → out/candidates_YYYY-MM-DD_select.json
   - A 08:00 y 16:00: ejecutar scripts/run_slot_window.sh morning|afternoon (o los comandos python3 equivalentes en CRON_COLOMBIA.md), luego el flujo de modelo → telegram_payload.json → render_telegram_payload.py → enviar el TEXTO (cuerpo del mensaje) de out/telegram_message.txt, sin adjuntar archivo ni reescribir con LLM.
5) persist_picks / validate_picks: activar según política del usuario para campo real (no pedido en prueba sin persistencia).

No inventes daily_run_id: debe salir del ingest o de la DB. No inventes la fecha: usar date del día en CO en cada cron.

Confirma al final: archivos tocados, comandos exactos para cada cron, y que event_splitter quedó en el camino antes del análisis.
```
