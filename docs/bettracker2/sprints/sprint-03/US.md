# Sprint 03 — US (Fuente de verdad)

> Este archivo define qué se implementa en Sprint 03.
> Todo cambio técnico debe mapear a una US aquí.
> Prefijos obligatorios por capa: `US-BE-###`, `US-OPS-###` (ver `../../01_CONTRATO_US.md`).
> Sprint 03 es exclusivamente Backend. El Frontend se conecta en Sprint 04.

## Estado del sprint

- Fecha inicio: **2026-04-07** (tras cierre de Pass 5 del Atraco)
- Fecha fin estimada: **2026-04-20**
- Owner: Backend Agent
- Estado: **Planificado**

## Contexto del sprint

Sprint 03 es el **sprint de conexión**: transforma los datos crudos del Atraco (JSONB en `raw_sportmonks_fixtures`) en un modelo canónico de dominio (CDM) normalizado, agrega autenticación JWT y reemplaza los stubs de `bt2_router.py` con endpoints reales que leen de PostgreSQL. Al cerrar Sprint 03, el backend entrega datos reales por API. El frontend se conecta en Sprint 04.

> **Nota de numeración para Sprint 04 FE:**
> Sprint 01 usó US-FE-001 a US-FE-024. Sprint 04 FE debe continuar desde **US-FE-025**.
> No usar US-FE-015 a 018 — ya están asignados en Sprint 01 a tours, diagnóstico y contrato de auth ficticio.

**Estado de entrada:**
- `raw_sportmonks_fixtures`: ~19,000+ fixtures de 88 ligas (2023-08 → 2025-05)
- `raw_theoddsapi_snapshots`: vacía (plan free, sin activar)
- `bt2_router.py`: 4 endpoints con datos hardcodeados (stubs)
- V1 (scraper + SQLite + DSR): corriendo en paralelo, **no tocar**

**Decisiones de diseño fijas:**
- CDM normaliza todas las ligas excepto amistosos e IDs sin valor predictivo
- El normalizador corre como job Python standalone (no como endpoint)
- Los stubs de `bt2_router.py` se reemplazan en orden: meta → session → vault → metrics
- V1 sigue usando su propio pipeline de scrapers para tenis y fútbol scrapeado
- El job de candidatos BT2 (US-BE-008) alimenta el pipeline DSR existente sin modificarlo

---

## US-BE-005 — CDM: normalizador y tablas canónicas

### 1) Objetivo de negocio

Convertir los JSONB crudos de Sportmonks en tablas tipadas y consultables del dominio BT2. Sin este paso, no hay datos reales que servir por API. Es el **bloqueante** de US-BE-007 y US-BE-008.

### 2) Alcance

- Incluye:
  - Tablas nuevas en PostgreSQL (migración Alembic):
    - `bt2_leagues`: `id (PK int)`, `name`, `country`, `tier (S/A/B/unknown)`, `is_active bool`, `sportmonks_id int`.
    - `bt2_teams`: `id (PK)`, `name`, `short_name`, `sportmonks_id int`, `league_id (FK)`.
    - `bt2_events`: `id (PK)`, `sportmonks_fixture_id int (unique)`, `league_id (FK)`, `home_team_id (FK)`, `away_team_id (FK)`, `kickoff_utc (timestamptz)`, `status (scheduled/finished/cancelled)`, `result_home int`, `result_away int`, `season varchar`, `created_at`, `updated_at`.
    - `bt2_odds_snapshot`: `id (PK)`, `event_id (FK)`, `bookmaker`, `market`, `selection`, `odds decimal`, `fetched_at timestamptz`.
  - Job `scripts/bt2_cdm/normalize_fixtures.py`:
    - Lee `raw_sportmonks_fixtures` paginado (1,000 rows a la vez).
    - Filtra ligas excluidas (ver §5 Reglas).
    - Upsert en `bt2_leagues`, `bt2_teams`, `bt2_events`, `bt2_odds_snapshot`.
    - Log de progreso cada 500 fixtures. Reporte final en `recon_results/cdm_normalize_{fecha}.md`.
  - `scripts/bt2_cdm/__init__.py`.
