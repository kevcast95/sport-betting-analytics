# Runbook — Medición intradía SportMonks (US-BE-061) y benchmark (US-BE-062)

**Norma congelada:** [`../sprints/sprint-06.4/DECISIONES.md`](../sprints/sprint-06.4/DECISIONES.md) **D-06-068** (§1–§6). Este documento **no** renegocia §1–§6; solo operativiza implementación y SQL.

**Handoff:** [`../sprints/sprint-06.4/HANDOFF_BE_EJECUCION_S6_4.md`](../sprints/sprint-06.4/HANDOFF_BE_EJECUCION_S6_4.md) §1b (061) y §4 (062).

**Alcance:** observabilidad / insumo a política F3 (**D-06-067**). **No** verdad productiva BT2/CDM; **no** DSR productivo en el job 061; **sin** fallback SofaScore en 061.

---

## 1. Universo (D-06-068 §1)

- **Día operativo:** conjunto de fixtures cuyo partido cae en la ventana del día según la misma TZ que `kickoff_at` (ver § TZ abajo).
- **Ligas:** exactamente las **5 ligas F2 / S6.3** documentadas en [`bt2_f2_official_leagues.md`](./bt2_f2_official_leagues.md) y en código `apps/api/bt2_f2_league_constants.py` → `F2_OFFICIAL_LEAGUE_SPORTMONKS_IDS` / `F2_OFFICIAL_LEAGUE_DISPLAY_ORDER`:

| Clave interna   | sportmonks_id (liga SM) |
|-----------------|-------------------------|
| premier_league  | 8                       |
| la_liga         | 564                     |
| serie_a         | 384                     |
| bundesliga      | 82                      |
| ligue_1         | 301                     |

Resolución a `bt2_leagues.id` CDM: `resolve_f2_official_league_bt2_ids` en el mismo módulo; override opcional `BT2_F2_OFFICIAL_LEAGUE_IDS`.

---

## 2. `kickoff_at` y zona horaria (T-280)

- **Instante de anclaje:** **`bt2_events.kickoff_utc`** (Postgres `timestamptz`, **UTC**). Es la columna CDM usada como “kickoff del fixture” para calcular ventanas **T−24h … T+15m** de **D-06-068** §2.
- **Origen datos:** el valor proviene del payload SportMonks alimentado en CDM. En `scripts/bt2_cdm/normalize_fixtures.py`, función `_parse_kickoff`:
  - Prioriza `starting_at` (string ISO o `YYYY-MM-DD HH:MM:SS` sin TZ → se **interpreta como UTC** añadiendo `+00:00` cuando no hay componente de zona).
  - Si falta, usa `starting_at_timestamp` como **epoch UTC**.
- **Regla operativa:** toda la cadencia §2 se calcula en **UTC** sobre `kickoff_utc` (mismo instante que SM normalizado a CDM). Cualquier “día operativo” para filtrar fixtures debe definirse explícitamente como **corte en UTC** (recomendado: `[day_utc 00:00, day_utc+1 00:00)` sobre `kickoff_utc`) para alinear jobs con el universo §1 sin ambigüedad local.

---

## 3. Cadencia (D-06-068 §2)

Respecto a `kickoff_utc` de cada fixture:

| Ventana              | Intervalo |
|----------------------|-----------|
| T−24h → T−6h         | 60 min    |
| T−6h → T−90m         | 15 min    |
| T−90m → kickoff      | 5 min     |
| kickoff → T+15m      | 5 min     |

---

## 4. Familias observadas (D-06-068 §3)

**Lineups** (como familia de disponibilidad), **FT_1X2**, **OU_GOALS_2_5**, **BTTS**.

---

## 5. Reglas “disponible” (D-06-068 §4–§5)

- **Lineup disponible:** `true` solo si **ambos** equipos tienen lineup **usable** en esa observación; un solo lado ⇒ `false`.
- **Mercado disponible (por familia):** `true` si en esa observación existe **cotización usable** para esa familia (criterio usable materializado en el job **T-281** / benchmark **T-284**, alineado a procesadores existentes donde aplique).

---

## 6. Matching SM ↔ SofaScore (D-06-068 §6)

Clave primaria de matching: **liga** + **kickoff** (`kickoff_utc` alineado entre fuentes en UTC) + **nombres normalizados** local y visitante.

### Normalización de nombres home/away

Implementación canónica (compartida con **T-283**): `apps/api/bt2_benchmark_team_name_normalize.py` → `normalize_benchmark_team_name`.

Reglas en texto:

