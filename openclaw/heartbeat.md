# heartbeat.md — Pulso y estado (OpenClaw / pipeline)

**Ubicación canónica para OC:** este archivo **vive en OpenClaw** (contexto, reglas o docs del agente). El repo lo versiona en `openclaw/heartbeat.md` para que lo sincronices con tu instancia de OC.

Describe **qué es el heartbeat** en *este* proyecto y ofrece una **plantilla**. No sustituye al contrato de jobs y Telegram: eso está en **`openclaw.md`** (raíz del repo).

---

## Qué es (y qué no es)

| | |
|--|--|
| **Sí** | Artefacto ligero de **salud / sincronización**: última actividad, fase del pipeline, `daily_run_id`, eventual tarea actual. Útil para humanos y para **otro modelo o servicio** que necesite saber si los datos están frescos o si el scraper/agente quedó colgado. |
| **No** | No es la lista de comandos que debe ejecutar OC (eso es `openclaw.md` en la raíz del repo). |

**Archivo en vivo (workspace):** `out/heartbeat.md` — generado o actualizado por jobs u OC cuando corra el flujo (ruta relativa al repo `scrapper`).

---

## Plantilla — OpenClaw Heartbeat

```markdown
# OpenClaw Heartbeat

- **Last pulse (UTC):** YYYY-MM-DD HH:MM:SS
- **Status:** `Idle` | `Processing` | `Error`
- **Phase:** `ingest` | `select` | `analysis` | `persist` | `validate` | `telegram_render` | —
- **Daily run ID:** N
- **Current focus:** (opcional, ej. evento o liga en análisis)
- **DB:** `./db/sport-tracker.sqlite3` (o ruta efectiva)
- **Notes:** (errores recientes, advertencias)
```

---

## Uso práctico

1. Si **Last pulse** lleva mucho tiempo sin actualizar frente a lo esperado, revisar procesos (scraper, OC, red) antes de confiar en picks o análisis.
2. Otro modelo puede **leer** `out/heartbeat.md` en el workspace para decidir si espera a que `Phase` sea coherente (ej. no analizar picks de un run que aún está en `ingest`).
3. Un watchdog externo puede alertar si el archivo no se toca en X minutos — configuración opcional, no incluida por defecto en el repo.

---

## Relación con otros archivos

- **`openclaw.md`** (raíz del repo) — Contrato: qué ejecutar, qué prohibir, Telegram.
- **`out/telegram_message.txt`** — Salida final formateada para el canal (tras `render_telegram_payload.py`).
