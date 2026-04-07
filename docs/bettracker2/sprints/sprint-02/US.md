# Sprint 02 - US (Fuente de verdad)

> Este archivo define qué se implementa en Sprint 02.
> Todo cambio técnico debe mapear a una US aquí.
> Prefijos obligatorios por capa: `US-BE-###`, `US-DX-###`, `US-OPS-###` (ver `../../01_CONTRATO_US.md`).

## Estado del sprint

- Fecha inicio: **2026-04-06**
- Fecha fin estimada: **2026-04-19** (ventana máxima del trial Pro de Sportmonks)
- Owner: Backend Agent / Arquitecto Principal
- Estado: **En curso** — infraestructura + ingesta dual (Sportmonks Pro + The-Odds-API $119)

## Contexto del sprint

Sprint 02 es el **sprint de datos**: aprovecha la ventana de **14 días del plan Pro de Sportmonks** (incluye add-ons Odds & Predictions + Pressure Index & xG) y la activación del plan de pago de The-Odds-API ($119) para ejecutar el **Atraco Masivo** — ingesta masiva de datos históricos antes de que expiren los planes. El código de dominio (ACL, CDM, auth JWT, conexión FE) se planifica en Sprint 03 una vez que los datos estén en PostgreSQL.

---

## Operaciones / Infraestructura

### US-OPS-001 — Infraestructura PostgreSQL local (Docker + pydantic-settings)

#### 1) Objetivo de negocio

Levantar la base de datos local que persistirá todos los snapshots del Atraco Masivo. Sin este paso ningún worker puede guardar datos. Es el **bloqueante** de todas las US-BE del sprint.

#### 2) Alcance

- Incluye:
  - `docker-compose.yml` en la raíz del repo con servicio `postgres:16-alpine`, base de datos `bettracker2`, usuario `bt2`, contraseña `bt2local`, puerto `5432`, volumen persistente `bt2_pg_data`.
  - `apps/api/bt2_settings.py` con `BaseSettings` de `pydantic-settings`: carga `.env` raíz, expone los campos tipados necesarios para el sprint (`sportmonks_api_key`, `theoddsapi_key`, `bt2_database_url`, `bt2_secret_key`, `bt2_environment`).
  - Actualizar `.env` raíz con los campos que aún no existen (`THEODDSAPI_KEY`, `BT2_DATABASE_URL`, `BT2_SECRET_KEY`, `BT2_ENVIRONMENT`).
  - Verificación básica de conexión: script o comando one-liner que confirme que FastAPI puede alcanzar Postgres.
- Excluye:
  - Migraciones de schema (US-BE-003).
  - Auth JWT (Sprint 03).
  - Despliegue en cloud (backlog US-OPS).

#### 3) Contexto técnico actual

- Módulos: raíz del repo (nuevo `docker-compose.yml`), `apps/api/bt2_settings.py` (nuevo), `.env` raíz (edición).
- `apps/api/main.py` actualmente carga vars con `os.getenv()` directamente — `bt2_settings.py` convive sin romper eso; la migración a `settings` es incremental.
- Dependencias nuevas: `pydantic-settings`, `asyncpg` (driver async para PostgreSQL), `psycopg2-binary` (opcional para Alembic sync).

#### 4) Contrato de entrada/salida

```json
{
  "input": {
    "envFile": ".env (raíz del repo)"
  },
  "output": {
    "postgresRunning": true,
    "bt2SettingsImportable": true,
    "connectionVerified": true
  }
}
```

#### 5) Reglas de dominio

- Regla 1: La API key de Sportmonks y de The-Odds-API **nunca se hardcodean** en código; solo en `.env` (que está en `.gitignore`).
- Regla 2: `bt2_settings.py` es la **única fuente** de lectura de variables de entorno para el módulo BT2; no duplicar `os.getenv()` en otros archivos nuevos.
- Regla 3: La contraseña de la base de datos local (`bt2local`) es solo para desarrollo; el campo `BT2_DATABASE_URL` en `.env` puede apuntar a Neon/Supabase en staging sin cambiar código.

#### 6) Criterios de aceptación (Given / When / Then)

1. Given el repo clonado con `.env` correctamente poblado, When se ejecuta `docker compose up -d`, Then el contenedor `bt2_pg` levanta sin error y responde en `localhost:5432`.
2. Given el servidor FastAPI arrancando, When se importa `from apps.api.bt2_settings import bt2_settings`, Then no lanza `ValidationError` y `bt2_settings.sportmonks_api_key` tiene valor no vacío.
3. Given las credenciales del `.env`, When se ejecuta el one-liner de verificación de conexión, Then retorna `"conexión exitosa"` sin `OperationalError`.

