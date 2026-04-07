# Sprint 02 - QA Checklist

**Auditoría de cierre:** verificar contra `apps/api/`, `scripts/`, `docker-compose.yml` y PostgreSQL local.

**Premisa de cierre:**
- [ ] US-OPS-001, US-BE-002, US-BE-003 y US-BE-004 tienen DoD marcado en `US.md`.
- [ ] T-063 … T-074 marcadas como `[x]` en `TASKS.md`.
- [ ] `DECISIONES.md` actualizado con cualquier trade-off adicional encontrado durante la implementación.
- [ ] No hay API keys expuestas en ningún archivo commiteado.
- [ ] No hay nombres de proveedor en contratos de salida CDM (las tablas raw son internas — permitido en `payload JSONB` y columnas técnicas de backend).

---

## Bloque 1 — Infraestructura PostgreSQL (US-OPS-001, T-063…T-065)

### Docker y base de datos (T-063)
- [ ] `docker-compose.yml` existe en la raíz del repo.
- [ ] `docker compose up -d` levanta el contenedor `bt2_db` sin error.
- [ ] `docker compose ps` muestra estado `running` o `healthy`.
- [ ] El contenedor escucha en `localhost:5432`.
- [ ] El volumen `bt2_pg_data` persiste datos entre reinicios (`docker compose down && docker compose up -d` → datos intactos).

### bt2_settings.py (T-064)
- [ ] `apps/api/bt2_settings.py` existe y es importable: `python -c "from apps.api.bt2_settings import bt2_settings; print('ok')"`.
- [ ] `bt2_settings.sportmonks_api_key` no está vacío cuando el `.env` tiene la key.
- [ ] `bt2_settings.bt2_environment` retorna `"development"` con la config local.
- [ ] Si falta un campo requerido en `.env`, lanza `ValidationError` con mensaje claro.
- [ ] El módulo imprime `[BT2] settings loaded` al importarse.

### Variables de entorno (T-065)
- [ ] `.env` contiene los 5 campos: `SPORTMONKS_API_KEY`, `THEODDSAPI_KEY`, `BT2_DATABASE_URL`, `BT2_SECRET_KEY`, `BT2_ENVIRONMENT`.
- [ ] `.gitignore` confirma que `.env` está ignorado (`git status` no muestra `.env` como untracked si ya estaba, o lo muestra como ignorado).
- [ ] `BT2_DATABASE_URL` tiene prefijo `postgresql+asyncpg://`.

---

## Bloque 2 — Schema PostgreSQL (US-BE-003, T-069…T-071)

### Modelos SQLAlchemy (T-069)
- [ ] `apps/api/bt2_models.py` existe y es importable sin error.
- [ ] Los tres modelos existen: `RawSportmonksFixture`, `RawTheoddsapiSnapshot`, `Bt2EventIdentityMap`.
- [ ] Los modelos usan SQLAlchemy 2.0 (`DeclarativeBase`, tipos de columna tipados).
- [ ] El campo `payload` en los modelos raw es de tipo `JSONB` (no `JSON` ni `Text`).
- [ ] Todos los timestamps tienen `timezone=True`.

### Alembic y migración (T-070)
- [ ] `apps/api/alembic/` existe con `env.py`, `versions/`, `script.py.mako`.
- [ ] `apps/api/alembic.ini` existe con `sqlalchemy.url` correctamente configurado (URL sync).
- [ ] `alembic upgrade head` aplicado desde `apps/api/` sin error.
- [ ] `alembic current` muestra la revisión activa correcta.
- [ ] `alembic downgrade -1 && alembic upgrade head` completa sin error (idempotencia).

### Verificación de tablas (T-071)
- [ ] `\dt` en psql (o `SELECT tablename FROM pg_tables WHERE schemaname='public'`) lista las tres tablas.
- [ ] Inserción de prueba en `raw_sportmonks_fixtures` exitosa: `fixture_id=1, fixture_date=hoy, payload={"test": true}`.
- [ ] `INSERT ... ON CONFLICT (fixture_id) DO NOTHING` no lanza error al reinsertar el mismo `fixture_id`.
- [ ] Índice en `fixture_date` confirmado: `\di raw_sportmonks_fixtures*` muestra el índice.
- [ ] Índice compuesto en `(sport_key, commence_time)` de `raw_theoddsapi_snapshots` confirmado.

---

## Bloque 3 — Smoke Test de integración dual (US-BE-002, T-066…T-068)

### Ejecución del script (T-066 + T-067)
- [ ] `scripts/bt2_smoke_test.py` existe y es ejecutable: `python scripts/bt2_smoke_test.py` termina con exit code 0.
- [ ] El script imprime prefijos `[SMOKE][SM]` y `[SMOKE][ODDS]` correctamente.
- [ ] El script maneja error HTTP (403/404) sin lanzar excepción fatal — registra `❌` y continúa.
- [ ] No hardcodea ninguna API key — lee exclusivamente desde `.env` o `bt2_settings`.

