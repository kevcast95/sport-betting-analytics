# Sprint 02 - Decisiones técnicas

Registra decisiones de arquitectura y trade-offs del sprint de datos / Atraco Masivo.

## Formato

- Decisión:
- Contexto:
- Alternativas consideradas:
- Elegida:
- Impacto:
- Fecha:

---

## US-OPS-001 — Estrategia de base de datos local (2026-04-06)

- **Decisión:** Docker Compose con `postgres:16-alpine` como infraestructura local de desarrollo para Sprint 02. No se usa Supabase, Neon ni Railway en esta fase.
- **Contexto:** El objetivo del sprint es el Atraco Masivo — ingesta intensiva de datos históricos. Una base de datos local elimina la latencia de red en las escrituras y los límites de ancho de banda de planes cloud gratuitos. El volumen esperado (2 temporadas × 5 ligas × ~50 fixtures/jornada) puede superar las cuotas gratuitas de Neon/Supabase.
- **Alternativas consideradas:**
  - Supabase free: 500 MB límite, latencia de red, pausas automáticas — descartado por volumen.
  - Neon free: 512 MB, sin persistencia garantizada en tier gratuito — descartado.
  - PostgreSQL nativo en macOS: sin aislamiento, depende del entorno del desarrollador — descartado.
- **Elegida:** Docker Compose local. El `docker-compose.yml` queda versionado en el repo; la contraseña local (`bt2local`) es para desarrollo únicamente.
- **Impacto:** T-063. En Sprint 03, cuando se conecte el FE al BE en staging, se migrará a Neon o Railway con la misma `BT2_DATABASE_URL` en `.env`.
- **Fecha:** 2026-04-06

---

## US-OPS-001 — URL de base de datos: async vs sync (2026-04-06)

- **Decisión:** Usar **dos prefijos distintos** según el contexto: `postgresql+asyncpg://` para el runtime de FastAPI (async), `postgresql://` (psycopg2) para Alembic (sync). Ambas URLs apuntan al mismo servidor; solo cambia el driver.
- **Contexto:** SQLAlchemy 2.0 async requiere `asyncpg` como driver; Alembic no soporta drivers async nativamente sin configuración extra (`run_sync`). Mantener dos URLs simplifica la configuración inicial.
- **Alternativas consideradas:** Configurar Alembic con `run_sync` sobre engine async — más complejo, requiere código extra en `env.py`; descartado para no bloquear T-070.
- **Elegida:** `BT2_DATABASE_URL` en `.env` contiene la URL async (`postgresql+asyncpg://…`). `alembic.ini` usa la misma URL con el prefijo cambiado vía script en `env.py` (`url.replace("postgresql+asyncpg", "postgresql")`).
- **Impacto:** T-064, T-070. El agente ejecutor debe aplicar el reemplazo en `alembic/env.py`.
- **Fecha:** 2026-04-06

---

## US-BE-002 — Solo 4 requests en el smoke test (2026-04-06)

- **Decisión:** El smoke test ejecuta exactamente **4 requests** (2 Sportmonks + 2 The-Odds-API), no más.
- **Contexto:** Sportmonks Pro tiene 3,000 API calls en 14 días. Cada call desperdiciada en pruebas es una menos para el Atraco. The-Odds-API cobra por request. El objetivo del smoke test es solo confirmar que las keys funcionan y que la estructura de respuesta es la esperada.
- **Alternativas consideradas:** 10 requests para un reconocimiento más completo — descartado; el reconocimiento profundo puede hacerse con los datos ya ingestados del Atraco.
- **Elegida:** 4 requests fijas; si un endpoint falla con 403/404, se registra y se continúa.
- **Impacto:** T-066, T-067, T-068. El reporte de smoke test determina si se procede con el Atraco.
- **Fecha:** 2026-04-06

---

## US-BE-003 — JSONB para almacenamiento raw (2026-04-06)