#### 7) No funcionales

- Performance: el contenedor Postgres debe levantar en < 10 s en hardware típico de desarrollo.
- Seguridad: `.env` en `.gitignore` confirmado; `docker-compose.yml` no contiene secretos hardcodeados (usa variables de entorno del shell o el `.env` vía `env_file`).
- Observabilidad: mensaje de log `[BT2] settings loaded — env: development` al importar `bt2_settings`.

#### 8) Riesgos y mitigación

- Riesgo: conflicto de puerto 5432 con Postgres nativo instalado en la máquina.
  - Mitigación: mapear el puerto como `"5433:5432"` en `docker-compose.yml` como alternativa documentada en comentario.
- Riesgo: `.env` con `BT2_DATABASE_URL` apuntando a un host incorrecto al cambiar de entorno.
  - Mitigación: `bt2_settings.py` valida que la URL comience con `postgresql` en startup.

#### 9) Plan de pruebas

- Manual: `docker compose up -d && docker compose ps` — estado `healthy`; `python -c "from apps.api.bt2_settings import bt2_settings; print(bt2_settings.bt2_environment)"` — imprime `development`.
- No requiere tests automatizados en este sprint; el DoD se valida con los criterios de aceptación manuales.

#### 10) Definition of Done

- [ ] T-063 completada: `docker-compose.yml` en raíz, contenedor levanta.
- [ ] T-064 completada: `apps/api/bt2_settings.py` importable sin error.
- [ ] T-065 completada: `.env` raíz con los 5 campos requeridos (no commiteado).
- [ ] Verificación de conexión exitosa documentada en `DECISIONES.md`.

---

### US-OPS-002 — Configuración de entorno de desarrollo (sin Docker)

#### 1) Objetivo de negocio

Dejar el entorno local completamente operativo para que los workers del Atraco Masivo puedan arrancar: variables de entorno correctas, dependencias Python instaladas, `bt2_settings.py` funcional y conexión a PostgreSQL verificada — sin romper el servidor V1 (scrapper SQLite) que corre en paralelo.

#### 2) Alcance

- Incluye:
  - Agregar al `.env` raíz los 4 campos BT2 faltantes: `BT2_DATABASE_URL`, `BT2_SECRET_KEY`, `BT2_ENVIRONMENT`, `THEODDSAPI_KEY`.
  - Instalar dependencias Python: `pydantic-settings`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `httpx`, `python-dotenv`, `psycopg2-binary`.
  - Crear `apps/api/bt2_settings.py` con `BaseSettings` de `pydantic-settings`. **Regla de oro: este módulo NO se importa en `apps/api/main.py`** — solo lo importan `bt2_router.py` y los scripts de `scripts/bt2_atraco/`.
  - Script de verificación one-liner que confirma conexión a PostgreSQL con las credenciales del `.env`.
  - `docker-compose.yml` **omitido** — el usuario usa Postgres.app v18 corriendo en `localhost:5432`, base de datos `bettracker2` ya creada, usuario `kevcast` (autenticación OS, sin contraseña).
- Excluye:
  - Modelos SQLAlchemy ni migraciones (US-BE-003).
  - Auth JWT ni cambios a rutas existentes de V1.
  - Modificar `apps/api/main.py` de ninguna forma.

#### 3) Contexto técnico actual

- **V1 en paralelo:** `apps/api/main.py` es el servidor compartido (scrapper SQLite + BT2 stub). Corre con `uvicorn apps.api.main:app --reload`. Cualquier error de importación en un módulo que se cargue al arrancar **derriba el servidor V1**. Por eso `bt2_settings.py` se importa solo desde módulos BT2, nunca desde `main.py`.
- PostgreSQL: Postgres.app v18, puerto `5432`, usuario `kevcast`, base de datos `bettracker2` ya creada.
- `.env` actual: tiene `SPORTMONKS_API_KEY` y variables de V1. Faltan las 4 variables BT2.
- Módulos a crear: `apps/api/bt2_settings.py` (nuevo).

#### 4) Contrato de entrada/salida

```json
{
  "input": {
    "postgresRunning": true,
    "databaseCreated": "bettracker2",
    "sportmonksApiKeyPresent": true
  },
  "output": {
    "envComplete": true,
    "dependenciesInstalled": true,
    "bt2SettingsImportable": true,
    "postgresConnectionVerified": true,
    "v1ServerUnaffected": true
  }
}
```

