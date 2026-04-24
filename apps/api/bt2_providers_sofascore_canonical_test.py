"""Tests S6.5 — mapeo canónico SFS (T-273)."""

from __future__ import annotations

from apps.api.bt2.providers.sofascore.canonical_map import (
    count_core_additional_complete,
    is_event_useful_s65,
    is_ft_1x2_complete,
    map_all_raw_to_rows,
    map_featured_raw_to_rows,
    merge_canonical_rows,
)


def test_map_featured_minimal_ft_1x2() -> None:
    raw = {
        "featured": {
            "fullTime": {
                "choices": [
                    {"name": "1", "fractionalValue": "1/1"},
                    {"name": "X", "fractionalValue": "2/1"},
                    {"name": "2", "fractionalValue": "5/1"},
                ]
            }
        }
    }
    rows = map_featured_raw_to_rows(raw)
    assert is_ft_1x2_complete(rows)
    assert count_core_additional_complete(rows) == 0
    assert not is_event_useful_s65(rows)


def test_merge_featured_plus_all_useful() -> None:
    raw_f = {
        "featured": {
            "fullTime": {
                "choices": [
                    {"name": "1", "fractionalValue": "10/11"},
                    {"name": "X", "fractionalValue": "11/4"},
                    {"name": "2", "fractionalValue": "9/2"},
                ]
            }
        }
    }
    raw_a = {
        "markets": [
            {
                "marketName": "Both teams to score",
                "choices": [
                    {"name": "yes", "fractionalValue": "5/4"},
                    {"name": "no", "fractionalValue": "4/7"},
                ],
            }
        ]
    }
    merged = merge_canonical_rows(map_featured_raw_to_rows(raw_f), map_all_raw_to_rows(raw_a))
    assert is_event_useful_s65(merged)
