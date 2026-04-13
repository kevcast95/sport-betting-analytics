# API local — V1 (SQLite) + BetTracker 2 (`/bt2`)

El servidor **es uno solo**: `apps.api.main:app` sirve las rutas **Copa / scrapper** sobre **SQLite** y las rutas **`/bt2/*`** sobre **PostgreSQL**. Si falta configuración BT2, el proceso **no arranca** (el import de `bt2_router` carga `bt2_settings`).

## Requisitos

- **Python 3.9+**
- **Dependencias pip** (desde la **raíz del repo**):

  ```bash
  pip install -r requirements.txt -r apps/api/requirements.txt
  ```

- **SQLite** (V1): por defecto `db/sport-tracker.sqlite3`. Se crea/actualiza el esquema al arrancar (`lifespan` en `main.py`). Opcional: `DB_PATH=/ruta/al.sqlite3`.
- **PostgreSQL** (BT2): instancia accesible y **migraciones Alembic aplicadas** (tablas `bt2_*`). Sin esto, el servidor puede arrancar pero los endpoints `/bt2/*` fallarán al tocar la BD.

## Variables de entorno (archivo `.env` en la raíz del repo)

`bt2_settings` lee **`.env` en la raíz** (mismo directorio desde el que sueles lanzar `uvicorn`). Plantilla: **`.env.example`** en la raíz del monorepo.

| Variable | Obligatoria | Uso |
|----------|-------------|-----|
| `SPORTMONKS_API_KEY` | Sí (valor no vacío) | Requerida por `Bt2Settings`; para solo BT2 local puede ser un placeholder si no llamas jobs SportMonks. |
| `BT2_DATABASE_URL` | Sí | URL **sync** PostgreSQL, p. ej. `postgresql://usuario:clave@127.0.0.1:5432/nombre_db` (también acepta `postgresql+asyncpg://`; el router la normaliza). |
| `BT2_SECRET_KEY` | No | JWT BT2; default de desarrollo en código si no la defines. |
| `THEODDSAPI_KEY` | No | Integraciones odds. |
| `WEB_API_KEY` | No | Si está definida, muchas rutas V1 exigen header `X-Local-Api-Key` con el mismo valor. |
| `DB_PATH` | No | Ruta al SQLite del scrapper (V1). |

## Migraciones BT2 (una vez por base nueva)

Desde la **raíz del repo**:

```bash
export BT2_DATABASE_URL="postgresql://usuario:clave@127.0.0.1:5432/tu_db"
PYTHONPATH=apps/api python3 -m alembic -c apps/api/alembic.ini upgrade head
```

(`BT2_DATABASE_URL` debe coincidir con la de tu `.env`.)

## Refrescar snapshot de bóveda (mismo día operativo)

El pipeline en `POST /bt2/session/open` **no vuelve a generar** picks si ya existen filas en `bt2_daily_picks` para `(user_id, operating_day_key)`.

**Opción A — endpoint admin** (requiere `BT2_ADMIN_API_KEY` en el API y header `X-BT2-Admin-Key`):

```bash
# Sustituir USER_UUID (`bt2_users.id`, formato UUID con guiones). El API también acepta y corrige un sufijo `_BT2` copiado por error.
curl -sS -X POST "http://127.0.0.1:8000/bt2/admin/vault/regenerate-daily-snapshot?userId=USER_UUID&operatingDayKey=2026-04-09" \
  -H "X-BT2-Admin-Key: TU_CLAVE_ADMIN"
```

**Opción B — SQL + reabrir sesión** (si no usas admin): en `psql`, con tu `user_id` y `operating_day_key`:

```sql
DELETE FROM bt2_daily_picks WHERE user_id = '...uuid...' AND operating_day_key = 'YYYY-MM-DD';
DELETE FROM bt2_vault_day_metadata WHERE user_id = '...uuid...' AND operating_day_key = 'YYYY-MM-DD';
```

Luego en la app: **cierra** la sesión del día si está abierta (`POST /bt2/session/close`) y vuelve a **abrir** (`POST /bt2/session/open`) para disparar el snapshot otra vez.

**Importante (web):** la bóveda guarda los picks en el store persistido (`bt2_v2_vault`). Tras `regenerate-daily-snapshot`, el **mismo** `operating_day_key` no invalida esa caché sola: hay que **Sincronizar** en la cabecera de **La Bóveda** (vuelve a llamar `GET /bt2/vault/picks`) o borrar storage de la app. Los `id` tipo `dp-*` pueden **cambiar** al regenerar (nuevas filas en `bt2_daily_picks`); si un bookmark apunta a `dp-38` viejo, abre la bóveda y entra al pick desde la tarjeta actual.

## Levantar el servidor Python

**Siempre desde la raíz del repositorio**, con `PYTHONPATH` apuntando al repo (el paquete es `apps.api`):

```bash
cd /ruta/al/scrapper
export PYTHONPATH="${PWD}"
python3 -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 --reload
```

Atajo npm (equivalente, también fija `PYTHONPATH` al cwd):

```bash
cd /ruta/al/scrapper
npm run dev:api
```

**API + front juntos** (otra terminal o un solo comando):

```bash
npm run dev
```

Eso levanta el API en **127.0.0.1:8000** y el front en el puerto de Vite (proxy hacia el API según `apps/web`).

## Comprobar que V1 responde

```bash
curl -s http://127.0.0.1:8000/health
```

Respuesta esperada: `{"ok":true,"db_path":"…sport-tracker.sqlite3"}` (la ruta depende de `DB_PATH` / default).

Esto **no** comprueba PostgreSQL; solo confirma que el proceso arrancó y el SQLite de configuración es coherente.

## Comprobar BT2 (opcional)

Con usuario/token (registro/login según tu entorno):

```bash
curl -s http://127.0.0.1:8000/bt2/meta
```

Documentación interactiva: `http://127.0.0.1:8000/docs`.

## Fallos típicos tras un corte de luz / reinicio

1. **PostgreSQL no está levantado** → errores al llamar `/bt2/*`; arranca el servicio local o Docker.
2. **Falta `.env` o variables** → `ValidationError` al importar `bt2_settings`; revisa `.env.example`.
3. **`PYTHONPATH` incorrecto** → `ModuleNotFoundError: apps.api`; ejecuta siempre desde la raíz con `PYTHONPATH="${PWD}"`.
4. **Puerto 8000 ocupado** → cambia `--port 8001` y alinea el proxy del front (`apps/web`) si lo usas.

## Referencias

- Comando en docstring: `apps/api/main.py` (líneas iniciales).
- Script monorepo: `package.json` → `dev:api`, `dev`.
- Claves BT2: `apps/api/bt2_settings.py`.
