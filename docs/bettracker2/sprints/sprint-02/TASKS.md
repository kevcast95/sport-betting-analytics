# Sprint 02 - Tasks

## Estado general

Las tareas **T-001 … T-062** corresponden al Sprint 01 (FE + BE stub). Las tareas de Sprint 02 comienzan en **T-063**.

**Ventana crítica:** los 14 días del plan Pro de Sportmonks y el plan activo de The-Odds-API definen el deadline real de este sprint. Priorizar en este orden:
1. US-OPS-001 (infraestructura — bloqueante)
2. US-BE-003 (schema — bloqueante para workers)
3. US-BE-002 (smoke test — validar antes del Atraco)
4. US-BE-004 (Atraco Masivo — el objetivo principal)

**Orden recomendado para el agente ejecutor:** T-075 → T-076 → T-077 → T-078 → T-069 → T-070 → T-071 → T-066 → T-067 → T-068 → T-072 → T-073 → T-074.

> **Nota:** T-063, T-064 y T-065 de US-OPS-001 quedan **supersedidas** por T-075…T-078 de US-OPS-002. El usuario usa Postgres.app v18 (sin Docker). La base de datos `bettracker2` ya fue creada manualmente.

---

## Backlog ejecutable

### Ola US-OPS-002 — Configuración de entorno de desarrollo (PRIMER PASO — ejecutar antes que todo)

- [x] T-075 (US-OPS-002) — Agregar al `.env` raíz los siguientes campos si no existen (no sobreescribir los que ya están):
  ```
  BT2_DATABASE_URL=postgresql+asyncpg://kevcast@localhost:5432/bettracker2
  BT2_SECRET_KEY=cambia-esto-en-produccion
  BT2_ENVIRONMENT=development
  THEODDSAPI_KEY=
  ```
  Verificar que `SPORTMONKS_API_KEY` ya existe. Confirmar que `.env` está en `.gitignore`.

- [x] T-076 (US-OPS-002) — Instalar dependencias Python en el entorno activo del proyecto:
  ```bash
  pip install "pydantic-settings>=2.0" "sqlalchemy[asyncio]>=2.0" asyncpg alembic httpx python-dotenv psycopg2-binary
  ```
  Si existe `requirements.txt` o `pyproject.toml` en la raíz, agregar las dependencias ahí también. Verificar con `python -c "import sqlalchemy, asyncpg, alembic, httpx, pydantic_settings"`.

- [x] T-077 (US-OPS-002) — Crear `apps/api/bt2_settings.py` con el siguiente contenido:
  ```python
  import logging
  from pydantic_settings import BaseSettings

  logger = logging.getLogger(__name__)

  class BT2Settings(BaseSettings):
      sportmonks_api_key: str
      theoddsapi_key: str = ""
      bt2_database_url: str
      bt2_secret_key: str = "dev-secret-change-me"
      bt2_environment: str = "development"

      model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

  bt2_settings = BT2Settings()
  logger.info("[BT2] settings loaded — env: %s", bt2_settings.bt2_environment)
  ```
  **CRÍTICO:** Verificar con `grep -r "bt2_settings" apps/api/main.py` que el resultado esté **vacío** — `bt2_settings` nunca se importa en `main.py`. Si aparece, eliminar la línea de `main.py`. Después verificar que V1 sigue en pie: `curl http://127.0.0.1:8000/health` debe retornar `{"ok": true}`.

- [x] T-078 (US-OPS-002) — Verificar conexión a PostgreSQL ejecutando desde la raíz del repo:
  ```bash
  python -c "
  import asyncio, asyncpg
  async def check():
      conn = await asyncpg.connect('postgresql://kevcast@localhost:5432/bettracker2')
      ver = await conn.fetchval('SELECT version()')
      await conn.close()
      print('Conexión exitosa:', ver[:40])
  asyncio.run(check())
  "
  ```
  Si falla con `OperationalError`, documentar el error en `DECISIONES.md` y ajustar la URL. Hacer `curl http://127.0.0.1:8000/health` como último paso para confirmar que V1 no fue afectado.

---

### Ola US-OPS-001 — Infraestructura PostgreSQL local (SUPERSEDIDA por US-OPS-002)

> El usuario usa Postgres.app v18 — Docker no es necesario. Base de datos `bettracker2` ya creada. T-063…T-065 canceladas; cubiertas por T-075…T-078.

- [x] ~~T-063 (US-OPS-001)~~ — cancelada (Postgres.app reemplaza Docker)
- [x] ~~T-064 (US-OPS-001)~~ — cubierta por T-077
- [x] ~~T-065 (US-OPS-001)~~ — cubierta por T-075