#### 5) Reglas de dominio

- **Regla 1 (no romper V1):** `bt2_settings.py` **nunca** se importa en `apps/api/main.py`. Si se necesita en `bt2_router.py`, el import va dentro de las funciones o al inicio del archivo `bt2_router.py`, no en `main.py`.
- **Regla 2:** `BT2_DATABASE_URL` usa el formato `postgresql+asyncpg://kevcast@localhost:5432/bettracker2` (sin contraseña — autenticación OS de Postgres.app).
- **Regla 3:** `THEODDSAPI_KEY` se deja vacío en el `.env` hasta que el socio active el plan — `bt2_settings.py` debe aceptar string vacío con `theoddsapi_key: str = ""`.
- **Regla 4:** Las dependencias se instalan con `pip install` en el entorno activo del proyecto. Si hay un `requirements.txt` o `pyproject.toml`, agregar las dependencias ahí también.
- **Regla 5:** El agente ejecutor verifica que el servidor V1 sigue respondiendo en `http://127.0.0.1:8000/health` después de crear `bt2_settings.py` — si falla, hacer rollback del archivo.

#### 6) Criterios de aceptación (Given / When / Then)

1. Given el `.env` con los 4 campos BT2 agregados, When se ejecuta `python -c "from apps.api.bt2_settings import bt2_settings; print(bt2_settings.bt2_environment)"`, Then imprime `development` sin error.
2. Given `bt2_settings.py` creado, When se reinicia el servidor V1 (`uvicorn apps.api.main:app --reload`), Then arranca sin `ValidationError` ni `ImportError` y `GET /health` responde `{"ok": true}`.
3. Given la conexión configurada, When se ejecuta el one-liner de verificación de conexión PostgreSQL, Then retorna confirmación de conexión exitosa a `bettracker2`.
4. Given `pip install` completado, When se ejecuta `python -c "import sqlalchemy, asyncpg, alembic, httpx, pydantic_settings"`, Then no lanza `ModuleNotFoundError`.

#### 7) No funcionales

- El agente ejecutor **debe verificar `/health` de V1** antes y después de cada cambio. Si V1 cae, rollback inmediato.
- Las dependencias instaladas no deben crear conflictos de versión con el stack existente de V1 (FastAPI, Pydantic v2, uvicorn).
- El `.env` no se commitea — el agente verifica que está en `.gitignore`.

#### 8) Riesgos y mitigación

- Riesgo: `pydantic-settings` importado en el scope global de `main.py` por error → V1 cae si falta un campo.
  - Mitigación: el agente ejecutor verifica con `grep -r "bt2_settings" apps/api/main.py` que el resultado esté vacío.
- Riesgo: `asyncpg` incompatible con la versión de Python del entorno.
  - Mitigación: verificar `python --version` antes de instalar; `asyncpg` requiere Python 3.8+.
- Riesgo: conflicto de versión entre `sqlalchemy>=2.0` y dependencias existentes de V1.
  - Mitigación: correr `pip install --dry-run` primero y revisar si hay conflictos antes de instalar.

#### 9) Plan de pruebas

- `python -c "from apps.api.bt2_settings import bt2_settings; print(bt2_settings.model_dump())"` — debe imprimir el dict con los campos sin la API key en texto claro (opcional).
- `curl http://127.0.0.1:8000/health` — debe retornar `{"ok": true, ...}` después de cada cambio.
- `python -c "import asyncpg, sqlalchemy, alembic"` — sin error.

#### 10) Definition of Done

- [ ] T-075 completada: 4 campos BT2 agregados al `.env`.
- [ ] T-076 completada: dependencias Python instaladas sin conflictos.
- [ ] T-077 completada: `bt2_settings.py` creado con import seguro, no referenciado en `main.py`.
- [ ] T-078 completada: conexión a PostgreSQL verificada.
- [ ] `GET /health` de V1 responde `{"ok": true}` después de todos los cambios.
- [ ] Decisión de import seguro documentada en `DECISIONES.md`.

---

## Backend

### US-BE-002 — Smoke Test de integración dual (Sportmonks + The-Odds-API)

#### 1) Objetivo de negocio

Confirmar en < 2 horas que ambas API keys funcionan y que la estructura de respuesta real es compatible con el CDM antes de lanzar el Atraco Masivo. Si algo falla aquí, el Atraco no comienza. El resultado queda documentado como contrato de campo confirmado.

