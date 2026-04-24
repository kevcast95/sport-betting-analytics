"""Tests ligeros — replay ciego (utilidades de tiempo y máscara)."""

from __future__ import annotations

from datetime import datetime, timezone

from apps.api.bt2_admin_backtest_replay import (
    BLIND_LOT_OPERATING_DAY_KEY,
    blind_ds_input_item,
    bogota_operating_day_utc_window,
)
from apps.api.bt2_dsr_ds_input_builder import _normalize_odds_rows_for_aggregate
from apps.api.bt2_dsr_odds_aggregation import aggregate_odds_for_event


def test_bogota_window_ordering() -> None:
    a, b = bogota_operating_day_utc_window("2026-04-15")
    assert a < b
    assert (b - a).total_seconds() == 86400.0


def test_blind_strips_real_timestamp() -> None:
    item = {
        "event_id": 1,
        "schedule_display": {"utc_iso": "2020-01-01T00:00:00Z", "timezone_reference": "UTC"},
        "event_context": {"start_timestamp_unix": 1_000_000, "home_team": "A", "away_team": "B"},
    }
    b = blind_ds_input_item(item)
    assert b["schedule_display"]["utc_iso"] == "2099-06-15T20:00:00Z"
    assert "start_timestamp_unix" not in b["event_context"]


def test_constant_blind_day_not_calendar() -> None:
    assert BLIND_LOT_OPERATING_DAY_KEY.startswith("2099")


def test_normalize_odds_rows_mapping_matches_tuple() -> None:
    ft = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    tup = ("bk", "Match Winner", "Home", 2.1, ft)
    mapping = {
        "bookmaker": "bk",
        "market": "Match Winner",
        "selection": "Home",
        "odds": 2.1,
        "fetched_at": ft,
    }
    a1 = aggregate_odds_for_event([tup], min_decimal=1.30)
    a2 = aggregate_odds_for_event(_normalize_odds_rows_for_aggregate([mapping]), min_decimal=1.30)
    assert a1.consensus == a2.consensus

