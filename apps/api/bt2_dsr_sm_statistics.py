"""
T-201 — Subconjunto seguro de `statistics[]` del payload SportMonks → `processed.statistics`.

Solo type_id allowlisteados en `bt2_sm_statistic_type_map.json` (anti-fuga D-06-002).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional


def _type_map_path() -> Path:
    return Path(__file__).resolve().parent / "bt2_sm_statistic_type_map.json"


def load_sm_statistic_type_map() -> dict[str, Any]:
    with _type_map_path().open(encoding="utf-8") as f:
        return json.load(f)


def sm_fixture_statistics_block(payload: dict[str, Any]) -> Optional[dict[str, Any]]:
    """
    Devuelve `{ \"available\": true, ...claves del mapa }` o None si no hay métricas mapeadas.
    """
    stats = payload.get("statistics")
    if not isinstance(stats, list) or not stats:
        return None

    try:
        raw_map = load_sm_statistic_type_map()
    except (OSError, json.JSONDecodeError):
        return None

    out: dict[str, Any] = {"available": True}

    for row in stats:
        if not isinstance(row, dict):
            continue
        tid = row.get("type_id")
        if tid is None:
            continue
        try:
            tid_s = str(int(tid))
        except (TypeError, ValueError):
            continue
        spec = raw_map.get(tid_s)
        if not isinstance(spec, dict):
            continue
        kh = spec.get("key_home")
        ka = spec.get("key_away")
        if not isinstance(kh, str) or not isinstance(ka, str):
            continue

        data = row.get("data") if isinstance(row.get("data"), dict) else {}
        val = data.get("value")
        if not isinstance(val, (int, float)):
            try:
                val = int(val)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                continue

        loc = str(row.get("location") or "").lower()
        if loc == "home":
            out[kh] = val
        elif loc == "away":
            out[ka] = val

    if len(out) <= 1:
        return None
    return out


def merge_sm_statistics_into_processed_statistics(
    statistics_block: dict[str, Any],
    sm_inner: dict[str, Any],
) -> None:
    """Anida bajo `from_sm_fixture` sin pisar forma W/D/L u otras claves hermanas."""
    statistics_block["from_sm_fixture"] = sm_inner