- **Decisión:** Los snapshots de ambos proveedores se almacenan en una columna `payload JSONB` sin normalizar. Solo los metadatos de indexación (fecha, IDs, equipos) se mapean a columnas tipadas.
- **Contexto:** La estructura de respuesta de Sportmonks y The-Odds-API puede cambiar entre versiones del plan o por cambios del proveedor. Normalizar todo el payload en Sprint 02 requeriría conocer el shape exacto de cada campo antes de haberlo observado en producción — es prematuro.
- **Alternativas consideradas:**
  - Tablas completamente normalizadas desde el inicio: exige conocer el schema exacto antes del Atraco — descartado; se hace en Sprint 03 con datos reales.
  - Archivos JSON planos en disco: sin capacidad de query — descartado.
- **Elegida:** JSONB + columnas de metadatos para indexación. La normalización al CDM se hace en Sprint 03 como `US-BE-005` o superior, con datos reales ya ingestados.
- **Impacto:** T-069. Las tablas `raw_*` son de staging; las tablas normalizadas del CDM llegan en Sprint 03.
- **Fecha:** 2026-04-06

---

## US-BE-004 — Paralelismo con asyncio (no multiprocessing) (2026-04-06)

- **Decisión:** Los workers del Atraco usan `asyncio.gather` para correr en paralelo dentro del mismo proceso Python, **no** `multiprocessing` ni colas externas (BullMQ, Celery).
- **Contexto:** El Atraco es un proceso batch que corre durante horas, principalmente esperando respuestas HTTP (I/O bound). `asyncio` es suficiente para I/O concurrente sin el overhead de múltiples procesos. Celery/BullMQ es overkill para un script de ingesta manual.
- **Alternativas consideradas:**
  - `multiprocessing.Pool`: CPU-bound; no aplica aquí — descartado.
  - Celery + Redis: necesitaría infraestructura adicional (Redis); valioso para jobs recurrentes en producción — diferido a Sprint 04+ (US-OPS futura).
  - Script secuencial: los workers se esperan entre sí — descartado; el objetivo es maximizar el uso del tiempo disponible.
- **Elegida:** `asyncio.gather(run_sportmonks(), run_theoddsapi())` en `run_atraco.py`. Los dos workers son independientes y pueden correr simultáneamente.
- **Impacto:** T-074. Si un worker toca el rate limit y pausa 60 min, el otro sigue corriendo.
- **Fecha:** 2026-04-06

---

## US-BE-004 — Estrategia de priorización del Atraco (2026-04-06)

- **Decisión:** Primera pasada del Atraco: **2 temporadas** (2022-23 y 2023-24) de las **5 ligas prioritarias** (Premier League, La Liga, Bundesliga, Serie A, Champions League). Si los créditos de Sportmonks lo permiten, ampliar a la temporada 2024-25 en curso.
- **Contexto:** Con 3,000 API calls de Sportmonks y ~11 jornadas/mes × 10 partidos/jornada × 5 ligas = ~550 fixtures/mes. Dos temporadas completas (agosto-mayo) = ~10 meses × 550 = ~5,500 fixtures — supera el cupo. Por tanto, priorizar las ligas de mayor valor para el modelo.
- **Prioridad de ligas:** Premier League (ID 8) > Champions (ID 2) > La Liga (ID 564) > Bundesliga (ID 82) > Serie A (ID 384).
- **Elegida:** Iterar en ese orden de prioridad; si el cupo se agota, el worker de Sportmonks para y registra hasta dónde llegó.
- **Impacto:** T-072. El parámetro `--league-ids` de `run_atraco.py` define el orden; el default es la lista de prioridad acordada.
- **Fecha:** 2026-04-06

---

## US-OPS-002 — bt2_settings.py: import seguro, nunca en main.py (2026-04-06)

- **Decisión:** `apps/api/bt2_settings.py` se importa **únicamente** desde módulos BT2 (`bt2_router.py`, scripts de `scripts/bt2_atraco/`). **Nunca** se agrega un import de `bt2_settings` en `apps/api/main.py`.
- **Contexto:** V1 (scrapper SQLite) y BT2 comparten el mismo proceso FastAPI. `pydantic-settings` valida los campos requeridos al importarse. Si `bt2_settings` se importa en `main.py` y falta cualquier campo en `.env`, el servidor V1 cae con `ValidationError` — rompe el scrapper en producción.
- **Alternativas consideradas:**
  - Import en `main.py` con `try/except`: frágil, enmascara errores reales de configuración.
  - Hacer todos los campos opcionales (`str = ""`): permite arrancar pero produce bugs silenciosos en producción.
