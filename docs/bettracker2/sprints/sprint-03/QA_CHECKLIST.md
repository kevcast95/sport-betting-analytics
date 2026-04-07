# Sprint 03 — QA Checklist

> Verificar cada punto antes de declarar el sprint completo.
> Marcar `[x]` solo con evidencia real (output de terminal, screenshot, query SQL).

---

## Ola 1 — CDM (T-079, T-080)

### Schema
- [ ] `alembic current` muestra la revisión de Sprint 03 aplicada
- [ ] `\dt` en psql muestra: `bt2_leagues`, `bt2_teams`, `bt2_events`, `bt2_odds_snapshot`
- [ ] Índices creados: verificar con `\d bt2_events` y `\d bt2_odds_snapshot`

### Normalizador
- [ ] `python scripts/bt2_cdm/normalize_fixtures.py` corre sin error
- [ ] `SELECT COUNT(*) FROM bt2_events` retorna > 5,000
- [ ] `SELECT COUNT(*) FROM bt2_leagues` retorna > 50
- [ ] `SELECT COUNT(*) FROM bt2_odds_snapshot` retorna > 10,000
- [ ] Club Friendlies 3 (league_id 2451) NO aparece en `bt2_events`:
  ```sql
  SELECT COUNT(*) FROM bt2_events e JOIN bt2_leagues l ON e.league_id = l.sportmonks_id
  WHERE l.sportmonks_id = 2451;
  -- Debe retornar 0
  ```
- [ ] Premier League (ID 8) SÍ aparece con > 300 eventos:
  ```sql
  SELECT COUNT(*) FROM bt2_events e JOIN bt2_leagues l ON e.league_id = l.id
  WHERE l.sportmonks_id = 8;
  -- Debe retornar > 300
  ```
- [ ] Normalizador es idempotente: relanzar produce el mismo COUNT(*) sin duplicados
- [ ] Reporte `cdm_normalize_{fecha}.md` generado en `recon_results/`

---

## Ola 2 — Auth JWT (T-081, T-082, T-083)

- [ ] Tablas `bt2_users` y `bt2_sessions` creadas (verificar con `\d bt2_users`)
- [ ] Register exitoso:
  ```bash
  curl -X POST http://127.0.0.1:8000/bt2/auth/register \
    -H "Content-Type: application/json" \
    -d '{"email":"qa@test.com","password":"test1234","display_name":"QA"}'
  # Debe retornar 200 con access_token
  ```
- [ ] Register duplicado retorna 409:
  ```bash
  # Mismo comando anterior — debe retornar 409 Conflict
  ```
- [ ] Login exitoso con las mismas credenciales retorna nuevo token
- [ ] Login con password incorrecta retorna 401
- [ ] `GET /bt2/auth/me` con token válido retorna perfil (sin password_hash)
- [ ] `GET /bt2/auth/me` sin token retorna 401
- [ ] `GET /bt2/auth/me` con token malformado retorna 401
- [ ] **V1 intacta:** `curl http://127.0.0.1:8000/health` → `{"ok": true}`

---

## Ola 3 — Endpoints reales (T-084, T-085, T-086)

- [ ] `GET /bt2/meta` con token retorna `settlement_verification_mode` (no hardcodeado en código)
- [ ] `GET /bt2/session/day` con token retorna `operating_day_key` = fecha de hoy en Bogotá
- [ ] `GET /bt2/vault/picks` con token retorna lista (puede ser vacía si no hay partidos hoy — no el mock)
- [ ] `GET /bt2/vault/picks` sin token retorna 401
- [ ] `GET /bt2/events/upcoming` con token retorna lista de eventos próximos 48h
- [ ] `POST /bt2/user/bankroll` guarda y retorna el bankroll correctamente
- [ ] `GET /bt2/user/profile` retorna perfil con bankroll actualizado
- [ ] `GET /bt2/metrics/behavioral` retorna métricas (con `"is_demo": true` si no hay historial)
- [ ] `\d bt2_users` muestra columnas `bankroll_amount` y `bankroll_currency` (migración Ola 3 aplicada)
- [ ] `alembic downgrade -1` sobre la migración de Ola 3 no afecta las tablas de Ola 2 (`bt2_users`, `bt2_sessions` siguen existiendo)
- [ ] Ningún endpoint retorna strings hardcodeados como "Atlético Norte vs Rápidos"
- [ ] **V1 intacta:** `curl http://127.0.0.1:8000/health` → `{"ok": true}`

---

## Ola 4 — Job candidatos (T-087)

- [ ] `python scripts/bt2_cdm/build_candidates.py --date 2024-08-17` genera archivos en `out/batches/`
- [ ] Los archivos generados tienen formato `candidates_2024-08-17_exec_BT2_batch{N}of{M}.json`
- [ ] El JSON de cada batch tiene la estructura `ds_input` compatible con el pipeline DSR
- [ ] Test de integración end-to-end: pasar el output a `deepseek_batches_to_telegram_payload_parts.py` sin modificaciones — debe procesar sin error
- [ ] Para un día sin eventos, el script retorna 0 candidatos sin lanzar excepción

---

## Verificaciones transversales

- [ ] `apps/web/` no tiene ningún archivo modificado (verificar con `git diff apps/web/`)
- [ ] `apps/api/main.py` no tiene imports de `bt2_auth` ni de las nuevas tablas CDM
- [ ] V1 `/health` responde `{"ok": true}` al inicio Y al final del sprint
- [ ] `alembic downgrade -1 && alembic upgrade head` funciona sin error (migraciones reversibles)
- [ ] `requirements.txt` actualizado con `passlib[bcrypt]` y `python-jose[cryptography]`
- [ ] No hay API keys, passwords ni secrets en ningún archivo commiteado