---

### Ola US-BE-003 — Schema PostgreSQL (ejecutar antes del smoke test)

- [x] T-069 (US-BE-003) — Crear `apps/api/bt2_models.py` con `DeclarativeBase` de SQLAlchemy 2.0 y los modelos:
  - `RawSportmonksFixture`: tabla `raw_sportmonks_fixtures` — columnas `id (BigInteger PK autoincrement)`, `fixture_id (Integer, unique, not null)`, `fixture_date (Date, index)`, `league_id (Integer)`, `home_team (String(200))`, `away_team (String(200))`, `payload (JSONB, not null)`, `fetched_at (DateTime(timezone=True), default=now)`.
  - `RawTheoddsapiSnapshot`: tabla `raw_theoddsapi_snapshots` — columnas `id (BigInteger PK autoincrement)`, `event_id (String(100), not null)`, `sport_key (String(100), index)`, `commence_time (DateTime(timezone=True), index)`, `home_team (String(200))`, `away_team (String(200))`, `payload (JSONB, not null)`, `fetched_at (DateTime(timezone=True), default=now)`. Índice compuesto en `(sport_key, commence_time)`.
  - `Bt2EventIdentityMap`: tabla `bt2_event_identity_map` — columnas `id (BigInteger PK autoincrement)`, `sportmonks_fixture_id (Integer, nullable)`, `theoddsapi_event_id (String(100), nullable)`, `home_team (String(200))`, `away_team (String(200))`, `commence_time (DateTime(timezone=True))`, `league_slug (String(100))`, `mapped_at (DateTime(timezone=True), default=now)`, `confidence (String(20), default="low")`.
- [x] T-070 (US-BE-003) — Instalar Alembic (`pip install alembic`) y ejecutar `alembic init alembic` desde `apps/api/`. Configurar `alembic.ini` para que use la URL sync (`postgresql://bt2:bt2local@localhost:5432/bettracker2`). Configurar `env.py` para importar `bt2_models.Base.metadata`. Generar primera migración: `alembic revision --autogenerate -m "initial snapshot tables"`. Aplicar: `alembic upgrade head`.
- [x] T-071 (US-BE-003) — Verificar la migración: `alembic current` muestra la revisión head; `\dt` en psql lista las tres tablas. Insertar una fila de prueba en `raw_sportmonks_fixtures` con `fixture_id=1, fixture_date=hoy, payload={"test": true}` y verificar con SELECT. Documentar el resultado en `DECISIONES.md`.

---

### Ola US-BE-002 — Smoke Test de integración dual

- [x] T-066 (US-BE-002) — Crear `scripts/bt2_smoke_test.py`. Implementar función `check_sportmonks()` que ejecuta:
  1. `GET https://api.sportmonks.com/v3/football/leagues?api_token={KEY}` — extraer total de ligas, buscar Premier League ID 8, La Liga ID 564, Champions ID 2. Reportar campo `has_odds` si existe.
  2. `GET https://api.sportmonks.com/v3/football/fixtures/date/{HOY}?api_token={KEY}&include=participants;odds` — extraer el shape exacto del campo `odds` en el primer fixture encontrado. Si hoy no hay fixtures, intentar con ayer.
  Imprimir resultados con prefijo `[SMOKE][SM]`. Capturar `RateLimit-Remaining` del header si está disponible.
- [x] T-067 (US-BE-002) — En el mismo `scripts/bt2_smoke_test.py`, implementar función `check_theoddsapi()` que ejecuta:
  1. `GET https://api.the-odds-api.com/v4/sports?apiKey={KEY}` — confirmar que `soccer_epl` está en la lista. Extraer `x-requests-remaining` del header.
  2. `GET https://api.the-odds-api.com/v4/odds?sport=soccer_epl&regions=eu&markets=h2h&dateFormat=iso&apiKey={KEY}` — extraer estructura de `bookmakers[0].markets[0].outcomes` del primer evento. Reportar `x-requests-used` y `x-requests-remaining`.
  Imprimir resultados con prefijo `[SMOKE][ODDS]`.