- Excluye:
  - Identity map con The-Odds-API (Sprint 04).
  - Estadísticas de equipo, xG, Pressure Index — columnas reservadas en `bt2_events` para Sprint 04.
  - Picks del usuario, bankroll, sesiones.

### 3) Lista de exclusión de ligas (IDs a filtrar del CDM)

```python
EXCLUDED_LEAGUE_IDS = {
    # Amistosos y friendlies
    1082, 1101, 2450, 2451, 2452, 2453,
    # Club Friendlies por tier (todos los IDs de friendly detectados en el Atraco)
    # Completar con: SELECT DISTINCT league_id, COUNT(*) FROM raw_sportmonks_fixtures
    #                WHERE payload->>'league_id' IN (SELECT id FROM ligas con 'friendly' en nombre)
    # Copa del Mundo Qualifiers (contexto diferente al modelo de liga)
    723, 729,
    # Ligas femeninas
    45, 1419, 1583,
    # Youth leagues
    1329,
}
# El normalizador consulta el nombre de la liga en el JSONB.
# Si contiene 'friendly', 'amistoso', 'youth', 'u18', 'u21', 'women', 'femenin'
# (case-insensitive), también se excluye independientemente del ID.
```

### 4) Contexto técnico

- Depende de: `apps/api/bt2_models.py` (Sprint 02), `apps/api/bt2_settings.py`.
- Nuevas dependencias: ninguna — ya instaladas.
- Ejecución: `python scripts/bt2_cdm/normalize_fixtures.py` desde raíz del repo.
- Migraciones: `alembic upgrade head` en `apps/api/`.

### 5) Reglas de dominio

- Regla 1: Upsert idempotente — si `sportmonks_fixture_id` ya existe en `bt2_events`, actualiza `status`, `result_home`, `result_away`, `updated_at`. No duplica.
- Regla 2: Liga desconocida (no en BD ni en exclusión) → se crea en `bt2_leagues` con `tier='unknown'` y `is_active=false`. No se descarta.
- Regla 3: Fixture sin ambos participantes → se descarta con log `[CDM] Skipped fixture {id}: missing participants`.
- Regla 4: Odds: se normalizan solo las entradas con `bookmaker` reconocible y `odds > 1.0`. Resto se descarta silenciosamente.
- Regla 5: El job es reanudable — si se interrumpe, relanzar procesa solo los fixtures no normalizados aún (via `WHERE sportmonks_fixture_id NOT IN (SELECT sportmonks_fixture_id FROM bt2_events)`).

### 6) Criterios de aceptación

1. Given el job ejecutado sobre los ~19,000 fixtures del Atraco, When se consulta `SELECT COUNT(*) FROM bt2_events`, Then el conteo es > 5,000 (fixtures de ligas válidas, excluyendo amistosos y copas de relleno).
2. Given un fixture de la Premier League en `raw_sportmonks_fixtures`, When el normalizador lo procesa, Then existe una fila en `bt2_events` con `league_id` correcto, `kickoff_utc` en UTC, y al menos 1 fila en `bt2_odds_snapshot`.
3. Given que Club Friendlies 3 (ID 2451) tiene 1,902 fixtures en raw, When el normalizador corre, Then ningún fixture de liga 2451 aparece en `bt2_events`.
4. Given el job relanzado sobre una BD ya normalizada, When termina, Then `SELECT COUNT(*) FROM bt2_events` no cambia (idempotencia).

### 7) Definition of Done

- [ ] T-079: Migración Alembic con 4 tablas CDM creadas.
- [ ] T-080: `normalize_fixtures.py` con filtro de exclusión, upsert idempotente y log.
- [ ] `SELECT COUNT(*) FROM bt2_events` > 5,000 tras normalización completa.
- [ ] Reporte de normalización archivado en `recon_results/`.

---

## US-BE-006 — Auth JWT

### 1) Objetivo de negocio

