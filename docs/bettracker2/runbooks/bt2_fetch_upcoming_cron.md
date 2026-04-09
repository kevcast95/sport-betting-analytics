# Runbook — `fetch_upcoming` (BT2 CDM)

**US-OPS-001** / **D-06-005** / **T-160** — Sprint 06.

## Qué hace

Ingiere fixtures futuros desde Sportmonks hacia `bt2_events` + `bt2_odds_snapshot` (idempotente, S4).

## Comando recomendado (cron)

Desde la raíz del repo, con `.env` cargando `BT2_DATABASE_URL` y `SPORTMONKS_API_KEY`:

```bash
cd /ruta/al/repo
python3 scripts/bt2_cdm/job_fetch_upcoming.py --hours-ahead 72
```

- **Dry-run:** `python3 scripts/bt2_cdm/job_fetch_upcoming.py --dry-run`

## Exit codes (`job_fetch_upcoming.py`)

| Código | Significado |
|--------|-------------|
| 0 | OK (descarga API exitosa) |
| 1 | Error fatal (excepción, credenciales, DB) |
| 2 | Fallo de descarga API; revisar logs / 429 |

## Horario sugerido (D-06-013)

- Ejecutar **1×/día** en ventana acordada con el equipo (UTC o TZ operativa).
- Reintentos **429:** el script base ya espera y reintenta; si persiste, revisar cuota Sportmonks.

## Variables de entorno

| Variable | Requerida |
|----------|-----------|
| `BT2_DATABASE_URL` | Sí |
| `SPORTMONKS_API_KEY` | Sí (salvo `--dry-run` con código que no llame API) |

## Si hay 0 fixtures nuevos

- Puede ser válido (sin partidos en ventana).
- Verificar ligas `is_active = true` en `bt2_leagues` y rango `--hours-ahead`.
- Ver **D-06-009** (UX vacía honesta en app).

## Reportes

Markdown bajo `docs/bettracker2/recon_results/upcoming_YYYY-MM-DD.md` (generado por el script base).

## Alertas (placeholder D-06-011)

Hasta asignar canal/on-call: monitorizar exit code ≠ 0 en el scheduler y revisar logs del host.
