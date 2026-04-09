# Sprint 05.2 — curl mínimo vault (T-189)

Reemplazar `TOKEN` y `API` (p. ej. `http://127.0.0.1:8000`).

## Meta / `contractVersion`

```bash
curl -s "$API/bt2/meta" | jq .
# Esperar contractVersion bt2-dx-001-s5.4
```

## Sesión + vault

```bash
curl -sS -X POST "$API/bt2/session/open" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

```bash
curl -sS "$API/bt2/vault/picks" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

**Comprobar:** cada elemento de `picks` incluye `timeBand` (`morning` | `afternoon` | `evening` | `overnight`); raíz incluye `poolTargetCount` (15), `poolHardCap` (20), `poolItemCount`, `poolBelowTarget`.

## POST pick tras kickoff (D-05.2-001 A)

Con un `eventId` cuyo `kickoffUtc` ya pasó (y `status` sigue `scheduled` por lag CDM), debe responder **422** con cuerpo JSON que incluya `code: "pick_event_kickoff_elapsed"` y `kickoffUtc`.

```bash
curl -sS -X POST "$API/bt2/picks" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"event_id":EVENT_ID,"market":"1X2","selection":"1","odds_accepted":2.0,"stake_units":1}' | jq .
```

## Regresión premium unlock (05.1)

```bash
curl -sS -X POST "$API/bt2/vault/premium-unlock" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"vaultPickId":"dp-1"}' | jq .
```