Permitir que usuarios se registren e inicien sesión. Sin auth, los endpoints de dominio conductual (US-BE-007) no pueden ser personalizados por usuario. Es el **requisito previo** para persistir bankroll, sesión activa y picks del usuario.

### 2) Alcance

- Incluye:
  - Tabla `bt2_users`: `id (UUID PK)`, `email (unique)`, `password_hash`, `display_name`, `created_at`, `is_active bool`.
  - Tabla `bt2_sessions`: `id (UUID PK)`, `user_id (FK)`, `token_hash`, `created_at`, `expires_at`, `revoked bool`.
  - `apps/api/bt2_auth.py`: funciones `hash_password`, `verify_password`, `create_jwt`, `decode_jwt`.
  - Dependency `get_current_user` en `apps/api/deps.py` — inyectable en endpoints protegidos.
  - Endpoints en `bt2_router.py`:
    - `POST /bt2/auth/register` — crea usuario, retorna JWT.
    - `POST /bt2/auth/login` — verifica credenciales, retorna JWT.
    - `GET /bt2/auth/me` — retorna perfil del usuario autenticado (requiere token).
  - Migración Alembic para las 2 tablas.
- Excluye:
  - OAuth / social login.
  - Roles y permisos (todos los usuarios tienen el mismo nivel en MVP).
  - Reset de contraseña por email.
  - Refresh tokens (el JWT dura 7 días; suficiente para MVP).

### 3) Contexto técnico

- Dependencias nuevas: `passlib[bcrypt]`, `python-jose[cryptography]`.
- `BT2_SECRET_KEY` ya está en `.env` (configurado en Sprint 02).
- El JWT payload incluye: `sub` (user_id UUID), `exp`, `iat`.

### 4) Reglas de dominio

- Regla 1: La contraseña nunca se almacena en texto plano. Solo `bcrypt` hash.
- Regla 2: Email en minúsculas al registrar y al buscar (case-insensitive).
- Regla 3: JWT expira en 7 días. No hay refresh automático — el frontend maneja el re-login.
- Regla 4: El endpoint `/bt2/auth/me` es la única ruta de verificación de token — no exponer internals del JWT al cliente.
- Regla 5: `bt2_auth.py` nunca se importa en `apps/api/main.py` directamente — solo a través de `bt2_router.py`.

### 5) Criterios de aceptación

1. Given `POST /bt2/auth/register` con email y password válidos, When se llama, Then retorna `200` con `access_token` JWT y `user_id`.
2. Given un email ya registrado, When se llama `POST /bt2/auth/register` de nuevo, Then retorna `409 Conflict`.
3. Given `POST /bt2/auth/login` con credenciales correctas, When se llama, Then retorna `200` con JWT válido.
4. Given credenciales incorrectas, When se llama `POST /bt2/auth/login`, Then retorna `401 Unauthorized`.
5. Given un JWT válido en header `Authorization: Bearer {token}`, When se llama `GET /bt2/auth/me`, Then retorna el perfil del usuario sin exponer `password_hash`.
6. Given un JWT expirado o malformado, When se usa en cualquier endpoint protegido, Then retorna `401`.

### 6) Definition of Done

- [ ] T-081: Migración Alembic: `bt2_users` + `bt2_sessions`.
- [ ] T-082: `bt2_auth.py` con hash, verify, create_jwt, decode_jwt.
- [ ] T-083: Endpoints register, login, me en `bt2_router.py` + dependency `get_current_user`.
- [ ] Tests manuales: registro → login → me → token inválido — todos responden correctamente.
- [ ] V1 `/health` sigue respondiendo `{"ok": true}`.

---

## US-BE-007 — Endpoints reales (reemplazar stubs de bt2_router)

### 1) Objetivo de negocio

Los 4 endpoints actuales de `bt2_router.py` devuelven datos hardcodeados. Esta US los reemplaza con datos reales de PostgreSQL, preservando exactamente el mismo contrato de respuesta que el frontend V2 ya consume — sin romper nada en el frontend.

### 2) Alcance

Reemplazar en `bt2_router.py` (manteniendo los mismos paths y schemas de respuesta):

