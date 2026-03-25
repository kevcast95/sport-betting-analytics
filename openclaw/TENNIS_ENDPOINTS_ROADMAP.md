# Tennis Endpoints Roadmap (SofaScore)

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

