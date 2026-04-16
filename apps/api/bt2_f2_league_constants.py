"""
T-258 — Universo oficial de 5 ligas (F2 / DECISIONES_CIERRE_F2_S6_3_FINAL §7).

Identificadores **SportMonks** (`sportmonks_id` en `bt2_leagues`) como fuente estable para
resolver `bt2_leagues.id` sin ambigüedad. Valores alineados a API Football v3 típica; si tu seed
difiere, sobreescribí con **`BT2_F2_OFFICIAL_LEAGUE_IDS`** (IDs internos `bt2_leagues.id`, coma-separados).
"""

from __future__ import annotations

import os
import re
from typing import Optional

# sportmonks_id oficial por clave interna (orden §7 del doc).
F2_OFFICIAL_LEAGUE_SPORTMONKS_IDS: dict[str, int] = {
    "premier_league": 8,
    "la_liga": 564,
    "serie_a": 384,
    "bundesliga": 82,
    "ligue_1": 301,
}

F2_OFFICIAL_LEAGUE_DISPLAY_ORDER: tuple[tuple[str, str, int], ...] = (
    ("premier_league", "Premier League", F2_OFFICIAL_LEAGUE_SPORTMONKS_IDS["premier_league"]),
    ("la_liga", "LaLiga", F2_OFFICIAL_LEAGUE_SPORTMONKS_IDS["la_liga"]),
    ("serie_a", "Serie A", F2_OFFICIAL_LEAGUE_SPORTMONKS_IDS["serie_a"]),
    ("bundesliga", "Bundesliga", F2_OFFICIAL_LEAGUE_SPORTMONKS_IDS["bundesliga"]),
    ("ligue_1", "Ligue 1", F2_OFFICIAL_LEAGUE_SPORTMONKS_IDS["ligue_1"]),
)

_ENV_BT2_F2_LEAGUE_IDS = "BT2_F2_OFFICIAL_LEAGUE_IDS"


def parse_f2_official_league_bt2_ids_from_env() -> Optional[list[int]]:
    """
    Lista opcional de `bt2_leagues.id` (enteros CDM) que sustituyen la resolución por sportmonks_id.
    Formato: coma-separados, p.ej. `3,4,5,6,7`.
    """
    raw = (os.getenv(_ENV_BT2_F2_LEAGUE_IDS) or "").strip()
    if not raw:
        return None
    out: list[int] = []
    for part in raw.split(","):
        p = part.strip()
        if not p:
            continue
        out.append(int(p, 10))
    return out or None


def resolve_f2_official_league_bt2_ids(cur) -> list[int]:
    """
    Devuelve los 5 `bt2_leagues.id` del universo F2.

    Prioridad:
    1. `BT2_F2_OFFICIAL_LEAGUE_IDS` si está definido y tiene longitud > 0.
    2. SELECT por `sportmonks_id` ∈ valores canónicos de `F2_OFFICIAL_LEAGUE_SPORTMONKS_IDS`.
    """
    override = parse_f2_official_league_bt2_ids_from_env()
    if override is not None:
        return sorted(set(override))

    sm_ids = list(F2_OFFICIAL_LEAGUE_SPORTMONKS_IDS.values())
    cur.execute(
        """
        SELECT id FROM bt2_leagues
        WHERE sportmonks_id = ANY(%s::int[])
        ORDER BY id
        """,
        (sm_ids,),
    )
    rows = cur.fetchall()
    found: list[int] = []
    for r in rows:
        if isinstance(r, dict) or hasattr(r, "keys"):
            found.append(int(r["id"]))  # type: ignore[index]
        else:
            found.append(int(r[0]))
    return sorted(set(found))


def league_id_is_f2_tier_a(league_id: Optional[int], f2_bt2_league_ids: set[int]) -> bool:
    """Tier A (refuerzo F2) = evento pertenece a una de las 5 ligas objetivo."""
    if league_id is None:
        return False
    return int(league_id) in f2_bt2_league_ids


def f2_pool_tier_label(league_id: Optional[int], f2_bt2_league_ids: set[int]) -> str:
    return "A" if league_id_is_f2_tier_a(league_id, f2_bt2_league_ids) else "BASE"
