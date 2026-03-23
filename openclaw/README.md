# Paquete OpenClaw (OC)

Esta carpeta es el **hogar del agente** para este proyecto: lo que debe vivir **en el contexto / reglas de OpenClaw**, no como lógica del scrapper.

| Archivo | Rol |
|---------|-----|
| **`heartbeat.md`** | Pulso y plantilla de estado — **cárgalo en OC** (reglas o documentación adjunta). |
| **`SCHEDULE.md`** | Ventanas del día (ingest 1× vs análisis 3×), política de picks entre pasadas — **cárgalo en OC** si usas crons por franja. |
| **`PRUEBA_MODELO_TELEGRAM.md`** | Prueba ingest + análisis + formatter + Telegram **sin** `persist_picks` / `validate_picks`. |
| **`PROMPT_PRUEBA_MAÑANA_OC.md`** | Prompt largo listo para pegar a OC (antiambigüedad: texto como cuerpo del mensaje, no adjunto). |
| **`CRON_COLOMBIA.md`** | Horarios 00:00 / 08:00 / 16:00 y secuencia de jobs. |
| **`PROMPT_OC_DEPLOY_CAMPO.md`** | Prompt para que OC alinee repo + cron + `event_splitter` en despliegue real. |
| **`PROMPT_OPERATIVO_HOY.md`** | Primer día: leer docs, 00:00 ingest + mensaje «Partidos obtenidos: N», 08:00 y 16:00 analista + Telegram. |
| **`OPTIMIZACION_TOKENS.md`** | Timeout, coste, lotes (`split_ds_batches` / `merge_telegram_payload_parts`), rutas con fecha. |
| **`NAMING_ARTIFACTS.md`** | Nombres en `out/`: `candidates_{DATE}_select`, `exec_08h`, `exec_16h`, lotes. |
| **`PROMPT_ANTI_ALUCINACION_COSTOS.md`** | Guardrails: evidencias antes de “ban”, coste/tokens, heartbeat corto, plantilla de incidente. |
| **`DEEPSEEK_LOCAL.md`** | Ejecución local (sin OpenClaw): DeepSeek + formatter + Telegram. |
| **`INDEPENDENT_SYSTEM_WEEK1.md`** | Plan operativo 7 días sin OC: cron, variables, KPIs, dry-run. |
| **`../scripts/bootstrap_env.sh`** | Valida/carga `.env` y obliga separación `DS_CHAT_MODEL` vs `DS_ANALYSIS_MODEL`. |
| **`../jobs/report_effectiveness.py`** | Métricas de efectividad (win-rate/ROI) por día/mercado/franja a JSON+CSV. |
| **`../openclaw.md`** | Contrato operativo (pipeline, Telegram); en la raíz del repo para lectura humana y referencias cruzadas. |

El estado **en vivo** del run sigue recomendándose en `out/heartbeat.md` dentro del repo cuando ejecutes jobs (OC puede leerlo/actualizarlo por ruta si tiene acceso al workspace).
