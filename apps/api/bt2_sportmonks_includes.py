"""
D-06-037 / T-197 — includes comunes para fixtures SportMonks v3 (cubo A).

Usado por `scripts/bt2_atraco/sportmonks_worker.py` y `scripts/bt2_cdm/fetch_upcoming.py`.

Objetivo: pedir todo lo que la API documenta como `include` en el recurso fixture
(trial / plan base), más anidados hasta 3 niveles donde enriquecen el contexto
por partido (alineaciones con jugador/posición/detalle, eventos con jugador,
estadísticas con tipo legible).

Referencias:
- https://docs.sportmonks.com/v3/endpoints-and-entities/endpoints/fixtures/get-fixture-by-id
  (tabla «Include options», profundidad máxima 3 en anidados).

Si algún include no está en tu plan o la API devuelve 4xx, recorta aquí o divide
el job; el cliente HTTP usa `params` (query string), no suele haber límite práctico
de longitud por debajo del tope del servidor SM.
"""

from __future__ import annotations

# Bloque base + contexto competición / sede / clima / árbitro / DT / noticias / meta.
_BT2_SM_FIXTURE_INCLUDES_BASE: str = (
    "sport;round;stage;group;aggregate;"
    "league;season;"
    "participants;"
    "venue;state;weatherReport;"
    "tvStations;metadata;"
    "referees;coaches;"
    "prematchNews;postmatchNews;comments;"
    "odds;premiumOdds;inplayOdds;"
    "scores;periods;timeline;"
    "statistics;statistics.type;"
    "events;events.player;"
    "trends;"
    "lineups;lineups.player;lineups.type;lineups.position;lineups.detailedPosition;"
    "lineups.details.type;"
    "formations;expectedLineups;"
    "sidelined;sidelined.sideline;sidelined.player;sidelined.type;"
    "predictions;"
    "ballCoordinates;"
    "xGFixture;pressure;matchfacts;AIOverviews"
)

BT2_SM_FIXTURE_INCLUDES: str = _BT2_SM_FIXTURE_INCLUDES_BASE
