# Sprint 03 — TASKS

> Fuente de verdad para el agente ejecutor Backend.
> Marcar `[x]` solo cuando la tarea esté completada y verificada.
> Sprint 03 es exclusivamente Backend — no tocar `apps/web/`.

## Numeración

Las tareas de Sprint 02 llegaron hasta T-078. Sprint 03 comienza en **T-079**.

## Orden de ejecución obligatorio

```
T-079 → T-080 → T-081 → T-082 → T-083 → T-084 → T-085 → T-086 → T-087
```

Cada tarea desbloquea la siguiente. No saltar pasos.

---

## Ola 1 — CDM: Schema y Normalizador (US-BE-005)

- [x] T-079 (US-BE-005) — Migración Alembic: crear las 4 tablas del CDM.
  - `bt2_leagues`: `id (int PK)`, `name (varchar)`, `country (varchar)`, `tier (varchar, default 'unknown')`, `is_active (bool, default false)`, `sportmonks_id (int unique)`.
  - `bt2_teams`: `id (serial PK)`, `name (varchar)`, `short_name (varchar, nullable)`, `sportmonks_id (int unique)`, `league_id (int FK → bt2_leagues.id, nullable)`.
  - `bt2_events`: `id (serial PK)`, `sportmonks_fixture_id (int unique)`, `league_id (int FK)`, `home_team_id (int FK)`, `away_team_id (int FK)`, `kickoff_utc (timestamptz)`, `status (varchar, default 'scheduled')`, `result_home (int, nullable)`, `result_away (int, nullable)`, `season (varchar)`, `created_at (timestamptz default now())`, `updated_at (timestamptz default now())`.
  - `bt2_odds_snapshot`: `id (serial PK)`, `event_id (int FK → bt2_events.id)`, `bookmaker (varchar)`, `market (varchar)`, `selection (varchar)`, `odds (decimal 6,4)`, `fetched_at (timestamptz)`.
  - Índices: `bt2_events(kickoff_utc)`, `bt2_events(status, kickoff_utc)`, `bt2_odds_snapshot(event_id, market)`.
  - Ejecutar `alembic upgrade head` y verificar con `alembic current`.

- [x] T-080 (US-BE-005) — Crear `scripts/bt2_cdm/__init__.py` (vacío) y `scripts/bt2_cdm/normalize_fixtures.py`. Implementar:
  - Constante `EXCLUDED_LEAGUE_IDS` con los IDs de amistosos, copas menores, ligas femeninas y youth (ver US-BE-005 §3).
  - Función `should_exclude_league(league_id, league_name)` — retorna True si el ID está en la lista o el nombre contiene keywords de exclusión (`'friendly'`, `'amistoso'`, `'youth'`, `'u18'`, `'u21'`, `'women'`, `'femenin'`, `'reserve'`), case-insensitive.
  - Función `upsert_league(payload, session)` — extrae datos de liga del JSONB, aplica filtro de exclusión, hace upsert en `bt2_leagues`.
  - Función `upsert_teams(payload, session)` — extrae home/away de `participants`, upsert en `bt2_teams`.
  - Función `upsert_event(payload, session)` — upsert en `bt2_events`. Si ya existe el `sportmonks_fixture_id`, actualizar `status`, `result_home`, `result_away`, `updated_at`.
  - Función `upsert_odds(payload, event_id, session)` — itera el campo `odds` del JSONB, normaliza a registros de `bt2_odds_snapshot`. Solo insertar si `bookmaker` no es vacío y `odds > 1.0`.
  - Función `run_normalization()` — lee `raw_sportmonks_fixtures` en batches de 1,000, llama a las funciones anteriores, log de progreso cada 500. Al final escribe reporte en `docs/bettracker2/recon_results/cdm_normalize_{fecha}.md`.
  - Verificación: `python scripts/bt2_cdm/normalize_fixtures.py` desde la raíz del repo.

---

## Ola 2 — Auth JWT (US-BE-006)

- [x] T-081 (US-BE-006) — Migración Alembic: crear `bt2_users` y `bt2_sessions`.
  - `bt2_users`: `id (uuid PK default gen_random_uuid())`, `email (varchar unique, not null)`, `password_hash (varchar, not null)`, `display_name (varchar, nullable)`, `created_at (timestamptz default now())`, `is_active (bool default true)`.
  - `bt2_sessions`: `id (uuid PK default gen_random_uuid())`, `user_id (uuid FK → bt2_users.id)`, `token_hash (varchar, not null)`, `created_at (timestamptz default now())`, `expires_at (timestamptz)`, `revoked (bool default false)`.
  - Índice: `bt2_users(email)`, `bt2_sessions(user_id, revoked)`.
  - Instalar dependencias: `pip install "passlib[bcrypt]" "python-jose[cryptography]"` y añadir a `requirements.txt`.

- [x] T-082 (US-BE-006) — Crear `apps/api/bt2_auth.py`. Implementar:
  - `hash_password(plain: str) -> str` — bcrypt hash.
  - `verify_password(plain: str, hashed: str) -> bool`.
  - `create_jwt(user_id: str, expires_days: int = 7) -> str` — usa `BT2_SECRET_KEY` del `.env`.
  - `decode_jwt(token: str) -> dict` — retorna payload o lanza `HTTPException 401`.
  - `NEVER import bt2_auth in apps/api/main.py` — solo desde `bt2_router.py` y `deps.py`.