- **Elegida:** Import aislado en módulos BT2 únicamente. El agente ejecutor verifica con `grep -r "bt2_settings" apps/api/main.py` que el resultado esté vacío tras crear el archivo.
- **Verificación obligatoria:** Después de T-077, correr `curl http://127.0.0.1:8000/health` — si V1 no responde, hacer rollback de `bt2_settings.py` y revisar la causa.
- **Impacto:** T-077. Esta restricción aplica a todo Sprint 02 y siguientes.
- **Fecha:** 2026-04-06

---

## US-OPS-002 — Postgres.app v18 en lugar de Docker (2026-04-06)

- **Decisión:** Se usa Postgres.app v18 corriendo en `localhost:5432` en lugar del Docker Compose planificado en US-OPS-001. La base de datos `bettracker2` fue creada manualmente por el usuario.
- **Contexto:** El usuario tiene Postgres.app instalado y encuentra Docker confuso. Postgres.app ofrece la misma funcionalidad para desarrollo local sin overhead de contenedores.
- **URL de conexión:** `postgresql+asyncpg://kevcast@localhost:5432/bettracker2` (autenticación OS, sin contraseña — válido solo en desarrollo local con Postgres.app).
- **Impacto:** T-063 (docker-compose.yml) cancelada. En staging/producción se usará Neon o Railway con URL diferente en el `.env` del servidor — sin cambio de código.
- **Fecha:** 2026-04-06

---

## US-BE-003 — Verificación de migración inicial (2026-04-05)

- **Decisión:** Primera migración `15ee91ad0d69_initial_snapshot_tables` aplicada exitosamente a PostgreSQL 18.3 (Postgres.app). Tablas creadas: `raw_sportmonks_fixtures`, `raw_theoddsapi_snapshots`, `bt2_event_identity_map`. Idempotencia verificada con `downgrade -1 && upgrade head`.
- **Contexto:** Python 3.9 (Xcode Command Line Tools). Tipo `|` en type hints no soportado — se usó `Optional[X]` de `typing`. Las dependencias se instalaron con `pip install --user`.
- **env.py:** Lee `BT2_DATABASE_URL` del `.env` raíz via `python-dotenv`; reemplaza `postgresql+asyncpg://` por `postgresql://` para Alembic sync. El repo root se añade a `sys.path` con `Path(__file__).parents[3]`.
- **Inserción de prueba:** `raw_sportmonks_fixtures` con `fixture_id=1, payload={"test": true}` — exitosa y eliminada tras verificar.
- **Impacto:** T-069, T-070, T-071 — completadas.
- **Fecha:** 2026-04-05

---

## Atraco Masivo — Estrategia final aprobada por el arquitecto (2026-04-06)

- **Decisión:** Profundidad temporal sobre amplitud de ligas. **5 ligas top × 4 temporadas** es la configuración óptima para el backtesting del modelo conductual.
- **Contexto:** Con menos de 2 temporadas por liga, el modelo overfittea sobre ruido de una sola temporada. 4 temporadas permiten detectar patrones que se repiten vs. anomalías puntuales (efectos post-COVID, inflación de cuotas, cambios de técnico). Más de 7-8 ligas añade complejidad sin retorno en esta fase.
- **Ligas confirmadas disponibles en el plan Pro trial:**
  - Premier League (ID 8) ✅
  - La Liga (ID 564) ✅
  - Bundesliga (ID 82) ✅
  - Serie A (ID 384) ✅
  - Ligue 1 (ID 301) ✅ (bonus)
  - Champions League (ID 2) ❌ — no accesible en el tier actual; diferir a Sprint 03 si se activa add-on