#### 2) Alcance

- Incluye:
  - Script `scripts/bt2_smoke_test.py` que ejecuta **exactamente 4 requests** (2 por proveedor), imprime un resumen estructurado y genera el archivo `docs/bettracker2/recon_results/smoke_test_{FECHA}.md`.
  - **Sportmonks request 1:** `GET /football/leagues` — confirmar total de ligas, buscar Premier League (ID 8), La Liga (ID 564), Champions League (ID 2).
  - **Sportmonks request 2:** `GET /football/fixtures/date/{HOY}` con `include=participants;odds` — confirmar si el objeto `odds` está presente y su estructura.
  - **The-Odds-API request 1:** `GET /v4/sports` — confirmar que `soccer_epl` (Premier League) está en la lista.
  - **The-Odds-API request 2:** `GET /v4/odds?sport=soccer_epl&regions=eu&markets=h2h&dateFormat=iso` — confirmar estructura de `bookmakers[].markets[].outcomes`.
  - Directorio `docs/bettracker2/recon_results/` (crear si no existe).
- Excluye:
  - Persistencia en base de datos (aún no hay schema — US-BE-003).
  - Más de 10 requests totales para conservar créditos de ambos planes.
  - Mapeo CDM (se hace en Sprint 03 / ACL).

#### 3) Contexto técnico actual

- Módulos: `scripts/bt2_smoke_test.py` (nuevo), `apps/api/bt2_settings.py` (depende de US-OPS-001).
- Dependencias: `httpx` (async HTTP client), `python-dotenv` como fallback si `bt2_settings` no está disponible al correr el script standalone.
- Ejecutar desde la raíz: `python scripts/bt2_smoke_test.py`.

#### 4) Contrato de entrada/salida

```json
{
  "input": {
    "SPORTMONKS_API_KEY": "env var",
    "THEODDSAPI_KEY": "env var"
  },
  "output": {
    "sportmonks": {
      "leaguesTotal": "number",
      "premierLeagueId": "number | null",
      "oddsFieldPresent": "boolean",
      "oddsStructure": "object | null",
      "creditsRemaining": "number"
    },
    "theoddsapi": {
      "soccerEplAvailable": "boolean",
      "bookmakersCount": "number",
      "marketsStructure": "object | null",
      "requestsUsed": "number",
      "requestsRemaining": "number"
    }
  }
}
```

#### 5) Reglas de dominio

- Regla 1: Si un endpoint retorna 403 o 404, el script lo registra como `❌ No disponible en este plan` y **continúa** con el siguiente request; no lanza excepción fatal.
- Regla 2: El script imprime cuántos créditos/requests quedan de cada proveedor al finalizar.
- Regla 3: No hardcodear API keys en el script; leer desde `.env` vía `bt2_settings` o `python-dotenv`.
- Regla 4: Ningún campo de respuesta del proveedor se expone en el output markdown con nombre de proveedor como clave CDM — el reporte es un documento técnico interno, no un contrato de API.

#### 6) Criterios de aceptación (Given / When / Then)

1. Given ambas API keys configuradas en `.env`, When se ejecuta `python scripts/bt2_smoke_test.py`, Then el script termina en < 30 s sin excepción no capturada.
2. Given la ejecución completada, When se abre `docs/bettracker2/recon_results/smoke_test_{FECHA}.md`, Then contiene una tabla con `✅`/`❌` para cada campo confirmado de ambos proveedores.
3. Given un endpoint que retorna error HTTP, When el script lo detecta, Then registra el error y continúa con los siguientes requests.

#### 7) No funcionales

- Observabilidad: output con timestamps y prefijo `[SMOKE]` en cada request.
- Seguridad: el archivo de resultados puede commitearse (no contiene API keys ni datos sensibles de usuario).
- Portabilidad: el script funciona con Python 3.11+ sin dependencias fuera de `httpx` y `python-dotenv`.

#### 8) Riesgos y mitigación

- Riesgo: no hay partidos hoy → `fixtures/date/{HOY}` retorna lista vacía.
  - Mitigación: el script prueba también con la fecha de ayer si la respuesta de hoy está vacía.
- Riesgo: The-Odds-API cobra créditos por cada mercado y región solicitada.
  - Mitigación: la request usa solo `markets=h2h&regions=eu` (costo mínimo).

#### 9) Plan de pruebas

