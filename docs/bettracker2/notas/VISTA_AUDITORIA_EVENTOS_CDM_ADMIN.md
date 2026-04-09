# Vista de auditoría de eventos / candidatos CDM (admin) — propuesta V2

> **Estado:** borrador para conversar con PO/BA y bajar a US + TASKS.  
> **Contexto:** En V1 existe inspección por run (`GET /daily-runs/{id}/events`) con motivos de rechazo de contrato/candidato. En BT2, la bóveda depende de `bt2_events` + `bt2_odds_snapshot` y el snapshot se arma en servidor; hoy no hay una pantalla equivalente que explique “por qué no hay picks” o “qué se consultó”.

## Problema de producto

- El operador ve **0 picks** y no distingue: **falta ingesta CDM**, **filtros del snapshot**, **sesión ya abierta sin regenerar**, u **otro**.
- En desarrollo y staging hace falta **trazabilidad** sin exponer JSON crudo de proveedores (API-first / D-06-002).

## Objetivo de la vista

Una pantalla **solo admin**, misma semántica de acceso que la precisión DSR (`X-BT2-Admin-Key` / `BT2_ADMIN_API_KEY`), que para un **`operating_day_key`** (y opcionalmente TZ de referencia) muestre:

1. **Resumen operativo**
   - Eventos futuros en CDM (`kickoff_utc > now`) con liga activa (conteo).
   - Eventos en la **ventana del día operativo** usada por `_generate_daily_picks_snapshot` (inicio/fin UTC derivados de TZ usuario o parámetro).
   - Cuántos pasan cada filtro acumulativo (ver abajo).

2. **Lista de eventos candidatos o “casi candidatos”**
   - Identidad humana: equipos, liga, kickoff local, `event_id`.
   - Flags o motivo único de exclusión (**español operativo**), por ejemplo:
     - `sin_ingesta` — no está en `bt2_events` para ese día/liga.
     - `liga_inactiva` — `bt2_leagues.is_active = false`.
     - `estado_partido` — no `scheduled` (live, finished, postponed…).
     - `fuera_ventana_dia` — kickoff fuera del día operativo en TZ.
     - `sin_cuota_minima` — ninguna fila en `bt2_odds_snapshot` con `odds >= 1.30` (umbral actual del snapshot).
     - `en_pool_sql` — entró en el `LIMIT 80` ordenado por tier/margin (sí es base del snapshot).
     - `en_snapshot` — existe fila en `bt2_daily_picks` para ese `user_id`/`operating_day_key` (opcional: scope “usuario demo” o agregado sin PII).

3. **Separación clara: CDM vs decisión de producto**
   - Todo lo anterior es **regla servidor** antes o durante composición del pool.
   - Una segunda sección (fase 2) podría enlazar **DSR / `dsr_source`** o “no propuesto por lote” cuando exista trazabilidad persistida.

## Backend (líneas de implementación tentativas)

- Nuevo endpoint bajo prefijo admin existente, por ejemplo:  
  `GET /bt2/admin/cdm-day-audit?operatingDayKey=YYYY-MM-DD&userId=<uuid opcional para línea snapshot>`  
  con header **`X-BT2-Admin-Key`**.
- Implementación preferente: **SQL agregado + lista paginada** leyendo `bt2_events`, `bt2_leagues`, `bt2_odds_snapshot`, y opcionalmente `bt2_daily_picks` (sin volcar odds completas al cliente).
- Mantener alineación con la query real del snapshot en `bt2_router._generate_daily_picks_snapshot` para que la auditoría **no mienta** respecto a producción.

## Frontend (identidad V2)

- Ruta nueva bajo el **shell admin** ya usado para precisión DSR (sidebar solo enlace + contenido en `main`).
- Estética **Zurich Calm** / ALTEA: tipografía mono para datos, jerarquía clara, estados vacío/error.
- Export CSV: **fuera de alcance** hasta decisión explícita (coherente con D-06-010 en otras vistas admin).

## Relación con operación

- Enlazar desde [`runbooks/bt2_fetch_upcoming_cron.md`](../runbooks/bt2_fetch_upcoming_cron.md), `GUIA_OPERACION_Y_ARQUITECTURA` y esta nota: la vista admin debe ayudar a separar **“CDM vacío”** de **“filtros del snapshot”**.
- **Cron / job programado:** `scripts/bt2_cdm/job_fetch_upcoming.py` debe ejecutarse de forma **recurrente** (p. ej. 1×/día o antes de la ventana operativa) con `SPORTMONKS_API_KEY` y `BT2_DATABASE_URL` válidos. Sin cron estable, es esperable quedarse con **0 eventos futuros** y por tanto **0 picks**, independiente de la calidad del modelo.
- **Cuando falle la descarga o no traiga datos útiles:**
  - **Exit code 2** — la corrida terminó pero `download_ok` fue **false** (error de red/API en la pasada paginada de Sportmonks): **no asumir** que la BD quedó al día; revisar logs y **re-ejecutar**.
  - **Exit code 1** — error fatal (clave faltante, excepción): corregir entorno y relanzar.
  - **Post-condición recomendada:** tras cada ejecución en producción/staging, comprobar (métrica, script o alerta) que `COUNT(*) FROM bt2_events WHERE kickoff_utc > now()` **> 0** en horario esperado, o al menos que el reporte Markdown en `docs/bettracker2/recon_results/` refleje `events_futuros_despues` acorde al calendario. Si es **0** con partidos reales en el mercado, disparar **alerta** o ticket on-call (**D-06-011**).
- La vista de auditoría debe mostrar explícitamente **conteo futuro bajo** y, si se integra metadata opcional, **última corrida exitosa del job** (fuera de alcance MVP si no hay tabla de runs; hasta entonces, enlace al runbook + checklist manual).

## Mejoras futuras (backlog encadenado)

- **`POST /bt2/admin/snapshot/refresh`** (nombre tentativo) o regla equivalente en servidor: **regenerar** `bt2_daily_picks` para un `operating_day_key` (y opcionalmente un `user_id`) cuando el **pool publicado está vacío** pero **CDM ya tiene candidatos** que pasarían la query del snapshot — evita depender de **cerrar sesión + volver a abrir** tras una ingesta tardía (`fetch_upcoming` corrido después de `session/open`). Misma protección admin que el resto: header **`X-BT2-Admin-Key`** / `BT2_ADMIN_API_KEY`, idempotencia y trazabilidad en logs.
- Encaja con el backlog de **Sprint 6.1** (calidad señal / operación) y con esta misma vista de auditoría: primero se **diagnostica**, luego se **corrige datos o se fuerza refresh** sin hacks en SQL en local.
- **Idempotencia actual:** mientras no exista ese endpoint, documentar en runbook el flujo operativo: ingesta → si sesión ya abierta con snapshot vacío → `session/close` + `session/open` (o borrado controlado en dev de `bt2_daily_picks` para ese día).

## Próximos pasos sugeridos

1. PO valida **alcance MVP** (solo filtros del snapshot + conteos, sin DSR).  
2. `US-BE-###` + `US-FE-###` + `US-DX-###` si el contrato de respuesta se publica en OpenAPI.  
3. Tarea en `sprint-06.1` o `07` según prioridad vs `T-153`/`T-155`.

---

*Última revisión: 2026-04-09 — añadidos cron/exit codes/alertas y admin refresh snapshot.*
