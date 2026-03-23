# Ventanas diarias de análisis (inventario + 2 análisis) — producción CO

**Producción (Colombia):** medianoche = ingest del día; **08:00** y **16:00** = análisis por ventana + un Telegram cada una. Detalle de cron: `CRON_COLOMBIA.md`. La partición por kickoff la hace **`jobs/event_splitter.py`**, no el LLM.

**Idea:** **una** pasada de inventario y **varias** pasadas de análisis según ventanas de **kickoff** (cuándo se juega cada partido), no varias opiniones sobre el mismo partido.

---

## 1. Idea central (partidos distintos por ventana)

| Capa | Qué hace | Cuántas veces / día |
|------|----------|---------------------|
| **Inventario** | Ingest del `daily_run`: traer **todos** los eventos del día (fecha objetivo) a la DB. | **1×** (típico: madrugada o primera ventana) o 2× si quieres refrescar odds de tarde. |
| **Análisis por ventana** | Solo entran partidos cuyo **kickoff** (en tu TZ) cae en **esa franja**. Cada cron analiza **otro subconjunto** (mañana vs tarde). | **2×** en producción CO (08:00 y 16:00); puedes añadir un tercer cron si lo necesitas. |

Ejemplo: a las **08:00** analizas kickoffs en `[00:00, 16:00)`; a las **16:00**, en `[16:00, 24:00)` el mismo día calendario. **Picks distintos por franja** (partidos distintos). El filtro exacto: `event_splitter.py --slot morning|afternoon`.

La franja `[inicio, fin)` de kickoff **local** define qué partidos entran en **ese** cron; así en cada horario solo cargas al modelo los encuentros de **esa** banda.

---

## 2. Definir ventanas explícitas (zona horaria fija)

Fija **una** zona (ej. `America/Bogota` como ya usa el proyecto) y para cada slot define:

- `slot_id` (ej. `morning`, `afternoon`, `night`)
- `cron` (hora de disparo en esa zona)
- `window_end` = hora del **siguiente** cron (o fin de “día deportivo” si el último slot manda picks del día siguiente)

**Ejemplo esquemático** (ajústalo a tus horarios reales):

| Slot | Dispara | Ventana de kickoff (local) para *este* análisis |
|------|---------|---------------------------------------------------|
| A | 00:30 | Partidos del calendario día D con kickoff en [00:30, 08:00) — suele ser poco; muchos equipos lo dejan vacío o solo “early birds”. |
| B | 08:00 | Kickoff en **[08:00, 16:00)** (hasta antes del siguiente cron). |
| C | 16:00 | Kickoff en **[16:00, 23:59)** o hasta **antes del primer cron del día D+1** si quieres que el tercer pase cubra noche + madrugada siguiente. |

Lo importante no son los números concretos sino la regla: **en cada ejecución solo entran partidos cuyo kickoff cae en esa franja horaria del día**.

---

## 3. Telegram — **un mensaje por franja** (regla fija)

Con ventanas = **horarios de juego distintos**:

- Tras **cada** análisis de una franja: generas `telegram_payload` **solo** con los picks válidos de **esa** franja → `render_telegram_payload` → **un envío a Telegram por franja** (en producción CO: **2 mensajes al día** si hay actividad en ambas ventanas).
- Ejemplo: a las **08:00** recibes en Telegram las opciones válidas de partidos que **se juegan** con kickoff **desde** el inicio de esa franja **hasta antes** del siguiente punto del día (ej. si el siguiente cron es a las **14:00**, la franja de kickoff puede ser `[08:00, 14:00)` en hora local — ajusta a tus horarios reales). A las **14:00**, otro mensaje solo con la siguiente franja; y así sucesivamente.

**No hace falta** “primera vs última decisión” **para el mismo partido** en el diseño base: cada partido cae en **una** franja de kickoff.

### Resultados del día (expectativa operativa)

Las tres franjas son **tandas independientes** para el calendario (partidos distintos). A nivel de resultado:

- Puede darse **acertar picks en las tres** franjas el mismo día.
- También puede darse **ir mal en la primera** y **recuperar en la segunda o tercera** — no están atadas; cada mensaje refleja solo su franja.

Si en el **futuro** re-analizas el **mismo** `event_id` en dos ventanas, ahí sí haría falta regla de DB (“primera gana” / “última pisa”) — **no es el caso base** aquí.

---

## 4. Qué hacer en OC (estructura)

1. **Cron 1 (inventario):** `ingest_daily_events` para `date=D` + `select_candidates` **opcional** si quieres ver candidatos totales (o saltar hasta la ventana humana).
2. **Cron 2, 3, 4 (análisis):** mismos `daily_run_id` y misma DB; en cada uno:
   - Filtrar la lista de eventos (por **kickoff** en la franja de **esa** ventana) **antes** de llamar al modelo largo.
   - `persist_picks` / `validate` para los picks de esa franja.
   - `render_telegram_payload` + envío a Telegram **en cada ventana** (un mensaje por franja; ver §3).

3. **Heartbeat:** en cada ejecución, actualizar `out/heartbeat.md` con `Phase`, `slot_id` y ventana efectiva para que otro proceso sepa “en qué tanda vamos”.

---

## 5. Implementación en código (hoy vs mañana)

Hoy `select_candidates` **no** recorta por ventana de kickoff en CLI; ordena/filtra por calidad de datos. Para que sea **determinista** sin depender del modelo:

- Añadir flags tipo `--kickoff-local-after` / `--kickoff-local-before` (en la TZ del job), **o**
- Filtrar con `event_splitter` (salidas `candidates_{DATE}_exec_08h.json` / `_exec_16h.json`; ver `NAMING_ARTIFACTS.md`).

Hasta que exista eso, la regla de ventana puede ser **convención en el prompt** + lista explícita de `event_id` por slot — más frágil pero viable al inicio.

---

## 6. Resumen

- **Sí:** un ingest amplio del día + **varios análisis**, cada uno solo para partidos cuyo **kickoff** cae en la **franja hasta antes del siguiente punto** del día (partidos distintos entre franjas, en lo normal).
- **Telegram:** **obligatorio un mensaje por franja** (no un solo digest al cierre salvo que cambies esta política por escrito).
- **Definir:** zona horaria y límites explícitos de cada franja (alineados con la hora del siguiente cron).
- **Siguiente paso de repo (opcional):** filtros de tiempo en `select_candidates` o script de ventana para no depender solo del LLM.