- **Rango de fechas:** 2021-08-01 → 2025-05-31 (4 temporadas completas)
- **Parámetros del Atraco:** `--league-ids 8,564,82,384,301 --start 2021-08-01 --end 2025-05-31`
- **Créditos estimados Sportmonks:** ~1,100 requests / 2,998 disponibles ✅
- **Créditos estimados The-Odds-API:** ~15,000 / 100,000 del plan $59 ✅
- **Impacto:** T-072, T-073, T-074. Prueba corta con `--start 2024-01-01 --end 2024-01-07` antes del rango completo.
- **Fecha:** 2026-04-06

---

## Arquitectura de proveedores — corrección y decisión final (2026-04-06)

- **Corrección de análisis previo:** La limitación de "7 días" aplica únicamente al **Premium Odds Feed** (€129/mes, TXOdds). El **Standard Odds Feed** incluido en el add-on Odds & Predictions (€15/mes) guarda el último snapshot de odds por fixture **sin límite de tiempo**. Sportmonks es autosuficiente para backtesting básico de valor esperado.
- **Roles de cada proveedor (revisados):**
  - **Sportmonks:** fixtures, estadísticas, xG, Pressure Index, odds estándar (~50 bookmakers, último snapshot pre-partido). Fuente principal del CDM. **Autosuficiente para el MVP.**
  - **The-Odds-API:** control exacto de timestamp de snapshot, mejor cobertura LATAM, análisis CLV (closing line value). **Complementario, no obligatorio** para el Atraco inicial.
- **Decisión sobre The-Odds-API $59:** diferido al **Día 7-8 del trial**. Activar solo si:
  1. El Atraco Pass 1 de Sportmonks produce datos limpios en PostgreSQL.
  2. La validación de identity mapping con datos EPL en vivo supera el 90% de match rate.
  3. El arquitecto confirma que el CLV granular es necesario para el modelo MVP.
  Si no se cumplen las 3 condiciones, cancelar. Los datos históricos de The-Odds-API no expiran — se pueden comprar en Sprint 03.
- **Plan económico post-trial confirmado:**
  - Sportmonks Starter (€29/mes) + Odds & Predictions add-on (€15/mes) = **€44/mes**.
  - Elegir las 5 ligas operativas **después** de analizar el backtesting del Atraco, no antes.
  - The-Odds-API: opcional, evaluar en Sprint 03.
- **Fecha:** 2026-04-06

---

## Atraco Masivo — Estrategia de 3 pasadas (2026-04-06)

- **Decisión:** El Atraco corre en 3 pasadas priorizadas durante los 14 días del trial Pro de Sportmonks. El objetivo es maximizar los datos históricos en PostgreSQL antes de bajar al plan Starter de 5 ligas.
- **Principio:** Los datos colectados durante el trial son de propiedad permanente en PostgreSQL. La elección de las 5 ligas operativas post-trial se basa en los resultados del backtesting, no en suposiciones previas.

**Pass 1 — Tier S (Días 1-4) — PRIORIDAD MÁXIMA:**
```
Ligas: Premier League (8), La Liga (564), Bundesliga (82),
       Serie A (384), Ligue 1 (301)
Rango: 2021-08-01 → 2025-05-31 (4 temporadas)
Includes: participants;odds;statistics;events;league;scores
Créditos estimados Sportmonks: ~600 requests
```

**Pass 2 — Tier A (Días 5-9) — ALTA PRIORIDAD:**
```
Ligas: Eredivisie (72), Pro League Bélgica (208),
       Liga Portugal (462), Super Lig (600),
       Ekstraklasa (453), Premiership Escocia (501),
       Liga BetPlay Colombia (672)
Rango: 2022-08-01 → 2024-05-31 (2 temporadas)
Créditos estimados Sportmonks: ~350 requests
```

**Pass 3 — Tier B (Días 10-12, si quedan créditos):**
```
Ligas: Championship (9), 2. Bundesliga (85), Ligue 2 (304),
       Serie B (387), MLS (779), Liga MX (743)
Rango: 2023-08-01 → 2024-05-31 (1 temporada)
Créditos estimados Sportmonks: ~200 requests
```

