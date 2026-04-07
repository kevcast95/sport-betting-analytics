# Sprint 04 — QA Checklist

> Para validación cruzada tras implementación backend.
> Marcar `[x]` al verificar manualmente con curl o psql.

---

## US-BE-009 — Schema conductual

- [x] `alembic upgrade head` aplicado sin error.
- [x] `alembic downgrade -1 && alembic upgrade head` sin error.
- [x] `alembic current` muestra `7a609e85688b (head)`.
- [x] 6 tablas existen: `bt2_picks`, `bt2_operating_sessions`, `bt2_bankroll_snapshots`, `bt2_dp_ledger`, `bt2_behavioral_blocks`, `bt2_user_settings`.
- [x] `POST /bt2/auth/register` crea fila en `bt2_user_settings` con `risk_per_pick_pct=2.0`, `timezone='America/Bogota'`, `display_currency='COP'`.
- [x] Verificar: `SELECT * FROM bt2_user_settings WHERE user_id = '<nuevo_user_id>'`.

---

## US-BE-010 — API de picks

### POST /bt2/picks
- [x] Token válido + event scheduled → `201` con `status='open'`.
- [x] Pick duplicado (mismo user+event+market+selection) → `409`.
- [x] `odds_accepted <= 1.0` → `422`.
- [x] `stake_units <= 0` → `422`.
- [ ] `event_id` no existe → `404`.
- [ ] Evento con `status='finished'` → `422`.

### GET /bt2/picks
- [x] `?status=open` retorna picks abiertos del usuario.
- [x] `?status=all` retorna todos.
- [ ] `?date=YYYY-MM-DD` filtra por fecha de apertura.

### GET /bt2/picks/{id}
- [x] Pick existente del usuario → `200` con todos los campos.
- [ ] Pick de otro usuario → `404`.
- [ ] Pick inexistente → `404`.

### POST /bt2/picks/{id}/settle
- [x] Pick open + resultado → `200` con `status='won'`, `pnl_units=stake*(odds-1)`, `earned_dp=10` (D-04-011).
- [x] Pick ya liquidado → `409`.
- [x] `bankroll_amount` del usuario actualizado en BD.
- [x] Entrada en `bt2_bankroll_snapshots` con `event_type='pick_win'`.
- [x] Entrada en `bt2_dp_ledger` con `delta_dp=10`, `reason='pick_settle'` (won).
- [ ] Pick lost: `pnl_units=-stake`, `earned_dp=5`, `event_type='pick_loss'`.
- [ ] Pick void: `pnl_units=0`, `earned_dp=0`, `event_type='pick_void'`.

```sql
-- Verificar settle en BD
SELECT p.status, p.pnl_units, b.balance_units, b.event_type, d.delta_dp, d.balance_after_dp
FROM bt2_picks p
JOIN bt2_bankroll_snapshots b ON b.reference_id = p.id
JOIN bt2_dp_ledger d ON d.reference_id = p.id
WHERE p.id = <pick_id>;
```

---

## US-BE-011 — Sesión operativa

### POST /bt2/session/open
- [x] Sin sesión previa hoy → `201` con `session_id`, `operating_day_key`, `station_opened_at`.
- [x] Sesión ya abierta hoy → `409`.

### POST /bt2/session/close
- [x] Sesión abierta → `200` con `status='closed'`, `grace_until_iso = closed_at + 24h`.
- [ ] Sin sesión abierta → `404`.
- [x] `pending_settlements` = picks open del día.

### GET /bt2/session/day
- [x] Sin sesión: `stationClosedForOperatingDay=false`, `graceUntilIso=null`.
- [x] Sesión abierta: `stationClosedForOperatingDay=false`.
- [x] Sesión cerrada: `stationClosedForOperatingDay=true`, `graceUntilIso` real.
- [x] `pendingSettlementsPreviousDay` = picks open del día anterior.
- [x] `userTimeZone` viene de `bt2_user_settings.timezone`.

---

## US-BE-012 — Settings y DP

### GET /bt2/user/settings
- [x] Usuario con settings → retorna valores reales.
- [x] `riskPerPickPct=2.0`, `timezone='America/Bogota'` por default.

### PUT /bt2/user/settings
- [x] `riskPerPickPct=3.5` → actualiza y retorna nuevo valor.
- [x] `riskPerPickPct=15` → `422`.
- [ ] `riskPerPickPct=0.1` → `422`.
- [ ] `dpUnlockPremiumThreshold=5` → `422`.
- [ ] `dpUnlockPremiumThreshold=600` → `422`.
- [ ] Campos no enviados no se modifican.