1. Unicode **NFKC**; minúsculas; trim.
2. Quitar marcas diacríticas (descomposición NFD y filtrar categoría `Mn`).
3. Sustituir cualquier secuencia de caracteres que no sea `a-z` o `0-9` por un único espacio.
4. Colapsar espacios internos y volver a trim.

Si hay **ambigüedad** (más de un candidato SofaScore para la misma tripleta), la fila de mapeo en **T-283** llevará `needs_review`; el job global **no** aborta (**D-06-068** §6).

---

## 7. Persistencia SM — migración **T-287**

| Ítem        | Valor |
|------------|--------|
| **Tabla**  | `bt2_nonprod_sm_fixture_observation_s64` |
| **Modelo** | `Bt2NonprodSmFixtureObservationS64` en `apps/api/bt2_models.py` |
| **Tipo**   | Append-only de observaciones; **no** productivo; **no** referenciar desde pipelines BT2/CDM productivos (**D-06-066** para lado SofaScore / **T-286**). |

**Columnas previstas:**

| Columna | Tipo | Significado |
|---------|------|-------------|
| `id` | bigserial | PK |
| `sm_fixture_id` | int | ID fixture SportMonks (mismo sentido que `bt2_events.sportmonks_fixture_id`) |
| `observed_at` | timestamptz | Momento de la observación (server/API) |
| `lineup_home_usable` | boolean | Lado local usable |
| `lineup_away_usable` | boolean | Lado visitante usable |
| `lineup_available` | boolean | §4: ambos usables |
| `ft_1x2_available` | boolean | §5 familia FT_1X2 |
| `ou_goals_2_5_available` | boolean | §5 familia OU_GOALS_2_5 |
| `btts_available` | boolean | §5 familia BTTS |

**Índices:** `(sm_fixture_id, observed_at)`; PK en `id`.

**T-281** insertará filas en esta tabla respetando rate limits SM; **T-282** documentará queries EOD en `EJECUCION.md`.

---

## 9. Job T-281 (cron sugerido)

- **Script:** `scripts/bt2_cdm/job_sm_intraday_observation.py`
- **Cliente SM:** `fetch_sportmonks_fixture_dict` (`apps/api/bt2_dev_sm_refresh.py`) — mismos includes que CDM, backoff 429, degradación 403.
- **Env:** `BT2_DATABASE_URL`, `SPORTMONKS_API_KEY`, opcional `BT2_SM_OBS_SLEEP_S` (default `0.35` s entre fixtures).
- **Día operativo:** `--operating-day YYYY-MM-DD` en **UTC** (default: hoy UTC). Filtra `kickoff_utc ∈ [día 00:00 UTC, día+1 00:00 UTC)` y ligas F2.
- **Cadencia:** el job consulta `max(observed_at)` por `sm_fixture_id` y solo hace GET+INSERT si cumple **D-06-068** §2 (`sm_observation_should_poll`). Conviene disparar el cron **cada 5 minutos** (mínimo común de la cadencia en ventana final); en tramos de 60 min muchas corridas no insertarán filas (esperado).
- **Smoke (sin cadencia):** `--ignore-cadence` hace un GET por fixture del día que esté en ventana T−24h…T+15m (no antes ni después); solo dev — no sustituye §2 en evidencia formal.
- **Dry-run:** `--dry-run` — llama SM y loguea flags sin `INSERT`.

Ejemplo crontab (UTC en el servidor o documentar TZ del host):

```cron
*/5 * * * * cd /ruta/al/repo && /usr/bin/python3 scripts/bt2_cdm/job_sm_intraday_observation.py >>/var/log/bt2_sm_obs.log 2>&1
```

**Manual en terminal (no es daemon):** cada ejecución del script **hace una pasada** sobre los fixtures del día, inserta lo que corresponda según cadencia §2 y **sale**. No queda en bucle infinito ni consulta SM hasta que lo detengas a menos que **tú** relances el proceso. Para monitorizar fuera del IDE, podés dejar un bucle en la terminal (ejemplo: intervalo 5 min entre corridas):

```bash
while true; do date -u; python3 scripts/bt2_cdm/job_sm_intraday_observation.py || true; sleep 300; done
```

Detener con `Ctrl+C`. Ajustá `sleep` si querés otra periodicidad (debe ser coherente con la cadencia mínima de 5 min en ventana final).

---

## 8. Referencias cruzadas

- **SofaScore solo benchmark:** **D-06-066**; tabla paralela **T-288** (migración separada).
- **Cadena de revisiones Alembic:** revisar `apps/api/alembic/versions/` — revisión que crea `bt2_nonprod_sm_fixture_observation_s64`.

---

*2026-04-16 — T-280 / T-287 / T-281; congelación **D-06-068**.*
