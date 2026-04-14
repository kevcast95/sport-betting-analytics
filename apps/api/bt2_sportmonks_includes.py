"""
D-06-037 / T-197 — includes comunes para fixtures SportMonks v3 (cubo A).

Usado por `scripts/bt2_atraco/sportmonks_worker.py`, `scripts/bt2_cdm/fetch_upcoming.py`
y `bt2_dev_sm_refresh`.

**Criterio de ingesta:** `BT2_SM_FIXTURE_INCLUDES` es la lista *deseada* (núcleo +
extras). Los clientes HTTP deben usar `bt2_sportmonks_include_resolve`: ante 403
por include no contratado se degrada automáticamente; los cálculos / DSR ya son
agnósticos a nodos ausentes en el JSON.

Referencias:
- https://docs.sportmonks.com/v3/endpoints-and-entities/endpoints/fixtures/get-fixture-by-id

El trial Pro típico devuelve 403 `code=5002` para algunos extras; no hace falta
mantener el archivo recortado a mano si la resolución 403 está activa.
"""

from __future__ import annotations

# Núcleo: contexto partido + odds estándar + estadísticas / alineaciones / xG…
BT2_SM_FIXTURE_INCLUDES_CORE: str = (
    "sport;round;stage;group;aggregate;"
    "league;season;"
    "participants;"
    "venue;state;weatherReport;"
    "tvStations;metadata;"
    "referees;coaches;"
    "comments;"
    "odds;inplayOdds;"
    "scores;periods;timeline;"
    "statistics;statistics.type;"
    "events;events.player;"
    "trends;"
    "lineups;lineups.player;lineups.type;lineups.position;lineups.detailedPosition;"
    "lineups.details.type;"
    "formations;"
    "sidelined;sidelined.sideline;sidelined.player;sidelined.type;"
    "predictions;"
    "ballCoordinates;"
    "xGFixture;pressure;matchfacts"
)

# Extras: si el plan los permite, vienen en el raw; si no, 403 → se omiten vía resolve.
BT2_SM_FIXTURE_INCLUDES_OPTIONAL: tuple[str, ...] = (
    "premiumOdds",
    "prematchNews",
    "postmatchNews",
    "expectedLineups",
)


def bt2_sm_join_include_segments(*segments: str) -> str:
    parts: list[str] = []
    for seg in segments:
        for p in seg.split(";"):
            s = p.strip()
            if s:
                parts.append(s)
    return ";".join(parts)


BT2_SM_FIXTURE_INCLUDES: str = bt2_sm_join_include_segments(
    BT2_SM_FIXTURE_INCLUDES_CORE,
    ";".join(BT2_SM_FIXTURE_INCLUDES_OPTIONAL),
)
