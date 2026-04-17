"""Idempotencia upsert snapshot (T-275) — mock de sesión."""

from __future__ import annotations

from unittest.mock import MagicMock

from apps.api.bt2_models import Bt2ProviderOddsSnapshot
from apps.api.bt2.providers.sofascore.snapshot_repo import upsert_provider_odds_snapshot


def test_upsert_overwrites_same_key() -> None:
    existing = MagicMock(spec=Bt2ProviderOddsSnapshot)
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = existing
    upsert_provider_odds_snapshot(
        session,
        bt2_event_id=1,
        provider="sofascore_experimental",
        source_scope="featured",
        run_id="r1",
        raw_payload={"a": 2},
        provider_event_ref="99",
    )
    assert existing.raw_payload == {"a": 2}
    assert existing.provider_event_ref == "99"


def test_upsert_inserts_when_missing() -> None:
    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = None
    upsert_provider_odds_snapshot(
        session,
        bt2_event_id=2,
        provider="sofascore_experimental",
        source_scope="all",
        run_id="r1",
        raw_payload={"x": 1},
        provider_event_ref="88",
    )
    session.add.assert_called_once()
