"""
D-06-037 / T-197 — includes comunes para fixtures SportMonks v3 (cubo A).

Usado por `scripts/bt2_atraco/sportmonks_worker.py` y `scripts/bt2_cdm/fetch_upcoming.py`.
"""

from __future__ import annotations

# Sin `lineups.details` en fase 1 (payload más liviano; el builder usa agregados).
BT2_SM_FIXTURE_INCLUDES: str = (
    "participants;odds;statistics;events;league;scores;"
    "lineups;formations;sidelined"
)
