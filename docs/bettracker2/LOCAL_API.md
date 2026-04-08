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