- [x] T-068 (US-BE-002) — En `scripts/bt2_smoke_test.py`, función `generate_report()` que crea el directorio `docs/bettracker2/recon_results/` (si no existe) y escribe `smoke_test_{YYYY-MM-DD}.md` con el siguiente formato:
  ```markdown
  # Smoke Test — {FECHA}
  ## Sportmonks
  - Ligas totales: X
  - Premier League (ID 8): ✅/❌
  - La Liga (ID 564): ✅/❌
  - Champions (ID 2): ✅/❌
  - Campo odds en fixture: ✅/❌
  - Estructura odds: {shape o "no disponible"}
  - Créditos restantes: X / 3000
  ## The-Odds-API
  - soccer_epl disponible: ✅/❌
  - Bookmakers retornados: X
  - Estructura outcomes: {shape o "no disponible"}
  - Requests usados: X
  - Requests restantes: X
  ## Decisión: ✅ Proceder con Atraco / ❌ Revisar antes de continuar
  ```
  El main del script llama a las tres funciones y termina con exit code 0.

---

### Ola US-BE-004 — Atraco Masivo (3 pasadas)

- [ ] T-072 (US-BE-004) — Crear `scripts/bt2_atraco/__init__.py` (vacío), `scripts/bt2_atraco/league_config.py` y `scripts/bt2_atraco/sportmonks_worker.py`. Implementar:
  - `league_config.py`: diccionario `PASS_CONFIG` con las 3 pasadas exactas definidas en US-BE-004 §4 (ligas, IDs, temporadas, estimado de requests). Importable por el orquestador.
  - Función `fetch_fixtures_for_season(league_id, season, session)` — `GET /football/fixtures/between/{start}/{end}?filters=fixtureLeagues:{league_id}&include=participants;odds;statistics;events;league;scores`. Retorna lista de fixtures.
  - Función `store_fixtures(fixtures, db_session)` — inserta en `raw_sportmonks_fixtures` con `INSERT ... ON CONFLICT (fixture_id, provider) DO NOTHING`.
  - Función `run_sportmonks(pass_number)` — itera las ligas/temporadas del pass indicado, llama fetch + store, maneja 429 (pausa 3600 s log `[SM-WORKER] Rate limit — pausing 60 min`), maneja 5xx (3 reintentos backoff 2/4/8 s), log `[SM-WORKER]` con progreso cada 50 fixtures. Al terminar cada liga, imprime subtotales.
- [ ] T-073 (US-BE-004) — Crear `scripts/bt2_atraco/theoddsapi_worker.py`. Implementar:
  - Al inicio, verificar que `THEODDSAPI_KEY` esté en el entorno. Si no está o está vacía, imprimir `[ODDS-WORKER] No active plan — skipping` y retornar `{"skipped": True, "snapshotsStored": 0}` sin lanzar excepción.
  - Cache local `scripts/bt2_atraco/.cache_theoddsapi.json` — formato `{"sport_key:date": true}`.
  - Función `fetch_odds_snapshot(sport_key, date, session)` — `GET /v4/historical/odds?sport={sport}&date={date}&regions=eu&markets=h2h,totals`. Retorna lista de eventos.
  - Función `store_snapshots(events, db_session)` — inserta en `raw_theoddsapi_snapshots` con `ON CONFLICT DO NOTHING` (conflicto en `event_id + snapshot_date`).
  - Función `run_theoddsapi(pass_number)` — itera sports del pass por rango de fechas (derivado de las temporadas en `PASS_CONFIG`), consulta cache, llama fetch + store, actualiza cache. Log `[ODDS-WORKER]` con requests restantes en header.
- [ ] T-074 (US-BE-004) — Crear `scripts/bt2_atraco/run_atraco.py`. Implementar:
  - Parser de argumentos: `--pass [1|2|3|all]` (obligatorio), `--dry-run` (opcional — no persiste, solo loguea).
  - `asyncio.gather(run_sportmonks(pass_number), run_theoddsapi(pass_number))` para ejecución paralela.
  - Reporte final por pasada: filas insertadas por tabla + por liga, créditos/requests consumidos, duración en minutos.
  - Guardar el reporte en `docs/bettracker2/recon_results/atraco_pass{N}_{YYYYMMDD}.md`.
  - Orden de ejecución recomendado en docstring:
    ```
    python scripts/bt2_atraco/run_atraco.py --pass 1   # Días 1-4
    python scripts/bt2_atraco/run_atraco.py --pass 2   # Días 5-9
    python scripts/bt2_atraco/run_atraco.py --pass 3   # Días 10-12
    ```

---

## Reglas

- Cada task debe referenciar una US con prefijo (`US-BE-###`, `US-OPS-###`).
- No iniciar T-066…T-068 sin que T-063…T-065 y T-069…T-071 estén completas.
- No iniciar T-072…T-074 sin que T-066…T-068 hayan producido un reporte `✅ Proceder`.
- El agente ejecutor verifica tasks por número: filtrar `[ ]` en este archivo para ver pendientes.
