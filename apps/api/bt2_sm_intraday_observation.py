"""
US-BE-061 / T-281 — lógica pura: ventanas D-06-068 §2 y flags §4–§5 desde payload SM.

Sin HTTP ni DSR. No productivo.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from apps.api.bt2_dsr_context_queries import extract_lineups_summary_from_raw_payload

# Once inicial SM: type_id 11; umbral alineado a extract_lineups_summary (F2 / CDM).
_MIN_STARTING_XI_ROWS = 11


def sm_observation_poll_interval_seconds(now: datetime, kickoff: datetime) -> Optional[int]:
    """
    Intervalo mínimo entre observaciones en el instante `now` (D-06-068 §2).
    None si fuera de ventana (antes de T−24h o después de T+15m).
    """
    if kickoff.tzinfo is None:
        kickoff = kickoff.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    if now < kickoff - timedelta(hours=24):
        return None
    if now > kickoff + timedelta(minutes=15):
        return None
    if now < kickoff - timedelta(hours=6):
        return 3600
    if now < kickoff - timedelta(minutes=90):
        return 900
    return 300


def sm_observation_should_poll(
    now: datetime,
    kickoff: datetime,
    last_observed_at: Optional[datetime],
) -> bool:
    iv = sm_observation_poll_interval_seconds(now, kickoff)
    if iv is None:
        return False
    if last_observed_at is None:
        return True
    if last_observed_at.tzinfo is None:
        last_observed_at = last_observed_at.replace(tzinfo=timezone.utc)
    elapsed = (now - last_observed_at).total_seconds()
    return elapsed >= iv


def lineup_flags_from_sm_payload(payload: dict[str, Any]) -> tuple[bool, bool, bool]:
    """
    (lineup_home_usable, lineup_away_usable, lineup_available) según D-06-068 §4.
    """
    summ = extract_lineups_summary_from_raw_payload(payload)
    if not summ:
        return (False, False, False)
    h = int(summ.get("starting_xi_rows_home") or 0)
    a = int(summ.get("starting_xi_rows_away") or 0)
    hu = h >= _MIN_STARTING_XI_ROWS
    au = a >= _MIN_STARTING_XI_ROWS
    return (hu, au, hu and au)


def _odd_value_usable(o: dict[str, Any]) -> Optional[float]:
    try:
        v = float(o.get("value") or 0)
    except (TypeError, ValueError):
        return None
    if v <= 1.0:
        return None
    return v


def _norm_label(o: dict[str, Any]) -> str:
    return str(o.get("label") or o.get("name") or "").strip().lower()


def _is_1x2_home(sl: str) -> bool:
    return sl in ("1", "home", "1 (home)") or sl.startswith("home")


def _is_1x2_draw(sl: str) -> bool:
    return sl in ("x", "draw", "x (draw)") or sl.startswith("draw")


def _is_1x2_away(sl: str) -> bool:
    return sl in ("2", "away", "2 (away)") or sl.startswith("away")


def _is_ou_over(sl: str) -> bool:
    return "over" in sl and "under" not in sl


def _is_ou_under(sl: str) -> bool:
    return "under" in sl


def _is_btts_yes(sl: str) -> bool:
    return sl in ("yes", "si", "sí", "ja") or sl.startswith("yes")


def _is_btts_no(sl: str) -> bool:
    return sl == "no" or sl.startswith("no ")


def _market_desc_lower(o: dict[str, Any]) -> str:
    return str(o.get("market_description") or o.get("name") or "").strip().lower()


def market_flags_from_sm_payload(payload: dict[str, Any]) -> tuple[bool, bool, bool]:
    """
    (ft_1x2_available, ou_goals_2_5_available, btts_available) según D-06-068 §5.

    FT_1X2: market_id 1 y piernas home/draw/away con cuota > 1.
    OU 2.5: market_id 80, total 2.5, over y under usables.
    BTTS: heurística por texto de mercado + yes/no usables (SportMonks no documenta
    un market_id único en repo; se alinea a heurística de bt2_dsr_odds_aggregation).
    """
    raw = payload.get("odds") or []
    if not isinstance(raw, list):
        return (False, False, False)

    has_home = has_draw = has_away = False
    has_over = has_under = False
    has_yes = has_no = False

    for o in raw:
        if not isinstance(o, dict):
            continue
        v = _odd_value_usable(o)
        if v is None:
            continue
        sl = _norm_label(o)
        if not sl:
            continue
        mid = o.get("market_id")
        try:
            mid_i = int(mid) if mid is not None else None
        except (TypeError, ValueError):
            mid_i = None

        if mid_i == 1:
            if _is_1x2_home(sl):
                has_home = True
            elif _is_1x2_draw(sl):
                has_draw = True
            elif _is_1x2_away(sl):
                has_away = True

        if mid_i == 80:
            total = str(o.get("total") or "")
            if total in ("2.5", "2,5"):
                if _is_ou_over(sl):
                    has_over = True
                elif _is_ou_under(sl):
                    has_under = True

        md = _market_desc_lower(o)
        if "both teams" in md or "btts" in md or ("both" in md and "score" in md):
            if _is_btts_yes(sl):
                has_yes = True
            elif _is_btts_no(sl):
                has_no = True

    ft = has_home and has_draw and has_away
    ou = has_over and has_under
    bt = has_yes and has_no
    return (ft, ou, bt)
