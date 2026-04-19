"""Tests ligeros — replay ciego (utilidades de tiempo y máscara)."""

from __future__ import annotations

from apps.api.bt2_admin_backtest_replay import (
    BLIND_LOT_OPERATING_DAY_KEY,
    blind_ds_input_item,
    bogota_operating_day_utc_window,
)


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