- Manual: ejecutar el script y verificar el archivo generado en `recon_results/`.
- Verificación: el archivo `.md` generado debe tener al menos 10 líneas con contenido no vacío.

#### 10) Definition of Done

- [ ] T-066 completada: requests Sportmonks ejecutadas y campos documentados.
- [ ] T-067 completada: requests The-Odds-API ejecutadas y campos documentados.
- [ ] T-068 completada: archivo `smoke_test_{FECHA}.md` generado en `recon_results/`.
- [ ] No se excedieron 10 requests totales combinadas.
- [ ] Resultado leído y aprobado por el arquitecto principal antes de lanzar US-BE-004.

---

### US-BE-003 — Schema PostgreSQL para snapshots del Atraco

#### 1) Objetivo de negocio

Definir las tablas que almacenarán los snapshots históricos crudos de ambos proveedores. El diseño prioriza **capturar el máximo de datos** con el mínimo de transformación — se persiste el JSON raw del proveedor en `JSONB` y los metadatos de indexación como columnas tipadas. La normalización CDM se hace en Sprint 03.

#### 2) Alcance

- Incluye:
  - `apps/api/bt2_models.py` con modelos SQLAlchemy 2.0 (`DeclarativeBase`, tipos tipados):
    - `RawSportmonksFixture`: `id (PK)`, `fixture_id (int, unique)`, `fixture_date (date)`, `league_id (int)`, `home_team (str)`, `away_team (str)`, `payload (JSONB)`, `fetched_at (datetime)`.
    - `RawTheoddsapiSnapshot`: `id (PK)`, `event_id (str, unique por fetch)`, `sport_key (str)`, `commence_time (datetime)`, `home_team (str)`, `away_team (str)`, `payload (JSONB)`, `fetched_at (datetime)`.
    - `Bt2EventIdentityMap`: `id (PK)`, `sportmonks_fixture_id (int, FK → raw_sportmonks_fixtures.fixture_id, nullable)`, `theoddsapi_event_id (str, nullable)`, `home_team (str)`, `away_team (str)`, `commence_time (datetime)`, `league_slug (str)`, `mapped_at (datetime)`, `confidence (str)` — para el cruce de identidades entre proveedores.
  - Setup de Alembic en `apps/api/alembic/` con `alembic.ini` en `apps/api/`.
  - Primera migración (`revision initial`) que crea las tres tablas.
- Excluye:
  - Tablas del dominio conductual (usuarios, sesiones, picks normalizados, ledger) — Sprint 03.
  - Relaciones hacia el CDM de usuario (FK hacia `users`) — Sprint 03.
  - Índices de búsqueda full-text — se añaden cuando el volumen lo justifique.

#### 3) Contexto técnico actual

- Módulos: `apps/api/bt2_models.py` (nuevo), `apps/api/alembic/` (nuevo), `apps/api/alembic.ini` (nuevo).
- Dependencias nuevas: `sqlalchemy>=2.0`, `alembic`, `asyncpg` (ya requerido en US-OPS-001).
- `BT2_DATABASE_URL` debe usar el prefijo `postgresql+asyncpg://` para async o `postgresql://` para las migraciones de Alembic (sync).

#### 4) Contrato de entrada/salida

```json
{
  "input": {
    "BT2_DATABASE_URL": "postgresql+asyncpg://bt2:bt2local@localhost:5432/bettracker2"
  },
  "output": {
    "tablesCreated": [
      "raw_sportmonks_fixtures",
      "raw_theoddsapi_snapshots",
      "bt2_event_identity_map"
    ],
    "alembicHeadApplied": true
  }
}
```

#### 5) Reglas de dominio

- Regla 1: El campo `payload` en las tablas raw es **inmutable post-ingesta** — nunca se actualiza el JSON crudo; si hay una versión nueva del mismo fixture, se inserta una nueva fila con `fetched_at` distinto.
- Regla 2: El campo `fixture_id` de Sportmonks y `event_id` de The-Odds-API no son globalmente únicos entre sí — son únicos dentro de su proveedor.
- Regla 3: La tabla `bt2_event_identity_map` es de uso interno del backend; **nunca se expone** directamente a través de una ruta `/bt2/*`.
- Regla 4: Todos los timestamps en UTC (`timezone=True` en SQLAlchemy).

#### 6) Criterios de aceptación (Given / When / Then)