### Cobertura de Sportmonks (T-066)
- [ ] Request 1 (leagues): `GET /football/leagues` retorna respuesta 200 con al menos 1 liga.
- [ ] Premier League (ID 8) identificada en la respuesta: `✅` o `❌` documentado.
- [ ] Request 2 (fixtures): `GET /football/fixtures/date/{HOY o ayer}` retorna respuesta 200.
- [ ] Estructura del campo `odds` documentada (presente o ausente con el plan actual).
- [ ] Créditos restantes de Sportmonks reportados en consola.

### Cobertura de The-Odds-API (T-067)
- [ ] Request 1 (sports): `GET /v4/sports` retorna 200 y `soccer_epl` está en la lista: `✅` o `❌`.
- [ ] Request 2 (odds): `GET /v4/odds?sport=soccer_epl&regions=eu&markets=h2h` retorna 200.
- [ ] Estructura de `bookmakers[].markets[].outcomes` documentada.
- [ ] `x-requests-remaining` reportado en consola.
- [ ] Total de requests combinadas ≤ 10.

### Reporte generado (T-068)
- [ ] Directorio `docs/bettracker2/recon_results/` existe.
- [ ] Archivo `smoke_test_{FECHA}.md` generado con la fecha de ejecución.
- [ ] El reporte contiene `✅`/`❌` para cada campo de ambos proveedores.
- [ ] El reporte incluye la línea de decisión: `✅ Proceder con Atraco` o `❌ Revisar antes de continuar`.
- [ ] El arquitecto principal ha leído y aprobado el reporte **antes** de lanzar US-BE-004.

---

## Bloque 4 — Atraco Masivo (US-BE-004, T-072…T-074)

### Estructura de scripts (T-072 + T-073 + T-074)
- [ ] Directorio `scripts/bt2_atraco/` existe con `__init__.py`.
- [ ] `sportmonks_worker.py` existe con función `run_sportmonks(start_date, end_date, league_ids)`.
- [ ] `theoddsapi_worker.py` existe con función `run_theoddsapi(start_date, end_date, sport_keys)`.
- [ ] `run_atraco.py` existe con parser de argumentos `--start`, `--end` y `--dry-run`.
- [ ] `python scripts/bt2_atraco/run_atraco.py --help` imprime el uso sin error.

### Prueba corta (smoke de 1 día)
- [ ] `python scripts/bt2_atraco/run_atraco.py --start {ayer} --end {ayer}` completa sin excepción.
- [ ] `SELECT COUNT(*) FROM raw_sportmonks_fixtures` retorna al menos 1 después de la prueba.
- [ ] `SELECT COUNT(*) FROM raw_theoddsapi_snapshots` retorna al menos 1 después de la prueba.
- [ ] Relanzar el script con los mismos parámetros **no duplica filas** (`ON CONFLICT DO NOTHING` funciona).

### Resiliencia y rate limiting (T-072 + T-073)
- [ ] El worker de Sportmonks loguea `[SM-WORKER] Rate limit hit — pausing 60 min` ante un 429 real o simulado.
- [ ] El worker de The-Odds-API consulta el cache `.cache_theoddsapi.json` y omite fechas ya procesadas.
- [ ] El cache persiste entre ejecuciones del script (no se borra al terminar).
- [ ] Ante un error 5xx, el worker reintenta hasta 3 veces antes de registrar el error y continuar.

### Reporte de cierre del Atraco
- [ ] `run_atraco.py` genera `docs/bettracker2/recon_results/atraco_{FECHA_INICIO}_{FECHA_FIN}.md` al finalizar.
- [ ] El reporte incluye: filas insertadas por tabla, créditos/requests consumidos por proveedor, duración total.
- [ ] Ninguna API key aparece en el reporte ni en los logs.
- [ ] `SELECT MIN(fixture_date), MAX(fixture_date), COUNT(*) FROM raw_sportmonks_fixtures` coincide con el reporte.

---

## Checks transversales de seguridad y arquitectura

- [ ] Ningún archivo commiteado contiene una API key real.
- [ ] `docker-compose.yml` no contiene contraseñas de producción — solo valores de desarrollo.
- [ ] Las tablas `raw_*` no tienen rutas `/bt2/*` expuestas — son internas del backend.
- [ ] Ningún nombre de proveedor (`sportmonks`, `theoddsapi`, `the-odds-api`) aparece en contratos de salida del CDM (los campos técnicos en `bt2_models.py` son internos — permitidos).
- [ ] `bt2_settings.py` es la única fuente de lectura de variables de entorno en los módulos nuevos.
