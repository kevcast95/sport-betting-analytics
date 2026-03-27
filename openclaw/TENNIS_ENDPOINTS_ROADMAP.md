# Tennis Endpoints Roadmap (SofaScore)

## Tabla de contenidos

- [Objetivo](#objetivo)
- [Endpoints revisados y prioridad](#endpoints-revisados-y-prioridad)
- [MVP tenis v1 (tabla ejecutiva)](#mvp-tenis-v1-tabla-ejecutiva)
- [Plan ejecutable en el repo](#plan-ejecutable-en-el-repo)

---

## Objetivo
Definir una hoja de ruta clara para integrar tenis con el mismo enfoque operativo del brazo de futbol, priorizando endpoints por impacto real en:

1. Ingesta diaria de eventos
2. Contexto util del evento
3. Mercados/cuotas para picks
4. Capa de confianza y explicabilidad
5. Persistencia consistente e idempotente

Este documento consolida **el inventario completo de endpoints de tenis** revisados en la captura actual (fútbol-paridad + calendario + estadísticas/rankings + live/bracket). No quedan huecos pendientes de clasificación en ese lote.

---

## Endpoints revisados y prioridad

### P0 (imprescindibles en v1)

- `GET /api/v1/sport/tennis/scheduled-tournaments/{date}/page/{n}`
  - Rol: indice diario de torneos (fan-out por fecha).
  - Estado: cubierto en el mapa; al implementar, validar payload real contra fixtures y paginación.
  - Dependencias: `uniqueTournament.id`.

- `GET /api/v1/unique-tournament/{uniqueTournamentId}/scheduled-events/{date}`
  - Rol: eventos del torneo por dia.
  - Valor: trae `homeTeam/awayTeam`, `ranking`, `roundInfo`, `groundType`, `eventFilters`, estado y timestamps.
  - Nota: este endpoint parece base principal para construir la lista diaria de partidos.

- `GET /api/v1/event/{eventId}`
  - Rol: detalle de evento y metadatos finos.
  - Valor: seed, ranking, superficie, ronda, estado, winnerCode, marcador por sets.
  - Nota: clave para enriquecer contexto y resolver cierres.

- `GET /api/v1/event/{eventId}/odds/1/featured`
  - Rol: snapshot rapido del mercado principal.
  - Valor: Home/Away (sin empate en tenis), tendencia (`change`), totales destacados.
  - Riesgo: estructura distinta a futbol; no asumir `draw`.

- `GET /api/v1/event/{eventId}/odds/1/all`
  - Rol: mercados ampliados y cuotas para picks.
  - Valor: `Full time`, `First set winner`, `Total games won` (Over/Under), etc.
  - Nota: fundamental para anclar cuota real en el pipeline.

### P1 (alta utilidad, no bloquean v1)

- `GET /api/v1/event/{eventId}/h2h`
  - Rol: historial directo simple.
  - Valor: `homeWins`, `awayWins`, `draws` (en tenis suele ser 0).
  - Uso: feature de apoyo y explicabilidad.

- `GET /api/v1/sport/tennis/categories/all`
  - Rol: catalogo de categorias/circuitos.
  - Valor: permite crear whitelist operable (ATP/WTA/Challenger/ITF).
  - Riesgo: trae ruido (virtual, simulated, exhibition, etc.) si no se filtra.

- `GET /api/v1/config/default-unique-tournaments/{countryCode}/tennis`
  - Ejemplo validado: `.../CO/tennis`
  - Rol: torneos destacados/default por pais.
  - Uso: priorizacion de cobertura y capa de confianza (no sustituye ingesta diaria completa).

---

## Campos clave por capa

### Capa Ingesta diaria
- `uniqueTournament.id`
- `tournament.id`
- `season.id`
- `startTimestamp`
- `status.type`

### Capa Contexto del evento
- `homeTeam.id`, `awayTeam.id`
- `homeTeam.ranking`, `awayTeam.ranking`
- `homeTeamSeed`, `awayTeamSeed`
- `roundInfo.round`, `roundInfo.name`
- `groundType`
- `eventFilters.category`, `eventFilters.level`, `eventFilters.gender`

### Capa Mercados/cuotas
- odds featured: mercado principal home/away, `change`
- odds all: mercados de set y total de games (`choiceGroup`, `choices`)

### Capa Confianza+
- `h2h.teamDuel.homeWins/awayWins`
- circuito/categoria (ATP/WTA/Challenger/ITF)
- torneo destacado por `default-unique-tournaments`

---

## Reglas de filtrado sugeridas (v1)

Para evitar ruido inicial:

- `eventFilters.category` contiene `singles`
- `eventFilters.level` contiene `pro`
- excluir categorias no operables al inicio:
  - `virtual-*`
  - `simulated-*`
  - `exhibition` (opcional, por defecto fuera)
  - juniors/wheelchairs (por ahora fuera)
- priorizar ATP/WTA/Challenger; ITF como fase 2 controlada

---

## Matriz de cruces (anti-errores de interpretacion)

Cruzar datos entre endpoints antes de aceptar un evento/pick:

1. **Torneo**
   - `scheduled-tournaments` -> `uniqueTournament.id`
   - validar mismo `uniqueTournament.id` en `scheduled-events` y en `event/{id}`.

2. **Evento**
   - `event/{id}` vs `scheduled-events`:
     - mismo `event.id`
     - mismo `startTimestamp`
     - mismo `homeTeam.id` / `awayTeam.id`

3. **Estado**
   - usar fuente canonica: `event.status.type`
   - si hay discrepancia textual secundaria, privilegiar `status.type`.

4. **Mercados y cuota**
   - market/selection del pick debe existir en `odds/1/all` o `odds/1/featured`.
   - si ambos existen, preferir `odds_all` como referencia principal y `featured` como contraste.

5. **Consistencia deportiva**
   - validar `sport.id == 5` y `sport.slug == "tennis"` en cada payload relevante.

---

## Riesgos detectados

- Reutilizar parser de futbol en tenis puede romper por:
  - ausencia de empate (`X`) en mercado principal
  - nombres de mercado distintos (`Total games won`, `First set winner`)
  - semantica de periodos (`set`, no tiempos de juego)

- Mezclar categorias sin filtro genera ruido estadistico y picks de baja calidad.

---

## Cómo incorporar endpoints nuevos (fuera de este inventario)

Si en el futuro aparecen rutas adicionales (otro deporte, otra versión de API, o endpoints no capturados aquí), usar la misma rutina:

1. URL + params
2. Payload real (muestra)
3. Campo canónico que aporta
4. Si reemplaza algo existente o es solo Confianza+
5. Decisión: `P0`, `P1`, `Confianza+`, `No prioritario`

---

## Plantilla operativa (rellenable) para endpoints adicionales

Usar este bloque solo para **nuevos** endpoints que no estén ya listados arriba.

```md
### Endpoint adicional #[N]
- URL:
- Metodo:
- Params de ruta:
- Query params:
- Ejemplo real de request:
- Ejemplo real de response (resumen):

#### Campos utiles detectados
- Campo:
  - Tipo:
  - Capa objetivo: (Ingesta | Contexto | Cuotas | Confianza+ | Persistencia)
  - Uso propuesto:

#### Riesgos / dudas
- 

#### Cruces obligatorios
- Cruza con endpoint:
- Regla de consistencia:
- Resultado esperado:

#### Decision
- Prioridad: (P0 | P1 | Confianza+ | No prioritario)
- Entra en v1: (Si/No)
- Bloquea release: (Si/No)
- Nota final:
```

### Checklist rapido por endpoint

- [ ] Confirma `sport.id == 5` y `sport.slug == tennis` cuando aplique
- [ ] Identifica `event.id` o `uniqueTournament.id` como llave primaria de cruce
- [ ] Detecta si duplica informacion de endpoint ya aprobado
- [ ] Verifica si aporta valor real para picks o solo cosmetico
- [ ] Define si el parser debe ser especifico de tenis
- [ ] Marca prioridad y decision final

---

## Evolución sugerida (post-MVP, no es deuda del mapa)

Con el inventario ya cerrado, la prioridad pasa a **implementación** y luego a mejoras iterativas. Orden razonable para fases posteriores:

1. Endpoints de calendario/scheduled ya priorizados: cablear fan-out diario y pruebas de paginación.
2. Estadísticas de jugador/partido (`statistics`, `overall`, rankings): activar con cache y fallback.
3. Forma reciente / historial (si se añaden rutas nuevas o se derivan de datos ya guardados).
4. Señales de lesiones/retiros (solo si hay fuente estable en la API o en otro canal acordado).
5. Live granular (`point-by-point`) y cuadros (`cup-trees`) cuando el producto lo justifique.

---

## Ronda 2 - Endpoints adicionales revisados

### `GET /api/v1/event/{eventId}/statistics`
- Prioridad: `P1` (sube a casi-P0 si se confirma buena cobertura pre-match/live temprana).
- Aporte:
  - Bloques robustos por servicio/return/points/games.
  - Muy util para capa de confianza y para explicar picks (ej. servicio/return edge).
- Riesgo:
  - Puede faltar pre-match en algunos torneos/partidos.
- Decision:
  - Incluir en pipeline tenis como `statistics_tennis` (parser propio, no reutilizar el de futbol sin adaptar).

### `GET /api/v1/team/{playerId}/rankings`
- Prioridad: `P1`
- Aporte:
  - Ranking oficial + variantes (`rankingClass`: team/livetennis/utr), historico simple (`bestRanking`).
  - Excelente para calibrar confianza y detectar mismatch entre ranking del evento y ranking actual.
- Riesgo:
  - Multiples tipos de ranking; hay que elegir una jerarquia canonica.
- Decision:
  - Usar como capa de confianza, no bloqueante de v1.

### `GET /api/v1/team/{playerId}/team-statistics/seasons`
- Prioridad: `P1` (endpoint puente)
- Aporte:
  - Mapa `uniqueTournament` + `season` y `typesMap` para saber que combinaciones soportan `overall/mainDraw`.
  - Sirve para construir rutas validas de season stats sin adivinar IDs.
- Riesgo:
  - Payload pesado; cache recomendado por `playerId`.
- Decision:
  - Incluir como endpoint de descubrimiento/metadata, no en tiempo critico de scoring.

### `GET /api/v1/team/{playerId}/unique-tournament/{utid}/season/{sid}/statistics/overall`
- Prioridad: `P1` / `Confianza+`
- Aporte:
  - Stats agregadas por temporada y torneo para el jugador.
  - Muy valioso para robustecer la capa de confianza en partidos con poca data puntual.
- Riesgo:
  - Cobertura puede variar segun torneo/temporada; conviene fallback cuando no exista.
- Decision:
  - Confirmado y aprobado para capa `Confianza+` (con cache y fallback).

### `GET /api/v1/event/{eventId}/point-by-point`
- Prioridad: `No prioritario` para v1 (operativo), `Confianza+` para fase avanzada in-play.
- Aporte:
  - Granularidad maxima de secuencia de puntos.
- Riesgo:
  - Muy alto costo/volumen; innecesario para modelo pre-match inicial.
- Decision:
  - Posponer para fase 2/3 (analitica live o debugging fino).

### `GET /api/v1/unique-tournament/{id}/cup-trees`
- Estado: payload validado (`cup_trees.txt` + `cup_trees_2.txt`).
- Prioridad final: `Confianza+` / `No prioritario` para v1.
- Uso real:
  - Brackets/cuadros de torneo y ruta potencial.
- Nota operativa:
  - Es valioso para analitica de cuadro (rutas, qualy->main draw, cruces futuros), pero no bloquea picks v1.
  - Recomendado para fase 2 (ranking de dificultad de ruta / fatiga potencial por cuadro).

---

## Decisiones consolidadas (actualizadas)

- **P0 tenis v1 (confirmados):**
  - `scheduled-tournaments/{date}/page/{n}`
  - `unique-tournament/{id}/scheduled-events/{date}`
  - `event/{id}`
  - `event/{id}/odds/1/featured`
  - `event/{id}/odds/1/all`

- **P1 / Confianza+ (confirmados):**
  - `event/{id}/h2h`
  - `event/{id}/statistics`
  - `team/{playerId}/rankings`
  - `team/{playerId}/team-statistics/seasons`
  - `team/{playerId}/unique-tournament/{utid}/season/{sid}/statistics/overall`
  - `categories/all`
  - `config/default-unique-tournaments/{country}/tennis`

- **Postergar (fase avanzada):**
  - `event/{id}/point-by-point`
  - `unique-tournament/{id}/cup-trees` (ya validado; mover a fase 2 cuando haya tiempo)

---

## MVP tenis v1 (tabla ejecutiva)

Implementar primero solo este bloque para evitar desvio de alcance:

| Endpoint | Capa | Prioridad | Implementar en v1 | Nota operativa |
|---|---|---|---|---|
| `sport/tennis/scheduled-tournaments/{date}/page/{n}` | Ingesta | P0 | Si | Fan-out diario de torneos por fecha |
| `unique-tournament/{id}/scheduled-events/{date}` | Ingesta + contexto | P0 | Si | Lista de partidos del torneo en ese dia |
| `event/{id}` | Contexto | P0 | Si | Metadatos del match (ronda, superficie, ranking, estado) |
| `event/{id}/odds/1/featured` | Cuotas | P0 | Si | Mercado principal y cambios de cuota |
| `event/{id}/odds/1/all` | Cuotas | P0 | Si | Mercados ampliados para picks |
| `event/{id}/h2h` | Confianza+ | P1 | Si (ligero) | Refuerzo de explicabilidad y calibracion |
| `event/{id}/statistics` | Confianza+ | P1 | Si (con fallback) | Usar si existe; no bloquear si falta |
| `team/{playerId}/rankings` | Confianza+ | P1 | Opcional v1 | Entra si no impacta latencia |
| `team/{playerId}/team-statistics/seasons` | Descubrimiento | P1 | Opcional v1 | Útil para resolver utid/season válidos |
| `team/{playerId}/unique-tournament/{utid}/season/{sid}/statistics/overall` | Confianza+ | P1 | Opcional v1 | Activar con cache + fallback |
| `sport/tennis/categories/all` | Gobernanza | P1 | Si (offline/config) | Whitelist/blacklist de categorías |
| `config/default-unique-tournaments/{country}/tennis` | Priorización | P1 | Opcional v1 | Priorizar torneos top por región |
| `event/{id}/point-by-point` | Live granular | Confianza+ | No | Fase 2/3 |
| `unique-tournament/{id}/cup-trees` | Bracket/ruta | Confianza+ | No | Fase 2 |

### Reglas de oro MVP

1. Si falta un endpoint P1, el pipeline **no se cae**; marca `*_ok=false` y sigue.
2. Si falta un endpoint P0 de cuotas, el evento no debe generar pick (o baja a tier degradado explícito).
3. Parser tenis separado del parser fútbol para mercados (evitar supuestos 1X2 con empate).
4. Filtro inicial estricto: singles + pro + categorías operables.

---

## Decision de arquitectura de datos (linea base)

Mantener **misma DB y esquema compartido multi-deporte**, extendiendo por `sport` y mapeadores por deporte.
Evitar duplicar tablas completas por tenis salvo necesidad puntual de extension.

---

## Plan ejecutable en el repo

Esta sección enlaza el **MVP** con el código real: qué ya corre, qué falta y en qué orden tocarlo.

### Aclaración: endpoints del roadmap vs código actual

**No** está integrada una llamada HTTP **por cada fila** del inventario P0/P1 del documento anterior. Lo que hay hoy es:

| Tema | Realidad en el repo |
|------|---------------------|
| **Descubrimiento diario tenis** | Sí: `scheduled-tournaments` → `unique-tournament/…/scheduled-events` + fallback `scheduled-events` (`core/tennis_daily_schedule.py`). |
| **Por cada `event_id`** | Un solo pipeline Playwright: `core/event_bundle_scraper.py` pide las URLs **compartidas** con fútbol (`/event/{id}`, `/odds/1/all`, `/odds/1/featured`, `/h2h`, `/statistics`, `lineups`, `team-streaks`, stats de temporada vía IDs del evento). |
| **P1 extra del roadmap** | **No** hay fetches dedicados a `team/{playerId}/rankings`, `categories/all`, `default-unique-tournaments`, `…/statistics/overall` como rutas aparte; parte de eso puede solaparse con lo que ya trae `event/{id}`, pero **no** está el árbol completo del roadmap. |
| **Parsers** | Cuotas amplias: `processors/tennis_odds_processor.py` → `processed.tennis_odds`. Resto de `processed.*` sigue pensado sobre todo para fútbol (p. ej. `process_statistics`); en tenis puede venir vacío o poco útil sin trabajo adicional. |

### Contrato candidato → DeepSeek (cómo fluye)

1. **`select_candidates`** (`jobs/select_candidates.py`) lee `daily_runs.sport` y las filas `event_features` del `captured_at_utc` del run (con `sport` alineado).
2. **`core/candidate_contract.py`** aplica reglas **distintas para tenis**:
   - **Base:** `event_ok` + (`odds_all_ok` **o** `odds_featured_ok`). **No** exige `lineups_ok`, `h2h_ok` ni `team_streaks_ok` (en fútbol sí).
   - **Tier A:** base + (`statistics_ok` **o** `h2h_ok`). **Tier B:** solo base si no hay stats ni h2h útiles.
3. El JSON de salida incluye **`ds_input`**: por evento seleccionado, un objeto con `event_context`, `processed` (incluye `tennis_odds` si el bundle fue tenis), `diagnostics`, `selection_tier`, `schedule_display`.
4. **`split_ds_batches`** trocea ese JSON en lotes.
5. **`deepseek_batches_to_telegram_payload_parts`** envía cada lote a la API DeepSeek (OpenAI-compatible) y genera las partes del payload Telegram / picks.

El modelo **no** recibe URLs de SofaScore: recibe el **bundle ya procesado** en JSON. El recordatorio en consola de `select_candidates` para tenis es: **1 = home (jugador local), 2 = away**; mercado típico no es 1X2 con empate.

### Mapa rápido: MVP ↔ código

| Área MVP | Qué hace el repo hoy | Siguiente mejora lógica |
|----------|----------------------|-------------------------|
| P0 ingesta diaria (torneos → eventos) | `core/tennis_daily_schedule.py` + rama `--sport tennis` en `jobs/ingest_daily_events.py` | Afinar parsing si SofaScore cambia forma de `groups`; tuneo de paginación `max_tournament_pages` |
| P0 `event/{id}` + cuotas | `core/event_bundle_scraper.py` (`fetch_event_bundle`, mismas URLs que fútbol) | Marcar en diagnósticos qué datasets son “soft fail” en tenis (p. ej. lineups vacíos) |
| Cuotas tenis (`odds/1/all`) | `processors/tennis_odds_processor.py` → `processed.tennis_odds` | Ampliar mercados ancla según picks que quieras emitir |
| Contrato / prompts | `core/candidate_contract.py`, `jobs/select_candidates.py` | Mantener 1=home / 2=away explícito en copy |
| Dashboard / runs | Web: `sport=tennis`, `useBarDailyRunId`, API `LOWER(TRIM(sport))` | — |
| Validación fecha ingesta | `ALTEA_ALLOW_DIVERGENT_INGEST_DATE`, chequeo ±400 días en `ingest_daily_events` | — |

### Variables de entorno (tenis)

| Variable | Efecto |
|----------|--------|
| `ALTEA_TENNIS_MVP_FILTER` | `1` (default): solo eventos con filtros MVP (`singles` + `pro`, sin `virtual`/`simulated` en category). `0`: desactiva el filtro (útil para depurar). |
| `ALTEA_ALLOW_DIVERGENT_INGEST_DATE=1` | Permite `--date` muy lejana de hoy (ingesta histórica / typo a propósito). |
| `INCLUDE_FINISHED=1` o `--include-finished` | Persiste bundles de partidos ya `finished` (backtest). |

### Fase 0 — Comprobar entorno

1. Python 3 con `PYTHONPATH=.` en la raíz del repo.
2. Playwright/Chromium operativo para `persist_event_bundle` (misma pista que fútbol).
3. Base SQLite inicializada (`db/init_db` vía job o API).

### Fase 1 — Ingesta diaria P0 (listo para ejecutar)

**Objetivo:** obtener `event_id` del día con la ruta canónica del roadmap y persistir features.

```bash
# Sustituye DB y fecha
PYTHONPATH=. python3 jobs/ingest_daily_events.py --sport tennis --date YYYY-MM-DD --db db/sport-tracker.sqlite3 --limit 5
```

Comportamiento:

1. Intenta **scheduled-tournaments** por página → **unique-tournament/…/scheduled-events** (fan-out).
2. Si no obtiene IDs, hace **fallback** a `sport/tennis/scheduled-events/{date}` (comportamiento previo).
3. Cada id pasa por `persist_event_bundle` con `--sport tennis` (cuotas enriquecidas con `tennis_odds`).

**Checklist**

- [ ] El job imprime `schedule_source: tennis P0 …` y `event_ids_fetched > 0` en un día con ATP/WTA.
- [ ] En SQLite, `event_features.sport = 'tennis'` y `daily_runs.sport = 'tennis'` para ese run.
- [ ] Si el filtro MVP deja 0 eventos, probar `ALTEA_TENNIS_MVP_FILTER=0` un momento para ver si el problema es filtro o API vacía.

### Fase 2 — Selección / modelo (`select_candidates` + DeepSeek)

**Objetivo:** generar `out/candidates_{date}_select_tennis.json` alineado al contrato tenis.

- Ejecutar el pipeline que ya usáis para fútbol adaptando `daily_run_id` y artefactos `_tennis`.
- Validar en UI: dashboard pestaña Tenis, enlaces a eventos/picks del run.

**Checklist**

- [ ] Artefacto `select_tennis` presente para la fecha.
- [ ] Números del dashboard (eventos / picks) coherentes con DB.

### Fase 3 — P1 / confianza (sin bloquear v1)

Activar de forma **opcional** y con `*_ok=false` tolerado:

- `event/{id}/statistics` (parser tenis dedicado cuando toque).
- `team/{playerId}/rankings` y cadena season/overall con caché.
- `categories/all` como whitelist offline (JSON en repo o env).

### Fase 4 — Telegram / persist picks

Mismo flujo que fútbol: payload merge → `persist_picks` → tablero web.

### Comando de referencia (cadena mínima)

```text
ingest_daily_events (tennis) → select_candidates (tennis) → batches DeepSeek → merge payload → persist_picks
```

Ajusta nombres de scripts y flags a los que tengáis en `jobs/` y en el runner nocturno (`independent_runner` / cron).

### Notas anti-alucinación

- La API de SofaScore **no está documentada oficialmente**; si un endpoint devuelve `403` desde datacenters o bots, el navegador Playwright sigue siendo la fuente de verdad para el bundle completo.
- Si el JSON de **scheduled-tournaments** cambia de forma, actualizar solo `core/tennis_daily_schedule.py` (extractores), no el resto del pipeline.