1. Given `docker-compose up -d` corriendo (US-OPS-001), When se ejecuta `alembic upgrade head` desde `apps/api/`, Then las tres tablas existen en PostgreSQL sin error.
2. Given las tablas creadas, When se inserta una fila de prueba en `raw_sportmonks_fixtures` con un `payload` JSONB arbitrario, Then la inserción tiene éxito y la fila es recuperable por `fixture_id`.
3. Given el modelo SQLAlchemy importado, When se ejecuta `from apps.api.bt2_models import RawSportmonksFixture`, Then no lanza `ImportError` ni error de mapeo.

#### 7) No funcionales

- Migraciones idempotentes: `alembic upgrade head` sobre una base ya migrada no debe fallar.
- Nomenclatura snake_case en nombres de tabla y columna (convención PostgreSQL).
- Índice en `fixture_date` de `raw_sportmonks_fixtures` y en `sport_key + commence_time` de `raw_theoddsapi_snapshots` para queries de rango en el Atraco.

#### 8) Riesgos y mitigación

- Riesgo: cambio de schema durante el Atraco requiere migración sobre datos ya ingestados.
  - Mitigación: el diseño con JSONB en `payload` absorbe cambios de estructura del proveedor sin migración; solo las columnas de metadatos son tipadas.
- Riesgo: conflicto entre `asyncpg` (async) y Alembic (sync).
  - Mitigación: `alembic.ini` usa `BT2_DATABASE_URL` con prefijo `postgresql://` (sync); los modelos en `bt2_models.py` usan `postgresql+asyncpg://` para el runtime; documentado en `DECISIONES.md`.

#### 9) Plan de pruebas

- Manual: `alembic upgrade head && alembic current` — debe mostrar la revisión aplicada.
- Inserción de prueba vía `psql` o script Python one-liner.
- `alembic downgrade -1 && alembic upgrade head` — idempotencia verificada.

#### 10) Definition of Done

- [ ] T-069 completada: `bt2_models.py` con los tres modelos SQLAlchemy 2.0.
- [ ] T-070 completada: Alembic configurado y primera migración aplicada con éxito.
- [ ] T-071 completada: `Bt2EventIdentityMap` con estructura de cruce de identidades.
- [ ] `alembic upgrade head` funciona sobre base limpia sin error.
- [ ] Decisión de URL sync vs async documentada en `DECISIONES.md`.

---

### US-BE-004 — Workers del Atraco Masivo (ingesta en 3 pasadas, Sportmonks primero)

#### 1) Objetivo de negocio

Ingestar el máximo volumen posible de datos históricos de fútbol en la ventana de 14 días del plan Pro de Sportmonks, usando una estrategia de **3 pasadas priorizadas por valor de backtesting**. La meta es dejar en PostgreSQL al menos 4 temporadas de las 5 ligas top europeas + 2 temporadas de 7 ligas secundarias antes de que expire el trial. The-Odds-API se ejecuta en paralelo si el plan está activo, pero **no bloquea** el Atraco de Sportmonks.

**Liga BetPlay Colombia (ID 672) incluida en Pass 2** por ser el mercado objetivo del producto.

#### 2) Alcance

- Incluye:
  - `scripts/bt2_atraco/sportmonks_worker.py`: itera por **liga + temporada** (no por fecha diaria). Llama `GET /football/fixtures/between/{start}/{end}?filters=fixtureLeagues:{id}` con `include=participants;odds;statistics;events;league;scores`. Persiste en `raw_sportmonks_fixtures` vía `INSERT ON CONFLICT DO NOTHING`. Manejo de 429: pausa 60 min y reintenta.
  - `scripts/bt2_atraco/theoddsapi_worker.py`: itera sports + fechas vía `GET /v4/historical/odds?sport={sport}&date={fecha}&regions=eu&markets=h2h,totals`. Persiste en `raw_theoddsapi_snapshots`. Mantiene cache local `scripts/bt2_atraco/.cache_theoddsapi.json` de `(sport_key, date)` ya fetched. **Si el plan no está activo, el worker imprime un aviso y retorna 0 filas — no lanza excepción.**
  - `scripts/bt2_atraco/run_atraco.py`: orquestador con parámetro `--pass [1|2|3|all]`. Lanza ambos workers en paralelo con `asyncio.gather`. Reporte de progreso cada 50 fixtures y log de créditos consumidos en cierre.
  - `scripts/bt2_atraco/league_config.py`: archivo de configuración con las ligas por pasada (ver §4), reutilizable por cualquier worker.
  - `scripts/bt2_atraco/__init__.py`.