### GET /bt2/user/dp-balance
- [x] Tras 1 pick ganado → `dpBalance=2`.
- [x] `pendingSettlements` = picks open de días anteriores.
- [x] `behavioralBlockCount` = 0 (ningún bloqueo aún).
- [ ] `dpBalance` nunca negativo (mínimo 0).

### GET /bt2/user/dp-ledger
- [x] Retorna entradas ordenadas `created_at DESC`.
- [x] `limit=20` por default.
- [ ] `?limit=5` retorna máximo 5 entradas.

---

## Verificaciones finales

- [x] `curl http://127.0.0.1:8000/health` → `{"ok": true, ...}` (V1 intacta).
- [x] Todos los endpoints protegidos rechazan requests sin token → `403`.
- [ ] `curl http://127.0.0.1:8000/docs` → OpenAPI muestra todos los endpoints Sprint 04.

---

## Notas para QA

### Eventos scheduled para testing
El CDM tiene 79 eventos con `status='scheduled'`. Obtener uno para testing:
```sql
SELECT e.id, th.name || ' vs ' || ta.name AS partido, e.kickoff_utc
FROM bt2_events e
JOIN bt2_teams th ON e.home_team_id = th.id
JOIN bt2_teams ta ON e.away_team_id = ta.id
WHERE e.status = 'scheduled'
LIMIT 5;
```

### Flujo completo de prueba
```bash
# 1. Register (crea user + settings)
curl -X POST /bt2/auth/register -d '{"email":"qa@test.com","password":"test1234"}'

# 2. Abrir sesión del día
curl -X POST /bt2/session/open -H "Authorization: Bearer <token>"

# 3. Crear pick
curl -X POST /bt2/picks -d '{"event_id":<id>,"market":"Match Winner","selection":"1","odds_accepted":2.1,"stake_units":1.0}'

# 4. Liquidar pick
curl -X POST /bt2/picks/1/settle -d '{"result_home":2,"result_away":0}'

# 5. Verificar DP balance
curl /bt2/user/dp-balance

# 6. Cerrar sesión
curl -X POST /bt2/session/close
```

---

## US-BE-013 — Ingesta diaria de eventos futuros

- [x] `python scripts/bt2_cdm/fetch_upcoming.py` ejecuta sin error.
- [x] `SELECT COUNT(*) FROM bt2_events WHERE kickoff_utc > now()` retorna > 0 tras ejecución.
- [x] Idempotencia: segunda ejecución → conteo NO crece (82 → 82 verificado).
- [x] Reporte generado en `docs/bettracker2/recon_results/upcoming_{fecha}.md`.
- [x] Solo ligas con `is_active=true` procesadas (27 ligas).
- [x] V1 health: `{"ok": true}`.

```bash
# Verificar eventos futuros
python3 -c "
import psycopg2, os; from dotenv import load_dotenv; load_dotenv('.env')
c = psycopg2.connect(os.getenv('BT2_DATABASE_URL','').replace('postgresql+asyncpg://','postgresql://')).cursor()
c.execute(\"SELECT COUNT(*) FROM bt2_events WHERE kickoff_utc > now()\")
print('Eventos futuros:', c.fetchone()[0])
"
```

---

## US-BE-014 — Pick snapshot diario

- [x] Migración `bt2_daily_picks` aplicada (T-105).
- [x] `alembic current` muestra `33ad702e05ab (head)`.
- [x] `POST /bt2/session/open` genera snapshot en `bt2_daily_picks` si hay eventos hoy.
- [x] Snapshot tiene hasta 5 filas: 3 `access_tier='standard'`, 2 `access_tier='premium'`.
- [x] Segunda apertura de sesión el mismo día → 409 y picks NO cambian.
- [x] `GET /bt2/vault/picks` retorna picks con `isAvailable`, `accessTier`, `externalSearchUrl`.
- [x] Sin snapshot (sesión no abierta) → lista vacía + mensaje informativo, sin 5xx.
- [x] Picks `premium` aparecen siempre en la lista (backend no los oculta).
- [x] `externalSearchUrl` formato: `https://www.google.com/search?q={home}+vs+{away}+{YYYY-MM-DD}`.
- [x] V1 health final: `{"ok": true}`.

```bash
# Abrir sesión y verificar snapshot
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/bt2/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@bt2.com","password":"test1234"}' | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")

# Abrir sesión
curl -s -X POST http://127.0.0.1:8000/bt2/session/open -H "Authorization: Bearer $TOKEN"

# Ver picks del día
curl -s http://127.0.0.1:8000/bt2/vault/picks -H "Authorization: Bearer $TOKEN"

# 2do intento (debe ser 409)
curl -s -X POST http://127.0.0.1:8000/bt2/session/open -H "Authorization: Bearer $TOKEN"
```