- [x] T-083 (US-BE-006) — Añadir a `apps/api/bt2_router.py`:
  - `POST /bt2/auth/register`: body `{ email, password, display_name? }`, crea usuario con email en lowercase, retorna `{ access_token, user_id, display_name }`. Retorna `409` si email ya existe.
  - `POST /bt2/auth/login`: body `{ email, password }`, verifica credenciales, retorna `{ access_token, user_id }`. Retorna `401` si inválido.
  - `GET /bt2/auth/me`: header `Authorization: Bearer {token}`, retorna `{ user_id, email, display_name, created_at }`. Retorna `401` si token inválido.
  - Añadir dependency `get_current_bt2_user` en `apps/api/deps.py` — decodifica el JWT del header y retorna el user_id. Usar `Depends(get_current_bt2_user)` en endpoints protegidos.
  - Verificación: `curl -X POST http://127.0.0.1:8000/bt2/auth/register -d '{"email":"test@test.com","password":"test1234"}' -H "Content-Type: application/json"` — debe retornar token.
  - Verificación V1: `curl http://127.0.0.1:8000/health` — debe seguir respondiendo `{"ok": true}`.

---

## Ola 3 — Endpoints reales (US-BE-007)

- [x] T-084 (US-BE-007) — Reemplazar en `bt2_router.py`:
  - `GET /bt2/meta` → leer `settlement_verification_mode` desde variable de entorno `BT2_SETTLEMENT_MODE` (default `'trust'`). Mismo schema de respuesta.
  - `GET /bt2/session/day` → calcular `operating_day_key` = fecha en zona horaria del usuario (default `America/Bogota`). Leer `grace_until_iso` y `station_closed_for_operating_day` desde la sesión del usuario en `bt2_sessions`. Requiere `Depends(get_current_bt2_user)`.

- [x] T-085 (US-BE-007) — Reemplazar `GET /bt2/vault/picks`:
  - Query: `SELECT e.*, t_home.name, t_away.name, l.name, o.* FROM bt2_events e JOIN ... WHERE e.kickoff_utc BETWEEN now() AND now() + interval '24 hours' AND e.status = 'scheduled' ORDER BY e.kickoff_utc`.
  - Mapear cada evento a `Bt2VaultPickOut` con los campos reales: `event_label = "{home} vs {away}"`, `titulo = "{liga} · {fecha}"`, odds reales del mejor bookmaker en `bt2_odds_snapshot`.
  - Si no hay eventos en las próximas 24h, retornar lista vacía (no el mock).
  - Requiere `Depends(get_current_bt2_user)`.

- [x] T-086 (US-BE-007) — Añadir endpoints nuevos a `bt2_router.py`:
  - `GET /bt2/events/upcoming`: parámetro `hours=48` (query param). Retorna lista de eventos próximos con `{ event_id, league, home_team, away_team, kickoff_utc, odds_1x2 }`.
  - `POST /bt2/user/bankroll`: body `{ amount: float, currency: str }`. Guarda en nueva columna `bt2_users.bankroll_amount` + `bt2_users.bankroll_currency` (añadir a migración T-081 o nueva migración). Retorna bankroll actualizado.
  - `GET /bt2/user/profile`: retorna `{ user_id, email, display_name, bankroll_amount, bankroll_currency, created_at }`.
  - `GET /bt2/metrics/behavioral`: si el usuario tiene historial de picks en BD, calcula métricas reales. Si no, retorna los defaults del stub actual con flag `"is_demo": true`.
  - **Migración separada (Ola 3):** crear nueva revisión Alembic que añade columnas nullable a `bt2_users`: `bankroll_amount (decimal, nullable)` y `bankroll_currency (varchar, nullable)`. Ejecutar `alembic upgrade head` y verificar con `\d bt2_users`. No añadir a la migración de T-081 — cada Ola debe ser atómica y reversible de forma independiente.

---

## Ola 4 — Job candidatos CDM (US-BE-008)

- [x] T-087 (US-BE-008) — Crear `scripts/bt2_cdm/build_candidates.py`. Implementar:
  - CLI args: `--date YYYY-MM-DD` (required), `--output-dir out/batches/` (default), `--max-events 50` (default).
  - Query: `bt2_events` con `kickoff_utc` entre `{date} 00:00 UTC` y `{date+1} 06:00 UTC`, `status = 'scheduled'`, que tengan al menos 1 fila en `bt2_odds_snapshot`.
  - Para cada evento: construir dict `ds_input` con formato compatible con `deepseek_batches_to_telegram_payload_parts.py`:
    ```python
    {
      "event_id": event.id,
      "sport": "football",
      "event_context": {
        "home_team": home_team.name,
        "away_team": away_team.name,
        "tournament": league.name,
        "date": event.kickoff_utc.date().isoformat(),
      },
      "processed": {
        "odds_all": {
          "1X2": {"1": odds_home, "X": odds_draw, "2": odds_away},
          "Over/Under 2.5": {"Over 2.5": odds_over, "Under 2.5": odds_under},
        }
      }
    }
    ```
  - Split en batches de máx 10 eventos cada uno. Guardar como `candidates_{date}_exec_BT2_batch{N}of{M}.json`.
  - Docstring con ejemplo de integración:
    ```
    python scripts/bt2_cdm/build_candidates.py --date 2024-08-17
    python jobs/deepseek_batches_to_telegram_payload_parts.py \
      --input-glob "out/batches/candidates_2024-08-17_exec_BT2_batch*.json" \
      --date 2024-08-17 --exec-id exec_BT2
    ```

---

## Reglas

- No modificar `apps/api/main.py` directamente — solo `bt2_router.py`, `bt2_auth.py`, `deps.py`.
- No modificar ningún archivo de `apps/web/` — Sprint 03 es solo BE.
- No modificar `jobs/deepseek_batches_to_telegram_payload_parts.py` ni ningún job de V1.
- Verificar `curl http://127.0.0.1:8000/health` después de cada Ola.
- Marcar `[x]` en este archivo solo cuando la tarea esté completada Y verificada manualmente.