- Excluye:
  - Normalización al CDM (Sprint 03).
  - Llenado de `bt2_event_identity_map` (job posterior, Sprint 03).
  - Datos de usuarios, picks o ledger.

#### 3) Contexto técnico actual

- Depende de: `apps/api/bt2_models.py` (US-BE-003), `apps/api/bt2_settings.py` (US-OPS-002).
- Dependencias Python: `httpx`, `sqlalchemy[asyncio]`, `asyncpg`. Ya instaladas en US-OPS-002.
- Ejecución desde la raíz del proyecto:
  ```bash
  # Pass 1 (Tier S — 4 temporadas, 5 ligas top)
  python scripts/bt2_atraco/run_atraco.py --pass 1

  # Pass 2 (Tier A — 2 temporadas, 7 ligas secundarias)
  python scripts/bt2_atraco/run_atraco.py --pass 2

  # Pass 3 (Tier B — 1 temporada, ligas de contexto)
  python scripts/bt2_atraco/run_atraco.py --pass 3
  ```

#### 4) Configuración de pasadas (league_config.py)

```python
PASS_CONFIG = {
    1: {
        "name": "Tier S — Top 5 Europa",
        "leagues": [
            {"id": 8,   "name": "Premier League",  "seasons": ["2021/2022", "2022/2023", "2023/2024", "2024/2025"]},
            {"id": 564, "name": "La Liga",          "seasons": ["2021/2022", "2022/2023", "2023/2024", "2024/2025"]},
            {"id": 82,  "name": "Bundesliga",       "seasons": ["2021/2022", "2022/2023", "2023/2024", "2024/2025"]},
            {"id": 384, "name": "Serie A",          "seasons": ["2021/2022", "2022/2023", "2023/2024", "2024/2025"]},
            {"id": 301, "name": "Ligue 1",          "seasons": ["2021/2022", "2022/2023", "2023/2024", "2024/2025"]},
        ],
        "sm_requests_estimate": 600,
    },
    2: {
        "name": "Tier A — Ligas secundarias (alta cobertura bookmakers)",
        "leagues": [
            {"id": 72,  "name": "Eredivisie",        "seasons": ["2022/2023", "2023/2024"]},
            {"id": 208, "name": "Pro League Bélgica", "seasons": ["2022/2023", "2023/2024"]},
            {"id": 462, "name": "Liga Portugal",     "seasons": ["2022/2023", "2023/2024"]},
            {"id": 600, "name": "Super Lig",         "seasons": ["2022/2023", "2023/2024"]},
            {"id": 453, "name": "Ekstraklasa",       "seasons": ["2022/2023", "2023/2024"]},
            {"id": 501, "name": "Premiership Escocia","seasons": ["2022/2023", "2023/2024"]},
        ],
        # Liga BetPlay Colombia (ID 672): descartada del Atraco.
        # Motivo: cobertura de bookmakers europeos no verificada en Sportmonks Standard Odds.
        # Sin odds de bookmakers solventes, los fixtures son solo marcadores — sin valor
        # para backtesting de expected value. Reevaluar en Sprint 04 si se activa The-Odds-API
        # y se confirma cobertura LATAM con datos reales.
        "sm_requests_estimate": 300,
    },
    3: {
        "name": "Tier B — Ligas de contexto",
        "leagues": [
            {"id": 9,   "name": "Championship",    "seasons": ["2023/2024"]},
            {"id": 85,  "name": "2. Bundesliga",   "seasons": ["2023/2024"]},
            {"id": 304, "name": "Ligue 2",         "seasons": ["2023/2024"]},
            {"id": 387, "name": "Serie B",         "seasons": ["2023/2024"]},
            {"id": 779, "name": "MLS",             "seasons": ["2024"]},
            {"id": 743, "name": "Liga MX",         "seasons": ["2023/2024"]},
        ],
        "sm_requests_estimate": 200,
    },
}

# Créditos totales estimados: ~1,150 / 2,992 disponibles
# Champions League (ID 2): no disponible en plan actual — gap documentado
```

#### 5) Contrato de entrada/salida

```json
{
  "input": {
    "pass": 1,
    "theoddsapi_active": false
  },
  "output": {
    "sportmonks": {
      "fixturesFetched": "number",
      "fixturesStored": "number",
      "requestsUsed": "number",
      "requestsRemaining": "number",
      "errors": []
    },
    "theoddsapi": {
      "skipped": true,
      "reason": "plan not active",
      "snapshotsStored": 0
    },
    "durationMinutes": "number",
    "logFile": "scripts/bt2_atraco/atraco_pass1_YYYYMMDD.log"
  }
}
```