- `GET /bt2/meta` → leer `settlement_verification_mode` desde configuración DB o `.env`. Sin cambios en schema.
- `GET /bt2/session/day` → calcular `operating_day_key` real basado en zona horaria del usuario autenticado. Requiere token (usar `get_current_user`).
- `GET /bt2/vault/picks` → retornar picks reales del día desde `bt2_events` del CDM — eventos de hoy o próximos 24h con odds disponibles. Formato idéntico al stub actual (`Bt2VaultPickOut`). Requiere token.
- `GET /bt2/metrics/behavioral` → leer métricas reales del usuario desde tablas de picks (Sprint 04 completa esto — en Sprint 03 retorna valores calculados si hay datos, o los defaults del stub si no hay historial aún).

- Incluye también:
  - `GET /bt2/events/upcoming` (nuevo) — lista de eventos próximos 48h desde `bt2_events`, con liga, equipos y odds. Para que el frontend pueda mostrar el calendario real.
  - `POST /bt2/user/bankroll` (nuevo) — guarda bankroll inicial del usuario autenticado.
  - `GET /bt2/user/profile` (nuevo) — retorna perfil + bankroll + estadísticas básicas.

- Excluye:
  - Persistencia de picks del usuario (Sprint 04).
  - Settlement real con resultados (Sprint 04).
  - Push notifications / Telegram desde el backend BT2.

### 3) Reglas de dominio

- Regla 1: Los schemas de respuesta existentes (`Bt2VaultPickOut`, `Bt2SessionDayOut`, etc.) son inmutables en Sprint 03 — el frontend ya los consume. Solo se cambia la fuente del dato.
- Regla 2: Si `bt2_events` no tiene picks para el día actual (p.ej. domingo sin partidos), `GET /bt2/vault/picks` retorna lista vacía — no retorna el mock hardcodeado.
- Regla 3: Todos los endpoints que requieren identidad de usuario usan `Depends(get_current_user)` — no se aceptan requests sin token válido.
- Regla 4: El endpoint de vault picks prioriza eventos con `odds > 1.30` y `status = 'scheduled'` con `kickoff_utc` en las próximas 24h.

### 4) Criterios de aceptación

1. Given un token JWT válido, When `GET /bt2/vault/picks` en un día con partidos en `bt2_events`, Then retorna picks con datos reales (nombres de equipos reales, odds reales).
2. Given `GET /bt2/vault/picks` sin token, Then retorna `401`.
3. Given `GET /bt2/events/upcoming` con token, Then retorna lista de eventos de las próximas 48h con `league`, `home_team`, `away_team`, `kickoff_utc`, `odds`.
4. Given `POST /bt2/user/bankroll` con `{ "amount": 500000, "currency": "COP" }`, Then guarda en BD y retorna el bankroll actualizado.
5. Given V1 `/health` después de cualquier cambio en `bt2_router.py`, Then sigue respondiendo `{"ok": true}`.

### 5) Definition of Done

- [ ] T-084: Reemplazar `GET /bt2/meta` y `GET /bt2/session/day` con datos reales.
- [ ] T-085: Reemplazar `GET /bt2/vault/picks` con eventos reales de `bt2_events`.
- [ ] T-086: Reemplazar `GET /bt2/metrics/behavioral` + añadir `/events/upcoming`, `/user/bankroll`, `/user/profile`.
- [ ] Ningún endpoint retorna datos hardcodeados en producción.
- [ ] V1 intacta.

---

## US-BE-008 — Job de candidatos BT2 desde CDM

### 1) Objetivo de negocio

Reemplazar el canal de fútbol scrapeado en el pipeline DSR por datos limpios del CDM de Sportmonks. El pipeline DSR existente (`split_ds_batches.py` → `deepseek_batches_to_telegram_payload_parts.py`) no se modifica — solo se reemplaza la fuente de `ds_input`.

### 2) Alcance