- **Créditos totales estimados:** ~1,100 / 2,992 disponibles. Margen amplio para reintentos.
- **Champions League (ID 2):** no disponible en el plan actual. Documentado como gap conocido.
- **Liga BetPlay Colombia (ID 672): descartada del Atraco.** Motivo técnico: la cobertura de bookmakers europeos (Pinnacle, Bet365) en Sportmonks Standard Odds para la BetPlay no está verificada. Sin odds de bookmakers solventes, los datos son solo marcadores sin valor para backtesting de expected value. Geografía del usuario no es criterio suficiente. Reevaluar en Sprint 04 si se activa The-Odds-API y se confirma cobertura LATAM.
- **Impacto:** T-072, T-073, T-074. El agente ejecutor implementa el parámetro `--pass` o ejecuta las pasadas secuencialmente.
- **Fecha:** 2026-04-06

---

## US-BE-004 — Acceso histórico Sportmonks: rango real de temporadas (2026-04-05)

- **Decisión:** El Atraco Masivo (Pass 1) arranca en **2023-08-01** en lugar de 2022-08-01. Los passes que apuntaban a 2022/23 quedan en espera del add-on histórico.
- **Contexto:** Validado empíricamente durante la ejecución del Atraco. El endpoint `/football/fixtures/date/{date}` devuelve vacío para fechas anteriores a ~2023-08-12 para las ligas Tier S (EPL, La Liga, Bundesliga, Serie A, Ligue 1). El endpoint `/leagues/{id}?include=seasons` confirma que el plan Pro (trial) solo expone **3 temporadas** para cada liga: 2023/24, 2024/25 y la próxima 2025/26. La temporada 2022/23 no está disponible sin el add-on histórico (€29 one-time).
- **Alternativas consideradas:**
  - Comprar el add-on €29 ahora: da acceso a 2022/23 y también a temporadas anteriores. Recomendado si el modelo de backtesting requiere >2 temporadas para ser estadísticamente robusto.
  - Continuar con 2 temporadas (2023-24 + 2024-25): ~760 partidos por liga × 5 ligas = ~3,800 fixtures. Suficiente para un MVP de backtesting.
- **Elegida:** Continuar con 2 temporadas disponibles. Si los primeros modelos de backtesting muestran varianza alta, se activa el add-on. La arquitectura ya está lista para reejecutar el Atraco con rango extendido.
- **Impacto:** Pass 1 cubre 670 días (2023-08-01 → 2025-05-31). Estimado: ~3,500-4,000 fixtures por liga × 5 ligas = ~17,500-20,000 filas en `raw_sportmonks_fixtures`. Peso estimado en disco: <500 MB incluyendo payload JSONB.
- **Filtro de ligas:** el endpoint `/fixtures/date/{date}` no acepta filtro multi-liga en URL. La estrategia es descargar TODAS las ligas por día (25 por página, ~10-12 páginas en días de jornada) y filtrar por `league_id` en Python antes de persistir. Costo: ~5,000-7,000 requests API para Pass 1 completo, dentro del límite de 3,000/hora del plan Pro.
- **Fecha:** 2026-04-05

---

## Pendiente de decisión

- **Cruce de identidades (bt2_event_identity_map):** la estrategia exacta para mapear `sportmonks_fixture_id` ↔ `theoddsapi_event_id` usando equipos + fecha como pivot. Se documenta en Sprint 03 cuando haya datos reales para validar la heurística.
- **Champions League (ID 2):** verificar si está disponible en páginas 51+ de la API o si requiere add-on de ligas. Evaluar en Sprint 03.
- **Sportmonks post-trial:** decidir si se baja a Starter (€29 + €15 odds) o se mantiene Growth (€99) según el volumen de datos que necesite el FE en producción.
- **Migración a cloud:** cuándo mover la base de datos de PostgreSQL local a Neon/Railway para staging. Sprint 03 cuando el FE empiece a consumir el BE real.
- **Alembic en CI/CD:** si se añade CD en Sprint 04+, evaluar `alembic upgrade head` como paso de despliegue automático.