#### 6) Reglas de dominio

- Regla 1: Ante 429, el worker espera **60 minutos** antes de reintentar. Log: `[SM-WORKER] Rate limit — pausing 60 min`.
- Regla 2: Ante 5xx, reintenta hasta **3 veces** con backoff exponencial (2s, 4s, 8s). Al tercer fallo registra error y **continúa con la siguiente liga/temporada**.
- Regla 3: `INSERT ON CONFLICT DO NOTHING` en ambas tablas — la clave de conflicto es `(fixture_id, provider)` para Sportmonks y `(event_id, snapshot_date)` para The-Odds-API.
- Regla 4: Si `THEODDSAPI_KEY` no está configurada o el plan está inactivo, el worker de The-Odds-API omite la ejecución con aviso `[ODDS-WORKER] No active plan — skipping`. No lanza excepción.
- Regla 5: Reporte de progreso cada 50 fixtures. Log final con totales de cada liga y créditos consumidos.
- Regla 6: Al finalizar cada pasada, el log se archiva en `docs/bettracker2/recon_results/atraco_pass{N}_{fecha}.log`.

#### 7) Criterios de aceptación (Given / When / Then)

1. Given el schema de US-BE-003 aplicado, When se ejecuta `run_atraco.py --pass 1`, Then la tabla `raw_sportmonks_fixtures` recibe datos de las 5 ligas del Pass 1 y el log reporta créditos restantes de Sportmonks.
2. Given que `THEODDSAPI_KEY` no está en `.env`, When el orquestador lanza el worker de The-Odds-API, Then el worker imprime aviso de skip y `raw_theoddsapi_snapshots` queda vacía sin error.
3. Given un 429 de Sportmonks durante el Pass 1, When el worker lo detecta, Then registra el evento en log, espera 60 min y retoma la misma liga/temporada sin perder el progreso anterior.
4. Given que el proceso se interrumpe a mitad del Pass 2, When se relanza `--pass 2`, Then `ON CONFLICT DO NOTHING` evita duplicados y el worker continúa con las ligas pendientes.
5. Given el Pass 1 completado, When se ejecuta `SELECT COUNT(*), league_id FROM raw_sportmonks_fixtures GROUP BY league_id`, Then aparecen las 5 ligas (IDs 8, 564, 82, 384, 301) con conteos mayores a 0.

#### 8) No funcionales

- Performance: workers en paralelo vía `asyncio.gather` — Sportmonks y The-Odds-API no se bloquean mutuamente.
- Observabilidad: prefijos `[SM-WORKER]` y `[ODDS-WORKER]` en todos los logs.
- Resiliencia: proceso reanudable sin pérdida de datos ya ingestados.
- Seguridad: API keys nunca en logs; solo créditos restantes.

#### 9) Riesgos y mitigación

- Riesgo: Champions League (ID 2) no disponible en el plan actual.
  - Mitigación: documentado. Se puede intentar en Pass 3 o verificar si aparece en paginación 51+.
- Riesgo: temporadas de Colombia tienen formato diferente (`"2022"` vs `"2022/2023"`).
  - Mitigación: `league_config.py` define el formato exacto por liga; el worker lo usa sin transformar.
- Riesgo: el disco local se llena con JSONB masivo.
  - Mitigación: estimar ~2 KB por fixture; 20,000 fixtures ≈ 40 MB — manejable. Monitorear antes del Pass 3.

#### 10) Definition of Done

- [ ] T-072 completada: `sportmonks_worker.py` con iteración por liga/temporada, `league_config.py`, persistencia JSONB y manejo de 429.
- [ ] T-073 completada: `theoddsapi_worker.py` con graceful skip si plan inactivo, cache local y manejo de rate limit.
- [ ] T-074 completada: `run_atraco.py` con parámetro `--pass [1|2|3|all]`, parallelismo `asyncio.gather` y log archivado.
- [ ] Pass 1 completado: datos de las 5 ligas top en `raw_sportmonks_fixtures`.
- [ ] Pass 2 completado: datos de 7 ligas secundarias incluyendo Liga BetPlay.
- [ ] No hay duplicados tras relanzar cualquier pasada.
- [ ] Log de cierre de cada pasada archivado en `docs/bettracker2/recon_results/`.