- Incluye:
  - `scripts/bt2_cdm/build_candidates.py`: lee `bt2_events` del día con odds desde `bt2_odds_snapshot`, construye el JSON en formato `ds_input` compatible con el pipeline DSR existente.
  - Parámetros: `--date YYYY-MM-DD`, `--output-dir out/batches/`, `--max-events N` (default 50).
  - Filtros de candidato: `kickoff_utc` entre `date 00:00` y `date+1 06:00 UTC`, `status = 'scheduled'`, al menos 1 odd disponible en `bt2_odds_snapshot`.
  - Formato de salida: idéntico al `ds_input` que ya consume `deepseek_batches_to_telegram_payload_parts.py` (campos `event_id`, `event_context`, `processed.odds_all`, `sport`).
  - Documentar el comando de integración en el docstring.

- Excluye:
  - Modificar `split_ds_batches.py` ni ningún job existente de V1.
  - Canal de tenis — sigue usando el scraper de SofaScore.
  - Envío a Telegram — lo hace el pipeline existente.

### 3) Contexto técnico

El formato de `ds_input` que DSR espera (del pipeline V1):
```json
{
  "event_id": 123,
  "sport": "football",
  "event_context": {
    "home_team": "Arsenal",
    "away_team": "Chelsea",
    "tournament": "Premier League",
    "date": "2024-03-15"
  },
  "processed": {
    "odds_all": {
      "1X2": { "1": 2.10, "X": 3.40, "2": 3.20 },
      "Over/Under 2.5": { "Over 2.5": 1.85, "Under 2.5": 1.95 }
    }
  }
}
```

### 4) Criterios de aceptación

1. Given `python scripts/bt2_cdm/build_candidates.py --date 2024-08-17 --output-dir out/batches/`, When se ejecuta, Then genera archivos `candidates_{date}_batch*.json` con al menos 1 evento con odds reales de la EPL.
2. Given el output de `build_candidates.py`, When se pasa a `deepseek_batches_to_telegram_payload_parts.py` (sin modificaciones), Then procesa sin error y genera picks válidos.
3. Given un día sin eventos en `bt2_events` para la fecha, When se ejecuta, Then retorna 0 candidatos con log informativo — no falla.

### 5) Definition of Done

- [ ] T-087: `build_candidates.py` con filtros, formato `ds_input` compatible y parámetros CLI.
- [ ] Test de integración end-to-end: `build_candidates.py` → `deepseek_batches_to_telegram_payload_parts.py` con datos reales del CDM.
- [ ] Docstring con instrucción de uso documentada.

---

## Nota de coordinación — numeración Sprint 04 (Frontend)

**Namespace global:** las US de frontend siguen una secuencia continua en todo el proyecto (como en Sprint 01: US-FE-001 … US-FE-024). No se usan prefijos por sprint ni rangos alternativos (p. ej. 201+).

**Nota de numeración para Sprint 04 FE:** Sprint 01 cerró en **US-FE-024**. Sprint 04 FE debe continuar desde **US-FE-025**. No reutilizar **US-FE-015 … US-FE-018**: ya están asignadas en Sprint 01 (tours, diagnóstico, contrato de auth sin token ficticio, etc.).

**Estado de entrada para quien redacte `sprints/sprint-04/US.md`:** arrancar en **US-FE-025** y seguir en orden **026, 027, 028** para las cuatro historias de integración FE acordadas:

| ID | Nombre |
|----|--------|
| **US-FE-025** | Desacoplar stores de mocks: vault y picks (`useVaultStore`, `useTradeStore`) → endpoints reales (`/bt2/events`, `/bt2/picks` u rutas finales acordadas con API). |
| **US-FE-026** | Auth flow real: login/registro con JWT del backend; `useUserStore` con token y perfil persistidos. |
| **US-FE-027** | Bankroll y sesión desde BD: `useSessionStore` y `useBankrollStore` leen/escriben vía API (PostgreSQL); estado conductual persistente entre sesiones. |
| **US-FE-028** | Settlement con resultados reales: pantalla lee `result` (u equivalente) desde `bt2_events`; liquidación actualiza bankroll real en BD. |
