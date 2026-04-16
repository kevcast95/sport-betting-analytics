"""
T-283 — matching D-06-068 §6 (liga via UT, kickoff, nombres normalizados).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from apps.api.bt2_benchmark_team_name_normalize import normalize_benchmark_team_name


def match_sofa_event_for_sm_fixture(
    *,
    kickoff_utc: datetime,
    home_name: str,
    away_name: str,
    expected_unique_tournament_id: int,
    sofa_stubs: list[dict[str, Any]],
    max_skew_seconds: int = 720,
) -> tuple[Optional[int], bool, str]:
    """
    Devuelve (sofascore_event_id | None, needs_review, map_note).
    needs_review true si ambigüedad o sin candidato usable.
    """
    if kickoff_utc.tzinfo is None:
        kickoff_utc = kickoff_utc.replace(tzinfo=timezone.utc)
    hn = normalize_benchmark_team_name(home_name)
    an = normalize_benchmark_team_name(away_name)
    if not hn or not an:
        return None, True, "missing_sm_names"

    cands: list[dict[str, Any]] = []
    for s in sofa_stubs:
        if int(s.get("unique_tournament_id", -1)) != int(expected_unique_tournament_id):
            continue
        sk = s.get("kickoff_utc")
        if not isinstance(sk, datetime):
            continue
        if sk.tzinfo is None:
            sk = sk.replace(tzinfo=timezone.utc)
        if abs((sk - kickoff_utc).total_seconds()) > max_skew_seconds:
            continue
        sh = normalize_benchmark_team_name(str(s.get("home_name") or ""))
        sa = normalize_benchmark_team_name(str(s.get("away_name") or ""))
        if sh == hn and sa == an:
            cands.append(s)

    if len(cands) == 1:
        return int(cands[0]["sofascore_event_id"]), False, ""
    if len(cands) == 0:
        return None, True, "no_candidate"
    return None, True, "ambiguous"
