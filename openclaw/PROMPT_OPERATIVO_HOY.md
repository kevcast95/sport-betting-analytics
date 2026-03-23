# Prompt para OC — primer día operativo (lectura + cron + mensajes)

Copiar el bloque siguiente y pegarlo a OpenClaw. Ajusta solo si **las 12** deben ser **mediodía** y no **medianoche** (ver nota al pie).

---

```text
## 0) Lee primero (contexto obligatorio)

Lee y sigue en este orden (raíz del repo `scrapper`):
- `openclaw.md`
- `openclaw/SCHEDULE.md`
- `openclaw/CRON_COLOMBIA.md`
- `openclaw/README.md`
- Cualquier archivo nuevo en `openclaw/` que documente cron, `event_splitter`, Telegram.

Reglas duras: NO ejecutes `reset_db.py` ni `./jobs/run_e2e_manual.sh` (ver `openclaw.md`).

---

## 1) Esta noche / madrugada — **00:00 hora Colombia** (medianoche)

A las **12 en punto de la noche** = **00:00** en `America/Bogota` (inicio del día calendario nuevo).

En ese instante debe ejecutarse el **primer job del pipeline**: ingest del día.

Comandos (plantilla; `DATE` = fecha del día que **acaba de empezar** en CO, típicamente `$(date +%Y-%m-%d)` en el host con `TZ=America/Bogota`):

```bash
cd /ruta/al/repo/scrapper
export TZ=America/Bogota
DATE=$(date +%Y-%m-%d)
python3 jobs/ingest_daily_events.py --sport football --date "$DATE" --db ./db/sport-tracker.sqlite3
```

Luego **select_candidates** para tener el JSON del run (necesitas `daily_run_id` del ingest):

```bash
python3 jobs/select_candidates.py --db ./db/sport-tracker.sqlite3 --daily-run-id <ID> -o "out/candidates_${DATE}_select.json"
```

**Por esta vez solamente**, después del ingest (y cuando tengas el total de eventos del run — p. ej. del log de ingest, de `select_candidates`, o de `run_inventory`):

- Envía **un mensaje a Telegram** cuyo texto sea **exactamente** en una o dos líneas, por ejemplo:
  `Partidos obtenidos: N`
  (donde **N** es el número total correcto según los datos del run; no inventes N).

No uses el formatter largo para este mensaje de confirmación; es solo aviso operativo. Los mensajes formateados del análisis van aparte (§3).

---

## 2) Mismo día — **08:00** y **16:00** hora Colombia

En cada horario:

1. Asegúrate de existir `out/candidates_${DATE}_select.json` del día (compartido por 08:00 y 16:00; si no, repetir select).
2. Ejecuta **event_splitter** para la ventana:
   - 08:00 → `--slot morning` → `out/candidates_${DATE}_exec_08h.json`
   - 16:00 → `--slot afternoon` → `out/candidates_${DATE}_exec_16h.json`

```bash
python3 jobs/event_splitter.py -i "out/candidates_${DATE}_select.json" -o "out/candidates_${DATE}_exec_08h.json" --date "$DATE" --slot morning --timezone America/Bogota
# 16:00: mismo _select.json de entrada, salida _exec_16h.json y --slot afternoon
```

3. El **analista** (modelo) trabaja sobre el JSON de esa ventana → genera `out/telegram_payload.json` →

```bash
python3 jobs/render_telegram_payload.py -i out/telegram_payload.json -o out/telegram_message.txt
```

4. **Telegram:** envía el **contenido textual completo** de `out/telegram_message.txt` como **cuerpo del mensaje** (UTF-8), sin adjuntar el archivo, sin reescribir con LLM (ver `openclaw.md` §3).

5. **persist_picks / validate:** según política del usuario para campo real; si no te lo pidieron, pregunta antes de persistir.

---

## 3) Scheduler

Configura en el host (cron, systemd, o el scheduler de OpenClaw) las tres ejecuciones con **TZ=America/Bogota**:
- `0 0 * * *` → ingest + aviso "Partidos obtenidos: N" (solo esta primera vez el texto extra; después puedes omitir el aviso o automatizar el conteo)
- `0 8 * * *` → ventana mañana + analista + Telegram formatter
- `0 16 * * *` → ventana tarde + analista + Telegram formatter

Confirma al usuario las rutas absolutas y que las pruebas de envío Telegram funcionan.

```

---

### Nota: ¿12:00 medianoche o mediodía?

- Si **medianoche (00:00)** → lo de arriba.  
- Si el usuario quiso **12:00 del mediodía** para el ingest, cambia el cron a `0 12 * * *` y aclara que el **DATE** del calendario debe ser el del **mismo día** que quieres scrapear (no el día siguiente).
